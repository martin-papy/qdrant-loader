"""
Core Search Engine - Lifecycle and Configuration Management.

This module implements the core SearchEngine class with initialization,
configuration management, and resource cleanup functionality.
"""

from typing import Any
import os
from pathlib import Path
import yaml
from qdrant_client import AsyncQdrantClient, models

# Expose OpenAI Async client symbol at module scope for tests to patch.
try:  # pragma: no cover - defensive import; tests may monkeypatch this
    from openai import AsyncOpenAI as _AsyncOpenAI  # type: ignore
except Exception:  # pragma: no cover - openai may be optional
    _AsyncOpenAI = None  # type: ignore[assignment]

# Public alias so tests can patch qdrant_loader_mcp_server.search.engine.AsyncOpenAI
AsyncOpenAI = _AsyncOpenAI  # type: ignore[assignment]

from ...config import OpenAIConfig, QdrantConfig, SearchConfig
from ...utils.logging import LoggingConfig
from ..components.search_result_models import HybridSearchResult
from ..enhanced.cross_document_intelligence import ClusteringStrategy, SimilarityMetric
from ..enhanced.topic_search_chain import ChainStrategy, TopicSearchChain
from ..hybrid_search import HybridSearchEngine

from .search import SearchOperations
from .topic_chain import TopicChainOperations
from .faceted import FacetedSearchOperations
from .intelligence import IntelligenceOperations
from .strategies import StrategySelector

logger = LoggingConfig.get_logger(__name__)


