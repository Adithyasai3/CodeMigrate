"""Build compact, paper-ready tables in paper/tables/ from results/tables/*_test.csv.

  python paper/make_tables.py
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "results" / "tables"
OUT = ROOT / "paper" / "tables"

NAMES = {
    "A-django-upgrade": "A: django-upgrade",
    "A-pyupgrade": "A: pyupgrade",
    "B-llm-only[gemini]": "B: LLM only",
    "C-rag-no-validator[gemini]": "C: RAG, no validator",
    "D-full[gemini]": "D: full (ours)",
    "D-full[offline]": "D: full, offline (ours)",
}
ORDER = list(NAMES)  # C[offline] is identical to D[offline] and is left out


def rows(name: str) -> list[dict]:
    with open(SRC / f"{name}_test.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write(name: str, caption: str, label: str, head: list[str], body: list[list[str]],
          wide: bool = False, note: str = "") -> None:
    env = "table*" if wide else "table"
    cols = "l" + "r" * (len(head) - 1)
    lines = [rf"\begin{{{env}}}[t]", r"\centering", r"\footnotesize", r"\setlength{\tabcolsep}{4pt}",
             rf"\caption{{{caption}}}", rf"\label{{{label}}}", rf"\begin{{tabular}}{{{cols}}}",
             r"\toprule", " & ".join(head) + r" \\", r"\midrule"]
    lines += [" & ".join(r) + r" \\" for r in body]
    lines += [r"\bottomrule", r"\end{tabular}"]
    if note:
        lines.append(rf"\par\vspace{{2pt}}\parbox{{\linewidth}}{{\scriptsize {note}}}")
    lines.append(rf"\end{{{env}}}")
    (OUT / f"{name}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def pct(v: str) -> str:
    return "--" if v in ("", "n/a") else v.replace("%", r"\%")


def comparison() -> None:
    by = {r["System"]: r for r in rows("comparison")}
    body = [[NAMES[s], by[s]["P (%)"], by[s]["R (%)"], by[s]["F1 (%)"], by[s]["F1 95% CI"],
             pct(by[s]["Halluc. (%)"]), pct(by[s]["Cit. acc. (%)"])] for s in ORDER]
    write("comparison", "System comparison on the test split (160 cases, values in \\%).",
          "tab:comparison-test", ["System", "P", "R", "F1", "F1 95\\% CI", "Halluc.", "Cit. acc."],
          body, wide=True,
          note="LLM: gemini-3.5-flash-lite, temperature 0. Halluc. = findings whose claimed change is "
               "not in the knowledge base. Rule-based tools make no citations (--).")


def ablations() -> None:
    names = {"exact": "Exact", "bm25": "BM25", "tfidf": "TF-IDF", "dense": "Dense",
             "hybrid_tfidf": "Hybrid (TF-IDF)", "hybrid": "Hybrid"}
    body = []
    for r in rows("ablations"):
        if r["ablation"] == "retriever":
            label = names[r["retriever"]]
        elif r["top_k"] != "5":
            label = f"Hybrid, top-$k$={r['top_k']}"
        else:
            continue  # same run as the hybrid row above
        body.append([label, r["precision"], r["recall"], r["f1"], r["findings"]])
    write("ablations", "Retriever and top-$k$ ablation, offline reasoner (test, values in \\%).",
          "tab:ablations-test", ["Retriever", "P", "R", "F1", "Findings"], body,
          note="Top-$k$=5 unless stated. Hallucination rate is 0 in every row.")


def breakdown() -> None:
    data: dict[str, dict[str, str]] = {}
    labels: dict[str, str] = {}
    for r in rows("breakdown"):
        data.setdefault(r["system"], {})[r["value"]] = r["recall"]
        labels[r["value"]] = r["labels"]
    keys = ["error", "warning only", "4.0.10", "4.1.13", "4.2.30", "5.0.14", "5.1.15"]
    head = ["System", f"Error ({labels['error']})", f"Warning ({labels['warning only']})"] + \
           [f"{k[:3]} ({labels[k]})" for k in keys[2:]]
    body = [[NAMES[s]] + [data[s][k] for k in keys] for s in ORDER]
    write("breakdown", "Recall (\\%) by evidence type and by the first Django version that fails "
          "(test; number of labels in brackets).", "tab:breakdown-test", head, body, wide=True)


def cost() -> None:
    by = {r["System"]: r for r in rows("latency_cost")}
    body = []
    for s in ORDER:
        r = by[s]
        llm = "gemini" in s
        body.append([NAMES[s], "cached" if llm else r["Latency/case (s)"],
                     f"{float(r['Tokens/case']):,.0f}" if llm else "0"])
    write("cost", "Latency and LLM tokens per case (test split).", "tab:cost-test",
          ["System", "Latency (s)", "Tokens"], body,
          note="Gemini runs were replayed from the response cache, so their latency is not "
               "measured. All runs used the free tier (cost \\$0).")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    comparison()
    ablations()
    breakdown()
    cost()
    print("wrote", OUT)
