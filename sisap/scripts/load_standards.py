"""Load the curated standards dataset into the SQLite database.

Usage (from the repository root):
    python3 scripts/load_standards.py

Idempotent: re-running upserts the dataset without duplicating standards.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from services.standards_service import standards_service  # noqa: E402


def main() -> int:
    try:
        meta = standards_service.load_dataset(force=True)
    except Exception as exc:  # pragma: no cover - CLI feedback
        print(f"ERROR: {exc}")
        return 1

    count = standards_service.count()
    print(f"Loaded {count} standards into {standards_service.database_path()}")
    print(f"Dataset: {meta.get('dataset_name')} v{meta.get('dataset_version')}")
    print(f"Verification: {meta.get('verification_status')}")
    print("\nStandards by category:")
    for category, total in standards_service.categories().items():
        print(f"  {category:<22} {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
