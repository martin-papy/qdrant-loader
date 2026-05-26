from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from ..models import CoreEdgeType, GraphEdge, GraphNode, SubGraph


# ------------------------
# EntityExtractor Interface
# ------------------------
class EntityExtractor(ABC):
    """
    Interface for all entity extractors.
    """

    _registry: dict[str, type[EntityExtractor]] = {}

    @abstractmethod
    def extract(self, raw: dict[str, Any]) -> SubGraph:
        """
        Map raw source data into a SubGraph
        """
        raise NotImplementedError

    # -------- Registry --------
    @classmethod
    def register_extractor(cls, source_type: str, extractor_cls: type[EntityExtractor]):
        cls._registry[source_type] = extractor_cls

    @classmethod
    def for_source(cls, source_type: str) -> EntityExtractor:
        if source_type not in cls._registry:
            raise ValueError(f"No extractor registered for source_type={source_type}")
        return cls._registry[source_type]()  # instantiate


# ------------------------
# BaseEntityExtractor
# ------------------------
class BaseEntityExtractor(EntityExtractor):
    """
    Base extractor implementing shared logic
    Build 6 fixed nodes:
        - Document
        - Person
        - Container
        - Label
        - Concept
        - Chunk
    """

    VALID_EDGE_TYPES = list(CoreEdgeType)

    def __init__(self):
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []

    # -------- Shared Logic --------
    def extract(self, raw: dict[str, Any]) -> SubGraph:
        self._nodes.clear()
        self._edges.clear()

        self._extract_impl(raw)

        return SubGraph(
            nodes=list(self._nodes.values()),
            edges=self._edges,
        )

    @staticmethod
    def _validate_iso8601(value: str) -> None:
        if not value:
            return
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            raise ValueError(f"Invalid ISO-8601 timestamp: {value}")

    @staticmethod
    def _normalize_label(value: str) -> str:
        return value.strip().lower()

    @abstractmethod
    def _extract_impl(self, raw: dict[str, Any]) -> None:
        """
        Source-specific mapping logic
        """
        raise NotImplementedError

    def build_document(
        self,
        *,
        source_type: str,
        native_id: str,
        title: str,
        url: str,
        created_at: str,
        updated_at: str,
        qdrant_point_ids: list[str],
        properties: dict[str, Any] | None = None,
    ) -> GraphNode:
        """
        Build a Document node strictly following the universal schema.
        """

        node_id = f"{source_type}:{native_id}"

        self._validate_iso8601(created_at)
        self._validate_iso8601(updated_at)

        if not isinstance(qdrant_point_ids, list):
            raise ValueError("qdrant_point_ids must be a list")

        node = GraphNode(
            id=node_id,
            label="Document",
            properties={
                "url": url,
                "updated_at": updated_at,
                "title": title,
                "source_type": source_type,
                "qdrant_point_ids": qdrant_point_ids,
                "properties": properties or {},
                "id": node_id,
                "created_at": created_at,
            },
        )

        self._nodes[node_id] = node
        return node

    def get_or_create_person(
        self,
        *,
        email: str | None = None,
        username: str | None = None,
        display_name: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> GraphNode:
        """
        Create or deduplicate a Person node.

        Priority:
        - Use email if available (preferred global identifier)
        - Otherwise fallback to username
        """

        if not email and not username:
            raise ValueError("Person must have either email or username")

        # Canonical ID resolution
        canonical_id = email.lower() if email else username.lower()
        node_id = f"person:{canonical_id}"

        # Create if not exists (dedup happens here)
        if node_id not in self._nodes:
            self._nodes[node_id] = GraphNode(
                id=node_id,
                label="Person",
                properties={
                    "id": canonical_id,
                    "display_name": display_name,
                    "properties": properties or {},
                },
            )
        else:
            # Optional: enrich existing node without overwriting
            existing = self._nodes[node_id]

            if display_name and not existing.properties.get("display_name"):
                existing.properties["display_name"] = display_name

            if properties:
                existing.properties.setdefault("properties", {}).update(properties)

        return self._nodes[node_id]

    def get_or_create_container(
        self,
        *,
        kind: str,
        native_id: str,
        name: str,
        properties: dict[str, Any] | None = None,
    ) -> GraphNode:
        """
        Create or deduplicate a Container node.
        """

        if not kind or not native_id or not name:
            raise ValueError("Container requires kind, native_id, and name")

        # Enforce ID convention
        node_id = f"{kind}:{native_id}"

        # Deduplication
        if node_id not in self._nodes:
            self._nodes[node_id] = GraphNode(
                id=node_id,
                label="Container",
                properties={
                    "id": node_id,
                    "kind": kind,
                    "name": name,
                    "properties": properties or {},
                },
            )
        else:
            # Optional enrichment (same pattern as Person)
            existing = self._nodes[node_id]

            if properties:
                existing.properties.setdefault("properties", {}).update(properties)

        return self._nodes[node_id]

    def get_or_create_label(
        self,
        *,
        name: str,
    ) -> GraphNode:
        """
        Create or deduplicate a Label node.
        """

        if not name:
            raise ValueError("Label name is required")

        # Normalize (IMPORTANT)
        normalized = self._normalize_label(name)

        node_id = f"label:{normalized}"

        # Deduplication
        if node_id not in self._nodes:
            self._nodes[node_id] = GraphNode(
                id=node_id,
                label="Label",
                properties={
                    "id": normalized,
                    "name": name,  # keep original display form
                },
            )
        return self._nodes[node_id]

    def get_or_create_concept(
        self,
        *,
        kind: str,
        native_id: str,
        name: str,
        properties: dict[str, Any] | None = None,
    ) -> GraphNode:
        """
        Create or deduplicate a Concept node.
        """

        if not kind or not native_id or not name:
            raise ValueError("Concept requires kind, native_id, and name")

        # ID convention
        node_id = f"{kind}:{native_id}"

        # Deduplication
        if node_id not in self._nodes:
            self._nodes[node_id] = GraphNode(
                id=node_id,
                label="Concept",
                properties={
                    "id": node_id,
                    "kind": kind,
                    "name": name,
                    "properties": properties or {},
                },
            )
        else:
            # Enrichment (same pattern)
            existing = self._nodes[node_id]

            if properties:
                existing.properties.setdefault("properties", {}).update(properties)

        return self._nodes[node_id]

    def build_chunk(
        self,
        *,
        chunk_id: str,  # Qdrant point ID
        document: GraphNode,
        chunk_index: int,
        content_hash: str,
    ) -> GraphNode:
        """
        Build a Chunk node (1-to-1 with Qdrant point)
        """

        if not chunk_id:
            raise ValueError("chunk_id is required")

        if not isinstance(chunk_index, int):
            raise ValueError("chunk_index must be int")

        if not content_hash:
            raise ValueError("content_hash is required")

        node_id = chunk_id  # must match Qdrant point ID

        # Dedup (important if re-processing)
        if node_id not in self._nodes:
            self._nodes[node_id] = GraphNode(
                id=node_id,
                label="Chunk",
                properties={
                    "id": chunk_id,
                    "document_id": document.id,
                    "chunk_index": chunk_index,
                    "content_hash": content_hash,
                },
            )

        chunk_node = self._nodes[node_id]

        # Link Document → Chunk
        self.emit_edge(
            source=document,
            target=chunk_node,
            edge_type="HAS_CHUNK",
        )

        return chunk_node

    def emit_edge(
        self,
        *,
        source: GraphNode,
        target: GraphNode,
        edge_type: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """
        Create a graph edge between two nodes with validation.
        """

        # Validate input nodes
        if not source or not target:
            raise ValueError("source and target must be provided")

        if not source.id or not target.id:
            raise ValueError("source and target must have valid ids")

        # Validate edge type
        if edge_type not in self.VALID_EDGE_TYPES:
            return # silently ignore invalid edge types to avoid upstream failures, but do not emit

        props = properties or {}

        edge = GraphEdge(
            source=source.id,
            target=target.id,
            edge_type=edge_type,
            properties=props,
        )

        self._edges.append(edge)
