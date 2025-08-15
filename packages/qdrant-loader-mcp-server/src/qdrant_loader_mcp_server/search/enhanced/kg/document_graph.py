"""
Document Knowledge Graph Interface.

This module provides a high-level interface for document knowledge graph operations,
integrating graph building, traversal, and content discovery.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...nlp.spacy_analyzer import QueryAnalysis, SpaCyQueryAnalyzer
    from ...models import SearchResult
else:
    QueryAnalysis = Any
    SpaCyQueryAnalyzer = Any
    SearchResult = Any

from ....utils.logging import LoggingConfig
from .models import NodeType, TraversalStrategy, TraversalResult
from .graph import KnowledgeGraph
from .builder import GraphBuilder
from .traverser import GraphTraverser

logger = LoggingConfig.get_logger(__name__)


class DocumentKnowledgeGraph:
    """High-level interface for document knowledge graph operations."""

    def __init__(self, spacy_analyzer: SpaCyQueryAnalyzer | None = None):
        """Initialize the document knowledge graph system."""
        # Import SpaCyQueryAnalyzer at runtime to avoid circular import
        if spacy_analyzer is None:
            from ...nlp.spacy_analyzer import SpaCyQueryAnalyzer
            self.spacy_analyzer = SpaCyQueryAnalyzer()
        else:
            self.spacy_analyzer = spacy_analyzer
        
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
