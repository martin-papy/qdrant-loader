"""Integration tests for dual transport support (stdio and HTTP)."""

import asyncio
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient

import pytest
from qdrant_loader_mcp_server.mcp import MCPHandler
from qdrant_loader_mcp_server.transport import HTTPTransportHandler
from qdrant_loader_mcp_server.search.models import SearchResult


@pytest.fixture
def mock_search_engine():
    """Create mock search engine with realistic data."""
    engine = Mock()
    engine.search = AsyncMock()
    
    # Sample search results
    sample_results = [
        SearchResult(
            score=0.92,
            text="Authentication is handled through OAuth 2.0 tokens.",
            source_title="Authentication Guide",
            source_type="confluence",
            file_path="/docs/auth.md",
            project_id="proj-auth",
            created_at="2024-01-01T00:00:00Z",
            last_modified="2024-01-15T00:00:00Z"
        ),
        SearchResult(
            score=0.87,
            text="Security best practices for API development.",
            source_title="Security Guidelines",
            source_type="documentation",
            file_path="/docs/security.md",
            project_id="proj-security",
            created_at="2024-01-10T00:00:00Z",
            last_modified="2024-01-20T00:00:00Z"
        )
    ]
    engine.search.return_value = sample_results
    return engine


@pytest.fixture
def mock_query_processor():
    """Create mock query processor."""
    processor = Mock()
    processor.process_query = AsyncMock()
    processor.process_query.return_value = {"query": "processed authentication query"}
    return processor


@pytest.fixture
def mcp_handler(mock_search_engine, mock_query_processor):
    """Create MCP handler for integration testing."""
    return MCPHandler(mock_search_engine, mock_query_processor)


@pytest.fixture
def http_transport(mcp_handler):
    """Create HTTP transport for testing."""
    return HTTPTransportHandler(mcp_handler, host="127.0.0.1", port=8888)


@pytest.fixture
def test_client(http_transport):
    """Create FastAPI test client."""
    return TestClient(http_transport.app)


class TestDualTransportInitialization:
    """Test initialization and setup of both transports."""

    @pytest.mark.asyncio
    async def test_stdio_transport_initialization(self, mcp_handler):
        """Test that stdio transport (direct handler) works correctly."""
        # Test initialize
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(init_request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["result"]["protocolVersion"] == "2025-06-18"

    def test_http_transport_initialization(self, http_transport):
        """Test that HTTP transport initializes correctly."""
        assert http_transport.mcp_handler is not None
        assert http_transport.host == "127.0.0.1"
        assert http_transport.port == 8888
        assert http_transport.app is not None
        assert isinstance(http_transport.sessions, dict)

    def test_both_transports_use_same_handler(self, mcp_handler):
        """Test that both transports can use the same MCP handler."""
        # Create HTTP transport with same handler
        http_transport = HTTPTransportHandler(mcp_handler)
        
        # Both should reference the same handler
        assert http_transport.mcp_handler is mcp_handler


class TestProtocolComplianceAcrossTransports:
    """Test MCP 2025-06-18 protocol compliance across both transports."""

    @pytest.mark.asyncio
    async def test_protocol_version_consistency_stdio(self, mcp_handler):
        """Test protocol version consistency in stdio transport."""
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        assert response["result"]["protocolVersion"] == "2025-06-18"

    def test_protocol_version_consistency_http(self, test_client):
        """Test protocol version consistency in HTTP transport."""
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
            "id": 1,
        }
        
        response = test_client.post(
            "/mcp",
            json=mcp_request,
            headers={
                "Origin": "http://localhost",
                "MCP-Protocol-Version": "2025-06-18"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["result"]["protocolVersion"] == "2025-06-18"

    @pytest.mark.asyncio
    async def test_tool_definitions_identical_across_transports(self, mcp_handler, test_client):
        """Test that tool definitions are identical across both transports."""
        # Get tools via stdio
        stdio_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1,
        }
        
        stdio_response = await mcp_handler.handle_request(stdio_request)
        stdio_tools = stdio_response["result"]["tools"]
        
        # Get tools via HTTP
        http_response = test_client.post(
            "/mcp",
            json=stdio_request,
            headers={"Origin": "http://localhost"}
        )
        
        http_tools = http_response.json()["result"]["tools"]
        
        # Should be identical
        assert len(stdio_tools) == len(http_tools)
        
        # Compare each tool
        for i in range(len(stdio_tools)):
            stdio_tool = stdio_tools[i]
            http_tool = http_tools[i]
            
            assert stdio_tool["name"] == http_tool["name"]
            assert stdio_tool["description"] == http_tool["description"]
            assert stdio_tool["annotations"] == http_tool["annotations"]
            assert "outputSchema" in stdio_tool
            assert "outputSchema" in http_tool


class TestStructuredOutputAcrossTransports:
    """Test structured output functionality across both transports."""

    @pytest.mark.asyncio
    async def test_search_structured_output_stdio(self, mcp_handler, mock_query_processor, mock_search_engine):
        """Test structured output via stdio transport."""
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "authentication", "limit": 5},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        
        assert "result" in response
        assert "content" in response["result"]
        assert "structuredContent" in response["result"]
        
        # Check structured content format
        structured = response["result"]["structuredContent"]
        assert "results" in structured
        assert "total_found" in structured
        assert "query_context" in structured
        
        # Verify data types
        assert isinstance(structured["results"], list)
        assert isinstance(structured["total_found"], int)
        assert isinstance(structured["query_context"], dict)

    def test_search_structured_output_http(self, test_client, mock_query_processor, mock_search_engine):
        """Test structured output via HTTP transport."""
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "authentication", "limit": 5},
            "id": 1,
        }
        
        response = test_client.post(
            "/mcp",
            json=mcp_request,
            headers={"Origin": "http://localhost"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "result" in data
        assert "content" in data["result"]
        assert "structuredContent" in data["result"]
        
        # Check structured content format
        structured = data["result"]["structuredContent"]
        assert "results" in structured
        assert "total_found" in structured
        assert "query_context" in structured

    @pytest.mark.asyncio
    async def test_structured_output_consistency(self, mcp_handler, test_client, mock_search_engine, mock_query_processor):
        """Test that structured output is consistent between transports."""
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "test", "limit": 3},
            "id": 1,
        }
        
        # Get response via stdio
        stdio_response = await mcp_handler.handle_request(request)
        stdio_structured = stdio_response["result"]["structuredContent"]
        
        # Get response via HTTP
        http_response = test_client.post(
            "/mcp",
            json=request,
            headers={"Origin": "http://localhost"}
        )
        http_structured = http_response.json()["result"]["structuredContent"]
        
        # Should be identical
        assert stdio_structured["total_found"] == http_structured["total_found"]
        assert len(stdio_structured["results"]) == len(http_structured["results"])
        
        # Compare individual results
        for i in range(len(stdio_structured["results"])):
            stdio_result = stdio_structured["results"][i]
            http_result = http_structured["results"][i]
            
            assert stdio_result["score"] == http_result["score"]
            assert stdio_result["title"] == http_result["title"]
            assert stdio_result["content"] == http_result["content"]


