"""MCP (Model Context Protocol) implementation for RAG server.

The hand-rolled JSON-RPC dispatcher (MCPHandler) and tool schemas were removed
in favour of the FastMCP app in ``fastmcp_app`` / ``fastmcp_tools``. The
SearchHandler/IntelligenceHandler business logic and MCPProtocol (used by them
to build response envelopes) remain and are consumed by the FastMCP tools.
"""

from .protocol import MCPProtocol

__all__ = ["MCPProtocol"]
