"""Shared helpers for FastMCP tool modules that delegate to legacy handlers."""

from __future__ import annotations

from typing import Any

from fastmcp.exceptions import ToolError

# Sentinel id for delegated legacy-handler calls. The handler uses it only to
# build a JSON-RPC envelope we immediately unwrap; any non-None value works.
REQUEST_ID = "fastmcp"


def unwrap(response: dict[str, Any]) -> dict[str, Any]:
    """Return structuredContent from a legacy handler response, or raise."""
    if "error" in response:
        err = response.get("error") or {}
        msg = err.get("message", "Tool error")
        data = err.get("data")
        raise ToolError(f"{msg}: {data}" if data else msg)
    return response.get("result", {}).get("structuredContent", {})
