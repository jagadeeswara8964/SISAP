"""Build the FAISS vector index over the standards corpus.

Usage (from the repository root):
    python3 scripts/build_faiss_index.py [--force]

The index is written to ``data/embeddings`` and is reused automatically on
startup unless the dataset changes or ``--force`` is passed.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from ai.embeddings import embedding_service  # noqa: E402
from ai.vector_store import vector_store  # noqa: E402
from config import settings  # noqa: E402
from recommendation.recommendation_engine import StandardRecommendationEngine  # noqa: E402
from services.standards_service import standards_service  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the SISAP FAISS index")
    parser.add_argument("--force", action="store_true", help="Rebuild even if an index already exists")
    args = parser.parse_args()

    started = time.time()
    try:
        if not standards_service.count():
            standards_service.load_dataset(force=True)

        if not args.force and vector_store.load() and vector_store.size == standards_service.count():
            print(f"Index already exists with {vector_store.size} vectors. Use --force to rebuild.")
            return 0

        standards = standards_service.all()
        engine = StandardRecommendationEngine(standards)
        count = engine.build_index(force=True)
    except Exception as exc:  # pragma: no cover - CLI feedback
        print(f"ERROR: {exc}")
        return 1

    print(f"Built FAISS index with {count} vectors in {time.time() - started:.1f}s")
    print(f"Embedding backend: {embedding_service.backend_name}")
    print(f"Embedding model:   {settings.embedding_model}")
    print(f"Index directory:   {settings.index_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
