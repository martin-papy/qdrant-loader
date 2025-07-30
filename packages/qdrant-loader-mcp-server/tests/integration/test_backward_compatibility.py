"""Integration tests for backward compatibility with MCP 2024-11-05 clients."""

from unittest.mock import Mock, AsyncMock
import pytest
from qdrant_loader_mcp_server.mcp import MCPHandler
from qdrant_loader_mcp_server.transport import HTTPTransportHandler
from qdrant_loader_mcp_server.search.models import SearchResult


@pytest.fixture
def mock_search_engine():
    """Create mock search engine with sample data."""
    engine = Mock()
    engine.search = AsyncMock()
    
    # Default sample results
    sample_results = [
        SearchResult(
            score=0.9,
            text="Sample document about testing",
            source_title="Test Document",
            source_type="documentation"
        )
    ]
    engine.search.return_value = sample_results
    return engine


@pytest.fixture  
def mock_query_processor():
    """Create mock query processor."""
    processor = Mock()
    processor.process_query = AsyncMock()
    processor.process_query.return_value = {"query": "processed query"}
    return processor


@pytest.fixture
def mcp_handler(mock_search_engine, mock_query_processor):
    """Create MCP handler for testing."""
    return MCPHandler(mock_search_engine, mock_query_processor)


class TestProtocolVersionBackwardCompatibility:
    """Test backward compatibility for protocol versions."""

    @pytest.mark.asyncio
    async def test_2024_11_05_client_initialize(self, mcp_handler):
        """Test that 2024-11-05 clients can still initialize."""
        # Simulate old client initialization
        old_client_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",  # Old version
                "capabilities": {"tools": {"listChanged": False}},
            },
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(old_client_request)
        
        # Should succeed
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        
        # Server should return its current version (2025-06-18)
        assert response["result"]["protocolVersion"] == "2025-06-18"
        
        # Should have proper server info
        assert response["result"]["serverInfo"]["name"] == "Qdrant Loader MCP Server"

    @pytest.mark.asyncio
    async def test_no_protocol_version_header_compatibility(self, mcp_handler):
        """Test compatibility when no protocol version header is provided."""
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
            "id": 1,
        }
        
        # No headers provided (old client behavior)
        response = await mcp_handler.handle_request(request)
        
        # Should work without issues
        assert response["result"]["protocolVersion"] == "2025-06-18"

    @pytest.mark.asyncio
    async def test_mixed_version_headers(self, mcp_handler):
        """Test handling when client sends different version in params vs headers."""
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
            "id": 1,
        }
        
        # Client sends newer version in header but old in params
        headers = {"mcp-protocol-version": "2025-06-18"}
        response = await mcp_handler.handle_request(request, headers=headers)
        
        # Should handle gracefully
        assert response["result"]["protocolVersion"] == "2025-06-18"


class TestOldClientToolUsage:
    """Test that old clients can still use tools without new features."""

    @pytest.mark.asyncio
    async def test_old_client_tools_list(self, mcp_handler):
        """Test that tools/list works for old clients."""
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
        
        # Old clients get tool definitions with new features
        # but should still be able to process them
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            
            # New features present but shouldn't break old clients
            assert "annotations" in tool
            assert "outputSchema" in tool

    @pytest.mark.asyncio
    async def test_old_client_search_functionality(self, mcp_handler, mock_query_processor, mock_search_engine):
        """Test that search functionality works for old clients."""
        # Setup mocks
        mock_search_engine.search.return_value = [
            SearchResult(
                score=0.8,
                text="Test result content",
                source_title="Test Title",
                source_type="confluence"
            )
        ]
        
        # Old client search request (no new parameters)
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "test query"},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        
        assert "result" in response
        assert "content" in response["result"]
        
        # Old clients expect content array with text
        content = response["result"]["content"]
        assert isinstance(content, list)
        assert len(content) > 0
        assert content[0]["type"] == "text"
        assert "text" in content[0]
        
        # New structured content is also present but old clients can ignore it
        assert "structuredContent" in response["result"]

    @pytest.mark.asyncio
    async def test_old_client_ignores_new_response_fields(self, mcp_handler, mock_query_processor, mock_search_engine):
        """Test that old clients can ignore new response fields without breaking."""
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "test"},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        
        # Response should be valid JSON-RPC
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        
        # Should have traditional fields that old clients expect
        result = response["result"]
        assert "content" in result
        assert "isError" in result
        
        # New fields present but don't break JSON structure
        assert "structuredContent" in result
        
        # Old clients would just ignore structuredContent field


class TestResponseFormatCompatibility:
    """Test response format compatibility between versions."""

    @pytest.mark.asyncio
    async def test_json_rpc_structure_preserved(self, mcp_handler):
        """Test that JSON-RPC 2.0 structure is preserved for old clients."""
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
            "id": "test-string-id",
        }
        
        response = await mcp_handler.handle_request(request)
        
        # Standard JSON-RPC 2.0 format
        assert "jsonrpc" in response
        assert "id" in response
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test-string-id"
        assert "result" in response or "error" in response

    @pytest.mark.asyncio
    async def test_error_format_compatibility(self, mcp_handler):
        """Test that error responses are compatible with old clients."""
        # Invalid request that should generate error
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {},  # Missing required query parameter
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        
        # Should be valid JSON-RPC error response
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "error" in response
        
        error = response["error"]
        assert "code" in error
        assert "message" in error
        assert isinstance(error["code"], int)
        assert isinstance(error["message"], str)

    @pytest.mark.asyncio
    async def test_content_array_format_preserved(self, mcp_handler, mock_search_engine, mock_query_processor):
        """Test that content array format is preserved for compatibility."""
        # Setup mock
        mock_search_engine.search.return_value = [
            SearchResult(score=0.9, text="Test content", source_title="Test", source_type="doc")
        ]
        
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "test"},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        
        # Content should be in the expected array format
        content = response["result"]["content"]
        assert isinstance(content, list)
        assert len(content) == 1
        
        content_item = content[0]
        assert content_item["type"] == "text"
        assert "text" in content_item
        assert isinstance(content_item["text"], str)


