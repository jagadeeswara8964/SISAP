"""Version / amendment / status validation for recommended standards.

IMPORTANT: validation is performed against the curated demo dataset only. No
live BIS verification is claimed - ``validation_source`` states this explicitly
so procurement officers know what the result is based on.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from utils import get_logger

logger = get_logger("validator")

VALIDATION_SOURCE = "Curated demo dataset"
NOT_AVAILABLE = "Not available in the current dataset."


class StandardsValidator:
    """Checks status, version, amendments and supersession for a standard."""

    def validate(self, standard: dict) -> dict:
        checks: list[str] = []
        status = (standard.get("status") or "").strip()
        version = (standard.get("version") or "").strip()
        amendments = list(standard.get("amendments", []) or [])
        superseded_by = list(standard.get("superseded_by", []) or [])
        certification = (standard.get("certification") or "").strip()

        # --- status --------------------------------------------------------
        if status.lower() == "active":
            checks.append("✓ Status: Active in the curated dataset")
        elif status.lower() == "superseded":
            checks.append("✗ Status: Superseded - this edition should not be cited for new procurement")
        elif status:
            checks.append(f"⚠ Status: {status} - confirm with the issuing authority")
        else:
            checks.append(f"⚠ Status: {NOT_AVAILABLE}")

        # --- version -------------------------------------------------------
        if version:
            checks.append(f"✓ Version recorded: {version}")
        else:
            checks.append(f"⚠ Version: {NOT_AVAILABLE}")

        # --- amendments ----------------------------------------------------
        if amendments:
            checks.append("⚠ Amendment available: " + ", ".join(amendments))
        else:
            checks.append("✓ No amendments recorded in the curated dataset")

        # --- supersession --------------------------------------------------
        if superseded_by:
            checks.append("✗ Superseding edition identified: " + ", ".join(superseded_by))
        elif status.lower() != "superseded":
            checks.append("✓ No known superseding standard in the curated dataset")

        # --- certification -------------------------------------------------
        if certification:
            checks.append(f"ℹ Certification: {certification}")
        else:
            checks.append(f"ℹ Certification: {NOT_AVAILABLE}")

        # --- source --------------------------------------------------------
        source = standard.get("source") or "BIS"
        if standard.get("bis_verified"):
            checks.append(f"ℹ Source: {source} (verified metadata)")
        else:
            checks.append(f"ℹ Source: {source} (unverified - curated demo dataset)")

        return {
            "standard_id": standard.get("id", ""),
            "status": status or NOT_AVAILABLE,
            "version": version or NOT_AVAILABLE,
            "amendments": amendments,
            "superseded_by": superseded_by,
            "certification": certification or NOT_AVAILABLE,
            "checks": checks,
            "validation_source": VALIDATION_SOURCE,
        }

    def validate_many(self, standards: Iterable[dict]) -> dict[str, dict]:
        return {standard["id"]: self.validate(standard) for standard in standards}

    def is_current(self, validation: dict) -> bool:
        return (validation.get("status") or "").lower() == "active" and not validation.get("superseded_by")


validator = StandardsValidator()
