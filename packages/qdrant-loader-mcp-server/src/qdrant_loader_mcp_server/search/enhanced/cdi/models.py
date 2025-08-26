from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import networkx as nx
from networkx.exception import NetworkXError, PowerIterationFailedConvergence

from ....utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class SimilarityMetric(Enum):
    """Types of similarity metrics for document comparison."""

    ENTITY_OVERLAP = "entity_overlap"
    TOPIC_OVERLAP = "topic_overlap"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    METADATA_SIMILARITY = "metadata_similarity"
    HIERARCHICAL_DISTANCE = "hierarchical_distance"
    CONTENT_FEATURES = "content_features"
    COMBINED = "combined"


class ClusteringStrategy(Enum):
    """Strategies for document clustering."""

    ENTITY_BASED = "entity_based"
    TOPIC_BASED = "topic_based"
    PROJECT_BASED = "project_based"
    HIERARCHICAL = "hierarchical"
    MIXED_FEATURES = "mixed_features"
    SEMANTIC_EMBEDDING = "semantic_embedding"


class RelationshipType(Enum):
    """Types of relationships between documents."""

    HIERARCHICAL = "hierarchical"
    CROSS_REFERENCE = "cross_reference"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    COMPLEMENTARY = "complementary"
    CONFLICTING = "conflicting"
    SEQUENTIAL = "sequential"
    TOPICAL_GROUPING = "topical_grouping"
    PROJECT_GROUPING = "project_grouping"


@dataclass
class DocumentSimilarity:
    """Represents similarity between two documents."""

    doc1_id: str
    doc2_id: str
    similarity_score: float  # 0.0 - 1.0
    metric_scores: dict[SimilarityMetric, float] = field(default_factory=dict)
    shared_entities: list[str] = field(default_factory=list)
    shared_topics: list[str] = field(default_factory=list)
    relationship_type: RelationshipType = RelationshipType.SEMANTIC_SIMILARITY
    explanation: str = ""

    def get_display_explanation(self) -> str:
        """Get human-readable explanation of similarity."""
        if self.explanation:
            return self.explanation

        explanations: list[str] = []
        if self.shared_entities:
            explanations.append(
                f"Shared entities: {', '.join(self.shared_entities[:3])}"
            )
        if self.shared_topics:
            explanations.append(f"Shared topics: {', '.join(self.shared_topics[:3])}")
        if self.metric_scores:
            top_metric = max(self.metric_scores.items(), key=lambda x: x[1])
            explanations.append(f"High {top_metric[0].value}: {top_metric[1]:.2f}")

        return "; ".join(explanations) if explanations else "Semantic similarity"


@dataclass
class DocumentCluster:
    """Represents a cluster of related documents."""

    cluster_id: str
    name: str
    documents: list[str] = field(default_factory=list)  # Document IDs
    shared_entities: list[str] = field(default_factory=list)
    shared_topics: list[str] = field(default_factory=list)
    cluster_strategy: ClusteringStrategy = ClusteringStrategy.MIXED_FEATURES
    coherence_score: float = 0.0  # 0.0 - 1.0
    representative_doc_id: str = ""
    cluster_description: str = ""

    def get_cluster_summary(self) -> dict[str, Any]:
        """Get summary information about the cluster."""
        return {
            "cluster_id": self.cluster_id,
            "name": self.name,
            "document_count": len(self.documents),
            "coherence_score": self.coherence_score,
            "primary_entities": self.shared_entities[:5],
            "primary_topics": self.shared_topics[:5],
            "strategy": self.cluster_strategy.value,
            "description": self.cluster_description,
        }


@dataclass
class CitationNetwork:
    """Represents a citation/reference network between documents."""

    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)  # doc_id -> metadata
    edges: list[tuple[str, str, dict[str, Any]]] = field(
        default_factory=list
    )  # (from, to, metadata)
    graph: nx.DiGraph | None = None
    authority_scores: dict[str, float] = field(default_factory=dict)
    hub_scores: dict[str, float] = field(default_factory=dict)
    pagerank_scores: dict[str, float] = field(default_factory=dict)

    def build_graph(self) -> nx.DiGraph:
        """Build NetworkX graph from nodes and edges."""
        if self.graph is None:
            self.graph = nx.DiGraph()

            for doc_id, metadata in self.nodes.items():
                self.graph.add_node(doc_id, **metadata)

            for from_doc, to_doc, edge_metadata in self.edges:
                self.graph.add_edge(from_doc, to_doc, **edge_metadata)

        return self.graph

    def calculate_centrality_scores(self):
        """Calculate various centrality scores for the citation network."""
        if self.graph is None:
            self.build_graph()

        try:
            if self.graph.number_of_edges() == 0:
                if self.graph.nodes():
                    degree_centrality = nx.degree_centrality(self.graph)
                    self.authority_scores = degree_centrality
                    self.hub_scores = degree_centrality
                    self.pagerank_scores = degree_centrality
                return

            hits_scores = nx.hits(self.graph, max_iter=100, normalized=True)
            self.hub_scores = hits_scores[0]
            self.authority_scores = hits_scores[1]

            self.pagerank_scores = nx.pagerank(self.graph, max_iter=100)

        except (NetworkXError, PowerIterationFailedConvergence, ValueError):
            logger.exception(
                "Centrality computation failed; falling back to degree centrality"
            )
            if self.graph.nodes():
                degree_centrality = nx.degree_centrality(self.graph)
                self.authority_scores = degree_centrality
                self.hub_scores = degree_centrality
                self.pagerank_scores = degree_centrality


@dataclass
class ComplementaryContent:
    """Represents complementary content recommendations."""

    target_doc_id: str
    recommendations: list[tuple[str, float, str]] = field(
        default_factory=list
    )  # (doc_id, score, reason)
    recommendation_strategy: str = "mixed"
    generated_at: datetime = field(default_factory=datetime.now)

    def get_top_recommendations(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get top N recommendations with detailed information."""
        # Validate input limit explicitly to avoid silent misuse
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be an int greater than 0")

        top_recs = sorted(self.recommendations, key=lambda x: x[1], reverse=True)[
            :limit
        ]
        return [
            {
                "document_id": doc_id,
                "relevance_score": score,
                "recommendation_reason": reason,
                "strategy": self.recommendation_strategy,
            }
            for doc_id, score, reason in top_recs
        ]


@dataclass
class ConflictAnalysis:
    """Represents analysis of conflicting information between documents."""

    conflicting_pairs: list[tuple[str, str, dict[str, Any]]] = field(
        default_factory=list
    )  # (doc1, doc2, conflict_info)
    conflict_categories: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    resolution_suggestions: dict[str, str] = field(default_factory=dict)

    def get_conflict_summary(self) -> dict[str, Any]:
        """Get summary of detected conflicts."""
        return {
            "total_conflicts": len(self.conflicting_pairs),
            "conflict_categories": {
                cat: len(pairs) for cat, pairs in self.conflict_categories.items()
            },
            "most_common_conflicts": self._get_most_common_conflicts(),
            "resolution_suggestions": list(self.resolution_suggestions.values())[:3],
        }

    def _get_most_common_conflicts(self) -> list[str]:
        """Get the most common types of conflicts."""
        return sorted(
            self.conflict_categories.keys(),
            key=lambda x: len(self.conflict_categories[x]),
            reverse=True,
        )[:3]
