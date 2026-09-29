"""Report generation and retrieval services."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from config import settings
from database.repositories import document_repo
from reports.pdf_report import report_builder
from services.analysis_service import analysis_service
from services.standards_service import standards_service
from utils import get_logger

logger = get_logger("report_service")


class ReportNotFoundError(Exception):
    """Raised when a requested report does not exist."""


class ReportService:
    """Generates and locates PDF analysis reports."""

    def generate(self, document_id: str) -> dict:
        document = document_repo.get(document_id)
        if document is None:
            raise KeyError(document_id)

        analysis = analysis_service.get_recommendations(document_id)
        graph_payload = self._graph_payload(analysis)

        report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"
        filename = f"sisap_report_{document_id}_{report_id}.pdf"
        output_path = settings.reports_dir / filename
        report_builder.build(analysis, document, graph_payload, output_path)

        logger.info("report %s generated for %s (%d bytes)", report_id, document_id, output_path.stat().st_size)
        return {
            "document_id": document_id,
            "report_id": report_id,
            "filename": filename,
            "download_url": f"/api/reports/{document_id}/download?file={filename}",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sections": [
                "Executive Summary",
                "Document Information",
                "Extracted Requirements",
                "Recommended Standards",
                "Relevance Reasons",
                "Related Standards",
                "Version and Amendment Validation",
                "Certification Information",
                "Potential Specification Gaps",
                "Standards Relationship Graph",
                "Review Notes",
                "Data Sources",
            ],
        }

    def _graph_payload(self, analysis: dict) -> dict:
        """Root the relationship graph at the highest-ranked primary standard."""
        recommendations = analysis.get("recommendations", [])
        primaries = [rec for rec in recommendations if rec["type"] == "Primary"]
        root = (primaries or recommendations or [None])[0]
        if root is None:
            return {"root": "", "nodes": [], "edges": []}

        scores = {rec["standard_id"]: rec["score"] for rec in recommendations}
        types = {rec["standard_id"]: rec["type"] for rec in recommendations}
        payload = analysis_service.graph.visualisation(
            root["standard_id"], scores=scores, types=types, depth=1
        )

        # Prefer showing recommended standards first when the graph is large.
        nodes = payload.get("nodes", [])
        ordered = sorted(
            nodes,
            key=lambda node: (0 if node["id"] in scores else 1, -(node.get("score") or 0)),
        )
        payload["nodes"] = ordered
        return payload

    def find(self, filename: str) -> Path:
        """Resolve a report filename inside the reports directory."""
        safe_name = Path(filename).name
        if safe_name != filename or not safe_name.endswith(".pdf"):
            raise ReportNotFoundError("Invalid report filename.")
        path = settings.reports_dir / safe_name
        if not path.exists() or not path.is_file():
            raise ReportNotFoundError(f"Report '{safe_name}' was not found.")
        return path


report_service = ReportService()


class DashboardService:
    """Aggregated statistics for the dashboard."""

    def stats(self) -> dict:
        from database.repositories import (
            document_repo,
            gap_repo,
            recommendation_repo,
            standards_repo,
        )

        documents = document_repo.list_recent(20)
        categories = standards_repo.categories()

        recent: list[dict] = []
        standards_recommended = 0
        potential_gaps = 0
        validated_references = 0

        for document in documents:
            recs = recommendation_repo.get(document["id"])
            gaps = gap_repo.get(document["id"])
            requirements = document_repo.get(document["id"]) or {}
            product = (requirements.get("requirements") or {}).get("product", "")
            standards_recommended += len(recs)
            potential_gaps += len(gaps)
            validated_references += sum(
                1 for rec in recs if (rec.get("validation") or {}).get("status") == "Active"
            )
            recent.append(
                {
                    "document_id": document["id"],
                    "filename": document.get("original_filename") or document.get("filename", ""),
                    "product": product or "Not identified",
                    "standards": len(recs),
                    "gaps": len(gaps),
                    "date": (document.get("uploaded_at") or "")[:16].replace("T", " "),
                    "status": self._status(document, recs),
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
        if any(rec.get("type") == "Primary" for rec in recommendations):
            return "Standards identified"
        return "Review required"

    def _confidence(self) -> dict:
        """Average composite score per standard type across all analyses."""
        from database.repositories import recommendation_repo

        rows = recommendation_repo.get("__none__")  # keeps type checkers quiet
        del rows

        from database.db import db

        data = db.query_all(
            """
            SELECT category AS type, AVG(score) AS average, COUNT(*) AS n
            FROM recommendations GROUP BY category
            """
        )
        return {row["type"]: round(float(row["average"]), 1) for row in data}


dashboard_service = DashboardService()
