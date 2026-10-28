"""Build docs/CodeMigrate_Team_Guide.pdf (who does what, simple explanations, code + architecture).

  python docs/make_team_guide.py
"""
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, Preformatted, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

OUT = str(Path(__file__).resolve().parent / "CodeMigrate_Team_Guide.pdf")
F = "C:/Windows/Fonts/"

LEAD = "Adithya"
M = {1: "Prabhas", 2: "Dhanush", 3: "Sandhani", 4: "Hemanth", 5: "Sandhani"}
pdfmetrics.registerFont(TTFont("Body", F + "segoeui.ttf"))
pdfmetrics.registerFont(TTFont("Body-Bold", F + "segoeuib.ttf"))
pdfmetrics.registerFont(TTFont("Mono", F + "consola.ttf"))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body", boldItalic="Body-Bold")

NAVY = colors.HexColor("#14213D")
ORANGE = colors.HexColor("#B5561C")
BLUE = colors.HexColor("#2F6FB0")
MUTED = colors.HexColor("#4A5568")
CARD = colors.HexColor("#F1F3F7")
LINE = colors.HexColor("#DCDFE5")
PEACH = colors.HexColor("#FDF0E6")

st = {
    "h1": ParagraphStyle("h1", fontName="Body-Bold", fontSize=22, leading=27, textColor=NAVY, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="Body-Bold", fontSize=15, leading=19, textColor=NAVY,
                         spaceBefore=10, spaceAfter=5),
    "h3": ParagraphStyle("h3", fontName="Body-Bold", fontSize=11.5, leading=15, textColor=ORANGE,
                         spaceBefore=8, spaceAfter=3),
    "p": ParagraphStyle("p", fontName="Body", fontSize=10, leading=14.5, textColor=colors.black,
                        alignment=TA_LEFT, spaceAfter=4),
    "small": ParagraphStyle("small", fontName="Body", fontSize=8.5, leading=11.5, textColor=MUTED),
    "eyebrow": ParagraphStyle("eb", fontName="Body-Bold", fontSize=9, leading=12, textColor=ORANGE),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=9, leading=12),
    "cellb": ParagraphStyle("cellb", fontName="Body-Bold", fontSize=9, leading=12, textColor=colors.white),
    "code": ParagraphStyle("code", fontName="Mono", fontSize=8.3, leading=11, textColor=NAVY),
    "bullet": ParagraphStyle("bl", fontName="Body", fontSize=10, leading=14, leftIndent=12,
                             bulletIndent=2, spaceAfter=2),
}
W = A4[0] - 36 * mm


def P(t, s="p"):
    return Paragraph(t, st[s])


def bullets(items):
    return [Paragraph(t, st["bullet"], bulletText="•") for t in items]


def code(text):
    t = Table([[Preformatted(text.strip("\n"), st["code"])]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CARD), ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t


def table(rows, widths, bold_last=False):
    data = [[Paragraph(c, st["cellb"]) for c in rows[0]]]
    data += [[Paragraph(c, st["cell"]) for c in r] for r in rows[1:]]
    t = Table(data, colWidths=[W * w for w in widths], repeatRows=1)
    style = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.4, LINE),
             ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 4),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    for i in range(2, len(data), 2):
        style.append(("BACKGROUND", (0, i), (-1, i), CARD))
    if bold_last:
        style.append(("BACKGROUND", (0, len(data) - 1), (-1, len(data) - 1), PEACH))
    t.setStyle(TableStyle(style))
    return t


def note(text):
    t = Table([[Paragraph(text, st["p"])]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PEACH), ("BOX", (0, 0), (-1, -1), 0.6, ORANGE),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 6),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return t


def qa(pairs):
    out = []
    for q, a in pairs:
        out.append(KeepTogether([P(f"<b>Q: {q}</b>", "p"), P(f"A: {a}", "p")]))
    return out


# ---------- architecture diagram ----------
def arrow(d, x1, y1, x2, y2, c=MUTED):
    d.add(Line(x1, y1, x2, y2, strokeColor=c, strokeWidth=1.3))
    if x2 > x1:
        d.add(Polygon([x2, y2, x2 - 6, y2 + 3.5, x2 - 6, y2 - 3.5], fillColor=c, strokeColor=c))
    elif y2 < y1:
        d.add(Polygon([x2, y2, x2 - 3.5, y2 + 6, x2 + 3.5, y2 + 6], fillColor=c, strokeColor=c))
    else:
        d.add(Polygon([x2, y2, x2 - 3.5, y2 - 6, x2 + 3.5, y2 - 6], fillColor=c, strokeColor=c))


def box(d, x, y, w, h, title, sub, who, fill=CARD, edge=LINE):
    d.add(Rect(x, y, w, h, rx=6, ry=6, fillColor=fill, strokeColor=edge, strokeWidth=1))
    d.add(String(x + w / 2, y + h - 15, title, fontName="Body-Bold", fontSize=9, fillColor=NAVY,
                 textAnchor="middle"))
    for i, line in enumerate(sub):
        d.add(String(x + w / 2, y + h - 28 - i * 10, line, fontName="Body", fontSize=7.3, fillColor=MUTED,
                     textAnchor="middle"))
    d.add(String(x + w / 2, y + 6, who, fontName="Body-Bold", fontSize=7.3, fillColor=ORANGE,
                 textAnchor="middle"))


