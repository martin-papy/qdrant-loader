from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qdrant_loader.core.document import Document

from abc import ABC, abstractmethod
from typing import ClassVar

from ..models import (
    CoreEdgeType,
    CoreNodeLabel,
    GraphEdge,
    GraphNode,
    PersonInfo,
    SubGraph,
)


# ------------------------
# EntityExtractor Interface
# ------------------------
class EntityExtractor(ABC):
    """
    Interface for all entity extractors.
    """

    _registry: dict[str, type[EntityExtractor]] = {}

    @abstractmethod
    def extract(self, doc: Document) -> SubGraph:
        """
        Map raw source data into a SubGraph
        """
        raise NotImplementedError

    # -------- Registry --------
    @classmethod
    def register_extractor(cls, source_type: str, extractor_cls: type[EntityExtractor]):
        if source_type in cls._registry:
            raise ValueError(
                f"Extractor already registered for source_type={source_type}"
            )
        cls._registry[source_type] = extractor_cls

    @classmethod
    def for_source(cls, source_type: str) -> EntityExtractor:
        if source_type not in cls._registry:
            raise ValueError(f"No extractor registered for source_type={source_type}")
        return cls._registry[source_type]()  # instantiate


class BaseEntityExtractor(EntityExtractor):
    """
    Base extractor implementing shared graph extraction.

    Common nodes:
        - Document
        - Person
        - Container
        - Label

    Source-specific nodes are extracted via
    _extract_source_specific().
    """

    source_type: ClassVar[str]

    def extract(self, doc: Document) -> SubGraph:
        project = self._project(doc)

        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        # 1. Document
        doc_node = self._build_document_node(doc, project)
        nodes.append(doc_node)

        # 2. People
        people = self._extract_people(doc)

        # Deduplicate people by canonical person id
        seen_people: set[str] = set()

        for person_info, role in people:
            canonical_id = person_info.id

            if canonical_id in seen_people:
                continue

            seen_people.add(canonical_id)

            person_node = self._person_node(person_info, project)
            nodes.append(person_node)

            edges.append(
                GraphEdge(
                    source=doc.id,
                    target=person_node.id,
                    edge_type=CoreEdgeType.AUTHORED_BY,
                    project=project,
                    properties={"role": role},
                )
            )

        # 3. Container (project / space / repo)
        container = self._extract_container(doc)

        if container:
            nodes.append(container)

            edges.append(
                GraphEdge(
                    source=doc.id,
                    target=container.id,
                    edge_type=CoreEdgeType.BELONGS_TO,
                    project=project,
                )
            )

        # 4. Labels
        labels = self._extract_labels(doc)

        for label in labels:
            nodes.append(label)

            edges.append(
                GraphEdge(
                    source=doc.id,
                    target=label.id,
                    edge_type=CoreEdgeType.HAS_LABEL,
                    project=project,
                )
            )

        # 5. Cross references
        link_nodes, link_edges = self._extract_links(doc)

        nodes.extend(link_nodes)
        edges.extend(link_edges)

        # 6. Source specific
        custom_nodes, custom_edges = self._extract_source_specific(doc)

        nodes.extend(custom_nodes)
        edges.extend(custom_edges)

        return SubGraph(
            nodes=nodes,
            edges=edges,
        )

    def _build_document_node(
        self,
        doc: Document,
        project: str | None,
    ) -> GraphNode:
        return GraphNode(
            id=doc.id,
            label=CoreNodeLabel.DOCUMENT,
            project=project,
            properties={
                "title": doc.title,
                "source_type": self.source_type,
            },
        )

    def _person_node(
        self,
        person_info: PersonInfo,
        project: str | None,
    ) -> GraphNode:
        return GraphNode(
            id=person_info.id,
            label=CoreNodeLabel.PERSON,
            project=project,
            properties={
                "display_name": person_info.display_name,
            },
        )

    # ------------------------------------------------------------------
    # Required hooks
    # ------------------------------------------------------------------

    @abstractmethod
    def _project(self, doc: Document) -> str | None:
        """
        Return project / space / repository identifier.
        """

    @abstractmethod
    def _extract_people(
        self,
        doc: Document,
    ) -> list[tuple[PersonInfo, str]]:
        """
        Return [(person_info, role), ...]
        """

    @abstractmethod
    def _extract_container(
        self,
        doc: Document,
    ) -> GraphNode | None:
        """
        Return container node (project / space / repository)
        """

    # ------------------------------------------------------------------
    # Optional hooks
    # ------------------------------------------------------------------

    def _extract_labels(
        self,
        doc: Document,
    ) -> list[GraphNode]:
        return []

    def _extract_links(
        self,
        doc: Document,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        return [], []

    def _extract_source_specific(
        self,
        doc: Document,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        return [], []
