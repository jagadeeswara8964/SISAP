"""FAISS vector store for standard embeddings.

The index is persisted under ``data/embeddings`` (index file + id mapping +
backend metadata) so the API can start without re-encoding the catalogue.
Because vectors are L2-normalised, an inner-product index equals cosine
similarity. The store is intentionally narrow so it can later be backed by
pgvector with the same interface.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

from config import settings
from utils import get_logger

logger = get_logger("vector_store")


@dataclass
class SearchHit:
    standard_id: str
    score: float
    rank: int


class VectorStore:
    """Thin wrapper around a FAISS inner-product index."""

    def __init__(self, index_dir: Path | None = None) -> None:
        self.index_dir = Path(index_dir or settings.index_dir)
        self.index_path = self.index_dir / "standards.faiss"
        self.ids_path = self.index_dir / "standards_ids.json"
        self.meta_path = self.index_dir / "standards_meta.json"
        self._index = None
        self._ids: list[str] = []
        self._meta: dict = {}
        self._lock = threading.Lock()

    # -- persistence --------------------------------------------------------
    @property
    def is_ready(self) -> bool:
        return self._index is not None and len(self._ids) > 0

    def exists_on_disk(self) -> bool:
        return self.index_path.exists() and self.ids_path.exists()

    def build(self, vectors: np.ndarray, ids: Sequence[str], meta: dict | None = None) -> None:
        import faiss

        vectors = np.ascontiguousarray(vectors, dtype="float32")
        if vectors.ndim != 2:
            raise ValueError("vectors must be a 2-D array")
        if vectors.shape[0] != len(ids):
            raise ValueError("vector count must match id count")
        if vectors.shape[0] == 0:
            raise ValueError("cannot build an empty index")

        dimension = vectors.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(vectors)

        with self._lock:
            self._index = index
            self._ids = list(ids)
            self._meta = meta or {}

        self.index_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, str(self.index_path))
        self.ids_path.write_text(json.dumps(list(ids), ensure_ascii=False), encoding="utf-8")
        self.meta_path.write_text(json.dumps(self._meta, indent=2), encoding="utf-8")
        logger.info("faiss index built: %d vectors, dim=%d", len(ids), dimension)

    def load(self) -> bool:
        if not self.exists_on_disk():
            return False
        try:
            import faiss

            index = faiss.read_index(str(self.index_path))
            ids = json.loads(self.ids_path.read_text(encoding="utf-8"))
            meta = {}
            if self.meta_path.exists():
                meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
            with self._lock:
                self._index = index
                self._ids = ids
                self._meta = meta
            logger.info("faiss index loaded: %d vectors", len(ids))
            return True
        except Exception as exc:
            logger.warning("could not load faiss index (%s); it will be rebuilt", exc)
            return False

    def reset(self) -> None:
        with self._lock:
            self._index = None
            self._ids = []
            self._meta = {}
        for path in (self.index_path, self.ids_path, self.meta_path):
            if path.exists():
                path.unlink()

    # -- search -------------------------------------------------------------
    def search(self, query_vectors: np.ndarray, top_k: int = 10) -> list[list[SearchHit]]:
        if not self.is_ready:
            raise RuntimeError("vector store is not initialised")
        query_vectors = np.ascontiguousarray(query_vectors, dtype="float32")
        if query_vectors.ndim == 1:
            query_vectors = query_vectors.reshape(1, -1)

        top_k = max(1, min(top_k, len(self._ids)))
        with self._lock:
            scores, indices = self._index.search(query_vectors, top_k)

        results: list[list[SearchHit]] = []
        for row_scores, row_indices in zip(scores, indices):
            hits: list[SearchHit] = []
            for rank, (score, idx) in enumerate(zip(row_scores, row_indices)):
                if idx < 0 or idx >= len(self._ids):
                    continue
                hits.append(SearchHit(standard_id=self._ids[int(idx)], score=float(score), rank=rank))
            results.append(hits)
        return results

    def search_one(self, query_vector: np.ndarray, top_k: int = 10) -> list[SearchHit]:
        return self.search(query_vector, top_k)[0]

    @property
    def size(self) -> int:
        return len(self._ids)

    @property
    def dimension(self) -> int:
        if self._index is None:
            return 0
        return int(self._index.d)

    @property
    def metadata(self) -> dict:
        return dict(self._meta)


vector_store = VectorStore()
