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
    # Save original combiner values up front for safe restoration
    original_vector_weight = engine.result_combiner.vector_weight
    original_keyword_weight = engine.result_combiner.keyword_weight
    original_min_score = engine.result_combiner.min_score

    combined_results: list[HybridSearchResult]

    try:
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
            adaptive_config = engine.adaptive_strategy.adapt_search(
                search_intent, query
            )
            if adaptive_config:
                local_combiner.vector_weight = adaptive_config.vector_weight
                local_combiner.keyword_weight = adaptive_config.keyword_weight
                local_combiner.min_score = adaptive_config.min_score_threshold
                limit = min(adaptive_config.max_results, limit * 2)

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

        # Ensure combiner threshold honors engine-level minimum when applicable
        engine_min_score = getattr(engine, "min_score", None)
        if engine_min_score is not None and (
            getattr(local_combiner, "min_score", None) is None
            or local_combiner.min_score < engine_min_score
        ):
            # Use the stricter (higher) engine threshold
            local_combiner.min_score = engine_min_score

        if plan.use_pipeline and engine.hybrid_pipeline is not None:
            p = engine.hybrid_pipeline
            if isinstance(p, HybridPipeline):
                # Clone pipeline for this request with the local combiner to avoid shared mutation
                local_pipeline = HybridPipeline(
                    vector_searcher=p.vector_searcher,
                    keyword_searcher=p.keyword_searcher,
                    result_combiner=local_combiner,
                    reranker=p.reranker,
                    booster=p.booster,
                    normalizer=p.normalizer,
                    deduplicator=p.deduplicator,
                )
                combined_results = await engine._orchestrator.run_pipeline(
                    local_pipeline,
                    query=query,
                    limit=limit,
                    query_context=query_context,
                    source_types=source_types,
                    project_ids=project_ids,
                    vector_query=plan.expanded_query,
                    keyword_query=query,
                )
            else:
                # Custom or mocked pipeline: honor its run override without cloning
                combined_results = await engine._orchestrator.run_pipeline(
                    p,
                    query=query,
                    limit=limit,
                    query_context=query_context,
                    source_types=source_types,
                    project_ids=project_ids,
                    vector_query=plan.expanded_query,
                    keyword_query=query,
                )
        else:
            vector_results = await engine._vector_search(
                expanded_query, limit * 3, project_ids
            )
            keyword_results = await engine._keyword_search(
                query, limit * 3, project_ids
            )
            combined_results = await _combine_results_helper(
                local_combiner,
                getattr(engine, "min_score", 0.0),
                vector_results,
                keyword_results,
                query_context,
                limit,
                source_types,
                project_ids,
            )
    finally:
        # Always attempt to restore engine combiner settings to their original values.
        # Log any restoration failures with context, without masking original exceptions.
        try:
            engine_rc = getattr(engine, "result_combiner", None)
            if engine_rc is not None:
                restorations = [
                    ("vector_weight", original_vector_weight),
                    ("keyword_weight", original_keyword_weight),
                    ("min_score", original_min_score),
                ]
                for attr_name, original_value in restorations:
                    try:
                        setattr(engine_rc, attr_name, original_value)
                    except Exception as e:  # noqa: F841 - keep behavior
                        try:
                            logger.error(
                                "Failed to restore result_combiner.%s to %r on %s: %s",
                                attr_name,
                                original_value,
                                type(engine_rc).__name__,
                                e,
                                exc_info=True,
                            )
                        except Exception:
                            # Never allow logging to raise
                            pass
        except Exception:
            # Never raise from restoration; preserve original exception flow
            try:
                logger.error(
                    "Unexpected error during result_combiner restoration on %s",
                    type(getattr(engine, "result_combiner", object())).__name__,
                    exc_info=True,
                )
            except Exception:
                pass

    return combined_results
