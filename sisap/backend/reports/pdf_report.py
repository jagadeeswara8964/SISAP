"""Professional PDF procurement analysis report (ReportLab)."""

from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from utils import get_logger, truncate

logger = get_logger("pdf_report")

NAVY = colors.HexColor("#0F2A47")
GOVERNMENT_BLUE = colors.HexColor("#1B4F8A")
LIGHT_BLUE = colors.HexColor("#E8EEF5")
NEUTRAL = colors.HexColor("#5B6570")
LINE_GREY = colors.HexColor("#C9D2DB")
AMBER = colors.HexColor("#B4690E")
RED = colors.HexColor("#A32020")

TYPE_COLOURS = {
    "Primary": GOVERNMENT_BLUE,
    "Testing": colors.HexColor("#2E6F9E"),
    "Safety": colors.HexColor("#8A2E2E"),
    "Reference": NEUTRAL,
    "Installation": colors.HexColor("#4A6B2A"),
    "Terminology": colors.HexColor("#5C4B8A"),
    "Related": colors.HexColor("#7A6A55"),
}

# How many standards get a full evidence breakdown in section 5.
DETAILED_REASONS_LIMIT = 10

SEVERITY_COLOURS = {
    "Critical": RED,
    "High": colors.HexColor("#B4690E"),
    "Medium": colors.HexColor("#8A6D1F"),
    "Low": NEUTRAL,
}


