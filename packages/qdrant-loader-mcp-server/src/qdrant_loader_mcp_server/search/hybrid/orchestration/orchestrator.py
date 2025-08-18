from __future__ import annotations

from typing import Any, List, Optional


class HybridOrchestrator:
    """Execute a planned hybrid search using engine-provided services.

    This layer is deliberately thin to preserve current behavior.
    """

    async def run_pipeline(
        self,
        pipeline: Any,
        *,
        query: str,
        limit: int,
        query_context: dict[str, Any],
        source_types: Optional[list[str]] = None,
        project_ids: Optional[list[str]] = None,
        vector_query: Optional[str] = None,
        keyword_query: Optional[str] = None,
    ) -> Any:
        return await pipeline.run(
            query=query,
            limit=limit,
            query_context=query_context,
            source_types=source_types,
            project_ids=project_ids,
            vector_query=vector_query or query,
            keyword_query=keyword_query or query,
        )


