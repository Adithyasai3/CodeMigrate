"""Hybrid retrieval with reciprocal rank fusion (RRF) of several retrievers."""

from __future__ import annotations

from codemigrate.kb.schema import KBEntry
from codemigrate.retrieval.base import Retriever
from codemigrate.schemas import CodeRef


class HybridRetriever(Retriever):
    """score(d) = sum_r w_r / (k_rrf + rank_r(d)) over each retriever's top ``depth`` list."""

    name = "hybrid"

    def __init__(
        self,
        entries: list[KBEntry],
        retrievers: list[Retriever],
        weights: dict[str, float] | None = None,
        k_rrf: int = 60,
        depth: int = 20,
    ) -> None:
        super().__init__(entries)
        self.retrievers = retrievers
        self.weights = weights or {}
        self.k_rrf = k_rrf
        self.depth = depth

    def score_all(self, ref: CodeRef | str) -> list[float]:
        fused = [0.0] * len(self.entries)
        for r in self.retrievers:
            scores = r.score_all(ref)
            order = sorted((i for i, s in enumerate(scores) if s > 0), key=lambda i: -scores[i])
            w = self.weights.get(r.name, 1.0)
            for rank, i in enumerate(order[: self.depth], 1):
                fused[i] += w / (self.k_rrf + rank)
        return fused
