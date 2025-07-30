"""Result combination and ranking logic for hybrid search."""

from typing import Any

from ...utils.logging import LoggingConfig
from ..nlp.spacy_analyzer import SpaCyQueryAnalyzer
from .search_result_models import (
    BaseSearchResult,
    HybridSearchResult,
    create_hybrid_search_result,
)
from .metadata_extractor import MetadataExtractor


class ResultCombiner:
    """Combines and ranks search results from multiple sources."""

    def __init__(
        self,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.3,
        metadata_weight: float = 0.1,
        min_score: float = 0.3,
        spacy_analyzer: SpaCyQueryAnalyzer | None = None,
    ):
        """Initialize the result combiner.
        
        Args:
            vector_weight: Weight for vector search scores (0-1)
            keyword_weight: Weight for keyword search scores (0-1)
            metadata_weight: Weight for metadata-based scoring (0-1)
            min_score: Minimum combined score threshold
            spacy_analyzer: Optional spaCy analyzer for semantic boosting
        """
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.metadata_weight = metadata_weight
        self.min_score = min_score
        self.spacy_analyzer = spacy_analyzer
        self.logger = LoggingConfig.get_logger(__name__)
        
        self.metadata_extractor = MetadataExtractor()

    async def combine_results(
        self,
        vector_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        query_context: dict[str, Any],
        limit: int,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
    ) -> list[HybridSearchResult]:
        """Combine and rerank results from vector and keyword search.
        
        Args:
            vector_results: Results from vector search
            keyword_results: Results from keyword search
            query_context: Query analysis context
            limit: Maximum number of results to return
            source_types: Optional source type filters
            project_ids: Optional project ID filters
            
        Returns:
            List of combined and ranked HybridSearchResult objects
        """
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
        
        # Extract intent-specific filtering configuration
        search_intent = query_context.get("search_intent")
        adaptive_config = query_context.get("adaptive_config")
        result_filters = adaptive_config.result_filters if adaptive_config else {}
        
        for text, info in combined_dict.items():
            # Skip if source type doesn't match filter
            if source_types and info["source_type"] not in source_types:
                continue

            metadata = info["metadata"]
            
            # Apply intent-specific result filtering
            if search_intent and result_filters:
                if self._should_skip_result(metadata, result_filters, query_context):
                    continue

            combined_score = (
                self.vector_weight * info["vector_score"]
                + self.keyword_weight * info["keyword_score"]
            )

            if combined_score >= self.min_score:
                # Extract all metadata components
                metadata_components = self.metadata_extractor.extract_all_metadata(metadata)
                
                # Boost score with metadata
                boosted_score = self._boost_score_with_metadata(
                    combined_score, metadata, query_context
                )

                # Create HybridSearchResult using factory function
                hybrid_result = create_hybrid_search_result(
                    score=boosted_score,
                    text=text,
                    source_type=info["source_type"],
                    source_title=metadata.get("title", ""),
                    vector_score=info["vector_score"],
                    keyword_score=info["keyword_score"],
                    source_url=metadata.get("url"),
                    file_path=metadata.get("file_path"),
                    repo_name=metadata.get("repository_name"),
                    # Flatten metadata components for backward compatibility
                    **self._flatten_metadata_components(metadata_components),
                )

                combined_results.append(hybrid_result)

        # Sort by combined score
        combined_results.sort(key=lambda x: x.score, reverse=True)
        
        # Apply diversity filtering for exploratory intents
        if adaptive_config and adaptive_config.diversity_factor > 0.0:
            diverse_results = self._apply_diversity_filtering(
                combined_results, adaptive_config.diversity_factor, limit
            )
            self.logger.debug(
                "Applied diversity filtering",
                original_count=len(combined_results),
                diverse_count=len(diverse_results),
                diversity_factor=adaptive_config.diversity_factor,
            )
            return diverse_results
        
        return combined_results[:limit]

    def _should_skip_result(
        self, 
        metadata: dict, 
        result_filters: dict, 
        query_context: dict
    ) -> bool:
        """Check if a result should be skipped based on intent-specific filters."""
        # Content type filtering
        if "content_type" in result_filters:
            allowed_content_types = result_filters["content_type"]
            content_analysis = metadata.get("content_type_analysis", {})
            
            # Check if any content type indicators match
            has_matching_content = False
            
            for content_type in allowed_content_types:
                if content_type == "code" and content_analysis.get("has_code_blocks"):
                    has_matching_content = True
                    break
                elif content_type == "documentation" and not content_analysis.get("has_code_blocks"):
                    has_matching_content = True
                    break
                elif content_type == "technical" and query_context.get("is_technical"):
                    has_matching_content = True
                    break
                elif content_type in ["requirements", "business", "strategy"]:
                    # Check if content mentions business terms
                    business_indicators = self._count_business_indicators(metadata)
                    if business_indicators > 0:
                        has_matching_content = True
                        break
                elif content_type in ["guide", "tutorial", "procedure"]:
                    # Check for procedural content
                    section_type = metadata.get("section_type", "").lower()
                    if any(proc_word in section_type for proc_word in ["step", "guide", "procedure", "tutorial"]):
                        has_matching_content = True
                        break
            
            if not has_matching_content:
                return True
        
        return False

    def _count_business_indicators(self, metadata: dict) -> int:
        """Count business-related indicators in metadata."""
        # Simple heuristic for business content
        business_terms = ["requirement", "business", "strategy", "goal", "objective", "process"]
        title = metadata.get("title", "").lower()
        content = metadata.get("content", "").lower()
        
        count = 0
        for term in business_terms:
            if term in title or term in content:
                count += 1
        
        return count

    def _boost_score_with_metadata(
        self, base_score: float, metadata: dict, query_context: dict
    ) -> float:
        """Boost search scores using metadata context and spaCy semantic analysis."""
        boosted_score = base_score
        boost_factor = 0.0

        # Intent-aware boosting
        search_intent = query_context.get("search_intent")
        adaptive_config = query_context.get("adaptive_config")
        
        if search_intent and adaptive_config:
            boost_factor += self._apply_intent_boosting(
                metadata, search_intent, adaptive_config, query_context
            )

        # Content type relevance boosting
        boost_factor += self._apply_content_type_boosting(metadata, query_context)
        
        # Section level relevance boosting
        boost_factor += self._apply_section_level_boosting(metadata)
        
        # Content quality indicators boosting
        boost_factor += self._apply_content_quality_boosting(metadata)
        
        # File conversion boosting
        boost_factor += self._apply_conversion_boosting(metadata, query_context)
        
        # Semantic analysis boosting
        if self.spacy_analyzer:
            boost_factor += self._apply_semantic_boosting(metadata, query_context)
        else:
            boost_factor += self._apply_fallback_semantic_boosting(metadata, query_context)

        # Apply boost (cap at reasonable maximum)
        boost_factor = min(boost_factor, 0.5)  # Maximum 50% boost
        return boosted_score * (1 + boost_factor)

    def _apply_intent_boosting(
        self, 
        metadata: dict, 
        search_intent: Any, 
        adaptive_config: Any, 
        query_context: dict
    ) -> float:
        """Apply intent-specific ranking boosts."""
        boost_factor = 0.0
        
        ranking_boosts = adaptive_config.ranking_boosts
        source_type_preferences = adaptive_config.source_type_preferences
        
        # Source type preference boosting
        source_type = metadata.get("source_type", "")
        if source_type in source_type_preferences:
            source_boost = (source_type_preferences[source_type] - 1.0) * 0.2
            boost_factor += source_boost
            
        # Content type boosting from ranking_boosts
        for boost_key, boost_value in ranking_boosts.items():
            if boost_key == "section_type" and isinstance(boost_value, dict):
                section_type = metadata.get("section_type", "")
                if section_type in boost_value:
                    section_boost = (boost_value[section_type] - 1.0) * 0.15
                    boost_factor += section_boost
            elif boost_key == "source_type" and isinstance(boost_value, dict):
                if source_type in boost_value:
                    source_boost = (boost_value[source_type] - 1.0) * 0.15
                    boost_factor += source_boost
            elif boost_key in metadata and metadata[boost_key]:
                # Boolean metadata boosting
                if isinstance(boost_value, (int, float)):
                    bool_boost = (boost_value - 1.0) * 0.1
                    boost_factor += bool_boost
        
        # Intent-specific confidence boosting
        confidence_boost = search_intent.confidence * 0.05  # Up to 5% boost for high confidence
        boost_factor += confidence_boost
        
        return boost_factor

    def _apply_content_type_boosting(self, metadata: dict, query_context: dict) -> float:
        """Apply content type relevance boosting."""
        boost_factor = 0.0
        content_analysis = metadata.get("content_type_analysis", {})
        
        if query_context.get("prefers_code") and content_analysis.get("has_code_blocks"):
            boost_factor += 0.15
        
        if query_context.get("prefers_tables") and content_analysis.get("has_tables"):
            boost_factor += 0.12
            
        if query_context.get("prefers_images") and content_analysis.get("has_images"):
            boost_factor += 0.10
            
        if query_context.get("prefers_docs") and not content_analysis.get("has_code_blocks"):
            boost_factor += 0.08

        return boost_factor

    def _apply_section_level_boosting(self, metadata: dict) -> float:
        """Apply section level relevance boosting."""
        boost_factor = 0.0
        section_level = metadata.get("section_level")
        
        if section_level is not None:
            if section_level <= 2:  # H1, H2 are more important
                boost_factor += 0.10
            elif section_level <= 3:  # H3 moderately important  
                boost_factor += 0.05

        return boost_factor

    def _apply_content_quality_boosting(self, metadata: dict) -> float:
        """Apply content quality indicators boosting."""
        boost_factor = 0.0
        content_analysis = metadata.get("content_type_analysis", {})
        word_count = content_analysis.get("word_count") or 0
        
        if word_count > 100:  # Substantial content
            boost_factor += 0.05
        if word_count > 500:  # Very detailed content
            boost_factor += 0.05

        return boost_factor

    def _apply_conversion_boosting(self, metadata: dict, query_context: dict) -> float:
        """Apply file conversion boosting."""
        boost_factor = 0.0
        
        # Converted file boosting (often contains rich content)
        if metadata.get("is_converted") and metadata.get("original_file_type") in ["docx", "xlsx", "pdf"]:
            boost_factor += 0.08

        # Excel sheet specific boosting for data queries
        if metadata.get("is_excel_sheet") and any(
            term in " ".join(query_context.get("keywords", [])) 
            for term in ["data", "table", "sheet", "excel", "csv"]
        ):
            boost_factor += 0.12

        return boost_factor

    def _apply_semantic_boosting(self, metadata: dict, query_context: dict) -> float:
        """Apply semantic analysis boosting using spaCy."""
        boost_factor = 0.0
        
        if "spacy_analysis" not in query_context:
            return boost_factor
            
        spacy_analysis = query_context["spacy_analysis"]
        
        # Enhanced entity matching using spaCy similarity
        entities = metadata.get("entities", [])
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
        topics = metadata.get("topics", [])
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

        return boost_factor

    def _apply_fallback_semantic_boosting(self, metadata: dict, query_context: dict) -> float:
        """Apply fallback semantic boosting without spaCy."""
        boost_factor = 0.0
        
        # Fallback to original entity/topic matching
        entities = metadata.get("entities", [])
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
        topics = metadata.get("topics", [])
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

        return boost_factor

    def _apply_diversity_filtering(
        self, 
        results: list[HybridSearchResult], 
        diversity_factor: float, 
        limit: int
    ) -> list[HybridSearchResult]:
        """Apply diversity filtering to promote varied result types."""
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

    def _flatten_metadata_components(self, metadata_components: dict[str, Any]) -> dict[str, Any]:
        """Flatten metadata components for backward compatibility."""
        flattened = {}
        
        for component_name, component in metadata_components.items():
            if component is None:
                continue
                
            if hasattr(component, "__dict__"):
                # Convert dataclass to dict and flatten
                component_dict = component.__dict__
                for key, value in component_dict.items():
                    flattened[key] = value
            elif isinstance(component, dict):
                flattened.update(component)
        
        return flattened