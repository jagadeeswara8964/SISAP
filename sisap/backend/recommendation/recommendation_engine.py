"""Standards recommendation engine.

Pipeline:
    requirements -> query embedding -> FAISS similarity search -> candidate
    standards -> requirement coverage -> product / application / category
    matching -> relationship expansion -> validation -> final ranking

The final score is a weighted composite, never raw cosine similarity:

    final_score = semantic_similarity   * 0.45
                + requirement_coverage  * 0.25
                + product_match         * 0.15
                + application_match     * 0.10
                + category_match        * 0.05      (normalised to 0-100)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from ai.embeddings import embedding_service
from ai.vector_store import SearchHit, vector_store
from utils import get_logger, truncate

logger = get_logger("recommendation")

SCORE_WEIGHTS = {
    "semantic_similarity": 0.45,
    "requirement_coverage": 0.25,
    "product_match": 0.15,
    "application_match": 0.10,
    "category_match": 0.05,
}

# Below this composite score a standard is not surfaced at all.
MIN_SCORE = 22.0
# Score at/above which a standard is treated as a primary (directly applicable) standard.
PRIMARY_SCORE_THRESHOLD = 45.0
# Relationship expansion keeps neighbours at/above this score.
EXPANSION_SCORE_THRESHOLD = 18.0

TYPE_PRIORITY = {
    "Primary": 0,
    "Testing": 1,
    "Safety": 2,
    "Installation": 3,
    "Terminology": 4,
    "Reference": 5,
    "Related": 6,
}

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "shall", "must", "should", "are", "was",
    "were", "have", "has", "been", "being", "not", "any", "all", "each", "other", "than", "then",
    "into", "onto", "over", "under", "when", "where", "which", "while", "also", "such", "use",
    "used", "using", "may", "can", "will", "per", "via", "its", "their", "there", "here", "more",
    "most", "some", "only", "very", "both", "same", "does", "did", "but", "out", "who", "whom",
    "between", "during", "after", "before", "because", "about", "against", "above", "below",
}

REQUIREMENT_FACET_KEYS = ("requirements", "testing", "safety", "installation")


@dataclass
class CandidateScore:
    semantic_similarity: float = 0.0
    requirement_coverage: float = 0.0
    product_match: float = 0.0
    application_match: float = 0.0
    category_match: float = 0.0

    @property
    def final(self) -> float:
        total = (
            self.semantic_similarity * SCORE_WEIGHTS["semantic_similarity"]
            + self.requirement_coverage * SCORE_WEIGHTS["requirement_coverage"]
            + self.product_match * SCORE_WEIGHTS["product_match"]
            + self.application_match * SCORE_WEIGHTS["application_match"]
            + self.category_match * SCORE_WEIGHTS["category_match"]
        )
        return round(min(max(total, 0.0), 1.0) * 100, 1)

    def breakdown(self) -> dict[str, float]:
        return {
            "semantic_similarity": round(self.semantic_similarity, 3),
            "requirement_coverage": round(self.requirement_coverage, 3),
            "product_match": round(self.product_match, 3),
            "application_match": round(self.application_match, 3),
            "category_match": round(self.category_match, 3),
            "weights": dict(SCORE_WEIGHTS),
        }


@dataclass
class Recommendation:
    standard: dict
    type: str = "Related"
    score: float = 0.0
    score_breakdown: dict = field(default_factory=dict)
    explanation: list[str] = field(default_factory=list)
    matched_requirements: list[str] = field(default_factory=list)
    missing_requirements: list[str] = field(default_factory=list)
    related_standards: list[str] = field(default_factory=list)
    relationship_path: str = ""


class StandardRecommendationEngine:
    """Ranks standards for a set of extracted requirements."""

    def __init__(self, standards: Sequence[dict]) -> None:
        self._standards = {std["id"]: std for std in standards}
        self._searchable: dict[str, str] = {sid: build_searchable_text(std) for sid, std in self._standards.items()}

    # -- index --------------------------------------------------------------
    def build_index(self, force: bool = False) -> int:
        """Build (or reuse) the FAISS index over the standards corpus."""
        ids = list(self._searchable.keys())
        if not force and vector_store.load():
            if vector_store.size == len(ids):
                logger.info("reusing persisted FAISS index (%d vectors)", vector_store.size)
                return vector_store.size
            vector_store.reset()

        corpus = [self._searchable[sid] for sid in ids]
        embedding_service.ensure_ready(corpus)
        vectors = embedding_service.encode(corpus)
        vector_store.build(
            vectors,
            ids,
            meta={
                "backend": embedding_service.backend_name,
                "model": settings_embedding_model(),
                "dimension": int(vectors.shape[1]),
                "count": len(ids),
                "source": "SISAP curated demo standards dataset",
            },
        )
        return len(ids)

    # -- recommendation -----------------------------------------------------
    def recommend(
        self,
        requirements: dict,
        top_k: int = 60,
        standards_graph=None,
        validator=None,
    ) -> list[Recommendation]:
        query_text = build_query_text(requirements)
        if not query_text.strip():
            logger.warning("empty query text; no recommendations produced")
            return []

        embedding_service.ensure_ready([self._searchable[sid] for sid in self._searchable])
        query_vector = embedding_service.encode([query_text])[0]
        hits = vector_store.search_one(query_vector, top_k=top_k)

        tender_tokens = tokenise(query_text)
        tender_products = set(lower_all(requirements.get("materials", []) or []))
        product_terms = extract_product_terms(requirements)
        application_terms = extract_application_terms(requirements)
        category = (requirements.get("category") or "").strip()

        scored: dict[str, CandidateScore] = {}
        for hit in hits:
            standard = self._standards.get(hit.standard_id)
            if standard is None:
                continue
            candidate = self._score(
                standard=standard,
                semantic=hit.score,
                tender_tokens=tender_tokens,
                product_terms=product_terms,
                application_terms=application_terms,
                category=category,
            )
            scored[standard["id"]] = candidate

        candidates = [
            (sid, candidate) for sid, candidate in scored.items() if candidate.final >= MIN_SCORE
        ]
        candidates.sort(key=lambda item: (-item[1].final, item[0]))

        recommendations: list[Recommendation] = []
        primary_ids: list[str] = []

        for sid, candidate in candidates:
            standard = self._standards[sid]
            base_type = classify_base_type(standard)
            # A standard is only "Primary" when it is both a product/assembly
            # standard AND scores above the primary threshold; below that it is
            # reported as a potentially relevant (related) standard.
            if base_type == "Primary":
                rec_type = "Primary" if candidate.final >= PRIMARY_SCORE_THRESHOLD else "Related"
                if rec_type == "Primary":
                    primary_ids.append(sid)
            else:
                rec_type = base_type
            recommendations.append(
                self._build_recommendation(standard, candidate, rec_type, tender_tokens)
            )

        # ---- relationship expansion --------------------------------------
        if standards_graph is not None and primary_ids:
            seen = {rec.standard["id"] for rec in recommendations}
            for primary_id in primary_ids:
                for neighbour_id, relationship in standards_graph.expand(primary_id):
                    if neighbour_id in seen or neighbour_id not in self._standards:
                        continue
                    neighbour = self._standards[neighbour_id]
                    candidate = self._score(
                        standard=neighbour,
                        semantic=0.0,
                        tender_tokens=tender_tokens,
                        product_terms=product_terms,
                        application_terms=application_terms,
                        category=category,
                    )
                    if candidate.final < EXPANSION_SCORE_THRESHOLD:
                        continue
                    seen.add(neighbour_id)
                    recommendations.append(
                        self._build_recommendation(
                            neighbour,
                            candidate,
                            classify_expanded_type(neighbour, relationship),
                            tender_tokens,
                            relationship=relationship,
                            root=primary_id,
                        )
                    )

        # ---- superseded edition handling ---------------------------------
        superseded_seen = {rec.standard["id"] for rec in recommendations}
        for rec in list(recommendations):
            standard = rec.standard
            if standard.get("status") == "Superseded":
                for successor_id in standard.get("superseded_by", []) or []:
                    if successor_id in superseded_seen or successor_id not in self._standards:
                        continue
                    successor = self._standards[successor_id]
                    candidate = self._score(
                        standard=successor,
                        semantic=0.0,
                        tender_tokens=tender_tokens,
                        product_terms=product_terms,
                        application_terms=application_terms,
                        category=category,
                    )
                    superseded_seen.add(successor_id)
                    recommendations.append(
                        self._build_recommendation(
                            successor,
                            candidate,
                            classify_base_type(successor),
                            tender_tokens,
                            relationship="supersedes",
                            root=standard["id"],
                        )
                    )

        recommendations.sort(
            key=lambda rec: (TYPE_PRIORITY.get(rec.type, 9), -rec.score, rec.standard["id"])
        )
        return recommendations

    # -- scoring ------------------------------------------------------------
    def _score(
        self,
        standard: dict,
        semantic: float,
        tender_tokens: set[str],
        product_terms: set[str],
        application_terms: set[str],
        category: str,
    ) -> CandidateScore:
        semantic_similarity = min(max(semantic, 0.0), 1.0)

        facets: list[str] = []
        for key in REQUIREMENT_FACET_KEYS:
            facets.extend(standard.get(key, []) or [])
        facets = dedupe(facets)
        if facets:
            matched = sum(1 for facet in facets if facet_matches_text(facet, tender_tokens))
            coverage = matched / len(facets)
        else:
            coverage = 0.0

        std_products = {p.lower() for p in standard.get("product_types", []) or []}
        if std_products:
            shared = [p for p in std_products if any(token in p or p in token for token in product_terms)]
            product_match = min(1.0, len(shared) / 3.0)
        else:
            product_match = 0.0

        std_applications = {a.lower() for a in standard.get("applications", []) or []}
        if std_applications:
            shared_apps = [a for a in std_applications if any(token in a for token in application_terms)]
            application_match = min(1.0, len(shared_apps) / 2.0)
        else:
            application_match = 0.0

        category_match = 1.0 if category and standard.get("category", "") == category else 0.0

        return CandidateScore(
            semantic_similarity=semantic_similarity,
            requirement_coverage=coverage,
            product_match=product_match,
            application_match=application_match,
            category_match=category_match,
        )

    # -- explanation --------------------------------------------------------
    def _build_recommendation(
        self,
        standard: dict,
        candidate: CandidateScore,
        rec_type: str,
        tender_tokens: set[str],
        relationship: str = "",
        root: str = "",
    ) -> Recommendation:
        explanation: list[str] = []
        matched: list[str] = []
        missing: list[str] = []

        facets_by_kind: dict[str, list[str]] = {
            "requirements": dedupe(standard.get("requirements", []) or []),
            "testing": dedupe(standard.get("testing", []) or []),
            "safety": dedupe(standard.get("safety", []) or []),
            "installation": dedupe(standard.get("installation", []) or []),
        }
        for kind, facets in facets_by_kind.items():
            kind_matched = [facet for facet in facets if facet_matches_text(facet, tender_tokens)]
            kind_missing = [facet for facet in facets if facet not in kind_matched]
            matched.extend(kind_matched)
            missing.extend(kind_missing)

            if kind_matched:
                label = {
                    "requirements": "Technical requirement overlap",
                    "testing": "Testing requirement overlap",
                    "safety": "Safety requirement overlap",
                    "installation": "Installation requirement overlap",
                }[kind]
                explanation.append(f"{label}: {truncate(kind_matched[0], 90)}")

        # product / application / material evidence
        product_evidence = [p for p in standard.get("product_types", []) or [] if facet_matches_text(p, tender_tokens)]
        if product_evidence:
            explanation.append(f"Product type matches: {truncate(', '.join(product_evidence[:3]), 90)}")

        application_evidence = [
            a for a in standard.get("applications", []) or [] if facet_matches_text(a, tender_tokens)
        ]
        if application_evidence:
            explanation.append(f"Intended application matches: {truncate(application_evidence[0], 90)}")

        material_evidence = [m for m in standard.get("materials", []) or [] if facet_matches_text(m, tender_tokens)]
        if material_evidence:
            explanation.append(f"Material requirement matches: {truncate(', '.join(material_evidence[:3]), 90)}")

        if relationship and root:
            explanation.append(f"Linked to {root} by '{{relationship}}' relationship".replace("{relationship}", relationship))

        if candidate.category_match:
            explanation.append(f"Category match: {standard.get('category', '')}")

        if standard.get("status") == "Superseded" and standard.get("superseded_by"):
            explanation.append(
                f"Superseded edition detected - current edition: {', '.join(standard['superseded_by'])}"
            )

        if candidate.semantic_similarity > 0:
            explanation.append(f"Semantic similarity to specification text: {candidate.semantic_similarity:.2f}")

        if not explanation:
            explanation.append("Matched on stored standard metadata (scope, requirements and relationships).")

        return Recommendation(
            standard=standard,
            type=rec_type,
            score=candidate.final,
            score_breakdown=candidate.breakdown(),
            explanation=explanation,
            matched_requirements=matched[:12],
            missing_requirements=missing[:10],
            related_standards=dedupe(
                list(standard.get("related_standards", []) or []) + list(standard.get("referenced_standards", []) or [])
            )[:12],
            relationship_path=f"{root} -> {standard['id']}" if root else "",
        )


# --------------------------------------------------------------------- helpers
def settings_embedding_model() -> str:
    from config import settings

    return settings.embedding_model


def build_searchable_text(standard: dict) -> str:
    """Combined searchable text: TITLE + SCOPE + PRODUCT TYPES + APPLICATIONS + REQUIREMENTS."""
    parts = [
        standard.get("title", ""),
        standard.get("scope", ""),
        "Products: " + ", ".join(standard.get("product_types", []) or []),
        "Applications: " + ", ".join(standard.get("applications", []) or []),
        "Requirements: "
        + ", ".join(
            dedupe(
                list(standard.get("requirements", []) or [])
                + list(standard.get("testing", []) or [])
                + list(standard.get("safety", []) or [])
                + list(standard.get("installation", []) or [])
            )
        ),
        "Materials: " + ", ".join(standard.get("materials", []) or []),
        "Category: " + standard.get("category", ""),
    ]
    return " ".join(part for part in parts if part).strip()


def build_query_text(requirements: dict) -> str:
    """Turn a requirement object into a semantic search query."""
    parts: list[str] = []
    for key in ("product", "category", "intended_use"):
        value = (requirements.get(key) or "").strip()
        if value:
            parts.append(value)
    for key in (
        "materials",
        "technical_requirements",
        "performance_requirements",
        "safety_requirements",
        "testing_requirements",
        "installation_requirements",
        "certification_requirements",
    ):
        values = requirements.get(key) or []
        if values:
            parts.append(", ".join(str(v) for v in values))
    return " ".join(parts).strip()


def tokenise(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {token for token in tokens if len(token) > 2 and token not in STOPWORDS}


def lower_all(values: Iterable[str]) -> list[str]:
    return [str(value).lower() for value in values]


def extract_product_terms(requirements: dict) -> set[str]:
    """Product-ish terms from the requirement object, including phrase fragments."""
    values: list[str] = [str(requirements.get("product") or "")]
    values += [str(v) for v in (requirements.get("materials") or [])]
    values += [str(v) for v in (requirements.get("technical_requirements") or [])]
    values += [str(v) for v in (requirements.get("performance_requirements") or [])]

    terms: set[str] = set()
    for value in values:
        if not value:
            continue
        terms.add(value.lower())
        terms.update(tokenise(value))
    return {term for term in terms if term}


def extract_application_terms(requirements: dict) -> set[str]:
    values: list[str] = [str(requirements.get("intended_use") or "")]
    values += [str(v) for v in (requirements.get("installation_requirements") or [])]
    values += [str(v) for v in (requirements.get("technical_requirements") or [])]
    terms: set[str] = set()
    for value in values:
        if not value:
            continue
        terms.add(value.lower())
        terms.update(tokenise(value))
    return {term for term in terms if term}


def facet_tokens(facet: str) -> set[str]:
    return tokenise(facet)


def facet_matches_text(facet: str, tender_tokens: set[str]) -> bool:
    """True when enough of a standard facet's tokens appear in the tender text."""
    tokens = facet_tokens(facet)
    if not tokens:
        return False
    hits = sum(1 for token in tokens if token in tender_tokens)
    return hits / len(tokens) >= 0.6


def dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = str(value).strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(str(value).strip())
    return result


def classify_base_type(standard: dict) -> str:
    """Classify a standard from its own stored metadata."""
    types = {t.lower() for t in standard.get("standard_types", []) or []}

    if "testing" in types or "method standard" in types:
        return "Testing"
    if "safety" in types and "primary" not in types:
        return "Safety"
    if ("installation" in types or "code of practice" in types) and "primary" not in types:
        return "Installation"
    if "terminology and dimensions" in types or ("terminology" in types and "primary" not in types):
        return "Terminology"
    if "reference" in types and "primary" not in types:
        return "Reference"
    if "primary" in types or "assembly" in types or "general requirements" in types:
        return "Primary"
    return "Related"


def classify_expanded_type(standard: dict, relationship: str) -> str:
    """Classify a standard reached through graph expansion."""
    base = classify_base_type(standard)
    if base in {"Testing", "Safety", "Installation", "Terminology"}:
        return base
    if relationship == "references":
        return "Reference"
    return "Related"
