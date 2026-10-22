"""Static analysis of Python source: find references to library APIs with exact positions.

Resolves ``import a.b as c``, ``from a import b as c``, attribute chains, ``settings.X``,
dotted strings (``"django.middleware.x.Y"``), ``class Meta`` options, module variables and
method calls on unresolved receivers whose names are distinctive enough to be worth checking.
"""

from __future__ import annotations

import ast
import logging
import re

from codemigrate.schemas import CodeRef, RefKind

log = logging.getLogger(__name__)

LIBRARY_ROOTS = ("django",)
DOTTED_STRING_RE = re.compile(r"^django(\.[A-Za-z_]\w*)+$")
SETTINGS_PATHS = {"django.conf.settings"}
# Method names too common to flag on unknown receivers (would match unrelated objects).
GENERIC_METHODS = {
    "save",
    "create",
    "delete",
    "get",
    "open",
    "close",
    "render",
    "copy",
    "update",
    "asc",
    "desc",
    "iterator",
    "attach",
    "location",
    "items",
    "keys",
    "values",
    "append",
    "add",
    "filter",
    "all",
    "first",
    "last",
    "count",
    "exists",
    "run",
    "start",
    "stop",
    "write",
    "read",
    "format",
    "join",
    "split",
    "strip",
    "lower",
    "upper",
    "replace",
    "encode",
    "decode",
    "send",
    "clean",
    "full_clean",
    "validate",
    "setUp",
    "tearDown",
    "user",
    "find",
    "datetimes",
    "acreate",
    "asave",
    "chunk_size",
    "coords",
    "message",
    "name",
    "path",
}
TEMPLATE_FILTER_RE = re.compile(r"\|\s*([A-Za-z_]\w*)")
TEMPLATE_TAG_RE = re.compile(r"{%\s*([A-Za-z_]\w*)")


