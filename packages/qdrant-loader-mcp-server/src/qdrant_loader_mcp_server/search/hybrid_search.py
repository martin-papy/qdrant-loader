"""Refactored hybrid search implementation using modular components."""

from datetime import datetime
from typing import Any

from openai import AsyncOpenAI
from qdrant_client import QdrantClient

from ..config import SearchConfig
from ..utils.logging import LoggingConfig
from .nlp.spacy_analyzer import SpaCyQueryAnalyzer
from .enhanced.intent_classifier import IntentClassifier, AdaptiveSearchStrategy
from .enhanced.knowledge_graph import DocumentKnowledgeGraph
from .enhanced.topic_search_chain import (
    TopicSearchChainGenerator, 
    TopicSearchChain, 
    ChainStrategy
)
from .enhanced.faceted_search import (
    FacetFilter,
    FacetedSearchResults,
    FacetedSearchEngine
)
from .enhanced.cross_document_intelligence import (
    CrossDocumentIntelligenceEngine,
    SimilarityMetric,
    ClusteringStrategy
)
from .components import (
    QueryProcessor,
    VectorSearchService,
    KeywordSearchService,
    ResultCombiner,
    MetadataExtractor,
    HybridSearchResult,
)

logger = LoggingConfig.get_logger(__name__)


