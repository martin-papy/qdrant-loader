"""Enhanced hybrid search implementation combining vector, keyword, and graph search."""

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, cast

from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models

from ..utils.logging import LoggingConfig
from .hybrid_search import HybridSearchEngine
from .models import SearchResult

logger = LoggingConfig.get_logger(__name__)


class SearchMode(Enum):
    """Search mode enumeration."""

    VECTOR_ONLY = "vector_only"
    GRAPH_ONLY = "graph_only"
    HYBRID = "hybrid"
    AUTO = "auto"


class FusionStrategy(Enum):
    """Result fusion strategy enumeration."""

    WEIGHTED_SUM = "weighted_sum"
    RANK_FUSION = "rank_fusion"
    RECIPROCAL_RANK_FUSION = "reciprocal_rank_fusion"
    MMR = "maximal_marginal_relevance"
    GRAPH_ENHANCED_WEIGHTED = "graph_enhanced_weighted"
    CONFIDENCE_ADAPTIVE = "confidence_adaptive"
    MULTI_STAGE = "multi_stage"
    CONTEXT_AWARE = "context_aware"


class RerankingStrategy(Enum):
    """Reranking strategy enumeration."""

    NONE = "none"
    CROSS_ENCODER = "cross_encoder"
    DIVERSITY_MMR = "diversity_mmr"
    TEMPORAL_BOOST = "temporal_boost"
    CONTEXTUAL_BOOST = "contextual_boost"
    COMBINED = "combined"


@dataclass
class QueryWeights:
    """Query-time weight overrides for search result fusion."""

    vector_weight: float | None = None
    keyword_weight: float | None = None
    graph_weight: float | None = None

    def __post_init__(self):
        """Validate weights after initialization."""
        if self.has_weights():
            self._validate_weights()

    def has_weights(self) -> bool:
        """Check if any weights are specified."""
        return any(
            [
                self.vector_weight is not None,
                self.keyword_weight is not None,
                self.graph_weight is not None,
            ]
        )

    def get_effective_weights(
        self, config: "EnhancedSearchConfig"
    ) -> tuple[float, float, float]:
        """Get effective weights, using query-time overrides or config defaults."""
        vector_weight = (
            self.vector_weight
            if self.vector_weight is not None
            else config.vector_weight
        )
        keyword_weight = (
            self.keyword_weight
            if self.keyword_weight is not None
            else config.keyword_weight
        )
        graph_weight = (
            self.graph_weight if self.graph_weight is not None else config.graph_weight
        )

        return vector_weight, keyword_weight, graph_weight

    def _validate_weights(self) -> None:
        """Validate that weights are within valid ranges and sum appropriately."""
        weights = []

        if self.vector_weight is not None:
            if not 0.0 <= self.vector_weight <= 1.0:
                raise ValueError(
                    f"vector_weight must be between 0.0 and 1.0, got {self.vector_weight}"
                )
            weights.append(self.vector_weight)

        if self.keyword_weight is not None:
            if not 0.0 <= self.keyword_weight <= 1.0:
                raise ValueError(
                    f"keyword_weight must be between 0.0 and 1.0, got {self.keyword_weight}"
                )
            weights.append(self.keyword_weight)

        if self.graph_weight is not None:
            if not 0.0 <= self.graph_weight <= 1.0:
                raise ValueError(
                    f"graph_weight must be between 0.0 and 1.0, got {self.graph_weight}"
                )
            weights.append(self.graph_weight)

        # If all three weights are specified, they should sum to 1.0 (with tolerance)
        if len(weights) == 3:
            total = sum(weights)
            if not 0.99 <= total <= 1.01:  # Allow small floating point tolerance
                raise ValueError(f"All three weights must sum to 1.0, got {total}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for caching and serialization."""
        return {
            "vector_weight": self.vector_weight,
            "keyword_weight": self.keyword_weight,
            "graph_weight": self.graph_weight,
        }


def validate_query_weights(
    vector_weight: float | None = None,
    keyword_weight: float | None = None,
    graph_weight: float | None = None,
) -> QueryWeights:
    """Validate and create QueryWeights instance.

    Args:
        vector_weight: Weight for vector search results (0.0-1.0)
        keyword_weight: Weight for keyword search results (0.0-1.0)
        graph_weight: Weight for graph search results (0.0-1.0)

    Returns:
        Validated QueryWeights instance

    Raises:
        ValueError: If weights are invalid
    """
    return QueryWeights(
        vector_weight=vector_weight,
        keyword_weight=keyword_weight,
        graph_weight=graph_weight,
    )


@dataclass
class EnhancedSearchConfig:
    """Configuration for enhanced hybrid search operations."""

    # Search mode and strategy
    mode: SearchMode = SearchMode.HYBRID
    fusion_strategy: FusionStrategy = FusionStrategy.RECIPROCAL_RANK_FUSION

    # Weighting parameters
    vector_weight: float = 0.5
    keyword_weight: float = 0.2
    graph_weight: float = 0.3

    # Search limits
    vector_limit: int = 50
    graph_limit: int = 50
    final_limit: int = 10

    # Score thresholds
    min_vector_score: float = 0.3
    min_graph_score: float = 0.1
    min_combined_score: float = 0.2

    # Graph search parameters
    max_graph_depth: int = 3
    include_entity_relationships: bool = True
    include_temporal_context: bool = True
    use_graphiti: bool = True

    # Caching configuration
    enable_caching: bool = True
    cache_ttl: int = 300  # 5 minutes
    cache_max_size: int = 1000  # Maximum number of cached entries
    cache_cleanup_interval: int = 60  # Cleanup interval in seconds

    # Reranking configuration
    enable_reranking: bool = True
    rerank_top_k: int = 20
    reranking_strategy: RerankingStrategy = RerankingStrategy.COMBINED

    # Cross-encoder reranking
    cross_encoder_model: str = "openai"  # "openai" or "bge"
    cross_encoder_threshold: float = 0.5

    # Diversity reranking (MMR-style)
    diversity_lambda: float = 0.7  # Balance between relevance and diversity
    diversity_threshold: float = 0.8  # Similarity threshold for diversity filtering

    # Temporal reranking
    temporal_decay_factor: float = 0.1  # How much to decay scores based on age
    temporal_boost_recent: float = 1.2  # Boost factor for recent content
    temporal_recent_threshold_days: int = 30  # Days to consider "recent"

    # Contextual reranking
    enable_user_feedback: bool = False
    enable_query_context: bool = True
    context_boost_factor: float = 1.1


@dataclass
class EnhancedSearchResult:
    """Enhanced search result with vector, keyword, and graph components."""

    # Core result data
    id: str
    content: str
    title: str
    source_type: str

    # Scoring information
    combined_score: float
    vector_score: float = 0.0
    keyword_score: float = 0.0
    graph_score: float = 0.0
    rerank_score: float = 0.0

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    # Vector search specific
    vector_distance: float = 0.0
    embedding_model: str | None = None

    # Graph search specific
    entity_ids: list[str] = field(default_factory=list)
    relationship_types: list[str] = field(default_factory=list)
    graph_distance: int = 0
    centrality_score: float = 0.0
    temporal_relevance: float = 0.0

    # Additional context
    explanation: str | None = None
    debug_info: dict[str, Any] = field(default_factory=dict)


class VectorSearchModule:
    """Enhanced vector search module using QDrant."""

    def __init__(
        self,
        qdrant_client: QdrantClient,
        openai_client: AsyncOpenAI,
        collection_name: str,
    ):
        """Initialize vector search module.

        Args:
            qdrant_client: QDrant client instance
            openai_client: OpenAI client instance
            collection_name: Name of the Qdrant collection
        """
        self.qdrant_client = qdrant_client
        self.openai_client = openai_client
        self.collection_name = collection_name
        self.logger = LoggingConfig.get_logger(__name__)

    async def search(
        self,
        query: str,
        limit: int,
        min_score: float = 0.3,
        project_ids: list[str] | None = None,
        **kwargs,
    ) -> list[EnhancedSearchResult]:
        """Perform vector search using QDrant.

        Args:
            query: Search query text
            limit: Maximum number of results
            min_score: Minimum similarity score threshold
            project_ids: Optional project ID filter
            **kwargs: Additional search parameters

        Returns:
            List of search results with vector scores
        """
        try:
            # Get query embedding
            query_embedding = await self._get_embedding(query)

            # Build filter for project IDs
            search_filter = self._build_filter(project_ids) if project_ids else None

            # Perform vector search
            search_params = models.SearchParams(hnsw_ef=128, exact=False)

            results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=min_score,
                search_params=search_params,
                query_filter=search_filter,
            )

            # Convert to EnhancedSearchResult objects
            search_results = []
            for result in results:
                if result.score >= min_score:
                    payload = result.payload or {}
                    metadata = payload.get("metadata", {})

                    search_result = EnhancedSearchResult(
                        id=str(result.id),
                        content=payload.get("content", ""),
                        title=metadata.get("title", ""),
                        source_type=payload.get("source_type", "unknown"),
                        combined_score=result.score,
                        vector_score=result.score,
                        vector_distance=1.0
                        - result.score,  # Convert similarity to distance
                        metadata=metadata,
                        debug_info={
                            "search_type": "vector",
                            "qdrant_id": str(result.id),
                        },
                    )
                    search_results.append(search_result)

            self.logger.debug(f"Vector search returned {len(search_results)} results")
            return search_results

        except Exception as e:
            self.logger.error(f"Vector search failed: {e}")
            raise

    async def _get_embedding(self, text: str) -> list[float]:
        """Get embedding for text using OpenAI."""
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            self.logger.error(f"Failed to get embedding: {e}")
            raise

    def _build_filter(self, project_ids: list[str]) -> models.Filter:
        """Build filter for project IDs."""
        return models.Filter(
            must=[
                models.FieldCondition(
                    key="project_id", match=models.MatchAny(any=project_ids)
                )
            ]
        )


