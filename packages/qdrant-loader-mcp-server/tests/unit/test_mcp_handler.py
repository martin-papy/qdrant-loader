"""Tests for MCP handler functionality."""

import pytest


@pytest.mark.asyncio
async def test_handle_tools_list(mcp_handler):
    """Test handling tools/list request."""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 1,
    }
    response = await mcp_handler.handle_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    assert "tools" in response["result"]
    assert len(response["result"]["tools"]) == 1

    tool = response["result"]["tools"][0]
    assert tool["name"] == "search"
    assert "description" in tool
    assert "inputSchema" in tool
    assert "properties" in tool["inputSchema"]
    assert "query" in tool["inputSchema"]["properties"]
    assert "source_types" in tool["inputSchema"]["properties"]
    assert "limit" in tool["inputSchema"]["properties"]


@pytest.mark.asyncio
async def test_handle_tools_call(mcp_handler):
    """Test handling tools/call request."""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "search", "arguments": {"query": "test query", "limit": 5}},
        "id": 2,
    }
    response = await mcp_handler.handle_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 2
    assert "result" in response
    assert "content" in response["result"]
    assert response["result"]["isError"] is False


@pytest.mark.asyncio
async def test_handle_search_direct(mcp_handler):
    """Test handling direct search request."""
    request = {
        "jsonrpc": "2.0",
        "method": "search",
        "params": {"query": "test query", "source_types": ["git"], "limit": 5},
        "id": 3,
    }
    response = await mcp_handler.handle_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 3
    assert "result" in response
    assert "content" in response["result"]
    assert response["result"]["isError"] is False
