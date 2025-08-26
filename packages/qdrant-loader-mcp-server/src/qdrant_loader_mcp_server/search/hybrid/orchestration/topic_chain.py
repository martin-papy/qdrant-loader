from __future__ import annotations

import inspect
from typing import Any

from ...components.search_result_models import HybridSearchResult
from ...enhanced.topic_search_chain import ChainStrategy, TopicSearchChain


async def generate_topic_search_chain(
    engine: Any,
    query: str,
    strategy: ChainStrategy = ChainStrategy.MIXED_EXPLORATION,
    max_links: int = 5,
    initialize_from_search: bool = True,
) -> TopicSearchChain:
    # Use public accessor instead of private attribute
    if initialize_from_search:
        try:
            init_attr = getattr(engine, "is_topic_chains_initialized", False)
            is_initialized: bool
            if callable(init_attr):
                init_result = init_attr()
                if inspect.isawaitable(init_result):
                    init_result = await init_result
                is_initialized = bool(init_result)
            else:
                is_initialized = bool(init_attr)
        except Exception:
            # Be conservative: if we cannot determine, assume not initialized
            is_initialized = False
        if not is_initialized:
            await _initialize_topic_relationships(engine, query)
    result = engine.topic_chain_generator.generate_search_chain(
        original_query=query, strategy=strategy, max_links=max_links
    )
    if inspect.isawaitable(result):
        return await result
    return result


async def execute_topic_chain_search(
    engine: Any,
    topic_chain: TopicSearchChain,
    results_per_link: int = 3,
    source_types: list[str] | None = None,
    project_ids: list[str] | None = None,
) -> dict[str, list[HybridSearchResult]]:
    chain_results: dict[str, list[HybridSearchResult]] = {}

    original_results = await engine.search(
        query=topic_chain.original_query,
        limit=results_per_link,
        source_types=source_types,
        project_ids=project_ids,
    )
    chain_results[topic_chain.original_query] = original_results

    for link in topic_chain.chain_links:
        try:
            link_results = await engine.search(
                query=link.query,
                limit=results_per_link,
                source_types=source_types,
                project_ids=project_ids,
            )
            chain_results[link.query] = link_results
        except Exception:
            # Log the exception with context; include traceback
            engine.logger.exception(
                "Error running topic chain for query=%s", link.query
            )
            chain_results[link.query] = []

    return chain_results


async def _initialize_topic_relationships(engine: Any, sample_query: str) -> None:
    sample_results = await engine.search(
        query=sample_query, limit=20, source_types=None, project_ids=None
    )
    if sample_results:
        engine.topic_chain_generator.initialize_from_results(sample_results)
        # Mark initialization via public API instead of touching private attribute
        if hasattr(engine, "set_topic_chains_initialized"):
            engine.set_topic_chains_initialized(True)
        else:
            engine.mark_topic_chains_initialized()