class GraphSearchModule:
    """Graph search module using Neo4j and Graphiti."""

    def __init__(self, neo4j_manager=None, graphiti_manager=None):
        """Initialize graph search module.

        Args:
            neo4j_manager: Neo4jManager instance (optional)
            graphiti_manager: GraphitiManager instance (optional)
        """
        self.neo4j_manager = neo4j_manager
        self.graphiti_manager = graphiti_manager
        self.logger = LoggingConfig.get_logger(__name__)

    async def search(
        self,
        query: str,
        limit: int,
        max_depth: int = 3,
        include_relationships: bool = True,
        include_temporal: bool = True,
        use_graphiti: bool = True,
        **kwargs,
    ) -> list[EnhancedSearchResult]:
        """Perform graph search using Neo4j and Graphiti.

        Args:
            query: Search query text
            limit: Maximum number of results
            max_depth: Maximum graph traversal depth
            include_relationships: Include relationship information
            include_temporal: Include temporal context
            use_graphiti: Use Graphiti for search if available
            **kwargs: Additional search parameters

        Returns:
            List of search results with graph scores
        """
        try:
            search_results = []

            # Use Graphiti for entity-based search if available and enabled
            if use_graphiti and self.graphiti_manager:
                graphiti_results = await self._search_with_graphiti(
                    query, limit, **kwargs
                )
                search_results.extend(graphiti_results)

            # Use Neo4j for direct graph queries if available
            if self.neo4j_manager:
                neo4j_results = await self._search_with_neo4j(
                    query, limit, max_depth, include_relationships, include_temporal
                )
                search_results.extend(neo4j_results)

            # Remove duplicates and sort by score
            unique_results = self._deduplicate_results(search_results)
            unique_results.sort(key=lambda x: x.graph_score, reverse=True)

            self.logger.debug(f"Graph search returned {len(unique_results)} results")
            return unique_results[:limit]

        except Exception as e:
            self.logger.error(f"Graph search failed: {e}")
            # Return empty results instead of raising to allow fallback to vector search
            return []

    async def _search_with_graphiti(
        self, query: str, limit: int, center_node_uuid: str | None = None, **kwargs
    ) -> list[EnhancedSearchResult]:
        """Search using Graphiti knowledge graph."""
        try:
            if not self.graphiti_manager:
                return []

            # Ensure Graphiti manager is initialized
            if not self.graphiti_manager.is_initialized:
                await self.graphiti_manager.initialize()

            # Perform Graphiti hybrid search with RRF reranking
            results = await self.graphiti_manager.search(
                query=query,
                limit=limit,
                center_node_uuid=center_node_uuid,
            )

            # Convert Graphiti results to EnhancedSearchResult objects
            search_results = []
            for i, result in enumerate(results):
                # Extract information from Graphiti result (edges with facts)
                fact_text = getattr(result, "fact", str(result))

                # Extract entity information if available
                entity_ids = []
                relationship_types = []

                # Try to extract source and target node UUIDs
                if hasattr(result, "source_node_uuid"):
                    entity_ids.append(str(result.source_node_uuid))
                if hasattr(result, "target_node_uuid"):
                    entity_ids.append(str(result.target_node_uuid))

                # Try to extract relationship type
                if hasattr(result, "relation_type"):
                    relationship_types.append(str(result.relation_type))

                search_result = EnhancedSearchResult(
                    id=f"graphiti_{i}_{hashlib.md5(fact_text.encode()).hexdigest()[:8]}",
                    content=fact_text,
                    title="Knowledge Graph Fact",
                    source_type="knowledge_graph",
                    combined_score=1.0 - (i * 0.05),  # Decreasing score based on rank
                    graph_score=1.0 - (i * 0.05),
                    entity_ids=entity_ids,
                    relationship_types=relationship_types,
                    temporal_relevance=1.0 - (i * 0.02),  # Slight temporal decay
                    debug_info={
                        "search_type": "graphiti",
                        "result_rank": i,
                        "center_node": center_node_uuid,
                        "fact_uuid": getattr(result, "uuid", None),
                    },
                )
                search_results.append(search_result)

            return search_results

        except Exception as e:
            self.logger.error(f"Graphiti search failed: {e}")
            return []

    async def _search_with_neo4j(
        self,
        query: str,
        limit: int,
        max_depth: int,
        include_relationships: bool,
        include_temporal: bool,
    ) -> list[EnhancedSearchResult]:
        """Search using direct Neo4j queries with enhanced relationship analysis."""
        try:
            if not self.neo4j_manager:
                return []

            # Ensure Neo4j manager is connected
            if not self.neo4j_manager.is_connected:
                self.neo4j_manager.connect()

            # Enhanced Cypher query for comprehensive graph search
            cypher_query = """
            // Multi-strategy search combining fulltext, semantic, and graph traversal
            CALL {
                // Strategy 1: Fulltext search on indexed content
                CALL {
                    CALL db.index.fulltext.queryNodes('entity_text_index', $query)
                    YIELD node, score
                    RETURN node, score, 'fulltext' as search_type
                    LIMIT $limit
                }
                UNION
                // Strategy 2: CONTAINS search for broader matching
                CALL {
                    MATCH (node)
                    WHERE any(prop in keys(node) WHERE toString(node[prop]) CONTAINS $query)
                    RETURN node, 0.5 as score, 'contains' as search_type
                    LIMIT $limit
                }
                UNION
                // Strategy 3: Semantic property matching
                CALL {
                    MATCH (node)
                    WHERE node.title =~ ('(?i).*' + $query + '.*') 
                       OR node.content =~ ('(?i).*' + $query + '.*')
                       OR node.description =~ ('(?i).*' + $query + '.*')
                    RETURN node, 0.7 as score, 'semantic' as search_type
                    LIMIT $limit
                }
            }
            WITH node, score, search_type
            
            // Enhanced relationship and centrality analysis
            OPTIONAL MATCH (node)-[r]-(related)
            WITH node, score, search_type, 
                 collect(DISTINCT {
                     type: type(r), 
                     direction: CASE 
                         WHEN startNode(r) = node THEN 'outgoing'
                         ELSE 'incoming'
                     END,
                     target_id: elementId(related),
                     target_labels: labels(related),
                     properties: properties(r)
                 }) as relationships,
                 count(DISTINCT related) as direct_connections
            
            // Calculate graph distance and centrality metrics
            OPTIONAL MATCH path = (node)-[*1..3]-(distant)
            WITH node, score, search_type, relationships, direct_connections,
                 collect(DISTINCT {
                     distance: length(path),
                     target_id: elementId(distant),
                     target_labels: labels(distant)
                 }) as graph_distances,
                 count(DISTINCT distant) as extended_connections
            
            // Calculate PageRank-style centrality approximation
            WITH node, score, search_type, relationships, direct_connections,
                 graph_distances, extended_connections,
                 CASE 
                     WHEN direct_connections > 0 
                     THEN (direct_connections * 1.0 + extended_connections * 0.3) / 10.0
                     ELSE 0.0
                 END as centrality_score
            
            // Temporal relevance calculation
            WITH node, score, search_type, relationships, direct_connections,
                 graph_distances, extended_connections, centrality_score,
                 CASE 
                     WHEN node.updated_at IS NOT NULL 
                     THEN duration.between(node.updated_at, datetime()).days
                     WHEN node.created_at IS NOT NULL
                     THEN duration.between(node.created_at, datetime()).days
                     ELSE 365
                 END as days_since_update
            
            // Calculate temporal relevance score (newer = higher score)
            WITH node, score, search_type, relationships, direct_connections,
                 graph_distances, extended_connections, centrality_score, days_since_update,
                 CASE 
                     WHEN days_since_update <= 7 THEN 1.0
                     WHEN days_since_update <= 30 THEN 0.8
                     WHEN days_since_update <= 90 THEN 0.6
                     WHEN days_since_update <= 365 THEN 0.4
                     ELSE 0.2
                 END as temporal_relevance
            
            // Final score calculation combining multiple factors
            WITH node, score, search_type, relationships, direct_connections,
                 graph_distances, extended_connections, centrality_score, 
                 temporal_relevance, days_since_update,
                 (score + centrality_score * 0.3 + temporal_relevance * 0.2) as final_score
            
            RETURN elementId(node) as id,
                   coalesce(node.content, node.text, node.description, '') as content,
                   coalesce(node.title, node.name, 'Neo4j Node') as title,
                   coalesce(node.source_type, 'neo4j') as source_type,
                   final_score as score,
                   search_type,
                   relationships,
                   direct_connections,
                   extended_connections,
                   centrality_score,
                   temporal_relevance,
                   days_since_update,
                   graph_distances,
                   node.created_at as created_at,
                   node.updated_at as updated_at,
                   labels(node) as node_labels,
                   properties(node) as node_properties
            ORDER BY final_score DESC
            LIMIT $limit
            """

            # Execute enhanced query
            try:
                results = self.neo4j_manager.execute_read_transaction(
                    cypher_query, query=query, limit=limit
                )

                # Convert Neo4j results to EnhancedSearchResult objects
                search_results = []
                for i, result in enumerate(results):
                    # Extract enhanced scoring information
                    base_score = float(result.get("score", 0.0))
                    centrality = float(result.get("centrality_score", 0.0))
                    temporal_relevance = float(result.get("temporal_relevance", 1.0))

                    # Extract relationship information
                    relationships = result.get("relationships", [])
                    relationship_types = list(
                        set(
                            [
                                rel.get("type", "")
                                for rel in relationships
                                if rel.get("type")
                            ]
                        )
                    )

                    # Calculate graph distance (average of all paths)
                    graph_distances = result.get("graph_distances", [])
                    avg_graph_distance = 0
                    if graph_distances:
                        distances = [
                            gd.get("distance", 0)
                            for gd in graph_distances
                            if gd.get("distance")
                        ]
                        avg_graph_distance = (
                            sum(distances) / len(distances) if distances else 0
                        )

                    # Extract entity IDs from relationships
                    entity_ids = [result.get("id", "")]
                    for rel in relationships:
                        if rel.get("target_id"):
                            entity_ids.append(rel["target_id"])

                    # Create enhanced metadata
                    enhanced_metadata = {
                        "node_labels": result.get("node_labels", []),
                        "created_at": result.get("created_at"),
                        "updated_at": result.get("updated_at"),
                        "search_type": result.get("search_type", "unknown"),
                        "direct_connections": result.get("direct_connections", 0),
                        "extended_connections": result.get("extended_connections", 0),
                        "days_since_update": result.get("days_since_update", 0),
                        "node_properties": result.get("node_properties", {}),
                        "relationship_details": relationships,
                        "graph_distances": graph_distances,
                    }

                    search_result = EnhancedSearchResult(
                        id=f"neo4j_{result['id']}",
                        content=result.get("content", ""),
                        title=result.get("title", "Neo4j Node"),
                        source_type=result.get("source_type", "neo4j"),
                        combined_score=base_score,
                        graph_score=base_score,
                        centrality_score=centrality,
                        temporal_relevance=temporal_relevance,
                        graph_distance=int(avg_graph_distance),
                        relationship_types=relationship_types,
                        entity_ids=entity_ids,
                        metadata=enhanced_metadata,
                        debug_info={
                            "search_type": "neo4j_enhanced",
                            "base_score": base_score,
                            "centrality_boost": centrality,
                            "temporal_boost": temporal_relevance,
                            "result_rank": i,
                            "query_strategy": result.get("search_type", "unknown"),
                        },
                    )
                    search_results.append(search_result)

                return search_results

            except Exception as e:
                self.logger.error(f"Enhanced Neo4j query failed: {e}")
                # Fallback to simpler query
                return await self._fallback_neo4j_search(query, limit)

        except Exception as e:
            self.logger.error(f"Neo4j search failed: {e}")
            return []

    async def _fallback_neo4j_search(
        self, query: str, limit: int
    ) -> list[EnhancedSearchResult]:
        """Fallback Neo4j search with simpler queries."""
        try:
            if not self.neo4j_manager:
                return []

            # Simple fallback query
            fallback_query = """
            MATCH (node)
            WHERE any(prop in keys(node) WHERE toString(node[prop]) CONTAINS $query)
            OPTIONAL MATCH (node)-[r]-(related)
            WITH node, count(DISTINCT related) as connections,
                 collect(DISTINCT type(r)) as relationship_types
            RETURN elementId(node) as id,
                   coalesce(node.content, node.text, node.name, '') as content,
                   coalesce(node.title, node.name, 'Neo4j Node') as title,
                   coalesce(node.source_type, 'neo4j') as source_type,
                   0.5 as score,
                   connections,
                   relationship_types,
                   labels(node) as node_labels
            ORDER BY connections DESC
            LIMIT $limit
            """

            results = self.neo4j_manager.execute_read_transaction(
                fallback_query, query=query, limit=limit
            )

            search_results = []
            for i, result in enumerate(results):
                search_result = EnhancedSearchResult(
                    id=f"neo4j_fallback_{result['id']}",
                    content=result.get("content", ""),
                    title=result.get("title", "Neo4j Node"),
                    source_type=result.get("source_type", "neo4j"),
                    combined_score=0.5 - (i * 0.05),
                    graph_score=0.5 - (i * 0.05),
                    centrality_score=float(result.get("connections", 0)) * 0.1,
                    relationship_types=result.get("relationship_types", []),
                    metadata={
                        "node_labels": result.get("node_labels", []),
                        "connections": result.get("connections", 0),
                    },
                    debug_info={
                        "search_type": "neo4j_fallback",
                        "result_rank": i,
                    },
                )
                search_results.append(search_result)

            return search_results

        except Exception as e:
            self.logger.error(f"Fallback Neo4j search failed: {e}")
            return []

    def _deduplicate_results(
        self, results: list[EnhancedSearchResult]
    ) -> list[EnhancedSearchResult]:
        """Remove duplicate results based on content similarity."""
        seen_ids = set()
        unique_results = []

        for result in results:
            content_hash = hashlib.md5(result.content.encode()).hexdigest()
            if content_hash not in seen_ids:
                seen_ids.add(content_hash)
                unique_results.append(result)

        return unique_results