def architecture():
    d = Drawing(W, 270)
    bw, bh, y = 82, 72, 120
    xs = [0, 101, 202, 303, 404]
    names = [("1. AST Analyzer", ["finds Django uses", "+ exact line"], M[3]),
             ("2. Retriever", ["exact + BM25 +", "dense, RRF fusion"], M[3]),
             ("3. LLM Reasoner", ["judges each use", "from evidence only"], M[4]),
             ("4. Citation", ["Validator: no proof,", "no claim"], M[4]),
             ("5. Patcher /", ["Updater: builds the", "fixed file"], M[5])]
    # input
    d.add(Rect(0, 222, 120, 34, rx=6, ry=6, fillColor=NAVY, strokeColor=NAVY))
    d.add(String(60, 241, "Your Django code", fontName="Body-Bold", fontSize=9, fillColor=colors.white,
                 textAnchor="middle"))
    d.add(String(60, 229, ".py file / zip upload", fontName="Body", fontSize=7.3, fillColor=colors.white,
                 textAnchor="middle"))
    arrow(d, 41, 222, 41, y + bh)
    for i, (t, sub, who) in enumerate(names):
        hl = i == 3
        box(d, xs[i], y, bw, bh, t, sub, who, PEACH if hl else CARD, ORANGE if hl else LINE)
        if i < 4:
            arrow(d, xs[i] + bw, y + bh / 2, xs[i + 1], y + bh / 2)
    # KB
    d.add(Rect(170, 10, 148, 62, rx=6, ry=6, fillColor=colors.HexColor("#EAF2FB"), strokeColor=BLUE))
    d.add(String(244, 56, "Knowledge Base (310 entries)", fontName="Body-Bold", fontSize=8.5, fillColor=NAVY,
                 textAnchor="middle"))
    d.add(String(244, 43, "built from official Django", fontName="Body", fontSize=7.3, fillColor=MUTED,
                 textAnchor="middle"))
    d.add(String(244, 33, "release notes 4.0 to 5.1", fontName="Body", fontSize=7.3, fillColor=MUTED,
                 textAnchor="middle"))
    d.add(String(244, 16, M[1], fontName="Body-Bold", fontSize=7.3, fillColor=ORANGE, textAnchor="middle"))
    arrow(d, 243, 72, 243, y, BLUE)
    d.add(String(250, 92, "evidence", fontName="Body", fontSize=7, fillColor=BLUE))
    # output
    d.add(Rect(W - 128, 222, 128, 34, rx=6, ry=6, fillColor=NAVY, strokeColor=NAVY))
    d.add(String(W - 64, 241, "Findings + fixed file", fontName="Body-Bold", fontSize=9,
                 fillColor=colors.white, textAnchor="middle"))
    d.add(String(W - 64, 229, "web app / CLI / PDF report", fontName="Body", fontSize=7.3,
                 fillColor=colors.white, textAnchor="middle"))
    arrow(d, 445, y + bh, 445, 222)
    # benchmark box
    d.add(Rect(350, 10, W - 350, 62, rx=6, ry=6, fillColor=CARD, strokeColor=LINE))
    d.add(String(350 + (W - 350) / 2, 56, "Benchmark + Metrics", fontName="Body-Bold", fontSize=8.5,
                 fillColor=NAVY, textAnchor="middle"))
    d.add(String(350 + (W - 350) / 2, 43, "235 cases, labels by running", fontName="Body", fontSize=7.3,
                 fillColor=MUTED, textAnchor="middle"))
    d.add(String(350 + (W - 350) / 2, 33, "code on 5 Django versions", fontName="Body", fontSize=7.3,
                 fillColor=MUTED, textAnchor="middle"))
    d.add(String(350 + (W - 350) / 2, 16, f"{M[2]} (scores the whole system)", fontName="Body-Bold",
                 fontSize=7.3, fillColor=ORANGE, textAnchor="middle"))
    d.add(String(0, 92, f"Web app + CLI wrap the whole pipeline ({M[5]})", fontName="Body", fontSize=7.3,
                 fillColor=MUTED))
    d.add(String(W, 104, f"Overall design + team lead: {LEAD}", fontName="Body-Bold", fontSize=7.3,
                 fillColor=NAVY, textAnchor="end"))
    return d


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Body", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 10 * mm, "CodeMigrate · team guide (internal, not paper text)")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


s = []
# ---------- cover ----------
s += [Spacer(1, 30 * mm), P("CODEMIGRATE · PROJECT REVIEW", "eyebrow"),
      P("Team Guide: who does what, and how it all works", "h1"),
      P(f"<b>Project lead: {LEAD}.</b> Team: {M[1]}, {M[2]}, {M[3]}, {M[4]}."),
      P("A simple explanation of the whole project, split into parts with one owner each. "
        "Each part has: what you own, an easy way to explain it, the code to show, the numbers to "
        "remember, likely reviewer questions with answers, and the paper section you write."),
      Spacer(1, 6),
      note("<b>Important:</b> this guide is for <b>understanding and preparing</b>. Do not copy its "
           "sentences into the IEEE paper. The paper must be under 10% AI-generated and under 10% "
           "similarity, so write your section in your own words from the code and the results."),
      Spacer(1, 10), P("Contents", "h2")]
s += bullets(["1. The project in one minute", "2. Architecture (diagram + one example walked through)",
              "3. Who does what (team table, status, review talk order)",
              f"4. Project lead: {LEAD}",
              f"5. Part 1: Knowledge Base ({M[1]})", f"6. Part 2: Benchmark and Evaluation ({M[2]})",
              f"7. Part 3: Code Analysis and Retrieval ({M[3]})",
              f"8. Part 4: LLM Reasoner and Citation Validator ({M[4]})",
              f"9. Part 5: Fixing, Web App and CLI ({M[5]})", "10. Results everyone must know",
              "11. Paper plan and timeline"])
s.append(PageBreak())

