from __future__ import annotations

from typing import Any


async def run_pipeline_ingestion(
    settings: Any,
    qdrant_manager: Any,
    *,
    project: str | None,
    source_type: str | None,
    source: str | None,
    force: bool,
    metrics_dir: str | None = None,
) -> None:
    from qdrant_loader.core.async_ingestion_pipeline import AsyncIngestionPipeline

    pipeline = (
        AsyncIngestionPipeline(settings, qdrant_manager, metrics_dir=metrics_dir)
        if metrics_dir
        else AsyncIngestionPipeline(settings, qdrant_manager)
    )
    try:
        await pipeline.process_documents(
            project_id=project,
            source_type=source_type,
            source=source,
            force=force,
        )
    finally:
        await pipeline.cleanup()


