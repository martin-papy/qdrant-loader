"""
Knowledge Graph for Search Enhancement.

This module implements knowledge graph capabilities for search enhancement:
- Multi-node graph construction from document metadata
- Relationship extraction and strength scoring
- Graph traversal algorithms for multi-hop search
- Integration with spaCy-powered components
"""

import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

import networkx as nx

from ...utils.logging import LoggingConfig
from ..models import SearchResult
from ..nlp.spacy_analyzer import QueryAnalysis, SpaCyQueryAnalyzer
from .kg import (
    NodeType,
    RelationshipType,
    GraphNode,
    GraphEdge,
    TraversalStrategy,
    TraversalResult,
    GraphTraverser,
    GraphBuilder,
)
from .kg.utils import (
    jaccard_similarity,
    calculate_list_similarity,
    calculate_node_similarity,
    build_reasoning_path,
    SIMILARITY_EDGE_THRESHOLD,
    ENTITY_SIM_WEIGHT,
    TOPIC_SIM_WEIGHT,
    KEYWORD_SIM_WEIGHT,
)
from .kg.extractors import (
    extract_entities_from_result,
    extract_topics_from_result,
    extract_concepts_from_result,
    extract_keywords_from_result,
)

logger = LoggingConfig.get_logger(__name__)




class KnowledgeGraph:
    """Core knowledge graph implementation using NetworkX."""

    def __init__(self):
        """Initialize the knowledge graph."""
        self.graph = nx.MultiDiGraph()  # Allow multiple edges between nodes
        self.nodes: dict[str, GraphNode] = {}
        self.edges: dict[tuple[str, str, str], GraphEdge] = (
            {}
        )  # (source, target, relationship)
        self.node_type_index: dict[NodeType, set[str]] = defaultdict(set)
        self.entity_index: dict[str, set[str]] = defaultdict(set)  # entity -> node_ids
        self.topic_index: dict[str, set[str]] = defaultdict(set)  # topic -> node_ids

        logger.info("Initialized empty knowledge graph")

    def add_node(self, node: GraphNode) -> bool:
        """Add a node to the graph."""
        try:
            if node.id in self.nodes:
                logger.debug(f"Node {node.id} already exists, updating")

            self.nodes[node.id] = node
            self.graph.add_node(node.id, **node.metadata)
            self.node_type_index[node.node_type].add(node.id)

            # Index entities and topics for fast lookup
            for entity in node.entities:
                self.entity_index[entity.lower()].add(node.id)
            for topic in node.topics:
                self.topic_index[topic.lower()].add(node.id)

            logger.debug(f"Added {node.node_type.value} node: {node.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add node {node.id}: {e}")
            return False

    def add_edge(self, edge: GraphEdge) -> bool:
        """Add an edge to the graph."""
        try:
            if edge.source_id not in self.nodes or edge.target_id not in self.nodes:
                logger.warning(
                    f"Edge {edge.source_id} -> {edge.target_id}: missing nodes"
                )
                return False

            edge_key = (edge.source_id, edge.target_id, edge.relationship_type.value)
            self.edges[edge_key] = edge

            self.graph.add_edge(
                edge.source_id,
                edge.target_id,
                key=edge.relationship_type.value,
                weight=edge.weight,
                relationship=edge.relationship_type.value,
                confidence=edge.confidence,
                **edge.metadata,
            )

            logger.debug(
                f"Added edge: {edge.source_id} --{edge.relationship_type.value}--> {edge.target_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to add edge {edge.source_id} -> {edge.target_id}: {e}"
            )
            return False

    def find_nodes_by_type(self, node_type: NodeType) -> list[GraphNode]:
        """Find all nodes of a specific type."""
        return [self.nodes[node_id] for node_id in self.node_type_index[node_type]]

    def find_nodes_by_entity(self, entity: str) -> list[GraphNode]:
        """Find all nodes containing a specific entity."""
        node_ids = self.entity_index.get(entity.lower(), set())
        return [self.nodes[node_id] for node_id in node_ids]

    def find_nodes_by_topic(self, topic: str) -> list[GraphNode]:
        """Find all nodes discussing a specific topic."""
        node_ids = self.topic_index.get(topic.lower(), set())
        return [self.nodes[node_id] for node_id in node_ids]

    def calculate_centrality_scores(self):
        """Calculate centrality scores for all nodes."""
        try:
            if len(self.graph.nodes) == 0:
                return

            # Calculate different centrality metrics
            degree_centrality = nx.degree_centrality(self.graph)
            betweenness_centrality = nx.betweenness_centrality(self.graph)

            # For directed graphs, calculate hub and authority scores
            try:
                hub_scores, authority_scores = nx.hits(self.graph, max_iter=100)
            except nx.PowerIterationFailedConvergence:
                logger.warning(
                    "HITS algorithm failed to converge, using default scores"
                )
                hub_scores = dict.fromkeys(self.graph.nodes, 0.0)
                authority_scores = dict.fromkeys(self.graph.nodes, 0.0)

            # Update node objects with calculated scores
            for node_id, node in self.nodes.items():
                node.centrality_score = (
                    degree_centrality.get(node_id, 0.0) * 0.4
                    + betweenness_centrality.get(node_id, 0.0) * 0.6
                )
                node.hub_score = hub_scores.get(node_id, 0.0)
                node.authority_score = authority_scores.get(node_id, 0.0)

            logger.info(f"Calculated centrality scores for {len(self.nodes)} nodes")

        except Exception as e:
            logger.error(f"Failed to calculate centrality scores: {e}")

    def get_neighbors(
        self, node_id: str, relationship_types: list[RelationshipType] | None = None
    ) -> list[tuple[str, GraphEdge]]:
        """Get neighboring nodes with their connecting edges."""
        neighbors = []

        if node_id not in self.graph:
            return neighbors

        for neighbor_id in self.graph.neighbors(node_id):
            # Get all edges between these nodes
            edge_data = self.graph.get_edge_data(node_id, neighbor_id)
            if edge_data:
                for _key, data in edge_data.items():
                    relationship = RelationshipType(data["relationship"])
                    if relationship_types is None or relationship in relationship_types:
                        edge_key = (node_id, neighbor_id, relationship.value)
                        if edge_key in self.edges:
                            neighbors.append((neighbor_id, self.edges[edge_key]))

        return neighbors

    def get_statistics(self) -> dict[str, Any]:
        """Get graph statistics."""
        stats = {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_types": {
                node_type.value: len(nodes)
                for node_type, nodes in self.node_type_index.items()
            },
            "relationship_types": {},
            "connected_components": nx.number_weakly_connected_components(self.graph),
            "avg_degree": sum(dict(self.graph.degree()).values())
            / max(len(self.graph.nodes), 1),
        }

        # Count relationship types
        for edge in self.edges.values():
            rel_type = edge.relationship_type.value
            stats["relationship_types"][rel_type] = (
                stats["relationship_types"].get(rel_type, 0) + 1
            )

        return stats


