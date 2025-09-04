"""
Core Search Engine - Lifecycle and Configuration Management.

This module implements the core SearchEngine class with initialization,
configuration management, and resource cleanup functionality.
"""

import os
from pathlib import Path
from typing import Any

import yaml
from qdrant_client import AsyncQdrantClient, models

from ...config import OpenAIConfig, QdrantConfig, SearchConfig
from ...utils.logging import LoggingConfig
from ..components.search_result_models import HybridSearchResult
from ..enhanced.topic_search_chain import ChainStrategy, TopicSearchChain
from ..hybrid_search import HybridSearchEngine
from .faceted import FacetedSearchOperations
from .intelligence import IntelligenceOperations
from .search import SearchOperations
from .strategies import StrategySelector
from .topic_chain import TopicChainOperations

# Expose OpenAI Async client symbol at module scope for tests to patch only.
# Do not import the OpenAI library at runtime to avoid hard dependency.
AsyncOpenAI = None  # type: ignore[assignment]

logger = LoggingConfig.get_logger(__name__)


def _safe_value_to_dict(value_obj: object) -> dict:
    """Safely convert a facet value object to a dict.

    Uses getattr with defaults and tolerates missing attributes.
    """
    return {
        "value": getattr(value_obj, "value", "unknown"),
        "count": getattr(value_obj, "count", 0),
        "display_name": getattr(value_obj, "display_name", "Unknown"),
        "description": getattr(value_obj, "description", None),
    }


