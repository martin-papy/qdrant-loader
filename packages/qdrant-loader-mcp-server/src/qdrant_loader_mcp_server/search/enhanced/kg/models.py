from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from qdrant_loader_core.graph.models import CoreNodeLabel, GraphEdge, GraphNode


class NodeLabel(Enum):
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


@dataclass(init=False)
class EnrichedNode:
    """
    Semantic wrapper around Core GraphNode.
    Adds query-time enrichment (scores, NLP features, etc.)
    """

    core: GraphNode  # composition (NOT duplication)

    # -------- Basic derived --------
    title: str | None = None
    content: str | None = None

    # -------- Ranking / Graph analytics --------
    centrality_score: float = 0.0
    authority_score: float = 0.0
    hub_score: float = 0.0

    # -------- NLP enrichment --------
    entities: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    # -------- Extra metadata --------
    metadata: dict[str, Any] = field(default_factory=dict)

    def __init__(
        self,
        core: GraphNode | None = None,
        *,
        id: str | None = None,
        node_type: NodeLabel | None = None,
        title: str | None = None,
        content: str | None = None,
        properties: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        entities: list[str] | None = None,
        topics: list[str] | None = None,
        concepts: list[str] | None = None,
        keywords: list[str] | None = None,
        centrality_score: float = 0.0,
        authority_score: float = 0.0,
        hub_score: float = 0.0,
    ) -> None:
        """
        Supports both:
        - EnrichedNode(core=GraphNode(...))
        - EnrichedNode(id=..., node_type=...)
        """

        # Case 1: build core from id + node_type (legacy path)
        if core is None:
            if id is None or node_type is None:
                raise ValueError("Must provide either core OR (id + node_type)")

            core_label = map_mcp_to_core_label(node_type)

            core = GraphNode(
                id=id,
                label=core_label,
                properties=properties or {},
            )

            self.core = core
            self.title = title
            self.content = content
            self.centrality_score = centrality_score
            self.authority_score = authority_score
            self.hub_score = hub_score
            self.entities = entities or []
            self.topics = topics or []
            self.concepts = concepts or []
            self.keywords = keywords or []
            self.metadata = metadata or {}
            if node_type is not None:
                self.metadata["node_type"] = node_type

        # ---------------------------------
        # Helper properties
        # ---------------------------------

    @property
    def id(self) -> str:
        return self.core.id

    @property
    def label(self):
        return self.core.label

    @property
    def properties(self):
        return self.core.properties

    @property
    def node_type(self) -> NodeLabel | None:
        return self.metadata.get("node_type")


@dataclass(init=False)
class EnrichedEdge:
    core: GraphEdge

    weight: float = 1.0
    confidence: float = 1.0

    metadata: dict[str, Any] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)

    def __init__(
        self,
        core: GraphEdge | None = None,
        *,
        source_id: str | None = None,
        target_id: str | None = None,
        relationship_type: str | None = None,
        weight: float = 1.0,
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
        evidence: list[str] | None = None,
    ):
        if core is None:
            if source_id is None or target_id is None or relationship_type is None:
                raise ValueError(
                    "Must provide core OR (source_id + target_id + relationship_type)"
                )

            core = GraphEdge(
                source=source_id,
                target=target_id,
                edge_type=relationship_type,
            )

        self.core = core
        self.weight = weight
        self.confidence = confidence
        self.metadata = metadata or {}
        self.evidence = evidence or []

    @property
    def source_id(self):
        return self.core.source

    @property
    def target_id(self):
        return self.core.target

    @property
    def relationship_type(self):
        return self.core.edge_type


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
    nodes: list[EnrichedNode]
    edges: list[EnrichedEdge]
    total_weight: float
    semantic_score: float
    hop_count: int
    reasoning_path: list[str]


def map_mcp_to_core_label(node_label: NodeLabel) -> CoreNodeLabel:
    """
    Map semantic (MCP) node label -> core graph label
    """

    mapping = {
        NodeLabel.DOCUMENT: CoreNodeLabel.DOCUMENT,
        NodeLabel.CONCEPT: CoreNodeLabel.CONCEPT,
        # Semantic -> generic mapping
        NodeLabel.SECTION: CoreNodeLabel.CONTAINER,
        NodeLabel.ENTITY: CoreNodeLabel.CONCEPT,
        NodeLabel.TOPIC: CoreNodeLabel.CONCEPT,
    }
    if node_label not in mapping:
        raise ValueError(f"Unsupported NodeLabel: {node_label}")
    return mapping[node_label]
