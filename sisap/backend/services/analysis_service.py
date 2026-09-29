"""Analysis orchestration: requirements -> recommendations -> validation -> gaps."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from database.repositories import document_repo, gap_repo, recommendation_repo
from graph.standards_graph import StandardsGraph
from recommendation.gap_detector import SpecificationGapDetector, summarise_gaps
from recommendation.recommendation_engine import StandardRecommendationEngine
from services.standards_service import standards_service
from utils import get_logger
from validation.standards_validator import StandardsValidator

logger = get_logger("analysis_service")

REVIEW_NOTE = (
    "AI-generated recommendations should be reviewed by the responsible "
    "procurement/technical authority."
)

TYPE_TO_SUMMARY_KEY = {
    "Primary": "primary",
    "Testing": "testing",
    "Safety": "safety",
    "Reference": "reference",
    "Installation": "installation",
    "Terminology": "terminology",
    "Related": "related",
}


class AnalysisService:
    """Runs the full recommendation pipeline for a document."""

    def __init__(self) -> None:
        self._engine: StandardRecommendationEngine | None = None
        self._graph: StandardsGraph | None = None
        self._validator = StandardsValidator()
        self._gap_detector = SpecificationGapDetector()

    # -- lifecycle ----------------------------------------------------------
    def initialise(self, force_rebuild: bool = False) -> None:
        if self._engine is not None and not force_rebuild:
            return
        standards = standards_service.all()
        if not standards:
            standards_service.load_dataset(force=True)
            standards = standards_service.all()
        self._engine = StandardRecommendationEngine(standards)
        self._engine.build_index(force=force_rebuild)
        self._graph = StandardsGraph(standards)
        logger.info("analysis service initialised with %d standards", len(standards))

    @property
    def engine(self) -> StandardRecommendationEngine:
        self.initialise()
        assert self._engine is not None
        return self._engine

    @property
    def graph(self) -> StandardsGraph:
        self.initialise()
        assert self._graph is not None
        return self._graph

    # -- analysis -----------------------------------------------------------
    def analyse_document(self, document_id: str, use_llm: bool = False) -> dict:
        from services.document_service import document_service

        document = document_repo.get(document_id)
        if document is None:
            raise KeyError(document_id)

        requirements = document.get("requirements")
        if not requirements:
            extracted = document_service.extract_requirements(document_id, use_llm=use_llm)
            requirements = extracted["requirements"]
        extraction_method = requirements.get("extraction_method") or "rule-based"

        return self._run(document_id, requirements, extraction_method)

    def analyse_text(self, text: str, use_llm: bool = False) -> dict:
        """Analyse pasted specification text without storing a document."""
        from services.document_service import document_service

        result = document_service.extractor.extract(text, use_llm=use_llm)
        return self._run("AD-HOC", result.requirements, result.extraction_method)

    def _run(self, document_id: str, requirements: dict, extraction_method: str) -> dict:
        recommendations = self.engine.recommend(requirements, standards_graph=self.graph)
        logger.info(
            "%s: %d recommendations (%s)", document_id, len(recommendations), extraction_method
        )

        validations = {
            rec.standard["id"]: self._validator.validate(rec.standard) for rec in recommendations
        }
        gaps = self._gap_detector.detect(requirements, recommendations)

        if document_id != "AD-HOC":
            recommendation_repo.replace(
                document_id,
                [
                    {
                        "standard_id": rec.standard["id"],
                        "score": rec.score,
                        "type": rec.type,
                        "explanation": rec.explanation,
                        "matched_requirements": rec.matched_requirements,
                        "missing_requirements": rec.missing_requirements,
                        "related_standards": rec.related_standards,
                        "validation": validations[rec.standard["id"]],
                    }
                    for rec in recommendations
                ],
            )
            gap_repo.replace(document_id, gaps)

        summary = self._summarise(recommendations, gaps)
        return {
            "document_id": document_id,
            "product": requirements.get("product", ""),
            "category": requirements.get("category", ""),
            "summary": summary,
            "recommendations": [
                self._serialise(rec, validations[rec.standard["id"]]) for rec in recommendations
            ],
            "gaps": gaps,
            "sections": self._sections(document_id),
            "extraction_method": extraction_method,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "review_note": REVIEW_NOTE,
        }

    @staticmethod
    def _sections(document_id: str) -> list[dict]:
        """Detected document sections (empty for ad-hoc text analyses)."""
        if document_id == "AD-HOC":
            return []
        try:
            from document_processing.text_processor import text_processor

            raw = document_repo.get_text(document_id)
            if not raw.strip():
                return []
            processed = text_processor.process(raw)
            return [
                {"key": section.key, "title": section.title, "characters": len(section.text)}
                for section in processed.sections
            ]
        except Exception:  # pragma: no cover - sections are advisory only
            return []

    # -- helpers ------------------------------------------------------------
    @staticmethod
    def _summarise(recommendations: Sequence, gaps: Sequence[dict]) -> dict:
        summary = {
            "total": len(recommendations),
            "primary": 0,
            "testing": 0,
            "safety": 0,
            "reference": 0,
            "installation": 0,
            "terminology": 0,
            "related": 0,
            "high_relevance": 0,
            "potential_gaps": len(gaps),
        }
        for rec in recommendations:
            key = TYPE_TO_SUMMARY_KEY.get(rec.type)
            if key:
                summary[key] += 1
            if rec.score >= 70:
                summary["high_relevance"] += 1
        return summary

    @staticmethod
    def _serialise(rec, validation: dict) -> dict:
        standard = rec.standard
        return {
            "standard_id": standard["id"],
            "standard_number": standard.get("standard_number", standard["id"]),
            "title": standard.get("title", ""),
            "category": standard.get("category", ""),
            "type": rec.type,
            "score": rec.score,
            "status": standard.get("status", "Active"),
            "score_breakdown": rec.score_breakdown,
            "explanation": rec.explanation,
            "matched_requirements": rec.matched_requirements,
            "missing_requirements": rec.missing_requirements,
            "related_standards": rec.related_standards,
            "validation": validation,
            "scope": standard.get("scope", ""),
            "version": standard.get("version", ""),
            "amendments": standard.get("amendments", []),
            "certification": standard.get("certification", ""),
            "source_url": standard.get("source_url", ""),
            "relationship_path": rec.relationship_path,
            "materials": standard.get("materials", []),
            "applications": standard.get("applications", []),
        }

    def get_recommendations(self, document_id: str) -> dict:
        stored = recommendation_repo.get(document_id)
        document = document_repo.get(document_id)
        if document is None:
            raise KeyError(document_id)
        if not stored:
            return self.analyse_document(document_id)

        standards = {std["id"]: std for std in standards_service.all()}
        recommendations = []
        stored_recs = []
        for row in stored:
            standard = standards.get(row["standard_id"])
            if standard is None:
                continue
            adapter = _StoredRecommendation(standard, row)
            stored_recs.append(adapter)
            recommendations.append(
                self._serialise(
                    adapter,
                    row.get("validation") or self._validator.validate(standard),
                )
            )
        gaps = gap_repo.get(document_id)
        requirements = document.get("requirements") or {}
        return {
            "document_id": document_id,
            "product": requirements.get("product", ""),
            "category": requirements.get("category", ""),
            "summary": self._summarise(stored_recs, gaps),
            "recommendations": recommendations,
            "gaps": gaps,
            "extraction_method": requirements.get("extraction_method", "rule-based"),
            "generated_at": document.get("uploaded_at", ""),
            "review_note": REVIEW_NOTE,
        }

    def get_gaps(self, document_id: str) -> dict:
        document = document_repo.get(document_id)
        if document is None:
            raise KeyError(document_id)
        gaps = gap_repo.get(document_id)
        if not gaps and document.get("requirements_extracted"):
            return self.analyse_document(document_id)
        counts = summarise_gaps(gaps)
        return {
            "document_id": document_id,
            "total": counts["total"],
            "critical": counts["Critical"],
            "high": counts["High"],
            "medium": counts["Medium"],
            "low": counts["Low"],
            "gaps": gaps,
            "review_note": (
                "Potential gaps requiring procurement officer review. "
                "SISAP does not declare a tender legally compliant or non-compliant."
            ),
        }


class _StoredRecommendation:
    """Adapter that presents a persisted recommendation row like a Recommendation."""

    def __init__(self, standard: dict, row: dict) -> None:
        self.standard = standard
        self.type = row.get("category", "Related")
        self.score = row.get("score", 0.0)
        self.score_breakdown = {}
        self.explanation = row.get("explanation", [])
        self.matched_requirements = row.get("matched_requirements", [])
        self.missing_requirements = row.get("missing_requirements", [])
        self.related_standards = row.get("related_standards", [])
        self.relationship_path = ""


analysis_service = AnalysisService()
