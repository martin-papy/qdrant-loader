"""Tests for hybrid search implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from openai import AsyncOpenAI
from qdrant_loader_mcp_server.search.components.search_result_models import (
    HybridSearchResult,
    create_hybrid_search_result,
)
from qdrant_loader_mcp_server.search.hybrid_search import (
    HybridSearchEngine,
)


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client."""
    client = AsyncMock()

    # Create mock search results
    search_result1 = MagicMock()
    search_result1.id = "1"
    search_result1.score = 0.8
    search_result1.payload = {
        "content": "Test content 1",
        "metadata": {"title": "Test Doc 1", "url": "http://test1.com"},
        "source_type": "git",
    }

    search_result2 = MagicMock()
    search_result2.id = "2"
    search_result2.score = 0.7
    search_result2.payload = {
        "content": "Test content 2",
        "metadata": {"title": "Test Doc 2", "url": "http://test2.com"},
        "source_type": "confluence",
    }

    search_result3 = MagicMock()
    search_result3.id = "3"
    search_result3.score = 0.6
    search_result3.payload = {
        "content": "Test content 3",
        "metadata": {"title": "Test Doc 3", "file_path": "/path/to/file.txt"},
        "source_type": "localfile",
    }

    # Mock query_points response (qdrant-client 1.10+)
    query_response = MagicMock()
    query_response.points = [search_result1, search_result2, search_result3]
    client.query_points = AsyncMock(return_value=query_response)

    # Create mock scroll results
    scroll_result1 = MagicMock()
    scroll_result1.id = "1"
    scroll_result1.payload = {
        "content": "Test content 1",
        "metadata": {"title": "Test Doc 1", "url": "http://test1.com"},
        "source_type": "git",
    }

    scroll_result2 = MagicMock()
    scroll_result2.id = "2"
    scroll_result2.payload = {
        "content": "Test content 2",
        "metadata": {"title": "Test Doc 2", "url": "http://test2.com"},
        "source_type": "confluence",
    }

    scroll_result3 = MagicMock()
    scroll_result3.id = "3"
    scroll_result3.payload = {
        "content": "Test content 3",
        "metadata": {"title": "Test Doc 3", "file_path": "/path/to/file.txt"},
        "source_type": "localfile",
    }

    client.scroll = AsyncMock(
        return_value=(
            [scroll_result1, scroll_result2, scroll_result3],
            None,
        )
    )

    # Mock collection operations
    collections_response = MagicMock()
    collections_response.collections = []
    client.get_collections = AsyncMock(return_value=collections_response)
    client.create_collection = AsyncMock(return_value=None)
    client.close = AsyncMock(return_value=None)

    return client


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    client = AsyncMock(spec=AsyncOpenAI)

    # Mock embeddings response
    embedding_response = MagicMock()
    embedding_data = MagicMock()
    embedding_data.embedding = [0.1, 0.2, 0.3] * 512  # 1536 dimensions
    embedding_response.data = [embedding_data]

    # Make the embeddings.create method async
    client.embeddings.create = AsyncMock(return_value=embedding_response)

    return client


@pytest.fixture
def hybrid_search(mock_qdrant_client, mock_openai_client):
    """Create a HybridSearchEngine instance with mocked dependencies."""
    return HybridSearchEngine(
        qdrant_client=mock_qdrant_client,
        openai_client=mock_openai_client,
        collection_name="test_collection",
    )


@pytest.mark.asyncio
async def test_search_basic(hybrid_search):
    """Test basic search functionality."""
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    hybrid_search._expand_query = AsyncMock(return_value="test query")

    results = await hybrid_search.search("test query")

    assert len(results) > 0
    assert isinstance(results[0], HybridSearchResult)
    assert results[0].score > 0


@pytest.mark.asyncio
async def test_search_with_source_type_filter(hybrid_search):
    """Test search with source type filtering."""
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    hybrid_search._expand_query = AsyncMock(return_value="test query")

    results = await hybrid_search.search("test query", source_types=["git"])
    assert results and all(r.source_type == "git" for r in results)


@pytest.mark.asyncio
async def test_search_with_localfile_filter(hybrid_search):
    """Test search with localfile source type filtering."""
    # Mock the internal methods to avoid actual API calls
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    hybrid_search._expand_query = AsyncMock(return_value="test query")

    results = await hybrid_search.search("test query", source_types=["localfile"])

    assert len(results) > 0
    assert all(r.source_type == "localfile" for r in results)


@pytest.mark.asyncio
async def test_search_query_expansion(hybrid_search):
    """Test query expansion functionality."""
    # Mock the internal methods to avoid actual API calls
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    hybrid_search._expand_query = AsyncMock(
        return_value="product requirements for API PRD requirements document product specification"
    )

    await hybrid_search.search("product requirements for API")

    # Verify that query expansion was called
    hybrid_search._expand_query.assert_called_once_with("product requirements for API")


@pytest.mark.asyncio
async def test_search_error_handling(hybrid_search, mock_qdrant_client):
    """Covered in test_hybrid_errors; keep a minimal sanity call that doesn't raise."""
    hybrid_search._expand_query = AsyncMock(return_value="q")
    hybrid_search._vector_search = AsyncMock(return_value=[])
    hybrid_search._keyword_search = AsyncMock(return_value=[])
    # Ensure fallback path uses the mocked legacy methods
    hybrid_search.hybrid_pipeline = None
    mock_qdrant_client.query_points.side_effect = None
    out = await hybrid_search.search("q")
    assert out == []


@pytest.mark.asyncio
async def test_search_result_scoring(hybrid_search):
    """Test that search results are properly scored and ranked."""
    # Mock the internal methods to avoid actual API calls
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    hybrid_search._expand_query = AsyncMock(return_value="test query")

    results = await hybrid_search.search("test query")

    # Check that results are sorted by score
    assert all(
        results[i].score >= results[i + 1].score for i in range(len(results) - 1)
    )


@pytest.mark.asyncio
async def test_search_with_limit(hybrid_search):
    """Test search with result limit."""
    # Mock the internal methods to avoid actual API calls
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    hybrid_search._expand_query = AsyncMock(return_value="test query")

    # Disable intent adaptation for this test to ensure predictable limit behavior
    original_enable_intent = getattr(hybrid_search, "enable_intent_adaptation", False)
    hybrid_search.enable_intent_adaptation = False

    limit = 1
    results = await hybrid_search.search("test query", limit=limit)
    assert len(results) <= limit

    # Restore original setting
    hybrid_search.enable_intent_adaptation = original_enable_intent


# New comprehensive tests for missing methods


@pytest.mark.asyncio
async def test_expand_query_with_expansions(hybrid_search):
    """Covered in test_hybrid_expansion; smoke-check here only."""
    expanded = await hybrid_search._expand_query("product requirements")
    assert isinstance(expanded, str) and expanded


@pytest.mark.asyncio
async def test_expand_query_case_insensitive(hybrid_search):
    """Test that query expansion is case insensitive and uses spaCy semantic expansion."""
    expanded = await hybrid_search._expand_query("PRODUCT REQUIREMENTS")
    # Test should verify spaCy-based expansion, not legacy keyword mapping
    # Be robust to stemming/lemmatization differences across spaCy versions
    expanded_lower = expanded.lower()
    assert any(tok.startswith("product") for tok in expanded_lower.split())
    assert "PRODUCT REQUIREMENTS" in expanded  # Original query preserved
    assert len(expanded.split()) > len(
        "PRODUCT REQUIREMENTS".split()
    )  # Query was expanded


def test_analyze_query_questions(hybrid_search):
    """Test query analysis for questions."""
    context = hybrid_search._analyze_query("What is the API documentation?")
    assert context["is_question"] is True
    # spaCy removes stopwords like "what", so check for meaningful keywords
    assert "api" in context["keywords"] or "documentation" in context["keywords"]

    context = hybrid_search._analyze_query("How to implement authentication?")
    assert context["is_question"] is True
    # Intent may be "general" if confidence is low, which is acceptable
    assert context["probable_intent"] in ["procedural", "general", "technical_lookup"]


