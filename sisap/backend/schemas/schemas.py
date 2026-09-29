"""Pydantic schemas for the SISAP REST API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

RecommendationCategory = Literal[
    "Primary",
    "Testing",
    "Safety",
    "Reference",
    "Installation",
    "Terminology",
    "Related",
]

GapSeverity = Literal["Critical", "High", "Medium", "Low"]


# --------------------------------------------------------------------- standards
class StandardBase(BaseModel):
    id: str
    standard_number: str
    title: str
    scope: str = ""
    category: str = ""
    version: str = ""
    status: str = "Active"
    certification: str = ""
    source: str = "BIS"
    source_url: str = ""
    standard_types: list[str] = Field(default_factory=list)
    product_types: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    applications: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    testing: list[str] = Field(default_factory=list)
    safety: list[str] = Field(default_factory=list)
    installation: list[str] = Field(default_factory=list)
    amendments: list[str] = Field(default_factory=list)
    related_standards: list[str] = Field(default_factory=list)
    referenced_standards: list[str] = Field(default_factory=list)
    superseded_by: list[str] = Field(default_factory=list)
    bis_verified: bool = False


class StandardOut(StandardBase):
    pass


class StandardSummary(BaseModel):
    id: str
    standard_number: str
    title: str
    category: str
    version: str
    status: str
    standard_types: list[str] = Field(default_factory=list)


class StandardsPage(BaseModel):
    total: int
    page: int
    page_size: int
    standards: list[StandardSummary]


# -------------------------------------------------------------------- documents
class RequirementObject(BaseModel):
    """Structured requirements extracted from a tender/specification document."""

    product: str = ""
    category: str = ""
    intended_use: str = ""
    materials: list[str] = Field(default_factory=list)
    technical_requirements: list[str] = Field(default_factory=list)
    performance_requirements: list[str] = Field(default_factory=list)
    safety_requirements: list[str] = Field(default_factory=list)
    testing_requirements: list[str] = Field(default_factory=list)
    installation_requirements: list[str] = Field(default_factory=list)
    certification_requirements: list[str] = Field(default_factory=list)


class DocumentOut(BaseModel):
    id: str
    filename: str
    page_count: int = 0
    char_count: int = 0
    is_scanned: bool = False
    extraction_status: str = "ok"
    source_type: str = "pdf"
    uploaded_at: str = ""
    requirements: RequirementObject | None = None
    requirements_extracted: bool = False
    extraction_method: str = ""
    text_preview: str = ""


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    page_count: int
    char_count: int
    is_scanned: bool
    extraction_status: str
    message: str = ""


class RecommendRequest(BaseModel):
    document_id: str | None = None
    text: str | None = Field(default=None, description="Manually pasted specification text")
    use_llm: bool = False


class ExtractRequest(BaseModel):
    document_id: str | None = None
    text: str | None = Field(default=None, description="Manually pasted specification text")
    use_llm: bool = False


class SectionInfo(BaseModel):
    key: str
    title: str
    characters: int = 0


class ExtractResponse(BaseModel):
    document_id: str
    requirements: RequirementObject
    extraction_method: str
    text_available: bool
    sections: list[SectionInfo] = Field(default_factory=list)


# --------------------------------------------------------------- recommendations
class ValidationOut(BaseModel):
    standard_id: str
    status: str = ""
    version: str = ""
    amendments: list[str] = Field(default_factory=list)
    superseded_by: list[str] = Field(default_factory=list)
    certification: str = ""
    checks: list[str] = Field(default_factory=list)
    validation_source: str = "Curated demo dataset"


class RecommendationOut(BaseModel):
    standard_id: str
    standard_number: str
    title: str
    category: str
    type: RecommendationCategory = "Related"
    score: float = 0.0
    status: str = "Active"
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    explanation: list[str] = Field(default_factory=list)
    matched_requirements: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    related_standards: list[str] = Field(default_factory=list)
    validation: ValidationOut | None = None
    scope: str = ""


class RecommendationSummary(BaseModel):
    total: int = 0
    primary: int = 0
    testing: int = 0
    safety: int = 0
    reference: int = 0
    installation: int = 0
    terminology: int = 0
    related: int = 0
    high_relevance: int = 0
    potential_gaps: int = 0


class RecommendationResponse(BaseModel):
    document_id: str
    product: str = ""
    category: str = ""
    summary: RecommendationSummary
    recommendations: list[RecommendationOut] = Field(default_factory=list)
    gaps: list[GapOut] = Field(default_factory=list)
    sections: list[SectionInfo] = Field(default_factory=list)
    extraction_method: str = "rule-based"
    generated_at: str = ""
    review_note: str = (
        "AI-generated recommendations should be reviewed by the responsible "
        "procurement/technical authority."
    )


class GapOut(BaseModel):
    gap_type: str
    severity: GapSeverity
    description: str
    suggested_action: str
    related_standards: list[str] = Field(default_factory=list)


class GapsResponse(BaseModel):
    document_id: str
    total: int
    critical: int
    high: int
    medium: int
    low: int
    gaps: list[GapOut]
    review_note: str = (
        "Potential gaps requiring procurement officer review. "
        "SISAP does not declare a tender legally compliant or non-compliant."
    )


# ------------------------------------------------------------------------ graph
class GraphNode(BaseModel):
    id: str
    label: str
    title: str
    node_type: str
    relationship: str = ""
    version: str = ""
    status: str = ""
    score: float | None = None
    explanation: list[str] = Field(default_factory=list)


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str


class GraphResponse(BaseModel):
    root: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    legend: dict[str, str] = Field(default_factory=dict)


# ----------------------------------------------------------------------- report
class ReportResponse(BaseModel):
    document_id: str
    report_id: str
    filename: str
    download_url: str
    generated_at: str
    sections: list[str] = Field(default_factory=list)


# -------------------------------------------------------------------- dashboard
class RecentAnalysis(BaseModel):
    document_id: str
    filename: str
    product: str
    standards: int
    gaps: int
    date: str
    status: str


class DashboardStats(BaseModel):
    documents_analyzed: int = 0
    standards_recommended: int = 0
    potential_gaps_found: int = 0
    validated_references: int = 0
    standards_in_database: int = 0
    categories: dict[str, int] = Field(default_factory=dict)
    confidence: dict[str, float] = Field(default_factory=dict)
    recent_analyses: list[RecentAnalysis] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    demo_mode: bool
    embedding_backend: str
    embedding_model: str
    standards_loaded: int
    faiss_vectors: int
    version: str
    settings: dict[str, Any]


class ErrorResponse(BaseModel):
    detail: str
    code: str = "error"
