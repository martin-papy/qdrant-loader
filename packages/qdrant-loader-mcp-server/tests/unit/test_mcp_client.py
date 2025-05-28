"""Test script for MCP server compatibility with Cursor client."""

import asyncio
import logging
from typing import Any

import pytest
import pytest_asyncio

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class MockMCPServer:
    """Mock MCP server for testing without external dependencies."""

    def __init__(self):
        """Initialize the mock server."""
        self.running = False
        self.request_queue = asyncio.Queue()
        self.response_queue = asyncio.Queue()

    async def start(self):
        """Start the mock server."""
        self.running = True
        logger.debug("Mock MCP server started")

    async def stop(self):
        """Stop the mock server."""
        self.running = False
        logger.debug("Mock MCP server stopped")

    async def send_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send a request to the mock server and get a response."""
        if not self.running:
            raise RuntimeError("Server is not running")

        # Mock responses based on request method
        method = request.get("method")
        request_id = request.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "Qdrant Loader MCP Server",
                        "version": "1.0.0",
                    },
                    "capabilities": {"tools": {"listChanged": False}},
                },
            }
        elif method == "ListOfferings":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "offerings": [
                        {
                            "id": "qdrant-loader",
                            "name": "Qdrant Loader",
                            "version": "1.0.0",
                            "tools": [
                                {
                                    "name": "search",
                                    "description": "Perform semantic search across multiple data sources",
                                }
                            ],
                        }
                    ]
                },
            }
        elif method == "InvalidMethod":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": "Method not found",
                    "data": "Method 'InvalidMethod' not found",
                },
            }
        elif method == "notify":
            # Notifications don't return responses
            return {}
        elif "jsonrpc" not in request or request["jsonrpc"] != "2.0":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32600,
                    "message": "Invalid Request",
                    "data": "Invalid JSON-RPC version",
                },
            }
        elif "method" not in request:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32600,
                    "message": "Invalid Request",
                    "data": "Missing method",
                },
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": "Method not found",
                    "data": f"Method '{method}' not found",
                },
            }


@pytest_asyncio.fixture
async def client():
    """Create and manage mock MCP test client."""
    client = MockMCPServer()
    await client.start()
    yield client
    await client.stop()


@pytest.mark.asyncio
async def test_initialize(client: MockMCPServer):
    """Test the initialize request."""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"supportsListOfferings": True},
        },
    }

    response = await client.send_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    assert response["result"]["protocolVersion"] == "2024-11-05"
    assert response["result"]["serverInfo"]["name"] == "Qdrant Loader MCP Server"
    assert response["result"]["capabilities"]["tools"]["listChanged"] is False


@pytest.mark.asyncio
async def test_list_offerings(client: MockMCPServer):
    """Test the ListOfferings request."""
    request = {"jsonrpc": "2.0", "id": 2, "method": "ListOfferings", "params": {}}

    response = await client.send_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 2
    assert "result" in response
    assert "offerings" in response["result"]
    assert len(response["result"]["offerings"]) == 1
    offering = response["result"]["offerings"][0]
    assert offering["id"] == "qdrant-loader"
    assert offering["name"] == "Qdrant Loader"
    assert offering["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_invalid_request(client: MockMCPServer):
    """Test an invalid request."""
    request = {"jsonrpc": "2.0", "id": 3, "method": "InvalidMethod", "params": {}}

    response = await client.send_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 3
    assert "error" in response
    assert response["error"]["code"] == -32601
    assert "Method not found" in response["error"]["message"]
    assert "InvalidMethod" in response["error"]["data"]


@pytest.mark.asyncio
async def test_malformed_request(client: MockMCPServer):
    """Test a malformed request."""
    # Missing jsonrpc
    request = {"id": 4, "method": "search", "params": {}}
    response = await client.send_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 4
    assert "error" in response
    assert response["error"]["code"] == -32600
    assert "Invalid Request" in response["error"]["message"]

    # Wrong jsonrpc version
    request = {"jsonrpc": "1.0", "id": 5, "method": "search", "params": {}}
    response = await client.send_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 5
    assert "error" in response
    assert response["error"]["code"] == -32600
    assert "Invalid Request" in response["error"]["message"]

    # Missing method
    request = {"jsonrpc": "2.0", "id": 6, "params": {}}
    response = await client.send_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 6
    assert "error" in response
    assert response["error"]["code"] == -32600
    assert "Invalid Request" in response["error"]["message"]


@pytest.mark.asyncio
async def test_notification(client: MockMCPServer):
    """Test a notification request."""
    request = {"jsonrpc": "2.0", "method": "notify", "params": {"event": "test"}}
    response = await client.send_request(request)
    assert response == {}


async def main():
    """Run all tests."""
    client = MockMCPServer()
    try:
        await client.start()

        # Test initialize
        await test_initialize(client)

        # Test ListOfferings
        await test_list_offerings(client)

        # Test invalid request
        await test_invalid_request(client)

        # Test malformed request
        await test_malformed_request(client)
    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
