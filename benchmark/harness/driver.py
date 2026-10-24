"""Execution driver: runs ONE benchmark case under the Django installed in this interpreter.

Runs inside the labeling container (Python 3.10). Never imports CodeMigrate. Output is a JSON
document with every exception and warning attributed to case file lines, plus line coverage.

Usage: python driver.py <case_dir> <out_json>

Python files are executed statement by statement (multi-name ``from x import a, b`` is split
into one statement per name) so one failure doesn't hide later ones. Settings cases are
loaded through ``django.setup()``; templates are rendered with the Django template engine.
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
import traceback
import warnings
from pathlib import Path

DJANGO_WARNING_RE = re.compile(r"^(RemovedInDjango\d+Warning|RemovedAfterNextVersionWarning)$")
STRING_SETTINGS = ("MIDDLEWARE", "PASSWORD_HASHERS", "AUTHENTICATION_BACKENDS",
                   "SESSION_SERIALIZER", "DEFAULT_FILE_STORAGE", "STATICFILES_STORAGE",
                   "FORM_RENDERER", "TEST_RUNNER", "MESSAGE_STORAGE")

BASE_SETTINGS = dict(
    SECRET_KEY="benchmark",
    DEBUG=True,
    USE_TZ=True,
    INSTALLED_APPS=[
        "django.contrib.contenttypes",
        "django.contrib.auth",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.admin",
        "django.contrib.sitemaps",
    ],
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    DEFAULT_AUTO_FIELD="django.db.models.AutoField",
    ROOT_URLCONF=__name__,
    TEMPLATES=[{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [],
                "APP_DIRS": True, "OPTIONS": {}}],
)
urlpatterns: list = []


class Recorder:
    def __init__(self, case_dir: Path) -> None:
        self.case_dir = case_dir.resolve()
        self.events: list[dict] = []
        self.executed: dict[str, set[int]] = {}
        self._rel_cache: dict[str, str | None] = {}

    def rel(self, filename: str) -> str | None:
        """Case-relative path of ``filename`` (memoized: called for every traced frame)."""
        if filename in self._rel_cache:
            return self._rel_cache[filename]
        try:
            rel = Path(filename).resolve().relative_to(self.case_dir).as_posix()
        except (ValueError, OSError):
            rel = None
        self._rel_cache[filename] = rel
        return rel

    def tracer(self, frame, event, arg):
        rel = self.rel(frame.f_code.co_filename)
        if rel is None:
            return None
        if event in ("line", "call"):
            self.executed.setdefault(rel, set()).add(frame.f_lineno)
        return self.tracer

    def warning_events(self, caught, file: str, stmt_line: int, stmt_end: int, phase: str):
        for w in caught:
            cat = w.category.__name__
            wrel = self.rel(w.filename)
            if wrel == file:
                line, how = w.lineno, "warning_location"
            else:
                line, how = stmt_line, "statement"
            norm = str(w.filename).replace("\\", "/")
            origin = ("case" if wrel == file else "django" if "/django/" in norm
                      else "other")  # "other": raised for another (third-party) module
            self.events.append({
                "kind": "warning", "file": file, "line": line, "stmt_line": stmt_line,
                "stmt_end": stmt_end, "type": cat, "django": bool(DJANGO_WARNING_RE.match(cat)),
                "message": str(w.message)[:500], "attribution": how, "phase": phase,
                "origin": origin, "transitive": origin == "other",
            })

    def error_event(self, exc: BaseException, file: str, stmt_line: int, stmt_end: int,
                    phase: str, failed_names: set[str]):
        tb = traceback.extract_tb(exc.__traceback__)
        case_frames = [i for i, fr in enumerate(tb) if self.rel(fr.filename) == file]
        line = tb[case_frames[-1]].lineno if case_frames else stmt_line
        after = tb[case_frames[-1] + 1:] if case_frames else tb
        # Frames after the case frame that are neither Django nor stdlib: the failure
        # originated in some other (third-party/package) module -> transitive.
        transitive = any(
            "site-packages" in fr.filename and "/django/" not in fr.filename.replace("\\", "/")
            for fr in after
        )
        cascade = isinstance(exc, NameError) and any(
            re.search(rf"'{re.escape(n)}'", str(exc)) for n in failed_names
        )
        self.events.append({
            "kind": "error", "file": file, "line": line, "stmt_line": stmt_line,
            "stmt_end": stmt_end, "type": type(exc).__name__, "message": str(exc)[:500],
            "transitive": transitive, "cascade": cascade, "phase": phase,
            "traceback_tail": [f"{Path(fr.filename).name}:{fr.lineno}" for fr in tb[-4:]],
        })


def split_statements(tree: ast.Module) -> list[ast.stmt]:
    out = []
    for stmt in tree.body:
        if isinstance(stmt, ast.ImportFrom) and len(stmt.names) > 1:
            for alias in stmt.names:
                single = ast.ImportFrom(module=stmt.module, names=[alias], level=stmt.level)
                ast.copy_location(single, stmt)
                single.end_lineno = stmt.end_lineno
                out.append(single)
        elif isinstance(stmt, ast.Import) and len(stmt.names) > 1:
            for alias in stmt.names:
                single = ast.Import(names=[alias])
                ast.copy_location(single, stmt)
                single.end_lineno = stmt.end_lineno
                out.append(single)
        else:
            out.append(stmt)
    return out


def bound_names(stmt: ast.stmt) -> set[str]:
    if isinstance(stmt, (ast.Import, ast.ImportFrom)):
        return {(a.asname or a.name).split(".")[0] for a in stmt.names}
    names = set()
    for node in ast.walk(stmt):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            names.add(node.name)
    return names


def run_python(rec: Recorder, case_dir: Path, rel: str, module_name: str) -> None:
    path = case_dir / rel
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    package = module_name.rpartition(".")[0]
    ns = {"__name__": module_name, "__file__": str(path), "__package__": package or None,
          "__builtins__": __builtins__}
    failed: set[str] = set()
    for stmt in split_statements(tree):
        code = compile(ast.Module(body=[stmt], type_ignores=[]), str(path), "exec")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            sys.settrace(rec.tracer)
            try:
                exec(code, ns)
            except Exception as exc:  # noqa: BLE001 - every failure is the data we record
                sys.settrace(None)
                rec.error_event(exc, rel, stmt.lineno, stmt.end_lineno or stmt.lineno, "exec",
                                failed)
                failed |= bound_names(stmt)
            finally:
                sys.settrace(None)
        rec.warning_events(caught, rel, stmt.lineno, stmt.end_lineno or stmt.lineno, "exec")
    # Exercise zero-argument functions named exercise* (used by hand-written cases).
    for name, fn in list(ns.items()):
        if name.startswith("exercise") and callable(fn):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                sys.settrace(rec.tracer)
                try:
                    fn()
                except Exception as exc:  # noqa: BLE001
                    sys.settrace(None)
                    line = fn.__code__.co_firstlineno
                    rec.error_event(exc, rel, line, line, "exercise", failed)
                finally:
                    sys.settrace(None)
            line = fn.__code__.co_firstlineno
            rec.warning_events(caught, rel, line, line, "exercise")


def line_of(source_lines: list[str], needle: str) -> int | None:
    for i, line in enumerate(source_lines, 1):
        if needle in line:
            return i
    return None


def attribute_by_message(rec: Recorder, rel: str, source: str, kind: str, type_: str,
                         message: str, phase: str, **extra) -> None:
    """Attribute a setup-time warning/error to the settings line it mentions."""
    lines = source.splitlines()
    candidates = re.findall(r"[A-Za-z_][\w.]{2,}", message)
    line = None
    for cand in sorted(set(candidates), key=len, reverse=True):
        if cand.isupper() or "." in cand or "_" in cand:
            line = line_of(lines, cand)
            if line:
                break
    rec.events.append({
        "kind": kind, "file": rel, "line": line, "stmt_line": line, "stmt_end": line,
        "type": type_, "message": message[:500], "attribution": "message" if line else "none",
        "phase": phase, "django": bool(DJANGO_WARNING_RE.match(type_)), **extra,
    })


def run_settings(rec: Recorder, case_dir: Path, rel: str) -> bool:
    """Load ``rel`` as the settings module via django.setup(); exercise import strings."""
    import django
    from django.conf import settings

    source = (case_dir / rel).read_text(encoding="utf-8")
    os.environ["DJANGO_SETTINGS_MODULE"] = rel[:-3].replace("/", ".")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            django.setup()
        except Exception as exc:  # noqa: BLE001
            attribute_by_message(rec, rel, source, "error", type(exc).__name__, str(exc),
                                 "setup", transitive=False, cascade=False)
            return False
    for w in caught:
        attribute_by_message(rec, rel, source, "warning", w.category.__name__, str(w.message),
                             "setup")
    from django.utils.module_loading import import_string

    for name in STRING_SETTINGS:
        value = getattr(settings, name, None)
        values = value if isinstance(value, (list, tuple)) else [value]
        for v in values:
            if not isinstance(v, str) or "." not in v:
                continue
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                try:
                    import_string(v)
                except Exception as exc:  # noqa: BLE001
                    rec.events.append({
                        "kind": "error", "file": rel, "line": line_of(source.splitlines(), v),
                        "type": type(exc).__name__, "message": str(exc)[:500],
                        "transitive": False, "cascade": False, "phase": "import_string",
                        "attribution": "setting_value",
                    })
            for w in caught:
                attribute_by_message(rec, rel, source, "warning", w.category.__name__,
                                     str(w.message), "import_string")
    lines = source.splitlines()
    executed = {i for i, line in enumerate(lines, 1) if line.strip() and not line.startswith("#")}
    rec.executed[rel] = executed  # settings modules are fully executed by setup()
    return True


def run_template(rec: Recorder, case_dir: Path, rel: str) -> None:
    from django.template import Context, Engine

    source = (case_dir / rel).read_text(encoding="utf-8")
    engine = Engine(debug=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            engine.from_string(source).render(Context({"items": [1, 2], "value": "x"}))
        except Exception as exc:  # noqa: BLE001
            info = getattr(exc, "template_debug", None)
            line = info["line"] if info else None
            if line is None:
                attribute_by_message(rec, rel, source, "error", type(exc).__name__, str(exc),
                                     "render", transitive=False, cascade=False)
            else:
                rec.events.append({"kind": "error", "file": rel, "line": line, "type":
                                   type(exc).__name__, "message": str(exc)[:500],
                                   "transitive": False, "cascade": False, "phase": "render",
                                   "attribution": "template_debug"})
    for w in caught:
        attribute_by_message(rec, rel, source, "warning", w.category.__name__, str(w.message),
                             "render")
    rec.executed[rel] = set(range(1, len(source.splitlines()) + 1))


def main() -> None:
    case_dir = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2])
    meta = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    rec = Recorder(case_dir)
    result = {"case_id": meta["case_id"], "python": sys.version.split()[0], "setup_error": None}
    import django

    result["django"] = django.get_version()
    if meta.get("add_case_dir_to_path", True):
        sys.path.insert(0, str(case_dir))
    for extra in meta.get("sys_path", []):
        sys.path.insert(0, str(case_dir / extra))
    settings_file = meta.get("settings_file")
    try:
        if settings_file:
            run_settings(rec, case_dir, settings_file)
        else:
            from django.conf import settings

            cfg = dict(BASE_SETTINGS)
            cfg["INSTALLED_APPS"] = cfg["INSTALLED_APPS"] + meta.get("installed_apps", [])
            settings.configure(**cfg)
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                try:
                    django.setup()
                except Exception as exc:  # noqa: BLE001
                    # Retry without case-provided apps (they may themselves be broken).
                    result["setup_error"] = f"{type(exc).__name__}: {exc}"[:500]
                    from django.apps import apps

                    apps.app_configs.clear()
                    apps.ready = apps.apps_ready = apps.models_ready = apps.loading = False
                    apps.populate(BASE_SETTINGS["INSTALLED_APPS"])
        for entry in meta["files"]:
            rel = entry["path"]
            if rel == settings_file:
                continue
            if rel.endswith(".py"):
                run_python(rec, case_dir, rel, entry.get("module") or Path(rel).stem)
            elif rel.endswith((".html", ".txt")):
                run_template(rec, case_dir, rel)
    except Exception as exc:  # noqa: BLE001
        result["setup_error"] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"[:2000]
    result["events"] = rec.events
    result["executed"] = {k: sorted(v) for k, v in rec.executed.items()}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
