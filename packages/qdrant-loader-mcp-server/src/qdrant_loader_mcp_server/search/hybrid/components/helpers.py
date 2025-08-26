from __future__ import annotations

from typing import Any


async def get_embedding(vector_search_service: Any, text: str) -> list[float]:
    return await vector_search_service.get_embedding(text)


def analyze_query(query_processor: Any, query: str) -> dict[str, Any]:
    return query_processor.analyze_query(query)


async def expand_query(query_processor: Any, query: str) -> str:
    return await query_processor.expand_query(query)


async def expand_query_aggressive(query_processor: Any, query: str) -> str:
    return await query_processor.expand_query_aggressive(query)


async def vector_search(
    vector_search_service: Any, query: str, limit: int, project_ids: list[str] | None
) -> list[dict[str, Any]]:
    return await vector_search_service.vector_search(query, limit, project_ids)


async def keyword_search(
    keyword_search_service: Any, query: str, limit: int, project_ids: list[str] | None
) -> list[dict[str, Any]]:
    return await keyword_search_service.keyword_search(query, limit, project_ids)


async def combine_results(
    result_combiner: Any,
    engine_min_score: float,
    vector_results: list[dict[str, Any]],
    keyword_results: list[dict[str, Any]],
    query_context: dict[str, Any],
    limit: int,
    source_types: list[str] | None,
    project_ids: list[str] | None,
):
    previous_min_score = getattr(result_combiner, "min_score", None)
    should_override = (
        previous_min_score is None or previous_min_score > engine_min_score
    )
    if should_override:
        result_combiner.min_score = engine_min_score
    try:
        return await result_combiner.combine_results(
            vector_results,
            keyword_results,
            query_context,
            limit,
            source_types,
            project_ids,
        )
    finally:
        if should_override:
            result_combiner.min_score = previous_min_score


def build_filter(vector_search_service: Any, project_ids: list[str] | None) -> Any:
    # Use public API on the service to avoid relying on private methods
    return vector_search_service.build_filter(project_ids)
