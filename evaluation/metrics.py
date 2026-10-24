"""Finding-level metrics against execution labels.

Matching (per case, per file):
  * findings on ignored lines (invalid under 4.0 / cascade / transitive) are dropped;
  * findings on lines never executed under 4.0 are "unscored" (no ground truth) and dropped;
  * findings are collapsed per (file, line); a collapsed finding matches a label when its line
    lies in the label's statement span [stmt_start, stmt_end] and, if the label's symbol is
    known, at least one of its symbols is compatible (same final identifier);
  * TP = matched labels, FN = unmatched labels, FP = scored collapsed findings matching nothing.
Hallucinated finding = its claimed symbol matches no KB entry in the version range, or (for
systems that cite) none of its citations is a valid in-range KB entry for that symbol.
"""

from __future__ import annotations

import json
import random
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from codemigrate.kb.schema import KBEntry
from codemigrate.kb.versions import in_range
from codemigrate.validation.matching import symbol_matches

LABELS_DIR = Path("benchmark/labels")


@dataclass
class CaseLabels:
    case_id: str
    kind: str
    split: str
    status: str
    labels: list[dict]
    ignored: set[tuple[str, int]]
    scored: dict[str, set[int]]


def load_labels(labels_dir: Path = LABELS_DIR) -> dict[str, CaseLabels]:
    out = {}
    for p in sorted(labels_dir.glob("*.json")):
        if p.name == "summary.json":
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        out[d["case_id"]] = CaseLabels(
            case_id=d["case_id"], kind=d["kind"], split=d["split"], status=d["status"],
            labels=d["labels"],
            ignored={(x["file"], x["line"]) for x in d["ignored_lines"]},
            scored={f: set(v) for f, v in d["scored_lines"].items()},
        )
    return out


def last_ident(symbol: str | None) -> str:
    if not symbol:
        return ""
    s = symbol.split(":")[-1].replace("*.", "")
    return re.split(r"[.\s(]", s.strip())[-1 if "(" not in s else 0].lower() if s else ""


def symbols_compatible(label_symbol: str | None, finding_symbols: set[str]) -> bool:
    if not label_symbol:
        return True
    want = last_ident(label_symbol)
    for s in finding_symbols:
        got = last_ident(s)
        if got == want or want in {p.lower() for p in re.split(r"[.:]", s)}:
            return True
    return False


@dataclass
class CaseResult:
    case_id: str
    tp: int = 0
    fp: int = 0
    fn: int = 0
    exact_line: int = 0
    unscored: int = 0
    tp_lines: list[tuple[str, int]] = field(default_factory=list)
    fp_lines: list[tuple[str, int]] = field(default_factory=list)
    fn_lines: list[tuple[str, int]] = field(default_factory=list)
    scored_negatives: int = 0  # scored lines without label (for TN in confusion matrix)


def score_case(cl: CaseLabels, findings: list[dict]) -> CaseResult:
    res = CaseResult(cl.case_id)
    collapsed: dict[tuple[str, int], set[str]] = defaultdict(set)
    for f in findings:
        key = (f["file"], int(f["line"]))
        if key in cl.ignored:
            continue
        label_span = any(lab["file"] == key[0] and lab["stmt_start"] <= key[1] <= lab["stmt_end"]
                         for lab in cl.labels)
        if key[1] not in cl.scored.get(key[0], set()) and not label_span:
            res.unscored += 1
            continue
        collapsed[key].add(f.get("symbol") or "")
    used: set[tuple[str, int]] = set()
    for lab in cl.labels:
        cands = [k for k in collapsed if k[0] == lab["file"]
                 and lab["stmt_start"] <= k[1] <= lab["stmt_end"]
                 and k not in used and symbols_compatible(lab.get("symbol"), collapsed[k])]
        if cands:
            best = min(cands, key=lambda k: abs(k[1] - lab["line"]))
            used.add(best)
            res.tp += 1
            res.exact_line += int(best[1] == lab["line"])
            res.tp_lines.append((lab["file"], lab["line"]))
        else:
            res.fn += 1
            res.fn_lines.append((lab["file"], lab["line"]))
    for k in collapsed:
        if k not in used:
            # A second finding inside an already-matched statement span is not a new error.
            if any(lab["file"] == k[0] and lab["stmt_start"] <= k[1] <= lab["stmt_end"]
                   for lab in cl.labels):
                continue
            res.fp += 1
            res.fp_lines.append(k)
    n_scored = sum(len(v) for v in cl.scored.values())
    res.scored_negatives = max(n_scored - len(cl.labels), 0)
    return res


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def aggregate(results: list[CaseResult]) -> dict:
    tp = sum(r.tp for r in results)
    fp = sum(r.fp for r in results)
    fn = sum(r.fn for r in results)
    p, r, f = prf(tp, fp, fn)
    tn = sum(max(r.scored_negatives - r.fp, 0) for r in results)
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": p, "recall": r, "f1": f,
            "line_exact": (sum(r.exact_line for r in results) / tp) if tp else 0.0,
            "unscored_findings": sum(r.unscored for r in results)}


