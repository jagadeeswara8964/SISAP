"""Document upload and requirement extraction services."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from config import settings
from database.repositories import document_repo
from document_processing.pdf_extractor import PDFExtractor
from document_processing.text_processor import text_processor
from recommendation.requirement_extractor import RequirementExtractor
from utils import get_logger

logger = get_logger("document_service")

SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


class DocumentValidationError(ValueError):
    """Raised for invalid uploads (bad type, too large, empty, unreadable)."""


class DocumentService:
    """Handles uploads, text extraction and requirement extraction."""

    def __init__(self, extractor: RequirementExtractor | None = None) -> None:
        self._extractor = extractor
        self._pdf_extractor = PDFExtractor()

    @property
    def extractor(self) -> RequirementExtractor:
        if self._extractor is None:
            from services.standards_service import standards_service

            self._extractor = RequirementExtractor(standards=standards_service.all())
        return self._extractor

    # -- upload -------------------------------------------------------------
    def validate_upload(self, filename: str, content: bytes) -> None:
        if not filename:
            raise DocumentValidationError("No filename supplied.")
        extension = Path(filename).suffix.lower().lstrip(".")
        if extension not in settings.allowed_extensions:
            raise DocumentValidationError(
                f"Unsupported file type '.{extension}'. Only PDF files are accepted."
            )
        if not content:
            raise DocumentValidationError("The uploaded file is empty.")
        if len(content) > settings.max_upload_bytes:
            raise DocumentValidationError(
                f"File is too large ({len(content) / (1024 * 1024):.1f} MB). "
                f"Maximum allowed size is {settings.max_upload_bytes / (1024 * 1024):.0f} MB."
            )
        if not content.startswith(b"%PDF"):
            raise DocumentValidationError("The file does not appear to be a valid PDF document.")

    @staticmethod
    def sanitise_filename(filename: str) -> str:
        """Return a filesystem-safe filename, preserving the extension."""
        name = Path(filename or "document.pdf").name
        safe = SAFE_FILENAME_RE.sub("_", name).strip("._")
        return safe or "document.pdf"

    def store_upload(self, filename: str, content: bytes) -> Path:
        safe_name = self.sanitise_filename(filename)
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        path = settings.upload_dir / f"{uuid.uuid4().hex[:12]}_{safe_name}"
        path.write_bytes(content)
        return path

    # -- extraction ---------------------------------------------------------
    def create_document(self, filename: str, content: bytes) -> dict:
        self.validate_upload(filename, content)
        stored_path = self.store_upload(filename, content)
        result = self._pdf_extractor.extract(content, filename)

        document = document_repo.create(
            filename=stored_path.name,
            original_filename=self.sanitise_filename(filename),
            extracted_text=result.text,
            page_count=result.page_count,
            is_scanned=result.is_scanned,
            extraction_status=result.extraction_status,
            source_type="pdf",
        )
        document["message"] = result.message
        logger.info(
            "document %s uploaded (%d pages, %d chars, status=%s)",
            document["id"],
            result.page_count,
            result.char_count,
            result.extraction_status,
        )
        return document

    def create_text_document(self, text: str, filename: str = "pasted-specification.txt") -> dict:
        """Register manually pasted specification text as a document."""
        text = (text or "").strip()
        if not text:
            raise DocumentValidationError("No specification text was provided.")
        if len(text) > settings.max_upload_bytes:
            raise DocumentValidationError("The pasted specification text is too large.")

        document = document_repo.create(
            filename=self.sanitise_filename(filename),
            original_filename=filename,
            extracted_text=text,
            page_count=0,
            is_scanned=False,
            extraction_status="ok",
            source_type="text",
        )
        document["message"] = "Specification text received."
        return document

    def extract_requirements(self, document_id: str, use_llm: bool = False) -> dict:
        document = document_repo.get(document_id)
        if document is None:
            raise DocumentValidationError(f"Document {document_id} was not found.")

        raw_text = document_repo.get_text(document_id)
        if not raw_text.strip():
            raise DocumentValidationError(
                "No text is available for this document. If it is a scanned PDF, OCR is required."
            )

        # Text cleaning + section detection happen before requirement extraction.
        processed = text_processor.process(raw_text)
        result = self.extractor.extract(processed.text, use_llm=use_llm)
        document_repo.save_requirements(document_id, result.requirements, result.extraction_method)
        logger.info(
            "requirements extracted for %s via %s (%d sentences, %d sections)",
            document_id,
            result.extraction_method,
            result.sentences_classified,
            len(processed.sections),
        )
        return {
            "document_id": document_id,
            "requirements": result.requirements,
            "extraction_method": result.extraction_method,
            "text_available": True,
            "sections": [
                {"key": section.key, "title": section.title, "characters": len(section.text)}
                for section in processed.sections
            ],
        }

    def get_document(self, document_id: str) -> dict | None:
        return document_repo.get(document_id)

    def list_documents(self, limit: int = 50) -> list[dict]:
        return document_repo.list_recent(limit)


document_service = DocumentService()