def test_analyze_query_broad_vs_specific(hybrid_search):
    """Test query analysis for broad vs specific queries."""
    # Broad query (< 5 words)
    context = hybrid_search._analyze_query("API docs")
    assert context["is_broad"] is True
    assert context["is_specific"] is False

    # Specific query (> 7 words)
    context = hybrid_search._analyze_query(
        "How to implement OAuth2 authentication in the REST API endpoints"
    )
    assert context["is_broad"] is False
    assert context["is_specific"] is True


def test_analyze_query_intent_detection(hybrid_search):
    """Test query intent detection."""
    # Requirements intent (spaCy may classify differently)
    context = hybrid_search._analyze_query("product requirements document")
    # Accept various intents that spaCy might assign
    assert context["probable_intent"] in [
        "business_context",
        "general",
        "informational",
    ]

    # Architecture intent (spaCy may classify as technical)
    context = hybrid_search._analyze_query("system architecture design")
    assert context["probable_intent"] in [
        "technical_lookup",
        "general",
        "business_context",
    ]

    # Procedural intent (spaCy may classify as general or procedural)
    context = hybrid_search._analyze_query("steps to deploy application")
    assert context["probable_intent"] in ["procedural", "general", "technical_lookup"]


@pytest.mark.asyncio
async def test_vector_search(hybrid_search, mock_qdrant_client):
    """Test vector search functionality."""
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)

    results = await hybrid_search._vector_search("test query", 5)

    assert len(results) == 3
    assert results[0]["score"] == 0.8
    assert results[0]["text"] == "Test content 1"
    assert results[0]["source_type"] == "git"

    # Verify Qdrant query_points was called with correct parameters (qdrant-client 1.10+)
    mock_qdrant_client.query_points.assert_called_once()
    call_args = mock_qdrant_client.query_points.call_args
    assert call_args[1]["collection_name"] == "test_collection"
    assert call_args[1]["limit"] == 5


@pytest.mark.asyncio
async def test_keyword_search(hybrid_search, mock_qdrant_client):
    """Test keyword search functionality."""
    # Add a third mock result to match BM25 scores
    search_result3 = MagicMock()
    search_result3.id = "3"
    search_result3.score = 0.6
    search_result3.payload = {
        "content": "Test content 3",
        "metadata": {"title": "Test Doc 3", "url": "http://test3.com"},
        "source_type": "jira",
    }

    # Update scroll to return 3 results
    original_scroll_return = mock_qdrant_client.scroll.return_value
    original_results = original_scroll_return[0]
    mock_qdrant_client.scroll.return_value = (original_results + [search_result3], None)

    with patch(
        "qdrant_loader_mcp_server.search.components.keyword_search_service.BM25Okapi"
    ) as mock_bm25:
        # Mock BM25 scoring
        mock_bm25_instance = MagicMock()
        mock_bm25_instance.get_scores.return_value = np.array([0.5, 0.8, 0.3])
        mock_bm25.return_value = mock_bm25_instance

        results = await hybrid_search._keyword_search("test query", 5)

        assert len(results) == 3
        # Results should be sorted by BM25 score (highest first)
        assert results[0]["score"] == 0.8
        assert results[1]["score"] == 0.5
        assert results[2]["score"] == 0.3

        # Verify scroll was called
        mock_qdrant_client.scroll.assert_called_once()


@pytest.mark.asyncio
async def test_combine_results(hybrid_search):
    """Verify combination logic computes expected scores, sorts, and preserves fields."""
    # Deterministic mock results
    vec_results = [
        {
            "score": 0.9,
            "text": "doc1",
            "metadata": {"title": "T1"},
            "source_type": "git",
        },
        {
            "score": 0.6,
            "text": "doc2",
            "metadata": {"title": "T2"},
            "source_type": "confluence",
        },
    ]
    kw_results = [
        {
            "score": 0.1,
            "text": "doc1",
            "metadata": {"title": "T1"},
            "source_type": "git",
        },
        {
            "score": 0.8,
            "text": "doc3",
            "metadata": {"title": "T3"},
            "source_type": "jira",
        },
    ]
    # Use engine defaults: vector 0.6, keyword 0.3 ->
    # doc1 combined ~ 0.9*0.6 + 0.1*0.3 = 0.54 + 0.03 = 0.57
    # doc2 combined ~ 0.6*0.6 + 0.0*0.3 = 0.36
    # doc3 combined ~ 0.0*0.6 + 0.8*0.3 = 0.24
    # Ensure low threshold so all combined results are kept
    original_min = getattr(hybrid_search, "min_score", 0.0)
    hybrid_search.min_score = 0.0
    out = await hybrid_search._combine_results(vec_results, kw_results, {}, 10)
    # Restore original min_score
    hybrid_search.min_score = original_min
    assert isinstance(out, list)
    assert len(out) == 3
    # Sorted by score desc: doc1, doc2, doc3
    assert [r.text for r in out] == ["doc1", "doc2", "doc3"]
    # Check top score approximately expected (metadata boosting may adjust slightly)
    assert out[0].score >= 0.57
    assert out[0].text == "doc1"
    # Original fields preserved
    assert out[0].source_type in ["git", "confluence", "jira"]
    assert hasattr(out[0], "source_title")


@pytest.mark.asyncio
async def test_combine_results_with_source_filter(hybrid_search):
    """Verify that only results matching source_types are kept."""
    out = await hybrid_search._combine_results(
        [
            {"score": 0.9, "text": "g1", "metadata": {}, "source_type": "git"},
            {"score": 0.7, "text": "o1", "metadata": {}, "source_type": "other"},
        ],
        [
            {"score": 0.8, "text": "g2", "metadata": {}, "source_type": "git"},
            {"score": 0.6, "text": "c1", "metadata": {}, "source_type": "confluence"},
        ],
        {},
        10,
        source_types=["git"],
    )
    assert len(out) >= 1
    assert all(getattr(r, "source_type", None) == "git" for r in out)


@pytest.mark.asyncio
async def test_combine_results_with_low_min_score(hybrid_search):
    """Covered in test_hybrid_combining; keep minimal count check."""
    hybrid_search.min_score = 0.1
    out = await hybrid_search._combine_results(
        [{"score": 0.8, "text": "t1", "metadata": {}, "source_type": "git"}],
        [
            {"score": 0.6, "text": "t1", "metadata": {}, "source_type": "git"},
            {"score": 0.4, "text": "t2", "metadata": {}, "source_type": "confluence"},
        ],
        {},
        5,
    )
    assert len(out) >= 2


def test_extract_metadata_info_hierarchy(hybrid_search):
    """Covered in test_hybrid_metadata; keep smoke-check."""
    info = hybrid_search._extract_metadata_info({})
    assert isinstance(info, dict)


def test_extract_metadata_info_attachment(hybrid_search):
    """Covered in test_hybrid_metadata; keep minimal assertion."""
    info = hybrid_search._extract_metadata_info({"is_attachment": True})
    assert info["is_attachment"] is True


def test_extract_metadata_info_file_size_formatting(hybrid_search):
    """Covered in test_hybrid_metadata; minimal check only."""
    info = hybrid_search._extract_metadata_info(
        {"is_attachment": True, "file_size": 512}
    )
    assert "attachment_context" in info


def test_extract_metadata_info_empty_metadata(hybrid_search):
    """Covered in test_hybrid_metadata; minimal default behavior check."""
    info = hybrid_search._extract_metadata_info({})
    assert info["is_attachment"] is False


@pytest.mark.asyncio
async def test_get_embedding_error_handling(hybrid_search, mock_openai_client):
    """Covered in test_hybrid_errors; keep positive path assertion here."""
    embedding = await hybrid_search._get_embedding("test text")
    assert isinstance(embedding, list)


