"""FastMCP `search` tool — semantic search across data sources."""

from __future__ import annotations

import asyncio
import inspect
from typing import Annotated, Any, Literal

from fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

SourceType = Literal["git", "confluence", "jira", "documentation", "localfile"]

class HierarchyFilter(BaseModel):
    """Hierarchy-aware filters for Confluence/localfile navigation."""

    depth: int | None = Field(
        default=None, description="Filter by specific hierarchy depth (0 = root pages)"
    )
    parent_title: str | None = Field(
        default=None, description="Filter by parent page title"
    )
    root_only: bool | None = Field(
        default=None, description="Show only root pages (no parent)"
    )
    has_children: bool | None = Field(
        default=None, description="Filter by whether pages have children"
    )


class AttachmentFilter(BaseModel):
    """Filters for file-attachment search."""

    attachments_only: bool | None = Field(
        default=None, description="Show only file attachments"
    )
    parent_document_title: str | None = Field(
        default=None, description="Filter by parent document title"
    )
    file_type: str | None = Field(
        default=None, description="Filter by file type (e.g., 'pdf', 'xlsx', 'png')"
    )
    file_size_min: int | None = Field(
        default=None, ge=0, description="Minimum file size in bytes"
    )
    file_size_max: int | None = Field(
        default=None, ge=0, description="Maximum file size in bytes"
    )
    author: str | None = Field(default=None, description="Filter by attachment author")


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

    @mcp.tool(annotations={"readOnlyHint": True})
    async def hierarchy_search(
        ctx: Context,
        query: Annotated[
            str, Field(description="The search query in natural language", min_length=1)
        ],
        hierarchy_filter: Annotated[
            HierarchyFilter | None,
            Field(description="Hierarchy-aware filters"),
        ] = None,
        organize_by_hierarchy: Annotated[
            bool, Field(description="Group results by hierarchy structure")
        ] = False,
        limit: Annotated[
            int, Field(description="Maximum number of results to return", ge=1)
        ] = 10,
    ) -> dict[str, Any]:
        """Search Confluence documents with hierarchy-aware filtering and organization."""
        handler = ctx.lifespan_context["search_handler"]
        hf = hierarchy_filter.model_dump(exclude_none=True) if hierarchy_filter else {}

        processed = await handler.query_processor.process_query(query)
        results = await handler.search_engine.search(
            query=processed["query"],
            source_types=["confluence", "localfile"],
            limit=max(limit * 2, 40),
        )
        # Filter helper may be sync or async-patched (matches legacy handling).
        maybe = handler._apply_hierarchy_filters(results, hf)
        filtered = await maybe if inspect.isawaitable(maybe) else maybe
        filtered = filtered[: max(limit, 20)]

        organized = (
            handler._organize_by_hierarchy(filtered) if organize_by_hierarchy else None
        )
        return handler.formatters.create_lightweight_hierarchy_results(
            filtered, organized or {}, query
        )

    @mcp.tool(annotations={"readOnlyHint": True})
    async def attachment_search(
        ctx: Context,
        query: Annotated[
            str, Field(description="The search query in natural language", min_length=1)
        ],
        attachment_filter: Annotated[
            AttachmentFilter | None,
            Field(description="Attachment filters"),
        ] = None,
        include_parent_context: Annotated[
            bool, Field(description="Include parent document information in results")
        ] = True, # TODO: Add behavior; logged-only for now
        limit: Annotated[
            int, Field(description="Maximum number of results to return", ge=1)
        ] = 10,
    ) -> dict[str, Any]:
        """Search for file attachments and their parent documents."""
        handler = ctx.lifespan_context["search_handler"]
        af = attachment_filter.model_dump(exclude_none=True) if attachment_filter else {}

        processed = await handler.query_processor.process_query(query)
        results = await handler.search_engine.search(
            query=processed["query"],
            source_types=None,
            limit=limit * 2,
        )
        filtered = handler._apply_lightweight_attachment_filters(results, af)
        filtered = filtered[: max(limit, 15)]

        attachment_groups = (
            handler.formatters._organize_attachments_by_type(filtered)
            if filtered
            else []
        )
        return handler.formatters.create_lightweight_attachment_results(
            attachment_groups, query
        )
