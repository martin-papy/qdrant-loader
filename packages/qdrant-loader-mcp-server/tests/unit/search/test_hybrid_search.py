"""Tests for hybrid search implementation."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from openai import AsyncOpenAI
from qdrant_loader_mcp_server.search.hybrid_search import HybridSearchEngine
from qdrant_loader_mcp_server.search.models import SearchResult


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client."""
    client = MagicMock()

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

    client.search.return_value = [search_result1, search_result2]

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

    client.scroll.return_value = ([scroll_result1, scroll_result2], None)
    return client


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    client = AsyncMock(spec=AsyncOpenAI)
    client.embeddings.create.return_value.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
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
    results = await hybrid_search.search("test query")

    assert len(results) > 0
    assert isinstance(results[0], SearchResult)
    assert results[0].score > 0
    assert results[0].text == "Test content 1"
    assert results[0].source_type == "git"


@pytest.mark.asyncio
async def test_search_with_source_type_filter(hybrid_search):
    """Test search with source type filtering."""
    results = await hybrid_search.search("test query", source_types=["git"])

    assert len(results) > 0
    assert all(r.source_type == "git" for r in results)


@pytest.mark.asyncio
async def test_search_query_expansion(hybrid_search):
    """Test query expansion functionality."""
    await hybrid_search.search("product requirements for API")

    # Verify that the expanded query was used
    assert (
        hybrid_search.openai_client.embeddings.create.call_args[1]["input"]
        .lower()
        .count("api")
        > 1
    )


@pytest.mark.asyncio
async def test_search_error_handling(hybrid_search, mock_qdrant_client):
    """Test error handling during search."""
    mock_qdrant_client.search.side_effect = Exception("Test error")

    with pytest.raises(Exception):
        await hybrid_search.search("test query")


@pytest.mark.asyncio
async def test_search_empty_results(hybrid_search, mock_qdrant_client):
    """Test handling of empty search results."""
    mock_qdrant_client.search.return_value = []
    mock_qdrant_client.scroll.return_value = ([], None)

    results = await hybrid_search.search("test query")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_search_result_scoring(hybrid_search):
    """Test that search results are properly scored and ranked."""
    results = await hybrid_search.search("test query")

    # Check that results are sorted by score
    assert all(
        results[i].score >= results[i + 1].score for i in range(len(results) - 1)
    )


@pytest.mark.asyncio
async def test_search_with_limit(hybrid_search):
    """Test search with result limit."""
    limit = 1
    results = await hybrid_search.search("test query", limit=limit)
    assert len(results) <= limit
