"""Tests for the search engine implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_loader_mcp_server.config import OpenAIConfig, QdrantConfig
from qdrant_loader_mcp_server.search.engine import SearchEngine
from qdrant_loader_mcp_server.search.components.search_result_models import HybridSearchResult, create_hybrid_search_result


@pytest.fixture
def search_engine():
    """Create a search engine instance."""
    return SearchEngine()


@pytest.fixture
def qdrant_config():
    """Create Qdrant configuration."""
    return QdrantConfig(
        url="http://localhost:6333",
        api_key="test_key",
        collection_name="test_collection",
    )


@pytest.fixture
def openai_config():
    """Create OpenAI configuration."""
    return OpenAIConfig(api_key="test_key")


@pytest.mark.asyncio
async def test_search_engine_initialization(
    search_engine, qdrant_config, openai_config, mock_qdrant_client, mock_openai_client
):
    """Test search engine initialization."""
    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.HybridSearchEngine"
        ) as mock_hybrid,
    ):

        await search_engine.initialize(qdrant_config, openai_config)

        assert search_engine.client is not None
        assert search_engine.openai_client is not None
        assert search_engine.hybrid_search is not None
        mock_hybrid.assert_called_once()


@pytest.mark.asyncio
async def test_search_engine_initialization_failure(
    search_engine, qdrant_config, openai_config
):
    """Test search engine initialization failure."""
    with patch(
        "qdrant_loader_mcp_server.search.engine.AsyncQdrantClient",
        side_effect=Exception("Connection failed"),
    ):
        with pytest.raises(RuntimeError, match="Failed to connect to Qdrant server"):
            await search_engine.initialize(qdrant_config, openai_config)


@pytest.mark.asyncio
async def test_search_engine_search(
    search_engine, qdrant_config, openai_config, mock_qdrant_client, mock_openai_client
):
    """Test search functionality."""
    # Mock hybrid search
    mock_hybrid_search = AsyncMock()
    mock_results = [
        create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="git",
            source_title="Test Doc",
            source_url="http://test.com",
        )
    ]
    mock_hybrid_search.search.return_value = mock_results

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):

        await search_engine.initialize(qdrant_config, openai_config)
        results = await search_engine.search("test query", ["git"], 5)

        assert len(results) == 1
        assert results[0].text == "Test content"
        assert results[0].source_type == "git"
        mock_hybrid_search.search.assert_called_once_with(
            query="test query", source_types=["git"], limit=5, project_ids=None
        )


@pytest.mark.asyncio
async def test_search_engine_search_not_initialized(search_engine):
    """Test search when engine is not initialized."""
    with pytest.raises(RuntimeError, match="Search engine not initialized"):
        await search_engine.search("test query")


@pytest.mark.asyncio
async def test_search_engine_cleanup(
    search_engine, qdrant_config, openai_config, mock_qdrant_client, mock_openai_client
):
    """Test search engine cleanup."""
    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch("qdrant_loader_mcp_server.search.engine.HybridSearchEngine"),
    ):

        await search_engine.initialize(qdrant_config, openai_config)
        await search_engine.cleanup()

        mock_qdrant_client.close.assert_called_once()
        assert search_engine.client is None


@pytest.mark.asyncio
async def test_search_engine_collection_creation(
    search_engine, qdrant_config, openai_config, mock_qdrant_client, mock_openai_client
):
    """Test collection creation when it doesn't exist."""
    # Mock empty collections list
    collections_response = MagicMock()
    collections_response.collections = []
    mock_qdrant_client.get_collections.return_value = collections_response

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch("qdrant_loader_mcp_server.search.engine.HybridSearchEngine"),
    ):

        await search_engine.initialize(qdrant_config, openai_config)

        mock_qdrant_client.create_collection.assert_called_once()


@pytest.mark.asyncio
async def test_search_engine_collection_exists(
    search_engine, qdrant_config, openai_config, mock_qdrant_client, mock_openai_client
):
    """Test when collection already exists."""
    # Mock existing collection
    collection = MagicMock()
    collection.name = "test_collection"
    collections_response = MagicMock()
    collections_response.collections = [collection]
    mock_qdrant_client.get_collections.return_value = collections_response

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch("qdrant_loader_mcp_server.search.engine.HybridSearchEngine"),
    ):

        await search_engine.initialize(qdrant_config, openai_config)

        mock_qdrant_client.create_collection.assert_not_called()
