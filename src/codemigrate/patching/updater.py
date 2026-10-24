"""Whole-file updates built from verified findings.

1. Every safe mechanical patch (see ``fixer``) is applied, one after another.
2. Optionally an LLM rewrites the lines that are still flagged; the caller accepts that rewrite
   only after re-checking it (see ``Pipeline.update_files``).
3. Whatever is left gets a ``# TODO(codemigrate): ...`` comment above the line. Comments are
   only inserted where they leave the syntax tree unchanged (never inside a string).
"""

from __future__ import annotations

import ast
import difflib
import json
import logging
import re

from codemigrate.llm.base import LLMClient, parse_json_object
from codemigrate.patching.fixer import apply_patch_text
from codemigrate.schemas import ValidatedFinding

log = logging.getLogger(__name__)

REWRITE_SYSTEM = """You update Python code for a Django upgrade.
Rules:
1. Fix ONLY the listed problems, using the fix described for each one.
2. Keep every other line exactly as it is (formatting, comments, names, order).
3. Add or change imports only when a fix needs them, and remove imports your fixes leave unused.
Return JSON only: {"updated_source": "<the complete updated file>"}"""

TODO_TAG = "TODO(codemigrate)"


def line_map(old: str, new: str) -> dict[int, int]:
    """Map 1-based line numbers of ``old`` to ``new`` for lines that survived unchanged."""
    sm = difflib.SequenceMatcher(a=old.splitlines(), b=new.splitlines(), autojunk=False)
    out: dict[int, int] = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out.update({i1 + k + 1: j1 + k + 1 for k in range(i2 - i1)})
        elif tag == "replace" and i2 - i1 == j2 - j1:  # same-size edit: lines correspond
            out.update({i1 + k + 1: j1 + k + 1 for k in range(i2 - i1)})
    return out


def apply_safe_patches(
    source: str, findings: list[ValidatedFinding]
) -> tuple[str, list[ValidatedFinding], list[ValidatedFinding]]:
    """Apply every mechanical fix. Returns (new_source, fixed, remaining) with original lines."""
    current = source
    pos = {id(f): f.line for f in findings}  # current line of each finding
    fixed, remaining = [], []
    for f in sorted(findings, key=lambda x: -x.line):
        line = pos.get(id(f))
        patched = (
            apply_patch_text(current, f.model_copy(update={"line": line})) if line else None
        )
        if patched is None:
            remaining.append(f)
            continue
        mapping = line_map(current, patched)
        for other in findings:
            if pos.get(id(other)) is not None:
                pos[id(other)] = mapping.get(pos[id(other)])
        current = patched
        fixed.append(f)
    remaining.sort(key=lambda x: x.line)
    return current, fixed, remaining


def rewrite_with_llm(
    client: LLMClient,
    path: str,
    source: str,
    findings: list[ValidatedFinding],
    from_version: str,
    to_version: str,
) -> str | None:
    """Ask the LLM for the whole file with ``findings`` fixed. None if the answer is unusable."""
    problems = [
        {
            "line": f.line,
            "symbol": f.symbol,
            "problem": f.explanation,
            "fix": f.suggested_fix
            or next((e.replacement for e in f.evidence if e.replacement), ""),
        }
        for f in findings
    ]
    numbered = "\n".join(f"{i:>4}| {s}" for i, s in enumerate(source.splitlines(), 1))
    prompt = (
        f"Upgrade: Django {from_version} -> {to_version}\nFile: {path}\n\n"
        f"Problems to fix (line numbers refer to the source below):\n"
        f"{json.dumps(problems, indent=1)}\n\n"
        f"Source (line numbers are not part of the code):\n{numbered}\n"
    )
    try:
        resp = client.complete(REWRITE_SYSTEM, prompt, temperature=0.0, seed=0)
        updated = parse_json_object(resp.text).get("updated_source")
    except Exception as exc:  # noqa: BLE001 - a failed rewrite only means no LLM fixes
        log.warning("LLM rewrite of %s failed: %s", path, exc)
        return None
    if not isinstance(updated, str) or not updated.strip():
        return None
    if source.endswith("\n") and not updated.endswith("\n"):
        updated += "\n"
    return updated


def add_todo_comments(source: str, notes: dict[int, str]) -> tuple[str, list[int]]:
    """Insert a TODO comment above each line in ``notes``; returns (source, lines commented)."""
    lines = source.splitlines(keepends=True)
    try:
        tree = ast.dump(ast.parse(source))
    except SyntaxError:
        return source, []
    done = []
    for line in sorted(notes, reverse=True):
        if not 1 <= line <= len(lines):
            continue
        target = lines[line - 1]
        indent = re.match(r"\s*", target).group(0)
        comment = f"{indent}# {TODO_TAG}: {notes[line]}\n"
        trial = lines[: line - 1] + [comment] + lines[line - 1 :]
        try:
            if ast.dump(ast.parse("".join(trial))) != tree:  # e.g. the line is inside a string
                continue
        except SyntaxError:
            continue
        lines = trial
        done.append(line)
    return "".join(lines), sorted(done)


def todo_text(f: ValidatedFinding) -> str:
    """Short note, e.g. ``is_iterable: deprecated in Django 5.1. Use isinstance(...) instead.``"""
    name = f.symbol.rsplit(".", 1)[-1]
    entry = f.evidence[0] if f.evidence else None
    kind = f.change_type or (entry.change_type.value if entry else "changed")
    head = f"{name}: {kind}" + (f" in Django {entry.version_introduced}" if entry else "")
    fix = f.suggested_fix or (f"use {entry.replacement}" if entry and entry.replacement else "")
    sentences = re.split(r"(?<=\.)\s+", f.explanation.strip())
    if not fix:  # release notes often say what to do in their last sentence
        fix = next((s for s in reversed(sentences) if re.match(r"(?i)use |pass |set ", s)), "")
    # without a fix, the note's own wording is more precise (e.g. "calling X without args")
    text = f"{head}. {fix}" if fix else f"{name}: {sentences[0]}"
    text = text.strip().rstrip(".") + "."
    return text if len(text) <= 130 else text[:127] + "..."