class TestErrorHandlingAcrossTransports:
    """Test error handling consistency across both transports."""

    @pytest.mark.asyncio
    async def test_invalid_request_stdio(self, mcp_handler):
        """Test invalid request handling via stdio."""
        invalid_request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {},  # Missing required query parameter
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(invalid_request)
        
        assert "error" in response
        assert response["error"]["code"] == -32602  # Invalid params
        assert response["id"] == 1

    def test_invalid_request_http(self, test_client):
        """Test invalid request handling via HTTP."""
        invalid_request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {},  # Missing required query parameter
            "id": 1,
        }
        
        response = test_client.post(
            "/mcp",
            json=invalid_request,
            headers={"Origin": "http://localhost"}
        )
        
        assert response.status_code == 200  # HTTP OK, but MCP error
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32602  # Invalid params

    @pytest.mark.asyncio
    async def test_error_format_consistency(self, mcp_handler, test_client):
        """Test that error formats are consistent across transports."""
        invalid_request = {
            "jsonrpc": "2.0",
            "method": "nonexistent/method",
            "params": {},
            "id": 1,
        }
        
        # Get error via stdio
        stdio_response = await mcp_handler.handle_request(invalid_request)
        
        # Get error via HTTP
        http_response = test_client.post(
            "/mcp",
            json=invalid_request,
            headers={"Origin": "http://localhost"}
        )
        http_data = http_response.json()
        
        # Error structure should be identical
        assert stdio_response["error"]["code"] == http_data["error"]["code"]
        assert stdio_response["error"]["message"] == http_data["error"]["message"]


