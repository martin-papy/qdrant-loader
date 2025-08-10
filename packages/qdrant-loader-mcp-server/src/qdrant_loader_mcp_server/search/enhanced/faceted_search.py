"""
This module provides intelligent faceted search capabilities that leverage the rich
metadata extracted during document ingestion. It dynamically generates facets from
HybridSearchResult metadata and provides filtering and refinement capabilities.

Key Features:
- Dynamic facet generation from metadata
- Intelligent facet grouping and sorting
- Multi-facet filtering with AND/OR logic
- Real-time facet value counting
- Smart facet suggestions based on query context
"""

import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ..components.search_result_models import HybridSearchResult

logger = logging.getLogger(__name__)


class FacetType(Enum):
    """Types of facets available for filtering."""

    # Content-based facets
    CONTENT_TYPE = "content_type"
    SOURCE_TYPE = "source_type"
    FILE_TYPE = "file_type"
    HAS_FEATURES = "has_features"

    # Hierarchical facets
    HIERARCHY_DEPTH = "hierarchy_depth"
    SECTION_LEVEL = "section_level"
    SECTION_TYPE = "section_type"

    # Project/Organization facets
    PROJECT = "project"
    COLLECTION = "collection"
    REPOSITORY = "repository"

    # Semantic facets
    ENTITIES = "entities"
    ENTITY_TYPES = "entity_types"
    TOPICS = "topics"
    KEY_PHRASES = "key_phrases"

    # Content size facets
    READ_TIME = "read_time"
    WORD_COUNT = "word_count"
    FILE_SIZE = "file_size"

    # Document structure facets
    ATTACHMENT_TYPE = "attachment_type"
    CONVERSION_TYPE = "conversion_type"
    CHUNKING_STRATEGY = "chunking_strategy"


@dataclass
class FacetValue:
    """A single facet value with count and metadata."""

    value: str
    count: int
    display_name: str
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.display_name} ({self.count})"


@dataclass
class Facet:
    """A facet with its type, values, and configuration."""

    facet_type: FacetType
    name: str
    display_name: str
    values: list[FacetValue]
    description: str | None = None
    is_multi_select: bool = True
    is_hierarchical: bool = False
    sort_by: str = "count"  # "count", "name", "relevance"
    max_visible: int = 10

    def get_top_values(self, limit: int | None = None) -> list[FacetValue]:
        """Get top facet values sorted by the configured sort method."""
        if limit is None:
            limit = self.max_visible

        if self.sort_by == "count":
            return sorted(self.values, key=lambda v: v.count, reverse=True)[:limit]
        elif self.sort_by == "name":
            return sorted(self.values, key=lambda v: v.display_name.lower())[:limit]
        else:  # relevance - for now same as count
            return sorted(self.values, key=lambda v: v.count, reverse=True)[:limit]


@dataclass
class FacetFilter:
    """A filter applied to search results based on facet selections."""

    facet_type: FacetType
    values: list[str]
    operator: str = "OR"  # "OR", "AND"

    def matches(self, result: HybridSearchResult) -> bool:
        """Check if a search result matches this facet filter."""
        result_values = self._extract_values_from_result(result)

        if self.operator == "OR":
            return any(value in result_values for value in self.values)
        else:  # AND
            return all(value in result_values for value in self.values)

    def _extract_values_from_result(self, result: HybridSearchResult) -> list[str]:
        """Extract values for this facet type from a search result."""
        if self.facet_type == FacetType.CONTENT_TYPE:
            return [result.source_type] if result.source_type else []
        elif self.facet_type == FacetType.SOURCE_TYPE:
            return [result.source_type] if result.source_type else []
        elif self.facet_type == FacetType.FILE_TYPE:
            file_type = result.get_file_type()
            return [file_type] if file_type else []
        elif self.facet_type == FacetType.HAS_FEATURES:
            features = []
            if result.has_code_blocks:
                features.append("code")
            if result.has_tables:
                features.append("tables")
            if result.has_images:
                features.append("images")
            if result.has_links:
                features.append("links")
            return features
        elif self.facet_type == FacetType.PROJECT:
            return [result.project_name] if result.project_name else []
        elif self.facet_type == FacetType.ENTITIES:
            entities = []
            for entity in result.entities:
                if isinstance(entity, dict) and "text" in entity:
                    entities.append(entity["text"].lower())
                elif isinstance(entity, str):
                    entities.append(entity.lower())
            return entities
        elif self.facet_type == FacetType.TOPICS:
            topics = []
            for topic in result.topics:
                if isinstance(topic, dict) and "text" in topic:
                    topics.append(topic["text"].lower())
                elif isinstance(topic, str):
                    topics.append(topic.lower())
            return topics
        elif self.facet_type == FacetType.HIERARCHY_DEPTH:
            if result.depth is not None:
                if result.depth <= 2:
                    return ["shallow"]
                elif result.depth <= 4:
                    return ["medium"]
                else:
                    return ["deep"]
            return []
        elif self.facet_type == FacetType.READ_TIME:
            if result.estimated_read_time is not None:
                if result.estimated_read_time <= 2:
                    return ["quick"]
                elif result.estimated_read_time <= 10:
                    return ["medium"]
                else:
                    return ["long"]
            return []

        return []


