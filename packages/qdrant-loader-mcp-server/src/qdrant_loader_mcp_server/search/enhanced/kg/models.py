from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(Enum):
    DOCUMENT = "document"
    SECTION = "section"
    ENTITY = "entity"
    TOPIC = "topic"
    CONCEPT = "concept"


class RelationshipType(Enum):
    CONTAINS = "contains"
    PART_OF = "part_of"
    SIBLING = "sibling"
    MENTIONS = "mentions"
    DISCUSSES = "discusses"
    RELATES_TO = "relates_to"
    SIMILAR_TO = "similar_to"
    REFERENCES = "references"
    CITES = "cites"
    BUILDS_ON = "builds_on"
    CONTRADICTS = "contradicts"
    CO_OCCURS = "co_occurs"
    CATEGORIZED_AS = "categorized_as"


@dataclass
class GraphNode:
    node_type: NodeType
    title: str
    id: str | None = None
    content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    centrality_score: float = 0.0
    authority_score: float = 0.0
    hub_score: float = 0.0

    entities: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.id is None or self.id == "":
            # Deterministic UUIDv5 id derived from stable inputs (node_type + title)
            # Fixed namespace ensures stable generation across runs/processes
            node_namespace = uuid.UUID("8f5b3e78-9b8c-4f07-b54e-27f7ac1d5a11")
            name = f"{self.node_type.value}::{self.title}"
            deterministic_uuid = uuid.uuid5(node_namespace, name)
            self.id = f"{self.node_type.value}_{deterministic_uuid}"


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    confidence: float = 1.0

    def __post_init__(self):
        self.weight = max(0.0, min(1.0, self.weight))
        self.confidence = max(0.0, min(1.0, self.confidence))


class TraversalStrategy(Enum):
    BREADTH_FIRST = "breadth_first"
    DEPTH_FIRST = "depth_first"
    WEIGHTED = "weighted"
    CENTRALITY = "centrality"
    SEMANTIC = "semantic"
    HIERARCHICAL = "hierarchical"


@dataclass
class TraversalResult:
    path: list[str]
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    total_weight: float
    semantic_score: float
    hop_count: int
    reasoning_path: list[str]
