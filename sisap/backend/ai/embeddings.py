"""Embedding service.

Primary backend is Sentence-Transformers (``all-MiniLM-L6-v2``) which produces
384-dimensional dense semantic vectors locally. If the model or torch is
unavailable the service degrades to a TF-IDF backend (still real embeddings,
fully deterministic and offline) so that DEMO_MODE never breaks.

Both backends emit L2-normalised vectors, so an inner-product index is
equivalent to cosine similarity.
"""

from __future__ import annotations

import threading
from typing import Protocol

import numpy as np

from config import settings
from utils import get_logger

logger = get_logger("embeddings")


class EmbeddingBackend(Protocol):
    name: str
    dimension: int

    def fit(self, texts: list[str]) -> None: ...

    def encode(self, texts: list[str]) -> np.ndarray: ...


class SentenceTransformerBackend:
    """Dense semantic embeddings via sentence-transformers."""

    name = "sentence-transformers"

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer  # imported lazily

        logger.info("loading sentence-transformers model '%s'", model_name)
        self._model = SentenceTransformer(model_name)
        # The accessor was renamed in sentence-transformers v5; support both.
        dimension_getter = getattr(self._model, "get_embedding_dimension", None) or getattr(
            self._model, "get_sentence_embedding_dimension"
        )
        self.dimension = int(dimension_getter())
        self.model_name = model_name

    def fit(self, texts: list[str]) -> None:  # no fitting required
        return None

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dimension), dtype="float32")
        vectors = self._model.encode(
            list(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
            batch_size=32,
        )
        return np.asarray(vectors, dtype="float32")


class TfidfBackend:
    """Deterministic offline fallback using character+word TF-IDF features."""

    name = "tfidf"

    def __init__(self) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            sublinear_tf=True,
            ngram_range=(1, 2),
            min_df=1,
            strip_accents="unicode",
        )
        self._fitted = False
        self.dimension = 0

    def fit(self, texts: list[str]) -> None:
        from scipy import sparse  # noqa: F401  (ensures scipy availability)

        self._vectorizer.fit(texts)
        self.dimension = len(self._vectorizer.vocabulary_)
        self._fitted = True
        logger.info("tfidf backend fitted with %d terms", self.dimension)

    def encode(self, texts: list[str]) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("TfidfBackend.encode called before fit()")
        if not texts:
            return np.zeros((0, self.dimension), dtype="float32")
        matrix = self._vectorizer.transform(list(texts))
        return np.asarray(matrix.todense(), dtype="float32")


class EmbeddingService:
    """Loads the best available embedding backend and exposes encode()."""

    def __init__(self, model_name: str | None = None, backend: str | None = None) -> None:
        self._requested_backend = (backend or settings.embedding_backend).lower()
        self._model_name = model_name or settings.embedding_model
        self._backend: EmbeddingBackend | None = None
        self._lock = threading.Lock()
        self._fallback_reason: str | None = None

    # -- lifecycle ----------------------------------------------------------
    def _build(self) -> EmbeddingBackend:
        if self._backend is not None:
            return self._backend

        with self._lock:
            if self._backend is not None:
                return self._backend

            if self._requested_backend in {"auto", "sentence-transformers", "sbert"}:
                try:
                    self._backend = SentenceTransformerBackend(self._model_name)
                    logger.info("embedding backend: %s (dim=%d)", self._backend.name, self._backend.dimension)
                    return self._backend
                except Exception as exc:  # pragma: no cover - depends on environment
                    self._fallback_reason = f"{type(exc).__name__}: {exc}"
                    logger.warning("sentence-transformers unavailable (%s); using TF-IDF", exc)
                    if self._requested_backend == "sentence-transformers":
                        raise

            self._backend = TfidfBackend()
            return self._backend

    def ensure_ready(self, corpus: list[str]) -> None:
        """Initialise the backend, fitting it when the backend needs a corpus."""
        backend = self._build()
        if isinstance(backend, TfidfBackend) and not backend._fitted:
            backend.fit(corpus)

    # -- API ----------------------------------------------------------------
    @property
    def backend_name(self) -> str:
        return self._build().name

    @property
    def dimension(self) -> int:
        return self._build().dimension

    @property
    def fallback_reason(self) -> str | None:
        return self._fallback_reason

    def fit(self, texts: list[str]) -> None:
        self._build().fit(texts)

    def encode(self, texts: list[str]) -> np.ndarray:
        backend = self._build()
        return backend.encode(texts)

    def encode_one(self, text: str) -> np.ndarray:
        return self.encode([text])[0]


embedding_service = EmbeddingService()
