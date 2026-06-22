"""
FastMCP Knowledge Graph tools (lazy-loading).

Delegate to IntelligenceHandler for graph exploration and querying
capabilities, including:

- find_ticket_dependencies: traverse Jira blocking dependencies
- get_epic_tree: retrieve full epic hierarchy
- find_related_documents: generic multi-hop graph traversal
- query_knowledge_graph: execute raw Cypher queries

Returns the structured graph response payload from the underlying handler.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context, FastMCP
from pydantic import Field

from ._common import REQUEST_ID, unwrap


def register_graph_tools(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True})
    async def find_ticket_dependencies(
        ctx: Context,
        ticket_key: Annotated[
            str,
            Field(
                description="Jira ticket key to analyze dependency relationships",
                min_length=1,
            ),
        ],
        depth: Annotated[
            int,
            Field(
                description="Maximum traversal depth for dependency relationships",
                ge=1,
                le=10,
            ),
        ] = 2,
    ) -> dict[str, Any]:
        """Traverse Jira blocking dependencies in the knowledge graph."""
        handler = ctx.lifespan_context["intelligence_handler"]

        params = {
            "ticket_key": ticket_key,
            "depth": depth,
        }

        return unwrap(
            await handler.handle_find_ticket_dependencies(
                REQUEST_ID,
                params,
            )
        )
