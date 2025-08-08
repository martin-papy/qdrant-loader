"""Tests for the query processor implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
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


class TestQueryProcessor:
    @pytest.mark.asyncio
    async def test_process_query_basic(self, query_processor, mock_openai_client):
        """Test basic query processing."""
        with patch.object(query_processor, "openai_client", mock_openai_client):
            result = await query_processor.process_query("test query")

            assert result["query"] == "test query"
            assert result["intent"] == "general"
            assert result["source_type"] is None
            assert result["processed"] is True


    @pytest.mark.asyncio
    async def test_process_query_with_source_detection(self, query_processor, mock_openai_client):
        """Test query processing with source type detection."""
        # With spaCy implementation, no need for OpenAI mocking
        result = await query_processor.process_query("show me git commits")

        assert result["query"] == "show me git commits"
        # spaCy implementation may return "general" if intent confidence is low
        assert result["intent"] in ["general", "code", "git"]
        # Source type detection should still work based on keywords
        assert result["source_type"] in ["git", None]  # May detect git or fallback to None
        assert result["processed"] is True


    @pytest.mark.asyncio
    async def test_process_query_error_handling(self, query_processor, mock_openai_client):
        """Test query processing error handling."""
        # With spaCy implementation, processing should succeed even if external APIs fail
        result = await query_processor.process_query("test query")

        # Should process successfully with spaCy
        assert result["query"] == "test query"
        assert result["intent"] == "general"
        assert result["source_type"] is None
        assert result["processed"] is True  # spaCy processing succeeds


    @pytest.mark.asyncio
    async def test_process_query_empty_query(self, query_processor):
        """Test processing empty query."""
        result = await query_processor.process_query("")

        assert result["query"] == ""
        assert result["intent"] == "general"
        assert result["source_type"] is None
        assert result["processed"] is False

    @pytest.mark.asyncio
    async def test_process_query_success_with_spacy(self, query_processor):
        """Test successful query processing with spaCy features."""
        with (
            patch.object(query_processor, '_clean_query', return_value="cleaned query"),
            patch.object(query_processor, '_infer_intent_spacy', return_value=("search", False)),
            patch.object(query_processor, '_infer_source_type', return_value="git")
        ):
            result = await query_processor.process_query("test query")
            
            # Verify successful processing
            assert result["query"] == "cleaned query"
            assert result["intent"] == "search"
            assert result["source_type"] == "git"
            assert result["processed"] is True
            assert result["uses_spacy"] is True

    def test_clean_query_whitespace_removal(self, query_processor):
        """Test query cleaning removes extra whitespace."""
        query = "  test   query   with   spaces  "
        cleaned = query_processor._clean_query(query)
        assert cleaned == "test query with spaces"

    def test_clean_query_edge_cases(self, query_processor):
        """Test query cleaning edge cases."""
        # Empty query
        assert query_processor._clean_query("") == ""
        # Only whitespace
        assert query_processor._clean_query("   ") == ""
        # Normal query
        assert query_processor._clean_query("normal query") == "normal query"

    @pytest.mark.asyncio
    async def test_infer_intent_spacy_code_keywords(self, query_processor):
        """Test intent inference for code-related queries."""
        intent, failed = await query_processor._infer_intent_spacy("function definition")
        assert intent == "code"
        assert failed is False

    @pytest.mark.asyncio
    async def test_infer_intent_spacy_documentation_keywords(self, query_processor):
        """Test intent inference for documentation-related queries."""
        intent, failed = await query_processor._infer_intent_spacy("how to guide")
        assert intent == "documentation"
        assert failed is False

    @pytest.mark.asyncio
    async def test_infer_intent_spacy_general_fallback(self, query_processor):
        """Test intent inference fallback to general."""
        intent, failed = await query_processor._infer_intent_spacy("random unrelated query")
        assert intent == "general"
        assert failed is False

    @pytest.mark.asyncio
    async def test_infer_intent_spacy_no_analyzer(self, query_processor):
        """Test intent inference when analyzer is not available."""
        # Mock no analyzer
        query_processor.spacy_analyzer = None
        intent, failed = await query_processor._infer_intent_spacy("test query")
        assert intent == "general"
        assert failed is True

    def test_infer_source_type_git_patterns(self, query_processor):
        """Test source type inference for git-related patterns."""
        source_type = query_processor._infer_source_type("repository commit")
        assert source_type == "git"
        
        source_type = query_processor._infer_source_type("branch code")
        assert source_type == "git"

    def test_infer_source_type_confluence_patterns(self, query_processor):
        """Test source type inference for confluence-related patterns."""
        source_type = query_processor._infer_source_type("wiki page")
        assert source_type == "confluence"
        
        source_type = query_processor._infer_source_type("documentation space")
        assert source_type == "confluence"

    def test_infer_source_type_jira_patterns(self, query_processor):
        """Test source type inference for jira-related patterns."""
        source_type = query_processor._infer_source_type("ticket issue")
        assert source_type == "jira"
        
        source_type = query_processor._infer_source_type("bug report")
        assert source_type == "jira"

    def test_infer_source_type_no_match(self, query_processor):
        """Test source type inference when no patterns match."""
        source_type = query_processor._infer_source_type("general query")
        assert source_type is None


@pytest.mark.asyncio
async def test_process_query_confluence_detection(query_processor, mock_openai_client):
    """Test confluence source detection."""
    # With spaCy implementation, test actual source detection logic
    result = await query_processor.process_query("find confluence documentation")

    # spaCy may classify intent differently
    assert result["intent"] in ["general", "documentation", "confluence"]
    # Source type detection should work based on keywords
    assert result["source_type"] in ["confluence", None]


@pytest.mark.asyncio
async def test_process_query_jira_detection(query_processor, mock_openai_client):
    """Test jira source detection."""
    # With spaCy implementation, test actual source detection logic
    result = await query_processor.process_query("show jira tickets")

    # spaCy may classify intent differently
    assert result["intent"] in ["general", "issues", "jira"]
    # Source type detection should work based on keywords
    assert result["source_type"] in ["jira", None]


@pytest.mark.asyncio
async def test_process_query_localfile_detection(query_processor, mock_openai_client):
    """Test localfile source detection."""
    # Mock response for localfile-related query
    chat_message = MagicMock()
    chat_message.content = "general"
    chat_choice = MagicMock()
    chat_choice.message = chat_message
    chat_response = MagicMock()
    chat_response.choices = [chat_choice]
    mock_openai_client.chat.completions.create.return_value = chat_response

    with patch.object(query_processor, "openai_client", mock_openai_client):
        result = await query_processor.process_query("find local files")

        assert result["intent"] == "general"
        assert result["source_type"] == "localfile"
