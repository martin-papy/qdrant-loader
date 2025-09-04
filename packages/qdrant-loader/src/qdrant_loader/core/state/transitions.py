from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from qdrant_loader.core.document import Document
from qdrant_loader.core.state.models import DocumentStateRecord, IngestionHistory

AsyncSessionFactory = Callable[[], Awaitable[Any]]


async def update_last_ingestion(
    session_factory: AsyncSessionFactory,
    *,
    source_type: str,
    source: str,
    status: str,
    error_message: str | None,
    document_count: int,
    project_id: str | None,
) -> None:
    async with session_factory() as session:  # type: ignore
        now = datetime.now(UTC)
        query = (
            select(IngestionHistory)
            .filter(IngestionHistory.source_type == source_type)
            .filter(IngestionHistory.source == source)
        )
        if project_id is not None:
            query = query.filter(IngestionHistory.project_id == project_id)
        result = await session.execute(query)
        ingestion = result.scalar_one_or_none()
        if ingestion:
            ingestion.last_successful_ingestion = (
                now if status == "SUCCESS" else ingestion.last_successful_ingestion
            )  # type: ignore
            ingestion.status = status  # type: ignore
            ingestion.document_count = (
                document_count if document_count else ingestion.document_count
            )  # type: ignore
            ingestion.updated_at = now  # type: ignore
            ingestion.error_message = error_message  # type: ignore
        else:
            ingestion = IngestionHistory(
                project_id=project_id,
                source_type=source_type,
                source=source,
                last_successful_ingestion=now,
                status=status,
                document_count=document_count,
                error_message=error_message,
                created_at=now,
                updated_at=now,
            )
            session.add(ingestion)
        await session.commit()