# ---------- 1 one minute ----------
s += [P("1. The project in one minute", "h2"),
      P("<b>Problem.</b> When a Django project moves from version 4.0 to 5.x, some functions, arguments "
        "and settings it uses have been removed or changed. The code breaks only when it runs. Existing "
        "rule tools (django-upgrade) know only a few hand-written fixes, and LLMs like ChatGPT often "
        "<i>make up</i> problems that do not exist."),
      P("<b>Our idea.</b> CodeMigrate reads your code, finds every Django API you use, looks up the "
        "<b>official Django release notes</b> for that API, lets an LLM decide if it breaks, and then "
        "<b>checks the LLM's answer with plain code</b>. A warning is shown only if a real release note "
        "backs it. Finally it gives back the <b>fixed file</b>."),
      P("<b>Easy analogy.</b> Think of a student (the LLM) writing an exam answer with an open book "
        "(the release notes). A strict teacher (our citation validator) checks that every answer quotes "
        "the right page of the book. Answers without a correct page number get zero."),
      P("<b>Result in one line.</b> Our system: F1 0.82 with 0% made-up findings. The existing tool "
        "django-upgrade: F1 0.02. An LLM alone: F1 0.71 with 29% made-up findings."),
      P("Key words", "h3")]
s.append(table([["Word", "Simple meaning"],
                ["AST", "Abstract Syntax Tree: Python's own tree view of code. Lets us find exact uses of "
                        "names, even with import aliases, without running the code."],
                ["Knowledge Base (KB)", "Our database of 310 Django API changes, each linked to the "
                                        "official release-note page."],
                ["RAG", "Retrieval-Augmented Generation: give the LLM the relevant documents before it answers."],
                ["BM25 / dense / RRF", "Three ways to search the KB (keywords, meaning, and a method to "
                                       "merge the rankings)."],
                ["Hallucination", "A finding the LLM made up: no real release note supports it."],
                ["Precision / Recall / F1", "Precision = how many warnings were right. Recall = how many real "
                                            "problems we caught. F1 = balance of both (0 to 1)."],
                ["Execution labels", "The 'answer key': we ran every test case on 5 Django versions and "
                                     "recorded which lines really break."]], [0.25, 0.75]))
s.append(PageBreak())

# ---------- 2 architecture ----------
s += [P("2. Architecture", "h2"),
      P("The pipeline has five stages. Each code file flows left to right. The Knowledge Base feeds "
        "evidence into the retriever. The benchmark measures the whole thing. The web app and CLI are "
        "two ways to run it."),
      architecture(), Spacer(1, 6),
      P("Where it lives in the code", "h3")]
s.append(table([["Stage", "Folder / file", "Explains it"],
                ["Build Knowledge Base", "src/codemigrate/kb/ (build_kb.py, symbol_index.py, schema.py)", M[1]],
                ["Benchmark + labels", "benchmark/ (build_benchmark.py, label_by_execution.py)", M[2]],
                ["Metrics + experiments", "evaluation/ (metrics.py, run_experiments.py, plots.py)", M[2]],
                ["1. AST Analyzer", "src/codemigrate/analysis/ (ast_analyzer.py, repo_scanner.py)", M[3]],
                ["2. Retriever", "src/codemigrate/retrieval/ (exact, bm25, dense, hybrid)", M[3]],
                ["3. LLM Reasoner", "src/codemigrate/llm/ (reasoner, prompts, gemini, offline, cache)", M[4]],
                ["4. Citation Validator", "src/codemigrate/validation/ (citation_validator.py, matching.py)", M[4]],
                ["Glue: runs stages 1-5", "src/codemigrate/pipeline.py", M[4]],
                ["5. Patcher / Updater", "src/codemigrate/patching/ (fixer.py, updater.py)", M[5]],
                ["Web app + CLI", "src/codemigrate/api/, frontend/src/, src/codemigrate/cli.py", M[5]]],
               [0.27, 0.58, 0.15]))
s += [P("One example, end to end", "h3"),
      P("Input file <font name='Mono'>views.py</font>, upgrading 4.0 to 5.1:")]
s.append(code("""
from django.utils.timezone import utc      # line 1
now = datetime.now(tz=utc)                 # line 2
"""))
s += bullets([
    "<b>Analyzer</b> sees line 1 imports <font name='Mono'>django.utils.timezone.utc</font> and line 2 uses it.",
    "<b>Retriever</b> finds KB entry <font name='Mono'>django-4.1-deprecated-django_utils_timezone_utc</font> "
    "(deprecated in 4.1, replacement <font name='Mono'>datetime.timezone.utc</font>, link to the 4.1 release notes).",
    "<b>LLM Reasoner</b> gets the code plus that entry and answers in JSON: line 1 breaks, cite that id.",
    "<b>Validator</b> checks: the id exists, was retrieved for that line, names the same symbol, and 4.1 is "
    "inside 4.0 to 5.1. All true, so the finding is <b>VERIFIED</b>.",
    "<b>Patcher</b> rewrites the import to use <font name='Mono'>datetime.timezone.utc</font> and returns the "
    "whole updated file, with a diff."])
s.append(Spacer(1, 10))

# ---------- 3 overview ----------
s += [P("3. Who does what", "h2"),
      P("Each person owns one or two parts: they learn it, explain it in the review, answer questions on "
        "it, show it in the demo, and write its section of the paper.")]
s.append(table([["Name", "Role / owns", "Shows in demo", "Writes in paper"],
                [f"<b>{LEAD}</b>", "<b>Project lead.</b> Idea, problem research, study of existing tools, "
                 "architecture, task division, implementation lead. Explains the overall project and leads "
                 "the team.", "Opens the talk with the full pipeline; closes with summary + questions",
                 "Reviews the final merged draft"],
                [M[1], "Part 1: Knowledge Base from release notes", "Open a KB entry and its official link",
                 "Knowledge Base + Related Work"],
                [M[2], "Part 2: Benchmark, execution labels, metrics, experiments",
                 "Show results table and graphs", "Benchmark + Results. Merges all sections in Overleaf"],
                [M[3], "Part 3: AST analyzer + retrieval. Part 5: fixer, web app, CLI",
                 "Show findings with exact lines; <b>runs the live demo</b> (Updated code tab)",
                 "Method: analysis + retrieval; System implementation"],
                [M[4], "Part 4: LLM reasoner (Gemini), citation validator, pipeline",
                 "Show a rejected (made-up) Gemini claim",
                 "Abstract, Introduction, Method: validator, Limitations, Conclusion. Runs the AI + "
                 "plagiarism checks"]], [0.13, 0.33, 0.27, 0.27]))
