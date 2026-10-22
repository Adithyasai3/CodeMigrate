"""Dense retrieval: sentence-transformer (or TF-IDF) embeddings + FAISS inner-product index."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import faiss
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from codemigrate.config import get_settings
from codemigrate.kb.schema import KBEntry
from codemigrate.retrieval.base import Retriever, ref_query_text, tokenize
from codemigrate.schemas import CodeRef

log = logging.getLogger(__name__)


class SentenceTransformerEmbedder:
    """Normalized sentence-transformer embeddings with an on-disk cache for the KB matrix."""

    def __init__(self, model_name: str | None = None) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name or get_settings().embedding_model
        self.model = SentenceTransformer(self.model_name, device="cpu")
        self.cache_dir = get_settings().repo_root / ".cache" / "embeddings"
        self._query_cache: dict[str, np.ndarray] = {}

    def fit(self, texts: list[str]) -> np.ndarray:
        key = hashlib.sha256(("\n".join(texts) + self.model_name).encode()).hexdigest()[:16]
        path: Path = self.cache_dir / f"{key}.npy"
        if path.exists():
            return np.load(path)
        vecs = self.encode(texts)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        np.save(path, vecs)
        return vecs

    def encode(self, texts: list[str]) -> np.ndarray:
        if len(texts) == 1 and texts[0] in self._query_cache:
            return self._query_cache[texts[0]]
        vecs = np.asarray(
            self.model.encode(
                texts, normalize_embeddings=True, batch_size=64, show_progress_bar=False
            ),
            dtype="float32",
        )
        if len(texts) == 1:
            self._query_cache[texts[0]] = vecs
        return vecs


class TfidfEmbedder:
    """TF-IDF vectors (L2-normalized) as a lightweight 'dense' baseline for ablations."""

    model_name = "tfidf"

    def __init__(self) -> None:
        self.vec = TfidfVectorizer(
            tokenizer=tokenize, lowercase=False, token_pattern=None, sublinear_tf=True
        )

    def fit(self, texts: list[str]) -> np.ndarray:
        return self.vec.fit_transform(texts).toarray().astype("float32")

    def encode(self, texts: list[str]) -> np.ndarray:
        return self.vec.transform(texts).toarray().astype("float32")


class DenseRetriever(Retriever):
    name = "dense"

    def __init__(self, entries: list[KBEntry], embedder=None) -> None:
        super().__init__(entries)
        self.embedder = embedder or SentenceTransformerEmbedder()
        if isinstance(self.embedder, TfidfEmbedder):
            self.name = "tfidf"
        vecs = self.embedder.fit([e.search_text() for e in entries])
        self.index = faiss.IndexFlatIP(vecs.shape[1])
        self.index.add(vecs)

    def score_all(self, ref: CodeRef | str) -> list[float]:
        q = self.embedder.encode([ref_query_text(ref)])
        sims, idx = self.index.search(q, len(self.entries))
        scores = [0.0] * len(self.entries)
        for s, i in zip(sims[0], idx[0], strict=True):
            if s > 0:  # cosine similarity; non-positive means unrelated
                scores[int(i)] = float(s)
        return scores
