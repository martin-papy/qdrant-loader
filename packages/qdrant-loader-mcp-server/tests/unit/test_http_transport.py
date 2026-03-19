"""Unit tests for HTTP Transport (router-based architecture)."""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from qdrant_loader_mcp_server.mcp import MCPHandler
from qdrant_loader_mcp_server.transport import mcp_router
from qdrant_loader_mcp_server.transport.dependencies import validate_origin


@pytest.fixture
def mock_mcp_handler():
    """Create mock MCP handler for testing."""
    handler = Mock(spec=MCPHandler)
    handler.handle_request = AsyncMock()
    return handler


@pytest.fixture
def app(mock_mcp_handler):
    """Create a FastAPI app wired with the MCP router."""
    app = FastAPI()
    app.state.mcp_handler = mock_mcp_handler
    app.include_router(mcp_router)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:[0-9]+)?",
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "healthy", "transport": "http", "protocol": "mcp"}

    return app


@pytest.fixture
def test_client(app):
    """Create FastAPI test client."""
    return TestClient(app)


class TestAppSetup:
    """Test that the app is configured correctly."""

    def test_routes_exist(self, app):
        """Test that expected routes are registered."""
        routes = [route.path for route in app.routes if hasattr(route, "path")]
        assert "/mcp" in routes
        assert "/health" in routes

    def test_mcp_handler_on_state(self, app, mock_mcp_handler):
        """Test that mcp_handler is set on app.state."""
        assert app.state.mcp_handler is mock_mcp_handler

    def test_get_and_post_mcp_routes(self, app):
        """Test that both GET and POST routes exist for /mcp."""
        mcp_methods = set()
        for route in app.routes:
            if (
                hasattr(route, "path")
                and route.path == "/mcp"
                and hasattr(route, "methods")
            ):
                mcp_methods.update(route.methods)
        assert "GET" in mcp_methods
        assert "POST" in mcp_methods


class TestOriginValidation:
    """Test the validate_origin dependency directly."""

    @pytest.mark.asyncio
    async def test_valid_origins(self):
        """Test that valid localhost origins pass."""
        from unittest.mock import MagicMock

        valid_origins = [
            "http://localhost",
            "https://localhost",
            "http://127.0.0.1",
            "https://127.0.0.1",
            "http://localhost:3000",
            "https://localhost:8080",
        ]
        for origin in valid_origins:
            request = MagicMock()
            request.headers = {"origin": origin}
            # Should not raise
            await validate_origin(request)

    @pytest.mark.asyncio
    async def test_invalid_origins(self):
        """Test that invalid origins are rejected."""
        from unittest.mock import MagicMock

        from fastapi import HTTPException

        invalid_origins = [
            "http://example.com",
            "https://malicious.site",
            "http://192.168.1.1",
            "https://external.domain.com",
        ]
        for origin in invalid_origins:
            request = MagicMock()
            request.headers = {"origin": origin}
            with pytest.raises(HTTPException) as exc_info:
                await validate_origin(request)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_no_origin_allowed(self):
        """Test that requests without an Origin header pass (non-browser clients)."""
        from unittest.mock import MagicMock

        request = MagicMock()
        request.headers = {}
        # Should not raise
        await validate_origin(request)

    @pytest.mark.asyncio
    async def test_empty_origin_allowed(self):
        """Test that an empty Origin header is treated as absent."""
        from unittest.mock import MagicMock

        request = MagicMock()
        request.headers = {"origin": ""}
        # Empty string is falsy, so should pass
        await validate_origin(request)


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
        expected_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"protocolVersion": "2025-06-18"},
        }
        mock_mcp_handler.handle_request = AsyncMock(return_value=expected_response)

        mcp_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
            "id": 1,
        }

        response = test_client.post(
            "/mcp",
            json=mcp_request,
            headers={"Origin": "http://localhost"},
        )

        assert response.status_code == 200
        assert response.json() == expected_response

        mock_mcp_handler.handle_request.assert_called_once()
        call_args = mock_mcp_handler.handle_request.call_args
        assert call_args[0][0] == mcp_request
        assert "headers" in call_args[1]

    def test_mcp_post_endpoint_invalid_origin(self, test_client):
        """Test MCP POST endpoint with invalid origin."""
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
            "id": 1,
        }

        response = test_client.post(
            "/mcp", json=mcp_request, headers={"Origin": "http://malicious.site"}
        )

        assert response.status_code == 403
        assert "Invalid origin" in response.text

    def test_mcp_post_endpoint_invalid_json(self, test_client):
        """Test MCP POST endpoint with invalid JSON."""
        response = test_client.post(
            "/mcp",
            data="invalid json",
            headers={"Origin": "http://localhost", "Content-Type": "application/json"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "error" in data
        assert data["error"]["code"] == -32700

    def test_mcp_get_endpoint_sse_stream(self, app):
        """Test MCP GET endpoint for SSE streaming setup."""
        get_routes = [
            route
            for route in app.routes
            if hasattr(route, "path")
            and route.path == "/mcp"
            and hasattr(route, "methods")
            and "GET" in route.methods
        ]
        assert len(get_routes) >= 1, "GET route for /mcp should exist"

    def test_cors_headers_present(self, test_client):
        """Test that CORS headers are properly configured."""
        response = test_client.options(
            "/mcp",
            headers={
                "Origin": "http://localhost",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers


class TestHTTPTransportErrorHandling:
    """Test error handling in HTTP transport."""

    def test_handler_exception_returns_json_rpc_error(
        self, test_client, mock_mcp_handler
    ):
        """Test error handling when MCP handler raises exception."""
        mock_mcp_handler.handle_request = AsyncMock(side_effect=Exception("Test error"))

        response = test_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "test", "id": 1},
            headers={"Origin": "http://localhost"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "error" in data
        assert data["error"]["code"] == -32603
        assert data["error"]["message"] == "Internal server error"

    def test_503_when_handler_not_initialised(self):
        """Test that 503 is returned when mcp_handler is not set."""
        app = FastAPI()
        # Intentionally do NOT set app.state.mcp_handler
        app.include_router(mcp_router)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "test", "id": 1},
        )

        assert response.status_code == 503
