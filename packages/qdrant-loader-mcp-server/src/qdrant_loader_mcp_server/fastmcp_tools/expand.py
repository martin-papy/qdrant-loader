"""FastMCP expansion tools (lazy-loading).

Delegate to existing handlers — SearchHandler for document/chunk expansion,
IntelligenceHandler for cluster expansion — and unwrap the structured payload.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context, FastMCP
from pydantic import Field

from ._common import REQUEST_ID, unwrap


def register_expand_tools(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True})
    async def expand_document(
        ctx: Context,
        document_id: Annotated[
            str,
            Field(
                description="The ID of the document to expand and retrieve full content",
                min_length=1,
            ),
        ],
        include_metadata: Annotated[
            bool, Field(description="Include detailed metadata (optional)")
        ] = True,
        include_hierarchy: Annotated[
            bool,
            Field(description="Include hierarchy information for Confluence documents"),
        ] = True,
        include_attachments: Annotated[
            bool, Field(description="Include attachment information if available")
        ] = True,
    ) -> dict[str, Any]:
        """Retrieve full document content by document ID for lazy loading."""
        handler = ctx.lifespan_context["search_handler"]
        params = {
            "document_id": document_id,
            "include_metadata": include_metadata,
            "include_hierarchy": include_hierarchy,
            "include_attachments": include_attachments,
        }
        return unwrap(await handler.handle_expand_document(REQUEST_ID, params))

    @mcp.tool(annotations={"readOnlyHint": True})
    async def expand_chunk_context(
        ctx: Context,
        document_id: Annotated[
            str, Field(description="Unique identifier of the document.", min_length=1)
        ],
        chunk_index: Annotated[
            int,
            Field(description="Index of the target chunk within the document.", ge=0),
        ],
        window_size: Annotated[
            int,
            Field(
                description="Number of chunks to include before and after the target chunk.",
                ge=0,
            ),
        ] = 2,
    ) -> dict[str, Any]:
        """Retrieve neighboring chunks within the same document based on chunk_index."""
        handler = ctx.lifespan_context["search_handler"]
        params = {
            "document_id": document_id,
            "chunk_index": chunk_index,
            "window_size": window_size,
        }
        return unwrap(await handler.handle_expand_chunk_context(REQUEST_ID, params))

    @mcp.tool(annotations={"readOnlyHint": True})
    async def expand_cluster(
        ctx: Context,
        cluster_id: Annotated[
            str,
            Field(
                description="The ID of the cluster to expand and retrieve all documents",
                min_length=1,
            ),
        ],
        cluster_session_id: Annotated[
            str, Field(description="UUID representing a clustering session", min_length=1)
        ],
        limit: Annotated[
            int,
            Field(description="Maximum number of documents to return from cluster", ge=1),
        ] = 20,
        offset: Annotated[
            int, Field(description="Number of documents to skip for pagination", ge=0)
        ] = 0,
        include_metadata: Annotated[
            bool, Field(description="Include detailed metadata for each document")
        ] = True,
    ) -> dict[str, Any]:
        """Retrieve all documents from a specific cluster for lazy loading."""
        handler = ctx.lifespan_context["intelligence_handler"]
        params = {
            "cluster_id": cluster_id,
            "cluster_session_id": cluster_session_id,
            "limit": limit,
            "offset": offset,
            "include_metadata": include_metadata,
        }
        return unwrap(await handler.handle_expand_cluster(REQUEST_ID, params))
