"""Main engine for the enhanced hybrid search."""

import asyncio
import hashlib
from typing import Any, cast

from openai import AsyncOpenAI
from qdrant_client import QdrantClient

from ...utils.logging import LoggingConfig
from ..hybrid_search import HybridSearchEngine
from ..models import SearchResult
from .cache_manager import CacheManager
from .fusion_engine import ResultFusionEngine
from .graph_search import GraphSearchModule
from .models import (
    EnhancedSearchConfig,
    EnhancedSearchResult,
    QueryWeights,
    SearchMode,
    validate_query_weights,
)
from .reranking_engine import RerankingEngine
from .vector_search import VectorSearchModule


class EnhancedHybridSearchEngine(HybridSearchEngine):
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
        """Initialize the enhanced hybrid search engine.

        Args:
            qdrant_client: Qdrant client instance
            openai_client: OpenAI client instance
            collection_name: Name of the Qdrant collection
            neo4j_manager: Neo4j manager instance (optional)
            graphiti_manager: Graphiti manager instance (optional)
            config: Enhanced search configuration (optional)
        """
        super().__init__(qdrant_client, openai_client, collection_name)
        self.config = config or EnhancedSearchConfig()
        self.logger = LoggingConfig.get_logger(__name__)

        # Initialize modules
        self.vector_search = VectorSearchModule(
            qdrant_client, openai_client, collection_name
        )
        self.graph_search = GraphSearchModule(neo4j_manager, graphiti_manager)
        self.fusion_engine = ResultFusionEngine(self.config)
        self.reranking_engine = RerankingEngine(self.config, openai_client)

        # Initialize cache if enabled
        self.cache_manager = (
            CacheManager(
                ttl=self.config.cache_ttl,
                max_size=self.config.cache_max_size,
                cleanup_interval=self.config.cache_cleanup_interval,
            )
            if self.config.enable_caching
            else None
        )

        self.logger.info("Enhanced Hybrid Search Engine initialized.")
        self.logger.info(f"Initial config: {self.config}")

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
            limit: Maximum number of final results
            project_ids: List of project IDs to filter by
            source_types: List of source types to filter by
            vector_weight: Query-time vector weight override
            keyword_weight: Query-time keyword weight override
            graph_weight: Query-time graph weight override
            **kwargs: Additional parameters for different search types

        Returns:
            List of final search results
        """
        final_limit = limit or self.config.final_limit
        search_mode = mode or self.config.mode

        # Validate and get query-time weights
        query_weights = validate_query_weights(
            vector_weight, keyword_weight, graph_weight
        )

        # Check cache first
        if self.cache_manager:
            cached_results = self.cache_manager.get(query, self.config, query_weights)
            if cached_results is not None:
                return self._convert_to_search_results(cached_results[:final_limit])

        # Execute search based on mode
        search_map = {
            SearchMode.VECTOR_ONLY: self._vector_only_search,
            SearchMode.GRAPH_ONLY: self._graph_only_search,
            SearchMode.HYBRID: self._hybrid_search,
            SearchMode.AUTO: self._auto_search,
        }

        search_function = search_map.get(search_mode)
        if not search_function:
            raise ValueError(f"Unsupported search mode: {search_mode}")

        # Prepare arguments for the selected search function
        search_args = {
            "query": query,
            "limit": final_limit,
            "project_ids": project_ids,
            "source_types": source_types,
            "query_weights": query_weights,
            **kwargs,
        }
        # For auto and hybrid, we don't pass limit down initially
        if search_mode in [SearchMode.HYBRID, SearchMode.AUTO]:
            del search_args["limit"]

        enhanced_results = await search_function(**search_args)

        # Rerank final results if enabled
        if self.config.enable_reranking:
            user_context = kwargs.get("user_context")
            enhanced_results = await self._rerank_results(
                query, enhanced_results, user_context
            )

        # Cache final results
        if self.cache_manager:
            self.cache_manager.set(query, self.config, enhanced_results, query_weights)

        # Convert to final SearchResult format and limit
        final_results = self._convert_to_search_results(enhanced_results)
        return final_results[:final_limit]

    async def _vector_only_search(
        self, query: str, limit: int, project_ids: list[str] | None = None, **kwargs
    ) -> list[EnhancedSearchResult]:
        """Perform vector-only search."""
        return await self.vector_search.search(
            query,
            limit=self.config.vector_limit,
            min_score=self.config.min_vector_score,
            project_ids=project_ids,
            **kwargs,
        )

    async def _graph_only_search(
        self, query: str, limit: int, **kwargs
    ) -> list[EnhancedSearchResult]:
        """Perform graph-only search."""
        return await self.graph_search.search(
            query,
            limit=self.config.graph_limit,
            max_depth=self.config.max_graph_depth,
            include_relationships=self.config.include_entity_relationships,
            include_temporal=self.config.include_temporal_context,
            use_graphiti=self.config.use_graphiti,
            **kwargs,
        )

    async def _hybrid_search(
        self,
        query: str,
        project_ids: list[str] | None = None,
        source_types: list[str] | None = None,
        query_weights: QueryWeights | None = None,
        **kwargs,
    ) -> list[EnhancedSearchResult]:
        """Perform hybrid search by combining vector, keyword, and graph results."""
        # Run searches in parallel
        vector_task = self.vector_search.search(
            query,
            self.config.vector_limit,
            self.config.min_vector_score,
            project_ids,
            **kwargs,
        )
        graph_task = self.graph_search.search(
            query,
            self.config.graph_limit,
            self.config.max_graph_depth,
            self.config.include_entity_relationships,
            self.config.include_temporal_context,
            self.config.use_graphiti,
            **kwargs,
        )
        keyword_task = self._get_keyword_results(query, project_ids, source_types)

        # Use gather with return_exceptions=True to handle individual failures
        results = await asyncio.gather(
            vector_task, graph_task, keyword_task, return_exceptions=True
        )

        # Handle results and exceptions
        vector_results: list[EnhancedSearchResult]
        graph_results: list[EnhancedSearchResult]
        keyword_results: list[EnhancedSearchResult]

        if isinstance(results[0], Exception):
            self.logger.error(f"Vector search failed: {results[0]}")
            vector_results = []
        else:
            vector_results = cast(list[EnhancedSearchResult], results[0])

        if isinstance(results[1], Exception):
            self.logger.error(f"Graph search failed: {results[1]}")
            graph_results = []
        else:
            graph_results = cast(list[EnhancedSearchResult], results[1])

        if isinstance(results[2], Exception):
            self.logger.error(f"Keyword search failed: {results[2]}")
            keyword_results = []
        else:
            keyword_results = cast(list[EnhancedSearchResult], results[2])

        self.logger.debug(f"Vector search returned {len(vector_results)} results")
        self.logger.debug(f"Graph search returned {len(graph_results)} results")
        self.logger.debug(f"Keyword search returned {len(keyword_results)} results")

        # Fuse results
        fused_results = self.fusion_engine.fuse_results(
            vector_results, keyword_results, graph_results, query_weights
        )

        return fused_results

    async def _auto_search(self, **kwargs: Any) -> list[EnhancedSearchResult]:
        """Automatically determine the best search strategy."""
        # Simple auto: for now, just fallback to hybrid
        # In the future, this could analyze the query to decide
        # whether to use vector, graph, or hybrid search.
        self.logger.info("Auto mode selected, defaulting to hybrid search.")
        return await self._hybrid_search(**kwargs)

    async def _get_keyword_results(
        self,
        query: str,
        project_ids: list[str] | None = None,
        source_types: list[str] | None = None,
    ) -> list[EnhancedSearchResult]:
        """Perform keyword search (delegated from base HybridSearchEngine).

        This method is a placeholder to show how keyword search would integrate.
        It calls the base class's search method and converts results.
        """
        try:
            # The base `search` from HybridSearchEngine is a simple keyword search
            keyword_base_results = await super().search(
                query, self.config.vector_limit, project_ids, source_types
            )

            # Convert SearchResult to EnhancedSearchResult
            keyword_results = []
            for i, res in enumerate(keyword_base_results):
                content_for_id = f"{res.source_title}:{res.text}"
                result_id = hashlib.md5(content_for_id.encode()).hexdigest()

                metadata = res.dict()
                # Remove fields that are already top-level in EnhancedSearchResult
                metadata.pop("score", None)
                metadata.pop("text", None)
                metadata.pop("source_type", None)
                metadata.pop("source_title", None)

                enhanced_res = EnhancedSearchResult(
                    id=f"keyword_{result_id}",
                    content=res.text,
                    title=res.source_title,
                    source_type=res.source_type,
                    combined_score=res.score,
                    keyword_score=res.score,
                    metadata=metadata,
                    debug_info={"search_type": "keyword", "result_rank": i},
                )
                keyword_results.append(enhanced_res)
            return keyword_results
        except Exception as e:
            self.logger.error(f"Keyword search failed: {e}")
            return []

    async def _rerank_results(
        self,
        query: str,
        results: list[EnhancedSearchResult],
        user_context: dict[str, Any] | None = None,
    ) -> list[EnhancedSearchResult]:
        """Rerank results using the configured reranking engine."""
        if not self.config.enable_reranking:
            return results

        return await self.reranking_engine.rerank_results(query, results, user_context)

    def _convert_to_search_results(
        self, results: list[EnhancedSearchResult]
    ) -> list[SearchResult]:
        """Convert enhanced results back to standard SearchResult for API compatibility."""
        final_results = []
        for res in results:
            # Prepare data for SearchResult, extracting from metadata where needed
            data = {
                "score": res.combined_score,
                "text": res.content,
                "source_type": res.source_type,
                "source_title": res.title,
                **res.metadata,  # Unpack metadata fields
            }
            # Add scores from enhanced result to the data payload
            # This is for debugging and transparency, not part of the core SearchResult model
            # but can be useful if the model is flexible or for logging.
            # If SearchResult has a 'metadata' field, we can store it there.
            # Assuming SearchResult is a Pydantic model that might ignore extra fields.

            # Let's ensure we don't overwrite metadata if it exists.
            if "metadata" not in data:
                data["metadata"] = {}

            data["metadata"].update(
                {
                    "graph_score": res.graph_score,
                    "vector_score": res.vector_score,
                    "keyword_score": res.keyword_score,
                    "rerank_score": res.rerank_score,
                    "entity_ids": res.entity_ids,
                    "relationship_types": res.relationship_types,
                }
            )

            # Ensure only valid fields for SearchResult are passed
            valid_fields = SearchResult.model_fields.keys()
            filtered_data = {k: v for k, v in data.items() if k in valid_fields}

            search_result = SearchResult(**filtered_data)
            final_results.append(search_result)
        return final_results

    def update_config(self, config: EnhancedSearchConfig) -> None:
        """Update the configuration of the search engine and its modules.

        Args:
            config: The new configuration object.
        """
        self.config = config
        self.fusion_engine.config = config
        self.reranking_engine.config = config

        # Re-initialize cache manager if caching settings changed
        if self.config.enable_caching and self.cache_manager:
            self.cache_manager.ttl = self.config.cache_ttl
            self.cache_manager.max_size = self.config.cache_max_size
        elif self.config.enable_caching and not self.cache_manager:
            self.cache_manager = CacheManager(
                ttl=self.config.cache_ttl, max_size=self.config.cache_max_size
            )
        elif not self.config.enable_caching and self.cache_manager:
            self.cache_manager = None

        self.logger.info(f"Search engine configuration updated: {config}")

    def get_stats(self) -> dict[str, Any]:
        """Get statistics from the search engine and its modules."""
        stats = {
            "config": self.config.to_dict(),
            "cache_stats": self.get_cache_stats(),
            "fusion_engine_type": self.fusion_engine.__class__.__name__,
            "reranking_engine_type": self.reranking_engine.__class__.__name__,
        }
        return stats

    def clear_cache(self) -> None:
        """Clear the search cache."""
        if self.cache_manager:
            self.cache_manager.clear()
        else:
            self.logger.warning("Caching is disabled, cannot clear cache.")

    def invalidate_cache_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching a pattern."""
        if self.cache_manager:
            return self.cache_manager.invalidate_pattern(pattern)
        self.logger.warning("Caching is disabled, cannot invalidate cache entries.")
        return 0

    def get_cache_stats(self) -> dict[str, Any]:
        """Get statistics from the cache manager."""
        if self.cache_manager:
            return self.cache_manager.get_stats()
        return {"status": "disabled"}
