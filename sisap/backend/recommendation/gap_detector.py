"""Specification gap detection.

Compares the requirements extracted from a tender against the requirement
facets of the recommended standards and reports what appears to be missing.

SISAP never declares a tender legally compliant or non-compliant: every finding
is phrased as a "potential gap requiring procurement officer review".
"""

from __future__ import annotations

import re
from typing import Sequence

from utils import get_logger

logger = get_logger("gap_detector")

STANDARD_NUMBER_RE = re.compile(r"\bIS\s?\d{3,5}(?:\s?\(Part\s?\d+\))?\s?:\s?\d{4}\b")

# Requirement dimensions compared between the tender and the standards.
DIMENSIONS: list[dict] = [
    {
        "key": "testing",
        "standard_key": "testing",
        "tender_key": "testing_requirements",
        "label": "Testing / inspection requirements",
        "absent_severity": "High",
        "action": (
            "Add the applicable testing or inspection standard to the tender and state the "
            "acceptance test regime (type tests, routine tests, third-party inspection)."
        ),
    },
    {
        "key": "safety",
        "standard_key": "safety",
        "tender_key": "safety_requirements",
        "label": "Safety requirements",
        "absent_severity": "Critical",
        "action": (
            "State the applicable safety requirements (protection against electric shock, "
            "fire, mechanical and environmental hazards) and reference the relevant safety standard."
        ),
    },
    {
        "key": "installation",
        "standard_key": "installation",
        "tender_key": "installation_requirements",
        "label": "Installation / commissioning requirements",
        "absent_severity": "Medium",
        "action": (
            "Add installation, mounting, clearance and commissioning requirements, and reference "
            "the applicable installation code of practice."
        ),
    },
    {
        "key": "certification",
        "standard_key": "certification",
        "tender_key": "certification_requirements",
        "label": "Certification / marking requirements",
        "absent_severity": "Medium",
        "action": (
            "State the certification and marking requirements expected of the supplier, and "
            "name the authority whose certification is acceptable."
        ),
    },
    {
        "key": "performance",
        "standard_key": "requirements",
        "tender_key": "performance_requirements",
        "label": "Performance requirements",
        "absent_severity": "Medium",
        "action": (
            "Add measurable performance requirements (ratings, temperature rise, efficiency, "
            "degree of protection, endurance) so that acceptance can be verified objectively."
        ),
    },
    {
        "key": "materials",
        "standard_key": "materials",
        "tender_key": "materials",
        "label": "Material specifications",
        "absent_severity": "Medium",
        "action": (
            "Specify the materials and grades to be used so that conformity can be checked "
            "against the recommended material standards."
        ),
    },
]

SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


class SpecificationGapDetector:
    """Detects potential specification gaps in a tender."""

    def detect(self, requirements: dict, recommendations: Sequence) -> list[dict]:
        gaps: list[dict] = []

        product = (requirements.get("product") or "").strip()
        if not product:
            gaps.append(
                {
                    "gap_type": "Product identification",
                    "severity": "Critical",
                    "description": (
                        "The document does not clearly identify the product being procured, "
                        "which makes it difficult to select applicable standards."
                    ),
                    "suggested_action": (
                        "State the product name, type and intended duty explicitly in the "
                        "specification (for example 'LV switchgear and controlgear assembly, "
                        "indoor, floor mounted')."
                    ),
                    "related_standards": [],
                }
            )

        cited = self._cited_standards(requirements)
        if not cited and recommendations:
            gaps.append(
                {
                    "gap_type": "Standards referenced",
                    "severity": "Medium",
                    "description": (
                        "The tender does not cite any Indian Standard. SISAP identified "
                        f"{len(recommendations)} potentially applicable standards from the "
                        "curated dataset."
                    ),
                    "suggested_action": (
                        "Cite the applicable Indian Standards (with edition year) in the "
                        "specification so that suppliers bid against a common technical baseline."
                    ),
                    "related_standards": [r.standard["id"] for r in recommendations[:5]],
                }
            )

        if cited:
            undated = [sid for sid in cited if not re.search(r":\s?\d{4}", sid)]
            if undated:
                gaps.append(
                    {
                        "gap_type": "Standard edition year",
                        "severity": "Low",
                        "description": (
                            "One or more cited standards do not include the edition year "
                            f"({', '.join(undated)}), so the applicable version is ambiguous."
                        ),
                        "suggested_action": (
                            "Quote each cited standard with its edition year, and state whether "
                            "later amendments apply."
                        ),
                        "related_standards": undated,
                    }
                )

        primaries = [r for r in recommendations if r.type == "Primary"]
        if not primaries:
            gaps.append(
                {
                    "gap_type": "Primary standard",
                    "severity": "Critical",
                    "description": (
                        "No primary (directly applicable) standard could be identified with "
                        "sufficient confidence from the curated dataset."
                    ),
                    "suggested_action": (
                        "Review the specification wording and expand the standards database, or "
                        "obtain a technical opinion on the applicable Indian Standard."
                    ),
                    "related_standards": [r.standard["id"] for r in recommendations[:5]],
                }
            )

        relevant = primaries or list(recommendations)[:5]
        for dimension in DIMENSIONS:
            provided = requirements.get(dimension["tender_key"]) or []
            expected_facets = [
                facet
                for rec in relevant
                for facet in (rec.standard.get(dimension["standard_key"]) or [])
            ]
            if not expected_facets:
                continue

            if not provided:
                gaps.append(
                    {
                        "gap_type": dimension["label"],
                        "severity": dimension["absent_severity"],
                        "description": (
                            "The tender specifies the product but does not specify "
                            f"{dimension['label'].lower()}. The recommended standards define "
                            f"{len(set(expected_facets))} such requirements."
                        ),
                        "suggested_action": dimension["action"],
                        "related_standards": [rec.standard["id"] for rec in relevant[:4]],
                    }
                )
            elif len(provided) <= 1 and len(set(expected_facets)) >= 4:
                gaps.append(
                    {
                        "gap_type": dimension["label"],
                        "severity": "Low",
                        "description": (
                            f"{dimension['label']} are mentioned only briefly "
                            f"({len(provided)} item(s)) compared with the "
                            f"{len(set(expected_facets))} requirements defined by the recommended standards."
                        ),
                        "suggested_action": dimension["action"],
                        "related_standards": [rec.standard["id"] for rec in relevant[:4]],
                    }
                )

        gaps.sort(key=lambda gap: SEVERITY_ORDER.get(gap["severity"], 9))
        return gaps

    @staticmethod
    def _cited_standards(requirements: dict) -> list[str]:
        """Find Indian Standard numbers cited anywhere in the extracted requirements."""
        text_parts = [
            str(requirements.get("product") or ""),
            str(requirements.get("intended_use") or ""),
            str(requirements.get("category") or ""),
        ]
        for key in (
            "materials",
            "technical_requirements",
            "performance_requirements",
            "safety_requirements",
            "testing_requirements",
            "installation_requirements",
            "certification_requirements",
        ):
            text_parts += [str(v) for v in (requirements.get(key) or [])]
        text = " ".join(text_parts)
        return list(dict.fromkeys(STANDARD_NUMBER_RE.findall(text)))


def summarise_gaps(gaps: Sequence[dict]) -> dict:
    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for gap in gaps:
        severity = gap.get("severity", "Medium")
        counts[severity] = counts.get(severity, 0) + 1
    return {"total": len(gaps), **counts}


gap_detector = SpecificationGapDetector()