s += [Spacer(1, 6), P("Status: what is done and what is left", "h3")]
s.append(table([["Work", "Status", "Who"],
                ["Idea, research, architecture, task division", "Done", LEAD],
                ["Full implementation: KB, benchmark, analyzer, retrieval, Gemini reasoner, validator, "
                 "fixer, web app, CLI, 53 tests", "Done", LEAD],
                ["Results, graphs, comparison tables", "Done", LEAD],
                ["Novelty PDF, slides, demo script, this guide, paper template + tables + references",
                 "Done", LEAD],
                ["Learn your part and practise a 2-minute explanation", "To do", "Everyone"],
                ["Write your paper section in your own words (paper/WRITING_PLAN.md)", "To do",
                 f"{M[1]}, {M[2]}, {M[3]}, {M[4]}"],
                ["Merge sections in Overleaf, compile PDF", "To do", M[2]],
                ["AI-content + plagiarism reports (both under 10%)", "To do", M[4]],
                ["One full practice of talk + demo together", "To do", "Everyone"]],
               [0.62, 0.12, 0.26]))
s += [Spacer(1, 6)]
s.append(KeepTogether([P("Review talk order (about 12 minutes)", "h3"), table([["Time", "Who", "Slides"],
                ["0:00-2:00", LEAD, "Title, team, problem, our idea, overall pipeline (all 5 stages)"],
                ["2:00-3:00", M[3], "Stages 1-2: analyzer and retrieval"],
                ["3:00-4:30", M[4], "Stages 3-4: Gemini reasoner and citation validator"],
                ["4:30-5:30", M[1], "Knowledge base"],
                ["5:30-8:00", M[2], "Benchmark, systems A/B/C/D, results, key result, ablation"],
                ["8:00-9:00", M[1], "Novelty table"],
                ["9:00-11:00", M[3], "Live demo (stage 5: Updated code tab)"],
                ["11:00-12:00", f"{LEAD}, then all", "Limits, summary, questions"]], [0.2, 0.2, 0.6])]))

# ---------- 4 project lead ----------
s += [Spacer(1, 14), P("PROJECT LEAD", "eyebrow"), P(f"4. {LEAD}: idea, design and team lead", "h2"),
      P(f"<b>{LEAD} did:</b>")]
s += bullets(["Found the problem: Django upgrades break code, and existing tools miss most of it.",
              "Researched existing tools (django-upgrade, pyupgrade) and related papers on LLMs, "
              "deprecated APIs and hallucination.",
              "Designed the 5-stage pipeline and the main idea: the LLM must cite a release note, and a "
              "rule-based validator checks every citation.",
              "Planned how to implement each part and divided the work into the five parts in this guide.",
              "Led the implementation and joined all parts into one working tool (web app + CLI)."])
s += [P(f"What {LEAD} says in the review (opening, about 2 minutes)", "h3")]
s += bullets(["<b>Problem:</b> when Django is upgraded, old code breaks; release notes list the changes, "
              "but the tools we tested do not check code against them.",
              "<b>Idea:</b> find every Django API in the code, look it up in 310 official release-note "
              "entries, let Gemini explain using only that evidence, and check every answer with rules.",
              "<b>Pipeline:</b> show the diagram on page 3 and name who explains each stage.",
              "<b>Team:</b> introduce each member and their part."])
s += [P("Closing (about 1 minute)", "h3")]
s += bullets(["Main result: F1 0.82 vs 0.02 for django-upgrade; made-up findings 29% to 0%.",
              "Limits: Django only, one Gemini run, small test files.",
              "Hand each question to the member who owns that part."])
s.append(PageBreak())


def member(n, title, owns, simple, steps, files, snippet, snippet_note, numbers, questions, paper):
    out = [P(f"PART {n} · OWNER: {M[n].upper()}", "eyebrow"), P(f"{n + 4}. {title}", "h2"),
           P(f"<b>{M[n]} owns:</b> " + owns),
           P("Explain it simply", "h3"), P(simple), P("How it works", "h3")]
    out += bullets(steps)
    out += [P("Files to know", "h3")] + bullets(files)
    out += [P("Code walkthrough", "h3"), code(snippet), P(snippet_note, "small")]
    out += [P("Numbers to remember", "h3")] + bullets(numbers)
    qs = qa(questions)
    out += [KeepTogether([P("Likely reviewer questions", "h3"), qs[0]])] + qs[1:]
    out += [P("Your paper section", "h3"), P(paper), PageBreak()]
    return out


