"""Unit tests for structured output functionality."""

from unittest.mock import Mock, AsyncMock
import pytest
from qdrant_loader_mcp_server.mcp import MCPHandler
from qdrant_loader_mcp_server.search.components.search_result_models import HybridSearchResult, create_hybrid_search_result


@pytest.fixture
def mock_search_engine():
    """Create mock search engine."""
    engine = Mock()
    engine.search = AsyncMock()
    return engine


@pytest.fixture
def mock_query_processor():
    """Create mock query processor."""
    processor = Mock()
    processor.process_query = AsyncMock()
    return processor


@pytest.fixture
def mcp_handler(mock_search_engine, mock_query_processor):
    """Create MCP handler with mocked dependencies."""
    return MCPHandler(mock_search_engine, mock_query_processor)


@pytest.fixture
def sample_search_results():
    """Create sample search results for testing."""
    return [
        create_hybrid_search_result(
            score=0.95,
            text="This is a test document about authentication.",
            source_title="Authentication Guide",
            source_type="confluence",
            file_path="/docs/auth.md",
            project_id="proj-123",
            created_at="2024-01-01T00:00:00Z",
            last_modified="2024-01-02T00:00:00Z"
        ),
        create_hybrid_search_result(
            score=0.87,
            text="API security best practices document.",
            source_title="Security Best Practices",
            source_type="documentation",
            file_path="/docs/security.md",
            project_id="proj-456",
            created_at="2024-01-03T00:00:00Z",
            last_modified="2024-01-04T00:00:00Z"
        )
    ]


class TestStructuredOutputFormat:
    """Test structured output format compliance."""

    @pytest.mark.asyncio
    async def test_search_returns_structured_content(self, mcp_handler, mock_query_processor, mock_search_engine, sample_search_results):
        """Test that search tool returns both text and structured content."""
        # Setup mocks
        mock_query_processor.process_query.return_value = {"query": "authentication"}
        mock_search_engine.search.return_value = sample_search_results
        
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "authentication", "limit": 5},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        
        result = response["result"]
        
        # Should have both content and structuredContent
        assert "content" in result
        assert "structuredContent" in result
        assert "isError" in result
        assert result["isError"] is False

    @pytest.mark.asyncio
    async def test_structured_content_schema_compliance(self, mcp_handler, mock_query_processor, mock_search_engine, sample_search_results):
        """Test that structured content matches the declared schema."""
        # Setup mocks
        mock_query_processor.process_query.return_value = {"query": "test"}
        mock_search_engine.search.return_value = sample_search_results
        
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "test", "limit": 5},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        structured_content = response["result"]["structuredContent"]
        
        # Check top-level structure
        assert "results" in structured_content
        assert "total_found" in structured_content
        assert "query_context" in structured_content
        
        # Check results array
        results = structured_content["results"]
        assert isinstance(results, list)
        assert len(results) == len(sample_search_results)
        
        # Check individual result structure
        for i, result_item in enumerate(results):
            assert "score" in result_item
            assert "title" in result_item
            assert "content" in result_item
            assert "source_type" in result_item
            assert "metadata" in result_item
            
            # Verify values match input
            assert result_item["score"] == sample_search_results[i].score
            assert result_item["title"] == sample_search_results[i].source_title
            assert result_item["content"] == sample_search_results[i].text
            assert result_item["source_type"] == sample_search_results[i].source_type
            
            # Check metadata structure
            metadata = result_item["metadata"]
            assert "file_path" in metadata
            assert "project_id" in metadata
            
            # Check root level fields (moved from metadata as per user request)
            assert "created_at" in result_item
            assert "updated_at" in result_item
            assert "document_id" in result_item

    @pytest.mark.asyncio
    async def test_query_context_in_structured_output(self, mcp_handler, mock_query_processor, mock_search_engine, sample_search_results):
        """Test that query context is properly included in structured output."""
        # Setup mocks
        mock_query_processor.process_query.return_value = {"query": "test query"}
        mock_search_engine.search.return_value = sample_search_results
        
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {
                "query": "test query",
                "source_types": ["confluence", "documentation"],
                "project_ids": ["proj-123"],
                "limit": 10
            },
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        query_context = response["result"]["structuredContent"]["query_context"]
        
        # Check query context structure
        assert "original_query" in query_context
        assert "source_types_filtered" in query_context
        assert "project_ids_filtered" in query_context
        
        # Verify values
        assert query_context["original_query"] == "test query"
        assert query_context["source_types_filtered"] == ["confluence", "documentation"]
        assert query_context["project_ids_filtered"] == ["proj-123"]

    @pytest.mark.asyncio
    async def test_total_found_accuracy(self, mcp_handler, mock_query_processor, mock_search_engine, sample_search_results):
        """Test that total_found count is accurate."""
        # Setup mocks
        mock_query_processor.process_query.return_value = {"query": "test"}
        mock_search_engine.search.return_value = sample_search_results
        
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "test"},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        structured_content = response["result"]["structuredContent"]
        
        assert structured_content["total_found"] == len(sample_search_results)


