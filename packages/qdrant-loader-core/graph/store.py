from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

# =========================
# Data Models
# =========================


@dataclass
class GraphNode:
    id: str
    label: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source: str
    target: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubGraph:
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# =========================
# Interface
# =========================


class GraphStore(ABC):
    """
    Backend-agnostic Graph Store interface.
    Supports FalkorDB, Neptune, etc.
    """

    @abstractmethod
    async def upsert_node(self, node: GraphNode) -> None:
        """Insert or update a node"""
        raise NotImplementedError

    @abstractmethod
    async def upsert_edge(self, edge: GraphEdge) -> None:
        """Insert or update an edge"""
        raise NotImplementedError

    @abstractmethod
    async def upsert_nodes_batch(self, nodes: list[GraphNode]) -> None:
        """Batch insert/update nodes"""
        raise NotImplementedError

    @abstractmethod
    async def upsert_edges_batch(self, edges: list[GraphEdge]) -> None:
        """Batch insert/update edges"""
        raise NotImplementedError

    @abstractmethod
    async def neighbors(
        self,
        node_id: str,
        depth: int,
        edge_types: list[str] | None = None,
    ) -> SubGraph:
        """
        Get neighbors up to a certain depth.
        Optionally filter by edge types.
        """
        raise NotImplementedError

    @abstractmethod
    async def query_cypher(
        self,
        cypher: str,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Execute Cypher query (for graph DBs that support it)
        """
        raise NotImplementedError
