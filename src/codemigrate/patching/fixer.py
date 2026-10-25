"""Mechanical fix suggestions as unified diffs; every patch must still parse.

Supported (only for KB entries with ``mechanical_fix`` and a ``replacement``):
  * same-parent renames: ``assertFormsetError`` -> ``assertFormSetError`` on the finding line
  * cross-module moves to an importable path (``django.utils.timezone.utc`` ->
    ``datetime.timezone.utc``): import lines are rewritten and attribute uses are replaced,
    adding ``import <top-level module>`` when needed.
Anything else returns None (no patch beats a wrong patch).
"""

from __future__ import annotations

import ast
import difflib
import logging
import re

from codemigrate.kb.schema import KBEntry
from codemigrate.schemas import ValidatedFinding

log = logging.getLogger(__name__)


def _parses(source: str) -> bool:
    try:
        ast.parse(source)
        return True
    except SyntaxError:
        return False


def _ensure_import(lines: list[str], module: str) -> list[str]:
    stmt = f"import {module}\n"
    if any(line.strip() == stmt.strip() for line in lines):
        return lines
    last = -1
    for i, line in enumerate(lines):
        if re.match(r"^(import|from)\s+\S", line):
            last = i
    insert_at = last + 1 if last >= 0 else 0
    return lines[:insert_at] + [stmt] + lines[insert_at:]


def _rewrite_line(line: str, entry: KBEntry, imported: bool = False) -> list[str] | None:
    old_path, new_path = entry.affected_api, entry.replacement or ""
    old_parent, old_name = old_path.rsplit(".", 1)
    new_parent, new_name = new_path.rsplit(".", 1) if "." in new_path else ("", new_path)
    eol = "\n" if line.endswith("\n") else ""
    body = line.rstrip("\n")

    if new_parent == old_parent or not new_parent:
        if not re.search(rf"\b{re.escape(old_name)}\b", body):
            return None
        return [re.sub(rf"\b{re.escape(old_name)}\b", new_name, body) + eol]

    # Cross-module move. Import line: ``from old_parent import a, old_name as x, b``
    m = re.match(rf"^(\s*)from\s+{re.escape(old_parent)}\s+import\s+(.+)$", body)
    if m:
        indent, names = m.group(1), [n.strip() for n in m.group(2).strip("()").split(",")]
        kept, alias = [], None
        for n in names:
            parts = n.split(" as ")
            if parts[0].strip() == old_name:
                alias = parts[1].strip() if len(parts) > 1 else old_name
            elif n:
                kept.append(n)
        if alias is None:
            return None
        top = new_path.split(".")[0]
        out = []
        if kept:
            out.append(f"{indent}from {old_parent} import {', '.join(kept)}{eol or chr(10)}")
        if not imported:
            out.append(f"{indent}import {top}\n")
        out.append(f"{indent}{alias} = {new_path}{eol}")
        return out
    # Attribute use: ``<alias>.old_name`` -> new_path
    if re.search(rf"\b\w+\.{re.escape(old_name)}\b", body):
        return [re.sub(rf"\b[\w.]+\.{re.escape(old_name)}\b", new_path, body) + eol]
    return None


def _patched(source: str, finding: ValidatedFinding) -> tuple[list[str], list[str]] | None:
    """Return (original_lines, patched_lines) or None if no safe mechanical fix exists."""
    entry = next((e for e in finding.evidence if e.mechanical_fix and e.replacement), None)
    if entry is None:
        return None
    lines = source.splitlines(keepends=True)
    idx = finding.line - 1
    if not 0 <= idx < len(lines):
        return None
    top = entry.replacement.split(".")[0]
    imported = any(line.strip() == f"import {top}" for line in lines)
    new_lines = _rewrite_line(lines[idx], entry, imported)
    if new_lines is None:
        return None
    patched = lines[:idx] + new_lines + lines[idx + 1 :]
    new_parent = entry.replacement.rsplit(".", 1)[0] if "." in entry.replacement else ""
    old_parent = entry.affected_api.rsplit(".", 1)[0]
    if new_parent and new_parent != old_parent and not lines[idx].lstrip().startswith("from "):
        patched = _ensure_import(patched, top)
    if patched == lines or not _parses("".join(patched)):
        log.info(
            "patch for %s:%d rejected (no change or does not parse)", finding.file, finding.line
        )
        return None
    return lines, patched


def make_patch(source: str, finding: ValidatedFinding, path: str) -> str | None:
    """Return a unified diff fixing ``finding`` or None if no safe mechanical fix exists."""
    result = _patched(source, finding)
    if result is None:
        return None
    lines, patched = result
    return "".join(difflib.unified_diff(lines, patched, f"a/{path}", f"b/{path}"))


def apply_patch_text(source: str, finding: ValidatedFinding) -> str | None:
    """Return the patched source, or None if no safe mechanical fix exists."""
    result = _patched(source, finding)
    return "".join(result[1]) if result else None
