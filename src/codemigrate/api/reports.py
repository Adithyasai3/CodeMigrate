"""Scan report export: Markdown and PDF."""

from __future__ import annotations

import io

from codemigrate.api.models import Scan


def to_markdown(scan: Scan, result: dict) -> str:
    lines = [f"# CodeMigrate report — scan #{scan.id}", "",
             f"* Source: {scan.source_name}",
             f"* Upgrade: Django {scan.from_version} → {scan.to_version}",
             f"* Reasoner: {scan.provider}; retriever: {scan.retriever}",
             f"* Files scanned: {result.get('files_scanned', 0)}; findings: "
             f"{len(result.get('findings', []))}; rejected claims: "
             f"{len(result.get('rejected', []))}", ""]
    if not result.get("findings"):
        lines.append("No verified breaking changes were found.")
    for i, f in enumerate(result.get("findings", []), 1):
        lines += [f"## {i}. `{f['file']}:{f['line']}` — `{f['symbol']}`", "",
                  f"**Status:** {f['status']}  ", f"**Change:** {f.get('change_type') or '-'}", "",
                  f.get("explanation") or "", ""]
        if f.get("suggested_fix"):
            lines += [f"**Fix:** {f['suggested_fix']}", ""]
        for url, cid in zip(f.get("source_urls", []), f.get("cited_ids", []), strict=False):
            lines.append(f"* Evidence: [{cid}]({url})")
        if f.get("patch"):
            lines += ["", "```diff", f["patch"].rstrip(), "```"]
        lines.append("")
    for u in result.get("updated_files") or []:
        lines += [f"## Updated `{u['path']}`", "",
                  f"{len(u['auto_fixed'])} fixed automatically, {len(u['llm_fixed'])} fixed by "
                  f"the LLM (re-checked), {len(u['manual'])} left as `TODO(codemigrate)` notes.",
                  "", "```python", u["content"].rstrip(), "```", ""]
    if result.get("file_errors"):
        lines += ["## Files that could not be analyzed", ""]
        lines += [f"* `{p}`: {e}" for p, e in result["file_errors"].items()]
    return "\n".join(lines) + "\n"


def to_pdf(scan: Scan, result: dict) -> bytes:
    from xml.sax.saxutils import escape

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f"CodeMigrate scan {scan.id}")
    styles = getSampleStyleSheet()
    story = [Paragraph(f"CodeMigrate report — scan #{scan.id}", styles["Title"]),
             Paragraph(escape(f"Django {scan.from_version} -> {scan.to_version} | "
                              f"{scan.source_name} | reasoner {scan.provider}"), styles["Normal"]),
             Spacer(1, 12)]
    findings = result.get("findings", [])
    if not findings:
        story.append(Paragraph("No verified breaking changes were found.", styles["Normal"]))
    for i, f in enumerate(findings, 1):
        story.append(Paragraph(escape(f"{i}. {f['file']}:{f['line']} — {f['symbol']} "
                                      f"[{f['status']}]"), styles["Heading3"]))
        story.append(Paragraph(escape(f.get("explanation") or ""), styles["Normal"]))
        if f.get("suggested_fix"):
            story.append(Paragraph(escape("Fix: " + f["suggested_fix"]), styles["Normal"]))
        for url in f.get("source_urls", []):
            story.append(Paragraph(f'<link href="{escape(url)}">{escape(url)}</link>',
                                   styles["Normal"]))
        if f.get("patch"):
            story.append(Preformatted(f["patch"], styles["Code"]))
        story.append(Spacer(1, 8))
    for u in result.get("updated_files") or []:
        story.append(Paragraph(escape(f"Updated {u['path']}"), styles["Heading2"]))
        story.append(Preformatted(u["content"], styles["Code"]))
    doc.build(story)
    return buf.getvalue()
