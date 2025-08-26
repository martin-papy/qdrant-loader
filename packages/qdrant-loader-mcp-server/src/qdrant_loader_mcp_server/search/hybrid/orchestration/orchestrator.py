from __future__ import annotations

from typing import Any


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
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
        vector_query: str | None = None,
        keyword_query: str | None = None,
    ) -> Any:
        return await pipeline.run(
            query=query,
            limit=limit,
            query_context=query_context,
            source_types=source_types,
            project_ids=project_ids,
            vector_query=vector_query if vector_query is not None else query,
            keyword_query=keyword_query if keyword_query is not None else query,
        )
