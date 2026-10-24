"""Run all systems and ablations on a benchmark split and write metrics to results/.

  python -m evaluation.run_experiments --split test            # final numbers
  python -m evaluation.run_experiments --split dev             # development only

Systems: A (django-upgrade, pyupgrade), B/C/D for every LLM provider whose key is present
(>= 3 seeds each), and D/C with the deterministic offline reasoner. Ablations (retriever,
top-k, validator) use the offline reasoner, plus the first LLM provider with --llm-ablations.
Every LLM call is cached on disk, so re-running is free and deterministic.
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import time
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from baselines.django_upgrade_runner import run_tool
from baselines.systems import full_system, llm_only, rag_no_validator
from codemigrate.config import get_settings
from codemigrate.kb.schema import load_kb
from codemigrate.llm import available_providers
from codemigrate.llm.base import BudgetExceeded, global_tracker
from codemigrate.pipeline import Pipeline, SystemConfig
from evaluation.metrics import (
    CaseResult,
    aggregate,
    bootstrap_f1,
    hallucination_flags,
    load_labels,
    mcnemar,
    paired_bootstrap,
    score_case,
)

log = logging.getLogger("run_experiments")
CASES = Path("benchmark/cases")
RESULTS = Path("results")
RUNS = RESULTS / "_runs"
FROM_V, TO_V = "4.0", "5.1"


def load_case_files(case_id: str) -> dict[str, str]:
    meta = json.loads((CASES / case_id / "case.json").read_text(encoding="utf-8"))
    return {f["path"]: (CASES / case_id / f["path"]).read_text(encoding="utf-8")
            for f in meta["files"]}


def run_pipeline_system(cfg: SystemConfig, case_ids: list[str], run_name: str,
                        kb) -> dict[str, dict]:
    """Return {case_id: {"findings": [...], "rejected": [...], "latency": s, tokens...}}."""
    out_path = RUNS / f"{run_name}.json"
    pipe = Pipeline(cfg, kb=kb, rejected_log=RUNS / f"{run_name}.rejected.jsonl")
    (RUNS / f"{run_name}.rejected.jsonl").unlink(missing_ok=True)
    per_case = {}
    for cid in case_ids:
        files = load_case_files(cid)
        res = pipe.scan_sources(list(files.items()), FROM_V, TO_V)
        per_case[cid] = {
            "findings": [f.model_dump(mode="json", exclude={"evidence"}) for f in res.findings],
            "rejected": [f.model_dump(mode="json", exclude={"evidence"}) for f in res.rejected],
            "latency_s": res.latency_s, "llm_calls": res.llm_calls,
            "cached_calls": res.cached_calls, "prompt_tokens": res.prompt_tokens,
            "completion_tokens": res.completion_tokens, "cost_usd": res.cost_usd,
        }
    out_path.write_text(json.dumps({"config": asdict(cfg), "cases": per_case}), encoding="utf-8")
    return per_case


def run_rewriter(tool: str, case_ids: list[str], run_name: str) -> dict[str, dict]:
    per_case = {}
    for cid in case_ids:
        findings, secs = run_tool(tool, load_case_files(cid), TO_V)
        per_case[cid] = {"findings": findings, "rejected": [], "latency_s": secs, "llm_calls": 0,
                         "cached_calls": 0, "prompt_tokens": 0, "completion_tokens": 0,
                         "cost_usd": 0.0}
    (RUNS / f"{run_name}.json").write_text(json.dumps({"config": {"tool": tool},
                                                       "cases": per_case}), encoding="utf-8")
    return per_case


def evaluate_run(per_case: dict[str, dict], labels, kb, cites: bool | None) -> tuple[dict, list]:
    case_results: list[CaseResult] = []
    halluc = n_find = cit_ok = cit_n = 0
    for cid, data in per_case.items():
        case_results.append(score_case(labels[cid], data["findings"]))
        if cites is None:
            continue
        for f in data["findings"]:
            h, c = hallucination_flags(f, kb, FROM_V, TO_V, cites)
            n_find += 1
            halluc += int(h)
            if c is not None:
                cit_n += 1
                cit_ok += int(c)
    m = aggregate(case_results)
    lo, hi = bootstrap_f1(case_results, seed=get_settings().seed)
    n = len(per_case)
    m.update({
        "f1_ci_low": lo, "f1_ci_high": hi,
        "hallucination_rate": (halluc / n_find) if (cites is not None and n_find) else
        (0.0 if cites is not None else None),
        "citation_accuracy": (cit_ok / cit_n) if cit_n else None,
        "findings": sum(len(d["findings"]) for d in per_case.values()),
        "rejected_claims": sum(len(d["rejected"]) for d in per_case.values()),
        "latency_s_per_case": sum(d["latency_s"] for d in per_case.values()) / n,
        "llm_calls": sum(d["llm_calls"] for d in per_case.values()),
        "tokens_per_case": sum(d["prompt_tokens"] + d["completion_tokens"]
                               for d in per_case.values()) / n,
        "cost_usd_per_case": sum(d["cost_usd"] for d in per_case.values()) / n,
        "cases": n,
    })
    return m, case_results


def summarize(rows: list[dict], group_cols: list[str]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    metrics = ["precision", "recall", "f1", "f1_ci_low", "f1_ci_high", "hallucination_rate",
               "citation_accuracy", "line_exact", "latency_s_per_case", "tokens_per_case",
               "cost_usd_per_case", "findings", "rejected_claims", "tp", "fp", "fn"]
    out = []
    for keys, g in df.groupby(group_cols, sort=False, dropna=False):
        row = dict(zip(group_cols, keys if isinstance(keys, tuple) else (keys,), strict=True))
        row["runs"] = len(g)
        for m in metrics:
            vals = [v for v in g[m].tolist() if v is not None and v == v]
            row[f"{m}_mean"] = statistics.fmean(vals) if vals else None
            row[f"{m}_std"] = statistics.stdev(vals) if len(vals) > 1 else (0.0 if vals else None)
        out.append(row)
    return pd.DataFrame(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test", choices=["dev", "test"])
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--temperature", type=float, default=0.5,
                    help="LLM sampling temperature for the repeated runs")
    ap.add_argument("--providers", default="auto",
                    help="comma list or 'auto' (= every provider with a key)")
    ap.add_argument("--llm-ablations", action="store_true")
    ap.add_argument("--include-ambiguous", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    RUNS.mkdir(parents=True, exist_ok=True)
    kb = load_kb(get_settings().kb_path)
    labels = load_labels()
    ok = {"ok", "ambiguous"} if args.include_ambiguous else {"ok"}
    case_ids = sorted(c for c, cl in labels.items() if cl.split == args.split and cl.status in ok)
    providers = (available_providers() if args.providers == "auto"
                 else args.providers.split(","))
    llm_providers = [p for p in providers if p != "offline"]
    print(f"split={args.split} cases={len(case_ids)} llm_providers={llm_providers or 'none'}")
    rows, ablation_rows, case_store = [], [], {}

    def record(system, run, per_case, cites, table, extra=None):
        t0 = time.perf_counter()
        m, cr = evaluate_run(per_case, labels, kb, cites)
        row = {"system": system, "run": run, **(extra or {}), **m}
        table.append(row)
        case_store[(system, run, json.dumps(extra or {}, sort_keys=True))] = cr
        print(f"  {system:<34} run={run} P={m['precision']:.3f} R={m['recall']:.3f} "
              f"F1={m['f1']:.3f} halluc={m['hallucination_rate']} n_find={m['findings']} "
              f"({time.perf_counter() - t0:.1f}s eval)")

    # --- A: rule-based rewriters
    for tool in ("django-upgrade", "pyupgrade"):
        record(f"A-{tool}", 0, run_rewriter(tool, case_ids, f"{args.split}-A-{tool}"), None, rows)

    # --- offline reasoner (deterministic: one run)
    for name, cfg in [("D-full[offline]", full_system("offline", 0, 0.0)),
                      ("C-rag-no-validator[offline]", rag_no_validator("offline", 0, 0.0))]:
        record(name, 0, run_pipeline_system(cfg, case_ids, f"{args.split}-{name}", kb),
               "D-full" in name, rows)

    # --- LLM systems, >= 3 seeds
    for prov in llm_providers:
        for seed in range(args.seeds):
            for maker, cites in ((llm_only, False), (rag_no_validator, True), (full_system, True)):
                cfg = maker(prov, seed, args.temperature)
                try:
                    per_case = run_pipeline_system(cfg, case_ids,
                                                   f"{args.split}-{cfg.name}-s{seed}", kb)
                except BudgetExceeded as exc:
                    print(f"BUDGET: {exc}; stopping LLM runs (partial results are cached)")
                    llm_providers = []
                    break
                record(cfg.name, seed, per_case, cites, rows)

    # --- ablations
    abl_reasoners = ["offline"] + (llm_providers[:1] if args.llm_ablations else [])
    for prov in abl_reasoners:
        for retr in ("exact", "bm25", "tfidf", "dense", "hybrid_tfidf", "hybrid"):
            cfg = full_system(prov, 0, 0.0 if prov == "offline" else args.temperature, retr, 5)
            per_case = run_pipeline_system(cfg, case_ids, f"{args.split}-abl-{prov}-{retr}-k5", kb)
            record(f"D[{prov}]", 0, per_case, True, ablation_rows,
                   {"ablation": "retriever", "retriever": retr, "top_k": 5})
        for k in (1, 3, 5):
            cfg = full_system(prov, 0, 0.0 if prov == "offline" else args.temperature, "hybrid", k)
            run_name = f"{args.split}-abl-{prov}-hybrid-k{k}"
            per_case = run_pipeline_system(cfg, case_ids, run_name, kb)
            record(f"D[{prov}]", 0, per_case, True, ablation_rows,
                   {"ablation": "top_k", "retriever": "hybrid", "top_k": k})

    # --- write tables
    RESULTS.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(RESULTS / f"runs_{args.split}.csv", index=False)
    summary = summarize(rows, ["system"])
    summary.to_csv(RESULTS / f"comparison_{args.split}.csv", index=False)
    if ablation_rows:
        pd.DataFrame(ablation_rows).to_csv(RESULTS / f"ablations_{args.split}.csv", index=False)

    # --- statistics: D vs C per reasoner (paired over cases)
    stats = {}
    for prov in ["offline", *llm_providers]:
        d_key = [k for k in case_store if k[0] == f"D-full[{prov}]" and k[2] == "{}"]
        c_key = [k for k in case_store if k[0] == f"C-rag-no-validator[{prov}]" and k[2] == "{}"]
        for dk, ck in zip(sorted(d_key), sorted(c_key), strict=False):
            stats[f"{prov}/seed{dk[1]}"] = {
                "paired_bootstrap_D_minus_C": paired_bootstrap(case_store[ck], case_store[dk]),
                "mcnemar_C_vs_D": mcnemar(case_store[ck], case_store[dk]),
            }
    (RESULTS / f"stats_{args.split}.json").write_text(json.dumps(stats, indent=1))
    per_case_dump = {
        f"{k[0]}|{k[1]}|{k[2]}": [r.__dict__ for r in v] for k, v in case_store.items()
    }
    (RUNS / f"case_results_{args.split}.json").write_text(json.dumps(per_case_dump))
    meta = {"split": args.split, "cases": len(case_ids), "llm_providers": llm_providers,
            "seeds": args.seeds, "temperature": args.temperature,
            "usage": global_tracker().snapshot(),
            "models": {p: _model_name(p) for p in llm_providers}}
    (RESULTS / f"run_meta_{args.split}.json").write_text(json.dumps(meta, indent=1))
    print(summary[["system", "runs", "precision_mean", "recall_mean", "f1_mean",
                   "hallucination_rate_mean"]].to_string(index=False))


def _model_name(provider: str) -> str:
    import os

    return {"gemini": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            "anthropic": os.getenv("ANTHROPIC_MODEL", ""),
            "openai": os.getenv("OPENAI_MODEL", "")}.get(provider, "")


if __name__ == "__main__":
    main()
