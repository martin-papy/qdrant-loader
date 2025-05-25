"""MCP Protocol implementation."""

from typing import Any


class MCPProtocol:
    """MCP Protocol implementation for handling RAG requests."""

    def __init__(self):
        """Initialize MCP Protocol."""
        self.version = "2.0"
        self.initialized = False

    def validate_request(self, request: dict[str, Any]) -> bool:
        """Validate MCP request format according to JSON-RPC 2.0 specification.

        Args:
            request: The request to validate

        Returns:
            bool: True if request is valid, False otherwise
        """
        # Check for required fields
        if not isinstance(request, dict):
            return False

        # Handle empty dict
        if not request:
            # Allow empty dict only during initialization
            return not self.initialized

        # For initialization request, be more lenient
        if not self.initialized:
            if request.get("method") == "initialize":
                return True

        # Standard validation for other requests
        if "jsonrpc" not in request or request["jsonrpc"] != "2.0":
            return False

        if "method" not in request or not isinstance(request["method"], str):
            return False

        # For requests (not notifications), id is required
        if "id" in request:
            if not isinstance(request["id"], str | int):
                return False
            if request["id"] is None:
                return False
        else:
            # This is a notification, which is valid
            return True

        # Params is optional but must be object or array if present
        if "params" in request and not isinstance(request["params"], dict | list):
            return False

        return True

    def validate_response(self, response: dict[str, Any]) -> bool:
        """Validate MCP response format according to JSON-RPC 2.0 specification.

        Args:
            response: The response to validate

        Returns:
            bool: True if response is valid, False otherwise
        """
        if not isinstance(response, dict):
            return False

        # Empty response is valid for notifications
        if not response:
            return True

        # Check required fields
        if "jsonrpc" not in response or response["jsonrpc"] != "2.0":
            return False

        if "id" not in response:
            return False

        if not isinstance(response["id"], str | int):
            return False

        # Must have either result or error, but not both
        has_result = "result" in response
        has_error = "error" in response

        if not has_result and not has_error:
            return False

        if has_result and has_error:
            return False

        # Validate error object structure if present
        if has_error:
            error = response["error"]
            if not isinstance(error, dict):
                return False
            if "code" not in error or not isinstance(error["code"], int):
                return False
            if "message" not in error or not isinstance(error["message"], str):
                return False

        return True

    def create_response(
        self,
        request_id: str | int | None,
        result: Any | None = None,
        error: dict | None = None,
    ) -> dict[str, Any]:
        """Create MCP response according to JSON-RPC 2.0 specification.

        Args:
            request_id: The ID of the request (None for notifications)
            result: The result of the request
            error: Any error that occurred

        Returns:
            Dict[str, Any]: The response object
        """
        # For notifications, return empty dict
        if request_id is None:
            return {}

        # Create base response
        response = {"jsonrpc": self.version, "id": request_id}

        # Add either result or error, but not both
        if error is not None:
            if (
                not isinstance(error, dict)
                or "code" not in error
                or "message" not in error
            ):
                error = {
                    "code": -32603,
                    "message": "Internal error",
                    "data": "Invalid error object format",
                }
            response["error"] = error
        else:
            # For successful responses, always include result (can be None)
            response["result"] = result

        # Validate response before returning
        if not self.validate_response(response):
            return {
                "jsonrpc": self.version,
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": "Generated invalid response format",
                },
            }

        return response

    def mark_initialized(self):
        """Mark the protocol as initialized."""
        self.initialized = True
