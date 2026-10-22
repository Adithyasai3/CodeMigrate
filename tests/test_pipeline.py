import json
from pathlib import Path

from typer.testing import CliRunner

from codemigrate.cli import app
from codemigrate.pipeline import Pipeline, SystemConfig

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample_project"


def test_offline_pipeline_on_sample_project():
    cfg = SystemConfig(retriever="exact", provider="offline")
    res = Pipeline(cfg).scan_path(SAMPLE, "4.0", "5.1")
    found = {(f.file, f.line) for f in res.findings}
    assert ("settings.py", 3) in found  # USE_L10N
    assert ("shop/models.py", 10) in found  # index_together
    assert ("shop/views.py", 3) in found  # utc import
    assert all(f.status.value == "VERIFIED" and f.source_urls for f in res.findings)
    assert res.rejected == []


def test_version_range_restricts_findings():
    res = Pipeline(SystemConfig(retriever="exact")).scan_path(SAMPLE, "5.1", "5.2")
    assert res.findings == []


def test_llm_only_offline_returns_nothing():
    cfg = SystemConfig(name="B", use_retrieval=False, provider="offline")
    assert Pipeline(cfg).scan_path(SAMPLE, "4.0", "5.1").findings == []


def test_cli_scan_json():
    args = ["scan", str(SAMPLE), "--from", "4.0", "--to", "5.1", "--retriever", "exact", "--json"]
    r = CliRunner().invoke(app, args)
    assert r.exit_code == 0, r.output
    data = json.loads(r.output[r.output.index("{") :])
    assert data["files_scanned"] == 6 and len(data["findings"]) >= 8


def test_cli_kb_stats():
    r = CliRunner().invoke(app, ["kb", "stats"])
    assert r.exit_code == 0 and "total" in r.output
