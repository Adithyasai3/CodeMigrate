"""Version helpers and the data-driven list of release-note sources."""

from __future__ import annotations

from pathlib import Path

import yaml
from packaging.version import Version

from codemigrate.config import REPO_ROOT

SOURCES_FILE = REPO_ROOT / "data" / "kb" / "sources.yaml"


def parse_version(v: str) -> Version:
    """Parse a version string like '5.1'."""
    return Version(v)


def in_range(version: str, from_version: str, to_version: str) -> bool:
    """True if from_version < version <= to_version (the changes you cross when upgrading)."""
    return parse_version(from_version) < parse_version(version) <= parse_version(to_version)


def load_sources(path: Path = SOURCES_FILE) -> dict:
    """Load the per-library source configuration (release-note URLs, pinned commit)."""
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def supported_versions(library: str = "django", path: Path = SOURCES_FILE) -> list[str]:
    """Versions for which release notes are configured."""
    return [str(v["version"]) for v in load_sources(path)["libraries"][library]["versions"]]
