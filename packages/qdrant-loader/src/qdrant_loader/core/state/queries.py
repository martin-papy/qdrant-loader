from __future__ import annotations

from sqlalchemy import select

from qdrant_loader.core.state.models import DocumentStateRecord, IngestionHistory


def select_ingestion_history(
    source_type: str, source: str, project_id: str | None = None
):
    q = select(IngestionHistory).filter_by(source_type=source_type, source=source)
    if project_id is not None:
        q = q.filter_by(project_id=project_id)
    return q


def select_last_ingestion(source_type: str, source: str, project_id: str | None = None):
    q = select(IngestionHistory).filter(
        IngestionHistory.source_type == source_type,
        IngestionHistory.source == source,
    )
    if project_id is not None:
        q = q.filter(IngestionHistory.project_id == project_id)
    return q.order_by(IngestionHistory.last_successful_ingestion.desc())


def select_document_state(
    source_type: str,
    source: str,
    document_id: str | None = None,
    project_id: str | None = None,
):
    conditions = [
        DocumentStateRecord.source_type == source_type,
        DocumentStateRecord.source == source,
    ]
    if document_id is not None:
        conditions.append(DocumentStateRecord.document_id == document_id)
    q = select(DocumentStateRecord).filter(*conditions)
    if project_id is not None:
        q = q.filter(DocumentStateRecord.project_id == project_id)
    return q
