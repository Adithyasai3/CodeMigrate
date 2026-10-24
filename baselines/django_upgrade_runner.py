"""System A: rule-based rewriters run as-is (django-upgrade, and pyupgrade for reference).

Neither tool reports findings; it rewrites files. Findings are derived from the rewrite: every
original line that is replaced or deleted becomes one finding (pure insertions, e.g. an added
import, are not findings). The finding's "symbol" is the original line text, so matching falls
back to file + line (+ identifier present in the line). This mapping is a threat to validity.
"""

from __future__ import annotations

import difflib
import logging
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

log = logging.getLogger(__name__)

TOOLS = {
    "django-upgrade": lambda target: [sys.executable, "-m", "django_upgrade",
                                      "--target-version", target],
    "pyupgrade": lambda target: [sys.executable, "-m", "pyupgrade", "--py310-plus"],
}


def changed_lines(before: str, after: str) -> list[int]:
    a, b = before.splitlines(), after.splitlines()
    lines: list[int] = []
    for tag, i1, i2, _j1, _j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag in ("replace", "delete"):
            lines.extend(range(i1 + 1, i2 + 1))
    return lines


def run_tool(tool: str, files: dict[str, str], to_version: str) -> tuple[list[dict], float]:
    """Run ``tool`` on copies of ``files`` ({relpath: text}); return (findings, seconds)."""
    findings: list[dict] = []
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        py_paths = []
        for rel, text in files.items():
            if not rel.endswith(".py"):
                continue
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8", newline="\n")
            py_paths.append((rel, p))
        if not py_paths:
            return [], 0.0
        cmd = TOOLS[tool](to_version) + [str(p) for _, p in py_paths]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode not in (0, 1):
            log.error("%s failed (%d): %s", tool, r.returncode, r.stderr[-500:])
        for rel, p in py_paths:
            after = p.read_text(encoding="utf-8")
            before = files[rel]
            for line in changed_lines(before, after):
                findings.append({"file": rel, "line": line,
                                 "symbol": before.splitlines()[line - 1].strip(),
                                 "cited_ids": [], "status": "REWRITE"})
        shutil.rmtree(root, ignore_errors=True)
    return findings, time.perf_counter() - t0
