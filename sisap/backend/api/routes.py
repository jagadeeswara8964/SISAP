"""REST API routes for SISAP."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel  # noqa: F401  (kept for parity with other modules)

from config import settings
from database.repositories import document_repo
from services.analysis_service import analysis_service
from services.dashboard_service import dashboard_service
from services.document_service import DocumentValidationError, document_service
from services.report_service import ReportNotFoundError, report_service
from schemas.schemas import (
    GapsResponse,
    HealthResponse,
    RecommendRequest,
    ReportResponse,
    StandardsPage,
)
from services.standards_service import DatasetError, standards_service
from utils import get_logger

logger = get_logger("api")

router = APIRouter(prefix="/api")


def _error(status_code: int, message: str, code: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": message, "code": code})


# --------------------------------------------------------------------- health
@router.get("/health", response_model=HealthResponse)
async def health() -> dict:
    from ai.embeddings import embedding_service
    from ai.vector_store import vector_store

    try:
        analysis_service.initialise()
        standards_loaded = standards_service.count()
        faiss_vectors = vector_store.size
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("health check partially failed: %s", exc)
        standards_loaded = standards_service.count()
        faiss_vectors = 0

    return {
        "status": "ok",
        "demo_mode": settings.demo_mode,
        "embedding_backend": embedding_service.backend_name,
        "embedding_model": settings.embedding_model,
        "standards_loaded": standards_loaded,
        "faiss_vectors": faiss_vectors,
        "version": settings.app_version,
        "settings": settings.public_dict(),
    }


@router.get("/dashboard/stats")
async def dashboard_stats() -> dict:
    return dashboard_service.stats()


# ------------------------------------------------------------------ documents
@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)) -> dict:
    try:
        content = await file.read()
        document = document_service.create_document(file.filename or "document.pdf", content)
    except DocumentValidationError as exc:
        return _error(400, str(exc), "invalid_upload")
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("upload failed")
        return _error(500, f"Upload failed: {exc}", "upload_failed")

    return {
        "document_id": document["id"],
        "filename": document.get("original_filename", document["filename"]),
        "page_count": document["page_count"],
        "char_count": document["char_count"],
        "is_scanned": document["is_scanned"],
        "extraction_status": document["extraction_status"],
        "message": document.get("message", ""),
    }


@router.post("/documents/text")
async def create_text_document(text: str = Form(...)) -> dict:
    try:
        document = document_service.create_text_document(text)
    except DocumentValidationError as exc:
        return _error(400, str(exc), "invalid_text")
    return {
        "document_id": document["id"],
        "filename": document["filename"],
        "page_count": 0,
        "char_count": document["char_count"],
        "is_scanned": False,
        "extraction_status": document["extraction_status"],
        "message": document.get("message", ""),
    }


@router.get("/documents/{document_id}")
async def get_document(document_id: str) -> dict:
    document = document_repo.get(document_id)
    if document is None:
        return _error(404, f"Document {document_id} was not found.", "document_not_found")
    return document


@router.post("/documents/{document_id}/extract")
async def extract_requirements(document_id: str, use_llm: bool = Query(False)) -> dict:
    try:
        return document_service.extract_requirements(document_id, use_llm=use_llm)
    except KeyError:
        return _error(404, f"Document {document_id} was not found.", "document_not_found")
    except DocumentValidationError as exc:
        return _error(400, str(exc), "extraction_failed")


@router.get("/documents/{document_id}/gaps")
async def get_gaps(document_id: str) -> GapsResponse:
    try:
        return analysis_service.get_gaps(document_id)
    except KeyError:
        return _error(404, f"Document {document_id} was not found.", "document_not_found")


# --------------------------------------------------------- recommendations
@router.post("/recommendations")
async def create_recommendations(payload: RecommendRequest) -> dict:
    try:
        if payload.document_id:
            return analysis_service.analyse_document(payload.document_id, use_llm=payload.use_llm)
        if payload.text:
            return analysis_service.analyse_text(payload.text, use_llm=payload.use_llm)
        return _error(400, "Provide either a document_id or specification text.", "invalid_request")
    except KeyError:
        return _error(404, f"Document {payload.document_id} was not found.", "document_not_found")
    except DocumentValidationError as exc:
        return _error(400, str(exc), "extraction_failed")
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("recommendation failed")
        return _error(500, f"Recommendation failed: {exc}", "recommendation_failed")


@router.get("/recommendations/{document_id}")
async def get_recommendations(document_id: str) -> dict:
    try:
        return analysis_service.get_recommendations(document_id)
    except KeyError:
        return _error(404, f"Document {document_id} was not found.", "document_not_found")


# ----------------------------------------------------------------- standards
@router.get("/standards")
async def list_standards(
    query: str = Query("", description="Search by number, title, product or keyword"),
    category: str = Query(""),
    standard_type: str = Query(""),
    status: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> StandardsPage:
    return standards_service.search(
        query=query,
        category=category,
        standard_type=standard_type,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.get("/standards/categories")
async def standard_categories() -> dict:
    return {"categories": standards_service.categories()}


@router.get("/standards/{standard_id}")
async def get_standard(standard_id: str) -> dict:
    standard = standards_service.get(standard_id)
    if standard is None:
        return _error(
            404, f"Standard {standard_id} was not found in the curated dataset.", "standard_not_found"
        )
    standard["relationships"] = analysis_service.graph.relationships_for(standard_id)
    return standard


@router.get("/standards/{standard_id}/graph")
async def get_standard_graph(standard_id: str, depth: int = Query(1, ge=1, le=2)) -> dict:
    standard = standards_service.get(standard_id)
    if standard is None:
        return _error(
            404, f"Standard {standard_id} was not found in the curated dataset.", "standard_not_found"
        )
    return analysis_service.graph.visualisation(standard_id, depth=depth)


# -------------------------------------------------------------------- reports
@router.post("/reports/{document_id}")
async def generate_report(document_id: str) -> ReportResponse:
    try:
        return report_service.generate(document_id)
    except KeyError:
        return _error(404, f"Document {document_id} was not found.", "document_not_found")
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("report generation failed")
        return _error(500, f"Report generation failed: {exc}", "report_failed")


@router.get("/reports/{document_id}/download")
async def download_report(document_id: str, file: str = Query(...)) -> FileResponse:
    try:
        path: Path = report_service.find(file)
    except ReportNotFoundError as exc:
        return _error(404, str(exc), "report_not_found")
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=path.name,
        headers={"Content-Disposition": f'attachment; filename="{path.name}"'},
    )


# ---------------------------------------------------------------- dataset ops
@router.post("/standards/reload")
async def reload_dataset(rebuild_index: bool = Query(True)) -> dict:
    try:
        standards_service.load_dataset(force=True)
        analysis_service.initialise(force_rebuild=rebuild_index)
    except DatasetError as exc:
        return _error(400, str(exc), "dataset_error")
    return {
        "status": "reloaded",
        "standards": standards_service.count(),
        "index_rebuilt": rebuild_index,
    }


@router.get("/demo/tender")
async def demo_tender() -> dict:
    """Return the bundled sample tender used for the demonstration flow."""
    sample_dir = settings.data_dir / "sample_tenders"
    candidates = sorted(sample_dir.glob("*.txt")) if sample_dir.exists() else []
    if not candidates:
        return _error(404, "No sample tender text is available.", "demo_not_found")

    # Prefer the industrial control panel tender (the primary demonstration).
    preferred = [path for path in candidates if "control_panel" in path.name]
    chosen = (preferred or candidates)[0]
    return {
        "filename": chosen.name,
        "text": chosen.read_text(encoding="utf-8"),
        "available_files": [path.name for path in candidates],
    }


@router.get("/config")
async def public_config() -> dict:
    return settings.public_dict()
