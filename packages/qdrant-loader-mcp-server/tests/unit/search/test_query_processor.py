"""Tests for the query processor implementation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from qdrant_loader_mcp_server.search.processor import QueryProcessor


@pytest.fixture
def query_processor():
    """Create a query processor instance."""
    from qdrant_loader_mcp_server.config import OpenAIConfig

    openai_config = OpenAIConfig(api_key="test_key")
    return QueryProcessor(openai_config)


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client for query processing."""
    client = AsyncMock()

    # Mock chat completion response
    chat_response = MagicMock()
    chat_choice = MagicMock()
    chat_message = MagicMock()
    chat_message.content = "general"
    chat_choice.message = chat_message
    chat_response.choices = [chat_choice]
    client.chat.completions.create.return_value = chat_response

    return client


@pytest.mark.asyncio
async def test_process_query_basic(query_processor, mock_openai_client):
    """Test basic query processing."""
    with patch.object(query_processor, "openai_client", mock_openai_client):
        result = await query_processor.process_query("test query")

        assert result["query"] == "test query"
        assert result["intent"] == "general"
        assert result["source_type"] is None
        assert result["processed"] is True


@pytest.mark.asyncio
async def test_process_query_with_source_detection(query_processor, mock_openai_client):
    """Test query processing with source type detection."""
    # Mock response for git-related query
    chat_message = MagicMock()
    chat_message.content = "git"
    chat_choice = MagicMock()
    chat_choice.message = chat_message
    chat_response = MagicMock()
    chat_response.choices = [chat_choice]
    mock_openai_client.chat.completions.create.return_value = chat_response

    with patch.object(query_processor, "openai_client", mock_openai_client):
        result = await query_processor.process_query("show me git commits")

        assert result["query"] == "show me git commits"
        assert result["intent"] == "git"
        assert result["source_type"] == "git"
        assert result["processed"] is True


@pytest.mark.asyncio
async def test_process_query_error_handling(query_processor, mock_openai_client):
    """Test query processing error handling."""
    mock_openai_client.chat.completions.create.side_effect = Exception("API Error")

    with patch.object(query_processor, "openai_client", mock_openai_client):
        result = await query_processor.process_query("test query")

        # Should fallback to basic processing
        assert result["query"] == "test query"
        assert result["intent"] == "general"
        assert result["source_type"] is None
        assert result["processed"] is False


@pytest.mark.asyncio
async def test_process_query_empty_query(query_processor):
    """Test processing empty query."""
    result = await query_processor.process_query("")

    assert result["query"] == ""
    assert result["intent"] == "general"
    assert result["source_type"] is None
    assert result["processed"] is False


@pytest.mark.asyncio
async def test_process_query_confluence_detection(query_processor, mock_openai_client):
    """Test confluence source detection."""
    # Mock response for confluence-related query
    chat_message = MagicMock()
    chat_message.content = "confluence"
    chat_choice = MagicMock()
    chat_choice.message = chat_message
    chat_response = MagicMock()
    chat_response.choices = [chat_choice]
    mock_openai_client.chat.completions.create.return_value = chat_response

    with patch.object(query_processor, "openai_client", mock_openai_client):
        result = await query_processor.process_query("find confluence documentation")

        assert result["intent"] == "confluence"
        assert result["source_type"] == "confluence"


@pytest.mark.asyncio
async def test_process_query_jira_detection(query_processor, mock_openai_client):
    """Test jira source detection."""
    # Mock response for jira-related query
    chat_message = MagicMock()
    chat_message.content = "jira"
    chat_choice = MagicMock()
    chat_choice.message = chat_message
    chat_response = MagicMock()
    chat_response.choices = [chat_choice]
    mock_openai_client.chat.completions.create.return_value = chat_response

    with patch.object(query_processor, "openai_client", mock_openai_client):
        result = await query_processor.process_query("show jira tickets")

        assert result["intent"] == "jira"
        assert result["source_type"] == "jira"
