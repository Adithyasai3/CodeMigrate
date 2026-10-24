"""Command-line interface: ``codemigrate kb ...``, ``codemigrate scan ...``."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import typer

from codemigrate.config import get_settings

app = typer.Typer(
    help="CodeMigrate: evidence-grounded Django upgrade checker.", no_args_is_help=True
)
kb_app = typer.Typer(help="Knowledge-base commands.", no_args_is_help=True)
app.add_typer(kb_app, name="kb")


@kb_app.command("build")
def kb_build(
    refresh: bool = typer.Option(False, help="Re-download release notes."),
    check_urls: bool = typer.Option(True, help="Verify source_url anchors online."),
) -> None:
    """Parse official release notes into data/kb/django_changes.jsonl."""
    from codemigrate.kb.build_kb import build

    report = build(refresh=refresh, check_urls=check_urls)
    typer.echo(json.dumps({k: v for k, v in report.items() if k != "skipped_examples"}, indent=2))


@kb_app.command("stats")
def kb_stats(path: Path = typer.Option(None, help="KB jsonl path.")) -> None:
    """Print entry counts per version and change type."""
    from codemigrate.kb.schema import load_kb

    entries = load_kb(path or get_settings().kb_path)
    versions = sorted(
        {e.version_introduced for e in entries}, key=lambda v: tuple(map(int, v.split(".")))
    )
    types = sorted({e.change_type.value for e in entries})
    counts = Counter((e.version_introduced, e.change_type.value) for e in entries)
    header = f"{'version':<8}" + "".join(f"{t:>18}" for t in types) + f"{'total':>8}"
    typer.echo(header)
    for v in versions:
        row = [counts[(v, t)] for t in types]
        typer.echo(f"{v:<8}" + "".join(f"{c:>18}" for c in row) + f"{sum(row):>8}")
    totals = [sum(counts[(v, t)] for v in versions) for t in types]
    typer.echo(f"{'total':<8}" + "".join(f"{c:>18}" for c in totals) + f"{len(entries):>8}")
    prov = Counter(e.provenance.value for e in entries)
    kinds = Counter(e.symbol_kind for e in entries)
    typer.echo(f"provenance: {dict(prov)}")
    typer.echo(f"symbol kinds: {dict(kinds)}")
    typer.echo(f"mechanical fixes: {sum(e.mechanical_fix for e in entries)}")


@app.command("scan")
def scan(
    path: Path = typer.Argument(..., exists=True, help="Directory, .py file or .zip"),
    from_version: str = typer.Option("4.0", "--from"),
    to_version: str = typer.Option("5.1", "--to"),
    provider: str = typer.Option(None, help="offline | gemini | anthropic | openai"),
    retriever: str = typer.Option("hybrid"),
    top_k: int = typer.Option(5),
    no_validator: bool = typer.Option(False, help="Report unvalidated claims (ablation)."),
    as_json: bool = typer.Option(False, "--json", help="Print the full result as JSON."),
    show_rejected: bool = typer.Option(False, help="Also list rejected claims."),
    write_fixed: Path = typer.Option(
        None, help="Write the updated files into this directory (inputs are never modified)."
    ),
) -> None:
    """Scan code for breaking Django API changes between two versions."""
    import os

    from codemigrate.pipeline import Pipeline, SystemConfig

    provider = provider or os.getenv("LLM_PROVIDER", "offline")
    cfg = SystemConfig(
        name=f"cli-{provider}",
        retriever=retriever,
        top_k=top_k,
        use_validator=not no_validator,
        provider=provider,
        make_updated=write_fixed is not None,
        llm_fixes=write_fixed is not None and provider != "offline",
    )
    result = Pipeline(cfg).scan_path(path, from_version, to_version)
    if as_json:
        typer.echo(result.model_dump_json(indent=2))
        return
    typer.echo(
        f"Django {from_version} -> {to_version}: {len(result.findings)} finding(s) in "
        f"{result.files_scanned} file(s) [{provider}, {retriever}, k={top_k}]"
    )
    for f in result.findings:
        typer.secho(f"\n{f.file}:{f.line}  {f.symbol}  [{f.status.value}]", bold=True)
        typer.echo(f"  {f.explanation}")
        if f.suggested_fix:
            typer.echo(f"  fix: {f.suggested_fix}")
        for url in f.source_urls:
            typer.echo(f"  source: {url}  ({', '.join(f.cited_ids)})")
        if f.patch:
            typer.echo("  patch:\n" + "\n".join("    " + ln for ln in f.patch.splitlines()))
    if show_rejected and result.rejected:
        typer.secho(f"\n{len(result.rejected)} rejected claim(s):", fg="yellow")
        for r in result.rejected:
            typer.echo(f"  {r.file}:{r.line} {r.symbol} [{r.status.value}] {r.reject_reason}")
    for p_, err in result.file_errors.items():
        typer.secho(f"skipped {p_}: {err}", fg="red")
    for u in result.updated_files:
        out = write_fixed / u.path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(u.content, encoding="utf-8")
        typer.secho(
            f"\nwrote {out}: {len(u.auto_fixed)} auto-fixed, {len(u.llm_fixed)} fixed by LLM "
            f"(verified), {len(u.manual)} marked TODO",
            fg="green",
        )


@app.command("llm-check")
def llm_check(provider: str = typer.Option("gemini")) -> None:
    """Send one tiny request to verify a provider key/model works (counts toward the cap)."""
    from codemigrate.llm import available_providers, get_client

    typer.echo(f"providers with keys: {available_providers()}")
    client = get_client(provider)
    resp = client.complete("Reply with JSON.", 'Return {"ok": true}', json_mode=True)
    typer.echo(f"{provider}/{client.model}: {resp.text.strip()[:200]} (cached={resp.cached})")


if __name__ == "__main__":
    app()