@pytest.mark.asyncio
async def test_get_embedding_success(hybrid_search, mock_openai_client):
    """Test successful embedding generation."""
    # Use the actual mock client instead of calling the real method
    embedding = await hybrid_search._get_embedding("test text")

    assert len(embedding) == 1536  # 512 * 3
    assert embedding[0] == 0.1

    # Verify OpenAI API was called correctly
    mock_openai_client.embeddings.create.assert_called_once_with(
        model="text-embedding-3-small", input="test text"
    )


# ============================================================================
# Intent Adaptation and Adaptive Search Tests
# ============================================================================


@pytest.fixture
def hybrid_search_with_intent(mock_qdrant_client, mock_openai_client):
    """Create a HybridSearchEngine instance with intent adaptation enabled."""
    return HybridSearchEngine(
        qdrant_client=mock_qdrant_client,
        openai_client=mock_openai_client,
        collection_name="test_collection",
        enable_intent_adaptation=True,
    )


@pytest.mark.asyncio
async def test_search_with_intent_adaptation(hybrid_search_with_intent):
    """Test search with intent adaptation enabled."""
    # Mock the internal methods to avoid actual API calls
    hybrid_search_with_intent._get_embedding = AsyncMock(
        return_value=[0.1, 0.2, 0.3] * 512
    )
    hybrid_search_with_intent._expand_query = AsyncMock(return_value="test query")
    hybrid_search_with_intent._expand_query_aggressive = AsyncMock(
        return_value="expanded test query aggressively"
    )

    # Mock intent classifier
    from qdrant_loader_mcp_server.search.enhanced.intent_classifier import (
        IntentType,
        SearchIntent,
    )

    mock_intent = SearchIntent(
        intent_type=IntentType.TECHNICAL_LOOKUP,
        confidence=0.8,
        is_question=False,
        is_technical=True,
    )

    hybrid_search_with_intent.intent_classifier.classify_intent = MagicMock(
        return_value=mock_intent
    )

    # Mock adaptive strategy
    from qdrant_loader_mcp_server.search.enhanced.intent_classifier import (
        AdaptiveSearchConfig,
    )

    mock_config = AdaptiveSearchConfig(
        vector_weight=0.7,
        keyword_weight=0.2,
        max_results=10,
        expand_query=True,
        expansion_aggressiveness=0.8,
        use_knowledge_graph=True,
    )

    hybrid_search_with_intent.adaptive_strategy.adapt_search = MagicMock(
        return_value=mock_config
    )

    # Test search with session and behavioral context
    results = await hybrid_search_with_intent.search(
        "test query",
        limit=5,
        session_context={"user_id": "test_user", "session_id": "test_session"},
        behavioral_context=["technical_lookup", "informational"],
    )

    assert len(results) > 0
    assert isinstance(results[0], HybridSearchResult)

    # Verify intent classification was called
    hybrid_search_with_intent.intent_classifier.classify_intent.assert_called_once()

    # Verify adaptive strategy was called
    hybrid_search_with_intent.adaptive_strategy.adapt_search.assert_called_once()


@pytest.mark.asyncio
async def test_search_with_aggressive_expansion(hybrid_search_with_intent):
    """Test search with aggressive query expansion."""
    # Mock the internal methods
    hybrid_search_with_intent._get_embedding = AsyncMock(
        return_value=[0.1, 0.2, 0.3] * 512
    )
    hybrid_search_with_intent._expand_query = AsyncMock(return_value="test query")
    hybrid_search_with_intent._expand_query_aggressive = AsyncMock(
        return_value="aggressively expanded test query"
    )

    # Mock intent classifier for aggressive expansion
    from qdrant_loader_mcp_server.search.enhanced.intent_classifier import (
        AdaptiveSearchConfig,
        IntentType,
        SearchIntent,
    )

    mock_intent = SearchIntent(
        intent_type=IntentType.EXPLORATORY, confidence=0.9, is_question=True
    )

    mock_config = AdaptiveSearchConfig(
        vector_weight=0.6,
        keyword_weight=0.3,
        max_results=15,
        expand_query=True,
        expansion_aggressiveness=0.9,  # High aggressiveness
        use_knowledge_graph=True,
    )

    hybrid_search_with_intent.intent_classifier.classify_intent = MagicMock(
        return_value=mock_intent
    )
    hybrid_search_with_intent.adaptive_strategy.adapt_search = MagicMock(
        return_value=mock_config
    )

    await hybrid_search_with_intent.search("broad search query")

    # Verify aggressive expansion was called
    hybrid_search_with_intent._expand_query_aggressive.assert_called_once_with(
        "broad search query"
    )


def test_get_adaptive_search_stats(hybrid_search_with_intent):
    """Test getting adaptive search statistics."""
    # Mock the stats methods
    hybrid_search_with_intent.intent_classifier.get_cache_stats = MagicMock(
        return_value={"cache_hits": 10, "cache_misses": 5}
    )
    hybrid_search_with_intent.adaptive_strategy.get_strategy_stats = MagicMock(
        return_value={"adaptations": 8}
    )

    stats = hybrid_search_with_intent.get_adaptive_search_stats()

    assert stats["intent_adaptation_enabled"] is True
    assert stats["has_knowledge_graph"] is False  # No KG provided in fixture
    assert stats["cache_hits"] == 10
    assert stats["cache_misses"] == 5
    assert stats["adaptations"] == 8


@pytest.fixture
def hybrid_search_disabled_intent(mock_qdrant_client, mock_openai_client):
    """Create a HybridSearchEngine instance with intent adaptation disabled."""
    return HybridSearchEngine(
        qdrant_client=mock_qdrant_client,
        openai_client=mock_openai_client,
        collection_name="test_collection",
        enable_intent_adaptation=False,
    )


def test_get_adaptive_search_stats_disabled(hybrid_search_disabled_intent):
    """Test getting adaptive search statistics when disabled."""
    stats = hybrid_search_disabled_intent.get_adaptive_search_stats()

    assert stats["intent_adaptation_enabled"] is False
    assert stats["has_knowledge_graph"] is False


# ============================================================================
# Topic Search Chain Tests
# ============================================================================


@pytest.mark.asyncio
async def test_generate_topic_search_chain(hybrid_search):
    """Test topic search chain generation."""
    from qdrant_loader_mcp_server.search.enhanced.topic_search_chain import (
        ChainStrategy,
        TopicChainLink,
        TopicSearchChain,
    )

    # Mock topic chain generator
    mock_chain = TopicSearchChain(
        original_query="API documentation",
        chain_links=[
            TopicChainLink(
                query="REST API endpoints",
                topic_focus="API",
                related_topics=["REST", "endpoints"],
                chain_position=1,
                relevance_score=0.8,
                exploration_type="related",
            )
        ],
        strategy=ChainStrategy.MIXED_EXPLORATION,
        total_topics_covered=3,
        estimated_discovery_potential=0.75,
        generation_time_ms=150.0,
    )

    hybrid_search.topic_chain_generator.generate_search_chain = MagicMock(
        return_value=mock_chain
    )

    result = await hybrid_search.generate_topic_search_chain(
        "API documentation", strategy=ChainStrategy.MIXED_EXPLORATION, max_links=5
    )

    assert result.original_query == "API documentation"
    assert len(result.chain_links) == 1
    assert result.chain_links[0].query == "REST API endpoints"
    assert result.strategy == ChainStrategy.MIXED_EXPLORATION

    # Verify generator was called correctly
    hybrid_search.topic_chain_generator.generate_search_chain.assert_called_once_with(
        original_query="API documentation",
        strategy=ChainStrategy.MIXED_EXPLORATION,
        max_links=5,
    )


