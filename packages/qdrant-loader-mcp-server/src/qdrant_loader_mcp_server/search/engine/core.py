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
        self, query: str, strategy: ChainStrategy = ChainStrategy.BREADTH_FIRST, max_links: int = 5
    ) -> TopicSearchChain:
        """Generate topic search chain."""
        if not self._topic_chain_ops:
            raise RuntimeError("Search engine not initialized")
        # Convert ChainStrategy enum to string if needed
        strategy_str = strategy.value if hasattr(strategy, 'value') else str(strategy)
        return await self._topic_chain_ops.generate_topic_chain(query, strategy_str, max_links)

    async def execute_topic_chain(
        self, 
        topic_chain: TopicSearchChain, 
        results_per_link: int = 3,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
    ) -> dict[str, list[HybridSearchResult]]:
        """Execute topic search chain."""
        if not self._topic_chain_ops:
            raise RuntimeError("Search engine not initialized")
        return await self._topic_chain_ops.execute_topic_chain(
            topic_chain, results_per_link, source_types, project_ids
        )

    async def search_with_topic_chain(
        self,
        query: str,
        strategy: str = "mixed_exploration",
        results_per_link: int = 3,
        max_links: int = 5,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
    ) -> dict:
        """Perform search with topic chain analysis."""
        if not self._topic_chain_ops:
            raise RuntimeError("Search engine not initialized")
        return await self._topic_chain_ops.search_with_topic_chain(
            query, strategy, results_per_link, max_links, source_types, project_ids
        )

    async def search_with_facets(
        self,
        query: str,
        limit: int = 5,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
        facet_filters: list[dict] | None = None,
    ) -> dict:
        """Perform faceted search."""
        if not self._faceted_ops:
            raise RuntimeError("Search engine not initialized")
        return await self._faceted_ops.search_with_facets(
            query, limit, source_types, project_ids, facet_filters
        )

    async def get_facet_suggestions(
        self, 
        query: str = None,
        current_filters: list[dict] = None,
        limit: int = 20,
        documents: list[HybridSearchResult] = None, 
        max_facets_per_type: int = 5
    ) -> dict:
        """Get facet suggestions from documents or query."""
        if not self._search_ops:
            raise RuntimeError("Search engine not initialized")
            
        # If query is provided, perform search to get documents
        if query is not None:
            search_results = await self._search_ops.search(query, limit=limit)
            # Use the hybrid search engine's suggestion method
            return self.hybrid_search.suggest_facet_refinements(search_results, current_filters or [])
        
        # Fallback to faceted operations if documents provided directly
        if documents is not None:
            if not self._faceted_ops:
                raise RuntimeError("Search engine not initialized")
            return await self._faceted_ops.get_facet_suggestions(documents, max_facets_per_type)
        
        raise ValueError("Either query or documents must be provided")

    async def analyze_document_relationships(
        self, 
        query: str = None,
        limit: int = 20,
        source_types: list[str] = None,
        project_ids: list[str] = None,
        documents: list[HybridSearchResult] = None
    ) -> dict:
        """Analyze relationships between documents."""
        if not self._intelligence_ops:
            raise RuntimeError("Search engine not initialized")
            
        # If query is provided, perform search to get documents
        if query is not None:
            search_results = await self._search_ops.search(query, source_types, limit, project_ids)
            
            # Check if we have sufficient documents for relationship analysis
            if len(search_results) < 2:
                return {
                    "error": f"Need at least 2 documents for relationship analysis, found {len(search_results)}",
                    "minimum_required": 2,
                    "found": len(search_results),
                    "document_count": len(search_results),
                    "query_metadata": {
                        "original_query": query,
                        "document_count": len(search_results),
                        "source_types": source_types,
                        "project_ids": project_ids
                    }
                }
            
            # Use the hybrid search engine's analysis method
            analysis_result = await self.hybrid_search.analyze_document_relationships(search_results)
            
            # Add query metadata to the result
            if isinstance(analysis_result, dict):
                analysis_result["query_metadata"] = {
                    "original_query": query,
                    "document_count": len(search_results),
                    "source_types": source_types,
                    "project_ids": project_ids
                }
            
            return analysis_result
        
        # Fallback to documents if provided directly
        if documents is not None:
            return await self._intelligence_ops.analyze_document_relationships(documents)
        
        raise ValueError("Either query or documents must be provided")

    async def find_similar_documents(
        self,
        target_query: str,
        comparison_query: str = "",
        similarity_metrics: list[str] = None,
        max_similar: int = 5,
        similarity_threshold: float = 0.7,
        limit: int = 5,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
    ) -> dict:
        """Find similar documents."""
        if not self._search_ops:
            raise RuntimeError("Search engine not initialized")
        
        # First, search for target documents
        target_documents = await self._search_ops.search(target_query, source_types, 1, project_ids)
        if not target_documents:
            return []  # No target document found
        
        # Then search for comparison documents  
        comparison_documents = await self._search_ops.search(comparison_query or target_query, source_types, limit, project_ids)
        
        # Use the hybrid search engine's method to find similarities
        return await self.hybrid_search.find_similar_documents(
            target_documents=target_documents,
            comparison_documents=comparison_documents, 
            similarity_metrics=similarity_metrics or ["semantic_similarity"],
            max_similar=max_similar,
            similarity_threshold=similarity_threshold
        )

    async def detect_document_conflicts(
        self, 
        query: str, 
        limit: int = 10,
        source_types: list[str] = None,
        project_ids: list[str] = None
    ) -> dict:
        """Detect conflicts between documents."""
        if not self._search_ops:
            raise RuntimeError("Search engine not initialized")
        
        # First, search for documents related to the query
        search_results = await self._search_ops.search(query, source_types, limit, project_ids)
        
        # Check if we have sufficient documents for conflict detection
        if len(search_results) < 2:
            return {
                "conflicts": [],
                "resolution_suggestions": {},
                "message": f"Need at least 2 documents for conflict detection, found {len(search_results)}",
                "document_count": len(search_results),
                "query_metadata": {
                    "original_query": query,
                    "document_count": len(search_results),
                    "source_types": source_types,
                    "project_ids": project_ids
                },
                "original_documents": [
                    {
                        "document_id": d.document_id,
                        "title": (
                            d.get_display_title()
                            if hasattr(d, "get_display_title") and callable(d.get_display_title)
                            else d.source_title or "Untitled"
                        ),
                        "source_type": d.source_type or "unknown",
                    }
                    for d in search_results
                ]
            }
        
        # Delegate to the intelligence module which handles query-based conflict detection
        if not self._intelligence_ops:
            raise RuntimeError("Intelligence operations not initialized")
            
        conflicts_result = await self._intelligence_ops.detect_document_conflicts(
            query=query,
            limit=limit,
            source_types=source_types,
            project_ids=project_ids
        )
        
        # Add query metadata and original documents to the result
        if isinstance(conflicts_result, dict):
            conflicts_result["query_metadata"] = {
                "original_query": query,
                "document_count": len(search_results),
                "source_types": source_types,
                "project_ids": project_ids
            }
            # Convert documents to lightweight format
            conflicts_result["original_documents"] = [
                {
                    "document_id": d.document_id,
                    "title": (
                        d.get_display_title()
                        if hasattr(d, "get_display_title") and callable(d.get_display_title)
                        else d.source_title or "Untitled"
                    ),
                    "source_type": d.source_type or "unknown",
                }
                for d in search_results
            ]
        
        return conflicts_result

    async def find_complementary_content(
        self,
        target_query: str,
        context_query: str,
        max_recommendations: int = 5,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
    ) -> dict:
        """Find complementary content."""
        if not self._intelligence_ops:
            raise RuntimeError("Search engine not initialized")
        return await self._intelligence_ops.find_complementary_content(
            target_query, context_query, max_recommendations, source_types, project_ids
        )

    async def cluster_documents(
        self,
        query: str,
        strategy: str = "mixed_features",
        max_clusters: int = 10,
        min_cluster_size: int = 2,
        limit: int = 30,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
    ) -> dict:
        """Cluster documents using specified strategy."""
        if not self._intelligence_ops:
            raise RuntimeError("Search engine not initialized")
        
        # Convert strategy string to enum if needed
        from qdrant_loader_mcp_server.search.enhanced.cdi.models import ClusteringStrategy
        if isinstance(strategy, str):
            if strategy == "adaptive":
                # First, get documents to analyze for optimal strategy selection
                documents = await self._search_ops.search(query, source_types, limit, project_ids)
                optimal_strategy = self._select_optimal_strategy(documents)
                strategy_map = {
                    "mixed_features": ClusteringStrategy.MIXED_FEATURES,
                    "semantic_embedding": ClusteringStrategy.SEMANTIC_EMBEDDING,
                    "topic_based": ClusteringStrategy.TOPIC_BASED,
                    "entity_based": ClusteringStrategy.ENTITY_BASED,
                    "project_based": ClusteringStrategy.PROJECT_BASED,
                    "hierarchical": ClusteringStrategy.HIERARCHICAL,
                }
                strategy_enum = strategy_map.get(optimal_strategy, ClusteringStrategy.MIXED_FEATURES)
            else:
                strategy_map = {
                    "mixed_features": ClusteringStrategy.MIXED_FEATURES,
                    "semantic_embedding": ClusteringStrategy.SEMANTIC_EMBEDDING,
                    "topic_based": ClusteringStrategy.TOPIC_BASED,
                    "entity_based": ClusteringStrategy.ENTITY_BASED,
                    "project_based": ClusteringStrategy.PROJECT_BASED,
                    "hierarchical": ClusteringStrategy.HIERARCHICAL,
                }
                strategy_enum = strategy_map.get(strategy, ClusteringStrategy.MIXED_FEATURES)
        else:
            strategy_enum = strategy
        
        return await self._intelligence_ops.cluster_documents(
            query, strategy_enum, max_clusters, min_cluster_size, limit, source_types, project_ids
        )

    # Strategy selection methods
    def _select_optimal_strategy(self, documents: list) -> str:
        """Select optimal search strategy."""
        # Handle empty documents case
        if not documents:
            return "mixed_features"  # Default strategy for empty documents
            
        if not self._strategy_selector:
            raise RuntimeError("Search engine not initialized")
        return self._strategy_selector.select_optimal_strategy(documents)

    def _analyze_document_characteristics(self, documents: list) -> dict[str, float]:
        """Analyze document characteristics."""
        if not self._strategy_selector:
            # Provide basic analysis when not initialized (for testing)
            characteristics = {}
            
            # Calculate hierarchical structure based on breadcrumb depths
            if documents:
                total_depth = 0
                valid_breadcrumbs = 0
                
                for doc in documents:
                    breadcrumb = getattr(doc, 'breadcrumb_text', '')
                    if breadcrumb and breadcrumb.strip():
                        depth = len(breadcrumb.split(' > ')) - 1
                        total_depth += depth
                        valid_breadcrumbs += 1
                
                if valid_breadcrumbs > 0:
                    avg_depth = total_depth / valid_breadcrumbs
                    # Normalize to 0-1 range (assuming max depth of 5 for normalization)
                    characteristics["hierarchical_structure"] = min(avg_depth / 5.0, 1.0)
                else:
                    characteristics["hierarchical_structure"] = 0.0
            else:
                characteristics["hierarchical_structure"] = 0.0
            
            return characteristics
            
        return self._strategy_selector.analyze_document_characteristics(documents)
