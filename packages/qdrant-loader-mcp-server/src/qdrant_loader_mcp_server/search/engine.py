"""Search engine implementation for the MCP server."""

from typing import Any

from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from ..config import OpenAIConfig, QdrantConfig
from ..graphiti import is_graphiti_available
from ..utils.logging import LoggingConfig
from .enhanced_hybrid_search import (
    EnhancedHybridSearchEngine,
    EnhancedSearchConfig,
    SearchMode,
)
from .exceptions import (
    HybridSearchError,
    OpenAIEmbeddingError,
    QdrantConnectionError,
    QdrantQueryError,
)
from .hybrid_search import HybridSearchEngine
from .models import SearchResult

logger = LoggingConfig.get_logger(__name__)


class SearchEngine:
    """Main search engine that orchestrates query processing and search."""

    def __init__(self):
        """Initialize the search engine."""
        self.client: QdrantClient | None = None
        self.config: QdrantConfig | None = None
        self.openai_client: AsyncOpenAI | None = None
        self.hybrid_search: HybridSearchEngine | None = None
        self.enhanced_hybrid_search: EnhancedHybridSearchEngine | None = None
        self.use_enhanced_search: bool = False
        self.logger = LoggingConfig.get_logger(__name__)

    async def initialize(
        self, config: QdrantConfig, openai_config: OpenAIConfig
    ) -> None:
        """Initialize the search engine with configuration."""
        self.config = config
        try:
            # Create Qdrant client with warning suppression for test environments
            import warnings

            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore", message="Api key is used with an insecure connection"
                )
                self.client = QdrantClient(url=config.url, api_key=config.api_key)
            self.openai_client = AsyncOpenAI(api_key=openai_config.api_key)

            # Ensure collection exists
            if self.client is None:
                raise RuntimeError("Failed to initialize Qdrant client")

            collections = self.client.get_collections().collections
            if not any(c.name == config.collection_name for c in collections):
                self.client.create_collection(
                    collection_name=config.collection_name,
                    vectors_config=models.VectorParams(
                        size=1536,  # Default size for OpenAI embeddings
                        distance=models.Distance.COSINE,
                    ),
                )

            # Check if Graphiti is available for enhanced search
            graphiti_available = await is_graphiti_available()
            self.logger.info(
                "Graphiti availability check",
                available=graphiti_available,
                will_use_enhanced_search=graphiti_available,
            )

            if graphiti_available and self.client and self.openai_client:
                # Initialize enhanced hybrid search with graph capabilities
                try:
                    enhanced_config = EnhancedSearchConfig(
                        mode=SearchMode.HYBRID,
                        vector_weight=0.5,
                        keyword_weight=0.2,
                        graph_weight=0.3,
                        enable_caching=True,
                        enable_reranking=True,
                    )

                    self.enhanced_hybrid_search = EnhancedHybridSearchEngine(
                        qdrant_client=self.client,
                        openai_client=self.openai_client,
                        collection_name=config.collection_name,
                        config=enhanced_config,
                    )
                    self.use_enhanced_search = True
                    self.logger.info(
                        "Enhanced hybrid search engine initialized successfully",
                        config=enhanced_config.__dict__,
                    )
                except Exception as e:
                    self.logger.warning(
                        "Failed to initialize enhanced hybrid search, falling back to basic hybrid search",
                        error=str(e),
                    )
                    self.use_enhanced_search = False

            # Initialize basic hybrid search as fallback or primary
            if self.client and self.openai_client:
                self.hybrid_search = HybridSearchEngine(
                    qdrant_client=self.client,
                    openai_client=self.openai_client,
                    collection_name=config.collection_name,
                )

            self.logger.info(
                "Search engine initialized successfully",
                url=config.url,
                enhanced_search=self.use_enhanced_search,
                graphiti_available=graphiti_available,
            )
        except UnexpectedResponse as e:
            self.logger.error(
                "Qdrant server returned unexpected response",
                error=str(e),
                url=config.url,
                status_code=getattr(e, "status_code", None),
            )
            raise QdrantConnectionError(
                message=f"Qdrant server returned unexpected response: {e}",
                qdrant_url=config.url,
                original_error=e,
            )
        except ConnectionError as e:
            self.logger.error(
                "Failed to connect to Qdrant server",
                error=str(e),
                url=config.url,
            )
            raise QdrantConnectionError(
                message=f"Cannot connect to Qdrant server at {config.url}",
                qdrant_url=config.url,
                original_error=e,
            )
        except Exception as e:
            self.logger.error(
                "Unexpected error during Qdrant initialization",
                error=str(e),
                url=config.url,
                error_type=type(e).__name__,
            )
            raise QdrantConnectionError(
                message=f"Failed to initialize Qdrant client: {e}",
                qdrant_url=config.url,
                original_error=e,
            )

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self.client:
            self.client.close()
            self.client = None

    async def search(
        self,
        query: str,
        source_types: list[str] | None = None,
        limit: int = 5,
        project_ids: list[str] | None = None,
        # Enhanced search parameters
        mode: SearchMode | None = None,
        vector_weight: float | None = None,
        keyword_weight: float | None = None,
        graph_weight: float | None = None,
        fusion_strategy: str | None = None,
    ) -> list[SearchResult]:
        """Search for documents using hybrid search.

        Args:
            query: Search query text
            source_types: Optional list of source types to filter by
            limit: Maximum number of results to return
            project_ids: Optional list of project IDs to filter by
            mode: Search mode (vector_only, graph_only, hybrid, auto) - enhanced search only
            vector_weight: Weight for vector search results (0.0-1.0) - enhanced search only
            keyword_weight: Weight for keyword search results (0.0-1.0) - enhanced search only
            graph_weight: Weight for graph search results (0.0-1.0) - enhanced search only
            fusion_strategy: Fusion strategy for combining results - enhanced search only
        """
        # Use enhanced search if available and enhanced parameters are provided
        use_enhanced = (
            self.use_enhanced_search
            and self.enhanced_hybrid_search
            and (
                mode is not None
                or vector_weight is not None
                or keyword_weight is not None
                or graph_weight is not None
                or fusion_strategy is not None
            )
        )

        if use_enhanced and self.enhanced_hybrid_search:
            self.logger.debug(
                "Using enhanced hybrid search",
                query=query,
                source_types=source_types,
                limit=limit,
                project_ids=project_ids,
                mode=mode,
                vector_weight=vector_weight,
                keyword_weight=keyword_weight,
                graph_weight=graph_weight,
                fusion_strategy=fusion_strategy,
            )

            try:
                # Handle fusion strategy if provided
                original_strategy = None
                if fusion_strategy is not None:
                    from .enhanced_hybrid_search import FusionStrategy

                    strategy_map = {
                        "weighted_sum": FusionStrategy.WEIGHTED_SUM,
                        "reciprocal_rank_fusion": FusionStrategy.RECIPROCAL_RANK_FUSION,
                        "maximal_marginal_relevance": FusionStrategy.MMR,
                        "graph_enhanced_weighted": FusionStrategy.GRAPH_ENHANCED_WEIGHTED,
                        "confidence_adaptive": FusionStrategy.CONFIDENCE_ADAPTIVE,
                        "multi_stage": FusionStrategy.MULTI_STAGE,
                        "context_aware": FusionStrategy.CONTEXT_AWARE,
                    }

                    if fusion_strategy in strategy_map:
                        original_strategy = (
                            self.enhanced_hybrid_search.config.fusion_strategy
                        )
                        self.enhanced_hybrid_search.config.fusion_strategy = (
                            strategy_map[fusion_strategy]
                        )

                results = await self.enhanced_hybrid_search.search(
                    query=query,
                    mode=mode,
                    limit=limit,
                    project_ids=project_ids,
                    source_types=source_types,
                    vector_weight=vector_weight,
                    keyword_weight=keyword_weight,
                    graph_weight=graph_weight,
                )

                # Restore original fusion strategy if it was changed
                if original_strategy is not None:
                    self.enhanced_hybrid_search.config.fusion_strategy = (
                        original_strategy
                    )

                self.logger.info(
                    "Enhanced search completed",
                    query=query,
                    result_count=len(results),
                    project_ids=project_ids,
                    mode=mode,
                )

                return results
            except QdrantConnectionError:
                # Re-raise Qdrant connection errors
                raise
            except QdrantQueryError:
                # Re-raise Qdrant query errors
                raise
            except OpenAIEmbeddingError:
                # Re-raise OpenAI embedding errors
                raise
            except Exception as e:
                self.logger.error(
                    "Enhanced search failed, falling back to basic search",
                    error=str(e),
                    error_type=type(e).__name__,
                    query=query,
                )
                # Wrap in HybridSearchError but allow fallback
                # Fall through to basic search

        # Use basic hybrid search
        if not self.hybrid_search:
            raise RuntimeError("Search engine not initialized")

        self.logger.debug(
            "Using basic hybrid search",
            query=query,
            source_types=source_types,
            limit=limit,
            project_ids=project_ids,
        )

        try:
            results = await self.hybrid_search.search(
                query=query,
                source_types=source_types,
                limit=limit,
                project_ids=project_ids,
            )

            self.logger.info(
                "Basic search completed",
                query=query,
                result_count=len(results),
                project_ids=project_ids,
            )

            return results
        except UnexpectedResponse as e:
            self.logger.error("Qdrant server error during basic search", error=str(e))
            raise QdrantQueryError(
                message=f"Qdrant query failed: {e}",
                query=query,
                original_error=e,
            )
        except ConnectionError as e:
            self.logger.error("Connection error during basic search", error=str(e))
            raise QdrantConnectionError(
                message=f"Connection lost during search: {e}",
                original_error=e,
            )
        except Exception as e:
            self.logger.error(
                "Unexpected error during basic search",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise HybridSearchError(
                message=f"Basic search failed: {e}",
                failed_components=["basic_hybrid_search"],
                original_error=e,
            )

    def get_search_capabilities(self) -> dict[str, bool]:
        """Get current search engine capabilities.

        Returns:
            Dict with capability flags
        """
        return {
            "basic_hybrid_search": self.hybrid_search is not None,
            "enhanced_hybrid_search": self.enhanced_hybrid_search is not None,
            "graph_search": self.use_enhanced_search,
            "vector_search": True,
            "keyword_search": True,
            "query_time_weighting": self.use_enhanced_search,
            "reranking": self.use_enhanced_search,
            "caching": self.use_enhanced_search,
        }

    def get_search_stats(self) -> dict[str, Any]:
        """Get search engine statistics and performance metrics.

        Returns:
            Dictionary containing search engine statistics
        """
        stats: dict[str, Any] = {
            "enhanced_search_available": self.use_enhanced_search,
            "graphiti_available": False,  # Will be updated async if needed
            "basic_search_available": self.hybrid_search is not None,
        }

        # Add enhanced search stats if available
        if self.use_enhanced_search and self.enhanced_hybrid_search:
            try:
                enhanced_stats = self.enhanced_hybrid_search.get_stats()
                stats["enhanced_search_stats"] = enhanced_stats
            except Exception as e:
                self.logger.warning(f"Failed to get enhanced search stats: {e}")

        return stats

    async def fusion_benchmark(
        self,
        query: str,
        strategies: list[str],
        limit: int = 10,
        include_debug: bool = False,
        project_ids: list[str] | None = None,
    ) -> dict[str, list[SearchResult]]:
        """Benchmark different fusion strategies for hybrid search.

        Args:
            query: Search query text
            strategies: List of fusion strategy names to benchmark
            limit: Maximum number of results per strategy
            include_debug: Whether to include debug information
            project_ids: Optional list of project IDs to filter by

        Returns:
            Dictionary mapping strategy names to their search results
        """
        if not self.use_enhanced_search or not self.enhanced_hybrid_search:
            # Fallback to basic search for all strategies
            self.logger.warning(
                "Enhanced search not available for fusion benchmark, using basic search"
            )
            basic_results = await self.search(
                query=query, limit=limit, project_ids=project_ids
            )
            return dict.fromkeys(strategies, basic_results)

        try:
            from .enhanced_hybrid_search import FusionStrategy

            # Map strategy names to enum values
            strategy_map = {
                "weighted_sum": FusionStrategy.WEIGHTED_SUM,
                "reciprocal_rank_fusion": FusionStrategy.RECIPROCAL_RANK_FUSION,
                "maximal_marginal_relevance": FusionStrategy.MMR,
                "graph_enhanced_weighted": FusionStrategy.GRAPH_ENHANCED_WEIGHTED,
                "confidence_adaptive": FusionStrategy.CONFIDENCE_ADAPTIVE,
                "multi_stage": FusionStrategy.MULTI_STAGE,
                "context_aware": FusionStrategy.CONTEXT_AWARE,
            }

            benchmark_results = {}

            for strategy_name in strategies:
                if strategy_name not in strategy_map:
                    self.logger.warning(f"Unknown fusion strategy: {strategy_name}")
                    continue

                try:
                    # Temporarily update the fusion strategy
                    original_strategy = (
                        self.enhanced_hybrid_search.config.fusion_strategy
                    )
                    self.enhanced_hybrid_search.config.fusion_strategy = strategy_map[
                        strategy_name
                    ]

                    # Perform search with this strategy
                    results = await self.enhanced_hybrid_search.search(
                        query=query,
                        mode=SearchMode.HYBRID,
                        limit=limit,
                        project_ids=project_ids,
                    )

                    # Restore original strategy
                    self.enhanced_hybrid_search.config.fusion_strategy = (
                        original_strategy
                    )

                    # Note: Debug information is available in the enhanced search engine
                    # but not exposed in the basic SearchResult model
                    benchmark_results[strategy_name] = results

                    self.logger.debug(
                        f"Fusion benchmark completed for strategy {strategy_name}",
                        result_count=len(results),
                    )

                except Exception as e:
                    self.logger.error(
                        f"Error benchmarking fusion strategy {strategy_name}: {e}"
                    )
                    benchmark_results[strategy_name] = []

            return benchmark_results

        except Exception as e:
            self.logger.error(f"Fusion benchmark failed: {e}")
            # Fallback to basic search
            basic_results = await self.search(
                query=query, limit=limit, project_ids=project_ids
            )
            return dict.fromkeys(strategies, basic_results)
