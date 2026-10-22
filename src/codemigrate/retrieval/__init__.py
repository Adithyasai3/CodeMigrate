"""Retrievers over the knowledge base. Use :func:`build_retriever` to get one by name."""

from __future__ import annotations

from codemigrate.kb.schema import KBEntry
from codemigrate.retrieval.base import Retriever

RETRIEVER_NAMES = ("exact", "bm25", "dense", "tfidf", "hybrid", "hybrid_tfidf")


def build_retriever(name: str, entries: list[KBEntry]) -> Retriever:
    """Construct a retriever: exact | bm25 | dense | tfidf | hybrid | hybrid_tfidf."""
    from codemigrate.retrieval.bm25 import BM25Retriever
    from codemigrate.retrieval.dense import DenseRetriever, TfidfEmbedder
    from codemigrate.retrieval.exact import ExactRetriever
    from codemigrate.retrieval.hybrid import HybridRetriever

    if name == "exact":
        return ExactRetriever(entries)
    if name == "bm25":
        return BM25Retriever(entries)
    if name == "dense":
        return DenseRetriever(entries)
    if name == "tfidf":
        return DenseRetriever(entries, TfidfEmbedder())
    if name in {"hybrid", "hybrid_tfidf"}:
        dense = DenseRetriever(entries, TfidfEmbedder() if name == "hybrid_tfidf" else None)
        retr = HybridRetriever(entries, [ExactRetriever(entries), BM25Retriever(entries), dense])
        retr.name = name
        return retr
    raise ValueError(f"unknown retriever {name!r}; choose from {RETRIEVER_NAMES}")
