"""Dataset loading and standards lookup services."""

from __future__ import annotations

import json
from pathlib import Path

from config import settings
from database.repositories import standards_repo
from utils import get_logger

logger = get_logger("standards_service")


class DatasetError(RuntimeError):
    """Raised when the curated dataset cannot be loaded."""


class StandardsService:
    """Loads the curated dataset and exposes lookup/search operations."""

    def __init__(self) -> None:
        self._standards: list[dict] | None = None
        self._dataset_meta: dict = {}

    # -- dataset ------------------------------------------------------------
    def load_dataset(self, force: bool = False) -> dict:
        """Read standards.json and upsert it into the database."""
        path = settings.standards_path
        if not path.exists():
            raise DatasetError(f"Standards dataset not found at {path}")

        with open(path, "r", encoding="utf-8") as handle:
            dataset = json.load(handle)

        standards = dataset.get("standards", [])
        if not standards:
            raise DatasetError("Standards dataset contains no standards")

        standards_repo.load_dataset(dataset)
        self._standards = None
        self._dataset_meta = {
            key: value
            for key, value in dataset.items()
            if key
            not in {
                "standards",
            }
        }
        logger.info("dataset loaded from %s (%d standards)", path.name, len(standards))
        return self._dataset_meta

    @property
    def dataset_meta(self) -> dict:
        return dict(self._dataset_meta)

    def all(self) -> list[dict]:
        if self._standards is None:
            self._standards = standards_repo.get_all()
        return self._standards

    def count(self) -> int:
        return standards_repo.count()

    def get(self, standard_id: str) -> dict | None:
        return standards_repo.get_by_id(standard_id)

    def categories(self) -> dict[str, int]:
        return standards_repo.categories()

    def search(
        self,
        query: str = "",
        category: str = "",
        standard_type: str = "",
        status: str = "",
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        total, standards = standards_repo.search(
            query=query,
            category=category,
            standard_type=standard_type,
            status=status,
            page=page,
            page_size=page_size,
        )
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "standards": [
                {
                    "id": std["id"],
                    "standard_number": std["standard_number"],
                    "title": std["title"],
                    "category": std["category"],
                    "version": std["version"],
                    "status": std["status"],
                    "standard_types": std["standard_types"],
                }
                for std in standards
            ],
        }

    def rebuild_index_corpus(self) -> list[dict]:
        return self.all()


standards_service = StandardsService()
