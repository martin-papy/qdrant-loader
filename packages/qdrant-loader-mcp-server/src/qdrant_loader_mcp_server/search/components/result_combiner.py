"""Result combination and ranking logic for hybrid search."""

from typing import Any

from ...utils.logging import LoggingConfig
from ..hybrid.components.scoring import HybridScorer, ScoreComponents
from ..nlp.spacy_analyzer import SpaCyQueryAnalyzer
from .combining import (
    boost_score_with_metadata,
    flatten_metadata_components,
    should_skip_result,
)
from .metadata_extractor import MetadataExtractor
from .search_result_models import HybridSearchResult, create_hybrid_search_result


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
        # Internal scorer to centralize weighting logic (behavior-preserving)
        self._scorer = HybridScorer(
            vector_weight=self.vector_weight,
            keyword_weight=self.keyword_weight,
            metadata_weight=self.metadata_weight,
        )

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
                    # 🔧 CRITICAL FIX: Include all root-level fields from search services
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "document_id": result.get("document_id", ""),
                    "source": result.get("source", ""),
                    "created_at": result.get("created_at", ""),
                    "updated_at": result.get("updated_at", ""),
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
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "document_id": result.get("document_id", ""),
                    "source": result.get("source", ""),
                    "created_at": result.get("created_at", ""),
                    "updated_at": result.get("updated_at", ""),
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
                if should_skip_result(metadata, result_filters, query_context):
                    continue

            combined_score = self._scorer.compute(
                ScoreComponents(
                    vector_score=info["vector_score"],
                    keyword_score=info["keyword_score"],
                    metadata_score=0.0,  # Preserve legacy behavior (no metadata in base score)
                )
            )

            if combined_score >= self.min_score:
                # Extract all metadata components
                metadata_components = self.metadata_extractor.extract_all_metadata(
                    metadata
                )

                # Boost score with metadata
                boosted_score = boost_score_with_metadata(
                    combined_score,
                    metadata,
                    query_context,
                    spacy_analyzer=self.spacy_analyzer,
                )

                # Extract fields from both direct payload fields and nested metadata
                # Use direct fields from Qdrant payload when available, fallback to metadata
                title = info.get("title", "") or metadata.get("title", "")

                # Extract rich metadata from nested metadata object
                file_name = metadata.get("file_name", "")
                metadata.get("file_type", "")
                chunk_index = metadata.get("chunk_index")
                total_chunks = metadata.get("total_chunks")

                # Enhanced title generation using actual Qdrant structure
                # Priority: root title > nested section_title > file_name + chunk info > source
                root_title = info.get(
                    "title", ""
                )  # e.g., "Stratégie commerciale MYA.pdf - Chunk 2"
                nested_title = metadata.get("title", "")  # e.g., "Preamble (Part 2)"
                section_title = metadata.get("section_title", "")

                if root_title:
                    title = root_title
                elif nested_title:
                    title = nested_title
                elif section_title:
                    title = section_title
                elif file_name:
                    title = file_name
                    # Add chunk info if available from nested metadata
                    sub_chunk_index = metadata.get("sub_chunk_index")
                    total_sub_chunks = metadata.get("total_sub_chunks")
                    if sub_chunk_index is not None and total_sub_chunks is not None:
                        title += (
                            f" - Chunk {int(sub_chunk_index) + 1}/{total_sub_chunks}"
                        )
                    elif chunk_index is not None and total_chunks is not None:
                        title += f" - Chunk {int(chunk_index) + 1}/{total_chunks}"
                else:
                    source = info.get("source", "") or metadata.get("source", "")
                    if source:
                        # Extract filename from path-like sources
                        import os

                        title = (
                            os.path.basename(source)
                            if "/" in source or "\\" in source
                            else source
                        )
                    else:
                        title = "Untitled"

                # Create enhanced metadata dict with rich Qdrant fields
                enhanced_metadata = {
                    # Core fields from root level of Qdrant payload
                    "source_url": info.get("url", ""),
                    "document_id": info.get("document_id", ""),
                    "created_at": info.get("created_at", ""),
                    "last_modified": info.get("updated_at", ""),
                    "repo_name": info.get("source", ""),
                    # Project scoping is stored at the root as 'source'
                    "project_id": info.get("source", ""),
                    # Construct file path from nested metadata
                    "file_path": (
                        metadata.get("file_directory", "").rstrip("/")
                        + "/"
                        + metadata.get("file_name", "")
                        if metadata.get("file_name") and metadata.get("file_directory")
                        else metadata.get("file_name", "")
                    ),
                }

                # Add rich metadata from nested metadata object (confirmed structure)
                rich_metadata_fields = {
                    "original_filename": metadata.get("file_name"),
                    "file_size": metadata.get("file_size"),
                    "original_file_type": metadata.get("file_type")
                    or metadata.get("original_file_type"),
                    "word_count": metadata.get("word_count"),
                    "char_count": metadata.get("character_count")
                    or metadata.get("char_count")
                    or metadata.get("line_count"),
                    "chunk_index": metadata.get("sub_chunk_index", chunk_index),
                    "total_chunks": metadata.get("total_sub_chunks", total_chunks),
                    "chunking_strategy": metadata.get("chunking_strategy")
                    or metadata.get("conversion_method"),
                    # Project fields now come from root payload; avoid overriding with nested metadata
                    "collection_name": metadata.get("collection_name"),
                    # Additional rich fields from actual Qdrant structure
                    "section_title": metadata.get("section_title"),
                    "parent_section": metadata.get("parent_section"),
                    "file_encoding": metadata.get("file_encoding"),
                    "conversion_failed": metadata.get("conversion_failed", False),
                    "is_excel_sheet": metadata.get("is_excel_sheet", False),
                }

                # Only add non-None values to avoid conflicts
                for key, value in rich_metadata_fields.items():
                    if value is not None:
                        enhanced_metadata[key] = value

                # Merge with flattened metadata components (flattened takes precedence for conflicts)
                flattened_components = flatten_metadata_components(metadata_components)
                enhanced_metadata.update(flattened_components)

                # NOTE: No additional fallback; root payload project_id is authoritative

                # Create HybridSearchResult using factory function
                hybrid_result = create_hybrid_search_result(
                    score=boosted_score,
                    text=text,
                    source_type=info["source_type"],
                    source_title=title,
                    vector_score=info["vector_score"],
                    keyword_score=info["keyword_score"],
                    **enhanced_metadata,
                )

                combined_results.append(hybrid_result)

        # Sort by combined score
        combined_results.sort(key=lambda x: x.score, reverse=True)

        # Apply diversity filtering for exploratory intents
        if adaptive_config and adaptive_config.diversity_factor > 0.0:
            try:
                from ..hybrid.components.diversity import apply_diversity_filtering

                diverse_results = apply_diversity_filtering(
                    combined_results, adaptive_config.diversity_factor, limit
                )
                self.logger.debug(
                    "Applied diversity filtering",
                    original_count=len(combined_results),
                    diverse_count=len(diverse_results),
                    diversity_factor=adaptive_config.diversity_factor,
                )
                return diverse_results
            except Exception:
                # Fallback to original top-N behavior if import or filtering fails
                pass

        return combined_results[:limit]

    # The following methods are thin wrappers delegating to combining/* modules
    # to preserve backward-compatible tests that call private methods directly.

    def _should_skip_result(
        self, metadata: dict, result_filters: dict, query_context: dict
    ) -> bool:
        return should_skip_result(metadata, result_filters, query_context)

    def _count_business_indicators(self, metadata: dict) -> int:
        return __import__(
            f"{__package__}.combining.filters", fromlist=["count_business_indicators"]
        ).count_business_indicators(metadata)

    def _boost_score_with_metadata(
        self, base_score: float, metadata: dict, query_context: dict
    ) -> float:
        return boost_score_with_metadata(
            base_score, metadata, query_context, spacy_analyzer=self.spacy_analyzer
        )

    def _apply_content_type_boosting(
        self, metadata: dict, query_context: dict
    ) -> float:
        from .combining import apply_content_type_boosting

        return apply_content_type_boosting(metadata, query_context)

    def _apply_section_level_boosting(self, metadata: dict) -> float:
        from .combining import apply_section_level_boosting

        return apply_section_level_boosting(metadata)

    def _apply_content_quality_boosting(self, metadata: dict) -> float:
        from .combining import apply_content_quality_boosting

        return apply_content_quality_boosting(metadata)

    def _apply_conversion_boosting(self, metadata: dict, query_context: dict) -> float:
        from .combining import apply_conversion_boosting

        return apply_conversion_boosting(metadata, query_context)

    def _apply_semantic_boosting(self, metadata: dict, query_context: dict) -> float:
        from .combining import apply_semantic_boosting

        return apply_semantic_boosting(metadata, query_context, self.spacy_analyzer)

    def _apply_fallback_semantic_boosting(
        self, metadata: dict, query_context: dict
    ) -> float:
        from .combining import apply_fallback_semantic_boosting

        return apply_fallback_semantic_boosting(metadata, query_context)

    def _apply_diversity_filtering(
        self, results: list[HybridSearchResult], diversity_factor: float, limit: int
    ) -> list[HybridSearchResult]:
        if diversity_factor <= 0.0 or len(results) <= limit:
            return results[:limit]

        diverse_results = []
        used_source_types = set()
        used_section_types = set()
        used_sources = set()

        for result in results:
            if len(diverse_results) >= limit:
                break

            diversity_score = 1.0
            source_type = result.source_type
            if source_type in used_source_types:
                diversity_score *= 1.0 - diversity_factor * 0.3

            section_type = result.section_type or "unknown"
            if section_type in used_section_types:
                diversity_score *= 1.0 - diversity_factor * 0.2

            source_key = f"{result.source_type}:{result.source_title}"
            if source_key in used_sources:
                diversity_score *= 1.0 - diversity_factor * 0.4

            adjusted_score = result.score * diversity_score

            if (
                len(diverse_results) < limit * 0.7
                or adjusted_score >= result.score * 0.6
            ):
                diverse_results.append(result)
                used_source_types.add(source_type)
                used_section_types.add(section_type)
                used_sources.add(source_key)

        remaining_slots = limit - len(diverse_results)
        if remaining_slots > 0:
            remaining_results = [r for r in results if r not in diverse_results]
            diverse_results.extend(remaining_results[:remaining_slots])

        return diverse_results[:limit]

    def _flatten_metadata_components(
        self, metadata_components: dict[str, Any]
    ) -> dict[str, Any]:
        return flatten_metadata_components(metadata_components)
