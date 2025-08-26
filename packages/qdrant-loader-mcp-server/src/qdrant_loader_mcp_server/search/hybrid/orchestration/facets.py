from __future__ import annotations

from datetime import datetime
from typing import Any

from ...enhanced.faceted_search import FacetedSearchResults, FacetFilter


async def search_with_facets(
    engine: Any,
    query: str,
    limit: int = 5,
    source_types: list[str] | None = None,
    project_ids: list[str] | None = None,
    facet_filters: list[FacetFilter] | None = None,
    generate_facets: bool = True,
    session_context: dict[str, Any] | None = None,
    behavioral_context: list[str] | None = None,
) -> FacetedSearchResults:
    """Perform faceted search with dynamic facet generation using the provided engine."""
    start_time = datetime.now()

    # First, perform regular search (potentially with larger limit for faceting)
    search_limit = max(limit * 2, 50) if generate_facets else limit

    search_results = await engine.search(
        query=query,
        limit=search_limit,
        source_types=source_types,
        project_ids=project_ids,
        session_context=session_context,
        behavioral_context=behavioral_context,
    )

    # Generate faceted results
    faceted_results = engine.faceted_search_engine.generate_faceted_results(
        results=search_results, applied_filters=facet_filters or []
    )

    # Limit final results
    faceted_results.results = faceted_results.results[:limit]
    faceted_results.filtered_count = len(faceted_results.results)

    search_time = (datetime.now() - start_time).total_seconds() * 1000

    engine.logger.info(
        "Faceted search completed",
        query=query,
        total_results=faceted_results.total_results,
        filtered_results=faceted_results.filtered_count,
        facet_count=len(faceted_results.facets),
        active_filters=len(faceted_results.applied_filters),
        search_time_ms=round(search_time, 2),
    )

    return faceted_results
