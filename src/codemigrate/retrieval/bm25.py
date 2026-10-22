"""BM25 retrieval over entry text."""

from __future__ import annotations

from rank_bm25 import BM25Okapi

from codemigrate.kb.schema import KBEntry
from codemigrate.retrieval.base import Retriever, ref_query_text, tokenize
from codemigrate.schemas import CodeRef


class BM25Retriever(Retriever):
    name = "bm25"

    def __init__(self, entries: list[KBEntry]) -> None:
        super().__init__(entries)
        self.bm25 = BM25Okapi([tokenize(e.search_text()) for e in entries])

    def score_all(self, ref: CodeRef | str) -> list[float]:
        return [float(s) for s in self.bm25.get_scores(tokenize(ref_query_text(ref)))]
