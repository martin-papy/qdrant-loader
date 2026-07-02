"""FastMCP tool registrations (migration target).

Each tool module exposes a ``register_*`` function that attaches tools to a
FastMCP instance. ``register_all`` wires them all up. During the migration
these live alongside the hand-rolled mcp/ handlers.
"""

from fastmcp import FastMCP

from .expand import register_expand_tools
from .graph import register_graph_tools
from .intelligence import register_intelligence_tools
from .search import register_search_tools


def register_all(mcp: FastMCP) -> None:
    register_search_tools(mcp)
    register_intelligence_tools(mcp)
    register_expand_tools(mcp)
    register_graph_tools(mcp)


__all__ = [
    "register_all",
    "register_search_tools",
    "register_intelligence_tools",
    "register_expand_tools",
    "register_graph_tools",
]
