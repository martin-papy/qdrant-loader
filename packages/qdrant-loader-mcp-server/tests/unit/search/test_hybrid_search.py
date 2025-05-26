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

    search_result3 = MagicMock()
    search_result3.id = "3"
    search_result3.score = 0.6
    search_result3.payload = {
        "content": "Test content 3",
        "metadata": {"title": "Test Doc 3", "file_path": "/path/to/file.txt"},
        "source_type": "localfile",
    }

    client.search.return_value = [search_result1, search_result2, search_result3]

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

    client.scroll.return_value = (
        [scroll_result1, scroll_result2, scroll_result3],
        None,
    )
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
    client.embeddings.create.return_value = embedding_response

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
    # Mock the internal methods to avoid actual API calls
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    hybrid_search._expand_query = AsyncMock(return_value="test query")

    results = await hybrid_search.search("test query")

    assert len(results) > 0
    assert isinstance(results[0], SearchResult)
    assert results[0].score > 0
    assert results[0].text == "Test content 1"
    assert results[0].source_type == "git"


@pytest.mark.asyncio
async def test_search_with_source_type_filter(hybrid_search):
    """Test search with source type filtering."""
    # Mock the internal methods to avoid actual API calls
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    hybrid_search._expand_query = AsyncMock(return_value="test query")

    results = await hybrid_search.search("test query", source_types=["git"])

    assert len(results) > 0
    assert all(r.source_type == "git" for r in results)


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
    """Test error handling during search."""
    mock_qdrant_client.search.side_effect = Exception("Test error")

    with pytest.raises(Exception):
        await hybrid_search.search("test query")


@pytest.mark.asyncio
async def test_search_empty_results(hybrid_search, mock_qdrant_client):
    """Test handling of empty search results."""
    # Mock the internal methods to avoid actual API calls
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    hybrid_search._expand_query = AsyncMock(return_value="test query")
    hybrid_search._vector_search = AsyncMock(return_value=[])
    hybrid_search._keyword_search = AsyncMock(return_value=[])

    mock_qdrant_client.search.return_value = []
    mock_qdrant_client.scroll.return_value = ([], None)

    results = await hybrid_search.search("test query")
    assert len(results) == 0


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

    limit = 1
    results = await hybrid_search.search("test query", limit=limit)
    assert len(results) <= limit
