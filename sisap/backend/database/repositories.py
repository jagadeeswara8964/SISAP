"""Repository layer over SQLite.

Repositories return plain dictionaries / model instances and are the only
components aware of storage details. Swapping to PostgreSQL + pgvector means
re-implementing these classes, not the services above them.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import uuid4

from database.db import db
from utils import get_logger

logger = get_logger("repositories")

_LIST_FIELDS = (
    "standard_types",
    "product_types",
    "materials",
    "applications",
    "requirements",
    "testing",
    "safety",
    "installation",
    "amendments",
    "related_standards",
    "referenced_standards",
    "superseded_by",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_document_id() -> str:
    return f"DOC-{uuid4().hex[:8].upper()}"


def _dumps(value: Any) -> str | None:
    if value in (None, "", [], {}):
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _as_text(value: Any) -> str:
    """Normalise a field that may be a string or a list into a single string."""
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple, set)):
        return "; ".join(str(item) for item in value)
    return str(value)


def _loads(value: str | None) -> list:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return [part.strip() for part in str(value).split(",") if part.strip()]
    if isinstance(parsed, list):
        return parsed
    return [parsed]


def _row_to_standard(row: dict) -> dict:
    standard = dict(row)
    for field in _LIST_FIELDS:
        standard[field] = _loads(standard.get(field))
    standard["bis_verified"] = bool(standard.get("bis_verified"))
    standard.setdefault("scope", "")
    standard.setdefault("certification", "")
    standard.setdefault("source_url", "")
    return standard


class StandardsRepository:
    """Access to the curated standards catalogue."""

    def load_dataset(self, dataset: dict) -> int:
        """Upsert a dataset (dict from standards.json) into the standards table."""
        standards = dataset.get("standards", [])
        rows = []
        for std in standards:
            rows.append(
                (
                    std["id"],
                    std.get("standard_number", std["id"]),
                    std.get("title", ""),
                    std.get("scope", ""),
                    std.get("category", ""),
                    std.get("version", ""),
                    std.get("status", "Active"),
                    _as_text(std.get("certification", "")),
                    _as_text(std.get("source_url", "")),
                    _dumps(std.get("standard_types", [])),
                    _dumps(std.get("product_types", [])),
                    _dumps(std.get("materials", [])),
                    _dumps(std.get("applications", [])),
                    _dumps(std.get("requirements", [])),
                    _dumps(std.get("testing", [])),
                    _dumps(std.get("safety", [])),
                    _dumps(std.get("installation", [])),
                    _dumps(std.get("amendments", [])),
                    _dumps(std.get("related_standards", [])),
                    _dumps(std.get("referenced_standards", [])),
                    _dumps(std.get("superseded_by", [])),
                    std.get("source", "BIS"),
                    1 if std.get("bis_verified") else 0,
                )
            )
        with db.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO standards (
                    id, standard_number, title, scope, category, version, status,
                    certification, source_url, standard_types, product_types, materials,
                    applications, requirements, testing, safety, installation, amendments,
                    related_standards, referenced_standards, superseded_by, source, bis_verified
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    standard_number=excluded.standard_number, title=excluded.title,
                    scope=excluded.scope, category=excluded.category, version=excluded.version,
                    status=excluded.status, certification=excluded.certification,
                    source_url=excluded.source_url, standard_types=excluded.standard_types,
                    product_types=excluded.product_types, materials=excluded.materials,
                    applications=excluded.applications, requirements=excluded.requirements,
                    testing=excluded.testing, safety=excluded.safety,
                    installation=excluded.installation, amendments=excluded.amendments,
                    related_standards=excluded.related_standards,
                    referenced_standards=excluded.referenced_standards,
                    superseded_by=excluded.superseded_by, source=excluded.source,
                    bis_verified=excluded.bis_verified
                """,
                rows,
            )
            self._rebuild_relationships(cur, standards)
        logger.info("loaded %d standards into the catalogue", len(standards))
        return len(standards)

    @staticmethod
    def _rebuild_relationships(cur, standards: Iterable[dict]) -> None:
        """Populate the relationship table from the dataset's link fields."""
        cur.execute("DELETE FROM standard_relationships")
        rows = []
        for std in standards:
            source = std["id"]
            for target in std.get("related_standards", []) or []:
                rows.append((source, target, "related"))
            for target in std.get("referenced_standards", []) or []:
                rows.append((source, target, "references"))
            for target in std.get("superseded_by", []) or []:
                rows.append((source, target, "supersedes"))
        if rows:
            cur.executemany(
                "INSERT OR IGNORE INTO standard_relationships (source_standard, target_standard, relationship_type)"
                " VALUES (?,?,?)",
                rows,
            )

    def count(self) -> int:
        row = db.query_one("SELECT COUNT(*) AS n FROM standards")
        return int(row["n"]) if row else 0

    def get_all(self) -> list[dict]:
        rows = db.query_all("SELECT * FROM standards ORDER BY standard_number")
        return [_row_to_standard(row) for row in rows]

    def get_by_id(self, standard_id: str) -> dict | None:
        row = db.query_one("SELECT * FROM standards WHERE id = ?", (standard_id,))
        return _row_to_standard(row) if row else None

    def get_many(self, ids: Iterable[str]) -> list[dict]:
        ids = [i for i in ids if i]
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = db.query_all(f"SELECT * FROM standards WHERE id IN ({placeholders})", tuple(ids))
        return [_row_to_standard(row) for row in rows]

    def search(
        self,
        query: str = "",
        category: str = "",
        standard_type: str = "",
        status: str = "",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[int, list[dict]]:
        """Filtered keyword search over the catalogue with pagination."""
        clauses, params = [], []
        if query:
            like = f"%{query.strip()}%"
            clauses.append(
                "(id LIKE ? OR standard_number LIKE ? OR title LIKE ? OR scope LIKE ?"
                " OR product_types LIKE ? OR category LIKE ?)"
            )
            params.extend([like] * 6)
        if category:
            clauses.append("category = ?")
            params.append(category)
        if standard_type:
            clauses.append("standard_types LIKE ?")
            params.append(f"%{standard_type}%")
        if status:
            clauses.append("status = ?")
            params.append(status)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        total_row = db.query_one(f"SELECT COUNT(*) AS n FROM standards {where}", tuple(params))
        total = int(total_row["n"]) if total_row else 0

        offset = max(page - 1, 0) * page_size
        rows = db.query_all(
            f"SELECT * FROM standards {where} ORDER BY standard_number LIMIT ? OFFSET ?",
            (*params, page_size, offset),
        )
        return total, [_row_to_standard(row) for row in rows]

    def categories(self) -> dict[str, int]:
        rows = db.query_all("SELECT category, COUNT(*) AS n FROM standards GROUP BY category ORDER BY n DESC")
        return {row["category"] or "Uncategorised": int(row["n"]) for row in rows}

    def relationships_for(self, standard_id: str) -> list[dict]:
        rows = db.query_all(
            """
            SELECT source_standard, target_standard, relationship_type
            FROM standard_relationships
            WHERE source_standard = ? OR target_standard = ?
            """,
            (standard_id, standard_id),
        )
        return [
            {
                "source": row["source_standard"],
                "target": row["target_standard"],
                "relationship_type": row["relationship_type"],
            }
            for row in rows
        ]


class DocumentRepository:
    """Uploaded documents and their extracted requirements."""

    def create(
        self,
        filename: str,
        extracted_text: str,
        page_count: int,
        is_scanned: bool,
        extraction_status: str = "ok",
        source_type: str = "pdf",
        original_filename: str | None = None,
    ) -> dict:
        doc_id = _new_document_id()
        with db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (id, filename, original_filename, extracted_text, page_count,
                                       char_count, is_scanned, extraction_status, source_type, uploaded_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    doc_id,
                    filename,
                    original_filename or filename,
                    extracted_text,
                    page_count,
                    len(extracted_text or ""),
                    1 if is_scanned else 0,
                    extraction_status,
                    source_type,
                    _now(),
                ),
            )
        return self.get(doc_id)  # type: ignore[return-value]

    def get(self, document_id: str) -> dict | None:
        row = db.query_one("SELECT * FROM documents WHERE id = ?", (document_id,))
        if not row:
            return None
        doc = dict(row)
        doc["is_scanned"] = bool(doc["is_scanned"])
        requirements = self.get_requirements(document_id)
        doc["requirements"] = requirements
        doc["requirements_extracted"] = requirements is not None
        doc["text_preview"] = (doc.get("extracted_text") or "")[:1200]
        return doc

    def get_text(self, document_id: str) -> str:
        row = db.query_one("SELECT extracted_text FROM documents WHERE id = ?", (document_id,))
        return (row or {}).get("extracted_text") or ""

    def list_recent(self, limit: int = 20) -> list[dict]:
        return db.query_all("SELECT * FROM documents ORDER BY uploaded_at DESC LIMIT ?", (limit,))

    def save_requirements(self, document_id: str, requirements: dict, method: str) -> None:
        with db.cursor() as cur:
            cur.execute("DELETE FROM extracted_requirements WHERE document_id = ?", (document_id,))
            cur.execute(
                """
                INSERT INTO extracted_requirements (
                    document_id, product, category, intended_use, materials,
                    technical_requirements, performance_requirements, safety_requirements,
                    testing_requirements, installation_requirements, certification_requirements,
                    extraction_method, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    document_id,
                    requirements.get("product", ""),
                    requirements.get("category", ""),
                    requirements.get("intended_use", ""),
                    _dumps(requirements.get("materials", [])),
                    _dumps(requirements.get("technical_requirements", [])),
                    _dumps(requirements.get("performance_requirements", [])),
                    _dumps(requirements.get("safety_requirements", [])),
                    _dumps(requirements.get("testing_requirements", [])),
                    _dumps(requirements.get("installation_requirements", [])),
                    _dumps(requirements.get("certification_requirements", [])),
                    method,
                    _now(),
                ),
            )

    def get_requirements(self, document_id: str) -> dict | None:
        row = db.query_one(
            "SELECT * FROM extracted_requirements WHERE document_id = ? ORDER BY id DESC LIMIT 1",
            (document_id,),
        )
        if not row:
            return None
        result = {
            "product": row.get("product") or "",
            "category": row.get("category") or "",
            "intended_use": row.get("intended_use") or "",
            "materials": _loads(row.get("materials")),
            "technical_requirements": _loads(row.get("technical_requirements")),
            "performance_requirements": _loads(row.get("performance_requirements")),
            "safety_requirements": _loads(row.get("safety_requirements")),
            "testing_requirements": _loads(row.get("testing_requirements")),
            "installation_requirements": _loads(row.get("installation_requirements")),
            "certification_requirements": _loads(row.get("certification_requirements")),
            "extraction_method": row.get("extraction_method") or "",
        }
        return result


class RecommendationRepository:
    def replace(self, document_id: str, recommendations: list[dict]) -> None:
        with db.cursor() as cur:
            cur.execute("DELETE FROM recommendations WHERE document_id = ?", (document_id,))
            for rec in recommendations:
                cur.execute(
                    """
                    INSERT INTO recommendations (
                        document_id, standard_id, score, category, explanation,
                        matched_requirements, missing_requirements, related_standards,
                        validation_status, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        document_id,
                        rec["standard_id"],
                        rec.get("score", 0.0),
                        rec.get("type", rec.get("category", "Related")),
                        _dumps(rec.get("explanation", [])),
                        _dumps(rec.get("matched_requirements", [])),
                        _dumps(rec.get("missing_requirements", [])),
                        _dumps(rec.get("related_standards", [])),
                        _dumps(rec.get("validation", {})),
                        _now(),
                    ),
                )

    def get(self, document_id: str) -> list[dict]:
        rows = db.query_all(
            "SELECT * FROM recommendations WHERE document_id = ? ORDER BY score DESC", (document_id,)
        )
        results = []
        for row in rows:
            rec = dict(row)
            rec["explanation"] = _loads(rec.get("explanation"))
            rec["matched_requirements"] = _loads(rec.get("matched_requirements"))
            rec["missing_requirements"] = _loads(rec.get("missing_requirements"))
            rec["related_standards"] = _loads(rec.get("related_standards"))
            validation = _loads(rec.get("validation_status"))
            rec["validation"] = validation[0] if validation else None
            results.append(rec)
        return results

    def count_all(self) -> int:
        row = db.query_one("SELECT COUNT(*) AS n FROM recommendations")
        return int(row["n"]) if row else 0