class TestHTTPSpecificFeatures:
    """Test HTTP-specific features that don't apply to stdio."""

    def test_http_health_endpoint(self, test_client):
        """Test HTTP health endpoint."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["transport"] == "http"
        assert data["protocol"] == "mcp"

    def test_http_cors_headers(self, test_client):
        """Test CORS headers for HTTP transport."""
        response = test_client.options(
            "/mcp",
            headers={"Origin": "http://localhost"}
        )
        
        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers

    def test_http_origin_validation(self, test_client):
        """Test origin validation for HTTP transport."""
        # Valid origin should work
        valid_response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18"},
                "id": 1,
            },
            headers={"Origin": "http://localhost"}
        )
        assert valid_response.status_code == 200
        
        # Invalid origin should be rejected
        invalid_response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0", 
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18"},
                "id": 1,
            },
            headers={"Origin": "http://malicious.site"}
        )
        assert invalid_response.status_code == 403

    def test_http_sse_stream_setup(self, http_transport):
        """Test SSE stream setup for HTTP transport."""
        # Test the SSE endpoint setup without consuming the infinite stream
        # We'll test the route exists and returns proper SSE headers
        from fastapi.testclient import TestClient
        
        client = TestClient(http_transport.app)
        
        # Make a HEAD request to check headers without consuming stream
        response = client.request(
            "HEAD",
            "/mcp",
            headers={
                "MCP-Session-Id": "test-session",
                "Accept": "text/event-stream"
            }
        )
        
        # The GET endpoint should exist (HEAD request to GET endpoint)
        # Status might be 405 for HEAD on GET-only endpoint, which is fine
        assert response.status_code in [200, 405]
        
        # Alternatively, test that the route exists by checking app routes
        routes = [route.path for route in http_transport.app.routes if hasattr(route, 'path')]
        assert "/mcp" in routes


class TestTransportSpecificPerformance:
    """Test performance characteristics of different transports."""

    @pytest.mark.asyncio
    async def test_stdio_direct_call_performance(self, mcp_handler, mock_search_engine, mock_query_processor):
        """Test stdio transport (direct calls) performance."""
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "performance test"},
            "id": 1,
        }
        
        # Multiple calls should work efficiently
        for i in range(5):
            response = await mcp_handler.handle_request(request)
            assert "result" in response
            assert "structuredContent" in response["result"]

    def test_http_transport_multiple_requests(self, test_client, mock_search_engine, mock_query_processor):
        """Test HTTP transport handling multiple requests."""
        request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "performance test"},
            "id": 1,
        }
        
        # Multiple HTTP requests should work efficiently
        for i in range(5):
            response = test_client.post(
                "/mcp",
                json=request,
                headers={"Origin": "http://localhost"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "result" in data
            assert "structuredContent" in data["result"]


class TestSessionManagementIntegration:
    """Test session management in HTTP transport."""

    def test_session_id_generation(self, test_client):
        """Test automatic session ID generation."""
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
            "id": 1,
        }
        
        # Request without session ID should work
        response = test_client.post(
            "/mcp",
            json=request,
            headers={"Origin": "http://localhost"}
        )
        
        assert response.status_code == 200

    def test_explicit_session_id_handling(self, test_client):
        """Test handling of explicit session IDs."""
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
            "id": 1,
        }
        
        # Request with explicit session ID should work
        response = test_client.post(
            "/mcp",
            json=request,
            headers={
                "Origin": "http://localhost",
                "MCP-Session-Id": "explicit-session-123"
            }
        )
        
        assert response.status_code == 200


class TestProtocolVersionNegotiation:
    """Test protocol version negotiation across transports."""

    @pytest.mark.asyncio
    async def test_version_negotiation_stdio(self, mcp_handler):
        """Test protocol version negotiation via stdio."""
        # Client requests older version
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
            "id": 1,
        }
        
        response = await mcp_handler.handle_request(request)
        
        # Server should respond with its version
        assert response["result"]["protocolVersion"] == "2025-06-18"

    def test_version_negotiation_http(self, test_client):
        """Test protocol version negotiation via HTTP."""
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
            "id": 1,
        }
        
        response = test_client.post(
            "/mcp",
            json=request,
            headers={
                "Origin": "http://localhost",
                "MCP-Protocol-Version": "2024-11-05"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Server should respond with its version
        assert data["result"]["protocolVersion"] == "2025-06-18"


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows across both transports."""

    @pytest.mark.asyncio
    async def test_complete_stdio_workflow(self, mcp_handler, mock_search_engine, mock_query_processor):
        """Test complete workflow: initialize -> list tools -> search."""
        # Initialize
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
            "id": 1,
        }
        
        init_response = await mcp_handler.handle_request(init_request)
        assert init_response["result"]["protocolVersion"] == "2025-06-18"
        
        # List tools
        tools_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2,
        }
        
        tools_response = await mcp_handler.handle_request(tools_request)
        assert len(tools_response["result"]["tools"]) > 0
        
        # Search
        search_request = {
            "jsonrpc": "2.0",
            "method": "search",
            "params": {"query": "authentication"},
            "id": 3,
        }
        
        search_response = await mcp_handler.handle_request(search_request)
        assert "structuredContent" in search_response["result"]

    def test_complete_http_workflow(self, test_client, mock_search_engine, mock_query_processor):
        """Test complete workflow via HTTP: initialize -> list tools -> search."""
        headers = {"Origin": "http://localhost"}
        
        # Initialize
        init_response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18"},
                "id": 1,
            },
            headers=headers
        )
        assert init_response.status_code == 200
        assert init_response.json()["result"]["protocolVersion"] == "2025-06-18"
        
        # List tools
        tools_response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 2,
            },
            headers=headers
        )
        assert tools_response.status_code == 200
        assert len(tools_response.json()["result"]["tools"]) > 0
        
        # Search
        search_response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "search",
                "params": {"query": "authentication"},
                "id": 3,
            },
            headers=headers
        )
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert "structuredContent" in search_data["result"] 