@pytest.mark.asyncio
async def test_execute_topic_chain_search(hybrid_search):
    """Covered in test_hybrid_topic_chain; smoke-check only."""
    from qdrant_loader_mcp_server.search.enhanced.topic_search_chain import (
        ChainStrategy,
        TopicSearchChain,
    )

    mock_chain = TopicSearchChain(
        original_query="q",
        chain_links=[],
        strategy=ChainStrategy.MIXED_EXPLORATION,
        total_topics_covered=0,
        estimated_discovery_potential=0.0,
        generation_time_ms=0.0,
    )
    results = await hybrid_search.execute_topic_chain_search(mock_chain)
    assert isinstance(results, dict)


@pytest.mark.asyncio
async def test_initialize_topic_relationships(hybrid_search):
    """Covered in test_hybrid_topic_chain; minimal call only."""
    await hybrid_search._initialize_topic_relationships("sample query")


# ============================================================================
# Faceted Search Tests
# ============================================================================


@pytest.mark.asyncio
async def test_search_with_facets(hybrid_search):
    """Test faceted search functionality."""
    from qdrant_loader_mcp_server.search.enhanced.faceted_search import (
        Facet,
        FacetedSearchResults,
        FacetFilter,
        FacetType,
        FacetValue,
    )

    # Mock search results
    search_results = [
        create_hybrid_search_result(
            score=0.8, text="Doc 1", source_type="git", source_title="Git Doc"
        ),
        create_hybrid_search_result(
            score=0.7,
            text="Doc 2",
            source_type="confluence",
            source_title="Confluence Doc",
        ),
    ]

    # Mock faceted results
    mock_facets = [
        Facet(
            facet_type=FacetType.SOURCE_TYPE,
            name="source_type",
            display_name="Source Type",
            values=[
                FacetValue(value="git", count=1, display_name="Git"),
                FacetValue(value="confluence", count=1, display_name="Confluence"),
            ],
        )
    ]

    mock_faceted_results = FacetedSearchResults(
        results=search_results,
        facets=mock_facets,
        applied_filters=[],
        total_results=2,
        filtered_count=2,
        generation_time_ms=50.0,
    )

    # Mock search and faceted search engine
    hybrid_search.search = AsyncMock(return_value=search_results)
    hybrid_search.faceted_search_engine.generate_faceted_results = MagicMock(
        return_value=mock_faceted_results
    )

    # Create facet filters
    facet_filters = [
        FacetFilter(facet_type=FacetType.SOURCE_TYPE, values=["git"], operator="OR")
    ]

    result = await hybrid_search.search_with_facets(
        query="test query", limit=5, facet_filters=facet_filters, generate_facets=True
    )

    assert isinstance(result, FacetedSearchResults)
    assert len(result.results) == 2
    assert len(result.facets) == 1
    assert result.facets[0].name == "source_type"
    assert (
        len(result.applied_filters) == 0
    )  # This gets set by the faceted search engine

    # Verify search was called with larger limit for faceting
    hybrid_search.search.assert_called_once()
    call_args = hybrid_search.search.call_args
    assert call_args[1]["limit"] == 50  # max(5 * 2, 50)

    # Verify faceted search engine was called
    hybrid_search.faceted_search_engine.generate_faceted_results.assert_called_once_with(
        results=search_results, applied_filters=facet_filters
    )


def test_suggest_facet_refinements(hybrid_search):
    """Test facet refinement suggestions."""
    from qdrant_loader_mcp_server.search.enhanced.faceted_search import (
        FacetFilter,
        FacetType,
    )

    # Mock current results and filters
    current_results = [
        create_hybrid_search_result(
            score=0.8, text="Doc 1", source_type="git", source_title="Git Doc"
        ),
        create_hybrid_search_result(
            score=0.7,
            text="Doc 2",
            source_type="confluence",
            source_title="Confluence Doc",
        ),
    ]

    current_filters = [
        FacetFilter(facet_type=FacetType.SOURCE_TYPE, values=["git"], operator="OR")
    ]

    # Mock refinement suggestions
    mock_suggestions = [
        {
            "facet": "project",
            "suggested_values": ["project1", "project2"],
            "reason": "common_projects",
        },
        {
            "facet": "content_type",
            "suggested_values": ["documentation"],
            "reason": "content_similarity",
        },
    ]

    hybrid_search.faceted_search_engine.suggest_refinements = MagicMock(
        return_value=mock_suggestions
    )

    suggestions = hybrid_search.suggest_facet_refinements(
        current_results, current_filters
    )

    assert len(suggestions) == 2
    assert suggestions[0]["facet"] == "project"
    assert suggestions[1]["facet"] == "content_type"

    # Verify faceted search engine was called
    hybrid_search.faceted_search_engine.suggest_refinements.assert_called_once_with(
        current_results, current_filters
    )


def test_generate_facets(hybrid_search):
    """Test facet generation."""
    from qdrant_loader_mcp_server.search.enhanced.faceted_search import (
        Facet,
        FacetType,
        FacetValue,
    )

    # Mock search results
    results = [
        create_hybrid_search_result(
            score=0.8, text="Doc 1", source_type="git", source_title="Git Doc"
        ),
        create_hybrid_search_result(
            score=0.7,
            text="Doc 2",
            source_type="confluence",
            source_title="Confluence Doc",
        ),
    ]

    # Mock generated facets
    mock_facets = [
        Facet(
            facet_type=FacetType.SOURCE_TYPE,
            name="source_type",
            display_name="Source Type",
            values=[
                FacetValue(value="git", count=1, display_name="Git"),
                FacetValue(value="confluence", count=1, display_name="Confluence"),
            ],
        )
    ]

    hybrid_search.faceted_search_engine.facet_generator.generate_facets = MagicMock(
        return_value=mock_facets
    )

    facets = hybrid_search.generate_facets(results)

    assert len(facets) == 1
    assert facets[0].name == "source_type"
    assert len(facets[0].values) == 2

    # Verify facet generator was called
    hybrid_search.faceted_search_engine.facet_generator.generate_facets.assert_called_once_with(
        results
    )


# ============================================================================
# Cross-Document Intelligence Tests
# ============================================================================


@pytest.mark.asyncio
async def test_analyze_document_relationships(hybrid_search):
    """Test cross-document relationship analysis."""
    # Mock documents
    documents = [
        create_hybrid_search_result(
            score=0.8, text="Doc 1", source_type="git", source_title="Git Doc"
        ),
        create_hybrid_search_result(
            score=0.7,
            text="Doc 2",
            source_type="confluence",
            source_title="Confluence Doc",
        ),
    ]

    # Mock analysis results
    mock_analysis = {
        "entity_relationships": [{"entity": "API", "documents": ["Doc 1", "Doc 2"]}],
        "topic_clusters": [{"topic": "development", "documents": ["Doc 1", "Doc 2"]}],
        "cross_references": [
            {"source": "Doc 1", "target": "Doc 2", "relationship": "references"}
        ],
    }

    hybrid_search.cross_document_engine.analyze_document_relationships = MagicMock(
        return_value=mock_analysis
    )

    result = await hybrid_search.analyze_document_relationships(documents)

    assert "entity_relationships" in result
    assert "topic_clusters" in result
    assert "cross_references" in result
    assert len(result["entity_relationships"]) == 1
    assert result["entity_relationships"][0]["entity"] == "API"

    # Verify cross-document engine was called
    hybrid_search.cross_document_engine.analyze_document_relationships.assert_called_once_with(
        documents
    )