class SearchEngine:
    """Main search engine that orchestrates query processing and search."""

    def __init__(self):
        """Initialize the search engine."""
        self.client: AsyncQdrantClient | None = None
        self.config: QdrantConfig | None = None
        self.openai_client: Any | None = None
        self.hybrid_search: HybridSearchEngine | None = None
        self.logger = LoggingConfig.get_logger(__name__)

        # Initialize operation modules (will be set up after initialization)
        self._search_ops: SearchOperations | None = None
        self._topic_chain_ops: TopicChainOperations | None = None
        self._faceted_ops: FacetedSearchOperations | None = None
        self._intelligence_ops: IntelligenceOperations | None = None
        self._strategy_selector: StrategySelector | None = None

    async def initialize(
        self,
        config: QdrantConfig,
        openai_config: OpenAIConfig,
        search_config: SearchConfig | None = None,
    ) -> None:
        """Initialize the search engine with configuration."""
        self.config = config
        try:
            # Configure timeout for Qdrant cloud instances
            # Set to 120 seconds to handle large datasets and prevent ReadTimeout errors
            self.client = AsyncQdrantClient(
                url=config.url,
                api_key=config.api_key,
                timeout=120,  # 120 seconds timeout for cloud instances
            )
            # Keep legacy OpenAI client for now; vector embeddings use provider with fallback
            try:
                if AsyncOpenAI is not None and getattr(openai_config, "api_key", None):
                    # Use module-scope alias so tests can patch this symbol
                    self.openai_client = AsyncOpenAI(api_key=openai_config.api_key)
                else:
                    self.openai_client = None
            except Exception:
                self.openai_client = None

            # Ensure collection exists
            if self.client is None:
                raise RuntimeError("Failed to initialize Qdrant client")

            collections = await self.client.get_collections()
            if not any(
                c.name == config.collection_name for c in collections.collections
            ):
                # Determine vector size from llm settings or defaults
                vector_size = 1536
                # 1) From env variable if provided
                try:
                    env_size = os.getenv("LLM_VECTOR_SIZE")
                    if env_size:
                        vector_size = int(env_size)
                except Exception:
                    pass
                # 2) From MCP_CONFIG file if present
                try:
                    cfg_path = os.getenv("MCP_CONFIG")
                    if cfg_path and Path(cfg_path).exists():
                        with open(cfg_path, "r", encoding="utf-8") as f:
                            data = yaml.safe_load(f) or {}
                        llm = (
                            data.get("global", {}).get("llm")
                            or data.get("global_config", {}).get("llm")
                            or {}
                        )
                        emb = llm.get("embeddings") or {}
                        if isinstance(emb.get("vector_size"), int):
                            vector_size = int(emb["vector_size"]) 
                except Exception:
                    pass

                await self.client.create_collection(
                    collection_name=config.collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE,
                    ),
                )

            # Initialize hybrid search (single path; pass through search_config which may be None)
            if self.client:
                self.hybrid_search = HybridSearchEngine(
                    qdrant_client=self.client,
                    openai_client=self.openai_client,
                    collection_name=config.collection_name,
                    search_config=search_config,
                )

            # Initialize operation modules
            self._search_ops = SearchOperations(self)
            self._topic_chain_ops = TopicChainOperations(self)
            self._faceted_ops = FacetedSearchOperations(self)
            self._intelligence_ops = IntelligenceOperations(self)
            self._strategy_selector = StrategySelector(self)

            self.logger.info("Successfully connected to Qdrant", url=config.url)
        except Exception as e:
            self.logger.error(
                "Failed to connect to Qdrant server",
                error=str(e),
                url=config.url,
                hint="Make sure Qdrant is running and accessible at the configured URL",
            )
            raise RuntimeError(
                f"Failed to connect to Qdrant server at {config.url}. "
                "Please ensure Qdrant is running and accessible."
            ) from None  # Suppress the original exception

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self.client:
            await self.client.close()
            self.client = None

    # Delegate operations to specialized modules
    async def search(
        self,
        query: str,
        source_types: list[str] | None = None,
        limit: int = 5,
        project_ids: list[str] | None = None,
    ) -> list[HybridSearchResult]:
        """Search for documents using hybrid search."""
        if not self._search_ops:
            raise RuntimeError("Search engine not initialized")
        return await self._search_ops.search(query, source_types, limit, project_ids)

    async def generate_topic_chain(
        self, query: str, strategy: ChainStrategy = ChainStrategy.BREADTH_FIRST
    ) -> TopicSearchChain:
        """Generate topic search chain."""
        if not self._topic_chain_ops:
            raise RuntimeError("Search engine not initialized")
        return await self._topic_chain_ops.generate_topic_chain(query, strategy)

    async def execute_topic_chain(
        self, chain: TopicSearchChain, limit_per_topic: int = 3
    ) -> dict[str, list[HybridSearchResult]]:
        """Execute topic search chain."""
        if not self._topic_chain_ops:
            raise RuntimeError("Search engine not initialized")
        return await self._topic_chain_ops.execute_topic_chain(chain, limit_per_topic)

    async def search_with_topic_chain(
        self,
        query: str,
        chain_strategy: ChainStrategy = ChainStrategy.BREADTH_FIRST,
        limit_per_topic: int = 3,
        max_topics: int = 5,
    ) -> dict:
        """Perform search with topic chain analysis."""
        if not self._topic_chain_ops:
            raise RuntimeError("Search engine not initialized")
        return await self._topic_chain_ops.search_with_topic_chain(
            query, chain_strategy, limit_per_topic, max_topics
        )

    async def search_with_facets(
        self,
        query: str,
        facet_filters: list | None = None,
        limit: int = 5,
        generate_facets: bool = True,
    ) -> dict:
        """Perform faceted search."""
        if not self._faceted_ops:
            raise RuntimeError("Search engine not initialized")
        return await self._faceted_ops.search_with_facets(
            query, facet_filters, limit, generate_facets
        )

    async def get_facet_suggestions(
        self, documents: list[HybridSearchResult], max_facets_per_type: int = 5
    ) -> dict:
        """Get facet suggestions from documents."""
        if not self._faceted_ops:
            raise RuntimeError("Search engine not initialized")
        return await self._faceted_ops.get_facet_suggestions(documents, max_facets_per_type)

    async def analyze_document_relationships(
        self, documents: list[HybridSearchResult]
    ) -> dict:
        """Analyze relationships between documents."""
        if not self._intelligence_ops:
            raise RuntimeError("Search engine not initialized")
        return await self._intelligence_ops.analyze_document_relationships(documents)

    async def find_similar_documents(
        self,
        target_document: HybridSearchResult,
        candidate_documents: list[HybridSearchResult],
        similarity_threshold: float = 0.7,
        limit: int = 5,
    ) -> dict:
        """Find similar documents."""
        if not self._intelligence_ops:
            raise RuntimeError("Search engine not initialized")
        return await self._intelligence_ops.find_similar_documents(
            target_document, candidate_documents, similarity_threshold, limit
        )

    async def detect_document_conflicts(
        self, documents: list[HybridSearchResult], limit: int = 10
    ) -> dict:
        """Detect conflicts between documents."""
        if not self._intelligence_ops:
            raise RuntimeError("Search engine not initialized")
        return await self._intelligence_ops.detect_document_conflicts(documents, limit)

    async def find_complementary_content(
        self,
        target_document: HybridSearchResult,
        candidate_documents: list[HybridSearchResult],
        max_recommendations: int = 5,
    ) -> dict:
        """Find complementary content."""
        if not self._intelligence_ops:
            raise RuntimeError("Search engine not initialized")
        return await self._intelligence_ops.find_complementary_content(
            target_document, candidate_documents, max_recommendations
        )

    async def cluster_documents(
        self,
        documents: list[HybridSearchResult],
        strategy: ClusteringStrategy = ClusteringStrategy.MIXED_FEATURES,
        max_clusters: int = 10,
        min_cluster_size: int = 2,
    ) -> dict:
        """Cluster documents using specified strategy."""
        if not self._intelligence_ops:
            raise RuntimeError("Search engine not initialized")
        return await self._intelligence_ops.cluster_documents(
            documents, strategy, max_clusters, min_cluster_size
        )

    # Strategy selection methods
    def _select_optimal_strategy(self, documents: list) -> str:
        """Select optimal search strategy."""
        if not self._strategy_selector:
            raise RuntimeError("Search engine not initialized")
        return self._strategy_selector.select_optimal_strategy(documents)

    def _analyze_document_characteristics(self, documents: list) -> dict[str, float]:
        """Analyze document characteristics."""
        if not self._strategy_selector:
            raise RuntimeError("Search engine not initialized")
        return self._strategy_selector.analyze_document_characteristics(documents)
