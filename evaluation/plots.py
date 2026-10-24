"""Figures (PNG + PDF) and LaTeX/CSV tables from results/*.csv produced by run_experiments.

  python -m evaluation.plots --split test
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from evaluation.metrics import load_labels, prf, score_case  # noqa: E402

RESULTS = Path("results")
FIG = RESULTS / "figures"
TAB = RESULTS / "tables"
# Fixed color per system family (validated reference palette, light mode); never by rank.
COLORS = {"A": "#8a8984", "B": "#eb6834", "C": "#1baf7a", "D": "#2a78d6"}
INK, MUTED = "#0b0b0b", "#52514e"

plt.rcParams.update({
    "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
    "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.6, "axes.axisbelow": True,
    "savefig.bbox": "tight", "savefig.dpi": 200,
})


def color_for(system: str) -> str:
    return COLORS.get(system[:1], MUTED)


def save(fig, name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"{name}.{ext}")
    plt.close(fig)


def latex_table(df: pd.DataFrame, path: Path, caption: str, label: str) -> None:
    """Minimal booktabs table without extra dependencies."""
    cols = list(df.columns)
    lines = [r"\begin{table}[t]", r"\centering", r"\small",
             rf"\caption{{{caption}}}", rf"\label{{{label}}}",
             r"\begin{tabular}{" + "l" + "r" * (len(cols) - 1) + "}", r"\toprule",
             " & ".join(c.replace("_", r"\_").replace("%", r"\%") for c in cols) + r" \\",
             r"\midrule"]
    for _, row in df.iterrows():
        cells = [str(v).replace("_", r"\_").replace("%", r"\%").replace("±", r"$\pm$")
                 for v in row.tolist()]
        lines.append(" & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def fmt(mean, std, pct=True) -> str:
    if mean is None or mean != mean:
        return "n/a"
    scale = 100 if pct else 1
    s = f"{mean * scale:.1f}"
    if std is not None and std == std and std > 0:
        s += f" ± {std * scale:.1f}"
    return s


def comparison_table(split: str) -> pd.DataFrame:
    df = pd.read_csv(RESULTS / f"comparison_{split}.csv")
    out = pd.DataFrame({
        "System": df["system"],
        "Runs": df["runs"],
        "P (%)": [fmt(m, s) for m, s in zip(df.precision_mean, df.precision_std, strict=True)],
        "R (%)": [fmt(m, s) for m, s in zip(df.recall_mean, df.recall_std, strict=True)],
        "F1 (%)": [fmt(m, s) for m, s in zip(df.f1_mean, df.f1_std, strict=True)],
        "F1 95% CI": [f"[{lo * 100:.1f}, {hi * 100:.1f}]" for lo, hi in
                      zip(df.f1_ci_low_mean, df.f1_ci_high_mean, strict=True)],
        "Halluc. (%)": [fmt(m, s) for m, s in
                        zip(df.hallucination_rate_mean, df.hallucination_rate_std, strict=True)],
        "Cit. acc. (%)": [fmt(m, s) for m, s in
                          zip(df.citation_accuracy_mean, df.citation_accuracy_std, strict=True)],
        "Exact line (%)": [fmt(m, s) for m, s in
                           zip(df.line_exact_mean, df.line_exact_std, strict=True)],
    })
    TAB.mkdir(parents=True, exist_ok=True)
    out.to_csv(TAB / f"comparison_{split}.csv", index=False)
    latex_table(out, TAB / f"comparison_{split}.tex",
                f"System comparison on the {split} split (execution-labeled).",
                f"tab:comparison-{split}")
    cost = pd.DataFrame({
        "System": df["system"],
        "Latency/case (s)": [
            fmt(m, s, pct=False)
            for m, s in zip(df.latency_s_per_case_mean, df.latency_s_per_case_std, strict=True)
        ],
        "Tokens/case": [fmt(m, s, pct=False) for m, s in
                        zip(df.tokens_per_case_mean, df.tokens_per_case_std, strict=True)],
        "Cost/case (USD)": [f"{m:.5f}" if m == m else "n/a" for m in df.cost_usd_per_case_mean],
        "Findings": [fmt(m, s, pct=False) for m, s in
                     zip(df.findings_mean, df.findings_std, strict=True)],
        "Rejected claims": [fmt(m, s, pct=False) for m, s in
                            zip(df.rejected_claims_mean, df.rejected_claims_std, strict=True)],
    })
    cost.to_csv(TAB / f"latency_cost_{split}.csv", index=False)
    latex_table(cost, TAB / f"latency_cost_{split}.tex",
                f"Latency, tokens and cost per case ({split} split).", f"tab:cost-{split}")
    return df


def bar_f1_hallucination(df: pd.DataFrame, split: str) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True)
    ys = range(len(df))
    for ax, (col, title) in zip(axes, [("f1", "F1 (%)"), ("hallucination_rate",
                                                          "Hallucinated findings (%)")],
                                strict=True):
        vals = (df[f"{col}_mean"].fillna(0) * 100).tolist()
        errs = (df[f"{col}_std"].fillna(0) * 100).tolist()
        ax.barh(list(ys), vals, xerr=errs, height=0.6, color=[color_for(s) for s in df.system],
                error_kw={"ecolor": MUTED, "lw": 1, "capsize": 2})
        for y, v, s in zip(ys, vals, df[f"{col}_mean"], strict=True):
            ax.text(v + 1, y, "n/a" if s != s else f"{v:.1f}", va="center", fontsize=8, color=INK)
        ax.set_title(title, loc="left", fontsize=9, color=INK)
        ax.set_xlim(0, 110)
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(list(ys), df.system.tolist())
    axes[0].invert_yaxis()
    save(fig, f"f1_hallucination_{split}")


def pr_curve(split: str) -> None:
    labels = load_labels()
    fig, ax = plt.subplots(figsize=(3.6, 3.0))
    plotted = 0
    for run_file in sorted((RESULTS / "_runs").glob(f"{split}-*-s0.json")) + sorted(
            (RESULTS / "_runs").glob(f"{split}-D-full[[]offline[]].json")):
        name = run_file.stem.removeprefix(f"{split}-").removesuffix("-s0")
        if not name.startswith(("C-", "D-", "B-")):
            continue
        cases = json.loads(run_file.read_text())["cases"]
        thresholds = sorted({f.get("confidence", 1.0) for d in cases.values()
                             for f in d["findings"]} | {0.0})
        pts = []
        for t in thresholds:
            tp = fp = fn = 0
            for cid, d in cases.items():
                r = score_case(labels[cid], [f for f in d["findings"]
                                             if f.get("confidence", 1.0) >= t])
                tp, fp, fn = tp + r.tp, fp + r.fp, fn + r.fn
            p, rcl, _ = prf(tp, fp, fn)
            pts.append((rcl, p))
        pts.sort()
        ax.plot([x for x, _ in pts], [y for _, y in pts], marker="o", ms=3, lw=2,
                color=color_for(name), label=name, alpha=0.9 if name.startswith("D") else 0.7)
        plotted += 1
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1.02)
    if plotted:
        ax.legend(fontsize=7, frameon=False, loc="lower left")
    ax.set_title("Precision-recall by confidence threshold", loc="left", fontsize=9)
    save(fig, f"pr_curve_{split}")


def ablation_charts(split: str) -> None:
    path = RESULTS / f"ablations_{split}.csv"
    if not path.exists():
        return
    df = pd.read_csv(path)
    TAB.mkdir(parents=True, exist_ok=True)
    keep = ["system", "ablation", "retriever", "top_k", "precision", "recall", "f1",
            "hallucination_rate", "findings"]
    tab = df[keep].copy()
    for c in ("precision", "recall", "f1", "hallucination_rate"):
        tab[c] = (tab[c] * 100).round(1)
    tab.to_csv(TAB / f"ablations_{split}.csv", index=False)
    latex_table(tab.rename(columns={"hallucination_rate": "halluc"}),
                TAB / f"ablations_{split}.tex", f"Ablations ({split} split).",
                f"tab:ablations-{split}")
    for system, g in df.groupby("system"):
        r = g[g.ablation == "retriever"]
        k = g[g.ablation == "top_k"].sort_values("top_k")
        fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
        axes[0].bar(r.retriever, r.f1 * 100, color=color_for("D"), width=0.6)
        axes[0].plot(r.retriever, r.precision * 100, "s", color=INK, ms=4, label="precision")
        axes[0].plot(r.retriever, r.recall * 100, "^", color=MUTED, ms=4, label="recall")
        axes[0].set_title(f"{system}: retriever (bars = F1 %)", loc="left", fontsize=9)
        axes[0].set_ylim(0, 105)
        axes[0].legend(fontsize=7, frameon=False)
        axes[0].tick_params(axis="x", rotation=30)
        axes[1].plot(k.top_k, k.f1 * 100, marker="o", lw=2, color=color_for("D"), label="F1")
        axes[1].plot(k.top_k, k.recall * 100, marker="^", lw=2, color=MUTED, label="recall")
        axes[1].plot(k.top_k, k.precision * 100, marker="s", lw=2, color=INK, label="precision")
        axes[1].set_xticks([1, 3, 5])
        axes[1].set_xlabel("top-k")
        axes[1].set_ylim(0, 105)
        axes[1].legend(fontsize=7, frameon=False)
        axes[1].set_title(f"{system}: top-k (hybrid)", loc="left", fontsize=9)
        save(fig, f"ablation_{system.replace('[', '_').replace(']', '')}_{split}")


def breakdown_and_confusion(split: str) -> None:
    store_path = RESULTS / "_runs" / f"case_results_{split}.json"
    if not store_path.exists():
        return
    store = json.loads(store_path.read_text())
    labels = load_labels()
    label_meta = {}
    for cid, cl in labels.items():
        for lab in cl.labels:
            kinds = {e["kind"] for e in lab["evidence"]}
            label_meta[(cid, lab["file"], lab["line"])] = (
                "error" if "error" in kinds else "warning only", lab["first_version"])
    rows = []
    for key, cases in store.items():
        system, run, extra = key.split("|", 2)
        if extra != "{}" or run != "0":
            continue
        counts = defaultdict(lambda: [0, 0])
        for c in cases:
            for f, ln in c["tp_lines"]:
                meta = label_meta.get((c["case_id"], f, ln), ("?", "?"))
                counts[("evidence", meta[0])][0] += 1
                counts[("first version", meta[1])][0] += 1
            for f, ln in c["fn_lines"]:
                meta = label_meta.get((c["case_id"], f, ln), ("?", "?"))
                counts[("evidence", meta[0])][1] += 1
                counts[("first version", meta[1])][1] += 1
        for (dim, val), (tp, fn) in sorted(counts.items()):
            rows.append({"system": system, "dimension": dim, "value": val, "labels": tp + fn,
                         "recall": round(tp / (tp + fn) * 100, 1) if tp + fn else None})
        if system.startswith("D-full"):
            tp = sum(c["tp"] for c in cases)
            fp = sum(c["fp"] for c in cases)
            fn = sum(c["fn"] for c in cases)
            tn = sum(max(c["scored_negatives"] - c["fp"], 0) for c in cases)
            fig, ax = plt.subplots(figsize=(2.8, 2.5))
            mat = [[tp, fn], [fp, tn]]
            ax.imshow([[1, 0], [0, 1]], cmap="Blues", vmin=-0.5, vmax=3, alpha=0.6)
            for i in range(2):
                for j in range(2):
                    ax.text(j, i, str(mat[i][j]), ha="center", va="center", fontsize=11,
                            color=INK)
            ax.set_xticks([0, 1], ["flagged", "not flagged"])
            ax.set_yticks([0, 1], ["breaking", "not breaking"])
            ax.grid(False)
            ax.set_title(f"{system} (line level)", loc="left", fontsize=9)
            save(fig, f"confusion_{system.replace('[', '_').replace(']', '')}_{split}")
    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(TAB / f"breakdown_{split}.csv", index=False)
        latex_table(df, TAB / f"breakdown_{split}.tex",
                    f"Recall by label evidence type and first failing version ({split}).",
                    f"tab:breakdown-{split}")
        ev = df[df.dimension == "first version"]
        systems = list(dict.fromkeys(ev.system))
        values = sorted(set(ev.value))
        fig, ax = plt.subplots(figsize=(7.2, 2.6))
        width = 0.8 / max(len(systems), 1)
        for i, s in enumerate(systems):
            g = ev[ev.system == s].set_index("value")
            xs = [j + i * width for j in range(len(values))]
            ax.bar(xs, [g.recall.get(v, 0) or 0 for v in values], width=width * 0.9,
                   color=color_for(s), alpha=1.0 if "offline" not in s else 0.55, label=s)
        ax.set_xticks([j + 0.4 - width / 2 for j in range(len(values))],
                      [f"breaks in {v}" for v in values])
        ax.set_ylabel("Recall (%)")
        ax.set_ylim(0, 105)
        ax.legend(fontsize=6, frameon=False, ncol=3)
        ax.set_title("Recall by Django version where the usage first fails/warns", loc="left",
                     fontsize=9)
        save(fig, f"breakdown_version_{split}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test")
    args = ap.parse_args()
    df = comparison_table(args.split)
    bar_f1_hallucination(df, args.split)
    pr_curve(args.split)
    ablation_charts(args.split)
    breakdown_and_confusion(args.split)
    print(f"figures -> {FIG}, tables -> {TAB}")


if __name__ == "__main__":
    main()