def bootstrap_f1(
    results: list[CaseResult], iters: int = 1000, seed: int = 0
) -> tuple[float, float]:
    rng = random.Random(seed)
    vals = []
    for _ in range(iters):
        sample = [results[rng.randrange(len(results))] for _ in results]
        vals.append(prf(sum(r.tp for r in sample), sum(r.fp for r in sample),
                        sum(r.fn for r in sample))[2])
    vals.sort()
    return vals[int(0.025 * iters)], vals[int(0.975 * iters) - 1]


def paired_bootstrap(a: list[CaseResult], b: list[CaseResult], iters: int = 2000,
                     seed: int = 0) -> dict:
    """P(F1_b <= F1_a) under case resampling; a and b are aligned by case."""
    rng = random.Random(seed)
    n = len(a)
    deltas = []
    for _ in range(iters):
        idx = [rng.randrange(n) for _ in range(n)]
        fa = prf(sum(a[i].tp for i in idx), sum(a[i].fp for i in idx), sum(a[i].fn for i in idx))[2]
        fb = prf(sum(b[i].tp for i in idx), sum(b[i].fp for i in idx), sum(b[i].fn for i in idx))[2]
        deltas.append(fb - fa)
    deltas.sort()
    return {"delta_f1_mean": sum(deltas) / iters, "ci_low": deltas[int(0.025 * iters)],
            "ci_high": deltas[int(0.975 * iters) - 1],
            "p_value_one_sided": sum(d <= 0 for d in deltas) / iters}


def mcnemar(a: list[CaseResult], b: list[CaseResult]) -> dict:
    """Exact McNemar on line-level decisions (labels + any flagged line), a vs b."""
    from scipy.stats import binomtest

    only_a = only_b = 0
    for ra, rb in zip(a, b, strict=True):
        labeled = set(ra.tp_lines) | set(ra.fn_lines)  # identical label set for both systems
        units = labeled | set(ra.fp_lines) | set(rb.fp_lines)
        for u in units:
            # correct = found a labeled line, or did not raise a false alarm on an unlabeled one
            ca = (u in ra.tp_lines) if u in labeled else (u not in ra.fp_lines)
            cb = (u in rb.tp_lines) if u in labeled else (u not in rb.fp_lines)
            if ca and not cb:
                only_a += 1
            elif cb and not ca:
                only_b += 1
    n = only_a + only_b
    p = binomtest(only_a, n, 0.5).pvalue if n else 1.0
    return {"a_correct_b_wrong": only_a, "b_correct_a_wrong": only_b, "p_value": p}


def hallucination_flags(finding: dict, kb: list[KBEntry], from_v: str, to_v: str,
                        cites: bool) -> tuple[bool, bool | None]:
    """Return (hallucinated, citation_accurate or None if the system doesn't cite)."""
    in_scope = [e for e in kb if in_range(e.version_introduced, from_v, to_v)]
    symbol = finding.get("symbol") or ""
    supported = any(symbol_matches(symbol, e) for e in in_scope)
    if not cites:
        return (not supported), None
    by_id = {e.id: e for e in kb}
    cited = finding.get("cited_ids") or []
    valid = [c for c in cited if c in by_id and in_range(by_id[c].version_introduced, from_v, to_v)
             and symbol_matches(symbol, by_id[c])]
    citation_ok = bool(cited) and len(valid) == len(cited)
    return (not supported or not valid), citation_ok
