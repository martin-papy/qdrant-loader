"""Unit tests for MCP Protocol 2025-06-18 compliance."""

from unittest.mock import Mock

import pytest
from qdrant_loader_mcp_server.mcp import MCPHandler


@pytest.fixture
def mcp_handler():
    """Create MCP handler fixture with mocked dependencies."""
    search_engine = Mock()
    query_processor = Mock()
    return MCPHandler(search_engine, query_processor)


class TestProtocolVersionCompliance:
    """Test MCP Protocol 2025-06-18 version compliance."""

    @pytest.mark.asyncio
    async def test_initialize_returns_correct_protocol_version(self, mcp_handler):
        """Test that initialize response returns 2025-06-18 protocol version."""
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {"listChanged": False}},
            },
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2025-06-18"
        assert response["result"]["serverInfo"]["name"] == "Qdrant Loader MCP Server"

    @pytest.mark.asyncio
    async def test_protocol_version_header_validation(self, mcp_handler):
        """Test protocol version header validation with backward compatibility."""
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
            "id": 1,
        }
        
        # Test with valid protocol version header
        headers = {"mcp-protocol-version": "2025-06-18"}
        response = await mcp_handler.handle_request(request, headers=headers)
        assert response["result"]["protocolVersion"] == "2025-06-18"
        
        # Test with older supported version
        headers = {"mcp-protocol-version": "2024-11-05"}
        response = await mcp_handler.handle_request(request, headers=headers)
        assert response["result"]["protocolVersion"] == "2025-06-18"  # Server returns its version
        
        # Test without header (backward compatibility)
        response = await mcp_handler.handle_request(request)
        assert response["result"]["protocolVersion"] == "2025-06-18"

    @pytest.mark.asyncio
    async def test_unsupported_protocol_version_warning(self, mcp_handler):
        """Test that unsupported protocol versions generate warning but continue processing."""
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
            "id": 1,
        }
        
        # Test with unsupported version - should still work but log warning
        headers = {"mcp-protocol-version": "unsupported-version"}
        response = await mcp_handler.handle_request(request, headers=headers)
        
        # Should still return successful response
        assert response["result"]["protocolVersion"] == "2025-06-18"


class TestToolBehavioralAnnotations:
    """Test tool behavioral annotations compliance."""

    @pytest.mark.asyncio
    async def test_all_tools_have_annotations(self, mcp_handler):
        """Test that all tools have behavioral annotations."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        
        assert "result" in response
        assert "tools" in response["result"]
        
        tools = response["result"]["tools"]
        assert len(tools) > 0
        
        # Check that every tool has annotations
        for tool in tools:
            assert "annotations" in tool, f"Tool '{tool['name']}' missing annotations"
            assert isinstance(tool["annotations"], list), f"Tool '{tool['name']}' annotations should be a list"
            assert len(tool["annotations"]) > 0, f"Tool '{tool['name']}' should have at least one annotation"

    @pytest.mark.asyncio
    async def test_search_tool_annotations(self, mcp_handler):
        """Test search tool has correct annotations."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        tools = response["result"]["tools"]
        
        search_tool = next((tool for tool in tools if tool["name"] == "search"), None)
        assert search_tool is not None, "Search tool not found"
        assert "read-only" in search_tool["annotations"]

    @pytest.mark.asyncio
    async def test_compute_intensive_tool_annotations(self, mcp_handler):
        """Test compute-intensive tools have correct annotations."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        tools = response["result"]["tools"]
        
        # Tools that should be marked as compute-intensive
        compute_intensive_tools = [
            "analyze_document_relationships",
            "detect_document_conflicts", 
            "cluster_documents"
        ]
        
        for tool_name in compute_intensive_tools:
            tool = next((tool for tool in tools if tool["name"] == tool_name), None)
            assert tool is not None, f"Tool '{tool_name}' not found"
            assert "read-only" in tool["annotations"], f"Tool '{tool_name}' should be read-only"
            assert "compute-intensive" in tool["annotations"], f"Tool '{tool_name}' should be compute-intensive"

    @pytest.mark.asyncio
    async def test_all_tools_are_read_only(self, mcp_handler):
        """Test that all tools are marked as read-only (safety requirement)."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        tools = response["result"]["tools"]
        
        for tool in tools:
            assert "read-only" in tool["annotations"], f"Tool '{tool['name']}' should be read-only"


