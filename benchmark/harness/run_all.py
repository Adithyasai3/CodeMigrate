"""Run driver.py for every (Django version, case) pair. Runs inside the labeling container
(or locally with --venvs pointing at venvs built from the same pinned requirements).

Usage: python run_all.py --cases /cases --out /runs --venvs /venvs [--jobs 8] [--force]
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import subprocess
import sys
from pathlib import Path

VERSIONS = ["4.0.10", "4.1.13", "4.2.30", "5.0.14", "5.1.15"]
HERE = Path(__file__).resolve().parent


def venv_python(venvs: Path, version: str) -> Path:
    for rel in ("bin/python", "Scripts/python.exe"):
        p = venvs / version / rel
        if p.exists():
            return p
    raise FileNotFoundError(f"no python in {venvs / version}")


def run_one(py: Path, case_dir: Path, out: Path, timeout: int) -> str:
    env = {**os.environ, "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("DJANGO_SETTINGS_MODULE", None)
    try:
        r = subprocess.run([str(py), str(HERE / "driver.py"), str(case_dir), str(out)],
                           capture_output=True, text=True, timeout=timeout, env=env,
                           cwd=str(case_dir))
    except subprocess.TimeoutExpired:
        out.write_text(json.dumps({"case_id": case_dir.name, "setup_error": "timeout",
                                   "events": [], "executed": {}}))
        return "timeout"
    if r.returncode != 0 or not out.exists():
        out.write_text(json.dumps({"case_id": case_dir.name,
                                   "setup_error": f"driver crashed: {r.stderr[-1500:]}",
                                   "events": [], "executed": {}}))
        return "crash"
    return "ok"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--venvs", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    jobs = []
    for version in VERSIONS:
        py = venv_python(args.venvs, version)
        (args.out / version).mkdir(parents=True, exist_ok=True)
        for case_dir in sorted(p for p in args.cases.iterdir() if (p / "case.json").exists()):
            out = args.out / version / f"{case_dir.name}.json"
            if out.exists() and not args.force:
                continue
            jobs.append((py, case_dir, out))
    print(f"{len(jobs)} runs to do", flush=True)
    status: dict[str, int] = {}
    with cf.ThreadPoolExecutor(args.jobs) as pool:
        futs = [pool.submit(run_one, py, c, o, args.timeout) for py, c, o in jobs]
        for i, f in enumerate(cf.as_completed(futs), 1):
            s = f.result()
            status[s] = status.get(s, 0) + 1
            if i % 100 == 0:
                print(f"{i}/{len(jobs)} {status}", flush=True)
    print(f"done {status}", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
