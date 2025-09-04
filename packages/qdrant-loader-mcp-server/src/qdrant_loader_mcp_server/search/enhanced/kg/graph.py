"""
Core Knowledge Graph Implementation.

This module implements the core knowledge graph using NetworkX with optimized
node/edge management, indexing, and centrality calculations.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import networkx as nx

from ....utils.logging import LoggingConfig
from .models import GraphEdge, GraphNode, NodeType, RelationshipType

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
                # Remove stale index entries for the existing node before overwrite
                old = self.nodes[node.id]
                try:
                    self.node_type_index[old.node_type].discard(node.id)
                except Exception:
                    pass
                for old_entity in getattr(old, "entities", []):
                    try:
                        self.entity_index[old_entity.lower()].discard(node.id)
                    except Exception:
                        pass
                for old_topic in getattr(old, "topics", []):
                    try:
                        self.topic_index[old_topic.lower()].discard(node.id)
                    except Exception:
                        pass

            # Overwrite node object and update graph node attributes
            self.nodes[node.id] = node
            if node.id in self.graph:
                try:
                    # Replace attributes with current metadata
                    self.graph.nodes[node.id].clear()
                except Exception:
                    pass
                self.graph.nodes[node.id].update(node.metadata)
            else:
                self.graph.add_node(node.id, **node.metadata)

            # Add to indices for fast lookup
            self.node_type_index[node.node_type].add(node.id)

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
            # Create a simple DiGraph view to ensure compatibility with HITS
            try:
                simple_digraph = nx.DiGraph(self.graph)
                hub_scores, authority_scores = nx.hits(simple_digraph, max_iter=100)
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
                    rel_value = data.get("relationship")
                    if rel_value is None:
                        logger.debug(
                            "Skipping edge with missing relationship metadata: %s -> %s",
                            node_id,
                            neighbor_id,
                        )
                        continue
                    try:
                        relationship = RelationshipType(rel_value)
                    except ValueError:
                        logger.warning(
                            "Skipping edge with invalid relationship value '%s': %s -> %s",
                            rel_value,
                            node_id,
                            neighbor_id,
                        )
                        continue
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
