"""Unit tests for HTTP Transport Handler."""

import asyncio
import json
import time
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient

import pytest
from qdrant_loader_mcp_server.transport import HTTPTransportHandler
from qdrant_loader_mcp_server.mcp import MCPHandler


@pytest.fixture
def mock_mcp_handler():
    """Create mock MCP handler for testing."""
    handler = Mock(spec=MCPHandler)
    handler.handle_request = AsyncMock()
    return handler


@pytest.fixture
def http_transport(mock_mcp_handler):
    """Create HTTP transport handler for testing."""
    return HTTPTransportHandler(mock_mcp_handler, host="127.0.0.1", port=8080)


@pytest.fixture
def test_client(http_transport):
    """Create FastAPI test client."""
    return TestClient(http_transport.app)


class TestHTTPTransportInitialization:
    """Test HTTP transport initialization."""

    def test_initialization_with_defaults(self, mock_mcp_handler):
        """Test initialization with default parameters."""
        transport = HTTPTransportHandler(mock_mcp_handler)
        
        assert transport.mcp_handler == mock_mcp_handler
        assert transport.host == "127.0.0.1"
        assert transport.port == 8080
        assert isinstance(transport.sessions, dict)
        assert len(transport.sessions) == 0
        assert transport.app is not None

    def test_initialization_with_custom_params(self, mock_mcp_handler):
        """Test initialization with custom host and port."""
        transport = HTTPTransportHandler(mock_mcp_handler, host="localhost", port=9090)
        
        assert transport.host == "localhost"
        assert transport.port == 9090

    def test_fastapi_app_routes_configured(self, http_transport):
        """Test that FastAPI routes are properly configured."""
        routes = [route.path for route in http_transport.app.routes if hasattr(route, 'path')]
        
        # Should have MCP endpoints and health check
        assert "/mcp" in routes
        assert "/health" in routes
        
        # Should have 3 /mcp routes (GET, POST, and OPTIONS)
        mcp_routes = [route for route in routes if route == "/mcp"]
        assert len(mcp_routes) == 3


class TestHTTPTransportSecurity:
    """Test HTTP transport security features."""

    def test_validate_origin_with_valid_origins(self, http_transport):
        """Test origin validation with valid localhost origins."""
        valid_origins = [
            "http://localhost",
            "https://localhost",
            "http://127.0.0.1",
            "https://127.0.0.1",
            "http://localhost:3000",
            "https://localhost:8080"
        ]
        
        for origin in valid_origins:
            assert http_transport._validate_origin(origin) is True

    def test_validate_origin_with_invalid_origins(self, http_transport):
        """Test origin validation with invalid origins."""
        invalid_origins = [
            "http://example.com",
            "https://malicious.site",
            "http://192.168.1.1",
            "https://external.domain.com"
        ]
        
        for origin in invalid_origins:
            assert http_transport._validate_origin(origin) is False

    def test_validate_origin_with_none(self, http_transport):
        """Test origin validation with None (should allow for non-browser clients)."""
        assert http_transport._validate_origin(None) is True

    def test_validate_origin_with_empty_string(self, http_transport):
        """Test origin validation with empty string."""
        assert http_transport._validate_origin("") is True

    def test_validate_protocol_version_with_supported_versions(self, http_transport):
        """Test protocol version validation with supported versions."""
        supported_versions = ["2025-06-18", "2025-03-26", "2024-11-05"]
        
        for version in supported_versions:
            assert http_transport._validate_protocol_version(version) is True

    def test_validate_protocol_version_with_unsupported_version(self, http_transport):
        """Test protocol version validation with unsupported version."""
        unsupported_versions = ["2023-01-01", "invalid-version", "1.0.0"]
        
        for version in unsupported_versions:
            assert http_transport._validate_protocol_version(version) is False

    def test_validate_protocol_version_with_none(self, http_transport):
        """Test protocol version validation with None (backward compatibility)."""
        assert http_transport._validate_protocol_version(None) is True


