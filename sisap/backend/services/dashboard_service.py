"""Dashboard statistics."""

from __future__ import annotations

from database.db import db
from database.repositories import (
    document_repo,
    gap_repo,
    recommendation_repo,
    standards_repo,
)
from services.standards_service import standards_service


class DashboardService:
    """Aggregated statistics for the dashboard page."""

    def stats(self) -> dict:
        documents = document_repo.list_recent(20)
        categories = standards_repo.categories()

        recent: list[dict] = []
        standards_recommended = 0
        potential_gaps = 0
        validated_references = 0

        for document in documents:
            recommendations = recommendation_repo.get(document["id"])
            gaps = gap_repo.get(document["id"])
            full = document_repo.get(document["id"]) or {}
            product = (full.get("requirements") or {}).get("product", "")
            standards_recommended += len(recommendations)
            potential_gaps += len(gaps)
            validated_references += sum(
                1 for rec in recommendations if (rec.get("validation") or {}).get("status") == "Active"
            )
            recent.append(
                {
                    "document_id": document["id"],
                    "filename": document.get("original_filename") or document.get("filename", ""),
                    "product": product or "Not identified",
                    "standards": len(recommendations),
                    "gaps": len(gaps),
                    "date": (document.get("uploaded_at") or "")[:16].replace("T", " "),
                    "status": self._status(document, recommendations),
                }
            )

        return {
            "documents_analyzed": len(documents),
            "standards_recommended": standards_recommended,
            "potential_gaps_found": potential_gaps,
            "validated_references": validated_references,
            "standards_in_database": standards_repo.count(),
            "categories": categories,
            "confidence": self._confidence(),
            "dataset": standards_service.dataset_meta,
            "recent_analyses": recent,
        }

    @staticmethod
    def _status(document: dict, recommendations: list[dict]) -> str:
        if document.get("is_scanned"):
            return "OCR required"
        if document.get("extraction_status") != "ok":
            return "Extraction issue"
        if not recommendations:
            return "Awaiting analysis"
        if any(rec.get("category") == "Primary" for rec in recommendations):
            return "Standards identified"
        return "Review required"

    @staticmethod
    def _confidence() -> dict:
        """Average composite score per standard type across all stored analyses."""
        rows = db.query_all(
            "SELECT category AS type, AVG(score) AS average FROM recommendations GROUP BY category"
        )
        return {row["type"]: round(float(row["average"]), 1) for row in rows}


dashboard_service = DashboardService()
