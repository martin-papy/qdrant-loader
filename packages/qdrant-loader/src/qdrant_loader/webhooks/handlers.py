from __future__ import annotations

import json
from typing import Any

from qdrant_loader.cli.commands import run_pipeline_ingestion
from qdrant_loader.config import get_settings
from qdrant_loader.core.qdrant_manager import QdrantManager
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)

SUPPORTED_SOURCE_TYPES = {
    "jira",
    "confluence",
    "git",
    "publicdocs",
    "localfile",
}


def normalize_source_type(source_type: str) -> str:
    """Normalize and validate the source type from webhook routes."""
    normalized_source_type = source_type.strip().lower()
    if normalized_source_type not in SUPPORTED_SOURCE_TYPES:
        raise ValueError(
            f"Unsupported source type '{source_type}'. "
            f"Allowed values are: {', '.join(sorted(SUPPORTED_SOURCE_TYPES))}."
        )
    return normalized_source_type


def summarize_payload(payload: Any) -> str:
    """Create a short summary of webhook payload data for logging."""
    try:
        summary = json.dumps(payload, default=str, ensure_ascii=False)
    except Exception:
        return "<non-serializable payload>"
    if len(summary) > 1000:
        return summary[:1000] + "..."
    return summary


async def process_webhook_event(
    project_id: str | None,
    source_type: str,
    source: str,
    payload: Any,
    force: bool = False,
) -> None:
    """Handle webhook event by invoking the ingestion pipeline for a configured source.

    NOTE: The current webhook implementation logs the payload and triggers a full
    ingestion for the given source. The payload is not currently used for
    event filtering, deduplication, or priority routing.
    """
    normalized_source_type = normalize_source_type(source_type)
    settings = get_settings()
    qdrant_manager = QdrantManager(settings)

    payload_summary = {
        "type": type(payload).__name__,
        "keys": sorted(payload.keys())[:20] if isinstance(payload, dict) else None,
    }
    logger.info(
        "Received webhook event",
        project_id=project_id,
        source_type=normalized_source_type,
        source=source,
        force=force,
        payload_meta=payload_summary,
    )

    await run_pipeline_ingestion(
        settings,
        qdrant_manager,
        project=project_id,
        source_type=normalized_source_type,
        source=source,
        force=force,
    )


async def process_ingest_request(
    project_id: str | None,
    source_type: str | None,
    source: str | None,
    force: bool = False,
) -> None:
    """Handle a direct HTTP ingest request by invoking the ingestion pipeline."""
    if source is not None and source_type is None:
        raise ValueError(
            "source_type must be provided when source is specified."
        )

    normalized_source_type = (
        normalize_source_type(source_type) if source_type is not None else None
    )
    settings = get_settings()
    qdrant_manager = QdrantManager(settings)

    logger.info(
        "Received direct ingest request",
        project_id=project_id,
        source_type=normalized_source_type,
        source=source,
        force=force,
    )

    await run_pipeline_ingestion(
        settings,
        qdrant_manager,
        project=project_id,
        source_type=normalized_source_type,
        source=source,
        force=force,
    )