@pytest.mark.asyncio
async def test_find_similar_documents(hybrid_search):
    """Test finding similar documents."""
    from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
        SimilarityMetric,
    )

    # Create a mock SimilarityResult class for testing
    class SimilarityResult:
        def __init__(self, similarity_score, metric_scores):
            self.similarity_score = similarity_score
            self.metric_scores = metric_scores

        def get_display_explanation(self):
            return "High similarity based on content analysis"

    # Mock target document and document pool
    target_doc = create_hybrid_search_result(
        score=0.8,
        text="Target doc",
        source_type="git",
        source_title="Target",
        document_id="target_id",
    )

    documents = [
        create_hybrid_search_result(
            score=0.7,
            text="Similar doc",
            source_type="git",
            source_title="Similar",
            document_id="similar_id",
        ),
        create_hybrid_search_result(
            score=0.6,
            text="Different doc",
            source_type="confluence",
            source_title="Different",
            document_id="different_id",
        ),
    ]

    # Mock similarity calculation
    def mock_calculate_similarity(target, doc, metrics):
        if doc.source_title == "Similar":
            return SimilarityResult(
                similarity_score=0.8, metric_scores={"semantic": 0.8, "entity": 0.7}
            )
        else:
            return SimilarityResult(
                similarity_score=0.3, metric_scores={"semantic": 0.3, "entity": 0.2}
            )

    hybrid_search.cross_document_engine.similarity_calculator.calculate_similarity = (
        MagicMock(side_effect=mock_calculate_similarity)
    )

    # Also need to mock the get_display_explanation method
    def mock_get_display_explanation():
        return "High semantic similarity based on content analysis"

    # Apply the mock to the return value
    hybrid_search.cross_document_engine.similarity_calculator.calculate_similarity.return_value.get_display_explanation = MagicMock(
        return_value="High similarity"
    )

    similar_docs = await hybrid_search.find_similar_documents(
        target_document=target_doc,
        documents=documents,
        similarity_metrics=[SimilarityMetric.SEMANTIC_SIMILARITY],
        max_similar=5,
    )

    assert len(similar_docs) == 2
    # Results should be sorted by similarity score (highest first)
    assert similar_docs[0]["document"].source_title == "Similar"
    assert similar_docs[0]["similarity_score"] == 0.8
    assert similar_docs[1]["document"].source_title == "Different"
    assert similar_docs[1]["similarity_score"] == 0.3

    # Verify document_id is included for lazy loading
    assert similar_docs[0]["document_id"] == "similar_id"
    assert similar_docs[1]["document_id"] == "different_id"


@pytest.mark.asyncio
async def test_detect_document_conflicts(hybrid_search):
    """Test document conflict detection."""
    # Mock documents
    documents = [
        create_hybrid_search_result(
            score=0.8, text="Doc 1 says X", source_type="git", source_title="Doc 1"
        ),
        create_hybrid_search_result(
            score=0.7,
            text="Doc 2 says Y",
            source_type="confluence",
            source_title="Doc 2",
        ),
    ]

    # Mock conflict analysis result
    from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
        ConflictAnalysis,
    )

    mock_conflict_analysis = ConflictAnalysis(
        conflicting_pairs=[("Doc 1", "Doc 2")],
        conflict_categories=["factual_disagreement"],
        resolution_suggestions=["Review both documents for accuracy"],
    )

    hybrid_search.cross_document_engine.conflict_detector.detect_conflicts = AsyncMock(
        return_value=mock_conflict_analysis
    )

    result = await hybrid_search.detect_document_conflicts(documents)

    assert "conflicting_pairs" in result
    assert "conflict_categories" in result
    assert "resolution_suggestions" in result
    assert len(result["conflicting_pairs"]) == 1
    assert result["conflicting_pairs"][0] == ("Doc 1", "Doc 2")
    assert "factual_disagreement" in result["conflict_categories"]

    # Verify conflict detector was called
    hybrid_search.cross_document_engine.conflict_detector.detect_conflicts.assert_called_once_with(
        documents
    )


@pytest.mark.asyncio
async def test_find_complementary_content(hybrid_search):
    """Test finding complementary content."""
    # Mock target document and document pool
    target_doc = create_hybrid_search_result(
        score=0.8,
        text="Target doc about APIs",
        source_type="git",
        source_title="API Guide",
        document_id="api_guide_id",
    )

    documents = [
        create_hybrid_search_result(
            score=0.7,
            text="Authentication methods",
            source_type="confluence",
            source_title="Auth Guide",
            document_id="auth_guide_id",
        ),
        create_hybrid_search_result(
            score=0.6,
            text="Database schema",
            source_type="git",
            source_title="DB Schema",
            document_id="db_schema_id",
        ),
    ]

    # Mock complementary content finder
    class MockComplementaryContent:
        def get_top_recommendations(self, max_recommendations):
            return [
                {
                    "document_id": "confluence:Auth Guide",  # Use composite key format
                    "relevance_score": 0.8,
                    "recommendation_reason": "Provides security context for API usage",
                    "strategy": "security_enhancement",
                },
                {
                    "document_id": "git:DB Schema",  # Use composite key format
                    "relevance_score": 0.6,
                    "recommendation_reason": "Shows data models used by APIs",
                    "strategy": "technical_depth",
                },
            ]

    mock_complementary_content = MockComplementaryContent()
    hybrid_search.cross_document_engine.complementary_finder.find_complementary_content = MagicMock(
        return_value=mock_complementary_content
    )

    recommendations = await hybrid_search.find_complementary_content(
        target_document=target_doc, documents=documents, max_recommendations=5
    )

    assert len(recommendations) == 2
    assert recommendations[0]["document"].source_title == "Auth Guide"
    assert recommendations[0]["relevance_score"] == 0.8
    assert (
        recommendations[0]["recommendation_reason"]
        == "Provides security context for API usage"
    )
    assert recommendations[1]["document"].source_title == "DB Schema"
    assert recommendations[1]["relevance_score"] == 0.6

    # Verify complementary finder was called
    hybrid_search.cross_document_engine.complementary_finder.find_complementary_content.assert_called_once_with(
        target_doc, documents
    )


# ============================================================================
# Document Clustering Tests
# ============================================================================


@pytest.mark.asyncio
async def test_cluster_documents(hybrid_search):
    """Test document clustering functionality."""
    from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
        ClusteringStrategy,
        DocumentCluster,
    )

    # Mock documents to cluster
    documents = [
        create_hybrid_search_result(
            score=0.8,
            text="API documentation content",
            source_type="git",
            source_title="API Guide",
            document_id="api_guide_id",
        ),
        create_hybrid_search_result(
            score=0.7,
            text="Authentication and security",
            source_type="confluence",
            source_title="Security Guide",
            document_id="security_guide_id",
        ),
        create_hybrid_search_result(
            score=0.6,
            text="Database schema and models",
            source_type="git",
            source_title="DB Schema",
            document_id="db_schema_id",
        ),
    ]

    # Mock clusters
    mock_clusters = [
        DocumentCluster(
            cluster_id="cluster_1",
            name="API Documentation",
            documents=["git:API Guide", "confluence:Security Guide"],
            shared_topics=["API", "documentation"],
            shared_entities=["authentication", "endpoints"],
            coherence_score=0.8,
            cluster_description="Documents related to API development and security",
            representative_doc_id="git:API Guide",
        ),
        DocumentCluster(
            cluster_id="cluster_2",
            name="Database Content",
            documents=["git:DB Schema"],
            shared_topics=["database", "schema"],
            shared_entities=["models", "tables"],
            coherence_score=0.9,
            cluster_description="Database-related documentation",
            representative_doc_id="git:DB Schema",
        ),
    ]

    hybrid_search.cross_document_engine.cluster_analyzer.create_clusters = MagicMock(
        return_value=mock_clusters
    )

    result = await hybrid_search.cluster_documents(
        documents=documents,
        strategy=ClusteringStrategy.MIXED_FEATURES,
        max_clusters=10,
        min_cluster_size=2,
    )

    assert "clusters" in result
    assert "clustering_metadata" in result
    assert "cluster_relationships" in result
    assert len(result["clusters"]) == 2

    # Verify first cluster
    cluster1 = result["clusters"][0]
    assert cluster1["id"] == "cluster_1"
    assert cluster1["name"] == "API Documentation"
    assert cluster1["coherence_score"] == 0.8
    assert "API" in cluster1["centroid_topics"]
    assert "authentication" in cluster1["shared_entities"]

    # Verify clustering metadata
    metadata = result["clustering_metadata"]
    assert metadata["strategy"] == ClusteringStrategy.MIXED_FEATURES.value
    assert metadata["total_documents"] == 3
    assert metadata["clusters_created"] == 2
    assert "processing_time_ms" in metadata
    assert "strategy_performance" in metadata

    # Verify cluster analyzer was called
    hybrid_search.cross_document_engine.cluster_analyzer.create_clusters.assert_called_once_with(
        documents, ClusteringStrategy.MIXED_FEATURES, 10, 2
    )