def _safe_facet_to_dict(facet: object, top_k: int = 10) -> dict:
    """Safely convert a facet object to a dict with defensive callable/None handling."""
    facet_type_obj = getattr(facet, "facet_type", None)
    facet_type_value = (
        getattr(facet_type_obj, "value", "unknown") if facet_type_obj else "unknown"
    )

    # Safely obtain top values
    get_top_values = getattr(facet, "get_top_values", None)
    values_raw: list = []
    if callable(get_top_values):
        try:
            values_raw = get_top_values(top_k) or []
        except Exception:
            values_raw = []

    return {
        "type": facet_type_value,
        "name": getattr(facet, "name", "unknown"),
        "display_name": getattr(facet, "display_name", "Unknown"),
        "description": getattr(facet, "description", None),
        "values": [_safe_value_to_dict(v) for v in values_raw],
    }


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
            client_kwargs = {
                "url": config.url,
                "timeout": 120,  # 120 seconds timeout for cloud instances
            }
            if getattr(config, "api_key", None):
                client_kwargs["api_key"] = config.api_key
            self.client = AsyncQdrantClient(**client_kwargs)
            # Keep legacy OpenAI client for now only when tests patch AsyncOpenAI
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
                # Determine vector size from env or config file; avoid hardcoded default when possible
                vector_size = None
                # 1) From env variable if provided
                try:
                    env_size = os.getenv("LLM_VECTOR_SIZE")
                    if env_size:
                        vector_size = int(env_size)
                except Exception:
                    vector_size = None
                # 2) From MCP_CONFIG file if present
                if vector_size is None:
                    try:
                        cfg_path = os.getenv("MCP_CONFIG")
                        if cfg_path and Path(cfg_path).exists():
                            with open(cfg_path, encoding="utf-8") as f:
                                data = yaml.safe_load(f) or {}
                            llm = data.get("global", {}).get("llm") or {}
                            emb = llm.get("embeddings") or {}
                            if isinstance(emb.get("vector_size"), int):
                                vector_size = int(emb["vector_size"])
                    except Exception:
                        vector_size = None
                # 3) Deprecated fallback
                if vector_size is None:
                    vector_size = 1536
                    try:
                        self.logger.warning(
                            "No vector_size provided via global.llm or env; falling back to 1536 (deprecated)."
                        )
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
            try:
                await self.client.close()
            except Exception as e:  # pragma: no cover - defensive cleanup
                # Prefer instance logger; fall back to module logger if needed
                try:
                    self.logger.warning(
                        "Error closing Qdrant client during cleanup", error=str(e)
                    )
                except Exception:
                    logger.warning(
                        "Error closing Qdrant client during cleanup", error=str(e)
                    )
            finally:
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
            # Fallback: delegate directly to hybrid_search when operations not initialized
            if not self.hybrid_search:
                raise RuntimeError("Search engine not initialized")
            return await self.hybrid_search.search(
                query=query,
                source_types=source_types,
                limit=limit,
                project_ids=project_ids,
            )
        return await self._search_ops.search(query, source_types, limit, project_ids)

    async def generate_topic_chain(
        self,
        query: str,
        strategy: ChainStrategy | str = ChainStrategy.BREADTH_FIRST,
        max_links: int = 5,
    ) -> TopicSearchChain:
        """Generate topic search chain.

        Parameters:
            query: The query string.
            strategy: Chain strategy to use; accepts a ChainStrategy enum or a string.
            max_links: Maximum number of links to generate.

        Returns:
            TopicSearchChain

        Raises:
            TypeError: If strategy is not a ChainStrategy or string.
        """
        if not self._topic_chain_ops:
            raise RuntimeError("Search engine not initialized")
        # Normalize strategy: allow ChainStrategy enum or string
        if hasattr(strategy, "value"):
            strategy_str = strategy.value  # ChainStrategy enum
        elif isinstance(strategy, str):
            strategy_str = strategy
        else:
            raise TypeError(
                "strategy must be a ChainStrategy or str, got "
                + type(strategy).__name__
            )
        return await self._topic_chain_ops.generate_topic_chain(
            query, strategy_str, max_links
        )

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
            # Fallback: delegate directly to hybrid_search when operations not initialized
            if not self.hybrid_search:
                raise RuntimeError("Search engine not initialized")

            # Convert facet filter dictionaries to FacetFilter objects if provided
            filter_objects = []
            if facet_filters:
                from ..enhanced.faceted_search import FacetFilter, FacetType

                for filter_dict in facet_filters:
                    try:
                        facet_type = FacetType(filter_dict["facet_type"])
                    except Exception:
                        continue  # Skip invalid facet filters

                    values_raw = filter_dict.get("values")
                    if not values_raw:
                        continue  # Skip filters with no values

                    if isinstance(values_raw, set | tuple):
                        values = list(values_raw)
                    elif isinstance(values_raw, list):
                        values = values_raw
                    else:
                        values = [str(values_raw)]

                    operator = filter_dict.get("operator", "OR")
                    filter_objects.append(
                        FacetFilter(
                            facet_type=facet_type,
                            values=values,
                            operator=operator,
                        )
                    )

            faceted_results = await self.hybrid_search.search_with_facets(
                query=query,
                limit=limit,
                source_types=source_types,
                project_ids=project_ids,
                facet_filters=filter_objects,
            )

            # Convert to MCP-friendly dict format (same as FacetedSearchOperations does)
            return {
                "results": getattr(faceted_results, "results", []),
                "facets": [
                    _safe_facet_to_dict(facet)
                    for facet in getattr(faceted_results, "facets", [])
                ],
                "total_results": getattr(faceted_results, "total_results", 0),
                "filtered_count": getattr(faceted_results, "filtered_count", 0),
                "applied_filters": [
                    {
                        "facet_type": (
                            getattr(getattr(f, "facet_type", None), "value", "unknown")
                            if getattr(f, "facet_type", None)
                            else "unknown"
                        ),
                        "values": getattr(f, "values", []),
                        "operator": getattr(f, "operator", "and"),
                    }
                    for f in getattr(faceted_results, "applied_filters", [])
                ],
                "generation_time_ms": getattr(
                    faceted_results, "generation_time_ms", 0.0
                ),
            }
        return await self._faceted_ops.search_with_facets(
            query, limit, source_types, project_ids, facet_filters
        )

    async def get_facet_suggestions(
        self,
        query: str = None,
        current_filters: list[dict] = None,
        limit: int = 20,
        documents: list[HybridSearchResult] = None,
        max_facets_per_type: int = 5,
    ) -> dict:
        """Get facet suggestions from documents or query."""
        # If query is provided, perform search to get documents
        if query is not None:
            if not self._search_ops:
                # Fallback: use hybrid_search directly when operations not initialized
                if not self.hybrid_search:
                    raise RuntimeError("Search engine not initialized")
                search_results = await self.hybrid_search.search(
                    query=query, limit=limit
                )
            else:
                search_results = await self._search_ops.search(query, limit=limit)

            # Use the hybrid search engine's suggestion method
            if hasattr(self.hybrid_search, "suggest_facet_refinements"):
                return self.hybrid_search.suggest_facet_refinements(
                    search_results, current_filters or []
                )
            else:
                return {"suggestions": []}

        # Fallback to faceted operations if documents provided directly
        if documents is not None:
            if not self._faceted_ops:
                raise RuntimeError("Search engine not initialized")
            return await self._faceted_ops.get_facet_suggestions(
                documents, max_facets_per_type
            )

        raise ValueError("Either query or documents must be provided")

    async def analyze_document_relationships(
        self,
        query: str = None,
        limit: int = 20,
        source_types: list[str] = None,
        project_ids: list[str] = None,
        documents: list[HybridSearchResult] = None,
    ) -> dict:
        """Analyze relationships between documents."""
        if not self._intelligence_ops:
            raise RuntimeError("Search engine not initialized")

        # If query is provided, perform search to get documents
        if query is not None:
            search_results = await self._search_ops.search(
                query, source_types, limit, project_ids
            )

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
                        "project_ids": project_ids,
                    },
                }

            # Use the hybrid search engine's analysis method
            analysis_result = await self.hybrid_search.analyze_document_relationships(
                search_results
            )

            # Add query metadata to the result
            if isinstance(analysis_result, dict):
                analysis_result["query_metadata"] = {
                    "original_query": query,
                    "document_count": len(search_results),
                    "source_types": source_types,
                    "project_ids": project_ids,
                }

            return analysis_result

        # Fallback to documents if provided directly
        if documents is not None:
            return await self._intelligence_ops.analyze_document_relationships(
                documents
            )

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
    ) -> dict | list[dict]:
        """Find similar documents."""
        if not self._search_ops:
            raise RuntimeError("Search engine not initialized")

        # First, search for target documents
        target_documents = await self._search_ops.search(
            target_query, source_types, 1, project_ids
        )
        if not target_documents:
            return {}

        # Then search for comparison documents
        comparison_documents = await self._search_ops.search(
            comparison_query or target_query, source_types, limit, project_ids
        )

        # Use the hybrid search engine's method to find similarities
        # API expects a single target document and a list of comparison documents.
        target_doc = target_documents[0]

        # Convert metric strings to enum values when provided; otherwise default
        try:
            from ..hybrid_search import SimilarityMetric as _SimMetric

            metric_enums = None
            if similarity_metrics:
                metric_enums = []
                for m in similarity_metrics:
                    try:
                        metric_enums.append(_SimMetric(m))
                    except Exception:
                        # Ignore unknown metrics gracefully
                        continue
            # Fallback default if conversion produced empty list
            if metric_enums is not None and len(metric_enums) == 0:
                metric_enums = None
        except Exception:
            metric_enums = None

        return await self.hybrid_search.find_similar_documents(
            target_doc,
            comparison_documents,
            metric_enums,
            max_similar,
        )

    async def detect_document_conflicts(
        self,
        query: str,
        limit: int = 10,
        source_types: list[str] = None,
        project_ids: list[str] = None,
    ) -> dict:
        """Detect conflicts between documents."""
        if not self._search_ops:
            raise RuntimeError("Search engine not initialized")

        # First, search for documents related to the query
        search_results = await self._search_ops.search(
            query, source_types, limit, project_ids
        )

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
                    "project_ids": project_ids,
                },
                "original_documents": [
                    {
                        "document_id": d.document_id,
                        "title": (
                            d.get_display_title()
                            if hasattr(d, "get_display_title")
                            and callable(d.get_display_title)
                            else d.source_title or "Untitled"
                        ),
                        "source_type": d.source_type or "unknown",
                    }
                    for d in search_results
                ],
            }

        # Delegate to the intelligence module which handles query-based conflict detection
        if not self._intelligence_ops:
            raise RuntimeError("Intelligence operations not initialized")

        conflicts_result = await self._intelligence_ops.detect_document_conflicts(
            query=query, limit=limit, source_types=source_types, project_ids=project_ids
        )

        # Add query metadata and original documents to the result
        if isinstance(conflicts_result, dict):
            conflicts_result["query_metadata"] = {
                "original_query": query,
                "document_count": len(search_results),
                "source_types": source_types,
                "project_ids": project_ids,
            }
            # Convert documents to lightweight format
            conflicts_result["original_documents"] = [
                {
                    "document_id": d.document_id,
                    "title": (
                        d.get_display_title()
                        if hasattr(d, "get_display_title")
                        and callable(d.get_display_title)
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
        from qdrant_loader_mcp_server.search.enhanced.cdi.models import (
            ClusteringStrategy,
        )

        if isinstance(strategy, str):
            if strategy == "adaptive":
                # First, get documents to analyze for optimal strategy selection
                documents = await self._search_ops.search(
                    query, source_types, limit, project_ids
                )
                optimal_strategy = self._select_optimal_strategy(documents)
                strategy_map = {
                    "mixed_features": ClusteringStrategy.MIXED_FEATURES,
                    "semantic_embedding": ClusteringStrategy.SEMANTIC_EMBEDDING,
                    "topic_based": ClusteringStrategy.TOPIC_BASED,
                    "entity_based": ClusteringStrategy.ENTITY_BASED,
                    "project_based": ClusteringStrategy.PROJECT_BASED,
                    "hierarchical": ClusteringStrategy.HIERARCHICAL,
                }
                strategy_enum = strategy_map.get(
                    optimal_strategy, ClusteringStrategy.MIXED_FEATURES
                )
            else:
                strategy_map = {
                    "mixed_features": ClusteringStrategy.MIXED_FEATURES,
                    "semantic_embedding": ClusteringStrategy.SEMANTIC_EMBEDDING,
                    "topic_based": ClusteringStrategy.TOPIC_BASED,
                    "entity_based": ClusteringStrategy.ENTITY_BASED,
                    "project_based": ClusteringStrategy.PROJECT_BASED,
                    "hierarchical": ClusteringStrategy.HIERARCHICAL,
                }
                strategy_enum = strategy_map.get(
                    strategy, ClusteringStrategy.MIXED_FEATURES
                )
        else:
            strategy_enum = strategy

        return await self._intelligence_ops.cluster_documents(
            query,
            strategy_enum,
            max_clusters,
            min_cluster_size,
            limit,
            source_types,
            project_ids,
        )

    # Strategy selection methods
    def _select_optimal_strategy(self, documents: list) -> str:
        """Select optimal search strategy."""
        # Handle empty documents case
        if not documents:
            return "mixed_features"  # Default strategy for empty documents

        if not self._strategy_selector:
            # Provide basic strategy selection when not initialized (for testing)
            # Use simple heuristics based on document characteristics
            analysis = self._analyze_document_characteristics(documents)

            # Simple strategy selection logic
            if analysis.get("entity_richness", 0) > 0.6:
                return "entity_based"
            elif analysis.get("project_distribution", 0) > 0.7:
                return "project_based"
            elif analysis.get("hierarchical_structure", 0) > 0.6:
                return "hierarchical"
            elif analysis.get("topic_clarity", 0) > 0.6:
                return "topic_based"
            else:
                return "mixed_features"  # Safe default

        # The strategy selector returns a ClusteringStrategy enum; normalize to string value
        selected = self._strategy_selector.select_optimal_strategy(documents)
        return selected.value if hasattr(selected, "value") else str(selected)

    def _analyze_document_characteristics(self, documents: list) -> dict[str, float]:
        """Analyze document characteristics."""
        if not self._strategy_selector:
            # Provide basic analysis when not initialized (for testing)
            characteristics = {}

            if documents:
                # Helper function to handle both dict and object formats
                def get_doc_attr(doc, attr, default=None):
                    if isinstance(doc, dict):
                        return doc.get(attr, default)
                    else:
                        return getattr(doc, attr, default)

                # Calculate hierarchical structure based on breadcrumb depths
                total_depth = 0
                valid_breadcrumbs = 0

                # Calculate source diversity
                source_types = set()
                project_ids = set()

                for doc in documents:

                    # Hierarchical structure
                    breadcrumb = get_doc_attr(doc, "breadcrumb_text", "")
                    if breadcrumb and breadcrumb.strip():
                        depth = len(breadcrumb.split(" > ")) - 1
                        total_depth += depth
                        valid_breadcrumbs += 1

                    # Source diversity
                    source_type = get_doc_attr(doc, "source_type", "unknown")
                    if source_type:
                        source_types.add(source_type)

                    # Project distribution
                    project_id = get_doc_attr(doc, "project_id", None)
                    if project_id:
                        project_ids.add(project_id)

                # Hierarchical structure
                if valid_breadcrumbs > 0:
                    avg_depth = total_depth / valid_breadcrumbs
                    characteristics["hierarchical_structure"] = min(
                        avg_depth / 5.0, 1.0
                    )
                else:
                    characteristics["hierarchical_structure"] = 0.0

                # Source diversity (0-1 based on variety of source types)
                characteristics["source_diversity"] = min(
                    len(source_types) / 4.0, 1.0
                )  # Normalize assuming max 4 source types

                # Project distribution (0-1 based on project spread)
                characteristics["project_distribution"] = min(
                    len(project_ids) / 3.0, 1.0
                )  # Normalize assuming max 3 projects

                # Entity richness (basic heuristic based on doc attributes)
                has_entities_count = sum(
                    1 for doc in documents if get_doc_attr(doc, "has_entities", False)
                )
                characteristics["entity_richness"] = (
                    has_entities_count / len(documents) if documents else 0.0
                )

                # Topic clarity (higher when source types are more consistent)
                if len(documents) > 0:
                    # Count occurrences of each source type
                    source_type_counts = {}
                    for doc in documents:
                        source_type = get_doc_attr(doc, "source_type", "unknown")
                        source_type_counts[source_type] = (
                            source_type_counts.get(source_type, 0) + 1
                        )

                    # Find most common source type and calculate consistency
                    if source_type_counts:
                        most_common_count = max(source_type_counts.values())
                        characteristics["topic_clarity"] = most_common_count / len(
                            documents
                        )
                    else:
                        characteristics["topic_clarity"] = 0.0
                else:
                    characteristics["topic_clarity"] = 0.0

            else:
                # Default values for empty documents
                characteristics.update(
                    {
                        "hierarchical_structure": 0.0,
                        "source_diversity": 0.0,
                        "project_distribution": 0.0,
                        "entity_richness": 0.0,
                        "topic_clarity": 0.0,
                    }
                )

            return characteristics

        return self._strategy_selector.analyze_document_characteristics(documents)
