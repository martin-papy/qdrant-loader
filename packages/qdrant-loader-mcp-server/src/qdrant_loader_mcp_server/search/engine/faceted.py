"""
Faceted Search Operations.

This module implements faceted search functionality with dynamic
facet generation and interactive filtering capabilities.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import SearchEngine

from ...utils.logging import LoggingConfig
from ..components.search_result_models import HybridSearchResult

logger = LoggingConfig.get_logger(__name__)


class FacetedSearchOperations:
    """Handles faceted search operations."""

    def __init__(self, engine: "SearchEngine"):
        """Initialize with search engine reference."""
        self.engine = engine
        self.logger = LoggingConfig.get_logger(__name__)

    async def search_with_facets(
        self,
        query: str,
        limit: int = 5,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
        facet_filters: list[dict] | None = None,
    ) -> dict:
        """
        Perform faceted search with dynamic facet generation.

        Returns search results with generated facets for interactive filtering.

        Args:
            query: Search query
            limit: Maximum number of results to return
            source_types: Optional list of source types to filter by
            project_ids: Optional list of project IDs to filter by
            facet_filters: Optional list of facet filters to apply

        Returns:
            Dictionary containing:
            - results: List of search results
            - facets: List of generated facets with counts
            - total_results: Total results before facet filtering
            - filtered_count: Results after facet filtering
            - applied_filters: Currently applied facet filters
        """
        if not self.engine.hybrid_search:
            raise RuntimeError("Search engine not initialized")

        try:
            # Convert facet filter dictionaries to FacetFilter objects if provided
            filter_objects = []
            if facet_filters:
                from ..enhanced.faceted_search import FacetFilter, FacetType

                for filter_dict in facet_filters:
                    try:
                        facet_type = FacetType(filter_dict["facet_type"])
                    except (ValueError, TypeError) as e:
                        self.logger.warning(
                            "Invalid facet_type provided; skipping facet filter",
                            facet_type=str(filter_dict.get("facet_type")),
                            error=str(e),
                            exc_info=True,
                        )
                        continue

                    # Validate and normalize values
                    values_raw = filter_dict.get("values")
                    if not values_raw:
                        self.logger.warning(
                            "Missing or empty 'values' for facet filter; skipping",
                            facet_type=facet_type.value,
                        )
                        continue
                    if isinstance(values_raw, (set, tuple)):
                        values = list(values_raw)
                    elif isinstance(values_raw, list):
                        values = values_raw
                    else:
                        values = [values_raw]

                    # Validate operator
                    allowed_operators = {"OR", "AND"}
                    operator = str(filter_dict.get("operator", "OR")).upper()
                    if operator not in allowed_operators:
                        self.logger.warning(
                            "Invalid operator for facet filter; defaulting to 'OR'",
                            operator=str(filter_dict.get("operator")),
                        )
                        operator = "OR"

                    filter_objects.append(
                        FacetFilter(
                            facet_type=facet_type,
                            values=values,
                            operator=operator,
                        )
                    )

            faceted_results = await self.engine.hybrid_search.search_with_facets(
                query=query,
                limit=limit,
                source_types=source_types,
                project_ids=project_ids,
                facet_filters=filter_objects,
                generate_facets=True,
            )

            # Convert to MCP-friendly format
            return {
                "results": faceted_results.results,
                "facets": [
                    {
                        "type": facet.facet_type.value,
                        "name": facet.name,
                        "display_name": facet.display_name,
                        "description": facet.description,
                        "values": [
                            {
                                "value": fv.value,
                                "count": fv.count,
                                "display_name": fv.display_name,
                                "description": fv.description,
                            }
                            for fv in facet.get_top_values(10)
                        ],
                    }
                    for facet in faceted_results.facets
                ],
                "total_results": faceted_results.total_results,
                "filtered_count": faceted_results.filtered_count,
                "applied_filters": [
                    {
                        "facet_type": f.facet_type.value,
                        "values": f.values,
                        "operator": f.operator,
                    }
                    for f in faceted_results.applied_filters
                ],
                "generation_time_ms": faceted_results.generation_time_ms,
            }

        except Exception as e:
            self.logger.error("Faceted search failed", error=str(e), query=query)
            raise

    async def get_facet_suggestions(
        self,
        documents: list[HybridSearchResult],
        max_facets_per_type: int = 5,
        enable_dynamic_generation: bool = True,
    ) -> dict:
        """
        Generate facet suggestions from a collection of documents.

        Analyzes document metadata to suggest useful facets for filtering.

        Args:
            documents: List of documents to analyze
            max_facets_per_type: Maximum facets to generate per type
            enable_dynamic_generation: Whether to enable AI-powered facet generation

        Returns:
            Dictionary containing:
            - suggested_facets: List of facet suggestions with metadata
            - facet_coverage: Coverage statistics for each facet type
            - generation_metadata: Information about facet generation process
        """
        if not self.engine.hybrid_search:
            raise RuntimeError("Search engine not initialized")

        try:
            # Use the hybrid search engine to generate facet suggestions
            from ..enhanced.faceted_search import DynamicFacetGenerator

            facet_generator = DynamicFacetGenerator()
            
            suggestions = await facet_generator.generate_facets_from_documents(
                documents=documents,
                max_facets_per_type=max_facets_per_type,
                enable_ai_generation=enable_dynamic_generation,
            )

            # Calculate coverage statistics
            coverage_stats = self._calculate_facet_coverage(documents, suggestions)

            return {
                "suggested_facets": [
                    {
                        "type": facet.facet_type.value,
                        "name": facet.name,
                        "display_name": facet.display_name,
                        "description": facet.description,
                        "coverage_percentage": coverage_stats.get(facet.name, 0),
                        "unique_values": len(facet.values),
                        "top_values": [
                            {
                                "value": fv.value,
                                "count": fv.count,
                                "display_name": fv.display_name,
                            }
                            for fv in facet.get_top_values(5)
                        ],
                    }
                    for facet in suggestions.facets
                ],
                "facet_coverage": coverage_stats,
                "generation_metadata": {
                    "total_documents_analyzed": len(documents),
                    "facet_types_generated": len(set(f.facet_type for f in suggestions.facets)),
                    "total_facets_generated": len(suggestions.facets),
                    "generation_time_ms": suggestions.generation_time_ms,
                    "ai_generation_enabled": enable_dynamic_generation,
                },
            }

        except Exception as e:
            self.logger.error("Facet suggestion generation failed", error=str(e))
            raise

    def _calculate_facet_coverage(
        self, documents: list[HybridSearchResult], suggestions
    ) -> dict[str, float]:
        """Calculate coverage statistics for generated facets."""
        if not documents:
            return {}

        coverage_stats = {}
        total_docs = len(documents)

        for facet in suggestions.facets:
            # Calculate how many documents have values for this facet
            covered_count = 0
            facet_name = facet.name.lower()

            for doc in documents:
                # Check various document attributes that might match this facet
                has_value = False
                
                # Source type facet
                if "source" in facet_name and hasattr(doc, "source_type"):
                    has_value = bool(doc.source_type)
                    
                # Project facet  
                elif "project" in facet_name and hasattr(doc, "project_id"):
                    has_value = bool(doc.project_id)
                    
                # Date/time facets
                elif any(time_word in facet_name for time_word in ["date", "time", "created"]):
                    has_value = bool(getattr(doc, "created_at", None))
                    
                # Content type facets
                elif "content" in facet_name or "type" in facet_name:
                    has_value = bool(getattr(doc, "content_type", None))
                    
                # Topic facets
                elif "topic" in facet_name:
                    has_value = bool(getattr(doc, "topics", None))
                    
                # Entity facets
                elif "entity" in facet_name:
                    has_value = bool(getattr(doc, "entities", None))
                    
                # Default: check if document has any relevant metadata
                else:
                    has_value = True  # Assume coverage for unknown facet types

                if has_value:
                    covered_count += 1

            coverage_percentage = (covered_count / total_docs) * 100
            coverage_stats[facet.name] = round(coverage_percentage, 1)

        return coverage_stats
