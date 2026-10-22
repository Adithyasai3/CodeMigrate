"""Retrieval-only benchmark: recall@k / MRR of each retriever on symbol -> entry pairs.

Queries are produced the same way the pipeline produces them: a usage snippet for a KB
entry is analyzed by the AST analyzer, and the CodeRef on the usage line is the query.
Relevant entries = all KB entries with the same affected_api (any version).

Caveat (also in README): queries are derived from KB names, so this measures how well
each retriever maps analyzer output to entries; it favors exact matching by construction.
End-to-end usefulness is measured on the execution-labeled benchmark (Phase 4/5).

Usage: python -m evaluation.retrieval_bench [--retrievers exact,bm25,...] [--out results/...]
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path

import pandas as pd

from codemigrate.analysis.ast_analyzer import analyze_source, analyze_template
from codemigrate.config import get_settings
from codemigrate.kb.build_kb import WHEEL_DIR
from codemigrate.kb.schema import load_kb
from codemigrate.kb.symbol_index import build_index
from codemigrate.kb.usage import usage_for
from codemigrate.retrieval import build_retriever
from codemigrate.retrieval.exact import method_names, template_names

log = logging.getLogger(__name__)
PAIRS_PATH = Path("benchmark/retrieval_pairs.jsonl")


def build_pairs(entries) -> tuple[list[dict], int]:
    """Return (pairs, analyzer_misses). Each pair: query ref + relevant entry ids."""
    index = build_index(WHEEL_DIR)
    methods, templates = method_names(entries), template_names(entries)
    by_api = defaultdict(set)
    for e in entries:
        by_api[e.affected_api].add(e.id)
    pairs, misses, seen = [], 0, set()
    for e in sorted(entries, key=lambda e: e.id):
        for variant in (0, 1):
            u = usage_for(e, index, variant)
            if u is None or u.code in seen:
                continue
            seen.add(u.code)
            if u.filename.endswith(".html"):
                refs = analyze_template(u.code, u.filename, templates)
            else:
                refs = analyze_source(u.code, u.filename, methods)
            on_line = [r for r in refs if r.line == u.line]
            if not on_line:
                misses += 1
                continue
            ref = max(on_line, key=lambda r: len(r.symbol))
            pairs.append(
                {
                    "query": ref.model_dump(mode="json"),
                    "style": u.style,
                    "api": e.affected_api,
                    "relevant": sorted(by_api[e.affected_api]),
                }
            )
    return pairs, misses


def evaluate(pairs, entries, retriever_names, ks=(1, 3, 5)) -> pd.DataFrame:
    from codemigrate.schemas import CodeRef

    rows = []
    for name in retriever_names:
        retr = build_retriever(name, entries)
        agg = defaultdict(float)
        for p in pairs:
            ref = CodeRef.model_validate(p["query"])
            ranked = [s.entry.id for s in retr.search(ref, k=max(ks))]
            rel = set(p["relevant"])
            for k in ks:
                top = ranked[:k]
                agg[f"recall@{k}"] += len(rel & set(top)) / min(len(rel), k)
                agg[f"hit@{k}"] += float(bool(rel & set(top)))
            rr = next((1 / (i + 1) for i, d in enumerate(ranked) if d in rel), 0.0)
            agg["mrr@5"] += rr
        n = len(pairs)
        rows.append({"retriever": name, "n_queries": n, **{k: v / n for k, v in agg.items()}})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--retrievers", default="exact,bm25,tfidf,dense,hybrid_tfidf,hybrid")
    ap.add_argument("--out", default="results/retrieval_benchmark.csv")
    args = ap.parse_args()
    entries = load_kb(get_settings().kb_path)
    pairs, misses = build_pairs(entries)
    PAIRS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PAIRS_PATH.open("w", encoding="utf-8", newline="\n") as fh:
        for p in pairs:
            fh.write(json.dumps(p) + "\n")
    df = evaluate(pairs, entries, args.retrievers.split(","))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False, float_format="%.4f")
    print(f"queries={len(pairs)} analyzer_misses={misses} (snippets whose usage line had no ref)")
    print(df.to_string(index=False, float_format=lambda x: f"{x:.3f}"))


if __name__ == "__main__":
    main()
