"""
Knowledge Graph Builder.

This module implements graph construction logic, building knowledge graphs
from document metadata and search results with intelligent relationship extraction.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import Counter, defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...models import SearchResult
    from ...nlp.spacy_analyzer import SpaCyQueryAnalyzer

from ....utils.logging import LoggingConfig
from .extractors import (
    extract_concepts_from_result,
    extract_entities_from_result,
    extract_keywords_from_result,
    extract_topics_from_result,
)
from .models import (
    GraphEdge,
    GraphNode,
    NodeType,
    RelationshipType,
)
from .utils import (
    SIMILARITY_EDGE_THRESHOLD,
    calculate_node_similarity,
)

logger = LoggingConfig.get_logger(__name__)


class RecoverableBuildError(Exception):
    """Raised for expected parsing/validation issues during graph building."""


class GraphBuilder:
    """Build knowledge graph from document metadata and search results."""

    def __init__(self, spacy_analyzer: SpaCyQueryAnalyzer | None = None):
        """Initialize the graph builder."""
        # Import SpaCyQueryAnalyzer at runtime to avoid circular import
        if spacy_analyzer is None:
            from ...nlp.spacy_analyzer import SpaCyQueryAnalyzer

            self.spacy_analyzer = SpaCyQueryAnalyzer()
        else:
            self.spacy_analyzer = spacy_analyzer
        logger.info("Initialized graph builder")

    def build_from_search_results(
        self, search_results: list[SearchResult]
    ) -> Any:  # KnowledgeGraph - avoiding circular import
        """Build knowledge graph from search results metadata."""
        # Import KnowledgeGraph at runtime to avoid circular import
        from ..knowledge_graph import KnowledgeGraph

        start_time = time.time()
        graph = KnowledgeGraph()

        try:
            # Step 1: Create nodes from search results
            document_nodes = self._create_document_nodes(search_results)
            for node in document_nodes:
                graph.add_node(node)

            # Step 2: Create entity and topic nodes
            entity_nodes, topic_nodes = self._create_concept_nodes(search_results)
            for node in entity_nodes + topic_nodes:
                graph.add_node(node)

            # Step 3: Create relationships
            edges = self._create_relationships(search_results, graph)
            for edge in edges:
                graph.add_edge(edge)

            # Step 4: Calculate centrality scores
            graph.calculate_centrality_scores()

            build_time = (time.time() - start_time) * 1000
            stats = graph.get_statistics()

            logger.info(
                f"Built knowledge graph in {build_time:.2f}ms",
                nodes=stats["total_nodes"],
                edges=stats["total_edges"],
                components=stats["connected_components"],
            )

            return graph

        except (
            ValueError,
            KeyError,
            json.JSONDecodeError,
            IndexError,
            RecoverableBuildError,
        ) as exc:
            # Known/parsing/validation issues: log and return a clear recoverable indicator
            logger.exception(
                "Recoverable error while building knowledge graph", error=str(exc)
            )
            return None
        except Exception as exc:
            # Unexpected/critical exceptions should propagate after logging for caller visibility
            logger.exception(
                "Unexpected error while building knowledge graph", error=str(exc)
            )
            raise

    def _create_document_nodes(
        self, search_results: list[SearchResult]
    ) -> list[GraphNode]:
        """Create document and section nodes from search results."""

        nodes = []
        seen_documents = set()

        for result in search_results:
            # Create document node
            doc_id = _doc_id_from_result(result)

            if doc_id not in seen_documents:
                seen_documents.add(doc_id)

                doc_node = GraphNode(
                    id=doc_id,
                    node_type=NodeType.DOCUMENT,
                    title=result.source_title or f"Document from {result.source_type}",
                    content=result.text[:500],  # First 500 chars as summary
                    metadata={
                        "source_type": result.source_type,
                        "source_title": result.source_title,
                        "url": result.source_url,
                        "project_id": result.project_id,
                        "collection_name": result.collection_name,
                    },
                    entities=self._extract_entities(result),
                    topics=self._extract_topics(result),
                    concepts=self._extract_concepts(result),
                    keywords=self._extract_keywords(result),
                )
                nodes.append(doc_node)

            # Create section node
            section_id = _section_id_from_result(result)
            # Build a safe title string for slicing
            _raw_title = result.section_title or result.breadcrumb_text or "Section"
            _safe_title = (
                _raw_title if isinstance(_raw_title, str) else str(_raw_title or "")
            )
            section_node = GraphNode(
                id=section_id,
                node_type=NodeType.SECTION,
                title=(_safe_title or "")[-50:],  # Last 50 chars
                content=result.text,
                metadata={
                    "parent_document": doc_id,
                    "breadcrumb": result.breadcrumb_text,
                    "section_level": result.section_level or result.depth,
                    "score": result.score,
                    "section_type": result.section_type,
                },
                entities=self._extract_entities(result),
                topics=self._extract_topics(result),
                concepts=self._extract_concepts(result),
                keywords=self._extract_keywords(result),
            )
            nodes.append(section_node)

        return nodes

    def _create_concept_nodes(
        self, search_results: list[SearchResult]
    ) -> tuple[list[GraphNode], list[GraphNode]]:
        """Create entity and topic nodes from extracted metadata."""

        # Collect all entities and topics
        entity_counts = Counter()
        topic_counts = Counter()

        for result in search_results:
            entities = self._extract_entities(result)
            topics = self._extract_topics(result)

            for entity in entities:
                entity_counts[entity] += 1
            for topic in topics:
                topic_counts[topic] += 1

        # Create nodes for frequent entities and topics
        entity_nodes = []
        topic_nodes = []

        # Entities mentioned in at least 2 documents
        for entity, count in entity_counts.items():
            if count >= 2:
                entity_node = GraphNode(
                    id=_build_stable_id("entity", entity),
                    node_type=NodeType.ENTITY,
                    title=entity,
                    metadata={"mention_count": count, "entity_type": "extracted"},
                )
                entity_nodes.append(entity_node)

        # Topics mentioned in at least 2 documents
        for topic, count in topic_counts.items():
            if count >= 2:
                topic_node = GraphNode(
                    id=_build_stable_id("topic", topic),
                    node_type=NodeType.TOPIC,
                    title=topic,
                    metadata={"mention_count": count, "topic_type": "extracted"},
                )
                topic_nodes.append(topic_node)

        return entity_nodes, topic_nodes

    def _create_relationships(
        self,
        search_results: list[SearchResult],
        graph: Any,  # KnowledgeGraph - avoiding circular import
    ) -> list[GraphEdge]:
        """Create relationships between graph nodes."""

        edges = []

        # Document -> Section relationships
        for result in search_results:
            doc_id = _doc_id_from_result(result)
            section_id = _section_id_from_result(result)

            if doc_id in graph.nodes and section_id in graph.nodes:
                edge = GraphEdge(
                    source_id=doc_id,
                    target_id=section_id,
                    relationship_type=RelationshipType.CONTAINS,
                    weight=1.0,
                    confidence=1.0,
                    evidence=["hierarchical_structure"],
                )
                edges.append(edge)

        # Entity relationships
        entity_edges = self._create_entity_relationships(search_results, graph)
        edges.extend(entity_edges)

        # Topic relationships
        topic_edges = self._create_topic_relationships(search_results, graph)
        edges.extend(topic_edges)

        # Semantic similarity relationships
        similarity_edges = self._create_similarity_relationships(graph)
        edges.extend(similarity_edges)

        return edges

    def _create_entity_relationships(
        self,
        search_results: list[SearchResult],
        graph: Any,  # KnowledgeGraph - avoiding circular import
    ) -> list[GraphEdge]:
        """Create entity-related relationships."""

        edges = []

        # Document/Section mentions Entity
        for result in search_results:
            section_id = _section_id_from_result(result)
            entities = self._extract_entities(result)

            for entity in entities:
                entity_nodes = graph.find_nodes_by_entity(entity)
                for entity_node in entity_nodes:
                    if section_id in graph.nodes:
                        edge = GraphEdge(
                            source_id=section_id,
                            target_id=entity_node.id,
                            relationship_type=RelationshipType.MENTIONS,
                            weight=0.7,
                            confidence=0.8,
                            evidence=[f"entity_extraction: {entity}"],
                        )
                        edges.append(edge)

        # Entity co-occurrence relationships
        co_occurrence_edges = self._create_entity_cooccurrence(search_results, graph)
        edges.extend(co_occurrence_edges)

        return edges

    def _create_topic_relationships(
        self,
        search_results: list[SearchResult],
        graph: Any,  # KnowledgeGraph - avoiding circular import
    ) -> list[GraphEdge]:
        """Create topic-related relationships."""

        edges = []

        # Document/Section discusses Topic
        for result in search_results:
            section_id = _section_id_from_result(result)
            topics = self._extract_topics(result)

            for topic in topics:
                topic_nodes = graph.find_nodes_by_topic(topic)
                for topic_node in topic_nodes:
                    if section_id in graph.nodes:
                        edge = GraphEdge(
                            source_id=section_id,
                            target_id=topic_node.id,
                            relationship_type=RelationshipType.DISCUSSES,
                            weight=0.6,
                            confidence=0.7,
                            evidence=[f"topic_extraction: {topic}"],
                        )
                        edges.append(edge)

        return edges

    def _create_entity_cooccurrence(
        self,
        search_results: list[SearchResult],
        graph: Any,  # KnowledgeGraph - avoiding circular import
    ) -> list[GraphEdge]:
        """Create entity co-occurrence relationships."""

        edges = []
        cooccurrence_counts = defaultdict(int)

        # Count entity co-occurrences
        for result in search_results:
            entities = self._extract_entities(result)
            for i, entity1 in enumerate(entities):
                for entity2 in entities[i + 1 :]:
                    pair = tuple(sorted([entity1, entity2]))
                    cooccurrence_counts[pair] += 1

        # Create edges for significant co-occurrences
        for (entity1, entity2), count in cooccurrence_counts.items():
            if count >= 2:  # Appeared together at least twice
                entity1_nodes = graph.find_nodes_by_entity(entity1)
                entity2_nodes = graph.find_nodes_by_entity(entity2)

                for node1 in entity1_nodes:
                    for node2 in entity2_nodes:
                        weight = min(1.0, count / 5.0)  # Normalize to max 1.0
                        edge = GraphEdge(
                            source_id=node1.id,
                            target_id=node2.id,
                            relationship_type=RelationshipType.CO_OCCURS,
                            weight=weight,
                            confidence=weight,
                            evidence=[f"co_occurrence_count: {count}"],
                        )
                        edges.append(edge)

        return edges

    def _create_similarity_relationships(
        self, graph: Any  # KnowledgeGraph - avoiding circular import
    ) -> list[GraphEdge]:
        """Create semantic similarity relationships between nodes."""

        edges = []

        # Calculate similarity between section nodes
        section_nodes = graph.find_nodes_by_type(NodeType.SECTION)

        for i, node1 in enumerate(section_nodes):
            for node2 in section_nodes[i + 1 :]:
                similarity = self._calculate_node_similarity(node1, node2)

                if (
                    similarity > SIMILARITY_EDGE_THRESHOLD
                ):  # Threshold for meaningful similarity
                    edge = GraphEdge(
                        source_id=node1.id,
                        target_id=node2.id,
                        relationship_type=RelationshipType.SIMILAR_TO,
                        weight=similarity,
                        confidence=similarity,
                        evidence=[f"semantic_similarity: {similarity:.3f}"],
                    )
                    edges.append(edge)

        return edges

    def _calculate_node_similarity(self, node1: GraphNode, node2: GraphNode) -> float:
        """Calculate similarity between two nodes."""
        return calculate_node_similarity(node1, node2)

    def _extract_entities(self, result: SearchResult) -> list[str]:
        return extract_entities_from_result(result)

    def _extract_topics(self, result: SearchResult) -> list[str]:
        return extract_topics_from_result(result)

    def _extract_concepts(self, result: SearchResult) -> list[str]:
        return extract_concepts_from_result(result)

    def _extract_keywords(self, result: SearchResult) -> list[str]:
        return extract_keywords_from_result(result)


def _stable_hash(value: Any) -> str:
    """Compute a deterministic SHA-256 hex digest for a value using stable serialization."""
    try:
        canonical = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
    except Exception:
        canonical = str(value)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _build_stable_id(prefix: str, value: Any, digest_length: int = 16) -> str:
    """Build a stable node id using a prefix and the truncated SHA-256 digest of the value."""
    digest = _stable_hash(value)[:digest_length]
    return f"{prefix}_{digest}"


def _id_from_result(result: Any, prefix: str) -> str:
    """Create a stable node id from a search result using a given prefix.

    Shared logic for document and section identifiers:
    - Use result.source_url if present
    - Otherwise fallback to the first 100 characters of result.text
    - Include result.source_type (defaulting to "unknown") in the id
    The final id format is: {prefix}_{source_type}_{digest}
    where digest is the first 16 characters of the SHA-256 hexdigest.
    """
    source_type = getattr(result, "source_type", "") or "unknown"
    preferred_identifier = getattr(result, "source_url", None)
    if not preferred_identifier:
        preferred_identifier = (getattr(result, "text", "") or "")[:100]
    if not isinstance(preferred_identifier, str):
        preferred_identifier = str(preferred_identifier)

    digest = hashlib.sha256(preferred_identifier.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{source_type}_{digest}"


def _doc_id_from_result(result: Any) -> str:
    """Create a stable document node id from a search result."""
    return _id_from_result(result, "doc")


def _section_id_from_result(result: Any) -> str:
    """Create a stable section node id from a search result."""
    return _id_from_result(result, "section")