class TestDualTransportCompatibility:
    """Test compatibility across both stdio and HTTP transports."""

    @pytest.mark.asyncio
    async def test_stdio_transport_still_works(self, mcp_handler):
        """Test that stdio transport (traditional) still works."""
        # This is the traditional way MCP clients work
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
            "id": 1,
        }
        
        # Direct handler call (simulates stdio)
        response = await mcp_handler.handle_request(request)
        
        assert response["result"]["protocolVersion"] == "2025-06-18"

    def test_http_transport_initialization_compatible(self, mcp_handler):
        """Test that HTTP transport can be initialized with old MCP handler."""
        # Should be able to create HTTP transport with existing handler
        http_transport = HTTPTransportHandler(mcp_handler)
        
        assert http_transport.mcp_handler == mcp_handler
        assert http_transport.app is not None
        
        # Should have backward-compatible validation
        assert http_transport._validate_protocol_version("2024-11-05") is True
        assert http_transport._validate_protocol_version("2025-06-18") is True
        assert http_transport._validate_protocol_version(None) is True

    @pytest.mark.asyncio
    async def test_http_post_with_old_client_request(self, mcp_handler):
        """Test HTTP POST endpoint with request from old client."""
        http_transport = HTTPTransportHandler(mcp_handler)
        
        # Mock request object
        class MockRequest:
            def __init__(self, json_data, headers):
                self._json_data = json_data
                self._headers = headers
            
            async def json(self):
                return self._json_data
            
            @property
            def headers(self):
                return MockHeaders(self._headers)
        
        class MockHeaders:
            def __init__(self, headers_dict):
                self._headers = headers_dict
            
            def get(self, key, default=None):
                return self._headers.get(key.lower(), default)
            
            def __getitem__(self, key):
                return self._headers[key.lower()]
            
            def __setitem__(self, key, value):
                self._headers[key.lower()] = value
            
            def __iter__(self):
                return iter(self._headers)
            
            def items(self):
                return self._headers.items()
            
            def keys(self):
                return self._headers.keys()
            
            def values(self):
                return self._headers.values()
        
        # Old client request (no special headers)
        request = MockRequest(
            {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
                "id": 1,
            },
            {"origin": "http://localhost"}  # Only basic origin header
        )
        
        response = await http_transport._handle_post_request(request)
        
        # Should work without protocol version header
        assert response["result"]["protocolVersion"] == "2025-06-18"


class TestToolAnnotationsBackwardCompatibility:
    """Test that tool annotations don't break old clients."""

    @pytest.mark.asyncio
    async def test_old_clients_ignore_annotations(self, mcp_handler):
        """Test that old clients can ignore tool annotations."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        tools = response["result"]["tools"]
        
        # All tools should have annotations, but old clients can ignore them
        for tool in tools:
            assert "annotations" in tool
            
            # The presence of annotations shouldn't break the tool definition
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            
            # Annotations should be a dictionary for 2025-06-18 protocol
            # Old clients that don't understand annotations can simply ignore this field
            assert isinstance(tool["annotations"], dict)
            
            # Verify the annotation contains expected properties
            assert "read-only" in tool["annotations"]
            assert isinstance(tool["annotations"]["read-only"], bool)

    @pytest.mark.asyncio
    async def test_output_schemas_dont_break_old_clients(self, mcp_handler):
        """Test that output schemas don't break old clients."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list", 
            "params": {},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        tools = response["result"]["tools"]
        
        # All tools should have output schemas
        for tool in tools:
            assert "outputSchema" in tool
            
            # But tool should still be usable by old clients
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            
            # Output schema should be valid JSON object that old clients can ignore
            assert isinstance(tool["outputSchema"], dict)


class TestGradualMigrationSupport:
    """Test support for gradual migration from old to new protocol."""

    @pytest.mark.asyncio
    async def test_client_can_check_server_version(self, mcp_handler):
        """Test that clients can check server version to determine capabilities."""
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        
        # Client can check server version to know what features are available
        server_version = response["result"]["protocolVersion"]
        assert server_version == "2025-06-18"
        
        # Client can decide whether to use new features based on server version
        if server_version >= "2025-06-18":
            # Client knows structured output is available
            pass
        else:
            # Client falls back to text-only mode
            pass

    @pytest.mark.asyncio
    async def test_feature_detection_through_tool_definitions(self, mcp_handler):
        """Test that clients can detect new features through tool definitions."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        tools = response["result"]["tools"]
        
        # Smart clients can detect new features
        for tool in tools:
            # Presence of outputSchema indicates structured output support
            has_structured_output = "outputSchema" in tool
            
            # Presence of annotations indicates behavioral annotation support
            has_annotations = "annotations" in tool
            
            assert has_structured_output is True
            assert has_annotations is True
            
            # Client can conditionally use features based on detection 