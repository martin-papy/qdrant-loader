"""FastMCP `search` tool — semantic search across data sources."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any, Literal

from fastmcp import Context, FastMCP
from pydantic import Field

SourceType = Literal["git", "confluence", "jira", "documentation", "localfile"]


def register_search_tools(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True})
    async def search(
        ctx: Context,
        query: Annotated[
            str, Field(description="The search query in natural language", min_length=1)
        ],
        source_types: Annotated[
            list[SourceType] | None,
            Field(description="Optional list of source types to filter results"),
        ] = None,
        project_ids: Annotated[
            list[str] | None,
            Field(description="Optional list of project IDs to filter results"),
        ] = None,
        limit: Annotated[
            int, Field(description="Maximum number of results to return", ge=1)
        ] = 5,
    ) -> dict[str, Any]:
        """Perform semantic search across multiple data sources."""
        handler = ctx.lifespan_context["search_handler"]
        st = source_types or []
        pids = project_ids or []

        processed = await handler.query_processor.process_query(query)
        results = await handler.search_engine.search(
            query=processed["query"],
            source_types=st,
            project_ids=pids,
            limit=limit,
        )
        if handler.reranker:
            results = await asyncio.to_thread(
                handler.reranker.rerank,
                query=query,
                results=results,
                top_k=limit,
                text_key="text",
            )

        return {
            "results": handler.formatters.create_structured_search_results(results),
            "total_found": len(results),
            "query_context": {
                "original_query": query,
                "source_types_filtered": st,
                "project_ids_filtered": pids,
            },
        }
