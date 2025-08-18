from unittest.mock import AsyncMock

import pytest

from qdrant_loader_mcp_server.search.components.search_result_models import (
    create_hybrid_search_result,
)
from qdrant_loader_mcp_server.search.enhanced.topic_search_chain import (
    ChainStrategy,
    TopicChainLink,
    TopicSearchChain,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_topic_chain_execution_with_failures(hybrid_search):
    """Execute a topic chain where one link fails; ensure robust handling."""
    mock_chain = TopicSearchChain(
        original_query="API documentation",
        chain_links=[
            TopicChainLink(
                query="working query",
                topic_focus="API",
                related_topics=["REST"],
                chain_position=1,
                relevance_score=0.8,
                exploration_type="related",
            ),
            TopicChainLink(
                query="failing query",
                topic_focus="security",
                related_topics=["auth"],
                chain_position=2,
                relevance_score=0.6,
                exploration_type="deeper",
            ),
        ],
        strategy=ChainStrategy.MIXED_EXPLORATION,
        total_topics_covered=3,
        estimated_discovery_potential=0.7,
        generation_time_ms=150.0,
    )

    async def mock_search_with_failures(query, limit, source_types=None, project_ids=None):
        if query == "API documentation":
            return [
                create_hybrid_search_result(
                    score=0.9,
                    text="API docs",
                    source_type="git",
                    source_title="API Guide",
                )
            ]
        elif query == "working query":
            return [
                create_hybrid_search_result(
                    score=0.8,
                    text="Working result",
                    source_type="confluence",
                    source_title="Working Page",
                )
            ]
        else:
            raise Exception("Search failed for query: failing query")

    hybrid_search.search = AsyncMock(side_effect=mock_search_with_failures)

    results = await hybrid_search.execute_topic_chain_search(
        topic_chain=mock_chain, results_per_link=1
    )

    # Should have results for both the original query and each link (failed link yields empty list)
    assert "API documentation" in results
    assert "working query" in results
    assert "failing query" in results
    assert len(results["API documentation"]) == 1
    assert len(results["working query"]) == 1
    assert results["failing query"] == []


