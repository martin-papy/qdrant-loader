"""Process queued webhook change events."""

from __future__ import annotations

from typing import Any

from qdrant_loader.config import get_settings
from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.factory import get_connector_instance
from qdrant_loader.core.document import Document
from qdrant_loader.core.qdrant_manager import QdrantManager
from qdrant_loader.utils.logging import LoggingConfig
from qdrant_loader.webhooks.queue_backend import (
    FULL_SCAN,
    SINGLE_DELETE,
    SINGLE_UPSERT,
    ChangeEvent,
)

logger = LoggingConfig.get_logger(__name__)


async def process_change_event(event: ChangeEvent) -> None:
    """Execute a queued webhook change event."""
    settings = get_settings()
    qdrant_manager = QdrantManager(settings)

    from qdrant_loader.core.async_ingestion_pipeline import AsyncIngestionPipeline

    pipeline = AsyncIngestionPipeline(settings, qdrant_manager)
    try:
        if event.operation == FULL_SCAN:
            await pipeline.process_documents(
                project_id=event.project_id,
                source_type=event.source_type or None,
                source=event.source or None,
                force=event.force,
            )
        elif event.operation == SINGLE_UPSERT:
            await _process_single_upsert(pipeline, event)
        elif event.operation == SINGLE_DELETE:
            await _process_single_delete(pipeline, event)
        else:
            raise ValueError(f"Unsupported webhook operation: {event.operation}")
    finally:
        await pipeline.cleanup()


async def _process_single_upsert(
    pipeline: Any,
    event: ChangeEvent,
) -> None:
    if not event.entity_id:
        raise ValueError("SINGLE_UPSERT requires entity_id")

    await pipeline.initialize()
    source_config, project_id = _resolve_source_config(
        pipeline, event.project_id, event.source_type, event.source
    )
    connector = get_connector_instance(source_config)
    file_conversion_config = pipeline.settings.global_config.file_conversion
    if (
        file_conversion_config
        and hasattr(connector, "set_file_conversion_config")
        and getattr(source_config, "enable_file_conversion", False)
    ):
        connector.set_file_conversion_config(file_conversion_config)

    async with connector:
        document = await connector.fetch_by_id(event.entity_id)

    if document is None:
        logger.warning(
            "Entity not found for SINGLE_UPSERT",
            entity_id=event.entity_id,
            source=event.source,
        )
        return

    if project_id and pipeline.project_manager:
        document.metadata = pipeline.project_manager.inject_project_metadata(
            project_id, document.metadata
        )

    result = await pipeline.orchestrator.components.document_pipeline.process_documents(
        [document]
    )
    await pipeline.orchestrator._update_document_states(
        [document],
        result.successfully_processed_documents,
        project_id,
    )
    logger.info(
        "SINGLE_UPSERT completed",
        entity_id=event.entity_id,
        source=event.source,
        chunks=result.success_count,
    )


async def _process_single_delete(
    pipeline: Any,
    event: ChangeEvent,
) -> None:
    document = _document_from_delete_payload(event)
    if document is None:
        logger.warning(
            "Could not build delete document from webhook payload",
            entity_id=event.entity_id,
            source=event.source,
        )
        return

    project_id = event.project_id
    if project_id and pipeline.project_manager:
        document.metadata = pipeline.project_manager.inject_project_metadata(
            project_id, document.metadata
        )

    await pipeline.initialize()
    await pipeline.orchestrator._process_deleted_documents(
        [document],
        project_id,
    )
    logger.info(
        "SINGLE_DELETE completed",
        entity_id=event.entity_id,
        document_id=document.id,
        source=event.source,
    )


def _document_from_delete_payload(event: ChangeEvent) -> Document | None:
    """Build a minimal Document for deletion from Jira webhook payload."""
    payload = event.payload if isinstance(event.payload, dict) else {}
    issue = payload.get("issue", {})
    issue_id = issue.get("id") or event.entity_id
    issue_key = issue.get("key") or event.entity_id
    if not issue_id:
        return None

    base_url = ""
    fields = issue.get("fields") or {}
    self_url = issue.get("self", "")
    if self_url and "/rest/api/" in self_url:
        base_url = self_url.split("/rest/api/")[0]

    url = f"{base_url}/browse/{issue_key}" if base_url and issue_key else ""
    updated = fields.get("updated", "")

    return Document(
        id=str(issue_id),
        content="",
        content_type="text",
        source=event.source,
        source_type=SourceType.JIRA,
        url=url,
        title=fields.get("summary", issue_key or "Deleted Issue"),
        is_deleted=True,
        metadata={
            "key": issue_key,
            "updated_at": updated,
            "uri": f"{SourceType.JIRA}:{event.source}:{url}",
        },
    )


def _resolve_source_config(
    pipeline: Any,
    project_id: str | None,
    source_type: str,
    source_name: str,
) -> tuple[Any, str | None]:
    """Resolve connector config and project id for a named source."""
    if source_type != "jira":
        raise ValueError(f"Single-event processing is not supported for {source_type}")

    if project_id:
        if not pipeline.project_manager:
            raise ValueError("Project manager not available")
        project_context = pipeline.project_manager.get_project_context(project_id)
        if not project_context or not project_context.config or not project_context.config.sources:
            raise ValueError(f"Project '{project_id}' not found")
        jira_sources = project_context.config.sources.jira or {}
        if source_name not in jira_sources:
            raise ValueError(
                f"Jira source '{source_name}' not found in project '{project_id}'"
            )
        return jira_sources[source_name], project_id

    if not pipeline.project_manager:
        raise ValueError("Project id is required when project manager is unavailable")

    for candidate_project_id in pipeline.project_manager.list_project_ids():
        project_context = pipeline.project_manager.get_project_context(
            candidate_project_id
        )
        if not project_context or not project_context.config:
            continue
        jira_sources = project_context.config.sources.jira or {}
        if source_name in jira_sources:
            return jira_sources[source_name], candidate_project_id

    raise ValueError(f"Jira source '{source_name}' not found in any project")
