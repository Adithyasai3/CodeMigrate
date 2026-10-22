"""AST index of a library's source (from wheels) used to resolve short names to dotted paths.

Release notes often say ``ModelAdmin.lookup_allowed`` or ``StringAgg``; this index maps those
to every fully qualified definition site and to public re-export paths, without importing code.
"""

from __future__ import annotations

import ast
import logging
import zipfile
from collections import defaultdict
from pathlib import Path

log = logging.getLogger(__name__)


class SymbolIndex:
    """Maps short names (``Name`` or ``Class.attr``) to fully qualified dotted paths."""

    def __init__(self) -> None:
        self.by_short: dict[str, set[str]] = defaultdict(set)
        self.qualified: set[str] = set()
        self.modules: set[str] = set()
        # public alias -> canonical definition (from ``from .x import Name`` in __init__.py)
        self.reexports: dict[str, str] = {}

    def add_definition(self, qualname: str) -> None:
        self.qualified.add(qualname)
        parts = qualname.split(".")
        self.by_short[parts[-1]].add(qualname)
        if len(parts) >= 2:
            self.by_short[".".join(parts[-2:])].add(qualname)

    def index_module(self, modname: str, source: str) -> None:
        """Record top-level defs, class attributes and package re-exports of one module."""
        self.modules.add(modname)
        self.by_short[modname.split(".")[-1]].add(modname)
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            log.warning("cannot parse %s: %s", modname, exc)
            return
        is_pkg_init = modname.endswith(".__init__")
        pkg = modname.removesuffix(".__init__")
        base = pkg if is_pkg_init else modname
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.add_definition(f"{base}.{node.name}")
            elif isinstance(node, ast.ClassDef):
                self.add_definition(f"{base}.{node.name}")
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self.add_definition(f"{base}.{node.name}.{sub.name}")
                    elif isinstance(sub, ast.Assign):
                        for t in sub.targets:
                            if isinstance(t, ast.Name):
                                self.add_definition(f"{base}.{node.name}.{t.id}")
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        self.add_definition(f"{base}.{t.id}")
            elif isinstance(node, ast.ImportFrom) and is_pkg_init:
                src_mod = _resolve_relative(pkg, node.module, node.level)
                for alias in node.names:
                    if alias.name == "*" or src_mod is None:
                        continue
                    public = f"{pkg}.{alias.asname or alias.name}"
                    self.reexports[public] = f"{src_mod}.{alias.name}"
        if is_pkg_init:
            self.modules.add(pkg)
            self.by_short[pkg.split(".")[-1]].add(pkg)

    def public_paths(self, qualname: str) -> list[str]:
        """Public re-export paths that point at ``qualname`` (shortest first)."""
        out = [pub for pub, canon in self.reexports.items() if canon == qualname]
        return sorted(out, key=len)

    def resolve(self, name: str, prefer_prefix: str = "django") -> list[str]:
        """Resolve a short or dotted name to candidate fully qualified names."""
        name = name.strip().removesuffix("()").lstrip("~.")
        if name in self.qualified or name in self.modules:
            return [name]
        if name in self.reexports:
            return [self.reexports[name]]
        cands = sorted(self.by_short.get(name, set()))
        if not cands and "." in name:
            # e.g. "django.contrib.admin.ModelAdmin.lookup_allowed" via re-exported class
            head, _, tail = name.rpartition(".")
            for h in self.resolve(head, prefer_prefix):
                if f"{h}.{tail}" in self.qualified:
                    cands.append(f"{h}.{tail}")
        cands = [c for c in cands if c.startswith(prefer_prefix)] or cands
        # Prefer non-test, non-private modules and the shortest path.
        return sorted(cands, key=lambda c: ("._" in c, ".tests" in c, len(c)))


def _resolve_relative(pkg: str, module: str | None, level: int) -> str | None:
    if level == 0:
        return module
    parts = pkg.split(".")
    if level > 1:
        parts = parts[: -(level - 1)]
    return ".".join(parts + ([module] if module else []))


def build_index(wheel_dir: Path, package: str = "django") -> SymbolIndex:
    """Index every ``.py`` file of ``package`` found in the wheels in ``wheel_dir`` (union)."""
    index = SymbolIndex()
    wheels = sorted(wheel_dir.glob("*.whl"))
    if not wheels:
        raise FileNotFoundError(f"no wheels in {wheel_dir}; run `codemigrate kb build` first")
    for whl in wheels:
        with zipfile.ZipFile(whl) as zf:
            for info in zf.infolist():
                n = info.filename
                if not n.startswith(f"{package}/") or not n.endswith(".py"):
                    continue
                if "/tests/" in n or "/migrations/" in n:
                    continue
                modname = n[:-3].replace("/", ".")
                index.index_module(modname, zf.read(info).decode("utf-8", errors="replace"))
    log.info("indexed %d qualified names from %d wheels", len(index.qualified), len(wheels))
    return index