class GapRepository:
    def replace(self, document_id: str, gaps: list[dict]) -> None:
        with db.cursor() as cur:
            cur.execute("DELETE FROM specification_gaps WHERE document_id = ?", (document_id,))
            for gap in gaps:
                cur.execute(
                    """
                    INSERT INTO specification_gaps (
                        document_id, gap_type, severity, description, suggested_action,
                        related_standards, created_at)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    (
                        document_id,
                        gap.get("gap_type", ""),
                        gap.get("severity", "Medium"),
                        gap.get("description", ""),
                        gap.get("suggested_action", ""),
                        _dumps(gap.get("related_standards", [])),
                        _now(),
                    ),
                )

    def get(self, document_id: str) -> list[dict]:
        rows = db.query_all(
            "SELECT * FROM specification_gaps WHERE document_id = ? ORDER BY"
            " CASE severity WHEN 'Critical' THEN 0 WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END",
            (document_id,),
        )
        for row in rows:
            row["related_standards"] = _loads(row.get("related_standards"))
        return rows

    def count_all(self) -> int:
        row = db.query_one("SELECT COUNT(*) AS n FROM specification_gaps")
        return int(row["n"]) if row else 0


standards_repo = StandardsRepository()
document_repo = DocumentRepository()
recommendation_repo = RecommendationRepository()
gap_repo = GapRepository()
