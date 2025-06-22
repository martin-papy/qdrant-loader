"""Focused tests to boost MCP handler coverage."""

from unittest.mock import AsyncMock, Mock

import pytest
from qdrant_loader_mcp_server.mcp.handler import MCPHandler
from qdrant_loader_mcp_server.search.engine import SearchEngine
from qdrant_loader_mcp_server.search.exceptions import SearchEngineError
from qdrant_loader_mcp_server.search.models import SearchResult
from qdrant_loader_mcp_server.search.processor import QueryProcessor


class TestMCPHandlerCoverageBoost:
    """Tests to boost MCP handler coverage."""

    @pytest.fixture
    def mock_search_engine(self):
        """Create a mock SearchEngine."""
        engine = Mock(spec=SearchEngine)
        engine.search = AsyncMock()
        engine.get_search_capabilities = Mock(
            return_value={"enhanced_hybrid_search": True}
        )
        return engine

    @pytest.fixture
    def mock_query_processor(self):
        """Create a mock QueryProcessor."""
        processor = Mock(spec=QueryProcessor)
        processor.process_query = AsyncMock(return_value={"query": "processed"})
        return processor

    @pytest.fixture
    def mcp_handler(self, mock_search_engine, mock_query_processor):
        """Create an MCPHandler instance."""
        return MCPHandler(mock_search_engine, mock_query_processor)

    @pytest.fixture
    def sample_results(self):
        """Create sample search results."""
        return [
            SearchResult(
                text="Test content",
                score=0.95,
                source_type="confluence",
                source_title="Test Document",
                source_url="https://example.com/doc",
            )
        ]

    # Test error handling paths

    @pytest.mark.asyncio
    async def test_handle_request_invalid_input_types(self, mcp_handler):
        """Test handling various invalid input types."""
        # Test with None
        response = await mcp_handler.handle_request(None)
        assert response["error"]["code"] == -32600

        # Test with string
        response = await mcp_handler.handle_request("invalid")
        assert response["error"]["code"] == -32600

        # Test with number
        response = await mcp_handler.handle_request(123)
        assert response["error"]["code"] == -32600

    @pytest.mark.asyncio
    async def test_handle_request_missing_required_fields(self, mcp_handler):
        """Test handling requests with missing required fields."""
        # Missing jsonrpc
        response = await mcp_handler.handle_request({"method": "test", "id": 1})
        assert response["error"]["code"] == -32600

        # Missing method
        response = await mcp_handler.handle_request({"jsonrpc": "2.0", "id": 1})
        assert response["error"]["code"] == -32600

        # Wrong jsonrpc version
        response = await mcp_handler.handle_request(
            {"jsonrpc": "1.0", "method": "test", "id": 1}
        )
        assert response["error"]["code"] == -32600

    @pytest.mark.asyncio
    async def test_handle_request_invalid_id_types(self, mcp_handler):
        """Test handling requests with invalid ID types."""
        # Dict as ID
        response = await mcp_handler.handle_request(
            {"jsonrpc": "2.0", "method": "test", "id": {"invalid": True}}
        )
        assert response["error"]["code"] == -32600

        # List as ID
        response = await mcp_handler.handle_request(
            {"jsonrpc": "2.0", "method": "test", "id": [1, 2, 3]}
        )
        assert response["error"]["code"] == -32600

    @pytest.mark.asyncio
    async def test_handle_notification_no_response(self, mcp_handler):
        """Test notification requests return empty response."""
        response = await mcp_handler.handle_request(
            {"jsonrpc": "2.0", "method": "notification"}
        )
        assert response == {}

    @pytest.mark.asyncio
    async def test_handle_unknown_method(self, mcp_handler):
        """Test handling unknown methods."""
        response = await mcp_handler.handle_request(
            {"jsonrpc": "2.0", "method": "unknown_method", "id": 1}
        )
        assert response["error"]["code"] == -32601
        assert "Method not found" in response["error"]["message"]

    # Test search error handling

    @pytest.mark.asyncio
    async def test_search_with_search_engine_error(
        self, mcp_handler, mock_search_engine
    ):
        """Test search with SearchEngineError."""
        mock_search_engine.search.side_effect = SearchEngineError(
            "Search failed", error_code="SEARCH_001"
        )

        response = await mcp_handler.handle_request(
            {"jsonrpc": "2.0", "method": "search", "params": {"query": "test"}, "id": 1}
        )

        assert response["error"]["code"] == -32603
        assert "Search error" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_search_with_generic_exception(self, mcp_handler, mock_search_engine):
        """Test search with generic exception."""
        mock_search_engine.search.side_effect = ValueError("Unexpected error")

        response = await mcp_handler.handle_request(
            {"jsonrpc": "2.0", "method": "search", "params": {"query": "test"}, "id": 1}
        )

        assert response["error"]["code"] == -32603
        assert "Unexpected search error" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_search_empty_results(self, mcp_handler, mock_search_engine):
        """Test search returning empty results."""
        mock_search_engine.search.return_value = []

        response = await mcp_handler.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "search",
                "params": {"query": "nothing"},
                "id": 1,
            }
        )

        assert response["result"]["isError"] is False
        assert "Found 0 results" in response["result"]["content"][0]["text"]

    # Test enhanced search error paths

    @pytest.mark.asyncio
    async def test_enhanced_search_missing_query(self, mcp_handler):
        """Test enhanced search without query parameter."""
        response = await mcp_handler.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "enhanced_search", "arguments": {}},
                "id": 1,
            }
        )

        assert response["error"]["code"] == -32602
        assert "Missing required parameter: query" in response["error"]["data"]

    @pytest.mark.asyncio
    async def test_enhanced_search_invalid_mode(self, mcp_handler):
        """Test enhanced search with invalid mode."""
        response = await mcp_handler.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "enhanced_search",
                    "arguments": {"query": "test", "mode": "invalid_mode"},
                },
                "id": 1,
            }
        )

        assert response["error"]["code"] == -32602
        assert "Invalid search mode" in response["error"]["data"]

    @pytest.mark.asyncio
    async def test_enhanced_search_invalid_weights(self, mcp_handler):
        """Test enhanced search with invalid weight values."""
        response = await mcp_handler.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "enhanced_search",
                    "arguments": {
                        "query": "test",
                        "vector_weight": 1.5,  # Invalid: > 1.0
                    },
                },
                "id": 1,
            }
        )

        assert response["error"]["code"] == -32602
        assert "Invalid vector_weight" in response["error"]["data"]

    # Test hierarchy search error paths

    @pytest.mark.asyncio
    async def test_hierarchy_search_missing_query(self, mcp_handler):
        """Test hierarchy search without query parameter."""
        response = await mcp_handler.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "hierarchy_search", "arguments": {}},
                "id": 1,
            }
        )

        assert response["error"]["code"] == -32602

    # Test attachment search error paths

    @pytest.mark.asyncio
    async def test_attachment_search_missing_query(self, mcp_handler):
        """Test attachment search without query parameter."""
        response = await mcp_handler.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "attachment_search", "arguments": {}},
                "id": 1,
            }
        )

        assert response["error"]["code"] == -32602

    # Test relationship search error paths

    @pytest.mark.asyncio
    async def test_enrich_with_relationships_missing_query(self, mcp_handler):
        """Test relationship enrichment without query parameter."""
        response = await mcp_handler.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "enrich_with_relationships", "arguments": {}},
                "id": 1,
            }
        )

        assert response["error"]["code"] == -32602

    # Test advanced tools error paths

    @pytest.mark.asyncio
    async def test_find_relationships_missing_entity_id(self, mcp_handler):
        """Test find relationships without entity_id."""
        response = await mcp_handler.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "find_relationships", "arguments": {}},
                "id": 1,
            }
        )

        assert response["error"]["code"] == -32602

    @pytest.mark.asyncio
    async def test_trace_dependencies_missing_entity_id(self, mcp_handler):
        """Test trace dependencies without entity_id."""
        response = await mcp_handler.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "trace_dependencies", "arguments": {}},
                "id": 1,
            }
        )

        assert response["error"]["code"] == -32602

    @pytest.mark.asyncio
    async def test_analyze_impact_missing_entity_id(self, mcp_handler):
        """Test analyze impact without entity_id."""
        response = await mcp_handler.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "analyze_impact", "arguments": {}},
                "id": 1,
            }
        )

        assert response["error"]["code"] == -32602

    @pytest.mark.asyncio
    async def test_get_temporal_context_missing_entity_id(self, mcp_handler):
        """Test get temporal context without entity_id."""
        response = await mcp_handler.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "get_temporal_context", "arguments": {}},
                "id": 1,
            }
        )

        assert response["error"]["code"] == -32602

    @pytest.mark.asyncio
    async def test_fusion_benchmark_missing_test_queries(self, mcp_handler):
        """Test fusion benchmark without test_queries."""
        response = await mcp_handler.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "fusion_benchmark", "arguments": {}},
                "id": 1,
            }
        )

        assert response["error"]["code"] == -32602

    # Test format and filter methods

    def test_format_search_result(self, mcp_handler, sample_results):
        """Test search result formatting."""
        result = sample_results[0]
        formatted = mcp_handler._format_search_result(result)

        assert "Test Document" in formatted
        assert "Test content" in formatted
        assert "Score: 0.95" in formatted

    def test_organize_by_hierarchy(self, mcp_handler, sample_results):
        """Test hierarchy organization."""
        # Add hierarchy info to results
        sample_results[0].parent_title = "Parent"

        organized = mcp_handler._organize_by_hierarchy(sample_results)
        # Results are organized by source_title, not parent_title
        assert "Test Document" in organized
        assert len(organized["Test Document"]) == 1

    def test_apply_hierarchy_filters(self, mcp_handler, sample_results):
        """Test hierarchy filtering."""
        # Add depth to results
        sample_results[0].depth = 2

        filtered = mcp_handler._apply_hierarchy_filters(sample_results, {"depth": 2})
        assert len(filtered) == 1

    def test_apply_attachment_filters(self, mcp_handler, sample_results):
        """Test attachment filtering."""
        # Make result an attachment
        sample_results[0].is_attachment = True

        filtered = mcp_handler._apply_attachment_filters(
            sample_results, {"attachments_only": True}
        )
        assert len(filtered) == 1

    # Test successful operations

    @pytest.mark.asyncio
    async def test_search_successful(
        self, mcp_handler, mock_search_engine, sample_results
    ):
        """Test successful search operation."""
        mock_search_engine.search.return_value = sample_results

        response = await mcp_handler.handle_request(
            {"jsonrpc": "2.0", "method": "search", "params": {"query": "test"}, "id": 1}
        )

        assert response["result"]["isError"] is False
        assert len(response["result"]["content"]) > 0

    @pytest.mark.asyncio
    async def test_hierarchy_search_successful(
        self, mcp_handler, mock_search_engine, sample_results
    ):
        """Test successful hierarchy search."""
        mock_search_engine.search.return_value = sample_results

        response = await mcp_handler.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "hierarchy_search",
                    "arguments": {"query": "test", "organize_by_hierarchy": True},
                },
                "id": 1,
            }
        )

        assert response["result"]["isError"] is False

    @pytest.mark.asyncio
    async def test_attachment_search_successful(
        self, mcp_handler, mock_search_engine, sample_results
    ):
        """Test successful attachment search."""
        mock_search_engine.search.return_value = sample_results

        response = await mcp_handler.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "attachment_search",
                    "arguments": {"query": "test", "include_parent_context": True},
                },
                "id": 1,
            }
        )

        assert response["result"]["isError"] is False
