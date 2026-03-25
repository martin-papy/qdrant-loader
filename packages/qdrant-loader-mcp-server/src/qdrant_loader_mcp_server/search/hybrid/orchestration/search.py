from __future__ import annotations

import logging
from typing import Any

from ...components.result_combiner import ResultCombiner
from ...components.search_result_models import HybridSearchResult
from ..components.helpers import combine_results as _combine_results_helper
from ..pipeline import HybridPipeline

logger = logging.getLogger(__name__)


async def run_search(
    engine: Any,
    query: str,
    limit: int,
    source_types: list[str] | None,
    project_ids: list[str] | None,
    session_context: dict[str, Any] | None,
    behavioral_context: list[str] | None,
) -> list[HybridSearchResult]:
    """
    Execute a hybrid search for the given query using the provided engine and return ranked results.

    Per-request adjustments (query expansion, intent-adaptive combiner weights, and fetch limits)
    are applied to a request-scoped combiner clone and never mutate the engine's shared state.

    Parameters:
        engine: Search engine instance providing hybrid search, planners, expansion, and orchestration.
        query (str): The user query to search for.
        limit (int): Maximum number of results to return.
        source_types (list[str] | None): Optional list of source types to filter results.
        project_ids (list[str] | None): Optional list of project IDs to restrict the search.
        session_context (dict[str, Any] | None): Optional session-level context used for intent classification and adaptations.
        behavioral_context (list[str] | None): Optional behavioral signals used for intent classification and adaptations.

    Returns:
        list[HybridSearchResult]: Ranked hybrid search results; length will be at most `limit`.
    """
    combined_results: list[HybridSearchResult]
    fetch_limit = limit

    # Build a request-scoped combiner clone to avoid mutating shared engine state
    base_combiner = engine.result_combiner
    local_combiner = ResultCombiner(
        vector_weight=getattr(base_combiner, "vector_weight", 0.6),
        keyword_weight=getattr(base_combiner, "keyword_weight", 0.3),
        metadata_weight=getattr(base_combiner, "metadata_weight", 0.1),
        min_score=getattr(base_combiner, "min_score", 0.3),
        spacy_analyzer=getattr(base_combiner, "spacy_analyzer", None),
    )

    # Intent classification and adaptive adjustments (applied to local combiner only)
    search_intent = None
    adaptive_config = None
    if engine.enable_intent_adaptation and engine.intent_classifier:
        search_intent = engine.intent_classifier.classify_intent(
            query, session_context, behavioral_context
        )
        adaptive_config = engine.adaptive_strategy.adapt_search(search_intent, query)
        if adaptive_config:
            local_combiner.vector_weight = adaptive_config.vector_weight
            local_combiner.keyword_weight = adaptive_config.keyword_weight
            local_combiner.min_score = adaptive_config.min_score_threshold
            fetch_limit = min(adaptive_config.max_results, limit * 2)

    # TODO: Evaluate the expanded_query logic to see it's impacts on vector and keyword searches
    expanded_query = await engine._expand_query(query)
    if adaptive_config and getattr(adaptive_config, "expand_query", False):
        aggressiveness = getattr(adaptive_config, "expansion_aggressiveness", None)
        if isinstance(aggressiveness, int | float) and aggressiveness > 0.5:
            expanded_query = await engine._expand_query_aggressive(query)

    query_context = engine._analyze_query(query)
    if search_intent:
        query_context["search_intent"] = search_intent
        query_context["adaptive_config"] = adaptive_config

    plan = engine._planner.make_plan(
        has_pipeline=engine.hybrid_pipeline is not None,
        expanded_query=expanded_query,
    )

    resolved_vector_query = plan.expanded_query
    resolved_keyword_query = query

    # Ensure combiner threshold honors engine-level minimum when applicable
    engine_min_score = getattr(engine, "min_score", None)
    if engine_min_score is not None and (
        getattr(local_combiner, "min_score", None) is None
        or local_combiner.min_score < engine_min_score
    ):
        # Use the stricter (higher) engine threshold
        local_combiner.min_score = engine_min_score

    if plan.use_pipeline and engine.hybrid_pipeline is not None:
        hybrid_pipeline: HybridPipeline = engine.hybrid_pipeline
        if isinstance(hybrid_pipeline, HybridPipeline):
            # Clone pipeline for this request with the local combiner to avoid shared mutation
            local_pipeline = HybridPipeline(
                vector_searcher=hybrid_pipeline.vector_searcher,
                keyword_searcher=hybrid_pipeline.keyword_searcher,
                result_combiner=local_combiner,
                reranker=hybrid_pipeline.reranker,
                booster=hybrid_pipeline.booster,
                normalizer=hybrid_pipeline.normalizer,
                deduplicator=hybrid_pipeline.deduplicator,
            )
            combined_results = await engine._orchestrator.run_pipeline(
                local_pipeline,
                query=query,
                limit=fetch_limit,
                query_context=query_context,
                source_types=source_types,
                project_ids=project_ids,
                vector_query=resolved_vector_query,
                keyword_query=resolved_keyword_query,
            )
        else:
            # Custom or mocked pipeline: honor its run override without cloning
            combined_results = await engine._orchestrator.run_pipeline(
                hybrid_pipeline,
                query=query,
                limit=fetch_limit,
                query_context=query_context,
                source_types=source_types,
                project_ids=project_ids,
                vector_query=resolved_vector_query,
                keyword_query=resolved_keyword_query,
            )
    else:
        vector_results = await engine._vector_search(
            expanded_query, fetch_limit * 3, project_ids
        )
        keyword_results = await engine._keyword_search(
            query, fetch_limit * 3, project_ids
        )
        combined_results = await _combine_results_helper(
            local_combiner,
            getattr(engine, "min_score", 0.0),
            vector_results,
            keyword_results,
            query_context,
            fetch_limit,
            source_types,
            project_ids,
        )

    return combined_results[:limit]