class TestBackwardCompatibility:
    """Test backward compatibility with text-only responses."""

    @pytest.mark.asyncio
    async def test_text_content_still_provided(self, mcp_handler, mock_query_processor, mock_search_engine, sample_search_results):
        """Test that text content is still provided for backward compatibility."""
        # Setup mocks
        mock_query_processor.process_query.return_value = {"query": "test"}
        mock_search_engine.search.return_value = sample_search_results
        
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "test"},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        result = response["result"]
        
        # Should have traditional content array
        assert "content" in result
        assert isinstance(result["content"], list)
        assert len(result["content"]) > 0
        
        # Should be text content
        content_item = result["content"][0]
        assert content_item["type"] == "text"
        assert "text" in content_item
        assert isinstance(content_item["text"], str)
        assert len(content_item["text"]) > 0

    @pytest.mark.asyncio
    async def test_text_content_includes_search_results(self, mcp_handler, mock_query_processor, mock_search_engine, sample_search_results):
        """Test that text content includes formatted search results."""
        # Setup mocks
        mock_query_processor.process_query.return_value = {"query": "test"}
        mock_search_engine.search.return_value = sample_search_results
        
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "test"},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        text_content = response["result"]["content"][0]["text"]
        
        # Should contain result count
        assert f"Found {len(sample_search_results)} results" in text_content
        
        # Should contain result details
        for result in sample_search_results:
            assert str(result.score) in text_content
            assert result.source_title in text_content or result.text in text_content


class TestStructuredOutputTypes:
    """Test different data types in structured output."""

    @pytest.mark.asyncio
    async def test_numeric_scores_are_numbers(self, mcp_handler, mock_query_processor, mock_search_engine, sample_search_results):
        """Test that scores are returned as numbers, not strings."""
        # Setup mocks
        mock_query_processor.process_query.return_value = {"query": "test"}
        mock_search_engine.search.return_value = sample_search_results
        
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "test"},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        results = response["result"]["structuredContent"]["results"]
        
        for result in results:
            assert isinstance(result["score"], (int, float))
            assert result["score"] >= 0.0
            assert result["score"] <= 1.0

    @pytest.mark.asyncio
    async def test_total_found_is_integer(self, mcp_handler, mock_query_processor, mock_search_engine, sample_search_results):
        """Test that total_found is an integer."""
        # Setup mocks
        mock_query_processor.process_query.return_value = {"query": "test"}
        mock_search_engine.search.return_value = sample_search_results
        
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "test"},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        total_found = response["result"]["structuredContent"]["total_found"]
        
        assert isinstance(total_found, int)
        assert total_found >= 0

    @pytest.mark.asyncio
    async def test_arrays_and_objects_structure(self, mcp_handler, mock_query_processor, mock_search_engine, sample_search_results):
        """Test that arrays and objects have correct structure."""
        # Setup mocks
        mock_query_processor.process_query.return_value = {"query": "test"}
        mock_search_engine.search.return_value = sample_search_results
        
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "test", "source_types": ["confluence"]},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        structured_content = response["result"]["structuredContent"]
        
        # Results should be array
        assert isinstance(structured_content["results"], list)
        
        # Query context should be object
        assert isinstance(structured_content["query_context"], dict)
        
        # Source types filtered should be array
        assert isinstance(structured_content["query_context"]["source_types_filtered"], list)


