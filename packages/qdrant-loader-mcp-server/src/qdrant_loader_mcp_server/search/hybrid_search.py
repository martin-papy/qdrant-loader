"""Hybrid search implementation combining vector and keyword search."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models
from rank_bm25 import BM25Okapi

from ..utils.logging import LoggingConfig
from .models import SearchResult
from .nlp.spacy_analyzer import SpaCyQueryAnalyzer
# 🔥 NEW: Phase 2.2 Intent-Aware Adaptive Search
from .enhanced.intent_classifier import IntentClassifier, AdaptiveSearchStrategy, SearchIntent
from .enhanced.knowledge_graph import DocumentKnowledgeGraph
# 🔥 NEW: Phase 1.2 Topic-Driven Search Chaining  
from .enhanced.topic_search_chain import (
    TopicSearchChainGenerator, 
    TopicSearchChain, 
    ChainStrategy,
    TopicChainLink
)
# 🔥 NEW: Phase 1.3 Dynamic Faceted Search Interface
from .enhanced.faceted_search import (
    FacetType,
    FacetFilter,
    FacetedSearchResults,
    DynamicFacetGenerator,
    FacetedSearchEngine
)
# 🔥 NEW: Phase 2.3 Cross-Document Intelligence
from .enhanced.cross_document_intelligence import (
    CrossDocumentIntelligenceEngine,
    SimilarityMetric,
    ClusteringStrategy,
    DocumentSimilarityCalculator
)

logger = LoggingConfig.get_logger(__name__)


@dataclass
class HybridSearchResult:
    """Container for hybrid search results with comprehensive metadata."""

    score: float
    text: str
    source_type: str
    source_title: str
    source_url: str | None = None
    file_path: str | None = None
    repo_name: str | None = None
    vector_score: float = 0.0
    keyword_score: float = 0.0

    # Project information (for multi-project support)
    project_id: str | None = None
    project_name: str | None = None
    project_description: str | None = None
    collection_name: str | None = None

    # Hierarchy information (primarily for Confluence)
    parent_id: str | None = None
    parent_title: str | None = None
    breadcrumb_text: str | None = None
    depth: int | None = None
    children_count: int | None = None
    hierarchy_context: str | None = None

    # Attachment information (for files attached to documents)
    is_attachment: bool = False
    parent_document_id: str | None = None
    parent_document_title: str | None = None
    attachment_id: str | None = None
    original_filename: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    attachment_author: str | None = None
    attachment_context: str | None = None

    # 🔥 NEW: Section-level intelligence
    section_title: str | None = None
    section_type: str | None = None  # e.g., "h1", "h2", "content"
    section_level: int | None = None
    section_anchor: str | None = None
    section_breadcrumb: str | None = None
    section_depth: int | None = None

    # 🔥 NEW: Content analysis
    has_code_blocks: bool = False
    has_tables: bool = False
    has_images: bool = False
    has_links: bool = False
    word_count: int | None = None
    char_count: int | None = None
    estimated_read_time: int | None = None  # minutes
    paragraph_count: int | None = None

    # 🔥 NEW: Semantic analysis (NLP results)
    entities: list[dict | str] = None
    topics: list[dict | str] = None
    key_phrases: list[dict | str] = None
    pos_tags: list[dict] = None

    # 🔥 NEW: Navigation context
    previous_section: str | None = None
    next_section: str | None = None
    sibling_sections: list[str] = None
    subsections: list[str] = None
    document_hierarchy: list[str] = None

    # 🔥 NEW: Chunking context
    chunk_index: int | None = None
    total_chunks: int | None = None
    chunking_strategy: str | None = None

    # 🔥 NEW: File conversion intelligence
    original_file_type: str | None = None
    conversion_method: str | None = None
    is_excel_sheet: bool = False
    is_converted: bool = False

    # 🔥 NEW: Cross-references and enhanced context
    cross_references: list[dict] = None
    topic_analysis: dict | None = None
    content_type_context: str | None = None  # Human-readable content description

    def __post_init__(self):
        """Initialize default values for list fields."""
        if self.entities is None:
            self.entities = []
        if self.topics is None:
            self.topics = []
        if self.key_phrases is None:
            self.key_phrases = []
        if self.pos_tags is None:
            self.pos_tags = []
        if self.sibling_sections is None:
            self.sibling_sections = []
        if self.subsections is None:
            self.subsections = []
        if self.document_hierarchy is None:
            self.document_hierarchy = []
        if self.cross_references is None:
            self.cross_references = []


class HybridSearchEngine:
    """Service for hybrid search combining vector and keyword search."""

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
        # 🔥 NEW: Phase 2.2 parameters
        knowledge_graph: DocumentKnowledgeGraph = None,
        enable_intent_adaptation: bool = True,
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
            knowledge_graph: Optional knowledge graph for Phase 2.1 integration
            enable_intent_adaptation: Enable Phase 2.2 intent-aware adaptive search

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

        # 🔥 NEW: Initialize spaCy query analyzer for intelligent query processing
        self.spacy_analyzer = SpaCyQueryAnalyzer(spacy_model="en_core_web_md")
        
        # 🔥 NEW: Phase 2.2 Intent-Aware Adaptive Search
        self.enable_intent_adaptation = enable_intent_adaptation
        self.knowledge_graph = knowledge_graph
        
        if self.enable_intent_adaptation:
            self.intent_classifier = IntentClassifier(self.spacy_analyzer)
            self.adaptive_strategy = AdaptiveSearchStrategy(self.knowledge_graph)
            logger.info("🔥 Phase 2.2: Intent-aware adaptive search ENABLED")
        else:
            self.intent_classifier = None
            self.adaptive_strategy = None
            logger.info("Intent-aware adaptive search DISABLED")
        
        # 🔥 NEW: Phase 1.2 Topic-Driven Search Chaining
        self.topic_chain_generator = TopicSearchChainGenerator(
            self.spacy_analyzer, 
            self.knowledge_graph
        )
        self._topic_chains_initialized = False
        logger.info("🔥 Phase 1.2: Topic-driven search chaining ENABLED")
        
        # 🔥 NEW: Phase 1.3 Dynamic Faceted Search Interface
        self.faceted_search_engine = FacetedSearchEngine()
        logger.info("🔥 Phase 1.3: Dynamic faceted search interface ENABLED")
        
        # Cross-Document Intelligence (always enabled)
        self.cross_document_engine = CrossDocumentIntelligenceEngine(
            self.spacy_analyzer,
            self.knowledge_graph
        )
        logger.info("Cross-document intelligence ENABLED")

        # Enhanced query expansions leveraging spaCy semantic understanding
        self.query_expansions = {
            "product requirements": [
                "PRD",
                "requirements document",
                "product specification",
            ],
            "requirements": ["specs", "requirements document", "features"],
            "architecture": ["system design", "technical architecture"],
            "UI": ["user interface", "frontend", "design"],
            "API": ["interface", "endpoints", "REST"],
            "database": ["DB", "data storage", "persistence"],
            "security": ["auth", "authentication", "authorization"],
            # 🔥 NEW: Content-type aware expansions
            "code": ["implementation", "function", "method", "class"],
            "documentation": ["docs", "guide", "manual", "instructions"],
            "config": ["configuration", "settings", "setup"],
            "table": ["data", "spreadsheet", "excel", "csv"],
            "image": ["screenshot", "diagram", "chart", "visual"],
            "link": ["reference", "url", "external", "connection"],
        }

    async def _expand_query(self, query: str) -> str:
        """🔥 ENHANCED: Expand query with spaCy semantic understanding and related terms."""
        # Use spaCy analyzer for intelligent query expansion
        try:
            query_analysis = self.spacy_analyzer.analyze_query_semantic(query)
            
            # Start with original query
            expanded_query = query
            
            # Add semantic keywords for broader matching
            if query_analysis.semantic_keywords:
                # Add top semantic keywords
                semantic_terms = " ".join(query_analysis.semantic_keywords[:3])
                expanded_query = f"{query} {semantic_terms}"
            
            # Add main concepts for concept-based expansion
            if query_analysis.main_concepts:
                concept_terms = " ".join(query_analysis.main_concepts[:2])
                expanded_query = f"{expanded_query} {concept_terms}"
            
            # Legacy expansion logic as fallback
            lower_query = query.lower()
            for key, expansions in self.query_expansions.items():
                if key.lower() in lower_query:
                    expansion_terms = " ".join(expansions[:2])  # Limit to avoid over-expansion
                    expanded_query = f"{expanded_query} {expansion_terms}"
                    break
            
            if expanded_query != query:
                self.logger.debug(
                    "🔥 spaCy-enhanced query expansion",
                    original_query=query,
                    expanded_query=expanded_query,
                    semantic_keywords=query_analysis.semantic_keywords[:3],
                    main_concepts=query_analysis.main_concepts[:2],
                )
            
            return expanded_query
            
        except Exception as e:
            self.logger.warning(f"spaCy expansion failed, using fallback: {e}")
            # Fallback to original expansion logic
            expanded_query = query
            lower_query = query.lower()
            
            for key, expansions in self.query_expansions.items():
                if key.lower() in lower_query:
                    expansion_terms = " ".join(expansions)
                    expanded_query = f"{query} {expansion_terms}"
                    self.logger.debug(
                        "Expanded query (fallback)",
                        original_query=query,
                        expanded_query=expanded_query,
                    )
                    break
            
            return expanded_query

    async def _expand_query_aggressive(self, query: str) -> str:
        """🔥 NEW: More aggressive query expansion for exploratory searches."""
        try:
            query_analysis = self.spacy_analyzer.analyze_query_semantic(query)
            
            # Start with original query
            expanded_query = query
            
            # Add more semantic keywords (increased from 3 to 5)
            if query_analysis.semantic_keywords:
                semantic_terms = " ".join(query_analysis.semantic_keywords[:5])
                expanded_query = f"{query} {semantic_terms}"
            
            # Add more main concepts (increased from 2 to 4)
            if query_analysis.main_concepts:
                concept_terms = " ".join(query_analysis.main_concepts[:4])
                expanded_query = f"{expanded_query} {concept_terms}"
            
            # Add entity-based expansion
            if query_analysis.entities:
                entity_terms = " ".join([ent[0] for ent in query_analysis.entities[:3]])
                expanded_query = f"{expanded_query} {entity_terms}"
            
            # Apply multiple legacy expansions for exploration
            lower_query = query.lower()
            expansion_count = 0
            for key, expansions in self.query_expansions.items():
                if key.lower() in lower_query and expansion_count < 3:  # Max 3 expansions
                    expansion_terms = " ".join(expansions[:3])
                    expanded_query = f"{expanded_query} {expansion_terms}"
                    expansion_count += 1
            
            self.logger.debug(
                "🔥 Aggressive query expansion for exploration",
                original_query=query,
                expanded_query=expanded_query,
                expansion_ratio=len(expanded_query.split()) / len(query.split()),
            )
            
            return expanded_query
            
        except Exception as e:
            self.logger.warning(f"Aggressive expansion failed, using standard: {e}")
            return await self._expand_query(query)

    async def _get_embedding(self, text: str) -> list[float]:
        """Get embedding for text using OpenAI."""
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            self.logger.error("Failed to get embedding", error=str(e))
            raise

    async def search(
        self,
        query: str,
        limit: int = 5,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
        # 🔥 NEW: Phase 2.2 parameters
        session_context: dict[str, Any] | None = None,
        behavioral_context: list[str] | None = None,
    ) -> list[SearchResult]:
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
            # 🔥 NEW: Phase 2.2 Intent Classification and Adaptive Search
            search_intent = None
            adaptive_config = None
            
            if self.enable_intent_adaptation and self.intent_classifier:
                # Classify search intent using comprehensive spaCy analysis
                search_intent = self.intent_classifier.classify_intent(
                    query, session_context, behavioral_context
                )
                
                # Adapt search configuration based on classified intent
                adaptive_config = self.adaptive_strategy.adapt_search(
                    search_intent, query
                )
                
                # Update search parameters based on adaptive configuration
                if adaptive_config:
                    # Override weights based on intent
                    original_vector_weight = self.vector_weight
                    original_keyword_weight = self.keyword_weight
                    original_min_score = self.min_score
                    
                    self.vector_weight = adaptive_config.vector_weight
                    self.keyword_weight = adaptive_config.keyword_weight
                    self.min_score = adaptive_config.min_score_threshold
                    
                    # Adjust limit based on intent configuration
                    limit = min(adaptive_config.max_results, limit * 2)
                    
                    self.logger.debug(
                        "🔥 Adapted search parameters based on intent",
                        intent=search_intent.intent_type.value,
                        confidence=search_intent.confidence,
                        vector_weight=self.vector_weight,
                        keyword_weight=self.keyword_weight,
                        adjusted_limit=limit,
                        use_kg=adaptive_config.use_knowledge_graph,
                    )

            # Expand query with related terms (now potentially adapted)
            expanded_query = await self._expand_query(query)
            
            # Apply intent-specific query expansion if available
            if adaptive_config and adaptive_config.expand_query:
                if adaptive_config.expansion_aggressiveness > 0.5:
                    # More aggressive expansion for exploratory queries
                    expanded_query = await self._expand_query_aggressive(query)

            # Get vector search results
            vector_results = await self._vector_search(
                expanded_query, limit * 3, project_ids
            )

            # Get keyword search results  
            keyword_results = await self._keyword_search(query, limit * 3, project_ids)

            # Analyze query for context
            query_context = self._analyze_query(query)
            
            # 🔥 NEW: Add intent information to query context
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
            
            # 🔥 NEW: Restore original search parameters if they were modified
            if adaptive_config:
                self.vector_weight = original_vector_weight
                self.keyword_weight = original_keyword_weight  
                self.min_score = original_min_score

            # Convert to SearchResult objects
            return [
                SearchResult(
                    score=result.score,
                    text=result.text,
                    source_type=result.source_type,
                    source_title=result.source_title,
                    source_url=result.source_url,
                    file_path=result.file_path,
                    repo_name=result.repo_name,
                    
                    # Project information
                    project_id=result.project_id,
                    project_name=result.project_name,
                    project_description=result.project_description,
                    collection_name=result.collection_name,
                    
                    # Basic hierarchy and attachment (existing)
                    parent_id=result.parent_id,
                    parent_title=result.parent_title,
                    breadcrumb_text=result.breadcrumb_text,
                    depth=result.depth,
                    children_count=result.children_count,
                    hierarchy_context=result.hierarchy_context,
                    is_attachment=result.is_attachment,
                    parent_document_id=result.parent_document_id,
                    parent_document_title=result.parent_document_title,
                    attachment_id=result.attachment_id,
                    original_filename=result.original_filename,
                    file_size=result.file_size,
                    mime_type=result.mime_type,
                    attachment_author=result.attachment_author,
                    attachment_context=result.attachment_context,
                    
                    # 🔥 NEW: Section-level intelligence
                    section_title=result.section_title,
                    section_type=result.section_type,
                    section_level=result.section_level,
                    section_anchor=result.section_anchor,
                    section_breadcrumb=result.section_breadcrumb,
                    section_depth=result.section_depth,
                    
                    # 🔥 NEW: Content analysis
                    has_code_blocks=result.has_code_blocks,
                    has_tables=result.has_tables,
                    has_images=result.has_images,
                    has_links=result.has_links,
                    word_count=result.word_count,
                    char_count=result.char_count,
                    estimated_read_time=result.estimated_read_time,
                    paragraph_count=result.paragraph_count,
                    
                    # 🔥 NEW: Semantic analysis
                    entities=result.entities,
                    topics=result.topics,
                    key_phrases=result.key_phrases,
                    pos_tags=result.pos_tags,
                    
                    # 🔥 NEW: Navigation context
                    previous_section=result.previous_section,
                    next_section=result.next_section,
                    sibling_sections=result.sibling_sections,
                    subsections=result.subsections,
                    document_hierarchy=result.document_hierarchy,
                    
                    # 🔥 NEW: Chunking context
                    chunk_index=result.chunk_index,
                    total_chunks=result.total_chunks,
                    chunking_strategy=result.chunking_strategy,
                    
                    # 🔥 NEW: File conversion intelligence
                    original_file_type=result.original_file_type,
                    conversion_method=result.conversion_method,
                    is_excel_sheet=result.is_excel_sheet,
                    is_converted=result.is_converted,
                    
                    # 🔥 NEW: Cross-references and enhanced context
                    cross_references=result.cross_references,
                    topic_analysis=result.topic_analysis,
                    content_type_context=result.content_type_context,
                )
                for result in combined_results
            ]

        except Exception as e:
            self.logger.error("Error in hybrid search", error=str(e), query=query)
            raise
    
    async def generate_topic_search_chain(
        self,
        query: str,
        strategy: ChainStrategy = ChainStrategy.MIXED_EXPLORATION,
        max_links: int = 5,
        initialize_from_search: bool = True
    ) -> TopicSearchChain:
        """🔥 NEW: Generate a topic-driven search chain for progressive content discovery.
        
        Args:
            query: Original search query
            strategy: Strategy for chain generation
            max_links: Maximum number of links in the chain
            initialize_from_search: Whether to initialize topic relationships from search results
            
        Returns:
            TopicSearchChain with progressive queries for exploration
        """
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
    ) -> dict[str, list[SearchResult]]:
        """🔥 NEW: Execute searches for all links in a topic chain.
        
        Args:
            topic_chain: The topic search chain to execute
            results_per_link: Number of results to return per chain link
            source_types: Optional source type filters
            project_ids: Optional project ID filters
            
        Returns:
            Dictionary mapping chain link queries to their search results
        """
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
            # Don't raise - topic chaining can still work with limited relationships

    def _analyze_query(self, query: str) -> dict[str, Any]:
        """🔥 ENHANCED: Analyze query using spaCy NLP instead of regex patterns."""
        try:
            # Use spaCy analyzer for comprehensive query analysis
            query_analysis = self.spacy_analyzer.analyze_query_semantic(query)
            
            # Create enhanced query context using spaCy analysis
            context = {
                # Basic query characteristics
                "is_question": query_analysis.is_question,
                "is_broad": len(query.split()) < 5,
                "is_specific": len(query.split()) > 7,
                "is_technical": query_analysis.is_technical,
                "complexity_score": query_analysis.complexity_score,
                
                # spaCy-powered intent detection
                "probable_intent": query_analysis.intent_signals.get("primary_intent", "informational"),
                "intent_confidence": query_analysis.intent_signals.get("confidence", 0.0),
                "linguistic_features": query_analysis.intent_signals.get("linguistic_features", {}),
                
                # Enhanced keyword extraction using spaCy
                "keywords": query_analysis.semantic_keywords,
                "entities": [entity[0] for entity in query_analysis.entities],  # Extract entity text
                "entity_types": [entity[1] for entity in query_analysis.entities],  # Extract entity labels
                "main_concepts": query_analysis.main_concepts,
                "pos_patterns": query_analysis.pos_patterns,
                
                # Store query analysis for later use
                "spacy_analysis": query_analysis,
            }
            
            # Enhanced content type preference detection using spaCy
            semantic_keywords_set = set(query_analysis.semantic_keywords)
            
            # Code preference detection
            code_keywords = {"code", "function", "implementation", "script", "method", "class", "api"}
            if semantic_keywords_set.intersection(code_keywords):
                context["prefers_code"] = True
            
            # Table/data preference detection  
            table_keywords = {"table", "data", "excel", "spreadsheet", "csv", "sheet"}
            if semantic_keywords_set.intersection(table_keywords):
                context["prefers_tables"] = True
            
            # Image preference detection
            image_keywords = {"image", "diagram", "screenshot", "visual", "chart", "graph"}
            if semantic_keywords_set.intersection(image_keywords):
                context["prefers_images"] = True
            
            # Documentation preference detection
            doc_keywords = {"documentation", "doc", "guide", "manual", "instruction", "help"}
            if semantic_keywords_set.intersection(doc_keywords):
                context["prefers_docs"] = True
            
            self.logger.debug(
                "🔥 spaCy query analysis completed",
                intent=context["probable_intent"],
                confidence=context["intent_confidence"],
                entities_found=len(query_analysis.entities),
                keywords_extracted=len(query_analysis.semantic_keywords),
                processing_time_ms=query_analysis.processing_time_ms,
            )
            
            return context
            
        except Exception as e:
            self.logger.warning(f"spaCy analysis failed, using fallback: {e}")
            # Fallback to original regex-based analysis
            return self._analyze_query_fallback(query)
    
    def _analyze_query_fallback(self, query: str) -> dict[str, Any]:
        """Fallback query analysis using original regex patterns."""
        context = {
            "is_question": bool(
                re.search(r"\?|what|how|why|when|who|where", query.lower())
            ),
            "is_broad": len(query.split()) < 5,
            "is_specific": len(query.split()) > 7,
            "probable_intent": "informational",
            "keywords": [
                word.lower() for word in re.findall(r"\b\w{3,}\b", query.lower())
            ],
        }

        lower_query = query.lower()
        if "how to" in lower_query or "steps" in lower_query:
            context["probable_intent"] = "procedural"
        elif any(
            term in lower_query for term in ["requirements", "prd", "specification"]
        ):
            context["probable_intent"] = "requirements"
        elif any(
            term in lower_query for term in ["architecture", "design", "structure"]
        ):
            context["probable_intent"] = "architecture"

        # Content type preferences (original logic)
        if any(term in lower_query for term in ["code", "function", "implementation", "script"]):
            context["prefers_code"] = True
        if any(term in lower_query for term in ["table", "data", "excel", "spreadsheet"]):
            context["prefers_tables"] = True
        if any(term in lower_query for term in ["image", "diagram", "screenshot", "visual"]):
            context["prefers_images"] = True
        if any(term in lower_query for term in ["documentation", "docs", "guide", "manual"]):
            context["prefers_docs"] = True

        return context

    def _boost_score_with_metadata(
        self, base_score: float, metadata_info: dict, query_context: dict
    ) -> float:
        """🔥 ENHANCED: Boost search scores using spaCy semantic analysis and metadata context."""
        boosted_score = base_score
        boost_factor = 0.0

        # 🔥 NEW: Phase 2.2 Intent-Aware Boosting
        search_intent = query_context.get("search_intent")
        adaptive_config = query_context.get("adaptive_config")
        
        if search_intent and adaptive_config:
            # Apply intent-specific ranking boosts
            ranking_boosts = adaptive_config.ranking_boosts
            source_type_preferences = adaptive_config.source_type_preferences
            
            # Source type preference boosting
            source_type = metadata_info.get("source_type", "")
            if source_type in source_type_preferences:
                source_boost = (source_type_preferences[source_type] - 1.0) * 0.2
                boost_factor += source_boost
                
            # Content type boosting from ranking_boosts
            for boost_key, boost_value in ranking_boosts.items():
                if boost_key == "section_type" and isinstance(boost_value, dict):
                    section_type = metadata_info.get("section_type", "")
                    if section_type in boost_value:
                        section_boost = (boost_value[section_type] - 1.0) * 0.15
                        boost_factor += section_boost
                elif boost_key == "source_type" and isinstance(boost_value, dict):
                    if source_type in boost_value:
                        source_boost = (boost_value[source_type] - 1.0) * 0.15
                        boost_factor += source_boost
                elif boost_key in metadata_info and metadata_info[boost_key]:
                    # Boolean metadata boosting (e.g., has_money_entities, has_org_entities)
                    if isinstance(boost_value, (int, float)):
                        bool_boost = (boost_value - 1.0) * 0.1
                        boost_factor += bool_boost
            
            # Intent-specific confidence boosting
            confidence_boost = search_intent.confidence * 0.05  # Up to 5% boost for high confidence
            boost_factor += confidence_boost
            
            self.logger.debug(
                "🔥 Applied intent-aware boosting",
                intent=search_intent.intent_type.value,
                confidence=search_intent.confidence,
                source_type=source_type,
                total_intent_boost=boost_factor,
            )

        # 🔥 Content type relevance boosting (enhanced)
        if query_context.get("prefers_code") and metadata_info.get("has_code_blocks"):
            boost_factor += 0.15
        
        if query_context.get("prefers_tables") and metadata_info.get("has_tables"):
            boost_factor += 0.12
            
        if query_context.get("prefers_images") and metadata_info.get("has_images"):
            boost_factor += 0.10
            
        if query_context.get("prefers_docs") and not metadata_info.get("has_code_blocks"):
            boost_factor += 0.08

        # 🔥 Section level relevance (higher level = more important)
        section_level = metadata_info.get("section_level")
        if section_level is not None:
            if section_level <= 2:  # H1, H2 are more important
                boost_factor += 0.10
            elif section_level <= 3:  # H3 moderately important  
                boost_factor += 0.05

        # 🔥 Content quality indicators
        word_count = metadata_info.get("word_count") or 0
        if word_count > 100:  # Substantial content
            boost_factor += 0.05
        if word_count > 500:  # Very detailed content
            boost_factor += 0.05

        # 🔥 Converted file boosting (often contains rich content)
        if metadata_info.get("is_converted") and metadata_info.get("original_file_type") in ["docx", "xlsx", "pdf"]:
            boost_factor += 0.08

        # 🔥 Excel sheet specific boosting for data queries
        if metadata_info.get("is_excel_sheet") and any(
            term in " ".join(query_context.get("keywords", [])) 
            for term in ["data", "table", "sheet", "excel", "csv"]
        ):
            boost_factor += 0.12

        # 🔥 NEW: spaCy-powered semantic entity relevance
        if "spacy_analysis" in query_context:
            spacy_analysis = query_context["spacy_analysis"]
            
            # Enhanced entity matching using spaCy similarity
            entities = metadata_info.get("entities", [])
            if entities and spacy_analysis.entities:
                max_entity_similarity = 0.0
                for entity in entities:
                    entity_text = entity if isinstance(entity, str) else entity.get("text", str(entity))
                    similarity = self.spacy_analyzer.semantic_similarity_matching(
                        spacy_analysis, entity_text
                    )
                    max_entity_similarity = max(max_entity_similarity, similarity)
                
                # Apply semantic entity boost based on similarity
                if max_entity_similarity > 0.6:  # High similarity
                    boost_factor += 0.15
                elif max_entity_similarity > 0.4:  # Medium similarity
                    boost_factor += 0.10
                elif max_entity_similarity > 0.2:  # Low similarity
                    boost_factor += 0.05
            
            # Enhanced topic relevance using spaCy
            topics = metadata_info.get("topics", [])
            if topics and spacy_analysis.main_concepts:
                max_topic_similarity = 0.0
                for topic in topics:
                    topic_text = topic if isinstance(topic, str) else topic.get("text", str(topic))
                    for concept in spacy_analysis.main_concepts:
                        similarity = self.spacy_analyzer.semantic_similarity_matching(
                            spacy_analysis, f"{topic_text} {concept}"
                        )
                        max_topic_similarity = max(max_topic_similarity, similarity)
                
                # Apply semantic topic boost
                if max_topic_similarity > 0.5:
                    boost_factor += 0.12
                elif max_topic_similarity > 0.3:
                    boost_factor += 0.08
        
        else:
            # Fallback to original entity/topic matching
            entities = metadata_info.get("entities", [])
            if entities:
                query_keywords = set(query_context.get("keywords", []))
                entity_texts = set()
                for entity in entities:
                    if isinstance(entity, str):
                        entity_texts.add(entity.lower())
                    elif isinstance(entity, dict):
                        if "text" in entity:
                            entity_texts.add(str(entity["text"]).lower())
                        elif "entity" in entity:
                            entity_texts.add(str(entity["entity"]).lower())
                        else:
                            entity_texts.add(str(entity).lower())
                
                if query_keywords.intersection(entity_texts):
                    boost_factor += 0.10

            # Original topic relevance
            topics = metadata_info.get("topics", [])
            if topics:
                query_keywords = set(query_context.get("keywords", []))
                topic_texts = set()
                for topic in topics:
                    if isinstance(topic, str):
                        topic_texts.add(topic.lower())
                    elif isinstance(topic, dict):
                        if "text" in topic:
                            topic_texts.add(str(topic["text"]).lower())
                        elif "topic" in topic:
                            topic_texts.add(str(topic["topic"]).lower())
                        else:
                            topic_texts.add(str(topic).lower())
                
                if query_keywords.intersection(topic_texts):
                    boost_factor += 0.08

        # Apply boost (cap at reasonable maximum)
        boost_factor = min(boost_factor, 0.5)  # Maximum 50% boost (increased from 40%)
        return boosted_score * (1 + boost_factor)

    async def _vector_search(
        self, query: str, limit: int, project_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Perform vector search using Qdrant."""
        query_embedding = await self._get_embedding(query)

        search_params = models.SearchParams(hnsw_ef=128, exact=False)

        results = await self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=self.min_score,
            search_params=search_params,
            query_filter=self._build_filter(project_ids),
        )

        return [
            {
                "score": hit.score,
                "text": hit.payload.get("content", "") if hit.payload else "",
                "metadata": hit.payload.get("metadata", {}) if hit.payload else {},
                "source_type": (
                    hit.payload.get("source_type", "unknown")
                    if hit.payload
                    else "unknown"
                ),
            }
            for hit in results
        ]

    async def _keyword_search(
        self, query: str, limit: int, project_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Perform keyword search using BM25."""
        scroll_results = await self.qdrant_client.scroll(
            collection_name=self.collection_name,
            limit=10000,
            with_payload=True,
            with_vectors=False,
            scroll_filter=self._build_filter(project_ids),
        )

        documents = []
        metadata_list = []
        source_types = []

        for point in scroll_results[0]:
            if point.payload:
                content = point.payload.get("content", "")
                metadata = point.payload.get("metadata", {})
                source_type = point.payload.get("source_type", "unknown")
                documents.append(content)
                metadata_list.append(metadata)
                source_types.append(source_type)

        tokenized_docs = [doc.split() for doc in documents]
        bm25 = BM25Okapi(tokenized_docs)

        tokenized_query = query.split()
        scores = bm25.get_scores(tokenized_query)

        top_indices = np.argsort(scores)[-limit:][::-1]

        return [
            {
                "score": float(scores[idx]),
                "text": documents[idx],
                "metadata": metadata_list[idx],
                "source_type": source_types[idx],
            }
            for idx in top_indices
            if scores[idx] > 0
        ]

    async def _combine_results(
        self,
        vector_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        query_context: dict[str, Any],
        limit: int,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
    ) -> list[HybridSearchResult]:
        """Combine and rerank results from vector and keyword search."""
        combined_dict = {}

        # Process vector results
        for result in vector_results:
            text = result["text"]
            if text not in combined_dict:
                metadata = result["metadata"]
                combined_dict[text] = {
                    "text": text,
                    "metadata": metadata,
                    "source_type": result["source_type"],
                    "vector_score": result["score"],
                    "keyword_score": 0.0,
                }

        # Process keyword results
        for result in keyword_results:
            text = result["text"]
            if text in combined_dict:
                combined_dict[text]["keyword_score"] = result["score"]
            else:
                metadata = result["metadata"]
                combined_dict[text] = {
                    "text": text,
                    "metadata": metadata,
                    "source_type": result["source_type"],
                    "vector_score": 0.0,
                    "keyword_score": result["score"],
                }

        # Calculate combined scores and create results
        combined_results = []
        
        # 🔥 NEW: Extract intent-specific filtering configuration
        search_intent = query_context.get("search_intent")
        adaptive_config = query_context.get("adaptive_config")
        result_filters = adaptive_config.result_filters if adaptive_config else {}
        
        for text, info in combined_dict.items():
            # Skip if source type doesn't match filter
            if source_types and info["source_type"] not in source_types:
                continue

            metadata = info["metadata"]
            metadata_info = self._extract_metadata_info(metadata)
            
            # 🔥 NEW: Apply intent-specific result filtering
            if search_intent and result_filters:
                should_skip = False
                
                # Content type filtering
                if "content_type" in result_filters:
                    allowed_content_types = result_filters["content_type"]
                    # Check if any content type indicators match
                    has_matching_content = False
                    
                    for content_type in allowed_content_types:
                        if content_type == "code" and metadata_info.get("has_code_blocks"):
                            has_matching_content = True
                            break
                        elif content_type == "documentation" and not metadata_info.get("has_code_blocks"):
                            has_matching_content = True
                            break
                        elif content_type == "technical" and query_context.get("is_technical"):
                            has_matching_content = True
                            break
                        elif content_type in ["requirements", "business", "strategy"]:
                            # Check if content mentions business terms
                            business_indicators = metadata_info.get("business_indicators", 0)
                            if business_indicators > 0:
                                has_matching_content = True
                                break
                        elif content_type in ["guide", "tutorial", "procedure"]:
                            # Check for procedural content
                            section_type = metadata_info.get("section_type", "").lower()
                            if any(proc_word in section_type for proc_word in ["step", "guide", "procedure", "tutorial"]):
                                has_matching_content = True
                                break
                    
                    if not has_matching_content:
                        should_skip = True
                
                if should_skip:
                    continue

            combined_score = (
                self.vector_weight * info["vector_score"]
                + self.keyword_weight * info["keyword_score"]
            )

            if combined_score >= self.min_score:
                # Extract project information
                project_info = self._extract_project_info(metadata)

                boosted_score = self._boost_score_with_metadata(
                    combined_score, metadata_info, query_context
                )

                combined_results.append(
                    HybridSearchResult(
                        score=boosted_score,
                        text=text,
                        source_type=info["source_type"],
                        source_title=metadata.get("title", ""),
                        source_url=metadata.get("url"),
                        file_path=metadata.get("file_path"),
                        repo_name=metadata.get("repository_name"),
                        vector_score=info["vector_score"],
                        keyword_score=info["keyword_score"],
                        
                        # Project information
                        project_id=project_info["project_id"],
                        project_name=project_info["project_name"],
                        project_description=project_info["project_description"],
                        collection_name=project_info["collection_name"],
                        
                        # Basic hierarchy and attachment (existing)
                        parent_id=metadata_info["parent_id"],
                        parent_title=metadata_info["parent_title"],
                        breadcrumb_text=metadata_info["breadcrumb_text"],
                        depth=metadata_info["depth"],
                        children_count=metadata_info["children_count"],
                        hierarchy_context=metadata_info["hierarchy_context"],
                        is_attachment=metadata_info["is_attachment"],
                        parent_document_id=metadata_info["parent_document_id"],
                        parent_document_title=metadata_info["parent_document_title"],
                        attachment_id=metadata_info["attachment_id"],
                        original_filename=metadata_info["original_filename"],
                        file_size=metadata_info["file_size"],
                        mime_type=metadata_info["mime_type"],
                        attachment_author=metadata_info["attachment_author"],
                        attachment_context=metadata_info["attachment_context"],
                        
                        # 🔥 NEW: Section-level intelligence
                        section_title=metadata_info["section_title"],
                        section_type=metadata_info["section_type"],
                        section_level=metadata_info["section_level"],
                        section_anchor=metadata_info["section_anchor"],
                        section_breadcrumb=metadata_info["section_breadcrumb"],
                        section_depth=metadata_info["section_depth"],
                        
                        # 🔥 NEW: Content analysis
                        has_code_blocks=metadata_info["has_code_blocks"],
                        has_tables=metadata_info["has_tables"],
                        has_images=metadata_info["has_images"],
                        has_links=metadata_info["has_links"],
                        word_count=metadata_info["word_count"],
                        char_count=metadata_info["char_count"],
                        estimated_read_time=metadata_info["estimated_read_time"],
                        paragraph_count=metadata_info["paragraph_count"],
                        
                        # 🔥 NEW: Semantic analysis
                        entities=metadata_info["entities"],
                        topics=metadata_info["topics"],
                        key_phrases=metadata_info["key_phrases"],
                        pos_tags=metadata_info["pos_tags"],
                        
                        # 🔥 NEW: Navigation context
                        previous_section=metadata_info["previous_section"],
                        next_section=metadata_info["next_section"],
                        sibling_sections=metadata_info["sibling_sections"],
                        subsections=metadata_info["subsections"],
                        document_hierarchy=metadata_info["document_hierarchy"],
                        
                        # 🔥 NEW: Chunking context
                        chunk_index=metadata_info["chunk_index"],
                        total_chunks=metadata_info["total_chunks"],
                        chunking_strategy=metadata_info["chunking_strategy"],
                        
                        # 🔥 NEW: File conversion intelligence
                        original_file_type=metadata_info["original_file_type"],
                        conversion_method=metadata_info["conversion_method"],
                        is_excel_sheet=metadata_info["is_excel_sheet"],
                        is_converted=metadata_info["is_converted"],
                        
                        # 🔥 NEW: Cross-references and enhanced context
                        cross_references=metadata_info["cross_references"],
                        topic_analysis=metadata_info["topic_analysis"],
                        content_type_context=metadata_info["content_type_context"],
                    )
                )

        # Sort by combined score
        combined_results.sort(key=lambda x: x.score, reverse=True)
        
        # 🔥 NEW: Apply diversity filtering for exploratory intents
        if adaptive_config and adaptive_config.diversity_factor > 0.0:
            diverse_results = self._apply_diversity_filtering(
                combined_results, adaptive_config.diversity_factor, limit
            )
            self.logger.debug(
                "🔥 Applied diversity filtering",
                original_count=len(combined_results),
                diverse_count=len(diverse_results),
                diversity_factor=adaptive_config.diversity_factor,
            )
            return diverse_results
        
        return combined_results[:limit]

    def _extract_metadata_info(self, metadata: dict) -> dict:
        """Extract comprehensive metadata information from document metadata.

        Args:
            metadata: Document metadata

        Returns:
            Dictionary with all available metadata information
        """
        # 🔥 ENHANCED: Extract ALL the rich metadata we store
        
        # Basic hierarchy information (existing)
        hierarchy_info = {
            "parent_id": metadata.get("parent_id"),
            "parent_title": metadata.get("parent_title"),
            "breadcrumb_text": metadata.get("breadcrumb_text"),
            "depth": metadata.get("depth"),
            "children_count": None,
            "hierarchy_context": None,
        }

        # Calculate children count
        children = metadata.get("children", [])
        if children:
            hierarchy_info["children_count"] = len(children)

        # Generate hierarchy context for display
        if metadata.get("breadcrumb_text") or metadata.get("depth") is not None:
            context_parts = []

            if metadata.get("breadcrumb_text"):
                context_parts.append(f"Path: {metadata.get('breadcrumb_text')}")

            if metadata.get("depth") is not None:
                context_parts.append(f"Depth: {metadata.get('depth')}")

            if (
                hierarchy_info["children_count"] is not None
                and hierarchy_info["children_count"] > 0
            ):
                context_parts.append(f"Children: {hierarchy_info['children_count']}")

            if context_parts:
                hierarchy_info["hierarchy_context"] = " | ".join(context_parts)

        # Basic attachment information (existing)
        attachment_info = {
            "is_attachment": metadata.get("is_attachment", False),
            "parent_document_id": metadata.get("parent_document_id"),
            "parent_document_title": metadata.get("parent_document_title"),
            "attachment_id": metadata.get("attachment_id"),
            "original_filename": metadata.get("original_filename"),
            "file_size": metadata.get("file_size"),
            "mime_type": metadata.get("mime_type"),
            "attachment_author": metadata.get("attachment_author") or metadata.get("author"),
            "attachment_context": None,
        }

        # Generate attachment context for display
        if attachment_info["is_attachment"]:
            context_parts = []

            if attachment_info["original_filename"]:
                context_parts.append(f"File: {attachment_info['original_filename']}")

            if attachment_info["file_size"]:
                # Convert bytes to human readable format
                size = attachment_info["file_size"]
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                elif size < 1024 * 1024 * 1024:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                else:
                    size_str = f"{size / (1024 * 1024 * 1024):.1f} GB"
                context_parts.append(f"Size: {size_str}")

            if attachment_info["mime_type"]:
                context_parts.append(f"Type: {attachment_info['mime_type']}")

            if attachment_info["attachment_author"]:
                context_parts.append(f"Author: {attachment_info['attachment_author']}")

            if context_parts:
                attachment_info["attachment_context"] = " | ".join(context_parts)

        # 🔥 NEW: Section-level intelligence
        section_info = {
            "section_title": metadata.get("section_title"),
            "section_type": metadata.get("section_type"),
            "section_level": metadata.get("section_level"),
            "section_anchor": metadata.get("section_anchor"),
            "section_breadcrumb": metadata.get("section_breadcrumb"),
            "section_depth": metadata.get("section_depth"),
        }

        # 🔥 NEW: Content analysis from content_type_analysis
        content_analysis = metadata.get("content_type_analysis", {})
        content_info = {
            "has_code_blocks": content_analysis.get("has_code_blocks", False),
            "has_tables": content_analysis.get("has_tables", False),
            "has_images": content_analysis.get("has_images", False),
            "has_links": content_analysis.get("has_links", False),
            "word_count": content_analysis.get("word_count"),
            "char_count": content_analysis.get("char_count"),
            "estimated_read_time": content_analysis.get("estimated_read_time"),
            "paragraph_count": content_analysis.get("paragraph_count"),
        }

        # Generate content type context
        content_types = []
        if content_info["has_code_blocks"]:
            content_types.append("Code")
        if content_info["has_tables"]:
            content_types.append("Tables")
        if content_info["has_images"]:
            content_types.append("Images")
        if content_info["has_links"]:
            content_types.append("Links")

        content_type_context = None
        if content_types:
            content_type_context = f"Contains: {', '.join(content_types)}"
            if content_info["word_count"]:
                content_type_context += f" | {content_info['word_count']} words"
            if content_info["estimated_read_time"]:
                content_type_context += f" | ~{content_info['estimated_read_time']}min read"

        # 🔥 NEW: Semantic analysis (NLP results)
        # Convert spaCy tuples to expected formats for Pydantic validation
        raw_entities = metadata.get("entities", [])
        raw_topics = metadata.get("topics", [])
        raw_key_phrases = metadata.get("key_phrases", [])
        raw_pos_tags = metadata.get("pos_tags", [])
        
        # Convert entities from tuples [(text, label)] to dicts [{"text": text, "label": label}]
        entities = []
        for entity in raw_entities:
            if isinstance(entity, (list, tuple)) and len(entity) >= 2:
                entities.append({"text": str(entity[0]), "label": str(entity[1])})
            elif isinstance(entity, str):
                entities.append(entity)  # Keep strings as-is
            elif isinstance(entity, dict):
                entities.append(entity)  # Keep dicts as-is
        
        # Convert topics from tuples to dicts
        topics = []
        for topic in raw_topics:
            if isinstance(topic, (list, tuple)) and len(topic) >= 2:
                topics.append({"text": str(topic[0]), "score": float(topic[1]) if isinstance(topic[1], (int, float)) else str(topic[1])})
            elif isinstance(topic, str):
                topics.append(topic)  # Keep strings as-is
            elif isinstance(topic, dict):
                topics.append(topic)  # Keep dicts as-is
        
        # Convert key_phrases from tuples to dicts
        key_phrases = []
        for phrase in raw_key_phrases:
            if isinstance(phrase, (list, tuple)) and len(phrase) >= 2:
                key_phrases.append({"text": str(phrase[0]), "score": float(phrase[1]) if isinstance(phrase[1], (int, float)) else str(phrase[1])})
            elif isinstance(phrase, str):
                key_phrases.append(phrase)  # Keep strings as-is
            elif isinstance(phrase, dict):
                key_phrases.append(phrase)  # Keep dicts as-is
        
        # Convert pos_tags from tuples [(token, tag)] to dicts [{"token": token, "tag": tag}]
        pos_tags = []
        for pos_tag in raw_pos_tags:
            if isinstance(pos_tag, (list, tuple)) and len(pos_tag) >= 2:
                pos_tags.append({"token": str(pos_tag[0]), "tag": str(pos_tag[1])})
            elif isinstance(pos_tag, dict):
                pos_tags.append(pos_tag)  # Keep dicts as-is
        
        semantic_info = {
            "entities": entities,
            "topics": topics,
            "key_phrases": key_phrases,
            "pos_tags": pos_tags,
            "topic_analysis": metadata.get("topic_analysis"),
        }

        # 🔥 NEW: Navigation context
        navigation_info = {
            "previous_section": metadata.get("previous_section"),
            "next_section": metadata.get("next_section"),
            "sibling_sections": metadata.get("sibling_sections", []),
            "subsections": metadata.get("subsections", []),
            "document_hierarchy": metadata.get("document_hierarchy", []),
        }

        # 🔥 NEW: Chunking context
        chunking_info = {
            "chunk_index": metadata.get("chunk_index"),
            "total_chunks": metadata.get("total_chunks"),
            "chunking_strategy": metadata.get("chunking_strategy"),
        }

        # 🔥 NEW: File conversion intelligence
        conversion_info = {
            "original_file_type": metadata.get("original_file_type"),
            "conversion_method": metadata.get("conversion_method"),
            "is_excel_sheet": metadata.get("is_excel_sheet", False),
            "is_converted": metadata.get("is_converted", False),
        }

        # 🔥 NEW: Cross-references
        cross_reference_info = {
            "cross_references": metadata.get("cross_references", []),
        }

        # Combine all metadata
        return {
            **hierarchy_info,
            **attachment_info,
            **section_info,
            **content_info,
            **semantic_info,
            **navigation_info,
            **chunking_info,
            **conversion_info,
            **cross_reference_info,
            "content_type_context": content_type_context,
        }

    def _extract_project_info(self, metadata: dict) -> dict:
        """Extract project information from document metadata.

        Args:
            metadata: Document metadata

        Returns:
            Dictionary with project information
        """
        return {
            "project_id": metadata.get("project_id"),
            "project_name": metadata.get("project_name"),
            "project_description": metadata.get("project_description"),
            "collection_name": metadata.get("collection_name"),
        }

    def _build_filter(
        self, project_ids: list[str] | None = None
    ) -> models.Filter | None:
        """Build a Qdrant filter based on project IDs."""
        if not project_ids:
            return None

        return models.Filter(
            must=[
                models.FieldCondition(
                    key="project_id", match=models.MatchAny(any=project_ids)
                )
            ]
        )

    def _apply_diversity_filtering(
        self, 
        results: list[HybridSearchResult], 
        diversity_factor: float, 
        limit: int
    ) -> list[HybridSearchResult]:
        """🔥 NEW: Apply diversity filtering to promote varied result types."""
        if diversity_factor <= 0.0 or len(results) <= limit:
            return results[:limit]
        
        diverse_results = []
        used_source_types = set()
        used_section_types = set()
        used_sources = set()
        
        # First pass: Take top results while ensuring diversity
        for result in results:
            if len(diverse_results) >= limit:
                break
                
            # Calculate diversity score
            diversity_score = 1.0
            
            # Penalize duplicate source types (less diversity)
            source_type = result.source_type
            if source_type in used_source_types:
                diversity_score *= (1.0 - diversity_factor * 0.3)
            
            # Penalize duplicate section types
            section_type = result.section_type or "unknown"
            if section_type in used_section_types:
                diversity_score *= (1.0 - diversity_factor * 0.2)
            
            # Penalize duplicate sources (same document/file)
            source_key = f"{result.source_type}:{result.source_title}"
            if source_key in used_sources:
                diversity_score *= (1.0 - diversity_factor * 0.4)
            
            # Apply diversity penalty to score
            adjusted_score = result.score * diversity_score
            
            # Use original score to determine if we should include this result
            if len(diverse_results) < limit * 0.7 or adjusted_score >= result.score * 0.6:
                diverse_results.append(result)
                used_source_types.add(source_type)
                used_section_types.add(section_type)
                used_sources.add(source_key)
        
        # Second pass: Fill remaining slots with best remaining results
        remaining_slots = limit - len(diverse_results)
        if remaining_slots > 0:
            remaining_results = [r for r in results if r not in diverse_results]
            diverse_results.extend(remaining_results[:remaining_slots])
        
        return diverse_results[:limit]
    
    def get_adaptive_search_stats(self) -> dict[str, Any]:
        """🔥 NEW: Get adaptive search statistics for monitoring."""
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
    # 🔥 Phase 1.3: Dynamic Faceted Search Interface Methods
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
        """
        🔥 Phase 1.3: Perform faceted search with dynamic facet generation.
        
        Args:
            query: Search query
            limit: Maximum number of results
            source_types: Optional source type filters
            project_ids: Optional project ID filters  
            facet_filters: Optional facet filters to apply
            generate_facets: Whether to generate facets from results
            session_context: Optional session context for intent classification
            behavioral_context: Optional behavioral context
            
        Returns:
            FacetedSearchResults with results and generated facets
        """
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
    
    def apply_facet_filters(
        self,
        results: list[SearchResult],
        filters: list[FacetFilter]
    ) -> list[SearchResult]:
        """
        🔥 Phase 1.3: Apply facet filters to search results.
        
        Args:
            results: Search results to filter
            filters: Facet filters to apply
            
        Returns:
            Filtered search results
        """
        return self.faceted_search_engine.apply_facet_filters(results, filters)
    
    def generate_facets(
        self,
        results: list[SearchResult]
    ) -> list:
        """
        🔥 Phase 1.3: Generate dynamic facets from search results.
        
        Args:
            results: Search results to analyze
            
        Returns:
            List of generated facets
        """
        return self.faceted_search_engine.facet_generator.generate_facets(results)
    
    def suggest_facet_refinements(
        self,
        current_results: list[SearchResult],
        current_filters: list[FacetFilter]
    ) -> list[dict[str, Any]]:
        """
        🔥 Phase 1.3: Suggest facet refinements based on current results.
        
        Args:
            current_results: Current search results
            current_filters: Currently applied filters
            
        Returns:
            List of suggested refinements with impact estimates
        """
        return self.faceted_search_engine.suggest_refinements(
            current_results, 
            current_filters
        )
    
    # 🔥 Phase 2.3: Cross-Document Intelligence Methods
    
    async def analyze_document_relationships(
        self,
        documents: list[SearchResult]
    ) -> dict[str, Any]:
        """
        🔥 Phase 2.3: Perform comprehensive cross-document relationship analysis.
        
        Args:
            documents: Documents to analyze for relationships
            
        Returns:
            Comprehensive analysis including clusters, similarities, and conflicts
        """
        try:
            return self.cross_document_engine.analyze_document_relationships(documents)
        except Exception as e:
            self.logger.error("Error in cross-document analysis", error=str(e))
            raise
    
    async def find_similar_documents(
        self,
        target_document: SearchResult,
        documents: list[SearchResult],
        similarity_metrics: list[SimilarityMetric] = None,
        max_similar: int = 5
    ) -> list[dict[str, Any]]:
        """
        🔥 Phase 2.3: Find documents similar to a target document.
        
        Args:
            target_document: Document to find similar documents for
            documents: Pool of documents to search within
            similarity_metrics: Metrics to use for similarity calculation
            max_similar: Maximum number of similar documents to return
            
        Returns:
            List of similar documents with similarity scores
        """
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
                    "document": doc,
                    "similarity_score": similarity.similarity_score,
                    "metric_scores": similarity.metric_scores,
                    "similarity_reasons": [similarity.get_display_explanation()]
                })
            
            # Sort by similarity score and return top results
            similar_docs.sort(key=lambda x: x["similarity_score"], reverse=True)
            return similar_docs[:max_similar]
            
        except Exception as e:
            self.logger.error("Error finding similar documents", error=str(e))
            raise
    
    async def detect_document_conflicts(
        self,
        documents: list[SearchResult]
    ) -> dict[str, Any]:
        """
        🔥 Phase 2.3: Detect conflicts between documents.
        
        Args:
            documents: Documents to analyze for conflicts
            
        Returns:
            Conflict analysis with detected conflicts and resolution suggestions
        """
        try:
            conflict_analysis = self.cross_document_engine.conflict_detector.detect_conflicts(documents)
            # Convert ConflictAnalysis object to dictionary format
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
        target_document: SearchResult,
        documents: list[SearchResult],
        max_recommendations: int = 5
    ) -> list[dict[str, Any]]:
        """
        🔥 Phase 2.3: Find content that complements the target document.
        
        Args:
            target_document: Document to find complementary content for
            documents: Pool of documents to search within
            max_recommendations: Maximum number of recommendations
            
        Returns:
            List of complementary documents with recommendation reasons
        """
        try:
            complementary_content = self.cross_document_engine.complementary_finder.find_complementary_content(
                target_document,
                documents
            )
            # Get top recommendations using the proper method
            return complementary_content.get_top_recommendations(max_recommendations)
        except Exception as e:
            self.logger.error("Error finding complementary content", error=str(e))
            raise
    
    async def cluster_documents(
        self,
        documents: list[SearchResult],
        strategy: ClusteringStrategy = ClusteringStrategy.MIXED_FEATURES,
        max_clusters: int = 10,
        min_cluster_size: int = 2
    ) -> dict[str, Any]:
        """
        🔥 Phase 2.3: Cluster documents based on similarity and relationships.
        
        Args:
            documents: Documents to cluster
            strategy: Clustering strategy to use
            max_clusters: Maximum number of clusters to create
            min_cluster_size: Minimum size for a cluster
            
        Returns:
            Document clusters with metadata and relationships
        """
        try:
            clusters = self.cross_document_engine.cluster_analyzer.create_clusters(
                documents,
                strategy,
                max_clusters,
                min_cluster_size
            )
            
            # Convert to serializable format
            cluster_data = []
            for cluster in clusters:
                cluster_data.append({
                    "id": cluster.cluster_id,
                    "documents": cluster.documents,
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
