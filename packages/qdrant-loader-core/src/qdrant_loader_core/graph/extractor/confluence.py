from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qdrant_loader.core.document import Document

from qdrant_loader_core.graph.extractor.base_extractor import (
    BaseEntityExtractor,
)
from qdrant_loader_core.graph.models import (
    CoreEdgeType,
    CoreNodeLabel,
    GraphEdge,
    GraphNode,
    PersonInfo,
)


class ConfluenceEntityExtractor(BaseEntityExtractor):
    """
    Confluence graph extractor.

    Extracts:
    - Document node from page
    - Person node from author
    - Container node from space
    - Parent / child page hierarchy
    """

    source_type = "confluence"

    # ------------------------------------------------------------------
    # Project / Space
    # ------------------------------------------------------------------

    def _project(
        self,
        doc: Document,
    ) -> str | None:
        return doc.metadata.get("space_key")

    # ------------------------------------------------------------------
    # People
    # ------------------------------------------------------------------

    def _extract_people(
        self,
        doc: Document,
    ) -> list[tuple[PersonInfo, str]]:
        author = doc.metadata.get("author")

        if not author:
            return []

        return [
            (
                PersonInfo(
                    id=str(author),
                    display_name=str(author),
                ),
                "author",
            )
        ]

    # ------------------------------------------------------------------
    # Space container
    # ------------------------------------------------------------------

    def _extract_container(
        self,
        doc: Document,
    ) -> GraphNode | None:
        space_key = doc.metadata.get("space_key")

        if not space_key:
            return None

        return GraphNode(
            id=f"space:{space_key}",
            label=CoreNodeLabel.CONTAINER,
            project=space_key,
            properties={
                "kind": "confluence_space",
                "space_key": space_key,
            },
        )

    # ------------------------------------------------------------------
    # Labels
    # ------------------------------------------------------------------

    def _extract_labels(
        self,
        doc: Document,
    ) -> list[GraphNode]:
        project = self._project(doc)

        labels = doc.metadata.get("labels", [])

        return [
            GraphNode(
                id=f"label:{label}",
                label=CoreNodeLabel.LABEL,
                project=project,
                properties={
                    "name": label,
                },
            )
            for label in labels
        ]

    # ------------------------------------------------------------------
    # Hierarchy
    # ------------------------------------------------------------------

    def _extract_source_specific(
        self,
        doc: Document,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        project = self._project(doc)

        edges: list[GraphEdge] = []

        parent_id = doc.metadata.get("parent_id")

        if parent_id:
            edges.append(
                GraphEdge(
                    source=doc.id,
                    target=str(parent_id),
                    edge_type=CoreEdgeType.PART_OF,
                    project=project,
                    properties={
                        "kind": "page_child",
                    },
                )
            )

        for child in doc.metadata.get("children", []):
            child_id = child.get("id")

            if not child_id:
                continue

            edges.append(
                GraphEdge(
                    source=doc.id,
                    target=str(child_id),
                    edge_type=CoreEdgeType.HAS_CHILD,
                    project=project,
                    properties={
                        "kind": "page_child",
                    },
                )
            )

        return [], edges