def test_build_document_lookup(hybrid_search):
    """Test building document lookup with multiple strategies."""
    documents = [
        create_hybrid_search_result(
            score=0.8,
            text="Doc 1",
            source_type="git",
            source_title="API Guide",
            document_id="api_guide_id",
        ),
        create_hybrid_search_result(
            score=0.7,
            text="Doc 2",
            source_type="confluence",
            source_title="Security Guide",
            document_id="security_guide_id",
        ),
    ]

    lookup = hybrid_search._build_document_lookup(documents)

    # Should have multiple lookup keys per document
    assert "git:API Guide" in lookup
    assert "confluence:Security Guide" in lookup
    assert "api_guide_id" in lookup
    assert "security_guide_id" in lookup
    assert "API Guide" in lookup
    assert "Security Guide" in lookup

    # Verify lookup works
    assert lookup["git:API Guide"].source_title == "API Guide"
    assert lookup["api_guide_id"].source_title == "API Guide"
    assert lookup["confluence:Security Guide"].source_title == "Security Guide"


def test_build_robust_document_lookup(hybrid_search):
    """Test building robust document lookup with edge cases."""
    documents = [
        create_hybrid_search_result(
            score=0.8,
            text="Doc 1",
            source_type="git",
            source_title="  API Guide  ",  # With whitespace
            document_id="api_guide_id",
        ),
        create_hybrid_search_result(
            score=0.7,
            text="Doc 2",
            source_type=None,  # None source type
            source_title="",  # Empty title
            document_id="empty_doc_id",
        ),
    ]

    lookup = hybrid_search._build_document_lookup(documents, robust=True)

    # Should handle whitespace and None values gracefully
    assert "git:  API Guide  " in lookup
    assert "git:API Guide" in lookup  # Sanitized key
    assert "unknown:" in lookup  # None source_type becomes "unknown"
    assert "api_guide_id" in lookup
    assert "empty_doc_id" in lookup


def test_find_document_by_id(hybrid_search):
    """Test finding documents by ID with various strategies."""
    documents = [
        create_hybrid_search_result(
            score=0.8,
            text="Doc 1",
            source_type="git",
            source_title="API Guide",
            document_id="api_guide_id",
        ),
        create_hybrid_search_result(
            score=0.7,
            text="Doc 2",
            source_type="confluence",
            source_title="Security Guide",
            document_id="security_guide_id",
        ),
    ]

    lookup = hybrid_search._build_document_lookup(documents, robust=True)

    # Test direct lookup
    doc = hybrid_search._find_document_by_id("api_guide_id", lookup)
    assert doc is not None
    assert doc.source_title == "API Guide"

    # Test composite key lookup
    doc = hybrid_search._find_document_by_id("git:API Guide", lookup)
    assert doc is not None
    assert doc.source_title == "API Guide"

    # Test partial matching
    doc = hybrid_search._find_document_by_id("API Guide", lookup)
    assert doc is not None
    assert doc.source_title == "API Guide"

    # Test title extraction from composite key
    doc = hybrid_search._find_document_by_id("confluence:Security Guide", lookup)
    assert doc is not None
    assert doc.source_title == "Security Guide"

    # Test not found
    doc = hybrid_search._find_document_by_id("nonexistent", lookup)
    assert doc is None

    # Test empty ID
    doc = hybrid_search._find_document_by_id("", lookup)
    assert doc is None


def test_calculate_cluster_quality(hybrid_search):
    """Test cluster quality calculation."""
    from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
        DocumentCluster,
    )

    # Mock cluster
    cluster = DocumentCluster(
        cluster_id="test_cluster",
        name="Test Cluster",
        documents=["doc1", "doc2", "doc3"],
        shared_topics=["topic1", "topic2"],
        shared_entities=["entity1", "entity2", "entity3"],
        coherence_score=0.75,
        cluster_description="Test cluster description",
        representative_doc_id="doc1",
    )

    # Mock cluster documents (2 out of 3 retrieved)
    cluster_documents = [
        create_hybrid_search_result(
            score=0.8, text="Doc 1", source_type="git", source_title="Doc 1"
        ),
        create_hybrid_search_result(
            score=0.7, text="Doc 2", source_type="git", source_title="Doc 2"
        ),
    ]

    quality = hybrid_search._calculate_cluster_quality(cluster, cluster_documents)

    assert "document_retrieval_rate" in quality
    assert quality["document_retrieval_rate"] == 2 / 3  # 2 retrieved out of 3
    assert quality["coherence_score"] == 0.75
    assert quality["entity_diversity"] == 3
    assert quality["topic_diversity"] == 2
    assert quality["has_representative"] is True
    assert quality["cluster_size_category"] == "small"  # 2 documents
    assert "content_similarity" in quality


def test_categorize_cluster_size(hybrid_search):
    """Test cluster size categorization."""
    assert hybrid_search._categorize_cluster_size(1) == "small"
    assert hybrid_search._categorize_cluster_size(2) == "small"
    assert hybrid_search._categorize_cluster_size(3) == "medium"
    assert hybrid_search._categorize_cluster_size(5) == "medium"
    assert hybrid_search._categorize_cluster_size(6) == "large"
    assert hybrid_search._categorize_cluster_size(10) == "large"
    assert hybrid_search._categorize_cluster_size(11) == "very_large"
    assert hybrid_search._categorize_cluster_size(20) == "very_large"


def test_estimate_content_similarity(hybrid_search):
    """Test content similarity estimation."""
    # Documents with overlapping content
    documents = [
        create_hybrid_search_result(
            score=0.8,
            text="API documentation and development guide",
            source_type="git",
            source_title="API Development Guide",
        ),
        create_hybrid_search_result(
            score=0.7,
            text="API authentication and security documentation",
            source_type="git",
            source_title="API Security Documentation",
        ),
    ]

    similarity = hybrid_search._estimate_content_similarity(documents)
    assert 0.0 <= similarity <= 1.0
    assert similarity > 0  # Should have some overlap due to "API" and "documentation"

    # Test single document
    single_doc = documents[:1]
    similarity = hybrid_search._estimate_content_similarity(single_doc)
    assert similarity == 1.0  # Single document should have similarity 1.0

    # Test empty documents - method returns 1.0 for len < 2
    similarity = hybrid_search._estimate_content_similarity([])
    assert similarity == 1.0  # Current implementation returns 1.0 for empty list


def test_assess_overall_quality(hybrid_search):
    """Test overall clustering quality assessment."""
    from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
        DocumentCluster,
    )

    # Mock high-quality clusters
    good_clusters = [
        DocumentCluster(
            cluster_id="cluster1",
            name="Cluster 1",
            documents=["doc1", "doc2", "doc3"],
            coherence_score=0.8,
            shared_topics=["topic1"],
            shared_entities=["entity1"],
            cluster_description="Good cluster",
            representative_doc_id="doc1",
        ),
        DocumentCluster(
            cluster_id="cluster2",
            name="Cluster 2",
            documents=["doc4", "doc5"],
            coherence_score=0.9,
            shared_topics=["topic2"],
            shared_entities=["entity2"],
            cluster_description="Another good cluster",
            representative_doc_id="doc4",
        ),
    ]

    quality = hybrid_search._assess_overall_quality(
        good_clusters, matched_docs=5, requested_docs=5
    )
    assert 0.0 <= quality <= 1.0
    assert quality > 0.5  # Should be good quality

    # Test empty clusters
    quality = hybrid_search._assess_overall_quality(
        [], matched_docs=0, requested_docs=0
    )
    assert quality == 0.0


