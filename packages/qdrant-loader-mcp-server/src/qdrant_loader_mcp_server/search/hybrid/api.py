from __future__ import annotations

from typing import Any


class HybridEngineAPI:
    def __init__(
        self,
        *,
        logger: Any | None = None,
        enable_intent_adaptation: bool = True,
        knowledge_graph: Any | None = None,
        min_score: float = 0.0,
        # Optional components (may be wired by a builder in concrete engines)
        vector_search_service: Any | None = None,
        keyword_search_service: Any | None = None,
        query_processor: Any | None = None,
        result_combiner: Any | None = None,
        metadata_extractor: Any | None = None,
        faceted_search_engine: Any | None = None,
        intent_classifier: Any | None = None,
        adaptive_strategy: Any | None = None,
    ) -> None:
        # Defer logger setup to central LoggingConfig if not provided
        if logger is None:
            try:
                from ...utils.logging import LoggingConfig  # Lazy import to avoid cycles

                self.logger = LoggingConfig.get_logger(__name__)
            except Exception:
                # Last-resort fallback to stdlib logger-like shim
                class _StdLogger:
                    def debug(self, *args, **kwargs):
                        pass

                    def info(self, *args, **kwargs):
                        pass

                    def warning(self, *args, **kwargs):
                        pass

                    def error(self, *args, **kwargs):
                        pass

                self.logger = _StdLogger()
        else:
            self.logger = logger

        # Core toggles and context
        self.enable_intent_adaptation = enable_intent_adaptation
        self.knowledge_graph = knowledge_graph
        self.min_score = min_score

        # Optional components used by helper wrappers
        self.vector_search_service = vector_search_service
        self.keyword_search_service = keyword_search_service
        self.query_processor = query_processor
        self.result_combiner = result_combiner
        self.metadata_extractor = metadata_extractor
        self.faceted_search_engine = faceted_search_engine
        self.intent_classifier = intent_classifier
        self.adaptive_strategy = adaptive_strategy
        # Frequently wired later by concrete engines/builders
        self.hybrid_pipeline = None
        self.topic_chain_generator = None
        self.processing_config = None
        self._planner = None
        self._orchestrator = None


    async def search(
        self,
        query: str,
        limit: int = 5,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
        *,
        session_context: dict[str, Any] | None = None,
        behavioral_context: list[str] | None = None,
    ) -> list["HybridSearchResult"]:
        from .orchestration.search import run_search

        self.logger.debug(
            "Starting hybrid search",
            query=query,
            limit=limit,
            source_types=source_types,
            project_ids=project_ids,
            intent_adaptation_enabled=self.enable_intent_adaptation,
        )
        return await run_search(
            self,
            query=query,
            limit=limit,
            source_types=source_types,
            project_ids=project_ids,
            session_context=session_context,
            behavioral_context=behavioral_context,
        )

    # Topic Search Chain
    async def generate_topic_search_chain(
        self,
        query: str,
        strategy: "ChainStrategy" | None = None,
        max_links: int = 5,
        initialize_from_search: bool = True,
    ) -> "TopicSearchChain":
        from .orchestration.topic_chain import generate_topic_search_chain as _gen
        if strategy is None:
            from ..enhanced.topic_search_chain import ChainStrategy as _CS
            strategy = _CS.MIXED_EXPLORATION
        return await _gen(
            self,
            query=query,
            strategy=strategy,
            max_links=max_links,
            initialize_from_search=initialize_from_search,
        )

    async def execute_topic_chain_search(
        self,
        topic_chain: "TopicSearchChain",
        results_per_link: int = 3,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
    ) -> dict[str, list["HybridSearchResult"]]:
        from .orchestration.topic_chain import execute_topic_chain_search as _exec
        return await _exec(
            self,
            topic_chain=topic_chain,
            results_per_link=results_per_link,
            source_types=source_types,
            project_ids=project_ids,
        )

    async def _initialize_topic_relationships(self, sample_query: str) -> None:
        from .orchestration.topic_chain import _initialize_topic_relationships as _init
        await _init(self, sample_query)

    # Faceted Search
    async def search_with_facets(
        self,
        query: str,
        limit: int = 5,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
        facet_filters: list["FacetFilter"] | None = None,
        generate_facets: bool = True,
        session_context: dict[str, Any] | None = None,
        behavioral_context: list[str] | None = None,
    ) -> "FacetedSearchResults":
        from .orchestration.facets import search_with_facets as _search_with_facets
        return await _search_with_facets(
            self,
            query=query,
            limit=limit,
            source_types=source_types,
            project_ids=project_ids,
            facet_filters=facet_filters,
            generate_facets=generate_facets,
            session_context=session_context,
            behavioral_context=behavioral_context,
        )

    # CDI
    async def analyze_document_relationships(
        self, documents: list["HybridSearchResult"]
    ) -> dict[str, Any]:
        from .orchestration.cdi import analyze_document_relationships as _analyze
        return await _analyze(self, documents)

    async def find_similar_documents(
        self,
        target_document: "HybridSearchResult",
        documents: list["HybridSearchResult"],
        similarity_metrics: list["SimilarityMetric"] | None = None,
        max_similar: int = 5,
    ) -> list[dict[str, Any]]:
        from .orchestration.cdi import find_similar_documents as _find
        return await _find(
            self,
            target_document=target_document,
            documents=documents,
            similarity_metrics=similarity_metrics,
            max_similar=max_similar,
        )

    async def detect_document_conflicts(
        self, documents: list["HybridSearchResult"]
    ) -> dict[str, Any]:
        from .orchestration.cdi import detect_document_conflicts as _detect
        return await _detect(self, documents)

    async def find_complementary_content(
        self,
        target_document: "HybridSearchResult",
        documents: list["HybridSearchResult"],
        max_recommendations: int = 5,
    ) -> list[dict[str, Any]]:
        from .orchestration.cdi import find_complementary_content as _find_comp
        return await _find_comp(
            self,
            target_document=target_document,
            documents=documents,
            max_recommendations=max_recommendations,
        )

    # Lookup
    def _build_document_lookup(
        self, documents: list["HybridSearchResult"], robust: bool = False
    ) -> dict[str, "HybridSearchResult"]:
        from .components.document_lookup import (
            build_document_lookup as _build,
        )
        return _build(documents, robust=robust, logger=self.logger)

    def _find_document_by_id(
        self, doc_id: str, doc_lookup: dict[str, "HybridSearchResult"]
    ) -> "HybridSearchResult" | None:
        from .components.document_lookup import find_document_by_id as _find
        return _find(doc_id, doc_lookup, logger=self.logger)

    async def cluster_documents(
        self,
        documents: list["HybridSearchResult"],
        strategy: "ClusteringStrategy" | None = None,
        max_clusters: int = 10,
        min_cluster_size: int = 2,
    ) -> dict[str, Any]:
        from .orchestration.clustering import cluster_documents as _cluster
        if strategy is None:
            from ..enhanced.cross_document_intelligence import (
                ClusteringStrategy as _CS,
            )
            strategy = _CS.MIXED_FEATURES
        return await _cluster(
            self,
            documents=documents,
            strategy=strategy,
            max_clusters=max_clusters,
            min_cluster_size=min_cluster_size,
        )

    # Cluster quality
    def _calculate_cluster_quality(
        self, cluster: Any, cluster_documents: list["HybridSearchResult"]
    ) -> dict[str, Any]:
        from .components.cluster_quality import calculate_cluster_quality
        return calculate_cluster_quality(cluster, cluster_documents)

    def _categorize_cluster_size(self, size: int) -> str:
        from .components.cluster_quality import categorize_cluster_size
        return categorize_cluster_size(size)

    def _estimate_content_similarity(
        self, documents: list["HybridSearchResult"]
    ) -> float:
        from .components.cluster_quality import estimate_content_similarity
        return estimate_content_similarity(documents)

    def _build_enhanced_metadata(
        self,
        clusters: list[Any],
        documents: list["HybridSearchResult"],
        strategy: Any,
        processing_time: float,
        matched_docs: int,
        requested_docs: int,
    ) -> dict[str, Any]:
        from .components.cluster_quality import build_enhanced_metadata
        return build_enhanced_metadata(
            clusters, documents, strategy, processing_time, matched_docs, requested_docs
        )

    def _calculate_std(self, values: list[float]) -> float:
        from .components.cluster_quality import calculate_std
        return calculate_std(values)

    def _assess_overall_quality(
        self, clusters: list[Any], matched_docs: int, requested_docs: int
    ) -> float:
        from .components.cluster_quality import assess_overall_quality
        return assess_overall_quality(clusters, matched_docs, requested_docs)

    def _generate_clustering_recommendations(
        self, clusters: list[Any], strategy: Any, matched_docs: int, requested_docs: int
    ) -> dict[str, Any]:
        from .components.cluster_quality import generate_clustering_recommendations
        return generate_clustering_recommendations(
            clusters, strategy, matched_docs, requested_docs
        )

    # Relationships
    def _analyze_cluster_relationships(
        self, clusters: list[Any], documents: list["HybridSearchResult"]
    ) -> list[dict[str, Any]]:
        from .orchestration.relationships import analyze_cluster_relationships as _rel
        return _rel(self, clusters, documents)

    def _analyze_cluster_pair(
        self, cluster_a: Any, cluster_b: Any, doc_lookup: dict
    ) -> dict[str, Any] | None:
        from .orchestration.relationships import analyze_cluster_pair as _pair
        return _pair(self, cluster_a, cluster_b, doc_lookup)

    def _analyze_entity_overlap(self, cluster_a: Any, cluster_b: Any) -> dict[str, Any] | None:
        from .components.relationships import analyze_entity_overlap
        return analyze_entity_overlap(cluster_a, cluster_b)

    def _analyze_topic_overlap(self, cluster_a: Any, cluster_b: Any) -> dict[str, Any] | None:
        from .components.relationships import analyze_topic_overlap
        return analyze_topic_overlap(cluster_a, cluster_b)

    def _analyze_source_similarity(self, docs_a: list, docs_b: list) -> dict[str, Any] | None:
        from .components.relationships import analyze_source_similarity
        return analyze_source_similarity(docs_a, docs_b)

    def _analyze_hierarchy_relationship(self, docs_a: list, docs_b: list) -> dict[str, Any] | None:
        from .components.relationships import analyze_hierarchy_relationship
        return analyze_hierarchy_relationship(docs_a, docs_b)

    def _analyze_content_similarity(self, docs_a: list, docs_b: list) -> dict[str, Any] | None:
        from .components.relationships import analyze_content_similarity
        return analyze_content_similarity(docs_a, docs_b)

    # Stats and settings
    def get_adaptive_search_stats(self) -> dict[str, Any]:
        stats = {
            "intent_adaptation_enabled": self.enable_intent_adaptation,
            "has_knowledge_graph": self.knowledge_graph is not None,
        }
        if self.enable_intent_adaptation and self.intent_classifier:
            stats.update(self.intent_classifier.get_cache_stats())
        if self.adaptive_strategy:
            stats.update(self.adaptive_strategy.get_strategy_stats())
        return stats

    def _build_conflict_settings(self, search_config: Any | None) -> dict[str, Any] | None:
        from .components.builder import build_conflict_settings
        return build_conflict_settings(search_config)

    # Helper wrappers
    async def _get_embedding(self, text: str) -> list[float]:
        from .components.helpers import get_embedding
        return await get_embedding(self.vector_search_service, text)

    async def _expand_query(self, query: str) -> str:
        from .components.helpers import expand_query
        return await expand_query(self.query_processor, query)

    async def _expand_query_aggressive(self, query: str) -> str:
        from .components.helpers import expand_query_aggressive
        return await expand_query_aggressive(self.query_processor, query)

    def _analyze_query(self, query: str) -> dict[str, Any]:
        from .components.helpers import analyze_query
        return analyze_query(self.query_processor, query)

    async def _vector_search(
        self, query: str, limit: int, project_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        from .components.helpers import vector_search
        return await vector_search(self.vector_search_service, query, limit, project_ids)

    async def _keyword_search(
        self, query: str, limit: int, project_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        from .components.helpers import keyword_search
        return await keyword_search(self.keyword_search_service, query, limit, project_ids)

    async def _combine_results(
        self,
        vector_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        query_context: dict[str, Any],
        limit: int,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
    ) -> list["HybridSearchResult"]:
        from .components.helpers import combine_results
        return await combine_results(
            self.result_combiner,
            self.min_score,
            vector_results,
            keyword_results,
            query_context,
            limit,
            source_types,
            project_ids,
        )

    def _extract_metadata_info(self, metadata: dict) -> dict:
        from .components.metadata import extract_metadata_info
        return extract_metadata_info(self.metadata_extractor, metadata)

    def _extract_project_info(self, metadata: dict) -> dict:
        from .components.metadata import extract_project_info
        return extract_project_info(self.metadata_extractor, metadata)

    def _build_filter(self, project_ids: list[str] | None = None) -> Any:
        from .components.helpers import build_filter
        return build_filter(self.vector_search_service, project_ids)

    def suggest_facet_refinements(
        self,
        current_results: list["HybridSearchResult"],
        current_filters: list["FacetFilter"],
    ) -> list[dict[str, Any]]:
        from .components.facets import suggest_refinements as _suggest
        return _suggest(self.faceted_search_engine, current_results, current_filters)

    def generate_facets(self, results: list["HybridSearchResult"]) -> list:
        from .components.facets import generate_facets as _generate
        return _generate(self.faceted_search_engine, results)


