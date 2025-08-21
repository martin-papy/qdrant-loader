from __future__ import annotations

from typing import Any, List

from ...components.search_result_models import HybridSearchResult


async def run_search(
    engine: Any,
    query: str,
    limit: int,
    source_types: list[str] | None,
    project_ids: list[str] | None,
    session_context: dict[str, Any] | None,
    behavioral_context: list[str] | None,
) -> list[HybridSearchResult]:
    # Intent classification and adaptive adjustments
    search_intent = None
    adaptive_config = None
    original_vector_weight = engine.result_combiner.vector_weight
    original_keyword_weight = engine.result_combiner.keyword_weight
    original_min_score = engine.result_combiner.min_score

    if engine.enable_intent_adaptation and engine.intent_classifier:
        search_intent = engine.intent_classifier.classify_intent(
            query, session_context, behavioral_context
        )
        adaptive_config = engine.adaptive_strategy.adapt_search(search_intent, query)
        if adaptive_config:
            engine.result_combiner.vector_weight = adaptive_config.vector_weight
            engine.result_combiner.keyword_weight = adaptive_config.keyword_weight
            engine.result_combiner.min_score = adaptive_config.min_score_threshold
            limit = min(adaptive_config.max_results, limit * 2)

    expanded_query = await engine._expand_query(query)
    if adaptive_config and getattr(adaptive_config, "expand_query", False):
        aggressiveness = getattr(adaptive_config, "expansion_aggressiveness", None)
        if isinstance(aggressiveness, (int, float)) and aggressiveness > 0.5:
            expanded_query = await engine._expand_query_aggressive(query)

    query_context = engine._analyze_query(query)
    if search_intent:
        query_context["search_intent"] = search_intent
        query_context["adaptive_config"] = adaptive_config

    plan = engine._planner.make_plan(
        has_pipeline=engine.hybrid_pipeline is not None, expanded_query=expanded_query
    )

    if plan.use_pipeline and engine.hybrid_pipeline is not None:
        combined_results = await engine._orchestrator.run_pipeline(
            engine.hybrid_pipeline,
            query=query,
            limit=limit,
            query_context=query_context,
            source_types=source_types,
            project_ids=project_ids,
            vector_query=plan.expanded_query,
            keyword_query=query,
        )
    else:
        vector_results = await engine._vector_search(expanded_query, limit * 3, project_ids)
        keyword_results = await engine._keyword_search(query, limit * 3, project_ids)
        combined_results = await engine._combine_results(
            vector_results,
            keyword_results,
            query_context,
            limit,
            source_types,
            project_ids,
        )

    if adaptive_config:
        engine.result_combiner.vector_weight = original_vector_weight
        engine.result_combiner.keyword_weight = original_keyword_weight
        engine.result_combiner.min_score = original_min_score

    return combined_results


