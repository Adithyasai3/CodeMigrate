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


if __name__ == "__main__":
    app()
