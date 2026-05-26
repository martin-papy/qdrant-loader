"""Single-event webhook handler for WS-5 (Jira)."""

from __future__ import annotations

from typing import Any

from qdrant_loader.utils.logging import LoggingConfig
from qdrant_loader.webhooks.queue_backend import (
    SINGLE_DELETE,
    SINGLE_UPSERT,
    ChangeEvent,
)

logger = LoggingConfig.get_logger(__name__)


async def parse_webhook_event(
    source_type: str,
    source: str,
    payload: Any,
) -> ChangeEvent | None:
    """Parse webhook payload into a ChangeEvent for Jira single-event processing."""
    if source_type != "jira":
        return None

    if not isinstance(payload, dict):
        logger.warning("Jira payload is not a dict", payload_type=type(payload))
        return None

    try:
        issue = payload.get("issue", {})
        issue_key = issue.get("key")
        webhook_event = payload.get("webhookEvent", "unknown")

        if not issue_key:
            logger.warning("No issue.key in Jira webhook payload")
            return None

        operation = _map_jira_event_to_operation(webhook_event)
        if operation is None:
            logger.debug(
                "Unsupported Jira webhook event type",
                event_type=webhook_event,
            )
            return None

        return ChangeEvent(
            source=source,
            source_type=source_type,
            project_id=None,
            entity_id=issue_key,
            payload=payload,
            operation=operation,
        )
    except Exception as exc:
        logger.exception("Failed to parse Jira webhook event", exc_info=exc)
        return None


def _map_jira_event_to_operation(jira_event: str) -> str | None:
    """Map Jira webhook event type to WS-5 operation."""
    mapping = {
        "jira:issue_created": SINGLE_UPSERT,
        "jira:issue_updated": SINGLE_UPSERT,
        "jira:issue_deleted": SINGLE_DELETE,
    }
    return mapping.get(jira_event)
