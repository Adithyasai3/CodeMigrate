"""Pydantic schema for knowledge-base entries describing API changes."""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ChangeType(StrEnum):
    REMOVED = "removed"
    DEPRECATED = "deprecated"
    BEHAVIOR_CHANGED = "behavior_changed"
    RENAMED = "renamed"


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Provenance(StrEnum):
    AUTO_PARSED = "auto_parsed"
    MANUALLY_CORRECTED = "manually_corrected"
    MANUAL = "manual"


class KBEntry(BaseModel):
    """One documented API change, always traceable to an official release-note section."""

    id: str = Field(pattern=r"^[a-z0-9_.\-]+$")
    library: str
    version_introduced: str = Field(pattern=r"^\d+\.\d+(\.\d+)?$")
    change_type: ChangeType
    affected_api: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    description: str = Field(min_length=10)
    replacement: str | None = None
    source_url: HttpUrl
    source_section: str
    severity: Severity
    provenance: Provenance = Provenance.AUTO_PARSED
    mechanical_fix: bool = False
    symbol_kind: str = "python"  # python | setting | template | other

    @field_validator("source_url")
    @classmethod
    def _official_docs(cls, v: HttpUrl) -> HttpUrl:
        if v.host not in {"docs.djangoproject.com"} and not str(v).startswith("https://"):
            raise ValueError(f"source_url must be an official https docs URL, got {v}")
        return v

    def all_names(self) -> set[str]:
        """Affected API plus aliases, used by exact matching and by the validator."""
        return {self.affected_api, *self.aliases}

    def search_text(self) -> str:
        """Text indexed by BM25/dense retrievers."""
        return " ".join(
            [
                self.affected_api,
                " ".join(self.aliases),
                self.change_type.value,
                self.description,
                self.replacement or "",
            ]
        )


def load_kb(path: Path) -> list[KBEntry]:
    """Load and validate a JSONL knowledge base."""
    entries = []
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if line.strip():
                try:
                    entries.append(KBEntry.model_validate_json(line))
                except Exception as exc:
                    raise ValueError(f"{path}:{lineno}: invalid KB entry: {exc}") from exc
    return entries


def save_kb(entries: list[KBEntry], path: Path) -> None:
    """Write entries as JSONL, sorted by id for stable diffs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for e in sorted(entries, key=lambda e: e.id):
            fh.write(json.dumps(e.model_dump(mode="json"), ensure_ascii=False) + "\n")