class ReportBuilder:
    """Builds the SISAP procurement analysis PDF."""

    def __init__(self) -> None:
        self.styles = getSampleStyleSheet()
        self._build_styles()

    # -- styles -------------------------------------------------------------
    def _build_styles(self) -> None:
        base = self.styles["Normal"]
        self.body = ParagraphStyle(
            "SisapBody",
            parent=base,
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#1B2430"),
        )
        self.small = ParagraphStyle("SisapSmall", parent=self.body, fontSize=7.5, leading=10.5, textColor=NEUTRAL)
        self.h2 = ParagraphStyle(
            "SisapH2",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=14,
            textColor=NAVY,
            spaceBefore=10,
            spaceAfter=5,
        )
        self.h3 = ParagraphStyle(
            "SisapH3",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=GOVERNMENT_BLUE,
            spaceBefore=6,
            spaceAfter=3,
        )
        self.cell = ParagraphStyle(
            "SisapCell",
            parent=base,
            fontName="Helvetica",
            fontSize=7.6,
            leading=10,
            textColor=colors.HexColor("#1B2430"),
        )
        self.cell_bold = ParagraphStyle("SisapCellBold", parent=self.cell, fontName="Helvetica-Bold")
        self.cell_white = ParagraphStyle(
            "SisapCellWhite", parent=self.cell, fontName="Helvetica-Bold", textColor=colors.white
        )
        self.bullet = ParagraphStyle(
            "SisapBullet", parent=self.body, leftIndent=9, bulletIndent=1, spaceAfter=1.5, fontSize=8.6, leading=12
        )
        self.cover_title = ParagraphStyle(
            "SisapCoverTitle", parent=base, fontName="Helvetica-Bold", fontSize=21, leading=25, textColor=colors.white
        )
        self.cover_sub = ParagraphStyle(
            "SisapCoverSub", parent=base, fontName="Helvetica", fontSize=10, leading=14, textColor=colors.HexColor("#C9D8E8")
        )

    # -- public API ---------------------------------------------------------
    def build(self, analysis: dict, document: dict | None, graph_payload: dict, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=16 * mm,
            rightMargin=16 * mm,
            topMargin=15 * mm,
            bottomMargin=16 * mm,
            title="SISAP Procurement Standards Analysis Report",
            author="SISAP - Smart Indian Standards Advisor for Procurement",
            subject="Applicable Indian Standards analysis for procurement specifications",
        )
        doc.build(
            self._story(analysis, document, graph_payload),
            onFirstPage=self._page_decorations,
            onLaterPages=self._page_decorations,
        )
        logger.info("report written to %s", output_path)
        return output_path

    # -- story --------------------------------------------------------------
    def _story(self, analysis: dict, document: dict | None, graph_payload: dict) -> list:
        story: list = []
        summary = analysis.get("summary", {})

        story.extend(self._cover(analysis, document, summary))
        story.append(PageBreak())

        story.append(Paragraph("1. Executive Summary", self.h2))
        story.append(Paragraph(self._executive_summary(analysis, summary), self.body))
        story.append(Spacer(1, 6))
        story.append(self._summary_table(summary))
        story.append(Spacer(1, 8))
        story.extend(self._confidence_bars(analysis.get("recommendations", [])))

        story.append(Paragraph("2. Document Information", self.h2))
        story.append(self._kv_table(self._document_rows(analysis, document)))

        story.append(Paragraph("3. Extracted Requirements", self.h2))
        story.extend(self._requirements_block(analysis))

        story.append(PageBreak())

        story.append(Paragraph("4. Recommended Standards", self.h2))
        story.append(
            Paragraph(
                f"{summary.get('total', 0)} standards identified. Ranked by composite relevance score "
                "(semantic similarity, requirement coverage, product, application and category matching).",
                self.small,
            )
        )
        story.append(Spacer(1, 5))
        story.append(self._recommendations_table(analysis.get("recommendations", [])))

        story.append(PageBreak())
        story.append(Paragraph("5. Relevance Reasons", self.h2))
        all_recommendations = analysis.get("recommendations", [])
        detailed = all_recommendations[:DETAILED_REASONS_LIMIT]
        if len(all_recommendations) > len(detailed):
            story.append(
                Paragraph(
                    f"Detailed evidence is provided for the {len(detailed)} highest-ranked "
                    f"standards. The remaining {len(all_recommendations) - len(detailed)} "
                    "recommendations are listed in section 4.",
                    self.small,
                )
            )
        story.extend(self._reasons_block(detailed))

        story.append(PageBreak())
        story.append(Paragraph("6. Related Standards", self.h2))
        story.append(self._related_table(analysis.get("recommendations", [])))

        story.append(Paragraph("7. Version and Amendment Validation", self.h2))
        story.append(self._validation_table(analysis.get("recommendations", [])))

        story.append(PageBreak())
        story.append(Paragraph("8. Certification Information", self.h2))
        story.append(self._certification_table(analysis.get("recommendations", [])))

        story.append(Paragraph("9. Potential Specification Gaps", self.h2))
        story.extend(self._gaps_block(analysis.get("gaps", [])))

        story.append(PageBreak())
        story.append(Paragraph("10. Standards Relationship Graph", self.h2))
        story.extend(self._graph_block(graph_payload))

        story.append(Paragraph("11. Review Notes", self.h2))
        story.extend(self._review_notes())

        story.append(Paragraph("12. Data Sources", self.h2))
        story.extend(self._data_sources())
        return story

    # -- section builders ---------------------------------------------------
    def _cover(self, analysis: dict, document: dict | None, summary: dict) -> list:
        generated = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC")
        document = document or {}

        cover_table = Table(
            [
                [Paragraph("SISAP", self.cover_title)],
                [
                    Paragraph(
                        "Smart Indian Standards Advisor for Procurement",
                        ParagraphStyle("cs2", parent=self.cover_sub, fontSize=11.5),
                    )
                ],
                [Spacer(1, 4)],
                [
                    Paragraph(
                        "Procurement Standards Analysis Report",
                        ParagraphStyle(
                            "cs3", parent=self.cover_sub, fontSize=9.5, textColor=colors.HexColor("#9FB8D0")
                        ),
                    )
                ],
            ],
            colWidths=[178 * mm],
        )
        cover_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10 * mm),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10 * mm),
                    ("TOPPADDING", (0, 0), (0, 0), 11 * mm),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 11 * mm),
                    ("TOPPADDING", (0, 1), (-1, -1), 2),
                ]
            )
        )

        meta_rows = [
            ["Product identified", analysis.get("product") or "Not identified"],
            ["Product category", analysis.get("category") or "Not identified"],
            ["Document ID", analysis.get("document_id", "-")],
            ["Document file", document.get("original_filename", "-")],
            ["Pages", str(document.get("page_count", "-"))],
            ["Requirement extraction", analysis.get("extraction_method", "rule-based")],
            ["Standards identified", str(summary.get("total", 0))],
            ["Potential gaps", str(summary.get("potential_gaps", 0))],
            ["Report generated", generated],
            ["Validation source", "Curated demo dataset (not verified against the live BIS catalogue)"],
        ]
        meta_table = Table(meta_rows, colWidths=[45 * mm, 133 * mm])
        meta_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
                    ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#1B2430")),
                    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, LIGHT_BLUE]),
                    ("GRID", (0, 0), (-1, -1), 0.4, LINE_GREY),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )

        return [
            cover_table,
            Spacer(1, 8 * mm),
            meta_table,
            Spacer(1, 6 * mm),
            self._callout(
                "Potentially applicable standards identified. Review required. "
                "This report is generated from a curated demonstration dataset and does not "
                "constitute legal, regulatory or certification advice."
            ),
        ]

    def _executive_summary(self, analysis: dict, summary: dict) -> str:
        product = analysis.get("product") or "the procured product"
        top = analysis.get("recommendations", [])[:3]
        top_text = ""
        if top:
            top_text = (
                " The highest-ranked standards are "
                + ", ".join(f"{rec['standard_number']} ({rec['score']:.0f})" for rec in top)
                + "."
            )
        return (
            f"SISAP analysed the uploaded specification and identified "
            f"<b>{summary.get('total', 0)}</b> potentially applicable Indian Standards, of which "
            f"<b>{summary.get('primary', 0)}</b> are classified as primary (directly applicable), "
            f"<b>{summary.get('testing', 0)}</b> as testing, <b>{summary.get('safety', 0)}</b> as safety, "
            f"<b>{summary.get('reference', 0)}</b> as reference/normative and "
            f"<b>{summary.get('related', 0)}</b> as related.{top_text} "
            f"<b>{summary.get('potential_gaps', 0)}</b> potential specification gap(s) requiring "
            f"procurement officer review were detected. All findings below are evidence-based "
            f"recommendations drawn from stored standard metadata for {html.escape(product)}."
        )

    def _summary_table(self, summary: dict) -> Table:
        rows = [
            [
                "Primary",
                "Testing",
                "Safety",
                "Reference",
                "Installation",
                "Related",
                "High relevance",
                "Potential gaps",
            ],
            [
                str(summary.get("primary", 0)),
                str(summary.get("testing", 0)),
                str(summary.get("safety", 0)),
                str(summary.get("reference", 0)),
                str(summary.get("installation", 0)),
                str(summary.get("related", 0)),
                str(summary.get("high_relevance", 0)),
                str(summary.get("potential_gaps", 0)),
            ],
        ]
        table = Table(rows, colWidths=[22 * mm] * 6 + [26 * mm, 22 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.4, LINE_GREY),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return table

    def _confidence_bars(self, recommendations: Sequence[dict]) -> list:
        if not recommendations:
            return []
        buckets: dict[str, list[float]] = {}
        for rec in recommendations:
            buckets.setdefault(rec["type"], []).append(float(rec["score"]))
        averages = {key: sum(values) / len(values) for key, values in buckets.items() if key in TYPE_COLOURS}
        if not averages:
            return []

        flow: list = [Paragraph("Recommendation confidence by standard type", self.h3)]
        rows = []
        bar_width = 90
        for key, value in sorted(averages.items(), key=lambda item: -item[1]):
            filled = int(round(bar_width * value / 100))
            rows.append(
                [
                    Paragraph(key, self.cell_bold),
                    Paragraph(
                        f"<font color='{TYPE_COLOURS[key].hexval()}'>{'#' * max(filled, 1)}</font>"
                        f"<font color='#E3E8ED'>{'#' * max(bar_width - filled, 0)}</font>",
                        ParagraphStyle("bar", parent=self.cell, fontName="Courier", fontSize=7),
                    ),
                    Paragraph(f"{value:.0f}%", self.cell_bold),
                ]
            )
        table = Table(rows, colWidths=[26 * mm, 110 * mm, 16 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.3, LINE_GREY),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        flow.append(table)
        return flow

    def _kv_table(self, rows: Sequence[Sequence[str]]) -> Table:
        table = Table(
            [[Paragraph(str(a), self.cell_bold), Paragraph(str(b), self.cell)] for a, b in rows],
            colWidths=[48 * mm, 130 * mm],
        )
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.4, LINE_GREY),
                    ("BACKGROUND", (0, 0), (0, -1), LIGHT_BLUE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ]
            )
        )
        return table

    def _document_rows(self, analysis: dict, document: dict | None) -> list:
        document = document or {}
        requirements = document.get("requirements") or {}
        return [
            ("Document ID", analysis.get("document_id", "-")),
            ("Original filename", document.get("original_filename", "-")),
            ("Source type", document.get("source_type", "pdf")),
            ("Pages", str(document.get("page_count", "-"))),
            ("Characters extracted", str(document.get("char_count", "-"))),
            ("Extraction status", document.get("extraction_status", "-")),
            ("Scanned / image only", "Yes - OCR required" if document.get("is_scanned") else "No"),
            ("Requirement extraction method", analysis.get("extraction_method", "rule-based")),
            ("Product", requirements.get("product") or analysis.get("product") or "Not identified"),
            ("Category", requirements.get("category") or analysis.get("category") or "Not identified"),
            ("Intended use", requirements.get("intended_use") or "Not stated in the document"),
            ("Uploaded at", document.get("uploaded_at", "-")),
        ]

    def _requirements_block(self, analysis: dict) -> list:
        requirements = self._requirements_of(analysis)
        rows = []
        for label, key in [("Product", "product"), ("Category", "category"), ("Intended use", "intended_use")]:
            rows.append((label, requirements.get(key) or "Not stated"))
        for label, key in [
            ("Materials", "materials"),
            ("Technical requirements", "technical_requirements"),
            ("Performance requirements", "performance_requirements"),
            ("Safety requirements", "safety_requirements"),
            ("Testing requirements", "testing_requirements"),
            ("Installation requirements", "installation_requirements"),
            ("Certification requirements", "certification_requirements"),
        ]:
            values = requirements.get(key) or []
            rows.append((label, ", ".join(values) if values else "Not stated in the document"))
        return [self._kv_table(rows)]

    def _requirements_of(self, analysis: dict) -> dict:
        from database.repositories import document_repo

        document = document_repo.get(analysis["document_id"])
        if document and document.get("requirements"):
            return document["requirements"]
        return {
            "product": analysis.get("product", ""),
            "category": analysis.get("category", ""),
            "intended_use": "",
        }

    def _recommendations_table(self, recommendations: Sequence[dict]) -> Table:
        header = [Paragraph(text, self.cell_white) for text in ["Standard", "Type", "Relevance", "Status", "Match reason"]]
        rows = [header]
        for rec in recommendations:
            reason = rec["explanation"][0] if rec.get("explanation") else "Matched on stored metadata"
            rows.append(
                [
                    Paragraph(f"<b>{rec['standard_number']}</b><br/>{truncate(rec['title'], 110)}", self.cell),
                    Paragraph(rec["type"], self.cell),
                    Paragraph(f"{rec['score']:.0f}", self.cell_bold),
                    Paragraph(rec.get("status", "Active"), self.cell),
                    Paragraph(truncate(reason, 120), self.cell),
                ]
            )
        table = Table(rows, colWidths=[52 * mm, 20 * mm, 16 * mm, 18 * mm, 72 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("GRID", (0, 0), (-1, -1), 0.4, LINE_GREY),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FA")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                    ("ALIGN", (2, 1), (3, -1), "CENTER"),
                ]
            )
        )
        return table

    def _reasons_block(self, recommendations: Sequence[dict]) -> list:
        flow: list = []
        for rec in recommendations:
            header = Table(
                [
                    [
                        Paragraph(
                            f"<b>{rec['standard_number']}</b> &nbsp; {rec['type']} &nbsp; "
                            f"Relevance {rec['score']:.0f}",
                            self.cell_white,
                        )
                    ]
                ],
                colWidths=[178 * mm],
            )
            header.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), TYPE_COLOURS.get(rec["type"], GOVERNMENT_BLUE)),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                    ]
                )
            )
            flow.append(KeepTogether([header, Spacer(1, 3)]))
            flow.append(Paragraph("Why this standard?", self.h3))
            for item in rec.get("explanation", [])[:8]:
                flow.append(Paragraph(f"&#10003; {html.escape(item)}", self.bullet))

            breakdown = rec.get("score_breakdown") or {}
            if breakdown:
                weights = breakdown.get("weights", {})
                parts = [
                    f"{key.replace('_', ' ')} {breakdown.get(key, 0):.2f} x {weights.get(key, 0):.2f}"
                    for key in (
                        "semantic_similarity",
                        "requirement_coverage",
                        "product_match",
                        "application_match",
                        "category_match",
                    )
                    if key in breakdown
                ]
                if parts:
                    flow.append(Paragraph("Score components: " + "; ".join(parts) + ".", self.small))

            matched = rec.get("matched_requirements") or []
            missing = rec.get("missing_requirements") or []
            if matched:
                flow.append(Paragraph("Matched requirements", self.h3))
                for item in matched[:6]:
                    flow.append(Paragraph(f"&#10003; {html.escape(truncate(item, 150))}", self.bullet))
            if missing:
                flow.append(Paragraph("Requirements not stated in the tender", self.h3))
                for item in missing[:5]:
                    flow.append(Paragraph(f"&#8226; {html.escape(truncate(item, 150))}", self.bullet))

            scope = rec.get("scope") or ""
            if scope:
                flow.append(Paragraph(f"<b>Scope:</b> {html.escape(truncate(scope, 320))}", self.small))
            flow.append(Spacer(1, 7))
        return flow

    def _related_table(self, recommendations: Sequence[dict]) -> Table:
        rows = [[Paragraph(text, self.cell_white) for text in ["Standard", "Type", "Related / referenced standards"]]]
        for rec in recommendations:
            related = rec.get("related_standards") or []
            rows.append(
                [
                    Paragraph(f"<b>{rec['standard_number']}</b>", self.cell),
                    Paragraph(rec["type"], self.cell),
                    Paragraph(", ".join(related) if related else "None recorded in the dataset", self.cell),
                ]
            )
        table = Table(rows, colWidths=[50 * mm, 22 * mm, 106 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("GRID", (0, 0), (-1, -1), 0.4, LINE_GREY),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FA")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ]
            )
        )
        return table

    def _validation_table(self, recommendations: Sequence[dict]) -> Table:
        rows = [
            [
                Paragraph(text, self.cell_white)
                for text in ["Standard", "Version", "Status", "Amendments", "Validation checks"]
            ]
        ]
        for rec in recommendations:
            validation = rec.get("validation") or {}
            amendments = validation.get("amendments") or []
            checks = validation.get("checks") or []
            rows.append(
                [
                    Paragraph(f"<b>{rec['standard_number']}</b>", self.cell),
                    Paragraph(str(validation.get("version", "-")), self.cell),
                    Paragraph(str(validation.get("status", "-")), self.cell),
                    Paragraph(", ".join(amendments) if amendments else "None recorded", self.cell),
                    Paragraph("<br/>".join(html.escape(check) for check in checks[:5]) or "-", self.cell),
                ]
            )
        table = Table(rows, colWidths=[34 * mm, 16 * mm, 18 * mm, 30 * mm, 80 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("GRID", (0, 0), (-1, -1), 0.4, LINE_GREY),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FA")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ]
            )
        )
        return table

    def _certification_table(self, recommendations: Sequence[dict]) -> Table:
        rows = [[Paragraph(text, self.cell_white) for text in ["Standard", "Certification information"]]]
        for rec in recommendations:
            certification = (
                rec.get("certification") or (rec.get("validation") or {}).get("certification") or ""
            )
            rows.append(
                [
                    Paragraph(f"<b>{rec['standard_number']}</b>", self.cell),
                    Paragraph(
                        html.escape(certification)
                        if certification
                        else "Not available in the current dataset.",
                        self.cell,
                    ),
                ]
            )
        table = Table(rows, colWidths=[52 * mm, 126 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("GRID", (0, 0), (-1, -1), 0.4, LINE_GREY),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FA")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ]
            )
        )
        return table

    def _gaps_block(self, gaps: Sequence[dict]) -> list:
        if not gaps:
            return [
                Paragraph(
                    "No specification gaps were detected against the recommended standards. "
                    "This does not mean the tender is compliant - review is still required.",
                    self.body,
                )
            ]
        flow = [
            Paragraph(
                "Potential gaps requiring procurement officer review. SISAP does not declare a tender "
                "legally compliant or non-compliant.",
                self.small,
            ),
            Spacer(1, 4),
        ]
        rows = [[Paragraph(text, self.cell_white) for text in ["Severity", "Gap", "Description", "Suggested action"]]]
        for gap in gaps:
            colour = SEVERITY_COLOURS.get(gap["severity"], NEUTRAL)
            rows.append(
                [
                    Paragraph(f"<b>{gap['severity']}</b>", ParagraphStyle("sev", parent=self.cell, textColor=colour)),
                    Paragraph(html.escape(gap["gap_type"]), self.cell),
                    Paragraph(html.escape(truncate(gap["description"], 260)), self.cell),
                    Paragraph(html.escape(truncate(gap["suggested_action"], 260)), self.cell),
                ]
            )
        table = Table(rows, colWidths=[18 * mm, 30 * mm, 66 * mm, 64 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("GRID", (0, 0), (-1, -1), 0.4, LINE_GREY),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FA")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ]
            )
        )
        flow.append(table)
        return flow

    def _graph_block(self, graph_payload: dict) -> list:
        nodes = graph_payload.get("nodes", [])
        edges = graph_payload.get("edges", [])
        if not nodes:
            return [Paragraph("No relationship graph could be constructed for this analysis.", self.body)]

        legend = Table(
            [
                [
                    Paragraph(f"<b>{key}</b>", ParagraphStyle("lg", parent=self.cell, textColor=colour))
                    for key, colour in TYPE_COLOURS.items()
                ]
            ],
            colWidths=[25 * mm] * 7,
        )
        legend.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.3, LINE_GREY),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        edge_rows = [[Paragraph(text, self.cell_white) for text in ["From", "Relationship", "To"]]]
        for edge in edges[:40]:
            edge_rows.append(
                [
                    Paragraph(edge["source"], self.cell),
                    Paragraph(edge["relationship"], self.cell),
                    Paragraph(edge["target"], self.cell),
                ]
            )
        edge_table = Table(edge_rows, colWidths=[60 * mm, 40 * mm, 60 * mm], repeatRows=1)
        edge_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("GRID", (0, 0), (-1, -1), 0.4, LINE_GREY),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FA")]),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        return [
            Paragraph(
                "The graph below shows the primary standard and the testing, safety, installation "
                "and reference standards reachable through the standards relationship graph.",
                self.small,
            ),
            Spacer(1, 5),
            self._graph_drawing(nodes, edges),
            Spacer(1, 4),
            legend,
            Spacer(1, 6),
            edge_table,
        ]

    def _graph_drawing(self, nodes: Sequence[dict], edges: Sequence[dict]) -> Drawing:
        width, height = 470, 250
        drawing = Drawing(width, height)

        root = next((node for node in nodes if node.get("is_root")), None) or (nodes[0] if nodes else None)
        if root is None:
            return drawing

        children = [node for node in nodes if node is not root][:10]
        node_w, node_h = 96, 30
        root_x, root_y = (width - node_w) / 2, height - node_h - 6

        positions: dict[str, tuple[float, float]] = {root["id"]: (root_x, root_y)}
        rows = [children[i : i + 5] for i in range(0, len(children), 5)]
        for row_index, row in enumerate(rows):
            row_y = root_y - 62 - row_index * 56
            spacing = width / max(len(row), 1)
            for col_index, node in enumerate(row):
                positions[node["id"]] = (spacing * col_index + (spacing - node_w) / 2, row_y)

        for edge in edges:
            source = positions.get(edge["source"])
            target = positions.get(edge["target"])
            if not source or not target:
                continue
            drawing.add(
                Line(
                    source[0] + node_w / 2,
                    source[1],
                    target[0] + node_w / 2,
                    target[1] + node_h,
                    strokeColor=LINE_GREY,
                    strokeWidth=0.8,
                    strokeDashArray=[2, 2],
                )
            )

        for node in nodes:
            position = positions.get(node["id"])
            if not position:
                continue
            x, y = position
            colour = TYPE_COLOURS.get(node.get("node_type", ""), GOVERNMENT_BLUE)
            drawing.add(
                Rect(x, y, node_w, node_h, rx=3, ry=3, fillColor=colors.white, strokeColor=colour, strokeWidth=1.1)
            )
            drawing.add(Rect(x, y, node_w, 3.5, fillColor=colour, strokeColor=None))
            label = node.get("label", node["id"])
            if len(label) > 16:
                label = label[:15] + "…"
            drawing.add(
                String(
                    x + node_w / 2,
                    y + node_h - 12,
                    label,
                    fontName="Helvetica-Bold",
                    fontSize=7.4,
                    fillColor=NAVY,
                    textAnchor="middle",
                )
            )
            drawing.add(
                String(
                    x + node_w / 2,
                    y + 5,
                    node.get("node_type", ""),
                    fontName="Helvetica",
                    fontSize=6.2,
                    fillColor=NEUTRAL,
                    textAnchor="middle",
                )
            )
        return drawing

    def _review_notes(self) -> list:
        notes = [
            "Potentially applicable standards identified. Review required.",
            "AI-generated recommendations should be reviewed by the responsible "
            "procurement/technical authority before being cited in a tender.",
            "Standard numbers, titles, editions, amendments and status values are drawn from a "
            "curated demonstration dataset and must be verified against the live BIS catalogue "
            "before use in a procurement.",
            "SISAP does not certify products and does not state that any product conforms to a "
            "standard. Certification information is indicative only.",
            "Where information was unavailable, the report states "
            '"Not available in the current dataset" rather than estimating a value.',
            "Specification gaps are described as potential gaps requiring procurement officer "
            "review; SISAP does not declare a tender legally compliant or non-compliant.",
        ]
        return [Paragraph(f"&#8226; {html.escape(note)}", self.bullet) for note in notes]

    def _data_sources(self) -> list:
        from services.standards_service import standards_service

        meta = standards_service.dataset_meta
        rows = [
            ("Dataset", meta.get("dataset_name", "SISAP Curated Demo Standards Dataset")),
            ("Dataset version", str(meta.get("dataset_version", "1.0.0"))),
            ("Last updated", str(meta.get("last_updated", "-"))),
            ("Verification status", meta.get("verification_status", "Curated demo dataset")),
            ("Standards in dataset", str(standards_service.count())),
            ("Primary source", "Bureau of Indian Standards (BIS) catalogue - public summaries"),
            ("Embedding backend", "Sentence-Transformers (all-MiniLM-L6-v2) or deterministic TF-IDF fallback"),
            ("Vector index", "FAISS inner-product index over L2-normalised embeddings"),
            ("Relationship graph", "NetworkX multigraph over the curated dataset"),
            ("Source URL", "https://www.services.bis.gov.in/"),
        ]
        return [
            Paragraph(
                "This report was produced from the SISAP curated demo dataset. It is not verified "
                "against the live BIS catalogue and contains no live BIS data.",
                self.small,
            ),
            Spacer(1, 4),
            self._kv_table(rows),
        ]

    # -- page furniture -----------------------------------------------------
    def _callout(self, text: str) -> Table:
        table = Table([[Paragraph(html.escape(text), self.body)]], colWidths=[178 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF6E5")),
                    ("BOX", (0, 0), (-1, -1), 0.7, AMBER),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return table

    def _page_decorations(self, canvas, doc) -> None:
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, A4[1] - 9 * mm, A4[0], 9 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 8.5)
        canvas.drawString(16 * mm, A4[1] - 6.4 * mm, "SISAP  |  Smart Indian Standards Advisor for Procurement")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(A4[0] - 16 * mm, A4[1] - 6.4 * mm, "Procurement Standards Analysis")

        canvas.setStrokeColor(LINE_GREY)
        canvas.setLineWidth(0.4)
        canvas.line(16 * mm, 12 * mm, A4[0] - 16 * mm, 12 * mm)
        canvas.setFillColor(NEUTRAL)
        canvas.setFont("Helvetica", 7.4)
        canvas.drawString(
            16 * mm,
            8.5 * mm,
            "Curated demo dataset - not verified against the live BIS catalogue. "
            "Recommendations require review by the responsible procurement/technical authority.",
        )
        canvas.drawRightString(A4[0] - 16 * mm, 8.5 * mm, f"Page {doc.page}")
        canvas.restoreState()


report_builder = ReportBuilder()
