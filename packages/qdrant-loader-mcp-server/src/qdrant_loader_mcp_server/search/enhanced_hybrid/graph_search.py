"""Graph search module for the enhanced hybrid search engine."""

import hashlib

from ...utils.logging import LoggingConfig
from .models import EnhancedSearchResult


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
