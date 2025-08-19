from __future__ import annotations

from typing import Any, List

from ...components.search_result_models import HybridSearchResult


def suggest_refinements(engine: Any, results: List[HybridSearchResult], filters: list) -> list[dict[str, Any]]:
    """Delegate to FacetedSearchEngine.suggest_refinements."""
    return engine.suggest_refinements(results, filters)


def generate_facets(engine: Any, results: List[HybridSearchResult]) -> list:
    """Delegate to facet generator to produce facets for results."""
    return engine.facet_generator.generate_facets(results)