async def get_last_ingestion(
    session_factory: AsyncSessionFactory,
    *,
    source_type: str,
    source: str,
    project_id: str | None,
) -> IngestionHistory | None:
    async with session_factory() as session:  # type: ignore
        query = (
            select(IngestionHistory)
            .filter(IngestionHistory.source_type == source_type)
            .filter(IngestionHistory.source == source)
        )
        if project_id is not None:
            query = query.filter(IngestionHistory.project_id == project_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()


async def mark_document_deleted(
    session_factory: AsyncSessionFactory,
    *,
    source_type: str,
    source: str,
    document_id: str,
    project_id: str | None,
) -> None:
    async with session_factory() as session:  # type: ignore
        now = datetime.now(UTC)
        query = select(DocumentStateRecord).filter(
            DocumentStateRecord.source_type == source_type,
            DocumentStateRecord.source == source,
            DocumentStateRecord.document_id == document_id,
        )
        if project_id is not None:
            query = query.filter(DocumentStateRecord.project_id == project_id)
        result = await session.execute(query)
        state = result.scalar_one_or_none()
        if state:
            state.is_deleted = True  # type: ignore
            state.updated_at = now  # type: ignore
            await session.commit()


async def get_document_state_record(
    session_factory: AsyncSessionFactory,
    *,
    source_type: str,
    source: str,
    document_id: str,
    project_id: str | None,
) -> DocumentStateRecord | None:
    async with session_factory() as session:  # type: ignore
        query = select(DocumentStateRecord).filter(
            DocumentStateRecord.source_type == source_type,
            DocumentStateRecord.source == source,
            DocumentStateRecord.document_id == document_id,
        )
        if project_id is not None:
            query = query.filter(DocumentStateRecord.project_id == project_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()


async def get_document_state_records(
    session_factory: AsyncSessionFactory,
    *,
    source_type: str,
    source: str,
    since: datetime | None,
) -> list[DocumentStateRecord]:
    async with session_factory() as session:  # type: ignore
        query = select(DocumentStateRecord).filter(
            DocumentStateRecord.source_type == source,
        )
        query = select(DocumentStateRecord).filter(
            DocumentStateRecord.source_type == source_type,
            DocumentStateRecord.source == source,
        )
        if since:
            query = query.filter(DocumentStateRecord.updated_at >= since)
        result = await session.execute(query)
        return list(result.scalars().all())


async def update_document_state(
    session_factory: AsyncSessionFactory,
    *,
    document: Document,
    project_id: str | None,
) -> DocumentStateRecord:
    async with session_factory() as session:  # type: ignore
        query = select(DocumentStateRecord).filter(
            DocumentStateRecord.source_type == document.source_type,
            DocumentStateRecord.source == document.source,
            DocumentStateRecord.document_id == document.id,
        )
        if project_id is not None:
            query = query.filter(DocumentStateRecord.project_id == project_id)
        result = await session.execute(query)
        document_state_record = result.scalar_one_or_none()

        now = datetime.now(UTC)

        metadata = document.metadata
        conversion_method = metadata.get("conversion_method")
        is_converted = conversion_method is not None
        conversion_failed = metadata.get("conversion_failed", False)

        is_attachment = metadata.get("is_attachment", False)
        parent_document_id = metadata.get("parent_document_id")
        attachment_id = metadata.get("attachment_id")

        if document_state_record:
            document_state_record.title = document.title  # type: ignore
            document_state_record.content_hash = document.content_hash  # type: ignore
            document_state_record.is_deleted = False  # type: ignore
            document_state_record.updated_at = now  # type: ignore

            document_state_record.is_converted = is_converted  # type: ignore
            document_state_record.conversion_method = conversion_method  # type: ignore
            document_state_record.original_file_type = metadata.get("original_file_type")  # type: ignore
            document_state_record.original_filename = metadata.get("original_filename")  # type: ignore
            document_state_record.file_size = metadata.get("file_size")  # type: ignore
            document_state_record.conversion_failed = conversion_failed  # type: ignore
            document_state_record.conversion_error = metadata.get("conversion_error")  # type: ignore
            document_state_record.conversion_time = metadata.get("conversion_time")  # type: ignore

            document_state_record.is_attachment = is_attachment  # type: ignore
            document_state_record.parent_document_id = parent_document_id  # type: ignore
            document_state_record.attachment_id = attachment_id  # type: ignore
            document_state_record.attachment_filename = metadata.get("attachment_filename")  # type: ignore
            document_state_record.attachment_mime_type = metadata.get("attachment_mime_type")  # type: ignore
            document_state_record.attachment_download_url = metadata.get("attachment_download_url")  # type: ignore
            document_state_record.attachment_author = metadata.get("attachment_author")  # type: ignore

            attachment_created_str = metadata.get("attachment_created_at")
            if attachment_created_str:
                try:
                    if isinstance(attachment_created_str, str):
                        document_state_record.attachment_created_at = (
                            datetime.fromisoformat(
                                attachment_created_str.replace("Z", "+00:00")
                            )
                        )  # type: ignore
                    elif isinstance(attachment_created_str, datetime):
                        document_state_record.attachment_created_at = attachment_created_str  # type: ignore
                except (ValueError, TypeError):
                    document_state_record.attachment_created_at = None  # type: ignore
        else:
            attachment_created_at = None
            attachment_created_str = metadata.get("attachment_created_at")
            if attachment_created_str:
                try:
                    if isinstance(attachment_created_str, str):
                        attachment_created_at = datetime.fromisoformat(
                            attachment_created_str.replace("Z", "+00:00")
                        )
                    elif isinstance(attachment_created_str, datetime):
                        attachment_created_at = attachment_created_str
                except (ValueError, TypeError):
                    attachment_created_at = None

            document_state_record = DocumentStateRecord(
                project_id=project_id,
                document_id=document.id,
                source_type=document.source_type,
                source=document.source,
                url=document.url,
                title=document.title,
                content_hash=document.content_hash,
                is_deleted=False,
                created_at=now,
                updated_at=now,
                is_converted=is_converted,
                conversion_method=conversion_method,
                original_file_type=metadata.get("original_file_type"),
                original_filename=metadata.get("original_filename"),
                file_size=metadata.get("file_size"),
                conversion_failed=conversion_failed,
                conversion_error=metadata.get("conversion_error"),
                conversion_time=metadata.get("conversion_time"),
                is_attachment=is_attachment,
                parent_document_id=parent_document_id,
                attachment_id=attachment_id,
                attachment_filename=metadata.get("attachment_filename"),
                attachment_mime_type=metadata.get("attachment_mime_type"),
                attachment_download_url=metadata.get("attachment_download_url"),
                attachment_author=metadata.get("attachment_author"),
                attachment_created_at=attachment_created_at,
            )
            session.add(document_state_record)

        await session.commit()
        return document_state_record


async def update_conversion_metrics(
    session_factory: AsyncSessionFactory,
    *,
    source_type: str,
    source: str,
    converted_files_count: int,
    conversion_failures_count: int,
    attachments_processed_count: int,
    total_conversion_time: float,
) -> None:
    async with session_factory() as session:  # type: ignore
        result = await session.execute(
            select(IngestionHistory).filter_by(source_type=source_type, source=source)
        )
        ingestion = result.scalar_one_or_none()
        if ingestion:
            ingestion.converted_files_count = (
                ingestion.converted_files_count or 0
            ) + converted_files_count  # type: ignore
            ingestion.conversion_failures_count = (
                ingestion.conversion_failures_count or 0
            ) + conversion_failures_count  # type: ignore
            ingestion.attachments_processed_count = (
                ingestion.attachments_processed_count or 0
            ) + attachments_processed_count  # type: ignore
            ingestion.total_conversion_time = (
                ingestion.total_conversion_time or 0.0
            ) + total_conversion_time  # type: ignore
            ingestion.updated_at = datetime.now(UTC)  # type: ignore
        else:
            now = datetime.now(UTC)
            ingestion = IngestionHistory(
                source_type=source_type,
                source=source,
                last_successful_ingestion=now,
                status="SUCCESS",
                document_count=0,
                converted_files_count=converted_files_count,
                conversion_failures_count=conversion_failures_count,
                attachments_processed_count=attachments_processed_count,
                total_conversion_time=total_conversion_time,
                created_at=now,
                updated_at=now,
            )
            session.add(ingestion)
        await session.commit()


async def get_conversion_metrics(
    session_factory: AsyncSessionFactory,
    *,
    source_type: str,
    source: str,
) -> dict[str, int | float]:
    async with session_factory() as session:  # type: ignore
        result = await session.execute(
            select(IngestionHistory).filter_by(source_type=source_type, source=source)
        )
        ingestion = result.scalar_one_or_none()
        if ingestion:
            converted_files: int | None = ingestion.converted_files_count  # type: ignore
            conversion_failures: int | None = ingestion.conversion_failures_count  # type: ignore
            attachments_processed: int | None = ingestion.attachments_processed_count  # type: ignore
            total_time: float | None = ingestion.total_conversion_time  # type: ignore
            return {
                "converted_files_count": (
                    converted_files if converted_files is not None else 0
                ),
                "conversion_failures_count": (
                    conversion_failures if conversion_failures is not None else 0
                ),
                "attachments_processed_count": (
                    attachments_processed if attachments_processed is not None else 0
                ),
                "total_conversion_time": total_time if total_time is not None else 0.0,
            }
        return {
            "converted_files_count": 0,
            "conversion_failures_count": 0,
            "attachments_processed_count": 0,
            "total_conversion_time": 0.0,
        }


async def get_attachment_documents(
    session_factory: AsyncSessionFactory,
    *,
    parent_document_id: str,
) -> list[DocumentStateRecord]:
    async with session_factory() as session:  # type: ignore
        result = await session.execute(
            select(DocumentStateRecord).filter(
                DocumentStateRecord.parent_document_id == parent_document_id,
                DocumentStateRecord.is_attachment.is_(True),
                DocumentStateRecord.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())


async def get_converted_documents(
    session_factory: AsyncSessionFactory,
    *,
    source_type: str,
    source: str,
    conversion_method: str | None,
) -> list[DocumentStateRecord]:
    async with session_factory() as session:  # type: ignore
        query = select(DocumentStateRecord).filter(
            DocumentStateRecord.source_type == source_type,
            DocumentStateRecord.source == source,
            DocumentStateRecord.is_converted.is_(True),
            DocumentStateRecord.is_deleted.is_(False),
        )
        if conversion_method:
            query = query.filter(
                DocumentStateRecord.conversion_method == conversion_method
            )
        result = await session.execute(query)
        return list(result.scalars().all())
