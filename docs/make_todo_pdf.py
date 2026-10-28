"""Build docs/CodeMigrate_Remaining_Work.pdf: the team's remaining tasks on 1-2 pages.

  python docs/make_todo_pdf.py
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = str(Path(__file__).resolve().parent / "CodeMigrate_Remaining_Work.pdf")
F = "C:/Windows/Fonts/"
pdfmetrics.registerFont(TTFont("Body", F + "segoeui.ttf"))
pdfmetrics.registerFont(TTFont("Body-Bold", F + "segoeuib.ttf"))
pdfmetrics.registerFont(TTFont("Mono", F + "consola.ttf"))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body", boldItalic="Body-Bold")

NAVY = colors.HexColor("#14213D")
ORANGE = colors.HexColor("#B5561C")
CARD = colors.HexColor("#F1F3F7")
LINE = colors.HexColor("#DCDFE5")
PEACH = colors.HexColor("#FDF0E6")
W = A4[0] - 32 * mm

st = {
    "h1": ParagraphStyle("h1", fontName="Body-Bold", fontSize=19, leading=23, textColor=NAVY),
    "sub": ParagraphStyle("sub", fontName="Body", fontSize=9.5, leading=13, textColor=colors.HexColor("#4A5568")),
    "h2": ParagraphStyle("h2", fontName="Body-Bold", fontSize=12.5, leading=16, textColor=ORANGE,
                         spaceBefore=8, spaceAfter=4),
    "p": ParagraphStyle("p", fontName="Body", fontSize=9.5, leading=13),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=8.8, leading=11.5),
    "cellb": ParagraphStyle("cellb", fontName="Body-Bold", fontSize=8.8, leading=11.5, textColor=colors.white),
    "bl": ParagraphStyle("bl", fontName="Body", fontSize=9.5, leading=13, leftIndent=12, bulletIndent=2,
                         spaceAfter=1.5),
}


def P(t, s="p"):
    return Paragraph(t, st[s])


def bullets(items):
    return [Paragraph(t, st["bl"], bulletText="•") for t in items]


def table(rows, widths):
    data = [[Paragraph(c, st["cellb"]) for c in rows[0]]] + [[Paragraph(c, st["cell"]) for c in r]
                                                            for r in rows[1:]]
    t = Table(data, colWidths=[W * w for w in widths], repeatRows=1)
    style = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.4, LINE),
             ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3.5),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5)]
    style += [("BACKGROUND", (0, i), (-1, i), CARD) for i in range(2, len(data), 2)]
    t.setStyle(TableStyle(style))
    return t


def note(text):
    t = Table([[P(text)]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PEACH), ("BOX", (0, 0), (-1, -1), 0.6, ORANGE),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 5),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return t


def M(path):
    return f"<font name='Mono'>{path}</font>"


s = [P("CodeMigrate: Remaining Work", "h1"),
     P("For Prabhas, Sandhani, Dhanush and Hemanth. The code, results, slides and guides are ready. "
       "This page lists what is left."),
     Spacer(1, 6),
     note("<b>Read first:</b> " + M("docs/CodeMigrate_Team_Guide.pdf") + " (your part's pages have a simple "
          "explanation, a code walkthrough, numbers to remember and likely questions with answers). "
          "<b>Paper help:</b> " + M("paper/WRITING_PLAN.md") + " gives one cue per sentence."),
     P("1. Your tasks", "h2")]

s.append(table([
    ["Name", "Learn + explain in review", "Code to open if mam asks", "Write in paper"],
    ["<b>Prabhas</b>", "Gemini reasoner + citation validator (main novelty); the novelty table "
     "(" + M("docs/CodeMigrate_Novelty.pdf") + ")",
     M("llm/reasoner.py") + ", " + M("llm/prompts.py") + ", " + M("validation/citation_validator.py"),
     "Abstract, Introduction, Related Work, Method: validator"],
    ["<b>Sandhani</b>", "Code analysis + retrieval; benchmark, metrics and results",
     M("analysis/ast_analyzer.py") + ", " + M("retrieval/hybrid.py") + ", " + M("evaluation/metrics.py"),
     "Method: analysis + retrieval, Benchmark, Results"],
    ["<b>Dhanush</b>", "Knowledge base (310 Django changes from release notes)",
     M("kb/schema.py") + ", " + M("data/kb/django_changes.jsonl"), "Knowledge Base, Conclusion"],
    ["<b>Hemanth</b>", "Web app, CLI, fixer; <b>runs the live demo</b>",
     M("api/routes.py") + ", " + M("cli.py") + ", " + M("patching/fixer.py"),
     "System implementation, Limitations"],
], [0.12, 0.3, 0.33, 0.25]))
s.append(P("All code paths are inside " + M("src/codemigrate/") + ".", "sub"))

s.append(P("2. Work we do together", "h2"))
s.append(table([
    ["Task", "Owner", "Done when"],
    ["Learn your part and practise explaining it in 2 minutes", "Everyone",
     "You can explain your code files without reading"],
    ["Write your paper section in your own words", "Everyone", "Section sent to Sandhani"],
    ["Merge all sections in Overleaf and compile the PDF", "Sandhani", "One IEEE PDF with all sections"],
    ["Add all names in the author line", "Sandhani", "Names + college in the PDF"],
    ["Run the AI-content and plagiarism checks", "Hemanth", "Both reports under 10%, saved as PDF"],
    ["Rewrite any part the checks flag", "Owner of that section", "Re-check passes"],
    ["Practise the full talk + live demo once together", "Everyone", "12 minutes, no stops"],
    ["Record a backup demo video", "Hemanth", "Video on the laptop in case the live demo fails"],
], [0.5, 0.2, 0.3]))

s.append(P("3. Order of work", "h2"))
s.append(table([
    ["Step", "What"],
    ["Day 1", "Everyone reads their part in the team guide and opens their code files."],
    ["Day 2-3", "Everyone writes their paper section. Send it to Sandhani."],
    ["Day 4", "Sandhani merges in Overleaf. Hemanth runs both checks. Fix anything flagged."],
    ["Day 5", "Full practice of talk + demo together. Hemanth records the backup video."],
], [0.15, 0.85]))

s.append(P("4. Paper rules (must follow)", "h2"))
s += bullets(["Write in <b>your own words</b>. No ChatGPT or other AI tools, and no paraphrasing tools: "
              "AI content must be under 10%.",
              "Do not copy from the team guide, slides, papers or websites: similarity must be under 10%.",
              "Use the numbers exactly as in " + M("results/tables/") + " and the FACTS notes in "
              + M("paper/main.tex") + ". Tables, figures and references are already in the template.",
              "Simple, short sentences are fine. It is a draft."])

s.append(P("5. Run the demo (Hemanth)", "h2"))
s += bullets(["Build the web app once: " + M("cd frontend; npm run build; cd .."),
              "Start: " + M('$env:WEB_DIR="frontend/dist"; .venv\\Scripts\\uvicorn codemigrate.api.main:app '
                            '--port 8000'),
              "Open " + M("http://localhost:8000") + ", register, create a project, versions 4.0 to 5.1, "
              "reasoner <b>offline</b>, tab Paste code, paste the demo code, click Scan.",
              "Show the findings, a source link, and the Updated code tab. Full steps and the code to "
              "paste: " + M("docs/DEMO_SCRIPT.md") + "."])

s.append(P("6. Bring to the review", "h2"))
s += bullets(["Laptop with the demo working + backup video",
              "Slides (" + M("docs/CodeMigrate_Review.pptx") + ") and novelty PDF",
              "Paper PDF + AI-content report + plagiarism report"])


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Body", 8)
    canvas.setFillColor(colors.HexColor("#4A5568"))
    canvas.drawString(16 * mm, 9 * mm, "CodeMigrate · remaining work")
    canvas.drawRightString(A4[0] - 16 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


SimpleDocTemplate(OUT, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm,
                  bottomMargin=16 * mm, title="CodeMigrate Remaining Work").build(s, onFirstPage=footer,
                                                                                  onLaterPages=footer)
print("wrote", OUT)