class ResultFusionEngine:
    """Engine for fusing results from multiple search modules."""

    def __init__(self, config: EnhancedSearchConfig):
        """Initialize fusion engine.

        Args:
            config: Search configuration
        """
        self.config = config
        self.logger = LoggingConfig.get_logger(__name__)

    def normalize_scores(
        self, results: list[EnhancedSearchResult], score_field: str = "combined_score"
    ) -> list[EnhancedSearchResult]:
        """Normalize scores to 0-1 range using min-max normalization.

        Args:
            results: List of search results to normalize
            score_field: Field name containing the score to normalize

        Returns:
            Results with normalized scores
        """
        if not results:
            return results

        try:
            scores = [getattr(result, score_field) for result in results]
            min_score = min(scores)
            max_score = max(scores)

            # Avoid division by zero
            if max_score == min_score:
                for result in results:
                    setattr(result, score_field, 1.0)
            else:
                score_range = max_score - min_score
                for result in results:
                    current_score = getattr(result, score_field)
                    normalized_score = (current_score - min_score) / score_range
                    setattr(result, score_field, normalized_score)

            return results

        except Exception as e:
            self.logger.warning(f"Score normalization failed: {e}")
            return results

    def apply_score_boosting(
        self, results: list[EnhancedSearchResult]
    ) -> list[EnhancedSearchResult]:
        """Apply score boosting based on result characteristics.

        Args:
            results: List of search results

        Returns:
            Results with boosted scores
        """
        try:
            for result in results:
                boost_factor = 1.0

                # Boost based on centrality score (for graph results)
                if result.centrality_score > 0:
                    boost_factor += 0.1 * result.centrality_score

                # Boost based on temporal relevance
                if result.temporal_relevance > 0:
                    boost_factor += 0.05 * result.temporal_relevance

                # Boost based on entity count (more entities = more connected)
                if result.entity_ids:
                    entity_boost = min(0.2, len(result.entity_ids) * 0.02)
                    boost_factor += entity_boost

                # Boost based on relationship diversity
                if result.relationship_types:
                    relationship_boost = min(
                        0.15, len(set(result.relationship_types)) * 0.03
                    )
                    boost_factor += relationship_boost

                # Apply boost to combined score
                result.combined_score *= boost_factor

                # Store boost information in debug info
                result.debug_info["boost_factor"] = boost_factor

            return results

        except Exception as e:
            self.logger.warning(f"Score boosting failed: {e}")
            return results

    def select_optimal_fusion_strategy(
        self,
        query: str,
        vector_results: list[EnhancedSearchResult],
        keyword_results: list[EnhancedSearchResult],
        graph_results: list[EnhancedSearchResult],
    ) -> FusionStrategy:
        """Select the optimal fusion strategy based on query and result characteristics.

        Args:
            query: Search query text
            vector_results: Results from vector search
            keyword_results: Results from keyword search
            graph_results: Results from graph search

        Returns:
            Recommended fusion strategy
        """
        try:
            # Analyze query characteristics
            query_tokens = query.lower().split()
            query_length = len(query_tokens)

            # Count results from each source
            vector_count = len(vector_results)
            keyword_count = len(keyword_results)
            graph_count = len(graph_results)
            total_results = vector_count + keyword_count + graph_count

            # Calculate result quality metrics
            avg_vector_score = (
                sum(r.vector_score for r in vector_results) / vector_count
                if vector_count > 0
                else 0
            )
            avg_keyword_score = (
                sum(r.keyword_score for r in keyword_results) / keyword_count
                if keyword_count > 0
                else 0
            )
            avg_graph_score = (
                sum(r.graph_score for r in graph_results) / graph_count
                if graph_count > 0
                else 0
            )

            # Calculate result diversity (unique content)
            all_results = vector_results + keyword_results + graph_results
            unique_content = set()
            for result in all_results:
                content_hash = hashlib.md5(result.content.encode()).hexdigest()
                unique_content.add(content_hash)

            diversity_ratio = (
                len(unique_content) / len(all_results) if all_results else 0
            )

            # Calculate graph richness (centrality and relationships)
            graph_richness = 0.0
            if graph_results:
                total_centrality = sum(r.centrality_score for r in graph_results)
                total_entities = sum(len(r.entity_ids) for r in graph_results)
                total_relationships = sum(
                    len(r.relationship_types) for r in graph_results
                )
                graph_richness = (
                    total_centrality + total_entities * 0.1 + total_relationships * 0.05
                ) / graph_count

            # Enhanced decision logic for fusion strategy selection

            # Context-aware fusion for complex scenarios with mixed quality
            if (
                total_results > 15
                and abs(avg_vector_score - avg_graph_score) < 0.3
                and diversity_ratio > 0.6
            ):
                self.logger.debug(
                    "Selected context-aware fusion due to complex mixed-quality scenario"
                )
                return FusionStrategy.CONTEXT_AWARE

            # Graph-enhanced weighted for high-quality graph results
            if graph_count > 5 and avg_graph_score > 0.6 and graph_richness > 0.5:
                self.logger.debug(
                    "Selected graph-enhanced weighted fusion due to high-quality graph results"
                )
                return FusionStrategy.GRAPH_ENHANCED_WEIGHTED

            # Multi-stage fusion for large result sets that need refinement
            if total_results > 25:
                self.logger.debug("Selected multi-stage fusion due to large result set")
                return FusionStrategy.MULTI_STAGE

            # Confidence adaptive for unbalanced result quality
            if (
                max(avg_vector_score, avg_keyword_score, avg_graph_score)
                - min(avg_vector_score, avg_keyword_score, avg_graph_score)
                > 0.4
            ):
                self.logger.debug(
                    "Selected confidence adaptive fusion due to unbalanced result quality"
                )
                return FusionStrategy.CONFIDENCE_ADAPTIVE

            # MMR for diverse results or when we want to avoid redundancy
            if diversity_ratio < 0.7 and len(all_results) > 10:
                self.logger.debug("Selected MMR fusion due to low diversity")
                return FusionStrategy.MMR

            # RRF when we have balanced results from multiple sources
            if (
                vector_count > 5
                and keyword_count > 5
                and graph_count > 5
                and abs(vector_count - keyword_count) < 10
                and abs(vector_count - graph_count) < 10
            ):
                self.logger.debug(
                    "Selected RRF fusion due to balanced multi-source results"
                )
                return FusionStrategy.RECIPROCAL_RANK_FUSION

            # Weighted sum for simple queries or when one source dominates
            if query_length <= 3 or max(
                vector_count, keyword_count, graph_count
            ) > 2 * min(vector_count, keyword_count, graph_count):
                self.logger.debug(
                    "Selected weighted sum fusion for simple query or dominant source"
                )
                return FusionStrategy.WEIGHTED_SUM

            # Default to graph-enhanced weighted for general cases
            self.logger.debug(
                "Selected graph-enhanced weighted fusion as enhanced default"
            )
            return FusionStrategy.GRAPH_ENHANCED_WEIGHTED

        except Exception as e:
            self.logger.warning(f"Fusion strategy selection failed: {e}")
            return FusionStrategy.GRAPH_ENHANCED_WEIGHTED  # Enhanced default

    def fuse_results(
        self,
        vector_results: list[EnhancedSearchResult],
        keyword_results: list[EnhancedSearchResult],
        graph_results: list[EnhancedSearchResult],
        query_weights: QueryWeights | None = None,
    ) -> list[EnhancedSearchResult]:
        """Fuse results from vector, keyword, and graph search.

        Args:
            vector_results: Results from vector search
            keyword_results: Results from keyword search
            graph_results: Results from graph search
            query_weights: Optional query-time weight overrides

        Returns:
            Fused and ranked results
        """
        try:
            # Normalize scores within each result type for fair comparison
            vector_results = self.normalize_scores(vector_results, "vector_score")
            keyword_results = self.normalize_scores(keyword_results, "keyword_score")
            graph_results = self.normalize_scores(graph_results, "graph_score")

            # Apply fusion strategy
            if self.config.fusion_strategy == FusionStrategy.WEIGHTED_SUM:
                fused_results = self._weighted_sum_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )
            elif self.config.fusion_strategy == FusionStrategy.RECIPROCAL_RANK_FUSION:
                fused_results = self._reciprocal_rank_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )
            elif self.config.fusion_strategy == FusionStrategy.MMR:
                fused_results = self._mmr_fusion(
                    vector_results,
                    keyword_results,
                    graph_results,
                    query_weights=query_weights,
                )
            elif self.config.fusion_strategy == FusionStrategy.GRAPH_ENHANCED_WEIGHTED:
                fused_results = self._graph_enhanced_weighted_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )
            elif self.config.fusion_strategy == FusionStrategy.CONFIDENCE_ADAPTIVE:
                fused_results = self._confidence_adaptive_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )
            elif self.config.fusion_strategy == FusionStrategy.MULTI_STAGE:
                fused_results = self._multi_stage_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )
            elif self.config.fusion_strategy == FusionStrategy.CONTEXT_AWARE:
                fused_results = self._context_aware_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )
            else:
                # Default to weighted sum
                fused_results = self._weighted_sum_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )

            # Apply score boosting based on result characteristics
            fused_results = self.apply_score_boosting(fused_results)

            # Final normalization of combined scores - but preserve relative ordering
            # and ensure no scores become exactly 0 unless they were originally 0
            if len(fused_results) > 1:
                # Store original scores to detect if any were originally > 0
                original_scores = [r.combined_score for r in fused_results]
                min_original = min(original_scores)

                # Apply normalization
                fused_results = self.normalize_scores(fused_results, "combined_score")

                # If normalization created zeros from non-zero scores, adjust
                if min_original > 0:
                    for result in fused_results:
                        if result.combined_score == 0.0:
                            result.combined_score = 0.001  # Small non-zero value
            elif len(fused_results) == 1:
                # Single result gets score 1.0
                fused_results[0].combined_score = 1.0

            # Sort by final combined score
            fused_results.sort(key=lambda x: x.combined_score, reverse=True)

            # Add fusion strategy information to debug info
            for result in fused_results:
                result.debug_info["fusion_strategy"] = self.config.fusion_strategy.value
                result.debug_info["weights"] = {
                    "vector": self.config.vector_weight,
                    "keyword": self.config.keyword_weight,
                    "graph": self.config.graph_weight,
                }

            return fused_results[: self.config.final_limit]

        except Exception as e:
            self.logger.error(f"Result fusion failed: {e}")
            # Return vector results as fallback
            return vector_results[: self.config.final_limit]

    def _weighted_sum_fusion(
        self,
        vector_results: list[EnhancedSearchResult],
        keyword_results: list[EnhancedSearchResult],
        graph_results: list[EnhancedSearchResult],
        query_weights: QueryWeights | None = None,
    ) -> list[EnhancedSearchResult]:
        """Fuse results using weighted sum of scores."""
        # Create a mapping of content to results
        result_map = {}

        # Add vector results
        for result in vector_results:
            key = self._get_result_key(result)
            if key not in result_map:
                result_map[key] = result
            else:
                # Update existing result with vector score
                result_map[key].vector_score = max(
                    result_map[key].vector_score, result.vector_score
                )

        # Add keyword results
        for result in keyword_results:
            key = self._get_result_key(result)
            if key not in result_map:
                result_map[key] = result
            else:
                # Update existing result with keyword score
                result_map[key].keyword_score = max(
                    result_map[key].keyword_score, result.keyword_score
                )

        # Add graph results
        for result in graph_results:
            key = self._get_result_key(result)
            if key not in result_map:
                result_map[key] = result
            else:
                # Update existing result with graph score
                result_map[key].graph_score = max(
                    result_map[key].graph_score, result.graph_score
                )
                # Merge graph-specific information
                result_map[key].entity_ids.extend(result.entity_ids)
                result_map[key].relationship_types.extend(result.relationship_types)
                result_map[key].centrality_score = max(
                    result_map[key].centrality_score, result.centrality_score
                )

        # Get effective weights (query-time overrides or config defaults)
        if query_weights and query_weights.has_weights():
            vector_weight, keyword_weight, graph_weight = (
                query_weights.get_effective_weights(self.config)
            )
        else:
            vector_weight, keyword_weight, graph_weight = (
                self.config.vector_weight,
                self.config.keyword_weight,
                self.config.graph_weight,
            )

        # Calculate combined scores
        fused_results = []
        for result in result_map.values():
            combined_score = (
                vector_weight * result.vector_score
                + keyword_weight * result.keyword_score
                + graph_weight * result.graph_score
            )

            # Ensure minimum positive score if any component score is > 0
            if (
                result.vector_score > 0
                or result.keyword_score > 0
                or result.graph_score > 0
            ):
                combined_score = max(combined_score, 0.001)

            if combined_score >= self.config.min_combined_score:
                result.combined_score = combined_score
                fused_results.append(result)

        # Sort by combined score
        fused_results.sort(key=lambda x: x.combined_score, reverse=True)
        return fused_results[: self.config.final_limit]

    def _reciprocal_rank_fusion(
        self,
        vector_results: list[EnhancedSearchResult],
        keyword_results: list[EnhancedSearchResult],
        graph_results: list[EnhancedSearchResult],
        query_weights: QueryWeights | None = None,
    ) -> list[EnhancedSearchResult]:
        """Fuse results using reciprocal rank fusion (RRF)."""
        # Create rank mappings for each result type
        vector_ranks = {
            self._get_result_key(r): i + 1 for i, r in enumerate(vector_results)
        }
        keyword_ranks = {
            self._get_result_key(r): i + 1 for i, r in enumerate(keyword_results)
        }
        graph_ranks = {
            self._get_result_key(r): i + 1 for i, r in enumerate(graph_results)
        }

        # Collect all unique results
        all_results = {}
        for results in [vector_results, keyword_results, graph_results]:
            for result in results:
                key = self._get_result_key(result)
                if key not in all_results:
                    all_results[key] = result

        # Get effective weights (query-time overrides or config defaults)
        if query_weights and query_weights.has_weights():
            vector_weight, keyword_weight, graph_weight = (
                query_weights.get_effective_weights(self.config)
            )
        else:
            vector_weight, keyword_weight, graph_weight = (
                self.config.vector_weight,
                self.config.keyword_weight,
                self.config.graph_weight,
            )

        # Calculate RRF scores
        k = 60  # RRF constant
        for key, result in all_results.items():
            rrf_score = 0.0

            if key in vector_ranks:
                rrf_score += vector_weight / (k + vector_ranks[key])
            if key in keyword_ranks:
                rrf_score += keyword_weight / (k + keyword_ranks[key])
            if key in graph_ranks:
                rrf_score += graph_weight / (k + graph_ranks[key])

            # Ensure minimum positive score
            result.combined_score = max(rrf_score, 0.001)

        # Filter by minimum score threshold
        filtered_results = [
            result
            for result in all_results.values()
            if result.combined_score >= self.config.min_combined_score
        ]

        # Sort by RRF score and return top results
        filtered_results.sort(key=lambda x: x.combined_score, reverse=True)
        return filtered_results[: self.config.final_limit]

    def _mmr_fusion(
        self,
        vector_results: list[EnhancedSearchResult],
        keyword_results: list[EnhancedSearchResult],
        graph_results: list[EnhancedSearchResult],
        lambda_param: float = 0.7,
        query_weights: QueryWeights | None = None,
    ) -> list[EnhancedSearchResult]:
        """Fuse results using Maximal Marginal Relevance (MMR).

        MMR balances relevance and diversity by selecting results that are
        relevant to the query but dissimilar to already selected results.

        Args:
            vector_results: Results from vector search
            keyword_results: Results from keyword search
            graph_results: Results from graph search
            lambda_param: Trade-off parameter between relevance and diversity (0-1)
                         1.0 = pure relevance, 0.0 = pure diversity

        Returns:
            Diversified and relevant results
        """
        try:
            # Combine all results and calculate initial relevance scores
            all_results = self._combine_and_score_results(
                vector_results, keyword_results, graph_results, query_weights
            )

            if not all_results:
                return []

            # Sort by relevance score initially
            all_results.sort(key=lambda x: x.combined_score, reverse=True)

            # MMR selection algorithm
            selected_results = []
            remaining_results = all_results.copy()

            # Select the most relevant result first
            if remaining_results:
                best_result = remaining_results.pop(0)
                selected_results.append(best_result)

            # Iteratively select results that maximize MMR score
            while remaining_results and len(selected_results) < self.config.final_limit:
                best_mmr_score = -float("inf")
                best_result_idx = 0

                for i, candidate in enumerate(remaining_results):
                    # Calculate relevance score (normalized)
                    relevance_score = candidate.combined_score

                    # Calculate maximum similarity to already selected results
                    max_similarity = 0.0
                    if selected_results:
                        similarities = [
                            self._calculate_content_similarity(candidate, selected)
                            for selected in selected_results
                        ]
                        max_similarity = max(similarities)

                    # Calculate MMR score
                    mmr_score = (
                        lambda_param * relevance_score
                        - (1 - lambda_param) * max_similarity
                    )

                    if mmr_score > best_mmr_score:
                        best_mmr_score = mmr_score
                        best_result_idx = i

                # Select the best MMR result
                selected_result = remaining_results.pop(best_result_idx)
                selected_result.combined_score = best_mmr_score
                selected_results.append(selected_result)

            return selected_results

        except Exception as e:
            self.logger.warning(f"MMR fusion failed: {e}")
            # Fallback to weighted sum
            return self._weighted_sum_fusion(
                vector_results, keyword_results, graph_results, query_weights
            )

    def _graph_enhanced_weighted_fusion(
        self,
        vector_results: list[EnhancedSearchResult],
        keyword_results: list[EnhancedSearchResult],
        graph_results: list[EnhancedSearchResult],
        query_weights: QueryWeights | None = None,
    ) -> list[EnhancedSearchResult]:
        """Enhanced weighted fusion that leverages graph centrality and temporal factors.

        This fusion strategy applies sophisticated graph-based boosting to improve
        the integration of vector similarity and graph relationship scores.
        """
        try:
            # Start with basic weighted sum fusion
            result_map = {}

            # Get effective weights
            if query_weights and query_weights.has_weights():
                vector_weight, keyword_weight, graph_weight = (
                    query_weights.get_effective_weights(self.config)
                )
            else:
                vector_weight, keyword_weight, graph_weight = (
                    self.config.vector_weight,
                    self.config.keyword_weight,
                    self.config.graph_weight,
                )

            # Process and combine all results
            for results, weight, score_field in [
                (vector_results, vector_weight, "vector_score"),
                (keyword_results, keyword_weight, "keyword_score"),
                (graph_results, graph_weight, "graph_score"),
            ]:
                for result in results:
                    key = self._get_result_key(result)
                    if key not in result_map:
                        result_map[key] = result
                        result_map[key].combined_score = weight * getattr(
                            result, score_field
                        )
                    else:
                        # Merge results and update scores
                        existing = result_map[key]
                        setattr(
                            existing,
                            score_field,
                            max(
                                getattr(existing, score_field),
                                getattr(result, score_field),
                            ),
                        )
                        existing.combined_score += weight * getattr(result, score_field)

                        # Merge graph-specific information
                        if hasattr(result, "entity_ids") and result.entity_ids:
                            existing.entity_ids.extend(result.entity_ids)
                        if (
                            hasattr(result, "relationship_types")
                            and result.relationship_types
                        ):
                            existing.relationship_types.extend(
                                result.relationship_types
                            )
                        if hasattr(result, "centrality_score"):
                            existing.centrality_score = max(
                                existing.centrality_score, result.centrality_score
                            )

            # Apply graph-enhanced scoring
            for result in result_map.values():
                # Graph centrality boost (exponential scaling for high centrality)
                if result.centrality_score > 0:
                    centrality_boost = 1.0 + (result.centrality_score**1.5) * 0.3
                    result.combined_score *= centrality_boost
                    result.debug_info["centrality_boost"] = centrality_boost

                # Temporal relevance boost (recent content gets higher boost)
                if result.temporal_relevance > 0:
                    temporal_boost = 1.0 + (result.temporal_relevance**0.8) * 0.2
                    result.combined_score *= temporal_boost
                    result.debug_info["temporal_boost"] = temporal_boost

                # Entity connectivity boost (more connected entities = higher relevance)
                if result.entity_ids:
                    unique_entities = len(set(result.entity_ids))
                    connectivity_boost = 1.0 + min(0.25, unique_entities * 0.03)
                    result.combined_score *= connectivity_boost
                    result.debug_info["connectivity_boost"] = connectivity_boost

                # Relationship diversity boost
                if result.relationship_types:
                    unique_relationships = len(set(result.relationship_types))
                    diversity_boost = 1.0 + min(0.2, unique_relationships * 0.04)
                    result.combined_score *= diversity_boost
                    result.debug_info["diversity_boost"] = diversity_boost

            # Filter and sort results
            filtered_results = [
                result
                for result in result_map.values()
                if result.combined_score >= self.config.min_combined_score
            ]

            filtered_results.sort(key=lambda x: x.combined_score, reverse=True)
            return filtered_results[: self.config.final_limit]

        except Exception as e:
            self.logger.warning(f"Graph enhanced weighted fusion failed: {e}")
            return self._weighted_sum_fusion(
                vector_results, keyword_results, graph_results, query_weights
            )

    def _confidence_adaptive_fusion(
        self,
        vector_results: list[EnhancedSearchResult],
        keyword_results: list[EnhancedSearchResult],
        graph_results: list[EnhancedSearchResult],
        query_weights: QueryWeights | None = None,
    ) -> list[EnhancedSearchResult]:
        """Adaptive fusion that adjusts weights based on result confidence scores.

        This strategy dynamically adjusts the fusion weights based on the confidence
        and quality of results from each search modality.
        """
        try:
            # Calculate confidence scores for each result type
            vector_confidence = self._calculate_result_confidence(
                vector_results, "vector"
            )
            keyword_confidence = self._calculate_result_confidence(
                keyword_results, "keyword"
            )
            graph_confidence = self._calculate_result_confidence(graph_results, "graph")

            # Get base weights
            if query_weights and query_weights.has_weights():
                base_vector_weight, base_keyword_weight, base_graph_weight = (
                    query_weights.get_effective_weights(self.config)
                )
            else:
                base_vector_weight, base_keyword_weight, base_graph_weight = (
                    self.config.vector_weight,
                    self.config.keyword_weight,
                    self.config.graph_weight,
                )

            # Adjust weights based on confidence
            total_confidence = vector_confidence + keyword_confidence + graph_confidence
            if total_confidence > 0:
                confidence_factor = 0.3  # How much confidence affects weighting

                vector_weight = base_vector_weight * (
                    1
                    + confidence_factor * (vector_confidence / total_confidence - 1 / 3)
                )
                keyword_weight = base_keyword_weight * (
                    1
                    + confidence_factor
                    * (keyword_confidence / total_confidence - 1 / 3)
                )
                graph_weight = base_graph_weight * (
                    1
                    + confidence_factor * (graph_confidence / total_confidence - 1 / 3)
                )

                # Normalize weights to sum to 1.0
                total_weight = vector_weight + keyword_weight + graph_weight
                if total_weight > 0:
                    vector_weight /= total_weight
                    keyword_weight /= total_weight
                    graph_weight /= total_weight
            else:
                vector_weight, keyword_weight, graph_weight = (
                    base_vector_weight,
                    base_keyword_weight,
                    base_graph_weight,
                )

            # Create adjusted query weights
            adjusted_weights = QueryWeights(
                vector_weight=vector_weight,
                keyword_weight=keyword_weight,
                graph_weight=graph_weight,
            )

            # Use graph enhanced weighted fusion with adjusted weights
            results = self._graph_enhanced_weighted_fusion(
                vector_results, keyword_results, graph_results, adjusted_weights
            )

            # Add confidence information to debug info
            for result in results:
                result.debug_info.update(
                    {
                        "vector_confidence": vector_confidence,
                        "keyword_confidence": keyword_confidence,
                        "graph_confidence": graph_confidence,
                        "adjusted_vector_weight": vector_weight,
                        "adjusted_keyword_weight": keyword_weight,
                        "adjusted_graph_weight": graph_weight,
                    }
                )

            return results

        except Exception as e:
            self.logger.warning(f"Confidence adaptive fusion failed: {e}")
            return self._graph_enhanced_weighted_fusion(
                vector_results, keyword_results, graph_results, query_weights
            )

    def _multi_stage_fusion(
        self,
        vector_results: list[EnhancedSearchResult],
        keyword_results: list[EnhancedSearchResult],
        graph_results: list[EnhancedSearchResult],
        query_weights: QueryWeights | None = None,
    ) -> list[EnhancedSearchResult]:
        """Multi-stage fusion with preliminary filtering and progressive refinement.

        This strategy applies fusion in multiple stages:
        1. Initial filtering based on individual scores
        2. Primary fusion with basic weighting
        3. Refinement with graph enhancement
        4. Final reranking with confidence adjustment
        """
        try:
            # Stage 1: Initial filtering - remove low-quality results
            filtered_vector = [
                r
                for r in vector_results
                if r.vector_score >= self.config.min_vector_score
            ]
            filtered_keyword = [
                r for r in keyword_results if r.keyword_score >= 0.1
            ]  # Lower threshold for keyword
            filtered_graph = [
                r for r in graph_results if r.graph_score >= self.config.min_graph_score
            ]

            self.logger.debug(
                f"Stage 1 filtering: vector {len(vector_results)}->{len(filtered_vector)}, "
                f"keyword {len(keyword_results)}->{len(filtered_keyword)}, "
                f"graph {len(graph_results)}->{len(filtered_graph)}"
            )

            # Stage 2: Primary fusion with weighted sum
            stage2_results = self._weighted_sum_fusion(
                filtered_vector, filtered_keyword, filtered_graph, query_weights
            )

            # Stage 3: Graph enhancement for top candidates
            top_k = min(
                self.config.final_limit * 2, len(stage2_results)
            )  # Process 2x final limit
            stage3_candidates = stage2_results[:top_k]

            # Apply graph enhancement to top candidates
            for result in stage3_candidates:
                enhancement_factor = 1.0

                # Enhanced centrality scoring
                if result.centrality_score > 0:
                    enhancement_factor += result.centrality_score * 0.4

                # Enhanced temporal scoring
                if result.temporal_relevance > 0:
                    enhancement_factor += result.temporal_relevance * 0.3

                # Multi-modal presence bonus (appears in multiple search types)
                modality_count = sum(
                    [
                        1 if result.vector_score > 0 else 0,
                        1 if result.keyword_score > 0 else 0,
                        1 if result.graph_score > 0 else 0,
                    ]
                )
                if modality_count > 1:
                    enhancement_factor += (modality_count - 1) * 0.15

                result.combined_score *= enhancement_factor
                result.debug_info["stage3_enhancement"] = enhancement_factor

            # Stage 4: Final confidence-based reranking
            stage4_results = sorted(
                stage3_candidates, key=lambda x: x.combined_score, reverse=True
            )

            # Apply final confidence adjustment
            for i, result in enumerate(stage4_results):
                # Position-based confidence (earlier results get slight boost)
                position_factor = 1.0 + (
                    0.1 * (len(stage4_results) - i) / len(stage4_results)
                )
                result.combined_score *= position_factor
                result.debug_info["position_factor"] = position_factor

            # Final sort and limit
            final_results = sorted(
                stage4_results, key=lambda x: x.combined_score, reverse=True
            )
            return final_results[: self.config.final_limit]

        except Exception as e:
            self.logger.warning(f"Multi-stage fusion failed: {e}")
            return self._confidence_adaptive_fusion(
                vector_results, keyword_results, graph_results, query_weights
            )

    def _context_aware_fusion(
        self,
        vector_results: list[EnhancedSearchResult],
        keyword_results: list[EnhancedSearchResult],
        graph_results: list[EnhancedSearchResult],
        query_weights: QueryWeights | None = None,
    ) -> list[EnhancedSearchResult]:
        """Context-aware fusion that adapts based on query characteristics and result patterns.

        This strategy analyzes the query and result characteristics to select
        the most appropriate fusion approach dynamically.
        """
        try:
            # Analyze result characteristics
            total_results = (
                len(vector_results) + len(keyword_results) + len(graph_results)
            )
            vector_ratio = (
                len(vector_results) / total_results if total_results > 0 else 0
            )
            keyword_ratio = (
                len(keyword_results) / total_results if total_results > 0 else 0
            )
            graph_ratio = len(graph_results) / total_results if total_results > 0 else 0

            # Calculate average scores for each modality
            avg_vector_score = (
                sum(r.vector_score for r in vector_results) / len(vector_results)
                if vector_results
                else 0
            )
            avg_keyword_score = (
                sum(r.keyword_score for r in keyword_results) / len(keyword_results)
                if keyword_results
                else 0
            )
            avg_graph_score = (
                sum(r.graph_score for r in graph_results) / len(graph_results)
                if graph_results
                else 0
            )

            # Determine context-based strategy
            if graph_ratio > 0.4 and avg_graph_score > 0.6:
                # High-quality graph results available - use graph-enhanced fusion
                self.logger.debug(
                    "Context-aware: Using graph-enhanced fusion (high graph quality)"
                )
                return self._graph_enhanced_weighted_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )

            elif vector_ratio > 0.6 and avg_vector_score > 0.7:
                # Strong vector results - use confidence adaptive
                self.logger.debug(
                    "Context-aware: Using confidence adaptive fusion (strong vector results)"
                )
                return self._confidence_adaptive_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )

            elif total_results > 20:
                # Many results available - use multi-stage for refinement
                self.logger.debug(
                    "Context-aware: Using multi-stage fusion (many results)"
                )
                return self._multi_stage_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )

            elif keyword_ratio > 0.5:
                # Keyword-heavy results - use MMR for diversity
                self.logger.debug("Context-aware: Using MMR fusion (keyword-heavy)")
                return self._mmr_fusion(
                    vector_results,
                    keyword_results,
                    graph_results,
                    query_weights=query_weights,
                )

            else:
                # Balanced or uncertain - use RRF as safe default
                self.logger.debug("Context-aware: Using RRF fusion (balanced/default)")
                return self._reciprocal_rank_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )

        except Exception as e:
            self.logger.warning(f"Context-aware fusion failed: {e}")
            return self._multi_stage_fusion(
                vector_results, keyword_results, graph_results, query_weights
            )

    def _calculate_result_confidence(
        self, results: list[EnhancedSearchResult], result_type: str
    ) -> float:
        """Calculate confidence score for a set of results.

        Args:
            results: List of search results
            result_type: Type of results ("vector", "keyword", or "graph")

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not results:
            return 0.0

        try:
            # Get relevant scores based on result type
            if result_type == "vector":
                scores = [r.vector_score for r in results]
            elif result_type == "keyword":
                scores = [r.keyword_score for r in results]
            elif result_type == "graph":
                scores = [r.graph_score for r in results]
            else:
                scores = [r.combined_score for r in results]

            if not scores:
                return 0.0

            # Calculate confidence metrics
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            score_variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
            score_std = score_variance**0.5

            # Confidence factors
            quality_factor = min(
                1.0, avg_score * 2
            )  # Higher average = higher confidence
            consistency_factor = max(
                0.0, 1.0 - score_std
            )  # Lower variance = higher confidence
            peak_factor = min(
                1.0, max_score * 1.5
            )  # High peak score = higher confidence
            volume_factor = min(
                1.0, len(results) / 10
            )  # More results = higher confidence (up to 10)

            # Weighted combination
            confidence = (
                0.4 * quality_factor
                + 0.2 * consistency_factor
                + 0.3 * peak_factor
                + 0.1 * volume_factor
            )

            return min(1.0, max(0.0, confidence))

        except Exception as e:
            self.logger.warning(f"Error calculating confidence for {result_type}: {e}")
            return 0.5  # Neutral confidence on error

    def _combine_and_score_results(
        self,
        vector_results: list[EnhancedSearchResult],
        keyword_results: list[EnhancedSearchResult],
        graph_results: list[EnhancedSearchResult],
        query_weights: QueryWeights | None = None,
    ) -> list[EnhancedSearchResult]:
        """Combine results from all sources and calculate initial relevance scores."""
        # Get effective weights (query-time overrides or config defaults)
        if query_weights and query_weights.has_weights():
            vector_weight, keyword_weight, graph_weight = (
                query_weights.get_effective_weights(self.config)
            )
        else:
            vector_weight, keyword_weight, graph_weight = (
                self.config.vector_weight,
                self.config.keyword_weight,
                self.config.graph_weight,
            )

        result_map = {}

        # Process vector results
        for result in vector_results:
            key = self._get_result_key(result)
            if key not in result_map:
                result_map[key] = result
                result_map[key].combined_score = vector_weight * result.vector_score
            else:
                result_map[key].vector_score = max(
                    result_map[key].vector_score, result.vector_score
                )
                result_map[key].combined_score += vector_weight * result.vector_score

        # Process keyword results
        for result in keyword_results:
            key = self._get_result_key(result)
            if key not in result_map:
                result_map[key] = result
                result_map[key].combined_score = keyword_weight * result.keyword_score
            else:
                result_map[key].keyword_score = max(
                    result_map[key].keyword_score, result.keyword_score
                )
                result_map[key].combined_score += keyword_weight * result.keyword_score

        # Process graph results
        for result in graph_results:
            key = self._get_result_key(result)
            if key not in result_map:
                result_map[key] = result
                result_map[key].combined_score = graph_weight * result.graph_score
            else:
                result_map[key].graph_score = max(
                    result_map[key].graph_score, result.graph_score
                )
                result_map[key].combined_score += graph_weight * result.graph_score
                # Merge graph-specific metadata
                result_map[key].entity_ids.extend(result.entity_ids)
                result_map[key].relationship_types.extend(result.relationship_types)
                result_map[key].centrality_score = max(
                    result_map[key].centrality_score, result.centrality_score
                )

        # Filter by minimum score threshold
        filtered_results = [
            result
            for result in result_map.values()
            if result.combined_score >= self.config.min_combined_score
        ]

        return filtered_results

    def _calculate_content_similarity(
        self, result1: EnhancedSearchResult, result2: EnhancedSearchResult
    ) -> float:
        """Calculate similarity between two search results.

        Uses a combination of content similarity and metadata overlap.

        Args:
            result1: First search result
            result2: Second search result

        Returns:
            Similarity score between 0.0 and 1.0
        """
        try:
            # Content similarity using simple token overlap (Jaccard similarity)
            content1_tokens = set(result1.content.lower().split())
            content2_tokens = set(result2.content.lower().split())

            if not content1_tokens and not content2_tokens:
                content_similarity = 1.0
            elif not content1_tokens or not content2_tokens:
                content_similarity = 0.0
            else:
                intersection = len(content1_tokens.intersection(content2_tokens))
                union = len(content1_tokens.union(content2_tokens))
                content_similarity = intersection / union if union > 0 else 0.0

            # Title similarity
            title1_tokens = set(result1.title.lower().split())
            title2_tokens = set(result2.title.lower().split())

            if not title1_tokens and not title2_tokens:
                title_similarity = 1.0
            elif not title1_tokens or not title2_tokens:
                title_similarity = 0.0
            else:
                intersection = len(title1_tokens.intersection(title2_tokens))
                union = len(title1_tokens.union(title2_tokens))
                title_similarity = intersection / union if union > 0 else 0.0

            # Source type similarity
            source_similarity = (
                1.0 if result1.source_type == result2.source_type else 0.0
            )

            # Entity overlap similarity (for graph results)
            entity1_set = set(result1.entity_ids)
            entity2_set = set(result2.entity_ids)

            if not entity1_set and not entity2_set:
                entity_similarity = 0.0  # No entities to compare
            elif not entity1_set or not entity2_set:
                entity_similarity = 0.0
            else:
                intersection = len(entity1_set.intersection(entity2_set))
                union = len(entity1_set.union(entity2_set))
                entity_similarity = intersection / union if union > 0 else 0.0

            # Weighted combination of similarities
            overall_similarity = (
                0.5 * content_similarity
                + 0.2 * title_similarity
                + 0.1 * source_similarity
                + 0.2 * entity_similarity
            )

            return min(1.0, max(0.0, overall_similarity))

        except Exception as e:
            self.logger.warning(f"Error calculating content similarity: {e}")
            return 0.0

    def _get_result_key(self, result: EnhancedSearchResult) -> str:
        """Generate a key for result deduplication."""
        # Use content hash for deduplication
        content_hash = hashlib.md5(result.content.encode()).hexdigest()
        return f"{result.source_type}_{content_hash}"


class CacheManager:
    """Advanced cache manager for search results with invalidation strategies."""

    def __init__(
        self, ttl: int = 300, max_size: int = 1000, cleanup_interval: int = 60
    ):
        """Initialize cache manager.

        Args:
            ttl: Time to live in seconds
            max_size: Maximum number of cached entries
            cleanup_interval: Interval for automatic cleanup in seconds
        """
        self.ttl = ttl
        self.max_size = max_size
        self.cleanup_interval = cleanup_interval
        self.cache: dict[str, dict[str, Any]] = {}
        self.access_times: dict[str, float] = {}  # For LRU eviction
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "cleanups": 0,
            "total_requests": 0,
        }
        self.last_cleanup = time.time()
        self.logger = LoggingConfig.get_logger(__name__)

    def get(
        self,
        query: str,
        config: EnhancedSearchConfig,
        query_weights: QueryWeights | None = None,
    ) -> list[EnhancedSearchResult] | None:
        """Get cached results for query.

        Args:
            query: Search query
            config: Search configuration
            query_weights: Optional query-time weight overrides

        Returns:
            Cached results if available and not expired
        """
        self.stats["total_requests"] += 1

        # Perform periodic cleanup
        self._maybe_cleanup()

        cache_key = self._get_cache_key(query, config, query_weights)

        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            current_time = time.time()

            if current_time - cached_data["timestamp"] < self.ttl:
                # Update access time for LRU
                self.access_times[cache_key] = current_time
                self.stats["hits"] += 1
                self.logger.debug(f"Cache hit for query: {query}")
                return cached_data["results"]
            else:
                # Remove expired entry
                self._remove_cache_entry(cache_key)

        self.stats["misses"] += 1
        return None

    def set(
        self,
        query: str,
        config: EnhancedSearchConfig,
        results: list[EnhancedSearchResult],
        query_weights: QueryWeights | None = None,
    ) -> None:
        """Cache search results.

        Args:
            query: Search query
            config: Search configuration
            results: Search results to cache
            query_weights: Optional query-time weight overrides
        """
        # Check if we need to evict entries to make room
        if len(self.cache) >= self.max_size:
            self._evict_lru_entries()

        cache_key = self._get_cache_key(query, config, query_weights)
        current_time = time.time()

        self.cache[cache_key] = {"results": results, "timestamp": current_time}
        self.access_times[cache_key] = current_time
        self.logger.debug(f"Cached results for query: {query}")

    def _get_cache_key(
        self,
        query: str,
        config: EnhancedSearchConfig,
        query_weights: QueryWeights | None = None,
    ) -> str:
        """Generate cache key for query and config."""
        # Use query weights if provided, otherwise use config defaults
        if query_weights and query_weights.has_weights():
            vector_weight, keyword_weight, graph_weight = (
                query_weights.get_effective_weights(config)
            )
        else:
            vector_weight = config.vector_weight
            keyword_weight = config.keyword_weight
            graph_weight = config.graph_weight

        config_str = json.dumps(
            {
                "mode": config.mode.value,
                "vector_weight": vector_weight,
                "keyword_weight": keyword_weight,
                "graph_weight": graph_weight,
                "fusion_strategy": config.fusion_strategy.value,
            },
            sort_keys=True,
        )

        combined = f"{query}_{config_str}"
        return hashlib.md5(combined.encode()).hexdigest()

    def clear(self) -> None:
        """Clear all cached results."""
        self.cache.clear()
        self.access_times.clear()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "cleanups": 0,
            "total_requests": 0,
        }
        self.logger.debug("Cache cleared")

    def _maybe_cleanup(self) -> None:
        """Perform cleanup if enough time has passed."""
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_expired()
            self.last_cleanup = current_time

    def _cleanup_expired(self) -> None:
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = []

        for cache_key, cached_data in self.cache.items():
            if current_time - cached_data["timestamp"] > self.ttl:
                expired_keys.append(cache_key)

        for key in expired_keys:
            self._remove_cache_entry(key)

        if expired_keys:
            self.stats["cleanups"] += 1
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    def _remove_cache_entry(self, cache_key: str) -> None:
        """Remove a cache entry and its access time."""
        if cache_key in self.cache:
            del self.cache[cache_key]
        if cache_key in self.access_times:
            del self.access_times[cache_key]

    def _evict_lru_entries(self) -> None:
        """Evict least recently used entries to make room."""
        if not self.access_times:
            return

        # Calculate how many entries to evict (25% of max_size)
        evict_count = max(1, self.max_size // 4)

        # Sort by access time and get the oldest entries
        sorted_entries = sorted(self.access_times.items(), key=lambda x: x[1])
        entries_to_evict = sorted_entries[:evict_count]

        for cache_key, _ in entries_to_evict:
            self._remove_cache_entry(cache_key)

        self.stats["evictions"] += len(entries_to_evict)
        self.logger.debug(f"Evicted {len(entries_to_evict)} LRU cache entries")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        hit_rate = (
            self.stats["hits"] / self.stats["total_requests"]
            if self.stats["total_requests"] > 0
            else 0.0
        )

        return {
            "cache_size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": hit_rate,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "evictions": self.stats["evictions"],
            "cleanups": self.stats["cleanups"],
            "total_requests": self.stats["total_requests"],
            "ttl": self.ttl,
            "cleanup_interval": self.cleanup_interval,
        }

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching a pattern.

        Args:
            pattern: Pattern to match against cache keys

        Returns:
            Number of entries invalidated
        """
        import re

        try:
            regex = re.compile(pattern)
            keys_to_remove = []

            for cache_key in self.cache.keys():
                if regex.search(cache_key):
                    keys_to_remove.append(cache_key)

            for key in keys_to_remove:
                self._remove_cache_entry(key)

            if keys_to_remove:
                self.logger.debug(
                    f"Invalidated {len(keys_to_remove)} cache entries matching pattern: {pattern}"
                )

            return len(keys_to_remove)

        except re.error as e:
            self.logger.error(f"Invalid regex pattern '{pattern}': {e}")
            return 0