s += member(
    1, "Knowledge Base (KB)",
    "turning Django's official release notes into a clean, searchable list of 310 API changes.",
    "The release notes are long web pages written for humans. We turn them into a table the computer can "
    "search: one row per change, saying <i>which API</i>, <i>which version</i>, <i>what happened</i> "
    "(removed, deprecated, renamed, behaviour changed), <i>what to use instead</i>, and the <i>link</i> to "
    "the official page. Every finding CodeMigrate shows points to one of these rows, so every claim can be "
    "traced back to Django's own documentation.",
    ["Download <font name='Mono'>docs/releases/&lt;version&gt;.txt</font> from Django's repository at a fixed "
     "commit (cached in <font name='Mono'>data/kb/raw/</font>), so the build is repeatable.",
     "Read only three sections: <i>Backwards incompatible changes</i>, <i>Features deprecated</i>, "
     "<i>Features removed</i>.",
     "Turn every bullet into one or more entries. Notes often say a short name like "
     "<font name='Mono'>ModelAdmin.lookup_allowed</font>; the <b>symbol index</b> (an AST scan of Django's "
     "own source) maps it to the full dotted path.",
     "Apply <font name='Mono'>data/kb/manual_corrections.yaml</font>: fixes for parser mistakes. Every "
     "override is logged and the entry is marked <font name='Mono'>manually_corrected</font>.",
     "Write <font name='Mono'>data/kb/django_changes.jsonl</font> (the KB) and "
     "<font name='Mono'>build_report.json</font>."],
    ["<font name='Mono'>src/codemigrate/kb/build_kb.py</font>: the build steps above",
     "<font name='Mono'>src/codemigrate/kb/schema.py</font>: what one entry looks like (KBEntry)",
     "<font name='Mono'>src/codemigrate/kb/symbol_index.py</font>: short name to full path",
     "<font name='Mono'>src/codemigrate/kb/versions.py</font>: version comparison helpers",
     "<font name='Mono'>data/kb/django_changes.jsonl</font>: the finished KB"],
    """
class KBEntry(BaseModel):          # src/codemigrate/kb/schema.py (simplified)
    id: str                        # e.g. django-4.1-deprecated-django_utils_timezone_utc
    version_introduced: str        # "4.1"
    change_type: ChangeType        # removed | deprecated | behavior_changed | renamed
    affected_api: str              # "django.utils.timezone.utc"
    replacement: str | None        # "datetime.timezone.utc"
    source_url: HttpUrl            # must be an official docs.djangoproject.com link
    provenance: Provenance         # auto_parsed | manually_corrected | manual
    mechanical_fix: bool           # True if the patcher can fix it automatically
""",
    "Pydantic checks every entry when it is loaded: a wrong version format or a non-official link is "
    "rejected, so a bad row can never reach the pipeline.",
    ["310 KB entries, Django 4.0 to 5.1 release notes.",
     "4 change types: removed, deprecated, renamed, behavior_changed.",
     "Every entry has an official source_url and a provenance flag."],
    [("Why not just let the LLM remember Django changes?",
      "LLM memory can be outdated or wrong, and it cannot give a source. Our KB is built from the official "
      "notes, so every finding has a link the user can check."),
     ("What if the parser reads a bullet wrongly?",
      "We fix it in manual_corrections.yaml. Each fix is logged and the entry is marked manually_corrected, "
      "so we can say exactly how many entries were hand-fixed."),
     ("Why do you need a symbol index?",
      "Release notes use short names. Code imports full paths. The index maps one to the other by reading "
      "Django's source code with the AST, without importing or running it."),
     ("Can this work for other libraries?",
      "The design can, as long as the library has structured release notes. We only built and tested it "
      "for Django.")],
    "Knowledge Base construction (sources, parsing, symbol resolution, manual corrections) and the "
    "Related Work section (read the papers in docs/RELATED_WORK.md first).")

s += member(
    2, "Benchmark and Evaluation",
    "the test cases, the answer key (labels), the metrics and all result tables and graphs.",
    "To prove our tool works we need an exam with an answer key. We wrote 235 small Django code cases. To "
    "get the answer key <b>without trusting any tool</b>, we actually <b>ran</b> every case on five Django "
    "versions and recorded which lines crash or give a removal warning. Then we score each system's "
    "warnings against that key.",
    ["<b>Build cases</b> (build_benchmark.py): <i>synthetic</i> (one KB API placed in small realistic code), "
     "<i>negative</i> (clean code and near-misses that should NOT be flagged) and <i>real</i> (files from "
     "Django 4.0-era open-source packages).",
     "<b>Split</b> into dev and test by hashing a group key, so variants of the same API never appear in "
     "both. All reported results are on the <b>test</b> split (160 cases).",
     "<b>Label by running</b> (label_by_execution.py): run each case on Django 4.0.10, 4.1.13, 4.2.30, "
     "5.0.14 and 5.1.15 in a Docker image.",
     "<b>Score</b> (metrics.py): match each warning to a labelled line, count TP / FP / FN, compute "
     "precision, recall, F1 with 95% bootstrap confidence intervals, and the hallucination rate.",
     "<b>Run everything</b> (run_experiments.py) and draw figures (plots.py) into results/."],
    ["<font name='Mono'>benchmark/build_benchmark.py</font>, <font name='Mono'>benchmark/label_by_execution.py</font>",
     "<font name='Mono'>evaluation/metrics.py</font>, <font name='Mono'>evaluation/run_experiments.py</font>, "
     "<font name='Mono'>evaluation/plots.py</font>, <font name='Mono'>evaluation/error_analysis.py</font>",
     "<font name='Mono'>results/tables/*.csv|.tex</font>, <font name='Mono'>results/figures/*.png</font>"],
    """
Labeling rule (from benchmark/label_by_execution.py, upgrade 4.0 -> 5.1):
  positive line = a statement that raises an error under some target version (4.1..5.1)
                  but not under 4.0,
               OR emits a Django removal warning (RemovedInDjangoXYWarning, X.Y > 4.0).
  ignored line  = fails already under 4.0, a NameError caused by a failed import,
                  or an error raised deep inside another third-party module.
  scored lines  = lines executed under 4.0 plus labelled lines.

Metric (evaluation/metrics.py):
  TP = labelled lines our findings hit      FN = labelled lines we missed
  FP = scored findings that hit nothing     F1 = 2PR / (P + R)
  hallucinated = cited evidence does not support the claimed symbol / version range
""",
    "The labels never use CodeMigrate itself, so the benchmark cannot be biased toward our tool.",
    ["235 usable cases: dev 75, test 160.", "5 Django versions run per case.",
     "Test results: ours (D) F1 0.82, LLM-only (B) 0.71, django-upgrade 0.02, pyupgrade 0.00.",
     "Hallucination: B 29%, C 6%, D 0%."],
    [("Why not label the cases by hand?",
      "Hand labels can be wrong or biased. Running the code on each Django version shows what really breaks."),
     ("What is a confidence interval here?",
      "We resample the test cases many times (bootstrap) and recompute F1. The 95% range shows how much "
      "the score could move with a different sample of cases."),
     ("Why is C's F1 (0.83) slightly higher than D's (0.82)?",
      "The validator also throws away a few correct findings (recall 0.92 to 0.88), but it removes every "
      "unsupported one. We trade a little recall for zero made-up findings."),
     ("Why only one Gemini run?",
      "The free API tier allows about 500 requests a day. Every call is cached in .cache/llm, so the "
      "reported numbers reproduce exactly without new calls.")],
    "Benchmark (case types, split, execution labelling, metrics) and Experimental Results (tables, "
    "figures, error analysis).")