class _Visitor(ast.NodeVisitor):
    def __init__(
        self, path: str, lines: list[str], method_names: set[str], member_names: set[str]
    ) -> None:
        self.path = path
        self.lines = lines
        self.method_names = method_names  # distinctive: flagged even on unknown receivers
        self.member_names = member_names  # all KB member names: flagged on known receivers
        self._class_bases: list[str | None] = []
        self.bindings: dict[str, str] = {}
        self.refs: list[CodeRef] = []
        self._consumed: set[int] = set()  # ids of Attribute nodes already part of a longer chain
        self._class_stack: list[str] = []
        self._depth = 0
        self.is_settings_module = False

    # -- helpers ---------------------------------------------------------------------------
    def _ctx(self, line: int) -> str:
        lo, hi = max(0, line - 3), min(len(self.lines), line + 2)
        return "\n".join(self.lines[lo:hi])

    def _add(self, node: ast.AST, symbol: str, kind: RefKind, **extra) -> None:
        line = getattr(node, "lineno", 1)
        raw = self.lines[line - 1].strip() if 0 < line <= len(self.lines) else ""
        self.refs.append(
            CodeRef(
                file=self.path,
                line=line,
                col=getattr(node, "col_offset", 0),
                end_col=getattr(node, "end_col_offset", None),
                symbol=symbol,
                raw_text=raw,
                kind=kind,
                context=self._ctx(line),
                **extra,
            )
        )

    @staticmethod
    def _is_library(path: str) -> bool:
        return path.split(".")[0] in LIBRARY_ROOTS

    def _chain(self, node: ast.AST) -> list[str] | None:
        parts: list[str] = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
            return list(reversed(parts))
        return None

    # -- imports ---------------------------------------------------------------------------
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.asname:
                self.bindings[alias.asname] = alias.name
            else:
                root = alias.name.split(".")[0]
                self.bindings[root] = root
            if self._is_library(alias.name):
                self._add(node, alias.name, RefKind.IMPORT)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level or not node.module:
            return
        for alias in node.names:
            if alias.name == "*":
                continue
            full = f"{node.module}.{alias.name}"
            self.bindings[alias.asname or alias.name] = full
            if self._is_library(node.module):
                self._add(node, full, RefKind.IMPORT)

    # -- expressions -----------------------------------------------------------------------
    def visit_Call(self, node: ast.Call) -> None:
        target = node.func
        chain = self._chain(target)
        if chain:
            resolved = self._resolve(chain)
            kwargs = [k.arg for k in node.keywords if k.arg]
            if resolved and self._is_library(resolved):
                self._add(
                    node, resolved, RefKind.CALL, call_args=len(node.args), call_kwargs=kwargs
                )
                self._mark_chain(target)
            elif isinstance(target, ast.Attribute) and target.attr in self.method_names:
                self._add(
                    target,
                    f"*.{target.attr}",
                    RefKind.METHOD,
                    call_args=len(node.args),
                    call_kwargs=kwargs,
                )
                self._mark_chain(target)
        self.generic_visit(node)

    def _mark_chain(self, node: ast.AST) -> None:
        while isinstance(node, ast.Attribute):
            self._consumed.add(id(node))
            node = node.value
        self._consumed.add(id(node))

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if id(node) not in self._consumed:
            chain = self._chain(node)
            if chain:
                resolved = self._resolve(chain)
                if resolved and resolved.startswith("settings."):
                    self._add(node, resolved, RefKind.SETTING)
                elif resolved and self._is_library(resolved):
                    self._add(node, resolved, RefKind.ATTRIBUTE)
                elif node.attr in self.method_names and resolved is None:
                    self._add(node, f"*.{node.attr}", RefKind.METHOD)
                self._mark_chain(node)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        # Bare use of an imported library name (e.g. ``utc`` after ``from ... import utc``).
        if id(node) in self._consumed:
            return
        if isinstance(node.ctx, ast.Load) and node.id in self.bindings:
            full = self.bindings[node.id]
            if self._is_library(full) and full.count(".") >= 2:
                self._add(node, full, RefKind.ATTRIBUTE)

    def _resolve(self, chain: list[str]) -> str | None:
        head = chain[0]
        if head in {"self", "cls"} and len(chain) >= 2:
            # self.member inside a subclass of a library class -> Base.member
            base = self._class_bases[-1] if self._class_bases else None
            if base and chain[1] in self.member_names:
                return f"{base}.{chain[1]}"
            return None
        if head not in self.bindings:
            return None
        full = ".".join([self.bindings[head], *chain[1:]])
        for sp in SETTINGS_PATHS:
            if full.startswith(sp + "."):
                return "settings." + full[len(sp) + 1 :]
        return full

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str) and DOTTED_STRING_RE.match(node.value):
            self._add(node, node.value, RefKind.STRING)

    # -- definitions -----------------------------------------------------------------------
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._class_stack.append(node.name)
        base = None
        for b in node.bases:
            chain = self._chain(b)
            resolved = self._resolve(chain) if chain else None
            if resolved and self._is_library(resolved):
                base = resolved
                break
        self._class_bases.append(base)
        if node.name == "Meta":
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for t in stmt.targets:
                        if isinstance(t, ast.Name):
                            self._add(stmt, f"Meta.{t.id}", RefKind.META)
        self.generic_visit(node)
        self._class_stack.pop()
        self._class_bases.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Overriding a method that changed signature/was renamed (e.g. get_next_page).
        base = self._class_bases[-1] if self._class_bases else None
        if base and node.name in self.member_names:
            self._add(node, f"{base}.{node.name}", RefKind.METHOD)
        elif self._class_stack and node.name in self.method_names:
            self._add(node, f"*.{node.name}", RefKind.METHOD)
        self._depth += 1
        self._class_bases.append(base)  # ``self`` inside the method refers to the class
        self.generic_visit(node)
        self._class_bases.pop()
        self._depth -= 1

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Module(self, node: ast.Module) -> None:
        names = {
            t.id
            for s in node.body
            if isinstance(s, ast.Assign)
            for t in s.targets
            if isinstance(t, ast.Name)
        }
        self.is_settings_module = bool(
            names & {"INSTALLED_APPS", "MIDDLEWARE", "DATABASES", "ROOT_URLCONF", "SECRET_KEY"}
        )
        for stmt in node.body:
            targets = []
            if isinstance(stmt, ast.Assign):
                targets = [t for t in stmt.targets if isinstance(t, ast.Name)]
            elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                targets = [stmt.target]
            for t in targets:
                if t.id == "default_app_config":
                    self._add(stmt, "default_app_config", RefKind.MODULE_VAR)
                elif self.is_settings_module and re.fullmatch(r"[A-Z][A-Z0-9_]*", t.id):
                    self._add(stmt, f"settings.{t.id}", RefKind.SETTING)
        self.generic_visit(node)


def analyze_source(
    source: str, path: str = "<string>", method_names: set[str] | None = None
) -> list[CodeRef]:
    """Return library references in Python ``source``. Raises SyntaxError on invalid code.

    ``method_names`` are distinctive method names (from the KB) that are reported even when
    the receiver's type is unknown, e.g. ``self.assertFormsetError(...)``.
    """
    tree = ast.parse(source, filename=path)
    members = method_names or set()
    visitor = _Visitor(path, source.splitlines(), members - GENERIC_METHODS, members)
    visitor.visit(tree)
    return _dedupe(visitor.refs)


def analyze_template(source: str, path: str, template_names: set[str]) -> list[CodeRef]:
    """Find uses of known template filters/tags (``{{ x|length_is:2 }}``) in a template."""
    refs = []
    lines = source.splitlines()
    for i, line in enumerate(lines, 1):
        for rx in (TEMPLATE_FILTER_RE, TEMPLATE_TAG_RE):
            for m in rx.finditer(line):
                if m.group(1) in template_names:
                    refs.append(
                        CodeRef(
                            file=path,
                            line=i,
                            col=m.start(1),
                            symbol=f"template:{m.group(1)}",
                            raw_text=line.strip(),
                            kind=RefKind.TEMPLATE,
                            context="\n".join(lines[max(0, i - 3) : i + 2]),
                        )
                    )
    return refs


def _dedupe(refs: list[CodeRef]) -> list[CodeRef]:
    seen: set[tuple] = set()
    out = []
    for r in sorted(refs, key=lambda r: (r.line, r.col)):
        key = (r.line, r.symbol)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out