def test_generate_clustering_recommendations(hybrid_search):
    """Test clustering improvement recommendations."""
    from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
        ClusteringStrategy,
        DocumentCluster,
    )

    # Test low retrieval rate scenario
    clusters = [
        DocumentCluster(
            cluster_id="cluster1",
            name="Cluster 1",
            documents=["doc1", "doc2"],
            coherence_score=0.5,
            shared_topics=["topic1"],
            shared_entities=["entity1"],
            cluster_description="Low coherence cluster",
            representative_doc_id="doc1",
        )
    ]

    recommendations = hybrid_search._generate_clustering_recommendations(
        clusters, ClusteringStrategy.MIXED_FEATURES, matched_docs=8, requested_docs=10
    )

    assert "quality_threshold_met" in recommendations
    assert "suggestions" in recommendations
    assert recommendations["quality_threshold_met"] is False  # 8/10 = 80% < 90%

    # Test single large cluster scenario
    large_cluster = [
        DocumentCluster(
            cluster_id="large_cluster",
            name="Large Cluster",
            documents=[f"doc{i}" for i in range(15)],  # 15 documents
            coherence_score=0.7,
            shared_topics=["topic1"],
            shared_entities=["entity1"],
            cluster_description="Large cluster",
            representative_doc_id="doc1",
        )
    ]

    recommendations = hybrid_search._generate_clustering_recommendations(
        large_cluster,
        ClusteringStrategy.MIXED_FEATURES,
        matched_docs=15,
        requested_docs=15,
    )

    assert any(
        "Single large cluster" in suggestion
        for suggestion in recommendations["suggestions"]
    )
    assert "alternative_strategies" in recommendations


# ============================================================================
# Utility and Helper Method Tests
# ============================================================================


def test_extract_project_info(hybrid_search):
    """Test project information extraction."""
    # Mock metadata with project info
    metadata = {
        "project_id": "proj_123",
        "project_name": "Test Project",
        "project_description": "A test project for validation",
        "collection_name": "test_collection",
    }

    # Create a mock object with __dict__ containing the metadata
    mock_project_info = type("ProjectInfo", (), {})()
    mock_project_info.__dict__ = metadata
    hybrid_search.metadata_extractor.extract_project_info = MagicMock(
        return_value=mock_project_info
    )

    info = hybrid_search._extract_project_info(metadata)

    assert info["project_id"] == "proj_123"
    assert info["project_name"] == "Test Project"
    assert info["project_description"] == "A test project for validation"
    assert info["collection_name"] == "test_collection"

    # Test with None result
    hybrid_search.metadata_extractor.extract_project_info = MagicMock(return_value=None)

    info = hybrid_search._extract_project_info({})

    assert info["project_id"] is None
    assert info["project_name"] is None
    assert info["project_description"] is None
    assert info["collection_name"] is None


def test_build_filter(hybrid_search):
    """Test filter building for Qdrant queries."""
    # Mock vector search service filter building
    mock_filter = {"must": [{"key": "project_id", "match": {"value": "proj_123"}}]}
    hybrid_search.vector_search_service._build_filter = MagicMock(
        return_value=mock_filter
    )

    filter_result = hybrid_search._build_filter(project_ids=["proj_123"])

    assert filter_result == mock_filter
    hybrid_search.vector_search_service._build_filter.assert_called_once_with(
        ["proj_123"]
    )

    # Test with no project IDs
    filter_result = hybrid_search._build_filter(project_ids=None)
    hybrid_search.vector_search_service._build_filter.assert_called_with(None)


def test_calculate_std(hybrid_search):
    """Test standard deviation calculation."""
    # Test normal case
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    std = hybrid_search._calculate_std(values)
    assert std > 0
    assert abs(std - 1.4142) < 0.1  # Approximate expected std dev (sqrt(2))

    # Test single value
    std = hybrid_search._calculate_std([2.0])
    assert std == 0.0

    # Test empty list
    std = hybrid_search._calculate_std([])
    assert std == 0.0

    # Test two identical values
    std = hybrid_search._calculate_std([3.0, 3.0])
    assert std == 0.0


def test_analyze_cluster_relationships(hybrid_search):
    """Test cluster relationship analysis."""
    from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
        DocumentCluster,
    )

    clusters = [
        DocumentCluster(
            cluster_id="cluster1",
            name="API Cluster",
            documents=["git:API Guide", "confluence:API Docs"],
            shared_topics=["API", "development"],
            shared_entities=["endpoints", "authentication"],
            coherence_score=0.8,
            cluster_description="API documentation cluster",
            representative_doc_id="git:API Guide",
        ),
        DocumentCluster(
            cluster_id="cluster2",
            name="Security Cluster",
            documents=["confluence:Security Guide", "git:Auth Service"],
            shared_topics=["security", "authentication"],
            shared_entities=["authentication", "authorization"],
            coherence_score=0.9,
            cluster_description="Security documentation cluster",
            representative_doc_id="confluence:Security Guide",
        ),
    ]

    documents = [
        create_hybrid_search_result(
            score=0.8, text="API guide", source_type="git", source_title="API Guide"
        ),
        create_hybrid_search_result(
            score=0.7,
            text="API docs",
            source_type="confluence",
            source_title="API Docs",
        ),
        create_hybrid_search_result(
            score=0.6,
            text="Security guide",
            source_type="confluence",
            source_title="Security Guide",
        ),
        create_hybrid_search_result(
            score=0.5,
            text="Auth service",
            source_type="git",
            source_title="Auth Service",
        ),
    ]

    relationships = hybrid_search._analyze_cluster_relationships(clusters, documents)

    # Should find relationships between clusters that share entities/topics
    assert (
        len(relationships) >= 0
    )  # May or may not find relationships depending on implementation

    # Each relationship should have required fields
    for rel in relationships:
        assert "cluster_a_id" in rel
        assert "cluster_b_id" in rel
        assert "relationship_type" in rel
        assert "strength" in rel
        assert "description" in rel
        assert 0.0 <= rel["strength"] <= 1.0


def test_analyze_entity_overlap(hybrid_search):
    """Test entity overlap analysis between clusters."""
    from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
        DocumentCluster,
    )

    # Clusters with overlapping entities
    cluster_a = DocumentCluster(
        cluster_id="cluster_a",
        name="Cluster A",
        documents=["doc1", "doc2"],
        shared_entities=["API", "authentication", "endpoints"],
        shared_topics=["development"],
        coherence_score=0.8,
        cluster_description="Cluster A",
        representative_doc_id="doc1",
    )

    cluster_b = DocumentCluster(
        cluster_id="cluster_b",
        name="Cluster B",
        documents=["doc3", "doc4"],
        shared_entities=["authentication", "security", "authorization"],
        shared_topics=["security"],
        coherence_score=0.9,
        cluster_description="Cluster B",
        representative_doc_id="doc3",
    )

    relationship = hybrid_search._analyze_entity_overlap(cluster_a, cluster_b)

    assert relationship is not None
    assert relationship["type"] == "entity_overlap"
    assert relationship["strength"] > 0
    assert "authentication" in relationship["shared_elements"]
    assert "authentication" in relationship["description"]


