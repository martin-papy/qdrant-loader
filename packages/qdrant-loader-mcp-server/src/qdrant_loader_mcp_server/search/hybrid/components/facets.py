from __future__ import annotations

from typing import Any, TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from ...components.models import HybridSearchResult


def suggest_refinements(engine: Any, results: Sequence["HybridSearchResult"], filters: list) -> list[dict[str, Any]]:
    """Delegate to FacetedSearchEngine.suggest_refinements."""
    return engine.suggest_refinements(results, filters)


def generate_facets(engine: Any, results: Sequence["HybridSearchResult"]) -> list:
    """Delegate to facet generator to produce facets for results."""
    return engine.facet_generator.generate_facets(results)