class HybridSearchEngine:
    """Refactored hybrid search service using modular components."""

    def __init__(
        self,
        qdrant_client: QdrantClient,
        openai_client: AsyncOpenAI,
        collection_name: str,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.3,
        metadata_weight: float = 0.1,
        min_score: float = 0.3,
        dense_vector_name: str = "dense",
        sparse_vector_name: str = "sparse",
        alpha: float = 0.5,
        # Enhanced search parameters
        knowledge_graph: DocumentKnowledgeGraph = None,
        enable_intent_adaptation: bool = True,
        search_config: SearchConfig | None = None,
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
            dense_vector_name: Name of the dense vector field
            sparse_vector_name: Name of the sparse vector field
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
        self.dense_vector_name = dense_vector_name
        self.sparse_vector_name = sparse_vector_name
        self.alpha = alpha
        self.logger = LoggingConfig.get_logger(__name__)

        # Initialize spaCy query analyzer
        self.spacy_analyzer = SpaCyQueryAnalyzer(spacy_model="en_core_web_md")
        
        # Initialize modular components
        self.query_processor = QueryProcessor(self.spacy_analyzer)
        
        # Configure vector search service with caching if config provided
        if search_config:
            self.vector_search_service = VectorSearchService(
                qdrant_client=qdrant_client,
                openai_client=openai_client,
                collection_name=collection_name,
                min_score=min_score,
                dense_vector_name=dense_vector_name,
                sparse_vector_name=sparse_vector_name,
                alpha=alpha,
                cache_enabled=search_config.cache_enabled,
                cache_ttl=search_config.cache_ttl,
                cache_max_size=search_config.cache_max_size,
            )
        else:
            self.vector_search_service = VectorSearchService(
                qdrant_client=qdrant_client,
                openai_client=openai_client,
                collection_name=collection_name,
                min_score=min_score,
                dense_vector_name=dense_vector_name,
                sparse_vector_name=sparse_vector_name,
                alpha=alpha,
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
            self.spacy_analyzer, 
            self.knowledge_graph
        )
        self._topic_chains_initialized = False
        logger.info("Topic-driven search chaining ENABLED")
        
        # Dynamic faceted search interface
        self.faceted_search_engine = FacetedSearchEngine()
        logger.info("Dynamic faceted search interface ENABLED")
        
        # Cross-document intelligence
        self.cross_document_engine = CrossDocumentIntelligenceEngine(
            self.spacy_analyzer,
            self.knowledge_graph
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

            # Get vector search results
            vector_results = await self._vector_search(
                expanded_query, limit * 3, project_ids
            )

            # Get keyword search results  
            keyword_results = await self._keyword_search(
                query, limit * 3, project_ids
            )

            # Analyze query for context
            query_context = self._analyze_query(query)
            
            # Add intent information to query context
            if search_intent:
                query_context["search_intent"] = search_intent
                query_context["adaptive_config"] = adaptive_config

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
        initialize_from_search: bool = True
    ) -> TopicSearchChain:
        """Generate a topic-driven search chain for progressive content discovery."""
        self.logger.debug(
            "Generating topic search chain",
            query=query,
            strategy=strategy.value,
            max_links=max_links
        )
        
        try:
            # Initialize topic relationships from search results if needed
            if initialize_from_search and not self._topic_chains_initialized:
                await self._initialize_topic_relationships(query)
            
            # Generate the topic search chain
            topic_chain = self.topic_chain_generator.generate_search_chain(
                original_query=query,
                strategy=strategy,
                max_links=max_links
            )
            
            self.logger.info(
                "Topic search chain generated successfully",
                chain_length=len(topic_chain.chain_links),
                strategy=strategy.value,
                topics_covered=topic_chain.total_topics_covered,
                discovery_potential=f"{topic_chain.estimated_discovery_potential:.2f}",
                generation_time=f"{topic_chain.generation_time_ms:.1f}ms"
            )
            
            return topic_chain
            
        except Exception as e:
            self.logger.error("Error generating topic search chain", error=str(e), query=query)
            raise
    
    async def execute_topic_chain_search(
        self,
        topic_chain: TopicSearchChain,
        results_per_link: int = 3,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None
    ) -> dict[str, list[HybridSearchResult]]:
        """Execute searches for all links in a topic chain."""
        self.logger.debug(
            "Executing topic chain search",
            chain_length=len(topic_chain.chain_links),
            results_per_link=results_per_link
        )
        
        chain_results = {}
        
        try:
            # Execute search for original query
            original_results = await self.search(
                query=topic_chain.original_query,
                limit=results_per_link,
                source_types=source_types,
                project_ids=project_ids
            )
            chain_results[topic_chain.original_query] = original_results
            
            # Execute search for each chain link
            for link in topic_chain.chain_links:
                try:
                    link_results = await self.search(
                        query=link.query,
                        limit=results_per_link,
                        source_types=source_types,
                        project_ids=project_ids
                    )
                    chain_results[link.query] = link_results
                    
                    self.logger.debug(
                        "Executed chain link search",
                        query=link.query,
                        results_count=len(link_results),
                        topic_focus=link.topic_focus,
                        exploration_type=link.exploration_type
                    )
                    
                except Exception as e:
                    self.logger.warning(
                        "Failed to execute chain link search",
                        query=link.query,
                        error=str(e)
                    )
                    chain_results[link.query] = []
            
            total_results = sum(len(results) for results in chain_results.values())
            self.logger.info(
                "Topic chain search execution completed",
                total_queries=len(chain_results),
                total_results=total_results,
                original_query=topic_chain.original_query
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
                project_ids=None
            )
            
            if sample_results:
                # Initialize topic relationships from the sample results
                self.topic_chain_generator.initialize_from_results(sample_results)
                self._topic_chains_initialized = True
                
                self.logger.info(
                    "Topic relationships initialized from search results",
                    sample_query=sample_query,
                    sample_results_count=len(sample_results)
                )
            else:
                self.logger.warning(
                    "No search results available for topic relationship initialization",
                    sample_query=sample_query
                )
                
        except Exception as e:
            self.logger.error(
                "Failed to initialize topic relationships",
                error=str(e),
                sample_query=sample_query
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
                behavioral_context=behavioral_context
            )
            
            # Generate faceted results
            faceted_results = self.faceted_search_engine.generate_faceted_results(
                results=search_results,
                applied_filters=facet_filters or []
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
                search_time_ms=round(search_time, 2)
            )
            
            return faceted_results
            
        except Exception as e:
            self.logger.error("Error in faceted search", query=query, error=str(e))
            raise

    # ============================================================================
    # Cross-Document Intelligence Methods
    # ============================================================================
    
    async def analyze_document_relationships(
        self,
        documents: list[HybridSearchResult]
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
        max_similar: int = 5
    ) -> list[dict[str, Any]]:
        """Find documents similar to a target document."""
        try:
            similarity_calculator = self.cross_document_engine.similarity_calculator
            similar_docs = []
            
            for doc in documents:
                if doc == target_document:
                    continue
                    
                similarity = similarity_calculator.calculate_similarity(
                    target_document, 
                    doc, 
                    similarity_metrics
                )
                
                similar_docs.append({
                    "document_id": doc.document_id,  # ✅ ADD document_id for lazy loading
                    "document": doc,
                    "similarity_score": similarity.similarity_score,
                    "metric_scores": similarity.metric_scores,
                    "similarity_reasons": [similarity.get_display_explanation()]
                })
            
            # ✅ Add debug logging before filtering
            self.logger.debug(f"Total similar documents calculated: {len(similar_docs)}")
            if similar_docs:
                scores = [doc["similarity_score"] for doc in similar_docs]
                self.logger.debug(f"Similarity scores range: {min(scores):.3f} - {max(scores):.3f}")
                self.logger.debug(f"Similarity scores: {[f'{s:.3f}' for s in scores[:10]]}")  # First 10 scores
            
            # Sort by similarity score and return top results
            similar_docs.sort(key=lambda x: x["similarity_score"], reverse=True)
            filtered_docs = similar_docs[:max_similar]
            
            self.logger.debug(f"Returning {len(filtered_docs)} documents after limiting to max_similar={max_similar}")
            return filtered_docs
            
        except Exception as e:
            self.logger.error("Error finding similar documents", error=str(e))
            raise
    
    async def detect_document_conflicts(
        self,
        documents: list[HybridSearchResult]
    ) -> dict[str, Any]:
        """Detect conflicts between documents."""
        try:
            conflict_analysis = self.cross_document_engine.conflict_detector.detect_conflicts(documents)
            return {
                "conflicting_pairs": conflict_analysis.conflicting_pairs,
                "conflict_categories": conflict_analysis.conflict_categories,
                "resolution_suggestions": conflict_analysis.resolution_suggestions
            }
        except Exception as e:
            self.logger.error("Error detecting conflicts", error=str(e))
            raise
    
    async def find_complementary_content(
        self,
        target_document: HybridSearchResult,
        documents: list[HybridSearchResult],
        max_recommendations: int = 5
    ) -> list[dict[str, Any]]:
        """Find content that complements the target document."""
        try:
            complementary_content = self.cross_document_engine.complementary_finder.find_complementary_content(
                target_document,
                documents
            )
            recommendations = complementary_content.get_top_recommendations(max_recommendations)
            
            # Create lookup dictionary for documents by ID
            doc_lookup = {f"{doc.source_type}:{doc.source_title}": doc for doc in documents}
            
            # Enhance recommendations with full document objects
            enhanced_recommendations = []
            for rec in recommendations:
                doc_id = rec["document_id"]
                if doc_id in doc_lookup:
                    enhanced_rec = {
                        "document": doc_lookup[doc_id],
                        "relevance_score": rec["relevance_score"],
                        "recommendation_reason": rec["recommendation_reason"],
                        "strategy": rec["strategy"]
                    }
                    enhanced_recommendations.append(enhanced_rec)
            
            return enhanced_recommendations
        except Exception as e:
            self.logger.error("Error finding complementary content", error=str(e))
            raise
    
    async def cluster_documents(
        self,
        documents: list[HybridSearchResult],
        strategy: ClusteringStrategy = ClusteringStrategy.MIXED_FEATURES,
        max_clusters: int = 10,
        min_cluster_size: int = 2
    ) -> dict[str, Any]:
        """Cluster documents based on similarity and relationships."""
        try:
            clusters = self.cross_document_engine.cluster_analyzer.create_clusters(
                documents,
                strategy,
                max_clusters,
                min_cluster_size
            )
            
            # Convert to serializable format with full HybridSearchResult objects
            doc_id_to_result = {}
            for doc in documents:
                doc_id = f"{doc.source_type}:{doc.source_title}"
                doc_id_to_result[doc_id] = doc
            
            cluster_data = []
            for cluster in clusters:
                cluster_documents = []
                for doc_id in cluster.documents:
                    if doc_id in doc_id_to_result:
                        cluster_documents.append(doc_id_to_result[doc_id])
                    else:
                        # Fallback: try to find by partial matching
                        for orig_id, result in doc_id_to_result.items():
                            if doc_id in orig_id or orig_id in doc_id:
                                cluster_documents.append(result)
                                break
                
                cluster_data.append({
                    "id": cluster.cluster_id,
                    "documents": cluster_documents,
                    "centroid_topics": cluster.shared_topics,
                    "shared_entities": cluster.shared_entities,
                    "coherence_score": cluster.coherence_score,
                    "cluster_summary": cluster.cluster_description
                })
            
            return {
                "clusters": cluster_data,
                "clustering_metadata": {
                    "strategy": strategy.value,
                    "total_clusters": len(clusters),
                    "total_documents": len(documents)
                }
            }
            
        except Exception as e:
            self.logger.error("Error clustering documents", error=str(e))
            raise

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
        return await self.keyword_search_service.keyword_search(query, limit, project_ids)
    
    async def _combine_results(
        self,
        vector_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        query_context: dict[str, Any],
        limit: int,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
    ) -> list[HybridSearchResult]:
        """Backward compatibility: Delegate to result combiner."""
        # Sync min_score for consistent scoring behavior
        original_min_score = self.result_combiner.min_score
        self.result_combiner.min_score = self.min_score
        
        try:
            return await self.result_combiner.combine_results(
                vector_results, keyword_results, query_context, limit, source_types, project_ids
            )
        finally:
            # Restore original min_score
            self.result_combiner.min_score = original_min_score
    
    def _extract_metadata_info(self, metadata: dict) -> dict:
        """Backward compatibility: Delegate to metadata extractor."""
        # Extract all metadata and flatten for compatibility
        components = self.metadata_extractor.extract_all_metadata(metadata)
        flattened = {}
        
        for component_name, component in components.items():
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
            "project_id", "project_name", "project_description", "collection_name",
            # Hierarchy info  
            "parent_id", "parent_title", "breadcrumb_text", "depth", "children_count", "hierarchy_context",
            # Attachment info
            "is_attachment", "parent_document_id", "parent_document_title", "attachment_id",
            "original_filename", "file_size", "mime_type", "attachment_author", "attachment_context",
            # Section info
            "section_title", "section_type", "section_level", "section_anchor", "section_breadcrumb", "section_depth",
            # Content analysis
            "has_code_blocks", "has_tables", "has_images", "has_links", "word_count", "char_count", 
            "estimated_read_time", "paragraph_count",
            # Semantic analysis
            "entities", "topics", "key_phrases", "pos_tags",
            # Navigation context
            "previous_section", "next_section", "sibling_sections", "subsections", "document_hierarchy",
            # Chunking context
            "chunk_index", "total_chunks", "chunking_strategy",
            # Conversion info
            "original_file_type", "conversion_method", "is_excel_sheet", "is_converted",
            # Cross-reference info
            "cross_references", "topic_analysis", "content_type_context",
        ]
        
        for key in expected_keys:
            if key not in flattened:
                if key in ["is_attachment", "has_code_blocks", "has_tables", "has_images", "has_links", "is_excel_sheet", "is_converted"]:
                    flattened[key] = False
                elif key in ["entities", "topics", "key_phrases", "pos_tags", "sibling_sections", "subsections", "document_hierarchy", "cross_references"]:
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
        current_filters: list[FacetFilter]
    ) -> list[dict[str, Any]]:
        """Backward compatibility: Delegate to faceted search engine."""
        return self.faceted_search_engine.suggest_refinements(
            current_results, 
            current_filters
        )
    
    def generate_facets(
        self,
        results: list[HybridSearchResult]
    ) -> list:
        """Backward compatibility: Delegate to faceted search engine."""
        return self.faceted_search_engine.facet_generator.generate_facets(results)