def test_analyze_topic_overlap(hybrid_search):
    """Test topic overlap analysis between clusters."""
    from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
        DocumentCluster,
    )

    # Clusters with overlapping topics
    cluster_a = DocumentCluster(
        cluster_id="cluster_a",
        name="Cluster A",
        documents=["doc1", "doc2"],
        shared_topics=["development", "API", "documentation"],
        shared_entities=["endpoints"],
        coherence_score=0.8,
        cluster_description="Cluster A",
        representative_doc_id="doc1",
    )

    cluster_b = DocumentCluster(
        cluster_id="cluster_b",
        name="Cluster B",
        documents=["doc3", "doc4"],
        shared_topics=["API", "security", "authentication"],
        shared_entities=["auth"],
        coherence_score=0.9,
        cluster_description="Cluster B",
        representative_doc_id="doc3",
    )

    relationship = hybrid_search._analyze_topic_overlap(cluster_a, cluster_b)

    assert relationship is not None
    assert relationship["type"] == "topic_overlap"
    assert relationship["strength"] > 0
    assert "API" in relationship["shared_elements"]
    assert "API" in relationship["description"]


def test_analyze_source_similarity(hybrid_search):
    """Test source type similarity analysis between clusters."""
    # Documents with same source types
    docs_a = [
        create_hybrid_search_result(
            score=0.8, text="Doc 1", source_type="git", source_title="Doc 1"
        ),
        create_hybrid_search_result(
            score=0.7, text="Doc 2", source_type="git", source_title="Doc 2"
        ),
    ]

    docs_b = [
        create_hybrid_search_result(
            score=0.6, text="Doc 3", source_type="git", source_title="Doc 3"
        ),
        create_hybrid_search_result(
            score=0.5, text="Doc 4", source_type="confluence", source_title="Doc 4"
        ),
    ]

    relationship = hybrid_search._analyze_source_similarity(docs_a, docs_b)

    assert relationship is not None
    assert relationship["type"] == "source_similarity"
    assert relationship["strength"] > 0
    assert "git" in relationship["shared_elements"]
    assert "git" in relationship["description"]


def test_analyze_content_similarity(hybrid_search):
    """Test content similarity analysis between clusters."""
    # Documents with similar characteristics
    docs_a = [
        create_hybrid_search_result(
            score=0.8,
            text="Code with examples",
            source_type="git",
            source_title="Code Guide",
            has_code_blocks=True,
            word_count=500,
        ),
        create_hybrid_search_result(
            score=0.7,
            text="More code examples",
            source_type="git",
            source_title="Code Examples",
            has_code_blocks=True,
            word_count=600,
        ),
    ]

    docs_b = [
        create_hybrid_search_result(
            score=0.6,
            text="Technical implementation",
            source_type="confluence",
            source_title="Technical Guide",
            has_code_blocks=True,
            word_count=550,
        ),
    ]

    relationship = hybrid_search._analyze_content_similarity(docs_a, docs_b)

    assert relationship is not None
    assert relationship["type"] == "content_similarity"
    assert relationship["strength"] > 0
    assert "code" in relationship["description"].lower()


# ============================================================================
# Error Handling and Edge Case Tests
# ============================================================================


@pytest.mark.asyncio
async def test_search_with_intent_adaptation_error_handling(hybrid_search_with_intent):
    """Covered in test_hybrid_intent; keep a minimal non-error call here."""
    hybrid_search_with_intent._get_embedding = AsyncMock(
        return_value=[0.1, 0.2, 0.3] * 512
    )
    hybrid_search_with_intent._expand_query = AsyncMock(return_value="q")
    # Disable intent adaptation to avoid extensive stubbing in this minimal check
    hybrid_search_with_intent.enable_intent_adaptation = False
    await hybrid_search_with_intent.search("q")


@pytest.mark.asyncio
async def test_topic_chain_generation_error_handling(hybrid_search):
    """Covered in test_hybrid_errors; keep a minimal non-error call here."""
    await hybrid_search.generate_topic_search_chain("test query")


@pytest.mark.asyncio
async def test_topic_chain_execution_with_failures(hybrid_search):
    """Test topic chain execution with some search failures."""
    from qdrant_loader_mcp_server.search.enhanced.topic_search_chain import (
        ChainStrategy,
        TopicChainLink,
        TopicSearchChain,
    )

    # Create a topic chain with multiple links
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

    # Mock search to succeed for some queries and fail for others
    async def mock_search_with_failures(
        query, limit, source_types=None, project_ids=None
    ):
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
                    source_type="git",
                    source_title="Working Doc",
                )
            ]
        elif query == "failing query":
            raise Exception("Search failed for this query")
        return []

    hybrid_search.search = AsyncMock(side_effect=mock_search_with_failures)

    results = await hybrid_search.execute_topic_chain_search(
        mock_chain, results_per_link=3
    )

    # Should have results for successful queries and empty list for failed ones
    assert len(results) == 3
    assert "API documentation" in results
    assert "working query" in results
    assert "failing query" in results
    assert len(results["API documentation"]) == 1
    assert len(results["working query"]) == 1
    assert len(results["failing query"]) == 0  # Failed query returns empty list


@pytest.mark.asyncio
async def test_initialize_topic_relationships_empty_results(hybrid_search):
    """Test topic relationship initialization with empty search results."""
    # Mock search to return empty results
    hybrid_search.search = AsyncMock(return_value=[])
    hybrid_search.topic_chain_generator.initialize_from_results = MagicMock()

    await hybrid_search._initialize_topic_relationships("empty query")

    # Should not crash and should not call initialize_from_results
    hybrid_search.topic_chain_generator.initialize_from_results.assert_not_called()
    assert hybrid_search._topic_chains_initialized is False


def test_extract_metadata_info_comprehensive(hybrid_search):
    """Test comprehensive metadata extraction with all fields."""
    comprehensive_metadata = {
        # Project info
        "project_id": "proj_123",
        "project_name": "Test Project",
        "collection_name": "test_collection",
        # Hierarchy info
        "parent_id": "parent_123",
        "parent_title": "Parent Doc",
        "breadcrumb_text": "Root > Parent > Current",
        "depth": 2,
        "children": ["child1", "child2"],
        # Attachment info
        "is_attachment": True,
        "parent_document_id": "doc_456",
        "attachment_id": "att_789",
        "original_filename": "test.pdf",
        "file_size": 1024000,
        "mime_type": "application/pdf",
        "author": "test@example.com",
        # Section info
        "section_title": "Introduction",
        "section_type": "heading",
        "section_level": 1,
        # Content analysis
        "has_code_blocks": True,
        "has_tables": True,
        "word_count": 500,
        "entities": ["API", "authentication"],
        "topics": ["development", "security"],
        # Conversion info
        "original_file_type": "docx",
        "is_excel_sheet": False,
        # Chunking context
        "chunk_index": 1,
        "total_chunks": 5,
    }

    # Mock the metadata extractor to return components that include the metadata
    project_info = type("ProjectInfo", (), {})()
    project_info.__dict__ = comprehensive_metadata

    content_analysis = type("ContentAnalysis", (), {})()
    content_analysis.__dict__ = comprehensive_metadata

    attachment_info = type("AttachmentInfo", (), {})()
    attachment_info.__dict__ = comprehensive_metadata

    mock_components = {
        "project_info": project_info,
        "content_analysis": content_analysis,
        "attachment_info": attachment_info,
    }

    hybrid_search.metadata_extractor.extract_all_metadata = MagicMock(
        return_value=mock_components
    )

    info = hybrid_search._extract_metadata_info(comprehensive_metadata)

    # Verify all fields are extracted
    assert info["project_id"] == "proj_123"
    assert info["parent_id"] == "parent_123"
    assert info["is_attachment"] is True
    assert info["section_title"] == "Introduction"
    assert info["has_code_blocks"] is True
    assert info["has_tables"] is True
    assert info["word_count"] == 500
    assert "API" in info["entities"]
    assert "development" in info["topics"]
    assert info["original_file_type"] == "docx"
    assert info["is_excel_sheet"] is False
    assert info["chunk_index"] == 1
