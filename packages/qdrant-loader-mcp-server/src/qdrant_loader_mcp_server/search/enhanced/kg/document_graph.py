"""
Document Knowledge Graph Interface.

This module provides a high-level interface for document knowledge graph operations,
integrating graph building, traversal, and content discovery.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from datetime import time as dtime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...models import SearchResult
    from ...nlp.spacy_analyzer import QueryAnalysis, SpaCyQueryAnalyzer
else:
    QueryAnalysis = Any
    SpaCyQueryAnalyzer = Any
    SearchResult = Any

from ....utils.logging import LoggingConfig
from .builder import GraphBuilder
from .graph import KnowledgeGraph
from .models import NodeType, TraversalResult, TraversalStrategy
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

        # Find nodes by entities (defensive against unexpected formats)
        for item in getattr(query_analysis, "entities", []) or []:
            try:
                entity_text: str | None = None
                # Accept tuple/list like (text, label, ...)
                if isinstance(item, list | tuple) and len(item) > 0:
                    entity_text = item[0]
                # Accept direct string entity
                elif isinstance(item, str):
                    entity_text = item
                # Skip dicts or None/empty safely
                if entity_text:
                    entity_nodes = self.knowledge_graph.find_nodes_by_entity(
                        entity_text
                    )
                    start_nodes.extend([node.id for node in entity_nodes])
            except IndexError:
                # Malformed entity entry; skip
                continue

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
                            "type": getattr(
                                node.node_type, "value", str(node.node_type)
                            ),
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
                            "relationship": getattr(
                                edge.relationship_type,
                                "value",
                                str(edge.relationship_type),
                            ),
                            "weight": edge.weight,
                            "confidence": edge.confidence,
                        }
                        for edge in self.knowledge_graph.edges.values()
                    ],
                }

                class EnhancedJSONEncoder(json.JSONEncoder):
                    def default(self, obj: Any) -> Any:  # type: ignore[override]
                        if isinstance(obj, datetime | date | dtime):
                            return obj.isoformat()
                        if isinstance(obj, Enum):
                            return getattr(obj, "value", str(obj))
                        if isinstance(obj, set):
                            return list(obj)
                        if isinstance(obj, bytes):
                            try:
                                return obj.decode("utf-8")
                            except Exception:
                                return obj.hex()
                        if isinstance(obj, Path):
                            return str(obj)
                        if hasattr(obj, "to_dict"):
                            try:
                                return obj.to_dict()
                            except Exception:
                                return str(obj)
                        if hasattr(obj, "__dict__"):
                            try:
                                return vars(obj)
                            except Exception:
                                return str(obj)
                        return str(obj)

                try:
                    return json.dumps(data, indent=2, cls=EnhancedJSONEncoder)
                except TypeError:
                    # Fallback: sanitize recursively
                    def sanitize(value: Any) -> Any:
                        try:
                            json.dumps(value)
                            return value
                        except TypeError:
                            if isinstance(value, dict):
                                return {
                                    sanitize(k): sanitize(v) for k, v in value.items()
                                }
                            if isinstance(value, list | tuple | set):
                                return [sanitize(v) for v in value]
                            if isinstance(value, datetime | date | dtime):
                                return value.isoformat()
                            if isinstance(value, Enum):
                                return getattr(value, "value", str(value))
                            if isinstance(value, bytes):
                                try:
                                    return value.decode("utf-8")
                                except Exception:
                                    return value.hex()
                            return str(value)

                    safe_data = sanitize(data)
                    return json.dumps(safe_data, indent=2)

        except Exception as e:
            logger.error(f"Failed to export graph: {e}")

        return None
