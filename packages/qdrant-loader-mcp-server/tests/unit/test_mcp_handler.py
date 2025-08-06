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
    assert len(response["result"]["tools"]) == 9

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


@pytest.mark.asyncio
async def test_handle_hierarchy_search_tools_call(mcp_handler):
    """Test handling hierarchy_search via tools/call request."""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "hierarchy_search",
            "arguments": {
                "query": "documentation",
                "hierarchy_filter": {"depth": 1, "has_children": True},
                "organize_by_hierarchy": True,
                "limit": 5,
            },
        },
        "id": 4,
    }
    response = await mcp_handler.handle_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 4
    assert "result" in response
    assert "content" in response["result"]
    assert response["result"]["isError"] is False


@pytest.mark.asyncio
async def test_handle_hierarchy_search_missing_query(mcp_handler):
    """Test hierarchy_search with missing query parameter."""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "hierarchy_search",
            "arguments": {"limit": 5},  # Missing query
        },
        "id": 5,
    }
    response = await mcp_handler.handle_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 5
    assert "error" in response
    assert response["error"]["code"] == -32602
    assert "Missing required parameter: query" in response["error"]["data"]


@pytest.mark.asyncio
async def test_handle_hierarchy_search_root_only_filter(mcp_handler):
    """Test hierarchy_search with root_only filter."""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "hierarchy_search",
            "arguments": {
                "query": "documentation",
                "hierarchy_filter": {"root_only": True},
                "limit": 3,
            },
        },
        "id": 6,
    }
    response = await mcp_handler.handle_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 6
    assert "result" in response
    assert "content" in response["result"]
    assert response["result"]["isError"] is False


@pytest.mark.asyncio
async def test_handle_hierarchy_search_parent_title_filter(mcp_handler):
    """Test hierarchy_search with parent_title filter."""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "hierarchy_search",
            "arguments": {
                "query": "API",
                "hierarchy_filter": {"parent_title": "Developer Guide"},
                "limit": 5,
            },
        },
        "id": 7,
    }
    response = await mcp_handler.handle_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 7
    assert "result" in response
    assert "content" in response["result"]
    assert response["result"]["isError"] is False


@pytest.mark.asyncio
async def test_handle_attachment_search_tools_call(mcp_handler):
    """Test handling attachment_search via tools/call request."""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "attachment_search",
            "arguments": {
                "query": "specification",
                "attachment_filter": {"attachments_only": True, "file_type": "pdf"},
                "include_parent_context": True,
                "limit": 5,
            },
        },
        "id": 8,
    }
    response = await mcp_handler.handle_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 8
    assert "result" in response
    assert "content" in response["result"]
    assert response["result"]["isError"] is False


@pytest.mark.asyncio
async def test_handle_attachment_search_missing_query(mcp_handler):
    """Test attachment_search with missing query parameter."""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "attachment_search",
            "arguments": {"limit": 5},  # Missing query
        },
        "id": 9,
    }
    response = await mcp_handler.handle_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 9
    assert "error" in response
    assert response["error"]["code"] == -32602
    assert "Missing required parameter: query" in response["error"]["data"]


@pytest.mark.asyncio
async def test_handle_attachment_search_file_size_filter(mcp_handler):
    """Test attachment_search with file size filters."""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "attachment_search",
            "arguments": {
                "query": "document",
                "attachment_filter": {
                    "attachments_only": True,
                    "file_size_min": 1048576,  # 1MB
                    "file_size_max": 10485760,  # 10MB
                },
                "limit": 5,
            },
        },
        "id": 10,
    }
    response = await mcp_handler.handle_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 10
    assert "result" in response
    assert "content" in response["result"]
    assert response["result"]["isError"] is False


@pytest.mark.asyncio
async def test_handle_attachment_search_author_filter(mcp_handler):
    """Test attachment_search with author filter."""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "attachment_search",
            "arguments": {
                "query": "project",
                "attachment_filter": {
                    "attachments_only": True,
                    "author": "john.doe@company.com",
                },
                "include_parent_context": True,
                "limit": 5,
            },
        },
        "id": 11,
    }
    response = await mcp_handler.handle_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 11
    assert "result" in response
    assert "content" in response["result"]
    assert response["result"]["isError"] is False


@pytest.mark.asyncio
async def test_handle_attachment_search_parent_document_filter(mcp_handler):
    """Test attachment_search with parent document filter."""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "attachment_search",
            "arguments": {
                "query": "requirements",
                "attachment_filter": {"parent_document_title": "Project Planning"},
                "include_parent_context": True,
                "limit": 5,
            },
        },
        "id": 12,
    }
    response = await mcp_handler.handle_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 12
    assert "result" in response
    assert "content" in response["result"]
    assert response["result"]["isError"] is False


@pytest.mark.asyncio
async def test_handle_unknown_tool(mcp_handler):
    """Test handling unknown tool request."""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "unknown_tool", "arguments": {"query": "test"}},
        "id": 13,
    }
    response = await mcp_handler.handle_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 13
    assert "error" in response
    assert response["error"]["code"] == -32601
    assert "Method not found" in response["error"]["message"]


@pytest.mark.asyncio
async def test_tools_list_contains_all_three_tools(mcp_handler):
    """Test that tools/list returns all three search tools."""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 14,
    }
    response = await mcp_handler.handle_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 14
    assert "result" in response
    assert "tools" in response["result"]

    tools = response["result"]["tools"]
    assert len(tools) == 9

    tool_names = [tool["name"] for tool in tools]
    assert "search" in tool_names
    assert "hierarchy_search" in tool_names
    assert "attachment_search" in tool_names

    # Check hierarchy_search tool schema
    hierarchy_tool = next(tool for tool in tools if tool["name"] == "hierarchy_search")
    assert "hierarchy_filter" in hierarchy_tool["inputSchema"]["properties"]
    assert "organize_by_hierarchy" in hierarchy_tool["inputSchema"]["properties"]

    # Check attachment_search tool schema
    attachment_tool = next(
        tool for tool in tools if tool["name"] == "attachment_search"
    )
    assert "attachment_filter" in attachment_tool["inputSchema"]["properties"]
    assert "include_parent_context" in attachment_tool["inputSchema"]["properties"]
