"""Ground-truth labels by execution (not by CodeMigrate).

1. Runs every case under Django 4.0.10, 4.1.13, 4.2.30, 5.0.14 and 5.1.15 (Python 3.10) in the
   labeling Docker image (benchmark/harness/Dockerfile) -> benchmark/_work/runs/<ver>/<case>.json
2. Converts raw runs into labels -> benchmark/labels/<case>.json (+ labels/summary.json)

Labeling rules (upgrade 4.0 -> 5.1):
  * positive line = a statement that raises under some target version (4.1..5.1) but not under
    4.0, OR emits a Django removal warning (RemovedInDjangoXYWarning, X.Y > 4.0) under any
    version 4.0..5.1. The line is the deepest case-file frame (or the warning location; or, for
    settings/templates, the line naming the setting/filter mentioned in the message).
  * ignored lines (neither positive nor negative): lines failing under 4.0 (invalid source
    code for the source version), NameError cascades from a failed import, and transitive
    failures raised inside another third-party module.
  * scored lines = lines executed under 4.0 plus labeled lines. Findings on never-executed
    lines are not scored (no ground truth).
  * case status: ok | ambiguous (a Django warning/error could not be attributed to a line) |
    silent_injection (synthetic case whose injected API produced nothing) | invalid_source
    (case cannot even be set up under 4.0).

Usage: python -m benchmark.label_by_execution [--backend docker|local] [--jobs 8] [--force]
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES = ROOT / "cases"
LABELS = ROOT / "labels"
RUNS = ROOT / "_work" / "runs"
HARNESS = ROOT / "harness"
IMAGE = "codemigrate-labeler:1"
FROM = "4.0.10"
TARGETS = ["4.1.13", "4.2.30", "5.0.14", "5.1.15"]
ALL = [FROM, *TARGETS]
log = logging.getLogger("label_by_execution")


# ----------------------------------------------------------------------------- running

def run_docker(jobs: int, force: bool) -> None:
    subprocess.run(["docker", "build", "-t", IMAGE, str(HARNESS)], check=True)
    RUNS.mkdir(parents=True, exist_ok=True)
    cmd = ["docker", "run", "--rm", "--network", "none",
           "-v", f"{CASES.resolve()}:/cases:ro", "-v", f"{RUNS.resolve()}:/runs",
           IMAGE, "python", "/harness/run_all.py", "--cases", "/cases", "--out", "/runs",
           "--venvs", "/venvs", "--jobs", str(jobs)] + (["--force"] if force else [])
    subprocess.run(cmd, check=True)


def run_local(jobs: int, force: bool, venvs: Path) -> None:
    cmd = [sys.executable, str(HARNESS / "run_all.py"), "--cases", str(CASES), "--out",
           str(RUNS), "--venvs", str(venvs), "--jobs", str(jobs)] + (["--force"] if force else [])
    subprocess.run(cmd, check=True)


# ----------------------------------------------------------------------------- labeling

SYMBOL_PATTERNS = [
    (re.compile(r"cannot import name '(\w+)' from '([\w.]+)'"), lambda m: f"{m[2]}.{m[1]}"),
    (re.compile(r"No module named '([\w.]+)'"), lambda m: m[1]),
    (re.compile(r"module '([\w.]+)' has no attribute '(\w+)'"), lambda m: f"{m[1]}.{m[2]}"),
    (re.compile(r"type object '(\w+)' has no attribute '(\w+)'"), lambda m: f"{m[1]}.{m[2]}"),
    (re.compile(r"'(\w+)' object has no attribute '(\w+)'"), lambda m: f"{m[1]}.{m[2]}"),
    (re.compile(r"(\w+)(?:\.__init__)?\(\) got an unexpected keyword argument '(\w+)'"),
     lambda m: f"{m[1]}"),
    (re.compile(r"'class Meta' got invalid attribute\(s\): (\w+)"), lambda m: f"Meta.{m[1]}"),
    (re.compile(r"Invalid filter: '(\w+)'"), lambda m: f"template:{m[1]}"),
]
WARNING_VERSION_RE = re.compile(r"RemovedInDjango(\d)(\d+)Warning")


def symbol_from_message(message: str) -> str | None:
    for rx, fn in SYMBOL_PATTERNS:
        m = rx.search(message)
        if m:
            return fn(m)
    return None


def relevant_warning(ev: dict) -> bool:
    if not ev.get("django"):
        return False
    m = WARNING_VERSION_RE.match(ev["type"])
    if not m:
        return ev["type"] == "RemovedAfterNextVersionWarning"
    return (int(m[1]), int(m[2])) > (4, 0)


def load_runs(case_id: str) -> dict[str, dict]:
    out = {}
    for v in ALL:
        p = RUNS / v / f"{case_id}.json"
        if p.exists():
            out[v] = json.loads(p.read_text(encoding="utf-8"))
    return out


def label_case(case: dict, runs: dict[str, dict], kb_names: dict[str, str]) -> dict:
    case_id = case["case_id"]
    result = {"case_id": case_id, "kind": case["kind"], "split": case["split"],
              "group": case["group"], "labels": [], "ignored_lines": [], "scored_lines": {},
              "status": "ok", "notes": [], "provenance": {
                  "method": "execution", "versions": ALL, "python": None,
                  "runner": "benchmark/harness/driver.py"}}
    if FROM not in runs or any(v not in runs for v in TARGETS):
        result["status"] = "missing_runs"
        return result
    src = runs[FROM]
    result["provenance"]["python"] = src.get("python")
    if src.get("setup_error") and not src.get("events") and not src.get("executed"):
        result["status"] = "invalid_source"
        result["notes"].append(f"4.0 setup failed: {src['setup_error'][:300]}")
        return result
    if src.get("setup_error"):
        result["notes"].append(f"4.0 setup fallback: {src['setup_error'][:200]}")

    ignored: dict[tuple[str, int], str] = {}
    for ev in src["events"]:
        if ev["kind"] == "error" and ev.get("line"):
            ignored[(ev["file"], ev["line"])] = (
                f"fails under 4.0: {ev['type']}: {ev['message'][:120]}"
            )
    labels: dict[tuple[str, int], dict] = {}
    unattributed = []
    for v in ALL:
        for ev in runs[v]["events"]:
            is_error = ev["kind"] == "error" and v != FROM
            is_warning = ev["kind"] == "warning" and relevant_warning(ev)
            if not (is_error or is_warning):
                continue
            if ev.get("line") is None:
                unattributed.append(f"{v} {ev['type']}: {ev['message'][:150]}")
                continue
            key = (ev["file"], ev["line"])
            if is_warning and ev.get("transitive"):
                ignored.setdefault(key, "transitive")
                continue
            if is_error and (ev.get("cascade") or ev.get("transitive")):
                ignored.setdefault(key, "cascade" if ev.get("cascade") else "transitive")
                continue
            if key in ignored and is_error:
                continue
            lab = labels.setdefault(key, {
                "file": ev["file"], "line": ev["line"],
                "stmt_start": ev.get("stmt_line") or ev["line"],
                "stmt_end": ev.get("stmt_end") or ev["line"],
                "symbol": None, "first_version": v, "evidence": []})
            lab["evidence"].append({"version": v, "kind": ev["kind"], "type": ev["type"],
                                    "message": ev["message"][:300],
                                    "attribution": ev.get("attribution", "traceback")})
            if lab["symbol"] is None and is_error:
                lab["symbol"] = symbol_from_message(ev["message"])
    for key, lab in labels.items():
        if key in ignored and ignored[key].startswith("fails under 4.0"):
            # warning-only label on a line that is broken under 4.0 anyway -> ignore
            continue
        _refine_line(case, lab)
        if lab["symbol"] is None:
            lab["symbol"] = _symbol_from_intended(case, lab, kb_names)
        result["labels"].append(lab)
    result["labels"].sort(key=lambda lab: (lab["file"], lab["line"]))
    labeled = {(lab["file"], lab["line"]) for lab in result["labels"]}
    result["ignored_lines"] = [{"file": f, "line": ln, "reason": r}
                               for (f, ln), r in sorted(ignored.items()) if (f, ln) not in labeled]
    scored: dict[str, set[int]] = {f: set(lines) for f, lines in src.get("executed", {}).items()}
    for lab in result["labels"]:
        scored.setdefault(lab["file"], set()).update(range(lab["stmt_start"], lab["stmt_end"] + 1))
    result["scored_lines"] = {f: sorted(s) for f, s in sorted(scored.items())}
    if unattributed:
        result["status"] = "ambiguous"
        result["notes"].extend(unattributed[:5])
    elif case["kind"] == "synthetic" and not result["labels"] and case.get("intended"):
        fails_on_source = any(x["reason"].startswith("fails under 4.0")
                              for x in result["ignored_lines"])
        result["status"] = "invalid_source" if fails_on_source else "silent_injection"
        if fails_on_source:
            result["notes"].append("injected usage already fails under 4.0 (e.g. needs GDAL/"
                                   "Oracle, or the API is newer than 4.0)")
    return result


def _refine_line(case: dict, lab: dict) -> None:
    """If the event points at the first line of a multi-line statement (e.g. ``class X:``)
    and a message names an identifier that appears on exactly one line inside the
    statement, move the label to that line (e.g. the ``index_together = ...`` line)."""
    if lab["stmt_end"] <= lab["stmt_start"] or lab["line"] != lab["stmt_start"]:
        return
    try:
        lines = (CASES / case["case_id"] / lab["file"]).read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    span = range(lab["stmt_start"], lab["stmt_end"] + 1)
    for ev in lab["evidence"]:
        for ident in re.findall(r"'([A-Za-z_]\w{3,})'|\b([a-z]+_[a-z_]+)\b", ev["message"]):
            ident = ident[0] or ident[1]
            hits = [n for n in span if re.search(rf"\b{re.escape(ident)}\b", lines[n - 1])]
            if len(hits) == 1:
                lab["line"] = hits[0]
                lab["line_refined_from"] = lab["stmt_start"]
                return


def _symbol_from_intended(case: dict, lab: dict, kb_names: dict[str, str]) -> str | None:
    src_path = CASES / case["case_id"] / lab["file"]
    try:
        lines = src_path.read_text(encoding="utf-8").splitlines()
        text = "\n".join(lines[lab["stmt_start"] - 1 : lab["stmt_end"]])
    except (OSError, IndexError):
        return None
    for kb_id in case.get("intended", []):
        api = kb_names.get(kb_id)
        if api and re.search(rf"\b{re.escape(api.split('.')[-1].split(':')[-1])}\b", text):
            return api
    return None


def build_labels() -> dict:
    sys.path.insert(0, str(ROOT.parent / "src"))
    from codemigrate.config import get_settings
    from codemigrate.kb.schema import load_kb

    kb_names = {e.id: e.affected_api for e in load_kb(get_settings().kb_path)}
    LABELS.mkdir(parents=True, exist_ok=True)
    for old in LABELS.glob("*.json"):
        old.unlink()
    summary: Counter = Counter()
    per_kind: Counter = Counter()
    for case_file in sorted(CASES.glob("*/case.json")):
        case = json.loads(case_file.read_text(encoding="utf-8"))
        lab = label_case(case, load_runs(case["case_id"]), kb_names)
        (LABELS / f"{case['case_id']}.json").write_text(json.dumps(lab, indent=1),
                                                       encoding="utf-8", newline="\n")
        summary[lab["status"]] += 1
        per_kind[(case["kind"], lab["status"])] += 1
    out = {"status": dict(summary), "by_kind": {f"{k}/{s}": n for (k, s), n in per_kind.items()}}
    (LABELS / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["docker", "local", "none"], default="docker",
                    help="'none' only recomputes labels from existing raw runs")
    ap.add_argument("--venvs", type=Path, default=ROOT / "_work" / "venvs")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    if args.backend == "docker":
        run_docker(args.jobs, args.force)
    elif args.backend == "local":
        run_local(args.jobs, args.force, args.venvs)
    print(json.dumps(build_labels(), indent=1))


if __name__ == "__main__":
    main()