s += member(
    3, "Code Analysis and Retrieval",
    "finding every Django API used in the code (with exact line numbers) and searching the KB for it.",
    "Step one is like highlighting every Django word in an essay, including nicknames (import aliases). "
    "Step two is like looking each highlighted word up in the index of a book: we use three different "
    "search methods and combine their rankings, so we find the right release note even when the wording "
    "is different.",
    ["<b>AST analyzer</b> parses each file into a syntax tree and resolves "
     "<font name='Mono'>import a.b as c</font>, <font name='Mono'>from a import b as c</font>, attribute "
     "chains, <font name='Mono'>settings.X</font>, dotted strings like "
     "<font name='Mono'>\"django.middleware.x.Y\"</font>, Meta options and distinctive method calls.",
     "Generic names (and dunder methods like <font name='Mono'>__str__</font>) are not flagged on unknown "
     "objects, to avoid false alarms.",
     "<b>Exact retriever</b>: matches the full dotted name or alias.",
     "<b>BM25</b>: keyword search over the entry text.",
     "<b>Dense</b>: MiniLM sentence embeddings + FAISS index, finds entries with similar meaning.",
     "<b>Hybrid</b>: merges the three ranked lists with Reciprocal Rank Fusion (RRF) and keeps the top-k "
     "entries inside the upgrade's version range."],
    ["<font name='Mono'>src/codemigrate/analysis/ast_analyzer.py</font>, "
     "<font name='Mono'>repo_scanner.py</font> (reads files/zips)",
     "<font name='Mono'>src/codemigrate/retrieval/exact.py</font>, <font name='Mono'>bm25.py</font>, "
     "<font name='Mono'>dense.py</font>, <font name='Mono'>hybrid.py</font>",
     "<font name='Mono'>evaluation/retrieval_bench.py</font> (retrieval quality)"],
    """
# src/codemigrate/retrieval/hybrid.py  (idea)
# score(entry) = sum over retrievers r of   w_r / (k_rrf + rank_r(entry))     with k_rrf = 60
#
# Example with all weights = 1: an entry ranked 1st by exact and 3rd by BM25:
#   1/(60+1) + 1/(60+3) = 0.0164 + 0.0159 = 0.0323   -> high final score
# An entry found by only one retriever at rank 10:
#   1/(60+10) = 0.0143                                -> lower
""",
    "RRF only uses ranks, not raw scores, so the three very different scoring methods can be combined "
    "fairly without tuning.",
    ["Ablation on test (offline reasoner): exact / BM25 / hybrid F1 0.81, dense F1 0.83.",
     "top-k 1, 3, 5 gave the same result offline.",
     "Removing dunder methods from 'distinctive' names raised test F1 from 0.76 to 0.79 (found during "
     "error analysis, confirmed on dev)."],
    [("Why AST and not regex/grep?",
      "AST understands Python: it follows import aliases and attribute chains and gives exact line numbers. "
      "Regex would miss aliases and match comments or strings by mistake."),
     ("Why three retrievers?",
      "Exact is precise but misses reworded names; BM25 catches keywords; dense catches meaning. Fusing them "
      "is more robust than any single one."),
     ("Dense scored best. Why keep hybrid as default?",
      "The difference (0.83 vs 0.81) is inside the confidence interval, and hybrid is more robust when "
      "names are unusual. We report the ablation honestly."),
     ("How do you avoid flagging every .save() or .get()?",
      "Common method names on objects whose type we do not know are skipped; only distinctive names are "
      "checked.")],
    "Method: static analysis and retrieval, plus the retriever and top-k ablation results.")

