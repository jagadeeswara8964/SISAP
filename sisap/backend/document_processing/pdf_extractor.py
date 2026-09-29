"""PDF text extraction with PyMuPDF.

Detects scanned / image-only PDFs (which would require OCR) instead of silently
returning empty text. OCR is intentionally not wired in: the pipeline reports
the condition so a modular OCR adapter can be added later.
"""

from __future__ import annotations

from dataclasses import dataclass

import pymupdf

from utils import get_logger

logger = get_logger("pdf")

# A page with fewer than this many characters is treated as having no text layer.
MIN_CHARS_PER_PAGE = 40
# If this fraction of pages has no text layer, treat the document as scanned.
SCANNED_PAGE_RATIO = 0.6


@dataclass
class ExtractionResult:
    text: str
    page_count: int
    char_count: int
    is_scanned: bool
    extraction_status: str
    message: str = ""


class PDFExtractor:
    """Extract text from PDF bytes using PyMuPDF."""

    def extract(self, pdf_bytes: bytes, filename: str = "document.pdf") -> ExtractionResult:
        try:
            document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        except Exception as exc:
            logger.warning("could not open %s as PDF: %s", filename, exc)
            return ExtractionResult(
                text="",
                page_count=0,
                char_count=0,
                is_scanned=False,
                extraction_status="invalid_pdf",
                message="The uploaded file could not be opened as a valid PDF. Please upload a text-based PDF.",
            )

        try:
            if document.needs_pass:
                return ExtractionResult(
                    text="",
                    page_count=document.page_count,
                    char_count=0,
                    is_scanned=False,
                    extraction_status="password_protected",
                    message="This PDF is password protected. Please upload an unprotected copy.",
                )

            page_count = document.page_count
            pages: list[str] = []
            empty_pages = 0

            for page in document:
                page_text = self._extract_page(page)
                if len(page_text.strip()) < MIN_CHARS_PER_PAGE:
                    empty_pages += 1
                pages.append(page_text)

            text = "\n\n".join(pages).strip()
            char_count = len(text)

            if char_count == 0 or (page_count and empty_pages / page_count >= SCANNED_PAGE_RATIO):
                return ExtractionResult(
                    text=text,
                    page_count=page_count,
                    char_count=char_count,
                    is_scanned=True,
                    extraction_status="scanned",
                    message=(
                        "Text could not be reliably extracted. OCR is required for this document. "
                        "OCR is not enabled in this deployment."
                    ),
                )

            return ExtractionResult(
                text=text,
                page_count=page_count,
                char_count=char_count,
                is_scanned=False,
                extraction_status="ok",
                message="Text extracted successfully.",
            )
        finally:
            document.close()

    @staticmethod
    def _extract_page(page) -> str:
        """Prefer the layout-preserving text mode, falling back to plain text."""
        try:
            text = page.get_text("text")
        except Exception:  # pragma: no cover - defensive
            text = ""
        if not text or not text.strip():
            try:
                text = page.get_text("blocks")
                if isinstance(text, list):
                    text = "\n".join(block[4] for block in text if isinstance(block, tuple) and len(block) > 4)
            except Exception:  # pragma: no cover - defensive
                text = ""
        return text or ""