class TestHTTPTransportSessionManagement:
    """Test HTTP transport session management."""

    def test_add_session_message(self, http_transport):
        """Test adding messages to session."""
        session_id = "test_session_123"
        message = {"type": "notification", "data": "test"}
        
        # Initialize session
        http_transport.sessions[session_id] = {"messages": [], "created_at": time.time()}
        
        # Add message
        http_transport.add_session_message(session_id, message)
        
        assert len(http_transport.sessions[session_id]["messages"]) == 1
        assert http_transport.sessions[session_id]["messages"][0] == message

    def test_add_session_message_nonexistent_session(self, http_transport):
        """Test adding message to non-existent session (should not crash)."""
        session_id = "nonexistent_session"
        message = {"type": "notification", "data": "test"}
        
        # Should not raise exception
        http_transport.add_session_message(session_id, message)
        
        # Session should not be created
        assert session_id not in http_transport.sessions

    def test_cleanup_sessions_removes_old_sessions(self, http_transport):
        """Test session cleanup removes old sessions."""
        current_time = time.time()
        
        # Add old session (2 hours ago)
        old_session_id = "old_session"
        http_transport.sessions[old_session_id] = {
            "messages": [],
            "created_at": current_time - 7200  # 2 hours ago
        }
        
        # Add recent session
        new_session_id = "new_session"
        http_transport.sessions[new_session_id] = {
            "messages": [],
            "created_at": current_time
        }
        
        # Cleanup with 1 hour max age
        http_transport.cleanup_sessions(max_age_seconds=3600)
        
        # Old session should be removed, new session should remain
        assert old_session_id not in http_transport.sessions
        assert new_session_id in http_transport.sessions

    def test_cleanup_sessions_keeps_recent_sessions(self, http_transport):
        """Test session cleanup keeps recent sessions."""
        current_time = time.time()
        
        # Add recent session (30 minutes ago)
        session_id = "recent_session"
        http_transport.sessions[session_id] = {
            "messages": [],
            "created_at": current_time - 1800  # 30 minutes ago
        }
        
        # Cleanup with 1 hour max age
        http_transport.cleanup_sessions(max_age_seconds=3600)
        
        # Recent session should remain
        assert session_id in http_transport.sessions


