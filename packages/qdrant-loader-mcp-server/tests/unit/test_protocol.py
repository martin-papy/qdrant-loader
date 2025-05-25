"""Tests for MCP Protocol implementation."""

import pytest
from qdrant_loader_mcp_server.mcp.protocol import MCPProtocol


@pytest.fixture
def protocol():
    """Create protocol instance for testing."""
    return MCPProtocol()


def test_validate_request_valid(protocol):
    """Test validation of valid requests."""
    # Standard request
    assert protocol.validate_request(
        {"jsonrpc": "2.0", "method": "search", "params": {"query": "test"}, "id": "1"}
    )

    # Notification (no id)
    assert protocol.validate_request(
        {"jsonrpc": "2.0", "method": "notify", "params": {"event": "test"}}
    )

    # Request without params
    assert protocol.validate_request({"jsonrpc": "2.0", "method": "status", "id": 1})

    # Request with array params
    assert protocol.validate_request(
        {"jsonrpc": "2.0", "method": "batch", "params": [1, 2, 3], "id": "2"}
    )

    # Request with empty params
    assert protocol.validate_request(
        {"jsonrpc": "2.0", "method": "empty", "params": {}, "id": 3}
    )


def test_validate_request_invalid(protocol):
    """Test validation of invalid requests."""
    # Not a dict
    assert not protocol.validate_request([])
    assert not protocol.validate_request("invalid")
    assert not protocol.validate_request(None)

    # Missing jsonrpc
    assert not protocol.validate_request({"method": "search", "id": "1"})

    # Wrong jsonrpc version
    assert not protocol.validate_request(
        {"jsonrpc": "1.0", "method": "search", "id": "1"}
    )
    assert not protocol.validate_request(
        {"jsonrpc": "3.0", "method": "search", "id": "1"}
    )

    # Missing method
    assert not protocol.validate_request({"jsonrpc": "2.0", "id": "1"})

    # Invalid method type
    assert not protocol.validate_request({"jsonrpc": "2.0", "method": 123, "id": "1"})

    # Invalid params type
    assert not protocol.validate_request(
        {"jsonrpc": "2.0", "method": "search", "params": "invalid", "id": "1"}
    )
    assert not protocol.validate_request(
        {"jsonrpc": "2.0", "method": "search", "params": 123, "id": "1"}
    )

    # Invalid id type
    assert not protocol.validate_request(
        {"jsonrpc": "2.0", "method": "search", "id": None}
    )
    assert not protocol.validate_request(
        {"jsonrpc": "2.0", "method": "search", "id": {}}
    )
    assert not protocol.validate_request(
        {"jsonrpc": "2.0", "method": "search", "id": []}
    )


def test_validate_response_valid(protocol):
    """Test validation of valid responses."""
    # Success response with object result
    assert protocol.validate_response(
        {"jsonrpc": "2.0", "result": {"data": "test"}, "id": "1"}
    )

    # Success response with null result
    assert protocol.validate_response({"jsonrpc": "2.0", "result": None, "id": 1})

    # Success response with array result
    assert protocol.validate_response(
        {"jsonrpc": "2.0", "result": [1, 2, 3], "id": "2"}
    )

    # Error response
    assert protocol.validate_response(
        {
            "jsonrpc": "2.0",
            "error": {"code": -32600, "message": "Invalid Request"},
            "id": 3,
        }
    )

    # Error response with data
    assert protocol.validate_response(
        {
            "jsonrpc": "2.0",
            "error": {
                "code": -32600,
                "message": "Invalid Request",
                "data": "Additional error info",
            },
            "id": "4",
        }
    )

    # Empty response (for notifications)
    assert protocol.validate_response({})


def test_validate_response_invalid(protocol):
    """Test validation of invalid responses."""
    # Not a dict
    assert not protocol.validate_response([])
    assert not protocol.validate_response("invalid")
    assert not protocol.validate_response(None)

    # Missing jsonrpc
    assert not protocol.validate_response({"result": {}, "id": "1"})

    # Wrong jsonrpc version
    assert not protocol.validate_response({"jsonrpc": "1.0", "result": {}, "id": "1"})
    assert not protocol.validate_response({"jsonrpc": "3.0", "result": {}, "id": "1"})

    # Missing id
    assert not protocol.validate_response({"jsonrpc": "2.0", "result": {}})

    # Invalid id type
    assert not protocol.validate_response({"jsonrpc": "2.0", "result": {}, "id": None})
    assert not protocol.validate_response({"jsonrpc": "2.0", "result": {}, "id": {}})
    assert not protocol.validate_response({"jsonrpc": "2.0", "result": {}, "id": []})

    # Both result and error
    assert not protocol.validate_response(
        {
            "jsonrpc": "2.0",
            "result": {},
            "error": {"code": -32600, "message": "Error"},
            "id": "1",
        }
    )

    # Neither result nor error
    assert not protocol.validate_response({"jsonrpc": "2.0", "id": "1"})

    # Invalid error object
    assert not protocol.validate_response(
        {"jsonrpc": "2.0", "error": "invalid", "id": "1"}
    )
    assert not protocol.validate_response({"jsonrpc": "2.0", "error": {}, "id": "1"})
    assert not protocol.validate_response(
        {"jsonrpc": "2.0", "error": {"message": "Error"}, "id": "1"}
    )
    assert not protocol.validate_response(
        {"jsonrpc": "2.0", "error": {"code": -32600}, "id": "1"}
    )
    assert not protocol.validate_response(
        {"jsonrpc": "2.0", "error": {"code": "invalid", "message": "Error"}, "id": "1"}
    )


def test_create_response(protocol):
    """Test response creation."""
    # Success response with object result
    response = protocol.create_response("1", result={"data": "test"})
    assert response == {"jsonrpc": "2.0", "result": {"data": "test"}, "id": "1"}

    # Success response with null result
    response = protocol.create_response(1, result=None)
    assert response == {"jsonrpc": "2.0", "result": None, "id": 1}

    # Success response with array result
    response = protocol.create_response("2", result=[1, 2, 3])
    assert response == {"jsonrpc": "2.0", "result": [1, 2, 3], "id": "2"}

    # Error response
    response = protocol.create_response(
        3, error={"code": -32600, "message": "Invalid Request"}
    )
    assert response == {
        "jsonrpc": "2.0",
        "error": {"code": -32600, "message": "Invalid Request"},
        "id": 3,
    }

    # Error response with data
    response = protocol.create_response(
        "4",
        error={
            "code": -32600,
            "message": "Invalid Request",
            "data": "Additional error info",
        },
    )
    assert response == {
        "jsonrpc": "2.0",
        "error": {
            "code": -32600,
            "message": "Invalid Request",
            "data": "Additional error info",
        },
        "id": "4",
    }

    # Notification response
    response = protocol.create_response(None)
    assert response == {}

    # Invalid error object gets converted to internal error
    response = protocol.create_response("1", error="invalid")
    assert response == {
        "jsonrpc": "2.0",
        "error": {
            "code": -32603,
            "message": "Internal error",
            "data": "Invalid error object format",
        },
        "id": "1",
    }

    # Invalid error object with missing fields
    response = protocol.create_response("1", error={"message": "Error"})
    assert response == {
        "jsonrpc": "2.0",
        "error": {
            "code": -32603,
            "message": "Internal error",
            "data": "Invalid error object format",
        },
        "id": "1",
    }
