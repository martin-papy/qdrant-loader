"""
Hybrid Search Engine Implementation.

This module implements the main HybridSearchEngine class that orchestrates
vector search, keyword search, intent classification, knowledge graph integration,
cross-document intelligence, and faceted search capabilities.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any
from importlib import import_module
import os

from qdrant_client import QdrantClient

from ...config import SearchConfig
from ...utils.logging import LoggingConfig
from ..components import (
    HybridSearchResult,
    KeywordSearchService,
    MetadataExtractor,
    QueryProcessor,
    ResultCombiner,
    VectorSearchService,
)
from ..enhanced.cross_document_intelligence import (
    ClusteringStrategy,
    CrossDocumentIntelligenceEngine,
    SimilarityMetric,
)
from ..enhanced.faceted_search import (
    FacetedSearchEngine,
    FacetedSearchResults,
    FacetFilter,
)
from ..enhanced.intent_classifier import AdaptiveSearchStrategy, IntentClassifier
from ..enhanced.knowledge_graph import DocumentKnowledgeGraph
from ..enhanced.topic_search_chain import (
    ChainStrategy,
    TopicSearchChain,
    TopicSearchChainGenerator,
)
from ..nlp.spacy_analyzer import SpaCyQueryAnalyzer
from .models import (
    HybridStage,
    HybridWeights,
    DEFAULT_VECTOR_WEIGHT,
    DEFAULT_KEYWORD_WEIGHT,
    DEFAULT_METADATA_WEIGHT,
    DEFAULT_MIN_SCORE,
    HybridProcessingConfig,
)
from .adapters import (
    VectorSearcherAdapter,
    KeywordSearcherAdapter,
    ResultCombinerAdapter,
)
from .pipeline import HybridPipeline
from .components.reranking import HybridReranker
from .orchestration import QueryPlanner, HybridOrchestrator
from .components.document_lookup import (
    build_document_lookup as _component_build_document_lookup,
    find_document_by_id as _component_find_document_by_id,
)

logger = LoggingConfig.get_logger(__name__)


class HybridSearchEngine:
    """Refactored hybrid search service using modular components."""

    def __init__(
        self,
        qdrant_client: QdrantClient,
        openai_client: Any,
        collection_name: str,
        vector_weight: float = DEFAULT_VECTOR_WEIGHT,
        keyword_weight: float = DEFAULT_KEYWORD_WEIGHT,
        metadata_weight: float = DEFAULT_METADATA_WEIGHT,
        min_score: float = DEFAULT_MIN_SCORE,
        # Enhanced search parameters
        knowledge_graph: DocumentKnowledgeGraph = None,
        enable_intent_adaptation: bool = True,
        search_config: SearchConfig | None = None,
        processing_config: HybridProcessingConfig | None = None,
    ):
        """Initialize the hybrid search service.

        Args:
            qdrant_client: Qdrant client instance
            openai_client: OpenAI client instance
            collection_name: Name of the Qdrant collection
            vector_weight: Weight for vector search scores (0-1)
            keyword_weight: Weight for keyword search scores (0-1)
            metadata_weight: Weight for metadata-based scoring (0-1)
            min_score: Minimum combined score threshold
            alpha: Weight for dense search (1-alpha for sparse search)
            knowledge_graph: Optional knowledge graph for integration
            enable_intent_adaptation: Enable intent-aware adaptive search
            search_config: Optional search configuration for performance optimization
        """
        self.qdrant_client = qdrant_client
        self.openai_client = openai_client
        self.collection_name = collection_name
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.metadata_weight = metadata_weight
        self.min_score = min_score
        self.logger = LoggingConfig.get_logger(__name__)

        # Initialize spaCy query analyzer
        self.spacy_analyzer = SpaCyQueryAnalyzer(spacy_model="en_core_web_md")

        # Initialize modular components
        self.query_processor = QueryProcessor(self.spacy_analyzer)

        # Configure vector search service with caching if config provided
        # Build embeddings provider using core (defer to env/file-driven config later)
        try:
            core_settings_mod = import_module("qdrant_loader_core.llm.settings")
            core_factory_mod = import_module("qdrant_loader_core.llm.factory")
            LLMSettings = getattr(core_settings_mod, "LLMSettings")
            create_provider = getattr(core_factory_mod, "create_provider")
            # For now, derive LLMSettings from environment (optional); leave empty when not available
            llm_cfg = {
                "provider": (os.getenv("LLM_PROVIDER") or "openai"),
                "base_url": os.getenv("LLM_BASE_URL"),
                "api_key": os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"),
                "models": {
                    "embeddings": os.getenv("LLM_EMBEDDING_MODEL") or "text-embedding-3-small",
                },
                "tokenizer": os.getenv("LLM_TOKENIZER") or "none",
                "request": {},
                "rate_limits": {},
                "embeddings": {},
            }
            llm_settings = LLMSettings.from_global_config({"llm": llm_cfg})
            embeddings_provider = create_provider(llm_settings)
        except Exception:
            embeddings_provider = None

        if search_config:
            self.vector_search_service = VectorSearchService(
                qdrant_client=qdrant_client,
                collection_name=collection_name,
                min_score=min_score,
                cache_enabled=search_config.cache_enabled,
                cache_ttl=search_config.cache_ttl,
                cache_max_size=search_config.cache_max_size,
                hnsw_ef=search_config.hnsw_ef,
                use_exact_search=search_config.use_exact_search,
                embeddings_provider=embeddings_provider,
                openai_client=openai_client,
            )
        else:
            self.vector_search_service = VectorSearchService(
                qdrant_client=qdrant_client,
                collection_name=collection_name,
                min_score=min_score,
                embeddings_provider=embeddings_provider,
                openai_client=openai_client,
            )

        self.keyword_search_service = KeywordSearchService(
            qdrant_client=qdrant_client,
            collection_name=collection_name,
        )

        self.result_combiner = ResultCombiner(
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
            metadata_weight=metadata_weight,
            min_score=min_score,
            spacy_analyzer=self.spacy_analyzer,
        )

        self.metadata_extractor = MetadataExtractor()

        # Optional hybrid pipeline (behavior-preserving: not used for routing yet)
        try:
            self.hybrid_pipeline = HybridPipeline(
                vector_searcher=VectorSearcherAdapter(self.vector_search_service),
                keyword_searcher=KeywordSearcherAdapter(self.keyword_search_service),
                result_combiner=ResultCombinerAdapter(self.result_combiner),
                reranker=None,
                booster=None,
                normalizer=None,
                deduplicator=None,
            )
        except Exception:
            # Keep engine functional even if pipeline wiring fails in exotic environments
            self.hybrid_pipeline = None

        # Orchestration utilities (scaffold for future extraction; no behavior change)
        self._planner = QueryPlanner()
        self._orchestrator = HybridOrchestrator()

        # Optional processing toggles
        self.processing_config = processing_config or HybridProcessingConfig()
        if self.hybrid_pipeline is not None:
            # Only wire hooks if explicitly enabled (behavior-preserving default is False for all)
            if self.processing_config.enable_reranker:
                try:
                    self.hybrid_pipeline.reranker = HybridReranker()
                except Exception:
                    self.hybrid_pipeline.reranker = None
            # The following components rely on simple default behaviors; keep None unless enabled
            if self.processing_config.enable_booster:
                from .components.boosting import ResultBooster

                self.hybrid_pipeline.booster = ResultBooster()
            if self.processing_config.enable_normalizer:
                from .components.normalization import ScoreNormalizer

                self.hybrid_pipeline.normalizer = ScoreNormalizer()
            if self.processing_config.enable_deduplicator:
                from .components.deduplication import ResultDeduplicator

                self.hybrid_pipeline.deduplicator = ResultDeduplicator()

        # Enhanced search components
        self.enable_intent_adaptation = enable_intent_adaptation
        self.knowledge_graph = knowledge_graph

        if self.enable_intent_adaptation:
            self.intent_classifier = IntentClassifier(self.spacy_analyzer)
            self.adaptive_strategy = AdaptiveSearchStrategy(self.knowledge_graph)
            logger.info("Intent-aware adaptive search ENABLED")
        else:
            self.intent_classifier = None
            self.adaptive_strategy = None
            logger.info("Intent-aware adaptive search DISABLED")

        # Topic-driven search chaining
        self.topic_chain_generator = TopicSearchChainGenerator(
            self.spacy_analyzer, self.knowledge_graph
        )
        self._topic_chains_initialized = False
        logger.info("Topic-driven search chaining ENABLED")

        # Dynamic faceted search interface
        self.faceted_search_engine = FacetedSearchEngine()
        logger.info("Dynamic faceted search interface ENABLED")

        # Cross-document intelligence
        # Build conflict settings from provided search_config (if any)
        conflict_settings = self._build_conflict_settings(search_config)

        self.cross_document_engine = CrossDocumentIntelligenceEngine(
            self.spacy_analyzer,
            self.knowledge_graph,
            self.qdrant_client,
            self.openai_client,
            self.collection_name,
            conflict_settings=conflict_settings,
        )
        logger.info("Cross-document intelligence ENABLED")

    async def search(
        self,
        query: str,
        limit: int = 5,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
        # Enhanced parameters
        session_context: dict[str, Any] | None = None,
        behavioral_context: list[str] | None = None,
    ) -> list[HybridSearchResult]:
        """Perform hybrid search combining vector and keyword search.

        Args:
            query: Search query text
            limit: Maximum number of results to return
            source_types: Optional list of source types to filter by
            project_ids: Optional list of project IDs to filter by
            session_context: Optional session context for intent classification
            behavioral_context: Optional behavioral context (previous intents)
        """
        self.logger.debug(
            "Starting hybrid search",
            query=query,
            limit=limit,
            source_types=source_types,
            project_ids=project_ids,
            intent_adaptation_enabled=self.enable_intent_adaptation,
        )

        try:
            # Intent classification and adaptive search
            search_intent = None
            adaptive_config = None

            if self.enable_intent_adaptation and self.intent_classifier:
                # Classify search intent
                search_intent = self.intent_classifier.classify_intent(
                    query, session_context, behavioral_context
                )

                # Adapt search configuration based on classified intent
                adaptive_config = self.adaptive_strategy.adapt_search(
                    search_intent, query
                )

                # Update search parameters based on adaptive configuration
                if adaptive_config:
                    original_vector_weight = self.result_combiner.vector_weight
                    original_keyword_weight = self.result_combiner.keyword_weight
                    original_min_score = self.result_combiner.min_score

                    self.result_combiner.vector_weight = adaptive_config.vector_weight
                    self.result_combiner.keyword_weight = adaptive_config.keyword_weight
                    self.result_combiner.min_score = adaptive_config.min_score_threshold

                    # Adjust limit based on intent configuration
                    limit = min(adaptive_config.max_results, limit * 2)

                    self.logger.debug(
                        "🔥 Adapted search parameters based on intent",
                        intent=search_intent.intent_type.value,
                        confidence=search_intent.confidence,
                        vector_weight=self.result_combiner.vector_weight,
                        keyword_weight=self.result_combiner.keyword_weight,
                        adjusted_limit=limit,
                        use_kg=adaptive_config.use_knowledge_graph,
                    )

            # Expand query with related terms
            expanded_query = await self._expand_query(query)

            # Apply intent-specific query expansion if available
            if adaptive_config and adaptive_config.expand_query:
                if adaptive_config.expansion_aggressiveness > 0.5:
                    expanded_query = await self._expand_query_aggressive(query)

            # Analyze query for context (must occur before pipeline combine)
            query_context = self._analyze_query(query)

            # Add intent information to query context
            if search_intent:
                query_context["search_intent"] = search_intent
                query_context["adaptive_config"] = adaptive_config

            # Decide execution path (pipeline vs legacy) without changing semantics
            plan = self._planner.make_plan(
                has_pipeline=self.hybrid_pipeline is not None,
                expanded_query=expanded_query,
            )

            # Get results via pipeline (behavior-preserving semantics)
            if plan.use_pipeline and self.hybrid_pipeline is not None:
                combined_results = await self._orchestrator.run_pipeline(
                    self.hybrid_pipeline,
                    query=query,
                    limit=limit,
                    query_context=query_context,
                    source_types=source_types,
                    project_ids=project_ids,
                    vector_query=plan.expanded_query,
                    keyword_query=query,
                )
                # Restore original params if adapted
                if adaptive_config:
                    self.result_combiner.vector_weight = original_vector_weight
                    self.result_combiner.keyword_weight = original_keyword_weight
                    self.result_combiner.min_score = original_min_score
                return combined_results

            # Fallback: legacy direct calls
            vector_results = await self._vector_search(expanded_query, limit * 3, project_ids)
            keyword_results = await self._keyword_search(query, limit * 3, project_ids)

            # Analyze query for context (already computed before pipeline); keep for clarity
            # query_context computed above

            # Combine and rerank results
            combined_results = await self._combine_results(
                vector_results,
                keyword_results,
                query_context,
                limit,
                source_types,
                project_ids,
            )

            # Restore original search parameters if they were modified
            if adaptive_config:
                self.result_combiner.vector_weight = original_vector_weight
                self.result_combiner.keyword_weight = original_keyword_weight
                self.result_combiner.min_score = original_min_score

            # 🔥 CLEAN: Return HybridSearchResult directly (no data loss!)
            return combined_results

        except Exception as e:
            self.logger.error("Error in hybrid search", error=str(e), query=query)
            raise

    # ============================================================================
    # Topic Search Chain Methods
    # ============================================================================

    async def generate_topic_search_chain(
        self,
        query: str,
        strategy: ChainStrategy = ChainStrategy.MIXED_EXPLORATION,
        max_links: int = 5,
        initialize_from_search: bool = True,
    ) -> TopicSearchChain:
        """Generate a topic-driven search chain for progressive content discovery."""
        self.logger.debug(
            "Generating topic search chain",
            query=query,
            strategy=strategy.value,
            max_links=max_links,
        )

        try:
            # Initialize topic relationships from search results if needed
            if initialize_from_search and not self._topic_chains_initialized:
                await self._initialize_topic_relationships(query)

            # Generate the topic search chain
            topic_chain = self.topic_chain_generator.generate_search_chain(
                original_query=query, strategy=strategy, max_links=max_links
            )

            self.logger.info(
                "Topic search chain generated successfully",
                chain_length=len(topic_chain.chain_links),
                strategy=strategy.value,
                topics_covered=topic_chain.total_topics_covered,
                discovery_potential=f"{topic_chain.estimated_discovery_potential:.2f}",
                generation_time=f"{topic_chain.generation_time_ms:.1f}ms",
            )

            return topic_chain

        except Exception as e:
            self.logger.error(
                "Error generating topic search chain", error=str(e), query=query
            )
            raise

    async def execute_topic_chain_search(
        self,
        topic_chain: TopicSearchChain,
        results_per_link: int = 3,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
    ) -> dict[str, list[HybridSearchResult]]:
        """Execute searches for all links in a topic chain."""
        self.logger.debug(
            "Executing topic chain search",
            chain_length=len(topic_chain.chain_links),
            results_per_link=results_per_link,
        )

        chain_results = {}

        try:
            # Execute search for original query
            original_results = await self.search(
                query=topic_chain.original_query,
                limit=results_per_link,
                source_types=source_types,
                project_ids=project_ids,
            )
            chain_results[topic_chain.original_query] = original_results

            # Execute search for each chain link
            for link in topic_chain.chain_links:
                try:
                    link_results = await self.search(
                        query=link.query,
                        limit=results_per_link,
                        source_types=source_types,
                        project_ids=project_ids,
                    )
                    chain_results[link.query] = link_results

                    self.logger.debug(
                        "Executed chain link search",
                        query=link.query,
                        results_count=len(link_results),
                        topic_focus=link.topic_focus,
                        exploration_type=link.exploration_type,
                    )

                except Exception as e:
                    self.logger.warning(
                        "Failed to execute chain link search",
                        query=link.query,
                        error=str(e),
                    )
                    chain_results[link.query] = []

            total_results = sum(len(results) for results in chain_results.values())
            self.logger.info(
                "Topic chain search execution completed",
                total_queries=len(chain_results),
                total_results=total_results,
                original_query=topic_chain.original_query,
            )

            return chain_results

        except Exception as e:
            self.logger.error("Error executing topic chain search", error=str(e))
            raise

    async def _initialize_topic_relationships(self, sample_query: str) -> None:
        """Initialize topic relationships from a sample search to bootstrap topic chaining."""
        try:
            # Perform a broad search to get diverse results for topic relationship mapping
            sample_results = await self.search(
                query=sample_query,
                limit=20,  # Get more results for better topic coverage
                source_types=None,
                project_ids=None,
            )

            if sample_results:
                # Initialize topic relationships from the sample results
                self.topic_chain_generator.initialize_from_results(sample_results)
                self._topic_chains_initialized = True

                self.logger.info(
                    "Topic relationships initialized from search results",
                    sample_query=sample_query,
                    sample_results_count=len(sample_results),
                )
            else:
                self.logger.warning(
                    "No search results available for topic relationship initialization",
                    sample_query=sample_query,
                )

        except Exception as e:
            self.logger.error(
                "Failed to initialize topic relationships",
                error=str(e),
                sample_query=sample_query,
            )

    # ============================================================================
    # Faceted Search Methods
    # ============================================================================

    async def search_with_facets(
        self,
        query: str,
        limit: int = 5,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
        facet_filters: list[FacetFilter] | None = None,
        generate_facets: bool = True,
        session_context: dict[str, Any] | None = None,
        behavioral_context: list[str] | None = None,
    ) -> FacetedSearchResults:
        """Perform faceted search with dynamic facet generation."""
        start_time = datetime.now()

        try:
            # First, perform regular search (potentially with larger limit for faceting)
            search_limit = max(limit * 2, 50) if generate_facets else limit

            search_results = await self.search(
                query=query,
                limit=search_limit,
                source_types=source_types,
                project_ids=project_ids,
                session_context=session_context,
                behavioral_context=behavioral_context,
            )

            # Generate faceted results
            faceted_results = self.faceted_search_engine.generate_faceted_results(
                results=search_results, applied_filters=facet_filters or []
            )

            # Limit final results
            faceted_results.results = faceted_results.results[:limit]
            faceted_results.filtered_count = len(faceted_results.results)

            search_time = (datetime.now() - start_time).total_seconds() * 1000

            self.logger.info(
                "Faceted search completed",
                query=query,
                total_results=faceted_results.total_results,
                filtered_results=faceted_results.filtered_count,
                facet_count=len(faceted_results.facets),
                active_filters=len(faceted_results.applied_filters),
                search_time_ms=round(search_time, 2),
            )

            return faceted_results

        except Exception as e:
            self.logger.error("Error in faceted search", query=query, error=str(e))
            raise

    # ============================================================================
    # Cross-Document Intelligence Methods
    # ============================================================================

    async def analyze_document_relationships(
        self, documents: list[HybridSearchResult]
    ) -> dict[str, Any]:
        """Perform comprehensive cross-document relationship analysis."""
        try:
            return self.cross_document_engine.analyze_document_relationships(documents)
        except Exception as e:
            self.logger.error("Error in cross-document analysis", error=str(e))
            raise

    async def find_similar_documents(
        self,
        target_document: HybridSearchResult,
        documents: list[HybridSearchResult],
        similarity_metrics: list[SimilarityMetric] = None,
        max_similar: int = 5,
    ) -> list[dict[str, Any]]:
        """Find documents similar to a target document."""
        try:
            similarity_calculator = self.cross_document_engine.similarity_calculator
            similar_docs = []

            for doc in documents:
                if doc == target_document:
                    continue

                similarity = similarity_calculator.calculate_similarity(
                    target_document, doc, similarity_metrics
                )

                similar_docs.append(
                    {
                        "document_id": doc.document_id,  # ✅ ADD document_id for lazy loading
                        "document": doc,
                        "similarity_score": similarity.similarity_score,
                        "metric_scores": similarity.metric_scores,
                        "similarity_reasons": [similarity.get_display_explanation()],
                    }
                )

            # ✅ Add debug logging before filtering
            self.logger.debug(
                f"Total similar documents calculated: {len(similar_docs)}"
            )
            if similar_docs:
                scores = [doc["similarity_score"] for doc in similar_docs]
                self.logger.debug(
                    f"Similarity scores range: {min(scores):.3f} - {max(scores):.3f}"
                )
                self.logger.debug(
                    f"Similarity scores: {[f'{s:.3f}' for s in scores[:10]]}"
                )  # First 10 scores

            # Sort by similarity score and return top results
            similar_docs.sort(key=lambda x: x["similarity_score"], reverse=True)
            filtered_docs = similar_docs[:max_similar]

            self.logger.debug(
                f"Returning {len(filtered_docs)} documents after limiting to max_similar={max_similar}"
            )
            return filtered_docs

        except Exception as e:
            self.logger.error("Error finding similar documents", error=str(e))
            raise

    async def detect_document_conflicts(
        self, documents: list[HybridSearchResult]
    ) -> dict[str, Any]:
        """Detect conflicts between documents."""
        try:
            conflict_analysis = (
                await self.cross_document_engine.conflict_detector.detect_conflicts(
                    documents
                )
            )
            return {
                "conflicting_pairs": conflict_analysis.conflicting_pairs,
                "conflict_categories": conflict_analysis.conflict_categories,
                "resolution_suggestions": conflict_analysis.resolution_suggestions,
            }
        except Exception as e:
            self.logger.error("Error detecting conflicts", error=str(e))
            raise

    async def find_complementary_content(
        self,
        target_document: HybridSearchResult,
        documents: list[HybridSearchResult],
        max_recommendations: int = 5,
    ) -> list[dict[str, Any]]:
        """Find content that complements the target document."""
        try:
            complementary_content = self.cross_document_engine.complementary_finder.find_complementary_content(
                target_document, documents
            )
            recommendations = complementary_content.get_top_recommendations(
                max_recommendations
            )

            # Build robust document lookup with multiple key strategies
            doc_lookup = self._build_document_lookup(documents, robust=True)

            # Enhance recommendations with document information in expected format
            enhanced_recommendations = []
            for rec in recommendations:
                doc_id = rec["document_id"]
                document = doc_lookup.get(doc_id)

                if document:
                    enhanced_rec = {
                        "document_id": rec["document_id"],
                        "document": document,  # Add the full document object for test compatibility
                        "title": document.get_display_title(),
                        "source_type": document.source_type,
                        "relevance_score": rec["relevance_score"],
                        "recommendation_reason": rec["recommendation_reason"],
                        "strategy": rec["strategy"],
                    }
                    enhanced_recommendations.append(enhanced_rec)
                else:
                    self.logger.warning(
                        f"Document not found in lookup for ID: {doc_id}"
                    )

            self.logger.info(
                f"Enhanced {len(enhanced_recommendations)} out of {len(recommendations)} recommendations"
            )
            return enhanced_recommendations
        except Exception as e:
            self.logger.error("Error finding complementary content", error=str(e))
            raise

    def _build_document_lookup(
        self, documents: list[HybridSearchResult], robust: bool = False
    ) -> dict[str, HybridSearchResult]:
        """Build document lookup (delegated)."""
        return _component_build_document_lookup(
            documents, robust=robust, logger=self.logger
        )

    async def cluster_documents(
        self,
        documents: list[HybridSearchResult],
        strategy: ClusteringStrategy = ClusteringStrategy.MIXED_FEATURES,
        max_clusters: int = 10,
        min_cluster_size: int = 2,
    ) -> dict[str, Any]:
        """Cluster documents based on similarity and relationships."""
        start_time = time.time()

        try:
            self.logger.info(
                f"Starting clustering with {len(documents)} documents using {strategy.value}"
            )

            clusters = self.cross_document_engine.cluster_analyzer.create_clusters(
                documents, strategy, max_clusters, min_cluster_size
            )

            # Build comprehensive document lookup with multiple strategies
            doc_lookup = self._build_document_lookup(documents, robust=True)

            cluster_data = []
            total_matched_docs = 0
            total_requested_docs = 0

            for i, cluster in enumerate(clusters):
                cluster_documents = []
                doc_ids_found = []
                doc_ids_missing = []

                total_requested_docs += len(cluster.documents)

                for doc_id in cluster.documents:
                    matched_doc = self._find_document_by_id(doc_id, doc_lookup)
                    if matched_doc:
                        cluster_documents.append(matched_doc)
                        doc_ids_found.append(doc_id)
                        total_matched_docs += 1
                    else:
                        doc_ids_missing.append(doc_id)
                        self.logger.warning(f"Document not found in lookup: {doc_id}")

                # Log cluster matching statistics
                self.logger.info(
                    f"Cluster {i}: Found {len(doc_ids_found)}/{len(cluster.documents)} documents"
                )
                if doc_ids_missing:
                    self.logger.warning(
                        f"Missing documents in cluster {i}: {doc_ids_missing[:3]}"
                    )

                # Calculate cluster quality metrics
                cluster_quality = self._calculate_cluster_quality(
                    cluster, cluster_documents
                )

                cluster_data.append(
                    {
                        "id": cluster.cluster_id,
                        "name": cluster.name,
                        "documents": cluster_documents,
                        "centroid_topics": cluster.shared_topics,
                        "shared_entities": cluster.shared_entities,
                        "coherence_score": cluster.coherence_score,
                        "cluster_summary": cluster.cluster_description,
                        "representative_doc_id": cluster.representative_doc_id,
                        "cluster_strategy": strategy.value,
                        "quality_metrics": cluster_quality,
                        "document_count": len(cluster_documents),
                        "expected_document_count": len(cluster.documents),
                    }
                )

            processing_time = (time.time() - start_time) * 1000

            # Enhanced clustering metadata
            clustering_metadata = self._build_enhanced_metadata(
                clusters,
                documents,
                strategy,
                processing_time,
                total_matched_docs,
                total_requested_docs,
            )

            # Analyze cluster relationships
            cluster_relationships = self._analyze_cluster_relationships(
                clusters, documents
            )

            self.logger.info(
                f"Clustering completed: {len(clusters)} clusters, "
                f"{total_matched_docs}/{total_requested_docs} documents matched, "
                f"{len(cluster_relationships)} relationships identified"
            )

            return {
                "clusters": cluster_data,
                "clustering_metadata": clustering_metadata,
                "cluster_relationships": cluster_relationships,
            }

        except Exception as e:
            self.logger.error("Error clustering documents", error=str(e), exc_info=True)
            raise

    def _find_document_by_id(
        self, doc_id: str, doc_lookup: dict[str, HybridSearchResult]
    ) -> HybridSearchResult | None:
        """Find document using multiple lookup strategies (delegated)."""
        return _component_find_document_by_id(doc_id, doc_lookup, logger=self.logger)

    def _calculate_cluster_quality(
        self, cluster, cluster_documents: list[HybridSearchResult]
    ) -> dict[str, Any]:
        """Calculate quality metrics for a cluster."""
        quality_metrics = {
            "document_retrieval_rate": (
                len(cluster_documents) / len(cluster.documents)
                if cluster.documents
                else 0
            ),
            "coherence_score": cluster.coherence_score,
            "entity_diversity": len(cluster.shared_entities),
            "topic_diversity": len(cluster.shared_topics),
            "has_representative": bool(cluster.representative_doc_id),
            "cluster_size_category": self._categorize_cluster_size(
                len(cluster_documents)
            ),
        }

        # Calculate content similarity if we have documents
        if len(cluster_documents) > 1:
            quality_metrics["content_similarity"] = self._estimate_content_similarity(
                cluster_documents
            )

        return quality_metrics

    def _categorize_cluster_size(self, size: int) -> str:
        from .components.cluster_quality import categorize_cluster_size
        return categorize_cluster_size(size)

    def _estimate_content_similarity(
        self, documents: list[HybridSearchResult]
    ) -> float:
        from .components.cluster_quality import estimate_content_similarity
        return estimate_content_similarity(documents)

    def _build_enhanced_metadata(
        self,
        clusters,
        documents,
        strategy,
        processing_time,
        matched_docs,
        requested_docs,
    ) -> dict[str, Any]:
        """Build enhanced clustering metadata (delegated)."""
        from .components.cluster_quality import build_enhanced_metadata

        return build_enhanced_metadata(
            clusters, documents, strategy, processing_time, matched_docs, requested_docs
        )

    def _calculate_std(self, values: list[float]) -> float:
        from .components.cluster_quality import calculate_std
        return calculate_std(values)

    def _assess_overall_quality(
        self, clusters, matched_docs: int, requested_docs: int
    ) -> float:
        from .components.cluster_quality import assess_overall_quality
        return assess_overall_quality(clusters, matched_docs, requested_docs)

    def _generate_clustering_recommendations(
        self, clusters, strategy, matched_docs: int, requested_docs: int
    ) -> dict[str, Any]:
        from .components.cluster_quality import generate_clustering_recommendations
        return generate_clustering_recommendations(
            clusters, strategy, matched_docs, requested_docs
        )

    def _analyze_cluster_relationships(
        self, clusters, documents: list[HybridSearchResult]
    ) -> list[dict[str, Any]]:
        """Analyze relationships between clusters."""
        if len(clusters) < 2:
            return []

        relationships = []
        # Use unified robust document lookup for consistency
        doc_lookup = self._build_document_lookup(documents, robust=True)

        # Analyze pairwise cluster relationships
        for i, cluster_a in enumerate(clusters):
            for _, cluster_b in enumerate(clusters[i + 1 :], i + 1):
                relationship = self._analyze_cluster_pair(
                    cluster_a, cluster_b, doc_lookup
                )
                if (
                    relationship and relationship["strength"] > 0.1
                ):  # Only include meaningful relationships
                    relationships.append(
                        {
                            "cluster_a_id": cluster_a.cluster_id,
                            "cluster_b_id": cluster_b.cluster_id,
                            "cluster_a_name": cluster_a.name,
                            "cluster_b_name": cluster_b.name,
                            "relationship_type": relationship["type"],
                            "strength": relationship["strength"],
                            "description": relationship["description"],
                            "shared_elements": relationship["shared_elements"],
                        }
                    )

        # Sort by relationship strength
        relationships.sort(key=lambda x: x["strength"], reverse=True)

        return relationships[:10]  # Return top 10 relationships

    def _analyze_cluster_pair(
        self, cluster_a, cluster_b, doc_lookup: dict
    ) -> dict[str, Any] | None:
        """Analyze the relationship between two clusters."""
        # Get cluster documents using robust lookup helper
        docs_a = []
        for doc_id in cluster_a.documents:
            doc = self._find_document_by_id(doc_id, doc_lookup)
            if doc:
                docs_a.append(doc)

        docs_b = []
        for doc_id in cluster_b.documents:
            doc = self._find_document_by_id(doc_id, doc_lookup)
            if doc:
                docs_b.append(doc)

        if not docs_a or not docs_b:
            return None

        # Analyze different relationship types
        relationships = []

        # 1. Entity overlap
        entity_relationship = self._analyze_entity_overlap(cluster_a, cluster_b)
        if entity_relationship:
            relationships.append(entity_relationship)

        # 2. Topic overlap
        topic_relationship = self._analyze_topic_overlap(cluster_a, cluster_b)
        if topic_relationship:
            relationships.append(topic_relationship)

        # 3. Source type similarity
        source_relationship = self._analyze_source_similarity(docs_a, docs_b)
        if source_relationship:
            relationships.append(source_relationship)

        # 4. Hierarchical relationship
        hierarchy_relationship = self._analyze_hierarchy_relationship(docs_a, docs_b)
        if hierarchy_relationship:
            relationships.append(hierarchy_relationship)

        # 5. Content similarity
        content_relationship = self._analyze_content_similarity(docs_a, docs_b)
        if content_relationship:
            relationships.append(content_relationship)

        # Return the strongest relationship
        if relationships:
            strongest = max(relationships, key=lambda x: x["strength"])
            return strongest

        return None

    def _analyze_entity_overlap(self, cluster_a, cluster_b) -> dict[str, Any] | None:
        from .components.relationships import analyze_entity_overlap
        return analyze_entity_overlap(cluster_a, cluster_b)

    def _analyze_topic_overlap(self, cluster_a, cluster_b) -> dict[str, Any] | None:
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

    # ============================================================================
    # Utility Methods
    # ============================================================================

    def get_adaptive_search_stats(self) -> dict[str, Any]:
        """Get adaptive search statistics for monitoring."""
        stats = {
            "intent_adaptation_enabled": self.enable_intent_adaptation,
            "has_knowledge_graph": self.knowledge_graph is not None,
        }

        if self.enable_intent_adaptation and self.intent_classifier:
            stats.update(self.intent_classifier.get_cache_stats())

        if self.adaptive_strategy:
            stats.update(self.adaptive_strategy.get_strategy_stats())

        return stats

    # ============================================================================
    # Internal Implementation Methods
    # ============================================================================

    def _build_conflict_settings(
        self, search_config: SearchConfig | None
    ) -> dict[str, Any] | None:
        """Construct conflict detection settings from ``search_config``.

        Returns None if ``search_config`` is None or if any error occurs while
        reading attributes. Default values and semantics mirror the previous
        inline implementation.
        """
        if search_config is None:
            return None
        try:
            return {
                "conflict_limit_default": getattr(
                    search_config, "conflict_limit_default", 10
                ),
                "conflict_max_pairs_total": getattr(
                    search_config, "conflict_max_pairs_total", 24
                ),
                "conflict_tier_caps": getattr(
                    search_config,
                    "conflict_tier_caps",
                    {"primary": 12, "secondary": 8, "tertiary": 4, "fallback": 0},
                ),
                "conflict_use_llm": getattr(search_config, "conflict_use_llm", True),
                "conflict_max_llm_pairs": getattr(
                    search_config, "conflict_max_llm_pairs", 2
                ),
                "conflict_llm_model": getattr(
                    search_config, "conflict_llm_model", "gpt-4o-mini"
                ),
                "conflict_llm_timeout_s": getattr(
                    search_config, "conflict_llm_timeout_s", 12.0
                ),
                "conflict_overall_timeout_s": getattr(
                    search_config, "conflict_overall_timeout_s", 9.0
                ),
                "conflict_text_window_chars": getattr(
                    search_config, "conflict_text_window_chars", 2000
                ),
                "conflict_embeddings_timeout_s": getattr(
                    search_config, "conflict_embeddings_timeout_s", 2.0
                ),
                "conflict_embeddings_max_concurrency": getattr(
                    search_config, "conflict_embeddings_max_concurrency", 5
                ),
            }
        except Exception:
            return None

    async def _get_embedding(self, text: str) -> list[float]:
        """Backward compatibility: Delegate to vector search service."""
        return await self.vector_search_service.get_embedding(text)

    async def _expand_query(self, query: str) -> str:
        """Backward compatibility: Delegate to query processor."""
        return await self.query_processor.expand_query(query)

    async def _expand_query_aggressive(self, query: str) -> str:
        """Backward compatibility: Delegate to query processor."""
        return await self.query_processor.expand_query_aggressive(query)

    def _analyze_query(self, query: str) -> dict[str, Any]:
        """Backward compatibility: Delegate to query processor."""
        return self.query_processor.analyze_query(query)

    async def _vector_search(
        self, query: str, limit: int, project_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Backward compatibility: Delegate to vector search service."""
        return await self.vector_search_service.vector_search(query, limit, project_ids)

    async def _keyword_search(
        self, query: str, limit: int, project_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Backward compatibility: Delegate to keyword search service."""
        return await self.keyword_search_service.keyword_search(
            query, limit, project_ids
        )

    async def _combine_results(
        self,
        vector_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        query_context: dict[str, Any],
        limit: int,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
    ) -> list[HybridSearchResult]:
        """Backward compatibility: Delegate to result combiner without overriding adaptive min_score."""
        # Ensure combiner uses current engine min_score unless combiner already set to lower value explicitly
        if self.result_combiner.min_score is None or self.result_combiner.min_score > self.min_score:
            self.result_combiner.min_score = self.min_score
        return await self.result_combiner.combine_results(
            vector_results,
            keyword_results,
            query_context,
            limit,
            source_types,
            project_ids,
        )

    def _extract_metadata_info(self, metadata: dict) -> dict:
        """Backward compatibility: Delegate to metadata extractor."""
        # Extract all metadata and flatten for compatibility
        components = self.metadata_extractor.extract_all_metadata(metadata)
        flattened = {}

        for _component_name, component in components.items():
            if component is None:
                continue

            if hasattr(component, "__dict__"):
                # Convert dataclass to dict and flatten
                component_dict = component.__dict__
                for key, value in component_dict.items():
                    flattened[key] = value
            elif isinstance(component, dict):
                flattened.update(component)

        # Ensure all expected keys are present with None defaults for test compatibility
        expected_keys = [
            # Project info
            "project_id",
            "project_name",
            "project_description",
            "collection_name",
            # Hierarchy info
            "parent_id",
            "parent_title",
            "breadcrumb_text",
            "depth",
            "children_count",
            "hierarchy_context",
            # Attachment info
            "is_attachment",
            "parent_document_id",
            "parent_document_title",
            "attachment_id",
            "original_filename",
            "file_size",
            "mime_type",
            "attachment_author",
            "attachment_context",
            # Section info
            "section_title",
            "section_type",
            "section_level",
            "section_anchor",
            "section_breadcrumb",
            "section_depth",
            # Content analysis
            "has_code_blocks",
            "has_tables",
            "has_images",
            "has_links",
            "word_count",
            "char_count",
            "estimated_read_time",
            "paragraph_count",
            # Semantic analysis
            "entities",
            "topics",
            "key_phrases",
            "pos_tags",
            # Navigation context
            "previous_section",
            "next_section",
            "sibling_sections",
            "subsections",
            "document_hierarchy",
            # Chunking context
            "chunk_index",
            "total_chunks",
            "chunking_strategy",
            # Conversion info
            "original_file_type",
            "conversion_method",
            "is_excel_sheet",
            "is_converted",
            # Cross-reference info
            "cross_references",
            "topic_analysis",
            "content_type_context",
        ]

        for key in expected_keys:
            if key not in flattened:
                if key in [
                    "is_attachment",
                    "has_code_blocks",
                    "has_tables",
                    "has_images",
                    "has_links",
                    "is_excel_sheet",
                    "is_converted",
                ]:
                    flattened[key] = False
                elif key in [
                    "entities",
                    "topics",
                    "key_phrases",
                    "pos_tags",
                    "sibling_sections",
                    "subsections",
                    "document_hierarchy",
                    "cross_references",
                ]:
                    flattened[key] = []
                else:
                    flattened[key] = None

        return flattened

    def _extract_project_info(self, metadata: dict) -> dict:
        """Backward compatibility: Delegate to metadata extractor."""
        project_info = self.metadata_extractor.extract_project_info(metadata)
        if project_info:
            return project_info.__dict__
        return {
            "project_id": None,
            "project_name": None,
            "project_description": None,
            "collection_name": None,
        }

    def _build_filter(
        self, project_ids: list[str] | None = None
    ) -> Any:  # Return type from qdrant_client.http.models.Filter
        """Backward compatibility: Delegate to vector search service."""
        return self.vector_search_service._build_filter(project_ids)

    def suggest_facet_refinements(
        self,
        current_results: list[HybridSearchResult],
        current_filters: list[FacetFilter],
    ) -> list[dict[str, Any]]:
        """Backward compatibility: Delegate to faceted search engine."""
        return self.faceted_search_engine.suggest_refinements(
            current_results, current_filters
        )

    def generate_facets(self, results: list[HybridSearchResult]) -> list:
        """Backward compatibility: Delegate to faceted search engine."""
        return self.faceted_search_engine.facet_generator.generate_facets(results)
