"""Priority coverage tests for MCP handler - targeting 195 missed lines."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from qdrant_loader_mcp_server.mcp.handler import MCPHandler
from qdrant_loader_mcp_server.search.exceptions import (
    SearchEngineError,
    QdrantConnectionError,
    Neo4jConnectionError,
    OpenAIEmbeddingError,
    HybridSearchError,
    FusionStrategyError,
    GraphitiError,
)


@pytest.fixture
def mock_search_engine():
    """Mock search engine for testing."""
    engine = AsyncMock()
    engine.search.return_value = []
    engine.enhanced_search.return_value = []
    engine.hierarchy_search.return_value = []
    engine.attachment_search.return_value = []
    engine.find_relationships.return_value = []
    engine.trace_dependencies.return_value = []
    engine.analyze_impact.return_value = []
    engine.get_temporal_context.return_value = []
    engine.fusion_benchmark.return_value = {"results": []}
    return engine


@pytest.fixture
def mock_query_processor():
    """Mock query processor for testing."""
    processor = AsyncMock()
    processor.process_query.return_value = {"query": "processed_query"}
    return processor


@pytest.fixture
def handler(mock_search_engine, mock_query_processor):
    """Create handler with mocked dependencies."""
    return MCPHandler(mock_search_engine, mock_query_processor)


class TestMCPHandlerErrorPaths:
    """Test error handling paths and edge cases."""

    @pytest.mark.asyncio
    async def test_handle_request_non_dict_input(self, handler):
        """Test handling non-dictionary request input."""
        # Test string input
        response = await handler.handle_request("invalid")
        assert response["jsonrpc"] == "2.0"
        assert response["id"] is None
        assert response["error"]["code"] == -32600
        assert "Invalid Request" in response["error"]["message"]

        # Test list input
        response = await handler.handle_request([1, 2, 3])
        assert response["jsonrpc"] == "2.0"
        assert response["id"] is None
        assert response["error"]["code"] == -32600

        # Test None input
        response = await handler.handle_request(None)
        assert response["jsonrpc"] == "2.0"
        assert response["id"] is None
        assert response["error"]["code"] == -32600

    @pytest.mark.asyncio
    async def test_handle_request_invalid_validation(self, handler):
        """Test request validation failure scenarios."""
        # Test missing jsonrpc
        request = {"method": "search", "id": 1}
        response = await handler.handle_request(request)
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["error"]["code"] == -32600

        # Test invalid jsonrpc version
        request = {"jsonrpc": "1.0", "method": "search", "id": 2}
        response = await handler.handle_request(request)
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert response["error"]["code"] == -32600

        # Test missing method
        request = {"jsonrpc": "2.0", "id": 3}
        response = await handler.handle_request(request)
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 3
        assert response["error"]["code"] == -32600

    @pytest.mark.asyncio
    async def test_handle_request_invalid_id_extraction(self, handler):
        """Test ID extraction for invalid requests."""
        # Test with invalid ID type (dict)
        request = {"jsonrpc": "2.0", "method": "search", "id": {"invalid": "id"}}
        response = await handler.handle_request(request)
        assert response["jsonrpc"] == "2.0"
        assert response["id"] is None
        assert response["error"]["code"] == -32600

        # Test with invalid ID type (list)
        request = {"jsonrpc": "2.0", "method": "search", "id": [1, 2, 3]}
        response = await handler.handle_request(request)
        assert response["jsonrpc"] == "2.0"
        assert response["id"] is None
        assert response["error"]["code"] == -32600

    @pytest.mark.asyncio
    async def test_handle_notification_requests(self, handler):
        """Test handling notification requests (no id)."""
        # Test notification with valid method
        request = {"jsonrpc": "2.0", "method": "search", "params": {"query": "test"}}
        response = await handler.handle_request(request)
        assert response == {}  # Notifications return empty response

        # Test notification with unknown method
        request = {"jsonrpc": "2.0", "method": "unknown_method"}
        response = await handler.handle_request(request)
        assert response == {}

    @pytest.mark.asyncio
    async def test_validate_fusion_strategy_invalid(self, handler):
        """Test fusion strategy validation with invalid values."""
        # Test invalid fusion strategy
        error_response = handler._validate_fusion_strategy("invalid_strategy", 1)
        assert error_response is not None
        assert error_response["error"]["code"] == -32602
        assert "Invalid fusion strategy" in error_response["error"]["data"]
        assert "Valid strategies:" in error_response["error"]["data"]

        # Test valid fusion strategy (use actual valid strategy)
        valid_response = handler._validate_fusion_strategy("weighted_sum", 1)
        assert valid_response is None

        # Test None fusion strategy (should be valid)
        none_response = handler._validate_fusion_strategy(None, 1)
        assert none_response is None

    @pytest.mark.asyncio
    async def test_handle_tools_call_method_validation(self, handler):
        """Test method validation in tools/call handling."""
        # Test with non-string method in listOfferings
        request = {
            "jsonrpc": "2.0",
            "method": ["listOfferings"],  # Invalid: list instead of string
            "id": 1,
        }
        with patch.object(handler.protocol, "validate_request", return_value=True):
            response = await handler.handle_request(request)
            assert (
                response["error"]["code"] == -32601
            )  # Method not found for invalid method type
            assert "Method not found" in response["error"]["message"]


class TestMCPHandlerAdvancedTools:
    """Test advanced tool methods with comprehensive scenarios."""

    @pytest.mark.asyncio
    async def test_handle_find_relationships_comprehensive(
        self, handler, mock_search_engine
    ):
        """Test find_relationships tool with various scenarios."""
        # Test missing entity_id
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "find_relationships", "arguments": {}},
            "id": 1,
        }
        response = await handler.handle_request(request)
        assert response["error"]["code"] == -32602
        assert "entity_id is required" in response["error"]["data"]

        # Test successful execution
        mock_search_engine.find_relationships.return_value = [
            Mock(content="Relationship 1", metadata={"type": "related_to"}),
            Mock(content="Relationship 2", metadata={"type": "depends_on"}),
        ]
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "find_relationships",
                "arguments": {
                    "entity_id": "test_entity",
                    "relationship_types": ["related_to", "depends_on"],
                    "max_depth": 2,
                    "limit": 10,
                },
            },
            "id": 2,
        }
        response = await handler.handle_request(request)
        assert "result" in response
        assert "content" in response["result"]
        assert (
            "Relationship-related content" in response["result"]["content"][0]["text"]
        )

        # Test with search engine error - since it uses fallback search, mock search instead
        mock_search_engine.search.side_effect = SearchEngineError("Connection failed")
        response = await handler.handle_request(request)
        assert response["error"]["code"] == -32603
        assert "Internal error" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_handle_trace_dependencies_comprehensive(
        self, handler, mock_search_engine
    ):
        """Test trace_dependencies tool with various scenarios."""
        # Test missing entity_id
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "trace_dependencies", "arguments": {}},
            "id": 1,
        }
        response = await handler.handle_request(request)
        assert response["error"]["code"] == -32602
        assert "entity_id is required" in response["error"]["data"]

        # Test successful execution with direction
        mock_search_engine.trace_dependencies.return_value = [
            Mock(content="Dependency 1", metadata={"level": 1}),
            Mock(content="Dependency 2", metadata={"level": 2}),
        ]
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "trace_dependencies",
                "arguments": {
                    "entity_id": "test_entity",
                    "direction": "upstream",
                    "max_depth": 3,
                    "include_transitive": True,
                },
            },
            "id": 2,
        }
        response = await handler.handle_request(request)
        assert "result" in response
        assert "content" in response["result"]
        # Note: The actual implementation uses content-based search fallback
        mock_search_engine.search.assert_called()

    @pytest.mark.asyncio
    async def test_handle_analyze_impact_comprehensive(
        self, handler, mock_search_engine
    ):
        """Test analyze_impact tool with various scenarios."""
        # Test missing entity_id
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "analyze_impact", "arguments": {}},
            "id": 1,
        }
        response = await handler.handle_request(request)
        assert response["error"]["code"] == -32602
        assert "entity_id is required" in response["error"]["data"]

        # Test successful execution with change type
        mock_search_engine.analyze_impact.return_value = [
            Mock(content="Impact analysis 1", metadata={"severity": "high"}),
            Mock(content="Impact analysis 2", metadata={"severity": "medium"}),
        ]
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "analyze_impact",
                "arguments": {
                    "entity_id": "test_entity",
                    "change_type": "modification",
                    "scope": "direct",
                    "include_downstream": True,
                },
            },
            "id": 2,
        }
        response = await handler.handle_request(request)
        assert "result" in response
        assert "content" in response["result"]
        # Note: The actual implementation uses content-based search fallback
        mock_search_engine.search.assert_called()

    @pytest.mark.asyncio
    async def test_handle_get_temporal_context_comprehensive(
        self, handler, mock_search_engine
    ):
        """Test get_temporal_context tool with various scenarios."""
        # Test missing entity_id
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "get_temporal_context", "arguments": {}},
            "id": 1,
        }
        response = await handler.handle_request(request)
        assert response["error"]["code"] == -32602
        assert "entity_id is required" in response["error"]["data"]

        # Test successful execution with time range
        mock_search_engine.get_temporal_context.return_value = [
            Mock(content="Temporal context 1", metadata={"timestamp": "2024-01-01"}),
            Mock(content="Temporal context 2", metadata={"timestamp": "2024-01-02"}),
        ]
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get_temporal_context",
                "arguments": {
                    "entity_id": "test_entity",
                    "time_range": {"start": "2024-01-01", "end": "2024-01-31"},
                    "include_related": True,
                    "granularity": "day",
                },
            },
            "id": 2,
        }
        response = await handler.handle_request(request)
        assert "result" in response
        assert "content" in response["result"]
        # Note: The actual implementation uses content-based search fallback
        mock_search_engine.search.assert_called()

    @pytest.mark.asyncio
    async def test_handle_fusion_benchmark_comprehensive(
        self, handler, mock_search_engine
    ):
        """Test fusion_benchmark tool with various scenarios."""
        # Test missing test_queries
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "fusion_benchmark", "arguments": {}},
            "id": 1,
        }
        response = await handler.handle_request(request)
        assert response["error"]["code"] == -32602
        assert "query is required" in response["error"]["data"]

        # Test successful execution
        mock_search_engine.fusion_benchmark.return_value = {
            "weighted_sum": [Mock(text="result1", score=0.8)],
            "graph_enhanced_weighted": [Mock(text="result2", score=0.9)],
        }
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "fusion_benchmark",
                "arguments": {
                    "query": "test query",
                    "strategies": ["weighted_sum", "graph_enhanced_weighted"],
                    "limit": 5,
                },
            },
            "id": 2,
        }
        response = await handler.handle_request(request)
        assert "result" in response
        assert "content" in response["result"]
        assert "Fusion Benchmark Results" in response["result"]["content"][0]["text"]
        mock_search_engine.fusion_benchmark.assert_called_with(
            query="test query",
            strategies=["weighted_sum", "graph_enhanced_weighted"],
            limit=5,
            include_debug=False,
            project_ids=[],
        )


class TestMCPHandlerGraphitiIntegration:
    """Test Graphiti integration capabilities."""

    @pytest.mark.asyncio
    async def test_handle_get_capabilities_comprehensive(self, handler):
        """Test get_capabilities tool with Graphiti scenarios."""
        # Test with Graphiti available
        with patch(
            "qdrant_loader_mcp_server.mcp.handler.get_graphiti_capabilities",
            return_value={
                "graphiti_available": True,
                "version": "1.0.0",
                "features": ["search", "relationships"],
                "status": "available",
            },
        ):
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "get_capabilities", "arguments": {}},
                "id": 1,
            }
            response = await handler.handle_request(request)
            assert response["result"]["isError"] is False
            assert "Graphiti Graph Database" in response["result"]["content"][0]["text"]
            assert "Available" in response["result"]["content"][0]["text"]

        # Test with Graphiti unavailable
        with patch(
            "qdrant_loader_mcp_server.mcp.handler.get_graphiti_capabilities",
            return_value={"graphiti_available": False},
        ):
            response = await handler.handle_request(request)
            assert response["result"]["isError"] is False
            assert "Not Available" in response["result"]["content"][0]["text"]

        # Test with Graphiti error
        with patch(
            "qdrant_loader_mcp_server.mcp.handler.get_graphiti_capabilities",
            side_effect=Exception("Graphiti error"),
        ):
            response = await handler.handle_request(request)
            assert response["error"]["code"] == -32603
            assert "Internal error" in response["error"]["message"]


class TestMCPHandlerExceptionHandling:
    """Test comprehensive exception handling scenarios."""

    @pytest.mark.asyncio
    async def test_search_engine_specific_errors(self, handler, mock_search_engine):
        """Test handling of specific search engine errors."""
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "test"},
            "id": 1,
        }

        # Test QdrantConnectionError
        mock_search_engine.search.side_effect = QdrantConnectionError(
            "Qdrant connection failed"
        )
        response = await handler.handle_request(request)
        assert response["error"]["code"] == -32603
        assert "Vector database connection failed" in response["error"]["message"]

        # Test Neo4jConnectionError
        mock_search_engine.search.side_effect = Neo4jConnectionError(
            "Neo4j connection failed"
        )
        response = await handler.handle_request(request)
        assert response["error"]["code"] == -32603
        assert "Graph database connection failed" in response["error"]["message"]

        # Test OpenAIEmbeddingError
        mock_search_engine.search.side_effect = OpenAIEmbeddingError(
            "OpenAI embedding failed"
        )
        response = await handler.handle_request(request)
        assert response["error"]["code"] == -32603
        assert "Text embedding generation failed" in response["error"]["message"]

        # Test HybridSearchError
        mock_search_engine.search.side_effect = HybridSearchError(
            "Hybrid search failed"
        )
        response = await handler.handle_request(request)
        assert response["error"]["code"] == -32603
        assert "Hybrid search operation failed" in response["error"]["message"]

        # Test FusionStrategyError
        mock_search_engine.search.side_effect = FusionStrategyError(
            "Fusion strategy failed"
        )
        response = await handler.handle_request(request)
        assert response["error"]["code"] == -32603
        assert "Result fusion failed" in response["error"]["message"]

        # Test GraphitiError
        mock_search_engine.search.side_effect = GraphitiError(
            "Graphiti operation failed"
        )
        response = await handler.handle_request(request)
        assert response["error"]["code"] == -32603
        assert "Knowledge graph search failed" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_enhanced_search_error_scenarios(self, handler, mock_search_engine):
        """Test enhanced search with various error scenarios."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "enhanced_search",
                "arguments": {"query": "test", "mode": "hybrid"},
            },
            "id": 1,
        }

        # Test with multiple exception types in enhanced search
        mock_search_engine.enhanced_search.side_effect = SearchEngineError(
            "Enhanced search failed"
        )
        response = await handler.handle_request(request)
        assert response["error"]["code"] == -32603
        assert "Internal error" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_unknown_tool_handling(self, handler):
        """Test handling of unknown tools in tools/call."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "unknown_tool", "arguments": {}},
            "id": 1,
        }
        response = await handler.handle_request(request)
        assert response["error"]["code"] == -32601
        assert "Method not found" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_unknown_method_handling(self, handler):
        """Test handling of unknown methods."""
        request = {
            "jsonrpc": "2.0",
            "method": "unknown_method",
            "params": {},
            "id": 1,
        }
        response = await handler.handle_request(request)
        assert response["error"]["code"] == -32601
        assert "Method not found" in response["error"]["message"]


class TestMCPHandlerUtilityMethods:
    """Test utility and formatting methods."""

    def test_format_search_result_edge_cases(self, handler):
        """Test search result formatting with edge cases."""
        # Test result with minimal metadata
        result = Mock()
        result.text = "Test content"
        result.score = 0.5
        result.source_type = "Unknown"
        result.source_title = "Unknown"
        result.get_project_info.return_value = ""
        result.original_filename = None
        result.attachment_context = None
        result.parent_document_title = None
        result.source_url = None
        result.file_path = None
        result.repo_name = None
        result.children_count = None
        formatted = handler._format_search_result(result)
        assert "Test content" in formatted
        assert "Unknown" in formatted

        # Test result with all metadata fields
        result.text = "Test content"
        result.score = 0.95
        result.source_type = "test_source"
        result.source_title = "Test Title"
        result.get_project_info.return_value = "Project Info"
        result.original_filename = "test.pdf"
        result.attachment_context = "Context"
        result.parent_document_title = "Parent Doc"
        result.source_url = "/test/path"
        result.file_path = "/test/path"
        result.repo_name = "test_repo"
        result.children_count = 5
        result.has_children.return_value = True
        formatted = handler._format_search_result(result)
        assert "Test content" in formatted
        assert "Test Title" in formatted
        assert "test_source" in formatted
        assert "0.95" in formatted

    def test_organize_by_hierarchy_edge_cases(self, handler):
        """Test hierarchy organization with edge cases."""
        # Test with empty results
        organized = handler._organize_by_hierarchy([])
        assert organized == {}

        # Test with results without hierarchy metadata
        results = [
            Mock(breadcrumb_text=None, source_title="Test1"),
            Mock(breadcrumb_text="", source_title="Test2"),
        ]
        organized = handler._organize_by_hierarchy(results)
        assert len(organized) >= 1

        # Test with mixed hierarchy levels
        result1 = Mock(breadcrumb_text="Root > Child1", source_title="Child1")
        result1.depth = 1
        result2 = Mock(breadcrumb_text="Root > Child2", source_title="Child2")
        result2.depth = 1
        result3 = Mock(breadcrumb_text="Other > Child3", source_title="Child3")
        result3.depth = 1

        results = [result1, result2, result3]
        organized = handler._organize_by_hierarchy(results)
        assert len(organized) >= 2

    def test_apply_hierarchy_filters_edge_cases(self, handler):
        """Test hierarchy filters with edge cases."""
        # Test with empty filter - must be confluence source
        results = [Mock(source_type="confluence", depth=1)]
        filtered = handler._apply_hierarchy_filters(results, {})
        assert len(filtered) == 1

        # Test with multiple filter conditions
        result1 = Mock(source_type="confluence")
        result1.depth = 1
        result1.parent_title = "Test"
        result1.has_children.return_value = True
        result1.is_root_document.return_value = False

        result2 = Mock(source_type="confluence")
        result2.depth = 2
        result2.parent_title = "Other"
        result2.has_children.return_value = False
        result2.is_root_document.return_value = False

        results = [result1, result2]
        hierarchy_filter = {
            "depth": 1,
            "has_children": True,
            "parent_title": "Test",
        }
        filtered = handler._apply_hierarchy_filters(results, hierarchy_filter)
        assert len(filtered) == 1

    def test_apply_attachment_filters_edge_cases(self, handler):
        """Test attachment filters with edge cases."""
        # Test with empty filter - must be confluence source
        results = [Mock(source_type="confluence", is_attachment=True)]
        filtered = handler._apply_attachment_filters(results, {})
        assert len(filtered) == 1

        # Test with complex filter combinations
        result1 = Mock(source_type="confluence")
        result1.is_attachment = True
        result1.get_file_type.return_value = "pdf"
        result1.file_size = 1024
        result1.attachment_author = "test_author"
        result1.parent_document_title = "Test Doc"

        result2 = Mock(source_type="confluence")
        result2.is_attachment = True
        result2.get_file_type.return_value = "docx"
        result2.file_size = 2048
        result2.attachment_author = "other_author"
        result2.parent_document_title = "Other Doc"

        results = [result1, result2]
        attachment_filter = {
            "attachments_only": True,
            "file_type": "pdf",
            "file_size_min": 500,
            "file_size_max": 1500,
            "author": "test_author",
        }
        filtered = handler._apply_attachment_filters(results, attachment_filter)
        assert len(filtered) == 1
