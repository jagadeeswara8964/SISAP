"""Standards relationship graph built with NetworkX.

Edge relationship types (per product spec):
    references, referenced_by, related, testing, safety, installation,
    terminology, supersedes

A MultiDiGraph is used so a single pair of standards can be linked by more
than one relationship type (for example both ``references`` and ``testing``).
"""

from __future__ import annotations

from typing import Iterable, Sequence

import networkx as nx

from recommendation.recommendation_engine import classify_base_type
from utils import get_logger

logger = get_logger("standards_graph")

# Relationship types that describe *why* a linked standard matters.
TYPE_TO_RELATIONSHIP = {
    "Testing": "testing",
    "Safety": "safety",
    "Installation": "installation",
    "Terminology": "terminology",
    "Reference": "references",
}


class StandardsGraph:
    """Relationship graph over the curated standards dataset."""

    def __init__(self, standards: Sequence[dict]) -> None:
        self._standards = {std["id"]: std for std in standards}
        self.graph = nx.MultiDiGraph()
        self._build()

    # -- construction -------------------------------------------------------
    def _build(self) -> None:
        for standard_id, standard in self._standards.items():
            self.graph.add_node(
                standard_id,
                label=standard.get("standard_number", standard_id),
                title=standard.get("title", ""),
                node_type=classify_base_type(standard),
                version=standard.get("version", ""),
                status=standard.get("status", "Active"),
                category=standard.get("category", ""),
            )

        for standard_id, standard in self._standards.items():
            base_type = classify_base_type(standard)
            is_primary_like = base_type in {"Primary", "Reference"}

            for target in standard.get("referenced_standards", []) or []:
                if target in self._standards:
                    self._add_edge(standard_id, target, "references")
                    self._add_edge(target, standard_id, "referenced_by")

            for target in standard.get("related_standards", []) or []:
                if target in self._standards:
                    self._add_edge(standard_id, target, "related")

            for target in standard.get("superseded_by", []) or []:
                if target in self._standards:
                    self._add_edge(standard_id, target, "supersedes")
                    self._add_edge(target, standard_id, "superseded_by")

            # A primary standard that links to a testing/safety/installation
            # standard gains a typed edge so the graph shows the relationship.
            if is_primary_like:
                for target in self._linked_targets(standard_id):
                    relationship = TYPE_TO_RELATIONSHIP.get(classify_base_type(self._standards[target]))
                    if relationship and relationship != "references":
                        self._add_edge(standard_id, target, relationship)

        logger.info(
            "standards graph built: %d nodes, %d edges",
            self.graph.number_of_nodes(),
            self.graph.number_of_edges(),
        )

    def _linked_targets(self, standard_id: str) -> list[str]:
        standard = self._standards[standard_id]
        targets = list(standard.get("referenced_standards", []) or [])
        targets += list(standard.get("related_standards", []) or [])
        return [target for target in targets if target in self._standards]

    def _add_edge(self, source: str, target: str, relationship: str) -> None:
        if source not in self._standards or target not in self._standards:
            return
        existing = self.graph.get_edge_data(source, target) or {}
        if any(data.get("relationship") == relationship for data in existing.values()):
            return
        self.graph.add_edge(source, target, relationship=relationship)

    # -- traversal ----------------------------------------------------------
    def expand(self, standard_id: str, relationships: Iterable[str] | None = None) -> list[tuple[str, str]]:
        """Return (neighbour_id, relationship) pairs reachable from a standard.

        Covers referenced standards, related standards, and the typed
        testing / safety / installation / terminology relationships.
        """
        if standard_id not in self.graph:
            return []

        allowed = set(relationships) if relationships else {
            "references", "related", "testing", "safety", "installation", "terminology", "supersedes"
        }
        results: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()

        for _, target, data in self.graph.out_edges(standard_id, data=True):
            relationship = data.get("relationship", "related")
            if relationship in allowed and (target, relationship) not in seen:
                seen.add((target, relationship))
                results.append((target, relationship))

        return results

    def relationships_for(self, standard_id: str) -> list[dict]:
        if standard_id not in self.graph:
            return []
        results = []
        for source, target, data in self.graph.edges(data=True):
            if source == standard_id or target == standard_id:
                results.append(
                    {
                        "source": source,
                        "target": target,
                        "relationship": data.get("relationship", "related"),
                    }
                )
        return results

    def node(self, standard_id: str) -> dict | None:
        if standard_id not in self.graph:
            return None
        return dict(self.graph.nodes[standard_id])

    def visualisation(
        self,
        root_id: str,
        scores: dict[str, float] | None = None,
        types: dict[str, str] | None = None,
        depth: int = 1,
    ) -> dict:
        """Build a node/edge payload for the frontend graph visualisation."""
        scores = scores or {}
        types = types or {}

        nodes: dict[str, dict] = {}
        edges: list[dict] = []
        frontier = [(root_id, 0, "")]

        while frontier:
            current, level, relationship = frontier.pop(0)
            if current in nodes or current not in self._standards:
                continue

            standard = self._standards[current]
            node_type = types.get(current) or classify_base_type(standard)
            nodes[current] = {
                "id": current,
                "label": standard.get("standard_number", current),
                "title": standard.get("title", ""),
                "node_type": node_type,
                "relationship": relationship,
                "version": standard.get("version", ""),
                "status": standard.get("status", "Active"),
                "score": scores.get(current),
                "is_root": current == root_id,
            }

            if level >= depth:
                continue

            for target, rel in self.expand(current):
                edges.append({"source": current, "target": target, "relationship": rel})
                frontier.append((target, level + 1, rel))

        return {"root": root_id, "nodes": list(nodes.values()), "edges": edges}


def build_graph(standards: Sequence[dict]) -> StandardsGraph:
    return StandardsGraph(standards)
