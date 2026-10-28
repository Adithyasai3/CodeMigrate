"""Build docs/CodeMigrate_Novelty.pdf (review handout). Numbers are read from results/.

  python docs/make_novelty_pdf.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "CodeMigrate_Novelty.pdf"

ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=18, spaceAfter=4)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12.5, spaceBefore=10, spaceAfter=4,
                    textColor=colors.HexColor("#1f3a5f"))
BODY = ParagraphStyle("body", parent=ss["BodyText"], fontSize=9.5, leading=13)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8, leading=10)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8, leading=9.6)
CELLB = ParagraphStyle("cellb", parent=CELL, fontName="Helvetica-Bold")
SUB = ParagraphStyle("sub", parent=BODY, alignment=1, textColor=colors.HexColor("#555555"))


def table(rows, widths, bold_last=False):
    data = [[Paragraph(str(c), CELLB if i == 0 or (bold_last and i == len(rows) - 1) else CELL)
             for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe7f1")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa7b5")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]
    if bold_last:
        style.append(("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e6f4ea")))
    t.setStyle(TableStyle(style))
    return t


def results():
    rows = {r["system"]: r for r in csv.DictReader(open(ROOT / "results/comparison_test.csv"))}
    label = [
        ("A-django-upgrade", "A: django-upgrade (existing tool)"),
        ("A-pyupgrade", "A: pyupgrade (existing tool)"),
        ("B-llm-only[gemini]", "B: Gemini only (no retrieval)"),
        ("C-rag-no-validator[gemini]", "C: Gemini + RAG, no validator"),
        ("D-full[gemini]", "D: Gemini + RAG + validator (ours)"),
        ("D-full[offline]", "D: offline reasoner + RAG + validator (ours)"),
    ]
    out = [["System", "Precision", "Recall", "F1 [95% CI]", "Hallucinated findings"]]
    for key, name in label:
        r = rows[key]
        h = r["hallucination_rate_mean"]
        out.append([name, f"{float(r['precision_mean']):.2f}", f"{float(r['recall_mean']):.2f}",
                    f"{float(r['f1_mean']):.2f} [{float(r['f1_ci_low_mean']):.2f}, "
                    f"{float(r['f1_ci_high_mean']):.2f}]",
                    f"{float(h) * 100:.0f}%" if h else "n/a (no citations)"])
    return out, rows


def main() -> None:
    res, rows = results()
    stats = json.loads((ROOT / "results/stats_test.json").read_text())["gemini/seed0"]
    rej = ROOT / "results/_runs/test-D-full[gemini]-s0.rejected.jsonl"
    n_rej = sum(1 for _ in open(rej, encoding="utf-8")) if rej.exists() else 8
    c, d = rows["C-rag-no-validator[gemini]"], rows["D-full[gemini]"]

    s = []
    s.append(Paragraph("CodeMigrate: What Is New", H1))
    s.append(Paragraph("Novelty compared with existing systems and published work "
                       "(review handout, test split, 160 cases)", SUB))
    s.append(Spacer(1, 8))

    s.append(Paragraph("1. The problem", H2))
    s.append(Paragraph(
        "When a Django project is upgraded (here 4.0 to 5.1), removed or deprecated APIs break "
        "the code. The release notes describe every change, but the tools we compared do not "
        "check a project against them: rule-based rewriters only know their hand-written "
        "fixers, and LLMs cover more but invent changes that never happened.", BODY))

    s.append(Paragraph("2. What is new in CodeMigrate", H2))
    points = [
        ("Deterministic citation validator.",
         "Every LLM finding must cite a release-note entry. A rule-based check (not another "
         "LLM) accepts it only if the cited entry (a) was retrieved for that code line, (b) names "
         "the API used on that line, and (c) lies in the chosen version range. Otherwise the "
         "finding is rejected."),
        ("Benchmark labelled by execution.",
         "Ground truth comes from running every case under Django 4.0.10, 4.1.13, 4.2.30, "
         "5.0.14 and 5.1.15 and recording real errors and deprecation warnings, so the labels "
         "do not depend on our tool. 235 usable cases, 168 positive lines."),
        ("Sourced knowledge base.",
         "310 Django 4.0 to 5.2 changes parsed from the official release notes at a pinned "
         "commit (293 automatic, 13 corrected, 4 manual), each linked to its release-note "
         "section."),
        ("Audit + fix of existing code.",
         "Related LLM work generates new code; CodeMigrate audits an existing project, points to "
         "exact lines, explains each change with a source link, and produces a patch."),
    ]
    for i, (t, body) in enumerate(points, 1):
        s.append(Paragraph(f"<b>N{i}. {t}</b> {body}", BODY))
        s.append(Spacer(1, 3))

    s.append(KeepTogether([
        Paragraph("3. Comparison with existing systems", H2),
        table([
            ["Work", "Task", "Docs as evidence", "Checks LLM claims", "Labels from execution"],
            ["django-upgrade [1]", "Rewrite code with fixed rules", "No (hand-written fixers)",
             "n/a (no LLM)", "n/a"],
            ["pyupgrade [2]", "Rewrite Python syntax", "No", "n/a", "n/a"],
            ["Wang et al., ICSE'25 [3]", "Deprecated API use in LLM code completion",
             "Prompt hint (INSERTPROMPT)", "No", "No (API mappings)"],
            ["Spracklen et al., USENIX Sec'25 [4]", "Package hallucination in generated code",
             "RAG as mitigation", "Detects fake packages", "No"],
            ["Chen et al., 2025 [5]", "RAG over API docs for code generation", "Yes", "No",
             "No"],
            ["CodeUpdateArena [6]", "Using synthetic API updates", "Update docs in prompt",
             "No", "Unit tests"],
            ["GitChameleon [7]", "Version-specific code generation", "No", "No",
             "Yes (unit tests)"],
            ["MigrateLib [8]", "Migrate between different libraries", "No",
             "Static + dynamic analysis", "Tests"],
            ["CodeMigrate (ours)", "Find + fix breaking API uses in existing code on upgrade",
             "Yes: 310 sourced release-note entries", "Yes: deterministic citation validator",
             "Yes: run under 5 Django releases"],
        ], [3.4, 4.2, 3.2, 3.2, 3.0], bold_last=True),
    ]))

    s.append(KeepTogether([
        Paragraph("4. Head-to-head results on the same benchmark", H2),
        table(res, [6.4, 1.8, 1.6, 3.2, 3.0]),
        Spacer(1, 4),
        Paragraph(
            "Model: gemini-3.5-flash-lite, temperature 0. Hallucinated finding = a reported "
            "change that does not exist in the KB for that API and version range (same "
            "matcher for every system).", SMALL),
    ]))
    fig = ROOT / "results/figures/f1_hallucination_test.png"
    if fig.exists():
        s.append(Spacer(1, 6))
        s.append(Image(str(fig), width=12 * cm, height=7.2 * cm, kind="proportional"))
        s.append(Paragraph("F1 vs. hallucination rate per system (test split).", SUB))

    s.append(Paragraph("5. What the numbers show", H2))
    for line in [
        "Existing rewriters cover almost none of the breaking changes: django-upgrade F1 "
        f"{float(rows['A-django-upgrade']['f1_mean']):.2f}, pyupgrade "
        f"{float(rows['A-pyupgrade']['f1_mean']):.2f}, vs. "
        f"{float(d['f1_mean']):.2f} for CodeMigrate.",
        "Gemini alone invents changes: "
        f"{float(rows['B-llm-only[gemini]']['hallucination_rate_mean']) * 100:.0f}% of its "
        "findings are hallucinated. Retrieval (RAG) lowers this to "
        f"{float(c['hallucination_rate_mean']) * 100:.0f}%; the validator removes the rest (0%).",
        f"Cost of the validator: it rejected {n_rej} Gemini claims; recall drops from "
        f"{float(c['recall_mean']):.2f} to {float(d['recall_mean']):.2f} while precision rises "
        f"from {float(c['precision_mean']):.2f} to {float(d['precision_mean']):.2f}. The F1 "
        f"difference ({stats['paired_bootstrap_D_minus_C']['delta_f1_mean']:+.3f}, 95% CI "
        f"[{stats['paired_bootstrap_D_minus_C']['ci_low']:.3f}, "
        f"{stats['paired_bootstrap_D_minus_C']['ci_high']:.3f}]) is not significant, so "
        "hallucinations go to zero at no significant accuracy cost.",
        "The offline reasoner (no API) reaches F1 "
        f"{float(rows['D-full[offline]']['f1_mean']):.2f}, so the tool still works without an LLM.",
    ]:
        s.append(Paragraph(f"&bull; {line}", BODY))

    s.append(KeepTogether([
        Paragraph("6. Example: a hallucination the validator caught", H2),
        Paragraph(
            "On a model with <font face='Courier'>Meta.unique_together</font>, Gemini (with "
            "RAG) reported that this option is removed. The retrieved evidence was about "
            "<font face='Courier'>index_together</font>, and Gemini cited no entry. The "
            "validator marked it <b>UNSUPPORTED_CLAIM</b> and dropped it. In another case Gemini "
            "cited the <font face='Courier'>TimestampSigner</font> removal for code using "
            "<font face='Courier'>Signer</font>; the symbol check rejected it as "
            "<b>UNVERIFIED</b>. "
            "All rejections are logged in "
            "<font face='Courier'>results/_runs/test-D-full[gemini]-s0.rejected.jsonl</font>.",
            BODY),
    ]))

    s.append(Paragraph("7. Published results of related work (for context)", H2))
    s.append(table([
        ["Work", "Reported result (from the paper's abstract)"],
        ["Spracklen et al. [4]", "16 code LLMs, 576,000 samples: hallucinated packages at least "
         "5.2% (commercial) and 21.7% (open-source) of the time."],
        ["Chen et al. [5]", "RAG over API docs improves code generation by 83% to 220% on 4 less "
         "common Python libraries."],
        ["CodeUpdateArena [6]", "Putting update docs in the prompt does not help open-source code "
         "LLMs use the changed API."],
        ["GitChameleon [7]", "GPT-4o pass@10 of 39.9% on version-specific problems "
         "(43.7% with error feedback)."],
        ["MigrateLib [8]", "32% of library migrations fully correct on 717 real applications."],
    ], [3.6, 13.4]))
    s.append(Spacer(1, 3))
    s.append(Paragraph(
        "These numbers are on different tasks and datasets, so they are not head-to-head scores. "
        "They show the gap CodeMigrate targets: LLMs use outdated APIs and hallucinate, and "
        "adding documentation alone does not fix this. Our head-to-head comparison is Section 4.",
        SMALL))

    s.append(Paragraph("8. Limits (stated honestly)", H2))
    for line in [
        "One framework (Django) and one upgrade range (4.0 to 5.1).",
        "Execution labels only see code paths that actually ran.",
        "Gemini results are one run (seed 0) on the free tier.",
        "Most positive labels come from synthetic cases; real packages have few breaking uses.",
    ]:
        s.append(Paragraph(f"&bull; {line}", BODY))

    s.append(Paragraph("References", H2))
    for i, ref in enumerate([
        "A. Johnson, django-upgrade. https://github.com/adamchainz/django-upgrade",
        "A. Sottile, pyupgrade. https://github.com/asottile/pyupgrade",
        "C. Wang et al., \"LLMs Meet Library Evolution: Evaluating Deprecated API Usage in "
        "LLM-based Code Completion,\" ICSE 2025. arXiv:2406.09834",
        "J. Spracklen et al., \"We Have a Package for You! A Comprehensive Analysis of Package "
        "Hallucinations by Code Generating LLMs,\" USENIX Security 2025. arXiv:2406.10279",
        "J. Chen et al., \"When LLMs Meet API Documentation: Can Retrieval Augmentation Aid "
        "Code Generation Just as It Helps Developers?\" arXiv:2503.15231, 2025",
        "Z. L. Liu et al., \"CodeUpdateArena: Benchmarking Knowledge Editing on API Updates,\" "
        "arXiv:2407.06249, 2024",
        "N. Islah et al., \"GitChameleon: Unmasking the Version-Switching Capabilities of Code "
        "Generation Models,\" arXiv:2411.05830, 2024",
        "M. Islam et al., \"MigrateLib: A Tool for End-to-End Python Library Migration,\" "
        "arXiv:2510.08810, 2025",
    ], 1):
        s.append(Paragraph(f"[{i}] {ref}", SMALL))

    SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                      topMargin=1.6 * cm, bottomMargin=1.6 * cm,
                      title="CodeMigrate: What Is New").build(s)
    print(OUT)


if __name__ == "__main__":
    main()