@dataclass
class FacetedSearchResults:
    """Container for faceted search results with facets and filtered results."""

    results: list[HybridSearchResult]
    facets: list[Facet]
    applied_filters: list[FacetFilter]
    total_results: int
    filtered_count: int
    generation_time_ms: float

    def get_facet(self, facet_type: FacetType) -> Facet | None:
        """Get a specific facet by type."""
        return next((f for f in self.facets if f.facet_type == facet_type), None)

    def has_active_filters(self) -> bool:
        """Check if any filters are currently applied."""
        return len(self.applied_filters) > 0


class DynamicFacetGenerator:
    """
    Dynamic Facet Generator

    Analyzes HybridSearchResult metadata to dynamically generate relevant facets
    for filtering and exploration. Leverages the rich metadata infrastructure
    from previous phases.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Configuration for facet generation
        self.facet_config = {
            FacetType.CONTENT_TYPE: {
                "display_name": "Content Type",
                "description": "Type of content source",
                "max_values": 10,
                "min_count": 1,
            },
            FacetType.HAS_FEATURES: {
                "display_name": "Content Features",
                "description": "Features present in the content",
                "max_values": 8,
                "min_count": 1,
            },
            FacetType.PROJECT: {
                "display_name": "Project",
                "description": "Project or workspace",
                "max_values": 15,
                "min_count": 1,
            },
            FacetType.REPOSITORY: {
                "display_name": "Repository",
                "description": "Source repository or code host",
                "max_values": 15,
                "min_count": 1,
            },
            FacetType.ENTITIES: {
                "display_name": "Entities",
                "description": "Named entities found in content",
                "max_values": 20,
                "min_count": 1,
            },
            FacetType.ENTITY_TYPES: {
                "display_name": "Entity Types",
                "description": "Types of named entities",
                "max_values": 15,
                "min_count": 1,
            },
            FacetType.TOPICS: {
                "display_name": "Topics",
                "description": "Topics and themes",
                "max_values": 15,
                "min_count": 1,
            },
            FacetType.KEY_PHRASES: {
                "display_name": "Key Phrases",
                "description": "Key phrases extracted from content",
                "max_values": 20,
                "min_count": 1,
            },
            FacetType.HIERARCHY_DEPTH: {
                "display_name": "Content Depth",
                "description": "Hierarchical depth in document structure",
                "max_values": 5,
                "min_count": 1,
            },
            FacetType.READ_TIME: {
                "display_name": "Reading Time",
                "description": "Estimated time to read",
                "max_values": 5,
                "min_count": 1,
            },
            FacetType.FILE_TYPE: {
                "display_name": "File Type",
                "description": "Original file type or format",
                "max_values": 10,
                "min_count": 1,
            },
        }

    def generate_facets(self, search_results: list[HybridSearchResult]) -> list[Facet]:
        """
        Generate dynamic facets from search results metadata.

        Args:
            search_results: List of search results to analyze

        Returns:
            List of generated facets with counts
        """
        start_time = datetime.now()

        if not search_results:
            return []

        facets = []

        # Generate each configured facet type
        for facet_type, config in self.facet_config.items():
            facet = self._generate_facet(facet_type, search_results, config)
            if facet and len(facet.values) > 0:
                facets.append(facet)

        # Sort facets by priority (most useful first)
        facets = self._sort_facets_by_priority(facets, search_results)

        generation_time = (datetime.now() - start_time).total_seconds() * 1000
        self.logger.debug(f"Generated {len(facets)} facets in {generation_time:.2f}ms")

        return facets

    def _generate_facet(
        self,
        facet_type: FacetType,
        search_results: list[HybridSearchResult],
        config: dict[str, Any],
    ) -> Facet | None:
        """Generate a specific facet from search results."""

        # Extract values for this facet type
        value_counts = Counter()

        for result in search_results:
            values = self._extract_facet_values(result, facet_type)
            for value in values:
                if value:  # Skip empty values
                    value_counts[value] += 1

        # Filter by minimum count
        min_count = config.get("min_count", 1)
        filtered_counts = {k: v for k, v in value_counts.items() if v >= min_count}

        if not filtered_counts:
            return None

        # Create facet values
        facet_values = []
        for value, count in filtered_counts.items():
            display_name = self._get_display_name(facet_type, value)
            description = self._get_value_description(facet_type, value)

            facet_values.append(
                FacetValue(
                    value=value,
                    count=count,
                    display_name=display_name,
                    description=description,
                )
            )

        # Limit to max values
        max_values = config.get("max_values", 10)
        facet_values = sorted(facet_values, key=lambda v: v.count, reverse=True)[
            :max_values
        ]

        return Facet(
            facet_type=facet_type,
            name=facet_type.value,
            display_name=config["display_name"],
            description=config.get("description"),
            values=facet_values,
            sort_by="count",
        )

    def _extract_facet_values(
        self, result: HybridSearchResult, facet_type: FacetType
    ) -> list[str]:
        """Extract values for a specific facet type from a search result."""

        if facet_type == FacetType.CONTENT_TYPE:
            return [result.source_type] if result.source_type else []

        elif facet_type == FacetType.SOURCE_TYPE:
            return [result.source_type] if result.source_type else []

        elif facet_type == FacetType.FILE_TYPE:
            file_type = result.get_file_type()
            return [file_type] if file_type else []

        elif facet_type == FacetType.HAS_FEATURES:
            features = []
            if result.has_code_blocks:
                features.append("code")
            if result.has_tables:
                features.append("tables")
            if result.has_images:
                features.append("images")
            if result.has_links:
                features.append("links")
            if result.is_attachment:
                features.append("attachment")
            return features

        elif facet_type == FacetType.PROJECT:
            values = []
            if result.project_name:
                values.append(result.project_name)
            if result.collection_name and result.collection_name != result.project_name:
                values.append(result.collection_name)
            return values

        elif facet_type == FacetType.REPOSITORY:
            return [result.repo_name] if result.repo_name else []

        elif facet_type == FacetType.ENTITIES:
            entities = []
            for entity in result.entities:
                if isinstance(entity, dict) and "text" in entity:
                    entities.append(entity["text"].lower().strip())
                elif isinstance(entity, str):
                    entities.append(entity.lower().strip())
            return [e for e in entities if len(e) >= 2]  # Filter very short entities

        elif facet_type == FacetType.ENTITY_TYPES:
            entity_types = []
            for entity in result.entities:
                if isinstance(entity, dict) and "label" in entity:
                    entity_types.append(entity["label"])
            return entity_types

        elif facet_type == FacetType.TOPICS:
            topics = []
            for topic in result.topics:
                if isinstance(topic, dict) and "text" in topic:
                    topics.append(topic["text"].lower().strip())
                elif isinstance(topic, str):
                    topics.append(topic.lower().strip())
            return [t for t in topics if len(t) > 2]  # Filter short topics

        elif facet_type == FacetType.KEY_PHRASES:
            phrases = []
            for phrase in result.key_phrases:
                if isinstance(phrase, dict) and "text" in phrase:
                    phrases.append(phrase["text"].lower().strip())
                elif isinstance(phrase, str):
                    phrases.append(phrase.lower().strip())
            return [p for p in phrases if len(p) > 3]  # Filter short phrases

        elif facet_type == FacetType.HIERARCHY_DEPTH:
            if result.depth is not None:
                if result.depth <= 2:
                    return ["shallow"]
                elif result.depth <= 4:
                    return ["medium"]
                else:
                    return ["deep"]
            return []

        elif facet_type == FacetType.SECTION_LEVEL:
            if result.section_level is not None:
                return [f"level_{result.section_level}"]
            return []

        elif facet_type == FacetType.SECTION_TYPE:
            return [result.section_type] if result.section_type else []

        elif facet_type == FacetType.READ_TIME:
            if result.estimated_read_time is not None:
                if result.estimated_read_time <= 2:
                    return ["quick"]
                elif result.estimated_read_time <= 10:
                    return ["medium"]
                else:
                    return ["long"]
            return []

        elif facet_type == FacetType.WORD_COUNT:
            if result.word_count is not None:
                if result.word_count <= 100:
                    return ["short"]
                elif result.word_count <= 500:
                    return ["medium"]
                else:
                    return ["long"]
            return []

        elif facet_type == FacetType.ATTACHMENT_TYPE:
            if result.is_attachment and result.mime_type:
                return [result.mime_type]
            return []

        elif facet_type == FacetType.CONVERSION_TYPE:
            if result.is_converted and result.conversion_method:
                return [result.conversion_method]
            return []

        elif facet_type == FacetType.CHUNKING_STRATEGY:
            return [result.chunking_strategy] if result.chunking_strategy else []

        return []

    def _get_display_name(self, facet_type: FacetType, value: str) -> str:
        """Get a human-readable display name for a facet value."""

        # Custom display names for specific facet types
        if facet_type == FacetType.HAS_FEATURES:
            feature_names = {
                "code": "Code Blocks",
                "tables": "Tables",
                "images": "Images",
                "links": "Links",
                "attachment": "Attachments",
            }
            return feature_names.get(value, value.title())

        elif facet_type == FacetType.HIERARCHY_DEPTH:
            depth_names = {
                "shallow": "Shallow (1-2 levels)",
                "medium": "Medium (3-4 levels)",
                "deep": "Deep (5+ levels)",
            }
            return depth_names.get(value, value.title())

        elif facet_type == FacetType.READ_TIME:
            time_names = {
                "quick": "Quick Read (≤2 min)",
                "medium": "Medium Read (3-10 min)",
                "long": "Long Read (10+ min)",
            }
            return time_names.get(value, value.title())

        elif facet_type == FacetType.WORD_COUNT:
            count_names = {
                "short": "Short (≤100 words)",
                "medium": "Medium (101-500 words)",
                "long": "Long (500+ words)",
            }
            return count_names.get(value, value.title())

        # Default: capitalize first letter
        return value.replace("_", " ").title()

    def _get_value_description(self, facet_type: FacetType, value: str) -> str | None:
        """Get a description for a facet value."""

        if facet_type == FacetType.HAS_FEATURES:
            descriptions = {
                "code": "Contains code blocks or snippets",
                "tables": "Contains structured data tables",
                "images": "Contains images or diagrams",
                "links": "Contains hyperlinks",
                "attachment": "File attachments",
            }
            return descriptions.get(value)

        return None

    def _sort_facets_by_priority(
        self, facets: list[Facet], search_results: list[HybridSearchResult]
    ) -> list[Facet]:
        """Sort facets by priority/usefulness for the current result set."""

        # Priority order - most useful facets first
        priority_order = [
            FacetType.CONTENT_TYPE,
            FacetType.PROJECT,
            FacetType.HAS_FEATURES,
            FacetType.ENTITIES,
            FacetType.TOPICS,
            FacetType.READ_TIME,
            FacetType.HIERARCHY_DEPTH,
            FacetType.FILE_TYPE,
            FacetType.SECTION_TYPE,
        ]

        # Create priority map
        priority_map = {facet_type: i for i, facet_type in enumerate(priority_order)}

        # Sort facets by priority, then by value count
        def facet_sort_key(facet: Facet) -> tuple[int, int]:
            priority = priority_map.get(facet.facet_type, 999)
            value_count = len(facet.values)
            return (priority, -value_count)  # Negative for descending count

        return sorted(facets, key=facet_sort_key)


class FacetedSearchEngine:
    """
    Faceted Search Engine

    Provides faceted search capabilities with filtering and refinement.
    Integrates with the existing HybridSearchEngine to add faceting layer.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.facet_generator = DynamicFacetGenerator()

    def apply_facet_filters(
        self, results: list[HybridSearchResult], filters: list[FacetFilter]
    ) -> list[HybridSearchResult]:
        """
        Apply facet filters to search results.

        Args:
            results: Original search results
            filters: List of facet filters to apply

        Returns:
            Filtered search results
        """
        if not filters:
            return results

        filtered_results = []

        for result in results:
            # Check if result matches ALL filters (AND logic between different facets)
            matches_all = True

            for filter_obj in filters:
                if not filter_obj.matches(result):
                    matches_all = False
                    break

            if matches_all:
                filtered_results.append(result)

        return filtered_results

    def generate_faceted_results(
        self,
        results: list[HybridSearchResult],
        applied_filters: list[FacetFilter] | None = None,
    ) -> FacetedSearchResults:
        """
        Generate faceted search results with facets and filtered results.

        Args:
            results: Original search results
            applied_filters: Currently applied filters

        Returns:
            FacetedSearchResults with facets and filtered results
        """
        start_time = datetime.now()

        applied_filters = applied_filters or []

        # Apply filters if any
        filtered_results = self.apply_facet_filters(results, applied_filters)

        # Generate facets from ALL results (not just filtered ones)
        # This allows users to see all available filter options
        facets = self.facet_generator.generate_facets(results)

        generation_time = (datetime.now() - start_time).total_seconds() * 1000

        return FacetedSearchResults(
            results=filtered_results,
            facets=facets,
            applied_filters=applied_filters,
            total_results=len(results),
            filtered_count=len(filtered_results),
            generation_time_ms=generation_time,
        )

    def create_filter_from_selection(
        self, facet_type: FacetType, selected_values: list[str], operator: str = "OR"
    ) -> FacetFilter:
        """Create a facet filter from user selections."""
        return FacetFilter(
            facet_type=facet_type, values=selected_values, operator=operator
        )

    def suggest_refinements(
        self,
        current_results: list[HybridSearchResult],
        current_filters: list[FacetFilter],
    ) -> list[dict[str, Any]]:
        """
        Suggest facet refinements based on current results and filters.

        Returns:
            List of suggested refinements with impact estimates
        """
        suggestions = []

        # Generate facets for current results
        facets = self.facet_generator.generate_facets(current_results)

        # Suggest filters that would significantly narrow results
        for facet in facets:
            # Skip facets that are already filtered
            if any(f.facet_type == facet.facet_type for f in current_filters):
                continue

            # Suggest top values that would filter to reasonable result count
            for facet_value in facet.get_top_values(3):
                # Estimate impact
                test_filter = FacetFilter(facet.facet_type, [facet_value.value])
                filtered_count = len(
                    self.apply_facet_filters(current_results, [test_filter])
                )

                if 0 < filtered_count < len(current_results) * 0.8:  # 20%+ reduction
                    suggestions.append(
                        {
                            "facet_type": facet.facet_type.value,
                            "facet_display_name": facet.display_name,
                            "value": facet_value.value,
                            "display_name": facet_value.display_name,
                            "current_count": len(current_results),
                            "filtered_count": filtered_count,
                            "reduction_percent": round(
                                (1 - filtered_count / len(current_results)) * 100
                            ),
                        }
                    )

        # Sort by usefulness (highest reduction first)
        suggestions.sort(key=lambda s: s["reduction_percent"], reverse=True)

        return suggestions[:5]  # Top 5 suggestions
