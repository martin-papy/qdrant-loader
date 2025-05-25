import pytest


@pytest.mark.asyncio
async def test_handle_list_offerings(mcp_handler):
    """Test handling list offerings request."""
    request = {
        "jsonrpc": "2.0",
        "method": "listOfferings",
        "params": {},
        "id": 1,
    }
    response = await mcp_handler.handle_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    assert "offerings" in response["result"]
    assert len(response["result"]["offerings"]) == 1

    offering = response["result"]["offerings"][0]
    assert offering["id"] == "qdrant-loader"
    assert offering["name"] == "Qdrant Loader"
    assert "tools" in offering
    assert len(offering["tools"]) == 1
    assert "resources" in offering
    assert "resourceTemplates" in offering

    tool = offering["tools"][0]
    assert tool["name"] == "search"
    assert "parameters" in tool
    assert "properties" in tool["parameters"]
    assert "query" in tool["parameters"]["properties"]
    assert "source_types" in tool["parameters"]["properties"]
    assert "limit" in tool["parameters"]["properties"]
