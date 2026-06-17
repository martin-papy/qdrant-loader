"""FastMCP cross-document intelligence tools.

These delegate to the existing IntelligenceHandler (reusing its
result-normalization logic) and unwrap the structured payload, rather than
re-implementing it.

The handler is stateful (its cluster store is shared with
expand_cluster), so a single instance is built in the lifespan and reused.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

# Sentinel id for delegated handler calls. The handler uses it only to build a
# JSON-RPC envelope we immediately unwrap; any non-None value works (None would
# signal a notification and yield an empty response).
_REQUEST_ID = "fastmcp"

SimilarityMetric = Literal[
    "entity_overlap",
    "topic_overlap",
    "semantic_similarity",
    "metadata_similarity",
    "hierarchical_distance",
    "content_features",
]
ClusterStrategy = Literal[
    "mixed_features",
    "entity_based",
    "topic_based",
    "project_based",
    "hierarchical",
    "adaptive",
]


def _unwrap(response: dict[str, Any]) -> dict[str, Any]:
    """Return structuredContent from a legacy handler response, or raise."""
    if "error" in response:
        err = response.get("error") or {}
        msg = err.get("message", "Tool error")
        data = err.get("data")
        raise ToolError(f"{msg}: {data}" if data else msg)
    return response.get("result", {}).get("structuredContent", {})


def register_intelligence_tools(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True})
    async def analyze_relationships(
        ctx: Context,
        query: Annotated[
            str,
            Field(description="Search query to get documents for analysis", min_length=1),
        ],
        limit: Annotated[
            int, Field(description="Maximum number of documents to analyze", ge=1, le=1000)
        ] = 20,
        source_types: Annotated[
            list[str] | None, Field(description="Optional list of source types to filter by")
        ] = None,
        project_ids: Annotated[
            list[str] | None, Field(description="Optional list of project IDs to filter by")
        ] = None,
        use_llm: Annotated[
            bool, Field(description="Enable LLM validation for top pairs (budgeted)")
        ] = False,
        max_llm_pairs: Annotated[
            int, Field(description="Maximum number of pairs to analyze with LLM", ge=0, le=100)
        ] = 5,
        overall_timeout_s: Annotated[
            float, Field(description="Overall analysis budget in seconds", ge=0, le=3600)
        ] = 60,
        max_pairs_total: Annotated[
            int,
            Field(description="Maximum candidate pairs to analyze after tiering", ge=0, le=100000),
        ] = 1000,
        text_window_chars: Annotated[
            int,
            Field(description="Per-document text window size for lexical analysis", ge=0, le=10000),
        ] = 1000,
    ) -> dict[str, Any]:
        """Analyze relationships between documents."""
        handler = ctx.lifespan_context["intelligence_handler"]
        params = {
            "query": query,
            "limit": limit,
            "source_types": source_types,
            "project_ids": project_ids,
            "use_llm": use_llm,
            "max_llm_pairs": max_llm_pairs,
            "overall_timeout_s": overall_timeout_s,
            "max_pairs_total": max_pairs_total,
            "text_window_chars": text_window_chars,
        }
        return _unwrap(
            await handler.handle_analyze_document_relationships(_REQUEST_ID, params)
        )

    @mcp.tool(annotations={"readOnlyHint": True})
    async def find_similar_documents(
        ctx: Context,
        target_query: Annotated[
            str, Field(description="Query to find the target document", min_length=1)
        ],
        comparison_query: Annotated[
            str, Field(description="Query to get documents to compare against", min_length=1)
        ],
        similarity_metrics: Annotated[
            list[SimilarityMetric] | None, Field(description="Similarity metrics to use")
        ] = None,
        max_similar: Annotated[
            int, Field(description="Maximum number of similar documents to return")
        ] = 5,
        source_types: Annotated[
            list[str] | None, Field(description="Optional list of source types to filter by")
        ] = None,
        project_ids: Annotated[
            list[str] | None, Field(description="Optional list of project IDs to filter by")
        ] = None,
    ) -> dict[str, Any]:
        """Find documents similar to a target document using multiple similarity metrics."""
        handler = ctx.lifespan_context["intelligence_handler"]
        params = {
            "target_query": target_query,
            "comparison_query": comparison_query,
            "similarity_metrics": similarity_metrics,
            "max_similar": max_similar,
            "source_types": source_types,
            "project_ids": project_ids,
        }
        return _unwrap(await handler.handle_find_similar_documents(_REQUEST_ID, params))

    @mcp.tool(annotations={"readOnlyHint": True})
    async def detect_conflicts(
        ctx: Context,
        query: Annotated[
            str, Field(description="Search query to get documents for conflict analysis")
        ],
        limit: Annotated[
            int, Field(description="Maximum number of documents to analyze")
        ] = 10,
        source_types: Annotated[
            list[str] | None, Field(description="Optional list of source types to filter by")
        ] = None,
        project_ids: Annotated[
            list[str] | None, Field(description="Optional list of project IDs to filter by")
        ] = None,
    ) -> dict[str, Any]:
        """Detect conflicts and contradictions between documents."""
        handler = ctx.lifespan_context["intelligence_handler"]
        params = {
            "query": query,
            "limit": limit,
            "source_types": source_types,
            "project_ids": project_ids,
        }
        return _unwrap(
            await handler.handle_detect_document_conflicts(_REQUEST_ID, params)
        )

    @mcp.tool(annotations={"readOnlyHint": True})
    async def find_complementary_content(
        ctx: Context,
        target_query: Annotated[
            str, Field(description="Query to find the target document")
        ],
        context_query: Annotated[
            str, Field(description="Query to get contextual documents")
        ],
        max_recommendations: Annotated[
            int, Field(description="Maximum number of recommendations")
        ] = 5,
        source_types: Annotated[
            list[str] | None, Field(description="Optional list of source types to filter by")
        ] = None,
        project_ids: Annotated[
            list[str] | None, Field(description="Optional list of project IDs to filter by")
        ] = None,
    ) -> dict[str, Any]:
        """Find content that complements a target document."""
        handler = ctx.lifespan_context["intelligence_handler"]
        params = {
            "target_query": target_query,
            "context_query": context_query,
            "max_recommendations": max_recommendations,
            "source_types": source_types,
            "project_ids": project_ids,
        }
        return _unwrap(
            await handler.handle_find_complementary_content(_REQUEST_ID, params)
        )

    @mcp.tool(annotations={"readOnlyHint": True})
    async def cluster_documents(
        ctx: Context,
        query: Annotated[
            str, Field(description="Search query to get documents for clustering", min_length=1)
        ],
        strategy: Annotated[
            ClusterStrategy,
            Field(description="Clustering strategy (adaptive auto-selects the best one)"),
        ] = "mixed_features",
        max_clusters: Annotated[
            int, Field(description="Maximum number of clusters to create", ge=1, le=1000)
        ] = 10,
        min_cluster_size: Annotated[
            int, Field(description="Minimum size for a cluster", ge=1, le=1000)
        ] = 2,
        limit: Annotated[
            int, Field(description="Maximum number of documents to cluster", ge=1, le=1000)
        ] = 25,
        source_types: Annotated[
            list[str] | None, Field(description="Optional list of source types to filter by")
        ] = None,
        project_ids: Annotated[
            list[str] | None, Field(description="Optional list of project IDs to filter by")
        ] = None,
    ) -> dict[str, Any]:
        """Cluster documents based on similarity and relationships."""
        handler = ctx.lifespan_context["intelligence_handler"]
        params = {
            "query": query,
            "strategy": strategy,
            "max_clusters": max_clusters,
            "min_cluster_size": min_cluster_size,
            "limit": limit,
            "source_types": source_types,
            "project_ids": project_ids,
        }
        return _unwrap(await handler.handle_cluster_documents(_REQUEST_ID, params))
