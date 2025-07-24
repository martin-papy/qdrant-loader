"""Integration tests for MCP server functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from qdrant_loader_mcp_server.mcp.handler import MCPHandler
from qdrant_loader_mcp_server.search.engine import SearchEngine
from qdrant_loader_mcp_server.search.processor import QueryProcessor


@pytest_asyncio.fixture
async def integration_handler():
    """Create an MCP handler with real components but mocked external services."""
    # Mock external services
    mock_qdrant_client = AsyncMock()
    mock_openai_client = AsyncMock()

    # Mock search results
    search_result1 = MagicMock()
    search_result1.id = "1"
    search_result1.score = 0.8
    search_result1.payload = {
        "content": "Integration test content 1",
        "metadata": {"title": "Integration Test Doc 1", "url": "http://test1.com"},
        "source_type": "git",
    }

    mock_qdrant_client.search.return_value = [search_result1]
    mock_qdrant_client.scroll.return_value = ([search_result1], None)
    
    # Mock collections response for get_collections
    collections_response = MagicMock()
    collections_response.collections = []
    mock_qdrant_client.get_collections.return_value = collections_response
    mock_qdrant_client.create_collection.return_value = None
    mock_qdrant_client.close.return_value = None

    # Mock OpenAI responses
    embedding_response = MagicMock()
    embedding_data = MagicMock()
    embedding_data.embedding = [0.1, 0.2, 0.3] * 512
    embedding_response.data = [embedding_data]
    mock_openai_client.embeddings.create.return_value = embedding_response

    chat_response = MagicMock()
    chat_choice = MagicMock()
    chat_message = MagicMock()
    chat_message.content = "general"
    chat_choice.message = chat_message
    chat_response.choices = [chat_choice]
    mock_openai_client.chat.completions.create.return_value = chat_response

    # Create real components with mocked dependencies
    search_engine = SearchEngine()

    # Create OpenAI config for query processor
    from qdrant_loader_mcp_server.config import OpenAIConfig

    openai_config = OpenAIConfig(api_key="test_key")
    query_processor = QueryProcessor(openai_config)

    # Patch external dependencies
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
            "qdrant_loader_mcp_server.search.processor.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
    ):

        # Initialize components
        from qdrant_loader_mcp_server.config import OpenAIConfig, QdrantConfig

        qdrant_config = QdrantConfig(api_key="test_key")
        openai_config = OpenAIConfig(api_key="test_key")

        await search_engine.initialize(qdrant_config, openai_config)

        # Create handler
        handler = MCPHandler(search_engine, query_processor)

        yield handler

        # Cleanup
        await search_engine.cleanup()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_search_workflow(integration_handler):
    """Test complete search workflow from MCP request to response."""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "search",
            "arguments": {"query": "integration test query", "limit": 5},
        },
        "id": 1,
    }

    response = await integration_handler.handle_request(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    assert "content" in response["result"]
    assert response["result"]["isError"] is False

    # Check that content contains search results
    content = response["result"]["content"]
    assert len(content) > 0
    assert "Integration test content 1" in str(content)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_search_with_source_filtering(integration_handler):
    """Test search with source type filtering."""
    request = {
        "jsonrpc": "2.0",
        "method": "search",
        "params": {"query": "test query", "source_types": ["git"], "limit": 3},
        "id": 2,
    }

    response = await integration_handler.handle_request(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 2
    assert "result" in response
    assert "content" in response["result"]
    assert response["result"]["isError"] is False


@pytest.mark.asyncio
@pytest.mark.integration
async def test_initialize_and_tools_list_workflow(integration_handler):
    """Test initialization and tools listing workflow."""
    # Test initialize
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
        },
        "id": 1,
    }

    init_response = await integration_handler.handle_request(init_request)
    assert init_response["jsonrpc"] == "2.0"
    assert init_response["id"] == 1
    assert "result" in init_response

    # Test tools list
    tools_request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 2,
    }

    tools_response = await integration_handler.handle_request(tools_request)
    assert tools_response["jsonrpc"] == "2.0"
    assert tools_response["id"] == 2
    assert "result" in tools_response
    assert "tools" in tools_response["result"]
    assert len(tools_response["result"]["tools"]) == 3


@pytest.mark.asyncio
@pytest.mark.integration
async def test_error_handling_integration(integration_handler):
    """Test error handling in integration scenario."""
    # Test invalid tool call
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "invalid_tool", "arguments": {}},
        "id": 3,
    }

    response = await integration_handler.handle_request(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 3
    assert "error" in response
    assert response["error"]["code"] == -32601


@pytest.mark.asyncio
@pytest.mark.integration
async def test_search_empty_results(integration_handler):
    """Test search with no results."""
    # Mock empty results
    with patch.object(integration_handler.search_engine, "search", return_value=[]):
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "nonexistent query", "limit": 5},
            "id": 4,
        }

        response = await integration_handler.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 4
        assert "result" in response
        assert "content" in response["result"]
        assert response["result"]["isError"] is False
