"""Walk a directory or zip archive and analyze every Python file and template."""

from __future__ import annotations

import logging
import zipfile
from collections.abc import Iterator
from pathlib import Path, PurePosixPath

from codemigrate.analysis.ast_analyzer import analyze_source, analyze_template
from codemigrate.schemas import ScannedFile

log = logging.getLogger(__name__)

SKIP_DIRS = {
    ".venv",
    "venv",
    "env",
    ".env",
    "node_modules",
    ".git",
    "__pycache__",
    "site-packages",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "build",
    "dist",
    ".eggs",
}
MAX_BYTES = 1_000_000
TEMPLATE_SUFFIXES = {".html", ".txt", ".djhtml"}


def _skip(parts: tuple[str, ...]) -> bool:
    return any(p in SKIP_DIRS or p.endswith(".egg-info") for p in parts)


def iter_sources(root: Path) -> Iterator[tuple[str, str]]:
    """Yield (relative_posix_path, text) for .py and template files in a dir or .zip."""
    if root.is_file() and root.suffix == ".zip":
        with zipfile.ZipFile(root) as zf:
            for info in zf.infolist():
                p = PurePosixPath(info.filename)
                if info.is_dir() or _skip(p.parts) or info.file_size > MAX_BYTES:
                    continue
                if p.suffix == ".py" or p.suffix in TEMPLATE_SUFFIXES:
                    if ".." in p.parts or p.is_absolute():
                        log.warning("skipping unsafe zip member %s", info.filename)
                        continue
                    yield str(p), zf.read(info).decode("utf-8", errors="replace")
        return
    if root.is_file():
        yield root.name, root.read_text(encoding="utf-8", errors="replace")
        return
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if not path.is_file() or _skip(rel.parts):
            continue
        if path.suffix != ".py" and path.suffix not in TEMPLATE_SUFFIXES:
            continue
        if path.stat().st_size > MAX_BYTES:
            log.warning("skipping large file %s", rel)
            continue
        yield rel.as_posix(), path.read_text(encoding="utf-8", errors="replace")


def scan_sources(
    sources: Iterator[tuple[str, str]],
    method_names: set[str],
    template_names: set[str],
    keep_source: bool = True,
) -> list[ScannedFile]:
    """Analyze (path, text) pairs; syntax errors are recorded per file, never raised."""
    out = []
    for rel, text in sources:
        text = text.removeprefix("﻿")  # UTF-8 BOM (common on Windows); Python accepts it
        if rel.endswith(".py"):
            try:
                refs = analyze_source(text, rel, method_names)
                out.append(ScannedFile(path=rel, refs=refs, source=text if keep_source else None))
            except SyntaxError as exc:
                log.warning("syntax error in %s: %s", rel, exc)
                out.append(
                    ScannedFile(
                        path=rel,
                        error=f"SyntaxError: {exc.msg} (line {exc.lineno})",
                        source=text if keep_source else None,
                    )
                )
        else:
            refs = analyze_template(text, rel, template_names)
            if refs:
                out.append(ScannedFile(path=rel, refs=refs, source=text if keep_source else None))
    return out


def scan_path(root: Path, method_names: set[str], template_names: set[str]) -> list[ScannedFile]:
    """Scan a directory, a single file, or a .zip archive."""
    return scan_sources(iter_sources(root), method_names, template_names)