class TestStructuredOutputErrorHandling:
    """Test structured output in error conditions."""

    @pytest.mark.asyncio
    async def test_empty_results_structured_output(self, mcp_handler, mock_query_processor, mock_search_engine):
        """Test structured output when no results are found."""
        # Setup mocks for empty results
        mock_query_processor.process_query.return_value = {"query": "nonexistent"}
        mock_search_engine.search.return_value = []
        
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "nonexistent"},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        structured_content = response["result"]["structuredContent"]
        
        # Should still have proper structure
        assert "results" in structured_content
        assert "total_found" in structured_content
        assert "query_context" in structured_content
        
        # Empty results
        assert structured_content["results"] == []
        assert structured_content["total_found"] == 0
        
        # Query context should still be present
        assert structured_content["query_context"]["original_query"] == "nonexistent"

    @pytest.mark.asyncio
    async def test_structured_output_with_missing_metadata(self, mcp_handler, mock_query_processor, mock_search_engine):
        """Test structured output when search results have missing metadata."""
        # Create results with missing metadata
        incomplete_results = [
            create_hybrid_search_result(
                score=0.8,
                text="Test document",
                source_title="Test Title",
                source_type="confluence"
                # Missing file_path, project_id, etc.
            )
        ]
        
        # Setup mocks
        mock_query_processor.process_query.return_value = {"query": "test"}
        mock_search_engine.search.return_value = incomplete_results
        
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "test"},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        structured_content = response["result"]["structuredContent"]
        
        # Should handle missing metadata gracefully
        result = structured_content["results"][0]
        assert "metadata" in result
        
        # Missing fields should be empty strings or handled gracefully
        metadata = result["metadata"]
        assert "file_path" in metadata
        assert "project_id" in metadata


class TestStructuredOutputConsistency:
    """Test consistency between text and structured output."""

    @pytest.mark.asyncio
    async def test_result_count_consistency(self, mcp_handler, mock_query_processor, mock_search_engine, sample_search_results):
        """Test that result counts are consistent between text and structured output."""
        # Setup mocks
        mock_query_processor.process_query.return_value = {"query": "test"}
        mock_search_engine.search.return_value = sample_search_results
        
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "test"},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        result = response["result"]
        
        # Get counts from both formats
        text_content = result["content"][0]["text"]
        structured_total = result["structuredContent"]["total_found"]
        structured_results_count = len(result["structuredContent"]["results"])
        
        # Text should mention the count
        assert f"Found {len(sample_search_results)} results" in text_content
        
        # Structured counts should match
        assert structured_total == len(sample_search_results)
        assert structured_results_count == len(sample_search_results)

    @pytest.mark.asyncio
    async def test_query_parameter_consistency(self, mcp_handler, mock_query_processor, mock_search_engine, sample_search_results):
        """Test that query parameters are consistently reflected in both outputs."""
        # Setup mocks
        mock_query_processor.process_query.return_value = {"query": "authentication security"}
        mock_search_engine.search.return_value = sample_search_results
        
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {
                "query": "authentication security",
                "source_types": ["confluence"],
                "limit": 3
            },
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        query_context = response["result"]["structuredContent"]["query_context"]
        
        # Query context should reflect the original parameters
        assert query_context["original_query"] == "authentication security"
        assert query_context["source_types_filtered"] == ["confluence"] 