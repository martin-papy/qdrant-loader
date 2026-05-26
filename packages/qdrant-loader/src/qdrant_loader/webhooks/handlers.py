from __future__ import annotations

import json
from typing import Any

from qdrant_loader.utils.logging import LoggingConfig
from qdrant_loader.webhooks.queue_backend import (
    FULL_SCAN,
    ChangeEvent,
    QueueBackendManager,
)
from qdrant_loader.webhooks.single_event_handler import parse_webhook_event

logger = LoggingConfig.get_logger(__name__)

# Single-event webhook support is Jira-only in v1.1.
SUPPORTED_SOURCE_TYPES = {"jira"}

# Direct /ingest API supports all configured connector types.
INGEST_SUPPORTED_SOURCE_TYPES = {
    "jira",
    "confluence",
    "git",
    "publicdocs",
    "localfile",
}


def normalize_source_type(source_type: str) -> str:
    """Normalize and validate the source type from Jira webhook routes."""
    normalized_source_type = source_type.strip().lower()
    if normalized_source_type not in SUPPORTED_SOURCE_TYPES:
        raise ValueError(
            f"Unsupported source type '{source_type}'. "
            f"Allowed values are: {', '.join(sorted(SUPPORTED_SOURCE_TYPES))}."
        )
    return normalized_source_type


def normalize_ingest_source_type(source_type: str) -> str:
    """Normalize and validate the source type for direct /ingest requests."""
    normalized_source_type = source_type.strip().lower()
    if normalized_source_type not in INGEST_SUPPORTED_SOURCE_TYPES:
        raise ValueError(
            f"Unsupported source type '{source_type}'. "
            f"Allowed values are: {', '.join(sorted(INGEST_SUPPORTED_SOURCE_TYPES))}."
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


async def enqueue_webhook_event(
    project_id: str | None,
    source_type: str,
    source: str,
    payload: Any,
    force: bool = False,
) -> dict[str, Any]:
    """Parse webhook payload and enqueue a durable change event.

    Jira webhooks use SINGLE_UPSERT/SINGLE_DELETE when the payload is parseable.
    Falls back to FULL_SCAN when force=True or parsing fails.
    """
    normalized_source_type = normalize_source_type(source_type)
    queue = QueueBackendManager.get_backend()

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

    if force:
        event = ChangeEvent(
            source=source,
            source_type=normalized_source_type,
            project_id=project_id,
            operation=FULL_SCAN,
            payload=payload,
            force=True,
        )
        message_id = await queue.enqueue(event)
        return {
            "operation": FULL_SCAN,
            "message_id": message_id,
            "queued": True,
        }

    change_event = await parse_webhook_event(
        normalized_source_type, source, payload
    )
    if change_event is not None:
        change_event.project_id = project_id
        message_id = await queue.enqueue(change_event)
        logger.info(
            "Enqueued single-event webhook",
            operation=change_event.operation,
            entity_id=change_event.entity_id,
            message_id=message_id,
        )
        return {
            "operation": change_event.operation,
            "entity_id": change_event.entity_id,
            "message_id": message_id,
            "queued": True,
        }

    logger.info(
        "Could not parse single-event; enqueueing full scan",
        source_type=normalized_source_type,
        source=source,
    )
    event = ChangeEvent(
        source=source,
        source_type=normalized_source_type,
        project_id=project_id,
        operation=FULL_SCAN,
        payload=payload,
        force=False,
    )
    message_id = await queue.enqueue(event)
    return {
        "operation": FULL_SCAN,
        "message_id": message_id,
        "queued": True,
    }


async def enqueue_ingest_request(
    project_id: str | None,
    source_type: str | None,
    source: str | None,
    force: bool = False,
) -> dict[str, Any]:
    """Enqueue a direct ingestion job (replaces CLI `qdrant-loader ingest`).

    Always uses FULL_SCAN; the worker runs the same pipeline as the ingest command.
    """
    if source is not None and source_type is None:
        raise ValueError(
            "source_type must be provided when source is specified."
        )

    normalized_source_type = (
        normalize_ingest_source_type(source_type) if source_type else None
    )
    queue = QueueBackendManager.get_backend()

    logger.info(
        "Received direct ingest request",
        project_id=project_id,
        source_type=normalized_source_type,
        source=source,
        force=force,
    )

    event = ChangeEvent(
        source=source or "",
        source_type=normalized_source_type,
        project_id=project_id,
        operation=FULL_SCAN,
        force=force,
    )
    message_id = await queue.enqueue(event)
    return {
        "operation": FULL_SCAN,
        "message_id": message_id,
        "queued": True,
    }
