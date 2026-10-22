"""Common retriever interface and query construction."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from codemigrate.kb.schema import KBEntry
from codemigrate.kb.versions import in_range
from codemigrate.schemas import CodeRef, ScoredEntry

_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def tokenize(text: str) -> list[str]:
    """Lowercase tokens; splits dotted paths, snake_case and CamelCase but keeps the pieces."""
    out: list[str] = []
    for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text):
        out.append(tok.lower())
        parts = [p for p in tok.split("_") if p]
        sub = [w.lower() for p in parts for w in _CAMEL.split(p) if w]
        if len(sub) > 1:
            out.extend(sub)
    return out


def ref_query_text(ref: CodeRef | str) -> str:
    """Text used by lexical/dense retrievers for a code reference."""
    if isinstance(ref, str):
        return ref
    symbol = ref.symbol.replace("*.", "")
    return f"{symbol} {symbol.replace('.', ' ')} {ref.raw_text}"


class Retriever(ABC):
    """Scores KB entries for a code reference; version filtering is applied uniformly."""

    name = "base"

    def __init__(self, entries: list[KBEntry]) -> None:
        self.entries = entries

    @abstractmethod
    def score_all(self, ref: CodeRef | str) -> list[float]:
        """Return one score per entry (same order as ``self.entries``); 0 means no match."""

    def search(
        self,
        ref: CodeRef | str,
        k: int = 5,
        from_version: str | None = None,
        to_version: str | None = None,
    ) -> list[ScoredEntry]:
        """Top-k entries with score > 0, restricted to from_version < v <= to_version."""
        scores = self.score_all(ref)
        ranked = []
        for entry, score in zip(self.entries, scores, strict=True):
            if score <= 0:
                continue
            if (
                from_version
                and to_version
                and not in_range(entry.version_introduced, from_version, to_version)
            ):
                continue
            ranked.append(ScoredEntry(entry=entry, score=float(score), retriever=self.name))
        ranked.sort(key=lambda s: (-s.score, s.entry.id))
        return ranked[:k]
