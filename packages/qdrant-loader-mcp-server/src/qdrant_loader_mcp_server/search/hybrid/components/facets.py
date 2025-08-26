from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...components.models import HybridSearchResult


def suggest_refinements(
    engine: Any, results: Sequence[HybridSearchResult], filters: list
) -> list[dict[str, Any]]:
    """Delegate to FacetedSearchEngine.suggest_refinements."""
    # Runtime validation to provide immediate, actionable errors
    if not hasattr(engine, "suggest_refinements"):
        raise AttributeError(
            "Engine is missing required method 'suggest_refinements(results, filters)'."
        )
    if not callable(engine.suggest_refinements):
        raise TypeError("Engine.suggest_refinements must be callable.")

    return engine.suggest_refinements(results, filters)


def generate_facets(engine: Any, results: Sequence[HybridSearchResult]) -> list:
    """Delegate to facet generator to produce facets for results."""
    # Runtime validation to ensure facet generator capability exists
    if not hasattr(engine, "facet_generator"):
        raise AttributeError("Engine is missing required attribute 'facet_generator'.")
    facet_generator = engine.facet_generator
    if not hasattr(facet_generator, "generate_facets"):
        raise AttributeError(
            "Engine.facet_generator is missing required method 'generate_facets(results)'."
        )
    if not callable(facet_generator.generate_facets):
        raise TypeError("Engine.facet_generator.generate_facets must be callable.")

    return facet_generator.generate_facets(results)