class RerankingEngine:
    """Advanced reranking engine with multiple strategies."""

    def __init__(
        self, config: EnhancedSearchConfig, openai_client: AsyncOpenAI | None = None
    ):
        """Initialize reranking engine.

        Args:
            config: Enhanced search configuration
            openai_client: OpenAI client for cross-encoder reranking
        """
        self.config = config
        self.openai_client = openai_client
        self.logger = logger

        # Initialize BGE reranker if needed
        self._bge_reranker = None
        if config.cross_encoder_model == "bge":
            self._initialize_bge_reranker()

    def _initialize_bge_reranker(self):
        """Initialize BGE reranker model."""
        try:
            from sentence_transformers import CrossEncoder

            self._bge_reranker = CrossEncoder("BAAI/bge-reranker-v2-m3")
            self.logger.info("BGE reranker initialized successfully")
        except ImportError:
            self.logger.warning(
                "sentence_transformers not available, falling back to OpenAI reranker"
            )
            self.config.cross_encoder_model = "openai"
        except Exception as e:
            self.logger.error(f"Failed to initialize BGE reranker: {e}")
            self.config.cross_encoder_model = "openai"

    async def rerank_results(
        self,
        query: str,
        results: list[EnhancedSearchResult],
        user_context: dict[str, Any] | None = None,
    ) -> list[EnhancedSearchResult]:
        """Apply reranking strategy to search results.

        Args:
            query: Original search query
            results: Search results to rerank
            user_context: Optional user context for contextual reranking

        Returns:
            Reranked search results
        """
        if not results or self.config.reranking_strategy == RerankingStrategy.NONE:
            return results

        # Limit to top-k for reranking efficiency
        top_results = results[: self.config.rerank_top_k]

        try:
            if self.config.reranking_strategy == RerankingStrategy.CROSS_ENCODER:
                return await self._cross_encoder_rerank(query, top_results)
            elif self.config.reranking_strategy == RerankingStrategy.DIVERSITY_MMR:
                return self._diversity_rerank(query, top_results)
            elif self.config.reranking_strategy == RerankingStrategy.TEMPORAL_BOOST:
                return self._temporal_rerank(top_results)
            elif self.config.reranking_strategy == RerankingStrategy.CONTEXTUAL_BOOST:
                return self._contextual_rerank(query, top_results, user_context)
            elif self.config.reranking_strategy == RerankingStrategy.COMBINED:
                return await self._combined_rerank(query, top_results, user_context)
            else:
                return top_results

        except Exception as e:
            self.logger.error(f"Reranking failed: {e}")
            return results

    async def _cross_encoder_rerank(
        self, query: str, results: list[EnhancedSearchResult]
    ) -> list[EnhancedSearchResult]:
        """Rerank using cross-encoder models."""
        if self.config.cross_encoder_model == "openai" and self.openai_client:
            return await self._openai_cross_encoder_rerank(query, results)
        elif self.config.cross_encoder_model == "bge" and self._bge_reranker:
            return self._bge_cross_encoder_rerank(query, results)
        else:
            self.logger.warning("Cross-encoder model not available, skipping reranking")
            return results

    async def _openai_cross_encoder_rerank(
        self, query: str, results: list[EnhancedSearchResult]
    ) -> list[EnhancedSearchResult]:
        """Rerank using OpenAI model for relevance classification."""
        try:
            # Prepare batch for OpenAI classification
            reranked_results = []

            for result in results:
                # Create relevance classification prompt
                prompt = f"""
                Query: {query}
                
                Document: {result.content[:1000]}...
                
                Rate the relevance of this document to the query on a scale of 0.0 to 1.0.
                Consider semantic similarity, topical relevance, and information completeness.
                Respond with only a number between 0.0 and 1.0.
                """

                try:
                    if not self.openai_client:
                        result.rerank_score = result.combined_score
                        reranked_results.append(result)
                        continue

                    response = await self.openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=10,
                        temperature=0.0,
                        logprobs=True,
                        top_logprobs=5,
                    )

                    # Extract relevance score from response
                    content = response.choices[0].message.content
                    if content is None:
                        result.rerank_score = result.combined_score
                        reranked_results.append(result)
                        continue

                    relevance_score = float(content.strip())
                    relevance_score = max(
                        0.0, min(1.0, relevance_score)
                    )  # Clamp to [0,1]

                    # Update result with cross-encoder score
                    result.rerank_score = relevance_score
                    result.combined_score = (
                        result.combined_score + relevance_score
                    ) / 2

                    reranked_results.append(result)

                except Exception as e:
                    self.logger.warning(
                        f"OpenAI reranking failed for result {result.id}: {e}"
                    )
                    result.rerank_score = result.combined_score
                    reranked_results.append(result)

            # Sort by updated combined score
            reranked_results.sort(key=lambda x: x.combined_score, reverse=True)
            return reranked_results

        except Exception as e:
            self.logger.error(f"OpenAI cross-encoder reranking failed: {e}")
            return results

    def _bge_cross_encoder_rerank(
        self, query: str, results: list[EnhancedSearchResult]
    ) -> list[EnhancedSearchResult]:
        """Rerank using BGE cross-encoder model."""
        try:
            if not self._bge_reranker:
                self.logger.warning("BGE reranker not available, skipping reranking")
                return results

            # Prepare query-document pairs
            pairs = [(query, result.content[:512]) for result in results]

            # Get relevance scores from BGE model
            scores = self._bge_reranker.predict(pairs)

            # Update results with cross-encoder scores
            for result, score in zip(results, scores, strict=False):
                result.rerank_score = float(score)
                result.combined_score = (result.combined_score + score) / 2

            # Sort by updated combined score
            results.sort(key=lambda x: x.combined_score, reverse=True)
            return results

        except Exception as e:
            self.logger.error(f"BGE cross-encoder reranking failed: {e}")
            return results

    def _diversity_rerank(
        self, query: str, results: list[EnhancedSearchResult]
    ) -> list[EnhancedSearchResult]:
        """Apply diversity-based reranking using MMR approach."""
        if len(results) <= 1:
            return results

        try:
            selected_results = []
            remaining_results = results.copy()

            # Select first result (highest relevance)
            if remaining_results:
                selected_results.append(remaining_results.pop(0))

            # Iteratively select diverse results
            while remaining_results and len(selected_results) < len(results):
                best_result = None
                best_score = -1
                best_idx = -1

                for idx, candidate in enumerate(remaining_results):
                    # Calculate relevance score
                    relevance_score = candidate.combined_score

                    # Calculate maximum similarity to already selected results
                    max_similarity = 0.0
                    for selected in selected_results:
                        similarity = self._calculate_content_similarity(
                            candidate, selected
                        )
                        max_similarity = max(max_similarity, similarity)

                    # MMR score: balance relevance and diversity
                    mmr_score = (
                        self.config.diversity_lambda * relevance_score
                        - (1 - self.config.diversity_lambda) * max_similarity
                    )

                    if mmr_score > best_score:
                        best_score = mmr_score
                        best_result = candidate
                        best_idx = idx

                if best_result:
                    selected_results.append(remaining_results.pop(best_idx))
                    best_result.rerank_score = best_score
                else:
                    break

            return selected_results

        except Exception as e:
            self.logger.error(f"Diversity reranking failed: {e}")
            return results

    def _temporal_rerank(
        self, results: list[EnhancedSearchResult]
    ) -> list[EnhancedSearchResult]:
        """Apply temporal relevance boosting."""
        try:
            from datetime import datetime, timedelta

            current_time = datetime.now()
            recent_threshold = current_time - timedelta(
                days=self.config.temporal_recent_threshold_days
            )

            for result in results:
                # Extract temporal information from metadata
                created_at = result.metadata.get("created_at")
                updated_at = result.metadata.get("updated_at")

                # Use the most recent timestamp available
                timestamp = None
                if updated_at:
                    timestamp = self._parse_timestamp(updated_at)
                elif created_at:
                    timestamp = self._parse_timestamp(created_at)

                if timestamp:
                    # Calculate temporal boost
                    if timestamp > recent_threshold:
                        # Recent content gets a boost
                        temporal_boost = self.config.temporal_boost_recent
                    else:
                        # Older content gets decay based on age
                        days_old = (current_time - timestamp).days
                        temporal_boost = max(
                            0.1,
                            1.0 - (days_old * self.config.temporal_decay_factor / 365),
                        )

                    # Apply temporal boost
                    result.temporal_relevance = temporal_boost
                    result.combined_score *= temporal_boost
                    result.rerank_score = result.combined_score

            # Sort by updated scores
            results.sort(key=lambda x: x.combined_score, reverse=True)
            return results

        except Exception as e:
            self.logger.error(f"Temporal reranking failed: {e}")
            return results

    def _contextual_rerank(
        self,
        query: str,
        results: list[EnhancedSearchResult],
        user_context: dict[str, Any] | None = None,
    ) -> list[EnhancedSearchResult]:
        """Apply contextual boosting based on user context and query context."""
        try:
            for result in results:
                context_boost = 1.0

                if user_context:
                    # Apply user preference boosting
                    user_preferences = user_context.get("preferences", {})
                    preferred_sources = user_preferences.get("source_types", [])

                    if preferred_sources and result.source_type in preferred_sources:
                        context_boost *= self.config.context_boost_factor

                    # Apply project context boosting
                    preferred_projects = user_context.get("recent_projects", [])
                    if (
                        preferred_projects
                        and result.metadata.get("project_id") in preferred_projects
                    ):
                        context_boost *= self.config.context_boost_factor

                # Apply query context boosting
                if self.config.enable_query_context:
                    # Boost results that match query intent patterns
                    query_lower = query.lower()
                    content_lower = result.content.lower()

                    # Simple heuristics for query intent
                    if any(
                        word in query_lower
                        for word in ["how", "tutorial", "guide", "example"]
                    ):
                        if any(
                            word in content_lower
                            for word in ["example", "tutorial", "guide", "how to"]
                        ):
                            context_boost *= 1.1

                    if any(
                        word in query_lower
                        for word in ["error", "bug", "issue", "problem"]
                    ):
                        if any(
                            word in content_lower
                            for word in ["error", "bug", "issue", "solution", "fix"]
                        ):
                            context_boost *= 1.1

                # Apply context boost
                result.combined_score *= context_boost
                result.rerank_score = result.combined_score

            # Sort by updated scores
            results.sort(key=lambda x: x.combined_score, reverse=True)
            return results

        except Exception as e:
            self.logger.error(f"Contextual reranking failed: {e}")
            return results

    async def _combined_rerank(
        self,
        query: str,
        results: list[EnhancedSearchResult],
        user_context: dict[str, Any] | None = None,
    ) -> list[EnhancedSearchResult]:
        """Apply combined reranking strategy using multiple approaches."""
        try:
            # Step 1: Apply cross-encoder reranking for relevance
            results = await self._cross_encoder_rerank(query, results)

            # Step 2: Apply temporal boosting
            results = self._temporal_rerank(results)

            # Step 3: Apply contextual boosting
            results = self._contextual_rerank(query, results, user_context)

            # Step 4: Apply diversity filtering as final step
            results = self._diversity_rerank(query, results)

            return results

        except Exception as e:
            self.logger.error(f"Combined reranking failed: {e}")
            return results

    def _calculate_content_similarity(
        self, result1: EnhancedSearchResult, result2: EnhancedSearchResult
    ) -> float:
        """Calculate content similarity between two results."""
        try:
            # Simple token-based similarity (can be enhanced with embeddings)
            content1 = set(result1.content.lower().split())
            content2 = set(result2.content.lower().split())

            if not content1 or not content2:
                return 0.0

            intersection = len(content1.intersection(content2))
            union = len(content1.union(content2))

            return intersection / union if union > 0 else 0.0

        except Exception:
            return 0.0

    def _parse_timestamp(self, timestamp_str: str) -> datetime | None:
        """Parse timestamp string to datetime object."""
        try:
            from datetime import datetime

            # Try common timestamp formats
            formats = [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_str, fmt)
                except ValueError:
                    continue

            return None

        except Exception:
            return None


