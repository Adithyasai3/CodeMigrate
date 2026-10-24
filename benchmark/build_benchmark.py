"""Build benchmark cases (inputs only; labels come from label_by_execution.py).

Case kinds:
  synthetic  - one KB entry's API injected into small realistic code (auto-generated from KB
               names + hand-written snippets in synthetic_snippets.yaml), plus "mixed" files
               combining several injected usages with clean code
  negative   - clean code and near-misses (negative_snippets.yaml)
  real       - files from Django-4.0-era open-source packages (real_sources.yaml), selected by
               a plain-text grep for KB names (NOT by the analyzer under test) plus randomly
               sampled other modules of the same packages

Splits: dev (30%) / test (70%), assigned by hashing a group key with the seed, so variants of
the same API (or files of the same package) never straddle dev and test.

Usage: python -m benchmark.build_benchmark [--seed 42]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import random
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import yaml

from codemigrate.config import get_settings
from codemigrate.kb.build_kb import WHEEL_DIR
from codemigrate.kb.schema import KBEntry, load_kb
from codemigrate.kb.symbol_index import build_index
from codemigrate.kb.usage import usage_for
from codemigrate.kb.versions import in_range

log = logging.getLogger("build_benchmark")
ROOT = Path(__file__).resolve().parent
CASES = ROOT / "cases"
WORK = ROOT / "_work"
FROM_V, TO_V = "4.0", "5.1"
DEV_FRACTION = 0.3

MODEL_SCAFFOLD = '''from django.db import connection, models


class Tag(models.Model):
    name = models.CharField(max_length=20)

    class Meta:
        app_label = "sessions"


class Note(models.Model):
    text = models.CharField(max_length=20)
    created = models.DateTimeField(auto_now_add=True)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, null=True)

    class Meta:
        app_label = "sessions"


with connection.schema_editor() as editor:
    editor.create_model(Tag)
    editor.create_model(Note)

tag = Tag.objects.create(name="t")
'''

CLEAN_PREAMBLE = [
    "from django.utils import timezone\n\nSTARTED = timezone.now()\n",
    "from django.utils.text import slugify\n\nSLUG = slugify('Upgrade Check')\n",
    "from django.db.models import Q\n\nACTIVE = Q(is_active=True)\n",
    "import logging\n\nlogger = logging.getLogger(__name__)\n",
]
SETTING_VALUES = {
    "DEFAULT_FILE_STORAGE": '"django.core.files.storage.FileSystemStorage"',
    "STATICFILES_STORAGE": '"django.contrib.staticfiles.storage.StaticFilesStorage"',
    "CSRF_COOKIE_MASKED": "False",
    "FORMS_URLFIELD_ASSUME_HTTPS": "True",
}
SETTINGS_TEMPLATE = '''SECRET_KEY = "benchmark"
USE_TZ = True
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
]
DATABASES = {{"default": {{"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}}}
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
{body}'''


def split_for(group: str, seed: int) -> str:
    h = int(hashlib.sha256(f"{seed}:{group}".encode()).hexdigest(), 16)
    return "dev" if (h % 1000) / 1000 < DEV_FRACTION else "test"


def write_case(case_id: str, kind: str, files: dict[str, str], meta: dict, group: str,
               seed: int) -> None:
    base, n = case_id, 2
    while (CASES / case_id).exists():
        case_id = f"{base}-{n}"
        n += 1
    d = CASES / case_id
    d.mkdir(parents=True)
    entries = []
    for rel, text in files.items():
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / rel).write_text(text, encoding="utf-8", newline="\n")
        entries.append({"path": rel, "module": meta.get("modules", {}).get(rel)})
    case = {"case_id": case_id, "kind": kind, "split": split_for(group, seed), "group": group,
            "files": entries, **{k: v for k, v in meta.items() if k != "modules"}}
    (d / "case.json").write_text(json.dumps(case, indent=1), encoding="utf-8", newline="\n")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


# ----------------------------------------------------------------------------- synthetic

def in_scope(e: KBEntry) -> bool:
    return in_range(e.version_introduced, FROM_V, TO_V) and e.change_type.value != (
        "behavior_changed")


def build_synthetic_auto(kb: list[KBEntry], seed: int) -> int:
    index = build_index(WHEEL_DIR)
    rng = random.Random(seed)
    n = 0
    seen_code: set[str] = set()
    for e in sorted(kb, key=lambda e: e.id):
        if not in_scope(e):
            continue
        for variant in (0, 1):
            u = usage_for(e, index, variant)
            if u is None or u.code in seen_code:
                continue
            seen_code.add(u.code)
            case_id = f"syn-auto-{slug(e.affected_api)}-v{variant}"
            meta = {"origin": {"generator": "kb.usage.usage_for", "variant": variant},
                    "intended": [e.id]}
            if u.style == "setting":
                name = e.affected_api.split(".", 1)[1]
                value = SETTING_VALUES.get(name, "True")
                files = {"settings.py": SETTINGS_TEMPLATE.format(body=f"{name} = {value}\n")}
                meta["settings_file"] = "settings.py"
            elif u.style == "template":
                files = {u.filename: u.code}
            elif u.style == "module_var":
                files = {"caseapp/__init__.py": u.code}
                meta["modules"] = {"caseapp/__init__.py": "caseapp"}
            else:
                pre = rng.choice(CLEAN_PREAMBLE)
                files = {"case.py": pre + "\n" + u.code}
                meta["modules"] = {"case.py": "case"}
            write_case(case_id, "synthetic", files, meta, group=e.affected_api, seed=seed)
            n += 1
    return n


def build_synthetic_manual(seed: int) -> int:
    snippets = yaml.safe_load((ROOT / "synthetic_snippets.yaml").read_text(encoding="utf-8"))
    for s in snippets:
        code = (MODEL_SCAFFOLD + "\n" + s["code"]) if s.get("uses_models") else s["code"]
        write_case(f"syn-manual-{slug(s['name'])}", "synthetic", {"case.py": code},
                   {"origin": {"generator": "synthetic_snippets.yaml", "name": s["name"]},
                    "intended": s.get("intended", []), "modules": {"case.py": "case"}},
                   group=f"manual:{s['name']}", seed=seed)
    return len(snippets)


def build_mixed(seed: int, count: int = 20) -> int:
    """Files combining 3 hand-written usages (imports hoisted) with clean code."""
    snippets = [s for s in yaml.safe_load((ROOT / "synthetic_snippets.yaml").read_text(
        encoding="utf-8")) if not s.get("uses_models")]
    rng = random.Random(seed + 1)
    for i in range(count):
        picks = rng.sample(snippets, 3)
        imports, bodies = [], []
        for s in picks:
            for line in s["code"].splitlines():
                (imports if re.match(r"^(from|import)\s", line) else bodies).append(line)
            bodies.append("")
        code_lines = list(dict.fromkeys(imports)) + ["", ""] + [
            rng.choice(CLEAN_PREAMBLE).strip()] + [""] + bodies
        code = "\n".join(code_lines).rstrip() + "\n"
        if any(line.startswith(" ") and "(" not in line for line in imports):
            continue
        group = "mixed:" + "+".join(sorted(s["name"] for s in picks))
        write_case(f"syn-mixed-{i:02d}", "synthetic", {"case.py": code},
                   {"origin": {"generator": "mixed", "parts": [s["name"] for s in picks]},
                    "intended": [x for s in picks for x in s.get("intended", [])],
                    "modules": {"case.py": "case"}}, group=group, seed=seed)
    return count


# ----------------------------------------------------------------------------- negatives

def build_negatives(seed: int) -> int:
    snippets = yaml.safe_load((ROOT / "negative_snippets.yaml").read_text(encoding="utf-8"))
    for s in snippets:
        meta = {"origin": {"generator": "negative_snippets.yaml", "name": s["name"],
                           "negative_kind": s["kind"]}, "intended": []}
        if s.get("settings"):
            files = {"settings.py": s["code"]}
            meta["settings_file"] = "settings.py"
        elif s.get("template"):
            files = {"templates/case.html": s["code"]}
        else:
            code = (MODEL_SCAFFOLD + "\n" + s["code"]) if s.get("uses_models") else s["code"]
            files = {"case.py": code}
            meta["modules"] = {"case.py": "case"}
        write_case(f"neg-{slug(s['name'])}", "negative", files, meta, group=f"neg:{s['name']}",
                   seed=seed)
    return len(snippets)


# ----------------------------------------------------------------------------- real code

def _extract(sdist: Path, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    if sdist.suffix == ".zip":
        with zipfile.ZipFile(sdist) as zf:
            zf.extractall(dest)
    else:
        with tarfile.open(sdist) as tf:
            tf.extractall(dest, filter="data")
    return next(p for p in dest.iterdir() if p.is_dir())


def _license(root: Path) -> str:
    pkg_info = root / "PKG-INFO"
    if pkg_info.exists():
        text = pkg_info.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^License: (.+)$", text, re.M)
        classifiers = re.findall(r"^Classifier: License :: (.+)$", text, re.M)
        parts = ([m.group(1).strip()] if m and m.group(1).strip() not in {"UNKNOWN", ""}
                 else []) + classifiers
        return "; ".join(parts) or "see LICENSE file"
    return "see LICENSE file"


def kb_grep_regex(kb: list[KBEntry]) -> re.Pattern:
    """Plain-text pattern of distinctive in-scope KB names (independent of the analyzer)."""
    names = set()
    for e in kb:
        if not in_scope(e):
            continue
        for n in e.all_names():
            last = n.split(".")[-1].split(":")[-1]
            if len(last) >= 6 and last not in {"datetimes", "iterator", "location"}:
                names.add(last)
    return re.compile(r"\b(" + "|".join(sorted(map(re.escape, names))) + r")\b")


def build_real(kb: list[KBEntry], seed: int) -> tuple[int, list[dict]]:
    spec = yaml.safe_load((ROOT / "real_sources.yaml").read_text(encoding="utf-8"))
    pattern = kb_grep_regex(kb)
    rng = random.Random(seed + 2)
    dl = WORK / "sdists"
    dl.mkdir(parents=True, exist_ok=True)
    count, provenance = 0, []
    for pkg in spec["packages"]:
        req = f"{pkg['name']}=={pkg['version']}"
        found = [p for p in dl.iterdir() if p.name.lower().replace("_", "-").startswith(
            f"{pkg['name'].lower()}-{pkg['version']}")]
        if not found:
            subprocess.run([sys.executable, "-m", "pip", "download", "-q", "--no-deps",
                            "--no-binary=:all:", req, "-d", str(dl)], check=True)
            found = [p for p in dl.iterdir() if p.name.lower().replace("_", "-").startswith(
                f"{pkg['name'].lower()}-{pkg['version']}")]
        sdist = found[0]
        root = _extract(sdist, WORK / "src_extract" / sdist.stem)
        lic = _license(root)
        pkg_root = root / pkg["package_dir"]
        candidates = sorted(
            p for p in pkg_root.rglob("*.py")
            if not re.search(r"(/|^)(tests?|migrations|docs)(/|$)|test_|conftest",
                             p.relative_to(root).as_posix())
        )
        hits = [p for p in candidates if pattern.search(p.read_text(encoding="utf-8",
                                                                    errors="replace"))]
        others = [p for p in candidates if p not in hits and p.stat().st_size > 300]
        sampled = rng.sample(others, min(pkg.get("random_files", 3), len(others)))
        for p in hits + sampled:
            rel_in_root = p.relative_to(root / pkg.get("import_root", "")).as_posix()
            module = rel_in_root[:-3].replace("/", ".").removesuffix(".__init__")
            case_id = f"real-{slug(pkg['name'])}-{slug(rel_in_root[:-3])}"
            meta = {
                "origin": {"package": pkg["name"], "version": pkg["version"],
                           "repository": pkg["repository"], "license": lic,
                           "sdist": sdist.name,
                           "sdist_sha256": hashlib.sha256(sdist.read_bytes()).hexdigest(),
                           "path": p.relative_to(root).as_posix(),
                           "selected_by": "kb_name_grep" if p in hits else "random_sample"},
                "intended": [],
                "installed_apps": pkg.get("installed_apps", []),
                "add_case_dir_to_path": False,
                "modules": {rel_in_root: module},
            }
            write_case(case_id, "real", {rel_in_root: p.read_text(encoding="utf-8")}, meta,
                       group=f"real:{pkg['name']}", seed=seed)
            provenance.append({"case_id": case_id, **meta["origin"]})
            count += 1
    return count, provenance


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=get_settings().seed)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    if CASES.exists():
        shutil.rmtree(CASES)
    kb = load_kb(get_settings().kb_path)
    counts = {
        "synthetic_auto": build_synthetic_auto(kb, args.seed),
        "synthetic_manual": build_synthetic_manual(args.seed),
        "synthetic_mixed": build_mixed(args.seed),
        "negative": build_negatives(args.seed),
    }
    counts["real"], provenance = build_real(kb, args.seed)
    (ROOT / "real_provenance.json").write_text(json.dumps(provenance, indent=1),
                                              encoding="utf-8", newline="\n")
    print(json.dumps(counts, indent=1), f"total={sum(counts.values())}")


if __name__ == "__main__":
    main()