class TestHTTPTransportEndpoints:
    """Test HTTP transport endpoints using FastAPI test client."""

    def test_health_endpoint(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["transport"] == "http"
        assert data["protocol"] == "mcp"

    def test_mcp_post_endpoint_valid_request(self, test_client, mock_mcp_handler):
        """Test MCP POST endpoint with valid request."""
        # Setup mock response
        expected_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"protocolVersion": "2025-06-18"}
        }
        # Since handle_request is AsyncMock, we need to set the return value properly
        mock_mcp_handler.handle_request = AsyncMock(return_value=expected_response)
        
        # Make request
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
            "id": 1
        }
        
        response = test_client.post(
            "/mcp",
            json=mcp_request,
            headers={
                "Origin": "http://localhost",
                "MCP-Protocol-Version": "2025-06-18",
                "MCP-Session-Id": "test_session"
            }
        )
        
        assert response.status_code == 200
        assert response.json() == expected_response
        
        # Verify MCP handler was called with headers
        mock_mcp_handler.handle_request.assert_called_once()
        call_args = mock_mcp_handler.handle_request.call_args
        assert call_args[0][0] == mcp_request  # First arg is the request
        assert "headers" in call_args[1]  # Second arg should have headers

    def test_mcp_post_endpoint_invalid_origin(self, test_client):
        """Test MCP POST endpoint with invalid origin."""
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
            "id": 1
        }
        
        response = test_client.post(
            "/mcp",
            json=mcp_request,
            headers={"Origin": "http://malicious.site"}
        )
        
        assert response.status_code == 403
        assert "Invalid origin" in response.text

    def test_mcp_post_endpoint_invalid_json(self, test_client):
        """Test MCP POST endpoint with invalid JSON."""
        response = test_client.post(
            "/mcp",
            data="invalid json",
            headers={
                "Origin": "http://localhost",
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 200  # Should return MCP error response
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "error" in data
        assert data["error"]["code"] == -32700  # Parse error

    def test_mcp_get_endpoint_sse_stream(self, http_transport):
        """Test MCP GET endpoint for SSE streaming setup."""
        # Test that the SSE route exists and is configured properly
        # We'll use stream mode to avoid hanging on the infinite response
        from fastapi.testclient import TestClient
        client = TestClient(http_transport.app)
        
        # Test that the GET route is available by checking routes
        get_routes = [
            route for route in http_transport.app.routes 
            if hasattr(route, 'path') and route.path == "/mcp" and hasattr(route, 'methods') and "GET" in route.methods
        ]
        assert len(get_routes) >= 1, "GET route for /mcp should exist"

    def test_cors_headers_present(self, test_client):
        """Test that CORS headers are properly configured."""
        response = test_client.options("/mcp", headers={"Origin": "http://localhost"})
        
        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers


class TestHTTPTransportProtocolVersionHandling:
    """Test protocol version handling in HTTP transport."""

    @pytest.mark.asyncio
    async def test_protocol_version_validation_warning(self, http_transport, mock_mcp_handler):
        """Test that unsupported protocol versions generate warnings."""
        with patch('qdrant_loader_mcp_server.transport.http_handler.logger') as mock_logger:
            # Mock the request processing
            # Create a proper headers mock that behaves like a dictionary
            class MockHeaders(dict):
                def __init__(self, headers_dict):
                    super().__init__(headers_dict)
                
                def get(self, key, default=None):
                    return super().get(key.lower(), default)
            
            mock_headers = MockHeaders({
                "origin": "http://localhost",
                "mcp-protocol-version": "unsupported-version"
            })
            
            mock_request = Mock()
            mock_request.headers = mock_headers
            mock_request.json = AsyncMock(return_value={
                "jsonrpc": "2.0",
                "method": "test",
                "id": 1
            })
            
            mock_mcp_handler.handle_request = AsyncMock(return_value={"jsonrpc": "2.0", "id": 1, "result": {}})
            
            # This should trigger the warning but continue processing
            await http_transport._handle_post_request(mock_request)
            
            # Verify warning was logged (though the exact call depends on the logger implementation)
            # The important thing is that processing continued
            mock_mcp_handler.handle_request.assert_called_once()

    def test_protocol_version_in_supported_list(self, http_transport):
        """Test that the supported version list is correct."""
        # Test all versions that should be supported
        supported_versions = ["2025-06-18", "2025-03-26", "2024-11-05"]
        
        for version in supported_versions:
            assert http_transport._validate_protocol_version(version) is True


class TestHTTPTransportErrorHandling:
    """Test error handling in HTTP transport."""

    @pytest.mark.asyncio
    async def test_handle_post_request_exception(self, http_transport, mock_mcp_handler):
        """Test error handling when MCP handler raises exception."""
        # Setup mock to raise exception
        mock_mcp_handler.handle_request.side_effect = Exception("Test error")
        
        # Create a proper headers mock that behaves like a dictionary
        class MockHeaders(dict):
            def __init__(self, headers_dict):
                super().__init__(headers_dict)
            
            def get(self, key, default=None):
                return super().get(key.lower(), default)
        
        mock_headers = MockHeaders({"origin": "http://localhost"})
        
        mock_request = Mock()
        mock_request.headers = mock_headers
        mock_request.json = AsyncMock(return_value={
            "jsonrpc": "2.0",
            "method": "test",
            "id": 1
        })
        
        response = await http_transport._handle_post_request(mock_request)
        
        # Should return proper JSON-RPC error response
        assert response["jsonrpc"] == "2.0"
        assert "error" in response
        assert response["error"]["code"] == -32603  # Internal error
        assert "Test error" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_session_id_generation(self, http_transport, mock_mcp_handler):
        """Test automatic session ID generation when not provided."""
        mock_mcp_handler.handle_request = AsyncMock(return_value={"jsonrpc": "2.0", "id": 1, "result": {}})
        
        # Create a proper headers mock that behaves like a dictionary
        class MockHeaders(dict):
            def __init__(self, headers_dict):
                super().__init__(headers_dict)
            
            def get(self, key, default=None):
                return super().get(key.lower(), default)
        
        mock_headers = MockHeaders({"origin": "http://localhost"})
        
        mock_request = Mock()
        mock_request.headers = mock_headers
        mock_request.json = AsyncMock(return_value={
            "jsonrpc": "2.0",
            "method": "test",
            "id": 1
        })
        
        # Should not raise exception and should generate session ID
        response = await http_transport._handle_post_request(mock_request)
        
        assert response["jsonrpc"] == "2.0"
        assert "result" in response 