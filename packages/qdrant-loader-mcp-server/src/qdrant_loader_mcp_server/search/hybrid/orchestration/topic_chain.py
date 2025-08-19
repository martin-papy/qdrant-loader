from __future__ import annotations

from typing import Any, Dict, List

from ...enhanced.topic_search_chain import ChainStrategy, TopicSearchChain
from ...components.search_result_models import HybridSearchResult


async def generate_topic_search_chain(
    engine: Any,
    query: str,
    strategy: ChainStrategy = ChainStrategy.MIXED_EXPLORATION,
    max_links: int = 5,
    initialize_from_search: bool = True,
) -> TopicSearchChain:
    if initialize_from_search and not engine._topic_chains_initialized:
        await _initialize_topic_relationships(engine, query)
    return engine.topic_chain_generator.generate_search_chain(
        original_query=query, strategy=strategy, max_links=max_links
    )


async def execute_topic_chain_search(
    engine: Any,
    topic_chain: TopicSearchChain,
    results_per_link: int = 3,
    source_types: list[str] | None = None,
    project_ids: list[str] | None = None,
) -> Dict[str, List[HybridSearchResult]]:
    chain_results: Dict[str, List[HybridSearchResult]] = {}

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
        except Exception as e:  # noqa: F841 - keep behavior
            chain_results[link.query] = []

    return chain_results


async def _initialize_topic_relationships(engine: Any, sample_query: str) -> None:
    sample_results = await engine.search(
        query=sample_query, limit=20, source_types=None, project_ids=None
    )
    if sample_results:
        engine.topic_chain_generator.initialize_from_results(sample_results)
        engine._topic_chains_initialized = True