class EnhancedHybridSearchEngine:
    """Enhanced hybrid search engine combining vector, keyword, and graph search."""

    def __init__(
        self,
        qdrant_client: QdrantClient,
        openai_client: AsyncOpenAI,
        collection_name: str,
        neo4j_manager=None,
        graphiti_manager=None,
        config: EnhancedSearchConfig | None = None,
    ):
        """Initialize enhanced hybrid search engine.

        Args:
            qdrant_client: QDrant client instance
            openai_client: OpenAI client instance
            collection_name: Name of the Qdrant collection
            neo4j_manager: Optional Neo4jManager instance
            graphiti_manager: Optional GraphitiManager instance
            config: Search configuration
        """
        self.config = config or EnhancedSearchConfig()
        self.logger = LoggingConfig.get_logger(__name__)

        # Initialize search modules
        self.vector_module = VectorSearchModule(
            qdrant_client, openai_client, collection_name
        )
        self.graph_module = GraphSearchModule(neo4j_manager, graphiti_manager)

        # Initialize existing hybrid search for keyword functionality
        self.keyword_engine = HybridSearchEngine(
            qdrant_client=qdrant_client,
            openai_client=openai_client,
            collection_name=collection_name,
        )

        # Initialize fusion engine
        self.fusion_engine = ResultFusionEngine(self.config)

        # Initialize reranking engine
        self.reranking_engine = (
            RerankingEngine(self.config, openai_client)
            if self.config.enable_reranking
            else None
        )

        # Initialize cache manager
        self.cache_manager = (
            CacheManager(
                ttl=self.config.cache_ttl,
                max_size=self.config.cache_max_size,
                cleanup_interval=self.config.cache_cleanup_interval,
            )
            if self.config.enable_caching
            else None
        )

        self.logger.info("Enhanced hybrid search engine initialized")

    async def search(
        self,
        query: str,
        mode: SearchMode | None = None,
        limit: int | None = None,
        project_ids: list[str] | None = None,
        source_types: list[str] | None = None,
        vector_weight: float | None = None,
        keyword_weight: float | None = None,
        graph_weight: float | None = None,
        **kwargs,
    ) -> list[SearchResult]:
        """Perform enhanced hybrid search.

        Args:
            query: Search query text
            mode: Search mode override
            limit: Result limit override
            project_ids: Optional project ID filter
            source_types: Optional source type filter
            vector_weight: Optional weight for vector search results (0.0-1.0)
            keyword_weight: Optional weight for keyword search results (0.0-1.0)
            graph_weight: Optional weight for graph search results (0.0-1.0)
            **kwargs: Additional search parameters

        Returns:
            List of search results
        """
        try:
            # Use provided parameters or defaults from config
            search_mode = mode or self.config.mode
            result_limit = limit or self.config.final_limit

            # Create query weights if any are specified
            query_weights = None
            if any(
                [
                    vector_weight is not None,
                    keyword_weight is not None,
                    graph_weight is not None,
                ]
            ):
                query_weights = validate_query_weights(
                    vector_weight=vector_weight,
                    keyword_weight=keyword_weight,
                    graph_weight=graph_weight,
                )

            # Check cache first
            if self.cache_manager:
                cached_results = self.cache_manager.get(
                    query, self.config, query_weights
                )
                if cached_results:
                    return self._convert_to_search_results(
                        cached_results[:result_limit]
                    )

            # Perform search based on mode
            if search_mode == SearchMode.VECTOR_ONLY:
                results = await self._vector_only_search(
                    query, result_limit, project_ids, **kwargs
                )
            elif search_mode == SearchMode.GRAPH_ONLY:
                results = await self._graph_only_search(query, result_limit, **kwargs)
            elif search_mode == SearchMode.HYBRID:
                results = await self._hybrid_search(
                    query,
                    result_limit,
                    project_ids,
                    source_types,
                    query_weights,
                    **kwargs,
                )
            elif search_mode == SearchMode.AUTO:
                results = await self._auto_search(
                    query,
                    result_limit,
                    project_ids,
                    source_types,
                    query_weights,
                    **kwargs,
                )
            else:
                raise ValueError(f"Unknown search mode: {search_mode}")

            # Apply reranking if enabled
            if self.config.enable_reranking and len(results) > 1:
                results = await self._rerank_results(query, results)

            # Cache results
            if self.cache_manager:
                self.cache_manager.set(query, self.config, results, query_weights)

            # Convert to SearchResult format for compatibility
            search_results = self._convert_to_search_results(results[:result_limit])

            self.logger.info(
                f"Enhanced search completed: {len(search_results)} results for query '{query}'"
            )
            return search_results

        except Exception as e:
            self.logger.error(f"Enhanced hybrid search failed: {e}")
            # Fallback to existing hybrid search
            return await self.keyword_engine.search(
                query=query,
                limit=result_limit,
                source_types=source_types,
                project_ids=project_ids,
            )

    async def _vector_only_search(
        self, query: str, limit: int, project_ids: list[str] | None = None, **kwargs
    ) -> list[EnhancedSearchResult]:
        """Perform vector-only search."""
        return await self.vector_module.search(
            query=query,
            limit=limit,
            min_score=self.config.min_vector_score,
            project_ids=project_ids,
            **kwargs,
        )

    async def _graph_only_search(
        self, query: str, limit: int, **kwargs
    ) -> list[EnhancedSearchResult]:
        """Perform graph-only search."""
        return await self.graph_module.search(
            query=query,
            limit=limit,
            max_depth=self.config.max_graph_depth,
            include_relationships=self.config.include_entity_relationships,
            include_temporal=self.config.include_temporal_context,
            use_graphiti=self.config.use_graphiti,
            **kwargs,
        )

    async def _hybrid_search(
        self,
        query: str,
        limit: int,
        project_ids: list[str] | None = None,
        source_types: list[str] | None = None,
        query_weights: QueryWeights | None = None,
        **kwargs,
    ) -> list[EnhancedSearchResult]:
        """Perform hybrid search combining vector, keyword, and graph search."""
        try:
            # Perform searches in parallel
            vector_task = self.vector_module.search(
                query, self.config.vector_limit, project_ids=project_ids
            )
            keyword_task = self._get_keyword_results(
                query, project_ids=project_ids, source_types=source_types
            )
            graph_task = self.graph_module.search(
                query,
                self.config.graph_limit,
                max_depth=self.config.max_graph_depth,
                include_relationships=self.config.include_entity_relationships,
                include_temporal=self.config.include_temporal_context,
                use_graphiti=self.config.use_graphiti,
            )

            vector_results, keyword_results, graph_results = await asyncio.gather(
                vector_task, keyword_task, graph_task, return_exceptions=True
            )

            # Handle exceptions and ensure proper typing
            final_vector_results: list[EnhancedSearchResult] = []
            final_keyword_results: list[EnhancedSearchResult] = []
            final_graph_results: list[EnhancedSearchResult] = []

            if isinstance(vector_results, Exception):
                self.logger.warning(f"Vector search failed: {vector_results}")
            else:
                final_vector_results = cast(list[EnhancedSearchResult], vector_results)

            if isinstance(keyword_results, Exception):
                self.logger.warning(f"Keyword search failed: {keyword_results}")
            else:
                final_keyword_results = cast(
                    list[EnhancedSearchResult], keyword_results
                )

            if isinstance(graph_results, Exception):
                self.logger.warning(f"Graph search failed: {graph_results}")
            else:
                final_graph_results = cast(list[EnhancedSearchResult], graph_results)

            # Use adaptive fusion strategy if enabled
            if kwargs.get("adaptive_fusion", False):
                original_strategy = self.config.fusion_strategy
                optimal_strategy = self.fusion_engine.select_optimal_fusion_strategy(
                    query,
                    final_vector_results,
                    final_keyword_results,
                    final_graph_results,
                )
                self.config.fusion_strategy = optimal_strategy
                self.logger.debug(
                    f"Using adaptive fusion strategy: {optimal_strategy.value}"
                )

            # Fuse results
            fused_results = self.fusion_engine.fuse_results(
                final_vector_results,
                final_keyword_results,
                final_graph_results,
                query_weights,
            )

            # Restore original strategy if adaptive fusion was used
            if kwargs.get("adaptive_fusion", False):
                self.config.fusion_strategy = original_strategy

            # Apply reranking if enabled
            if self.config.enable_reranking and fused_results:
                fused_results = await self._rerank_results(query, fused_results)

            return fused_results[:limit]

        except Exception as e:
            self.logger.error(f"Hybrid search failed: {e}")
            # Fallback to vector search only
            return await self._vector_only_search(query, limit, project_ids)

    async def _auto_search(
        self,
        query: str,
        limit: int,
        project_ids: list[str] | None = None,
        source_types: list[str] | None = None,
        query_weights: QueryWeights | None = None,
        **kwargs,
    ) -> list[EnhancedSearchResult]:
        """Automatically determine best search strategy."""
        # Simple heuristic: use hybrid for most queries
        # Could be enhanced with query analysis
        return await self._hybrid_search(
            query, limit, project_ids, source_types, query_weights, **kwargs
        )

    async def _get_keyword_results(
        self,
        query: str,
        project_ids: list[str] | None = None,
        source_types: list[str] | None = None,
    ) -> list[EnhancedSearchResult]:
        """Get keyword search results from existing engine."""
        try:
            # Use existing hybrid search engine for keyword functionality
            results = await self.keyword_engine.search(
                query=query,
                limit=self.config.vector_limit,
                source_types=source_types,
                project_ids=project_ids,
            )

            # Convert to EnhancedSearchResult format
            enhanced_results = []
            for result in results:
                enhanced_result = EnhancedSearchResult(
                    id=f"keyword_{hashlib.md5(result.text.encode()).hexdigest()[:8]}",
                    content=result.text,
                    title=result.source_title,
                    source_type=result.source_type,
                    combined_score=result.score,
                    keyword_score=result.score,
                    metadata={
                        "source_url": result.source_url,
                        "file_path": result.file_path,
                        "repo_name": result.repo_name,
                        "project_id": result.project_id,
                    },
                    debug_info={"search_type": "keyword"},
                )
                enhanced_results.append(enhanced_result)

            return enhanced_results

        except Exception as e:
            self.logger.error(f"Keyword search failed: {e}")
            return []

    async def _rerank_results(
        self,
        query: str,
        results: list[EnhancedSearchResult],
        user_context: dict[str, Any] | None = None,
    ) -> list[EnhancedSearchResult]:
        """Rerank results using the reranking engine."""
        if not self.reranking_engine or not results:
            return results

        try:
            return await self.reranking_engine.rerank_results(
                query, results, user_context
            )
        except Exception as e:
            self.logger.error(f"Reranking failed: {e}")
            return results

    def _convert_to_search_results(
        self, results: list[EnhancedSearchResult]
    ) -> list[SearchResult]:
        """Convert EnhancedSearchResult to SearchResult for compatibility."""
        search_results = []
        for result in results:
            search_result = SearchResult(
                score=result.combined_score,
                text=result.content,
                source_type=result.source_type,
                source_title=result.title,
                source_url=result.metadata.get("source_url"),
                file_path=result.metadata.get("file_path"),
                repo_name=result.metadata.get("repo_name"),
                project_id=result.metadata.get("project_id"),
                project_name=result.metadata.get("project_name"),
                project_description=result.metadata.get("project_description"),
                collection_name=result.metadata.get("collection_name"),
                parent_id=result.metadata.get("parent_id"),
                parent_title=result.metadata.get("parent_title"),
                breadcrumb_text=result.metadata.get("breadcrumb_text"),
                depth=result.metadata.get("depth"),
                children_count=result.metadata.get("children_count"),
                hierarchy_context=result.metadata.get("hierarchy_context"),
                is_attachment=result.metadata.get("is_attachment", False),
                parent_document_id=result.metadata.get("parent_document_id"),
                parent_document_title=result.metadata.get("parent_document_title"),
                attachment_id=result.metadata.get("attachment_id"),
                original_filename=result.metadata.get("original_filename"),
                file_size=result.metadata.get("file_size"),
                mime_type=result.metadata.get("mime_type"),
                attachment_author=result.metadata.get("attachment_author"),
                attachment_context=result.metadata.get("attachment_context"),
            )
            search_results.append(search_result)

        return search_results

    def update_config(self, config: EnhancedSearchConfig) -> None:
        """Update search configuration.

        Args:
            config: New search configuration
        """
        self.config = config
        self.fusion_engine = ResultFusionEngine(config)

        # Update reranking engine
        if config.enable_reranking and not self.reranking_engine:
            self.reranking_engine = RerankingEngine(
                config, self.vector_module.openai_client
            )
        elif not config.enable_reranking and self.reranking_engine:
            self.reranking_engine = None
        elif self.reranking_engine:
            # Update existing reranking engine config
            self.reranking_engine.config = config

        if config.enable_caching and not self.cache_manager:
            self.cache_manager = CacheManager(config.cache_ttl)
        elif not config.enable_caching and self.cache_manager:
            self.cache_manager = None

        self.logger.info("Enhanced search configuration updated")

    def get_stats(self) -> dict[str, Any]:
        """Get search engine statistics.

        Returns:
            Dictionary with search statistics
        """
        stats = {
            "config": {
                "mode": self.config.mode.value,
                "fusion_strategy": self.config.fusion_strategy.value,
                "vector_weight": self.config.vector_weight,
                "keyword_weight": self.config.keyword_weight,
                "graph_weight": self.config.graph_weight,
                "caching_enabled": self.config.enable_caching,
                "reranking_enabled": self.config.enable_reranking,
                "use_graphiti": self.config.use_graphiti,
            }
        }

        if self.cache_manager:
            stats["cache"] = self.cache_manager.get_stats()

        return stats

    def clear_cache(self) -> None:
        """Clear all cached search results."""
        if self.cache_manager:
            self.cache_manager.clear()
            self.logger.info("Search cache cleared")

    def invalidate_cache_pattern(self, pattern: str) -> int:
        """Invalidate cached results matching a pattern.

        Args:
            pattern: Regex pattern to match against cache keys

        Returns:
            Number of cache entries invalidated
        """
        if self.cache_manager:
            count = self.cache_manager.invalidate_pattern(pattern)
            self.logger.info(
                f"Invalidated {count} cache entries matching pattern: {pattern}"
            )
            return count
        return 0

    def get_cache_stats(self) -> dict[str, Any]:
        """Get detailed cache statistics.

        Returns:
            Dictionary with cache statistics or empty dict if caching disabled
        """
        if self.cache_manager:
            return self.cache_manager.get_stats()
        return {}
