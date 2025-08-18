from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def hybrid_search_with_intent(mock_qdrant_client, mock_openai_client):
    from qdrant_loader_mcp_server.search.hybrid_search import HybridSearchEngine

    return HybridSearchEngine(
        qdrant_client=mock_qdrant_client,
        openai_client=mock_openai_client,
        collection_name="test_collection",
        enable_intent_adaptation=True,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_with_intent_adaptation(hybrid_search_with_intent):
    hybrid_search_with_intent._get_embedding = AsyncMock(
        return_value=[0.1, 0.2, 0.3] * 512
    )
    hybrid_search_with_intent._expand_query = AsyncMock(return_value="test query")
    hybrid_search_with_intent._expand_query_aggressive = AsyncMock(
        return_value="aggressively expanded query"
    )

    # Mock intent classifier
    from qdrant_loader_mcp_server.search.enhanced.intent_classifier import (
        IntentType,
        SearchIntent,
    )

    mock_intent = SearchIntent(
        intent_type=IntentType.TECHNICAL_LOOKUP,
        confidence=0.95,
        is_question=True,
    )
    hybrid_search_with_intent.intent_classifier.classify_intent = MagicMock(
        return_value=mock_intent
    )

    # Mock adaptive strategy
    from qdrant_loader_mcp_server.search.enhanced.intent_classifier import (
        AdaptiveSearchConfig,
    )

    mock_adaptive_config = AdaptiveSearchConfig(
        vector_weight=0.7,
        keyword_weight=0.3,
        min_score_threshold=0.2,
        max_results=10,
        use_knowledge_graph=False,
        expand_query=False,
    )
    hybrid_search_with_intent.adaptive_strategy.adapt_search = MagicMock(
        return_value=mock_adaptive_config
    )

    results = await hybrid_search_with_intent.search(
        "test query", limit=5, session_context={"user": "x"}
    )

    # Verify intent classification and adaptation were called
    hybrid_search_with_intent.intent_classifier.classify_intent.assert_called_once()
    hybrid_search_with_intent.adaptive_strategy.adapt_search.assert_called_once()
    assert isinstance(results, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_with_aggressive_expansion(hybrid_search_with_intent):
    hybrid_search_with_intent._get_embedding = AsyncMock(
        return_value=[0.1, 0.2, 0.3] * 512
    )
    hybrid_search_with_intent._expand_query = AsyncMock(return_value="test query")
    hybrid_search_with_intent._expand_query_aggressive = AsyncMock(
        return_value="aggressive expansion"
    )

    from qdrant_loader_mcp_server.search.enhanced.intent_classifier import (
        IntentType,
        SearchIntent,
        AdaptiveSearchConfig,
    )

    mock_intent = SearchIntent(
        intent_type=IntentType.EXPLORATORY, confidence=0.9, is_question=True
    )
    hybrid_search_with_intent.intent_classifier.classify_intent = MagicMock(
        return_value=mock_intent
    )
    hybrid_search_with_intent.adaptive_strategy.adapt_search = MagicMock(
        return_value=AdaptiveSearchConfig(
            vector_weight=0.6,
            keyword_weight=0.4,
            min_score_threshold=0.2,
            max_results=10,
            use_knowledge_graph=True,
            expand_query=True,
            expansion_aggressiveness=0.8,
        )
    )

    await hybrid_search_with_intent.search("broad search query")
    hybrid_search_with_intent._expand_query_aggressive.assert_called_once_with(
        "broad search query"
    )


@pytest.mark.unit
def test_get_adaptive_search_stats(hybrid_search_with_intent):
    hybrid_search_with_intent.intent_classifier.get_cache_stats = MagicMock(
        return_value={"calls": 1}
    )
    hybrid_search_with_intent.adaptive_strategy.get_strategy_stats = MagicMock(
        return_value={"rules": 2}
    )

    stats = hybrid_search_with_intent.get_adaptive_search_stats()
    assert stats["intent_adaptation_enabled"] is True
    assert "calls" in stats
    assert "rules" in stats


@pytest.fixture
def hybrid_search_disabled_intent(mock_qdrant_client, mock_openai_client):
    from qdrant_loader_mcp_server.search.hybrid_search import HybridSearchEngine

    return HybridSearchEngine(
        qdrant_client=mock_qdrant_client,
        openai_client=mock_openai_client,
        collection_name="test_collection",
        enable_intent_adaptation=False,
    )


@pytest.mark.unit
def test_get_adaptive_search_stats_disabled(hybrid_search_disabled_intent):
    stats = hybrid_search_disabled_intent.get_adaptive_search_stats()
    assert stats["intent_adaptation_enabled"] is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_with_intent_adaptation_error_handling(hybrid_search_with_intent):
    hybrid_search_with_intent._get_embedding = AsyncMock(
        return_value=[0.1, 0.2, 0.3] * 512
    )
    hybrid_search_with_intent._expand_query = AsyncMock(return_value="test query")

    # Force intent classifier to raise
    hybrid_search_with_intent.intent_classifier.classify_intent = MagicMock(
        side_effect=Exception("Intent classification failed")
    )

    with pytest.raises(Exception, match="Intent classification failed"):
        await hybrid_search_with_intent.search("test query")