class TestToolOutputSchemas:
    """Test tool output schema compliance."""

    @pytest.mark.asyncio
    async def test_all_tools_have_output_schemas(self, mcp_handler):
        """Test that all tools have outputSchema defined."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        tools = response["result"]["tools"]
        
        # All tools should have outputSchema for 2025-06-18 compliance
        for tool in tools:
            assert "outputSchema" in tool, f"Tool '{tool['name']}' missing outputSchema"
            assert isinstance(tool["outputSchema"], dict), f"Tool '{tool['name']}' outputSchema should be a dict"
            assert "type" in tool["outputSchema"], f"Tool '{tool['name']}' outputSchema should have 'type'"
            assert tool["outputSchema"]["type"] == "object", f"Tool '{tool['name']}' outputSchema should be object type"

    @pytest.mark.asyncio
    async def test_search_tool_output_schema(self, mcp_handler):
        """Test search tool has correct output schema structure."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        tools = response["result"]["tools"]
        
        search_tool = next((tool for tool in tools if tool["name"] == "search"), None)
        assert search_tool is not None
        
        schema = search_tool["outputSchema"]
        assert "properties" in schema
        
        # Check for expected properties in search output schema
        properties = schema["properties"]
        assert "results" in properties
        assert "total_found" in properties
        assert "query_context" in properties
        
        # Check results array structure
        results_schema = properties["results"]
        assert results_schema["type"] == "array"
        assert "items" in results_schema
        
        # Check result item structure
        item_schema = results_schema["items"]
        assert item_schema["type"] == "object"
        item_properties = item_schema["properties"]
        assert "score" in item_properties
        assert "title" in item_properties
        assert "content" in item_properties
        assert "source_type" in item_properties
        assert "metadata" in item_properties

    @pytest.mark.asyncio
    async def test_analysis_tool_output_schemas(self, mcp_handler):
        """Test analysis tools have appropriate output schemas."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        tools = response["result"]["tools"]
        
        # Test analyze_document_relationships schema
        analyze_tool = next((tool for tool in tools if tool["name"] == "analyze_document_relationships"), None)
        assert analyze_tool is not None
        
        schema = analyze_tool["outputSchema"]
        properties = schema["properties"]
        assert "analysis_results" in properties
        assert "total_documents_analyzed" in properties
        assert "analysis_metadata" in properties
        
        # Check analysis_results structure
        analysis_results = properties["analysis_results"]["properties"]
        assert "similarity_clusters" in analysis_results
        assert "conflicts_detected" in analysis_results
        assert "complementary_pairs" in analysis_results

    @pytest.mark.asyncio  
    async def test_cluster_tool_output_schema(self, mcp_handler):
        """Test cluster tool has appropriate output schema."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        tools = response["result"]["tools"]
        
        cluster_tool = next((tool for tool in tools if tool["name"] == "cluster_documents"), None)
        assert cluster_tool is not None
        
        schema = cluster_tool["outputSchema"]
        properties = schema["properties"]
        assert "clusters" in properties
        assert "clustering_metadata" in properties
        assert "cluster_relationships" in properties
        
        # Check clusters array structure
        clusters_schema = properties["clusters"]
        assert clusters_schema["type"] == "array"
        
        cluster_item = clusters_schema["items"]["properties"]
        assert "cluster_id" in cluster_item
        assert "cluster_name" in cluster_item
        assert "documents" in cluster_item
        assert "cohesion_score" in cluster_item


class TestToolCapabilities:
    """Test tool capabilities and metadata."""

    @pytest.mark.asyncio
    async def test_server_capabilities_declaration(self, mcp_handler):
        """Test server declares proper capabilities."""
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        
        assert "capabilities" in response["result"]
        capabilities = response["result"]["capabilities"]
        assert "tools" in capabilities
        assert "listChanged" in capabilities["tools"]

    @pytest.mark.asyncio
    async def test_tool_count_consistency(self, mcp_handler):
        """Test that the number of tools is consistent across different list methods."""
        # Test tools/list
        tools_list_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1,
        }
        
        tools_response = await mcp_handler.handle_request(tools_list_request)
        tools_count = len(tools_response["result"]["tools"])
        
        # Should have exactly 8 tools (3 search + 5 analysis)
        expected_tools = [
            "search",
            "hierarchy_search", 
            "attachment_search",
            "analyze_document_relationships",
            "find_similar_documents",
            "detect_document_conflicts",
            "find_complementary_content",
            "cluster_documents"
        ]
        
        assert tools_count == len(expected_tools)
        
        # Check all expected tools are present
        tool_names = [tool["name"] for tool in tools_response["result"]["tools"]]
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Expected tool '{expected_tool}' not found"


class TestProtocolCompliance:
    """Test overall protocol compliance for 2025-06-18."""

    @pytest.mark.asyncio
    async def test_jsonrpc_2_0_compliance(self, mcp_handler):
        """Test JSON-RPC 2.0 compliance."""
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
            "id": "test-id-123",
        }
        
        response = await mcp_handler.handle_request(request)
        
        # JSON-RPC 2.0 compliance checks
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test-id-123"  # ID should be preserved
        assert "result" in response or "error" in response  # Must have result or error

    @pytest.mark.asyncio
    async def test_method_not_found_handling(self, mcp_handler):
        """Test proper handling of unknown methods."""
        request = {
            "jsonrpc": "2.0",
            "method": "nonexistent/method",
            "params": {},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "error" in response
        assert response["error"]["code"] == -32601  # Method not found

    @pytest.mark.asyncio
    async def test_invalid_params_handling(self, mcp_handler):
        """Test proper handling of invalid parameters."""
        request = {
            "jsonrpc": "2.0", 
            "method": "search",
            "params": {},  # Missing required 'query' parameter
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "error" in response
        assert response["error"]["code"] == -32602  # Invalid params

    @pytest.mark.asyncio
    async def test_notification_handling(self, mcp_handler):
        """Test handling of notifications (requests without id)."""
        notification = {
            "jsonrpc": "2.0",
            "method": "some/notification",
            "params": {}
            # No id = notification
        }
        
        response = await mcp_handler.handle_request(notification)
        
        # Notifications should not return a response
        assert response is None or (isinstance(response, dict) and "id" not in response) 