# GraphTraverser moved to kg.traverser


# GraphBuilder moved to kg.builder


class DocumentKnowledgeGraph:
    """High-level interface for document knowledge graph operations."""

    def __init__(self, spacy_analyzer: SpaCyQueryAnalyzer | None = None):
        """Initialize the document knowledge graph system."""
        self.spacy_analyzer = spacy_analyzer or SpaCyQueryAnalyzer()
        self.graph_builder = GraphBuilder(self.spacy_analyzer)
        self.knowledge_graph: KnowledgeGraph | None = None
        self.traverser: GraphTraverser | None = None

        logger.info("Initialized document knowledge graph system")

    def build_graph(self, search_results: list[SearchResult]) -> bool:
        """Build knowledge graph from search results."""
        try:
            self.knowledge_graph = self.graph_builder.build_from_search_results(
                search_results
            )
            self.traverser = GraphTraverser(self.knowledge_graph, self.spacy_analyzer)

            stats = self.knowledge_graph.get_statistics()
            logger.info("Knowledge graph built successfully", **stats)
            return True

        except Exception as e:
            logger.error(f"Failed to build knowledge graph: {e}")
            return False

    def find_related_content(
        self,
        query: str,
        max_hops: int = 3,
        max_results: int = 20,
        strategy: TraversalStrategy = TraversalStrategy.SEMANTIC,
    ) -> list[TraversalResult]:
        """Find related content using graph traversal."""

        if not self.knowledge_graph or not self.traverser:
            logger.warning("Knowledge graph not initialized")
            return []

        try:
            # Analyze query with spaCy
            query_analysis = self.spacy_analyzer.analyze_query_semantic(query)

            # Find starting nodes based on query entities and concepts
            start_nodes = self._find_query_start_nodes(query_analysis)

            if not start_nodes:
                logger.debug("No starting nodes found for query")
                return []

            # Traverse graph to find related content
            results = self.traverser.traverse(
                start_nodes=start_nodes,
                query_analysis=query_analysis,
                strategy=strategy,
                max_hops=max_hops,
                max_results=max_results,
            )

            logger.debug(
                f"Found {len(results)} related content items via graph traversal"
            )
            return results

        except Exception as e:
            logger.error(f"Failed to find related content: {e}")
            return []

    def _find_query_start_nodes(self, query_analysis: QueryAnalysis) -> list[str]:
        """Find starting nodes for graph traversal based on query analysis."""

        start_nodes = []

        # Find nodes by entities
        for entity_text, _entity_label in query_analysis.entities:
            entity_nodes = self.knowledge_graph.find_nodes_by_entity(entity_text)
            start_nodes.extend([node.id for node in entity_nodes])

        # Find nodes by main concepts (as topics)
        for concept in query_analysis.main_concepts:
            topic_nodes = self.knowledge_graph.find_nodes_by_topic(concept)
            start_nodes.extend([node.id for node in topic_nodes])

        # If no entity/topic matches, use high-centrality document nodes
        if not start_nodes:
            doc_nodes = self.knowledge_graph.find_nodes_by_type(NodeType.DOCUMENT)
            # Sort by centrality and take top 3
            doc_nodes.sort(key=lambda n: n.centrality_score, reverse=True)
            start_nodes = [node.id for node in doc_nodes[:3]]

        return list(set(start_nodes))  # Remove duplicates

    def get_graph_statistics(self) -> dict[str, Any] | None:
        """Get knowledge graph statistics."""
        if self.knowledge_graph:
            return self.knowledge_graph.get_statistics()
        return None

    def export_graph(self, format: str = "json") -> str | None:
        """Export knowledge graph in specified format."""
        if not self.knowledge_graph:
            return None

        try:
            if format == "json":
                # Export as JSON with nodes and edges
                data = {
                    "nodes": [
                        {
                            "id": node.id,
                            "type": node.node_type.value,
                            "title": node.title,
                            "centrality": node.centrality_score,
                            "entities": node.entities,
                            "topics": node.topics,
                        }
                        for node in self.knowledge_graph.nodes.values()
                    ],
                    "edges": [
                        {
                            "source": edge.source_id,
                            "target": edge.target_id,
                            "relationship": edge.relationship_type.value,
                            "weight": edge.weight,
                            "confidence": edge.confidence,
                        }
                        for edge in self.knowledge_graph.edges.values()
                    ],
                }
                return json.dumps(data, indent=2)

        except Exception as e:
            logger.error(f"Failed to export graph: {e}")

        return None
