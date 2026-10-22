"""Exact symbol matching against KB affected_api and aliases."""

from __future__ import annotations

from collections import defaultdict

from codemigrate.kb.schema import KBEntry
from codemigrate.retrieval.base import Retriever
from codemigrate.schemas import CodeRef


def method_names(entries: list[KBEntry]) -> set[str]:
    """Distinctive member names of classes in the KB (the ``method`` of ``Class.method``)."""
    out = set()
    for e in entries:
        if e.symbol_kind != "python":
            continue
        for name in e.all_names():
            parts = name.split(".")
            if len(parts) >= 2 and parts[-2][:1].isupper() and not parts[-1][:1].isupper():
                out.add(parts[-1])
    return out


def template_names(entries: list[KBEntry]) -> set[str]:
    """Template tag/filter names in the KB."""
    return {
        e.affected_api.split(":", 1)[1] for e in entries if e.affected_api.startswith("template:")
    }


class ExactRetriever(Retriever):
    """Exact name match = 1.0; longest module/class prefix match = 0.8;
    member-name match for an unresolved receiver (``*.name``) = 0.6;
    member-name match for an inherited member on a subclass path = 0.5."""

    name = "exact"

    def __init__(self, entries: list[KBEntry]) -> None:
        super().__init__(entries)
        self.by_name: dict[str, set[int]] = defaultdict(set)
        self.by_member: dict[str, set[int]] = defaultdict(set)
        for i, e in enumerate(entries):
            for n in e.all_names():
                self.by_name[n].add(i)
                parts = n.split(".")
                if len(parts) >= 2 and parts[-2][:1].isupper():
                    self.by_member[parts[-1]].add(i)

    def score_all(self, ref: CodeRef | str) -> list[float]:
        symbol = ref.symbol if isinstance(ref, CodeRef) else ref.strip()
        scores = [0.0] * len(self.entries)
        if symbol.startswith("*."):
            for i in self.by_member.get(symbol[2:], ()):
                scores[i] = 0.6
            return scores
        for i in self.by_name.get(symbol, ()):
            scores[i] = 1.0
        # Longest prefix: "django.utils.timezone.utc.tzname" -> "django.utils.timezone.utc".
        parts = symbol.split(".")
        for cut in range(len(parts) - 1, 1, -1):
            hits = self.by_name.get(".".join(parts[:cut]), ())
            for i in hits:
                scores[i] = max(scores[i], 0.8)
            if hits:
                break
        # Inherited member via a subclass path (django.test.TestCase.assertFormsetError is
        # defined on SimpleTestCase): fall back to the member name.
        if not any(scores) and len(parts) >= 2 and parts[-2][:1].isupper():
            for i in self.by_member.get(parts[-1], ()):
                scores[i] = 0.5
        return scores