s += member(
    4, "LLM Reasoner and Citation Validator",
    "asking the LLM to decide which uses break, and the code that checks every answer (our main novelty).",
    "The LLM is the student, the release notes are the open book, and the validator is the strict "
    "teacher. The student must quote an entry id for every claim. The teacher checks that the quoted "
    "entry really exists, was really in front of the student for that line, talks about the same API, "
    "and belongs to the right Django versions. Wrong or missing quotes: the claim is thrown out.",
    ["The pipeline (pipeline.py) runs the analyzer, gets evidence for each code reference, and sends one "
     "prompt per file to the LLM.",
     "Prompt rule: use <b>only the given evidence</b>, answer in <b>JSON</b>, cite entry ids. Temperature 0.",
     "Providers: Gemini (gemini-3.5-flash-lite, free tier), OpenAI-compatible, and an <b>offline</b> "
     "rule-based reasoner that needs no API key.",
     "Every LLM call is cached on disk by a hash of (provider, model, prompt, settings), so reruns are "
     "free and identical.",
     "The validator marks each finding VERIFIED, UNVERIFIED or UNSUPPORTED_CLAIM and logs the reason.",
     "Systems compared: B = LLM alone; C = LLM + evidence; D = LLM + evidence + validator (ours)."],
    ["<font name='Mono'>src/codemigrate/pipeline.py</font> (scan_sources: the main loop)",
     "<font name='Mono'>src/codemigrate/llm/</font>: reasoner.py, prompts.py, gemini.py, openai.py, "
     "offline.py, cache.py, base.py (retries, quota handling)",
     "<font name='Mono'>src/codemigrate/validation/citation_validator.py</font>, <font name='Mono'>matching.py</font>"],
    """
# src/codemigrate/validation/citation_validator.py  -- "no proof, no claim"
# A finding is VERIFIED only if at least one cited id:
#   1. exists in the KB,
#   2. was retrieved as evidence for a code reference on the claimed line,
#   3. is within the requested version range (e.g. 4.0 -> 5.1),
#   4. names the claimed symbol and the code reference's symbol.
# No valid citation (none, unknown id, or not in that line's evidence) -> UNSUPPORTED_CLAIM
# Citation exists but fails line / symbol / version checks          -> UNVERIFIED

# src/codemigrate/pipeline.py  (core of scan_sources, simplified)
for ref in file.refs:
    hits = retriever.search(ref, top_k, from_version, to_version)
    if hits: evidences.append(Evidence(ref, hits))
findings = reason_grounded(client, path, source, evidences, ...)
for f in findings:
    vf = validator.validate(f, evidences)
    (result.findings if vf.status is VERIFIED else result.rejected).append(vf)
""",
    "The validator is plain deterministic Python: no LLM is used to check the LLM.",
    ["Hallucination: B 29% -> C 6% -> D 0%.", "D F1 0.82, precision 0.78, recall 0.88.",
     "C and D share the same LLM answers (same cache), so the only difference is the validator."],
    [("What is new compared to normal RAG?",
      "Normal RAG puts documents in the prompt and trusts the answer. We also check the answer against the "
      "documents with code, and drop anything unsupported."),
     ("Why not ask a second LLM to check the first?",
      "A second LLM can also be wrong. Our checks are exact rules (ids, lines, symbols, versions), so they "
      "are repeatable and explainable."),
     ("What does the offline reasoner do?",
      "It applies fixed rules to the retrieved evidence instead of calling an LLM. It reaches F1 0.81 and "
      "lets anyone run the tool without an API key."),
     ("Why temperature 0 and a cache?",
      "To make results repeatable: the same input gives the same output, and cached calls cost nothing.")],
    "Abstract and Introduction (problem, idea, contributions, headline numbers), Method: the "
    "LLM reasoner and the citation validator, and Limitations + Conclusion.")

s += member(
    5, "Fixing, Web App and CLI",
    "turning verified findings into a fixed file, and the user-facing app, command line, tests and CI.",
    "Finding problems is only half the job; users want the corrected code. We only change code we are "
    "sure about: simple renames and moves are fixed automatically, harder cases can be rewritten by the "
    "LLM but only if the rewrite passes strict checks, and anything else gets a clear TODO comment. "
    "Users do all this from a web page or one command.",
    ["<b>Fixer</b> (fixer.py): for KB entries marked mechanical_fix, makes a unified diff for same-place "
     "renames (assertFormsetError to assertFormSetError) and module moves (django.utils.timezone.utc to "
     "datetime.timezone.utc). Every patch must still parse. Rule: <i>no patch beats a wrong patch</i>.",
     "<b>Updater</b> (updater.py + pipeline.update_files): applies safe patches bottom-up, then optionally "
     "asks the LLM to rewrite the rest. The rewrite is accepted only if it parses, stays at least 70% "
     "similar to the original, and a re-scan finds no new problems. Otherwise a "
     "<font name='Mono'># TODO(codemigrate): ...</font> comment is added (comments never change program behaviour).",
     "<b>API</b> (FastAPI): register/login with JWT, projects, scans run in a background thread pool "
     "(PENDING to RUNNING to COMPLETED or FAILED), Markdown and PDF reports.",
     "<b>Frontend</b> (React + Vite + TypeScript): Login, Dashboard (paste code or upload zip, choose versions, "
     "reasoner, retriever), Scan view with tabs Original / Updated code / Changes, History, Compare.",
     "<b>CLI</b>: <font name='Mono'>codemigrate scan ... --write-fixed DIR</font> writes fixed copies "
     "(never touches the originals).",
     "<b>Quality</b>: 53 pytest tests, 72% coverage (gate 70%), Playwright end-to-end test, GitHub Actions CI."],
    ["<font name='Mono'>src/codemigrate/patching/fixer.py</font>, <font name='Mono'>updater.py</font>",
     "<font name='Mono'>src/codemigrate/api/</font>: main.py, routes.py, auth.py, jobs.py, db.py, reports.py",
     "<font name='Mono'>frontend/src/pages/</font>: Dashboard.tsx, ScanView.tsx, History.tsx, Compare.tsx",
     "<font name='Mono'>src/codemigrate/cli.py</font>, <font name='Mono'>.github/workflows/ci.yml</font>"],
    """
# API routes (src/codemigrate/api/routes.py)
POST /auth/register   POST /auth/token   GET /auth/me
POST /projects        GET  /projects
POST /projects/{pid}/scans          (code in JSON)   -> 202, scan runs in background
POST /projects/{pid}/scans/upload   (zip file)
GET  /scans/{sid}                   findings + updated files
GET  /scans/{sid}/report.md   GET /scans/{sid}/report.pdf
GET  /results?split=test            benchmark tables for the Compare page

# Run locally (one server serves API + web app)
cd frontend; npm run build; cd ..
$env:WEB_DIR="frontend/dist"
.venv\\Scripts\\uvicorn codemigrate.api.main:app --port 8000   -> http://localhost:8000
""",
    "Use the offline reasoner in the live demo: it needs no API key and cannot run out of quota.",
    ["53 tests pass, 72% coverage.", "Scan states: PENDING, RUNNING, COMPLETED, FAILED.",
     "LLM rewrite accepted only if similarity is at least 0.7 and the re-scan is clean."],
    [("Can the automatic fix break my code?",
      "Mechanical patches only cover exact renames and moves, and every patch must parse. LLM rewrites are "
      "re-checked; if a check fails we add a TODO comment instead of changing code."),
     ("Why run scans in the background?",
      "An LLM scan can take a while. The API returns at once (202) and the page polls the status."),
     ("How are users kept apart?",
      "JWT login; every project and scan query checks the owner, so users only see their own data."),
     ("Why no Docker?",
      "It is optional (a docker-compose file exists), but the app runs directly with Python and Node, "
      "which is simpler for the demo.")],
    "System implementation (API, UI, updated-code feature, testing).")

