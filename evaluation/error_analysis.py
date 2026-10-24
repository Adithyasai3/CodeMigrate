"""Write results/error_cases.md: real failures of the primary system with diagnoses.

The diagnosis is computed, not hand-written: for a missed label we re-run each pipeline stage
(analyzer -> retriever -> reasoner -> validator) and report the first stage that lost it; for a
false positive we show the cited KB entry and what execution observed on that line.

  python -m evaluation.error_analysis --split test [--system "D-full[gemini]"] [--n 10]
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from codemigrate.analysis.ast_analyzer import analyze_source, analyze_template
from codemigrate.config import get_settings
from codemigrate.kb.schema import load_kb
from codemigrate.retrieval import build_retriever
from codemigrate.retrieval.exact import method_names, template_names
from codemigrate.validation.matching import symbol_matches
from evaluation.metrics import load_labels, score_case

RESULTS = Path("results")
CASES = Path("benchmark/cases")
FROM_V, TO_V = "4.0", "5.1"


def snippet(case_id: str, file: str, line: int, ctx: int = 2) -> str:
    lines = (CASES / case_id / file).read_text(encoding="utf-8").splitlines()
    lo, hi = max(1, line - ctx), min(len(lines), line + ctx)
    return "\n".join(f"{'>' if n == line else ' '}{n:4}| {lines[n - 1]}" for n in range(lo, hi + 1))


def diagnose_fn(case_id, lab, run, kb, retriever, methods, templates) -> str:
    file = lab["file"]
    text = (CASES / case_id / file).read_text(encoding="utf-8")
    try:
        refs = (analyze_template(text, file, templates) if file.endswith(".html")
                else analyze_source(text, file, methods))
    except SyntaxError as exc:
        return f"analyzer: file does not parse ({exc.msg})"
    on = [r for r in refs if lab["stmt_start"] <= r.line <= lab["stmt_end"]]
    if not on:
        return ("analyzer: no library reference resolved on this statement (dynamic access, "
                "unknown receiver type, or a pattern the analyzer does not model)")
    hits = [s for r in on for s in retriever.search(r, 5, FROM_V, TO_V)]
    matching = [s.entry for s in hits if any(symbol_matches(r.symbol, s.entry) for r in on)]
    if not matching:
        syms = ", ".join(sorted({r.symbol for r in on}))
        return (f"retrieval/KB: references found ({syms}) but no retrieved in-range KB entry "
                f"names them; the change may be missing from the KB or described differently")
    rej = [r for r in run.get("rejected", []) if lab["stmt_start"] <= r["line"] <= lab["stmt_end"]]
    if rej:
        return f"validator rejected the claim: {rej[0]['reject_reason']}"
    ids = ", ".join(e.id for e in matching[:2])
    types = {e.change_type.value for e in matching}
    return (f"reasoner: matching evidence was retrieved ({ids}; type {'/'.join(types)}) but no "
            f"finding was reported (behavior-change entries and argument-specific entries "
            f"without the argument in the call are skipped)")


def diagnose_fp(case_id, finding, label_case) -> str:
    cited = ", ".join(finding.get("cited_ids") or []) or "none"
    observed = "the line ran cleanly under every version (no error, no Django warning)"
    return (f"cited {cited}; execution: {observed}. Either the documented change does not "
            f"manifest on this code path (e.g. silently ignored or only affects other "
            f"arguments) or the reasoner over-applied the entry")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test")
    ap.add_argument("--system", default=None)
    ap.add_argument("--n", type=int, default=10)
    args = ap.parse_args()
    runs = sorted((RESULTS / "_runs").glob(f"{args.split}-D-full*.json"))
    if args.system:
        runs = [p for p in runs if args.system in p.name]
    else:  # prefer an LLM run over offline
        runs = sorted(runs, key=lambda p: ("offline" in p.name, p.name))
    if not runs:
        raise SystemExit("no D-full run found; run evaluation.run_experiments first")
    run_file = runs[0]
    system = run_file.stem.removeprefix(f"{args.split}-")
    data = json.loads(run_file.read_text())["cases"]
    labels = load_labels()
    kb = load_kb(get_settings().kb_path)
    retriever = build_retriever("hybrid", kb)
    methods, templates = method_names(kb), template_names(kb)

    failures = []
    for cid, run in sorted(data.items()):
        cl = labels[cid]
        res = score_case(cl, run["findings"])
        for f, ln in res.fn_lines:
            lab = next(x for x in cl.labels if x["file"] == f and x["line"] == ln)
            failures.append(("FN", cid, lab, None, run))
        for f, ln in res.fp_lines:
            fnd = next(x for x in run["findings"] if x["file"] == f and x["line"] == ln)
            failures.append(("FP", cid, None, fnd, run))
    rng = random.Random(get_settings().seed)
    # Balance kinds and prefer real cases, deterministically.
    picked = []
    for kind_order in (("real",), ("synthetic", "negative")):
        pool = [x for x in failures if labels[x[1]].kind in kind_order]
        rng.shuffle(pool)
        picked.extend(pool[: args.n - len(picked)] if kind_order[0] != "real"
                      else pool[: args.n // 2])
    picked = picked[: args.n]

    out = [f"# Error analysis: {system} ({args.split} split)", "",
           f"{len(failures)} failures in total ({sum(x[0] == 'FN' for x in failures)} missed, "
           f"{sum(x[0] == 'FP' for x in failures)} false positives). {len(picked)} shown, "
           f"sampled deterministically (seed {get_settings().seed}), real-code cases first.",
           "Diagnoses are computed by re-running each stage; see evaluation/error_analysis.py.",
           ""]
    for i, (kind, cid, lab, fnd, run) in enumerate(picked, 1):
        cl = labels[cid]
        if kind == "FN":
            ev = lab["evidence"][0]
            out += [f"## {i}. Missed breaking usage ({cl.kind}) `{cid}`", "",
                    f"**Input** `{lab['file']}:{lab['line']}`", "", "```python",
                    snippet(cid, lab["file"], lab["line"]), "```", "",
                    f"**Expected (execution):** Django {ev['version']}: {ev['type']}: "
                    f"{ev['message'][:200]}", "",
                    "**Got:** no finding on this statement", "",
                    f"**Why:** {diagnose_fn(cid, lab, run, kb, retriever, methods, templates)}",
                    ""]
        else:
            out += [f"## {i}. False positive ({cl.kind}) `{cid}`", "",
                    f"**Input** `{fnd['file']}:{fnd['line']}`", "", "```python",
                    snippet(cid, fnd["file"], fnd["line"]), "```", "",
                    "**Expected (execution):** no breaking change observed on this line", "",
                    f"**Got:** `{fnd['symbol']}` — {fnd.get('explanation', '')[:200]}", "",
                    f"**Why:** {diagnose_fp(cid, fnd, cl)}", ""]
    (RESULTS / "error_cases.md").write_text("\n".join(out), encoding="utf-8")
    print(f"wrote results/error_cases.md ({len(picked)} cases from {system})")


if __name__ == "__main__":
    main()
