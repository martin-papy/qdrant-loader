from __future__ import annotations

import traceback
from typing import Any

from qdrant_loader.utils.logging import LoggingConfig
from qdrant_loader.utils.sensitive import sanitize_exception_message


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
    logger = LoggingConfig.get_logger(__name__)
    ingestion_error: Exception | None = None
    try:
        await pipeline.process_documents(
            project_id=project,
            source_type=source_type,
            source=source,
            force=force,
        )
    except Exception as e:
        ingestion_error = e
        sanitized_traceback = sanitize_exception_message(traceback.format_exc())
        logger.error(
            "Ingestion failed",
            error=sanitize_exception_message(e),
            error_type=type(e).__name__,
            sanitized_traceback=sanitized_traceback,
        )
    cleanup_error: Exception | None = None
    try:
        await pipeline.cleanup()
    except Exception as e:
        cleanup_error = e
        sanitized_traceback = sanitize_exception_message(traceback.format_exc())
        if ingestion_error is not None:
            logger.error(
                "Cleanup failed after ingestion exception",
                error=sanitize_exception_message(e),
                error_type=type(e).__name__,
                sanitized_traceback=sanitized_traceback,
            )
        else:
            logger.error(
                "Cleanup failed after successful ingestion",
                error=sanitize_exception_message(e),
                error_type=type(e).__name__,
                sanitized_traceback=sanitized_traceback,
            )
    if ingestion_error is not None:
        raise ingestion_error
    if cleanup_error is not None:
        raise cleanup_error