# ---------- 9 results ----------
s += [P("10. Results everyone must know", "h2"),
      P("Test split, 160 cases. Gemini rows are one run (seed 0, temperature 0); 95% bootstrap confidence "
        "intervals in brackets.")]
s.append(table([["System", "Precision", "Recall", "F1 [95% CI]", "Made-up"],
                ["A: django-upgrade", "0.09", "0.01", "0.02 [0.00, 0.06]", "n/a"],
                ["A: pyupgrade", "0.00", "0.00", "0.00", "n/a"],
                ["B: LLM only (Gemini)", "0.68", "0.74", "0.71 [0.63, 0.78]", "29%"],
                ["C: LLM + release notes", "0.77", "0.92", "0.83 [0.77, 0.89]", "6%"],
                ["D: offline, no LLM", "0.75", "0.89", "0.81 [0.74, 0.88]", "0%"],
                ["D: full pipeline (ours)", "0.78", "0.88", "0.82 [0.75, 0.88]", "0%"]],
               [0.34, 0.13, 0.13, 0.25, 0.15], bold_last=True))
s += [Spacer(1, 6), P("Three sentences every member should be able to say:", "h3")]
s += bullets(["Existing rule tools catch almost none of these breaking changes (F1 0.02).",
              "Giving the LLM the release notes cuts made-up findings from 29% to 6%; our validator removes "
              "the rest (0%) at a small recall cost.",
              "The answer key comes from actually running the code on five Django versions, not from any tool."])
s += [P("Honest limits (say them before you are asked)", "h3")]
s += bullets(["Django only, versions 4.0 to 5.1.", "One LLM, one run, because of the free-tier quota.",
              "Benchmark cases are small files, not whole projects.",
              "Published numbers from other papers are on different tasks, so we compare head-to-head only "
              "with django-upgrade and pyupgrade, plus our own ablations."])
s.append(PageBreak())

# ---------- 10 paper ----------
s += [P("11. Paper plan and timeline", "h2"),
      P("The LaTeX template is in <font name='Mono'>paper/main.tex</font> (IEEE format) with a FACTS note "
        "in each section; tables and figures are already linked from <font name='Mono'>results/</font>. "
        "References are in <font name='Mono'>paper/refs.bib</font>. "
        "<font name='Mono'>paper/WRITING_PLAN.md</font> gives one cue per sentence.")]
s.append(table([["Section", "Writer", "Build it from"],
                ["Abstract, Introduction", M[4], "Problem + goal, contributions, headline numbers"],
                ["Related Work", M[1], "docs/RELATED_WORK.md (read each paper first)"],
                ["Knowledge Base", M[1], "kb/ code, build_report.json"],
                ["Method: analysis + retrieval", M[3], "analysis/, retrieval/"],
                ["Method: reasoner + validator", M[4], "llm/, validation/, pipeline.py"],
                ["Benchmark", M[2], "benchmark/README.md, Table dataset"],
                ["Experiments + Results", M[2], "results/tables, results/figures, error_cases.md"],
                ["System implementation", M[3], "api/, frontend/, patching/"],
                ["Limitations, Conclusion", M[4], "Limits list above"],
                ["Merge in Overleaf", M[2], "everyone's sections"],
                ["AI + plagiarism reports", M[4], "the compiled PDF"],
                ["Final read-through", LEAD, "the merged draft"]], [0.3, 0.2, 0.5]))
s += [P("Rules for writing", "h3")]
s += bullets(["Write in your own words from the code and results. Do not paste from this guide, the "
              "slides, papers or any AI tool, and do not use paraphrasing tools (they get flagged as AI).",
              "Cite only papers you have read. Check each BibTeX entry on the publisher page.",
              "Run your similarity and AI checks per section early, not just at the end.",
              "Every number in the paper must match results/tables. Ask for a fact-check of each draft."])
s += [P("Suggested timeline", "h3")]
s.append(table([["When", "What"],
                ["Days 1-2", "Each member reads their files and this guide; practise explaining your part in 2 minutes."],
                ["Days 3-4", "Rehearse the review talk and live demo once together; record a backup demo video."],
                ["Days 5-8", "Each member drafts their paper section."],
                ["Days 9-10", "Merge in Overleaf; fact-check numbers; run similarity and AI checks."],
                ["Day 11+", "Fix, final read-through, fill author names, submit."]], [0.2, 0.8]))

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                        bottomMargin=18 * mm, title="CodeMigrate Team Guide",
                        author=f"CodeMigrate team (lead: {LEAD})")
doc.build(s, onFirstPage=footer, onLaterPages=footer)
print("wrote", OUT)
