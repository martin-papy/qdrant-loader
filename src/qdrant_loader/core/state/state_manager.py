"""
State management service for tracking document ingestion state.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import and_, create_engine, event, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from qdrant_loader.config.state import StateManagementConfig
from qdrant_loader.core.document import Document

from .exceptions import DatabaseError
from .models import Base, DocumentStateRecord, IngestionHistory

logger = logging.getLogger(__name__)


def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragma for timezone support."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class StateManager:
    """Manages state for document ingestion."""

    def __init__(self, config: StateManagementConfig):
        """Initialize the state manager with configuration."""
        db_url = config.database_path
        if not db_url.startswith("sqlite:///"):
            db_url = f"sqlite:///{db_url}"

        # Create sync engine for migrations and sync operations
        engine_args = {}
        if not db_url == "sqlite:///:memory:":  # Don't use pool settings for in-memory SQLite
            engine_args.update(
                {
                    "pool_size": config.connection_pool["size"],
                    "pool_timeout": config.connection_pool["timeout"],
                }
            )

        self.engine = create_engine(db_url, **engine_args)
        if "sqlite" in db_url:
            event.listen(self.engine, "connect", _set_sqlite_pragma)

        # Create async engine for async operations
        self.async_engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_url.replace('sqlite:///', '')}", **engine_args
        )

        # Create session factories
        self.Session = sessionmaker(bind=self.engine)
        self.AsyncSession = async_sessionmaker(bind=self.async_engine)

        # Create tables
        Base.metadata.create_all(self.engine)

    def update_and_get_last_ingestion(self, source_type: str, source_name: str) -> datetime:
        """Update and get the last successful ingestion time for a source."""
        with self.Session() as session:
            now = datetime.now(UTC)
            ingestion = (
                session.query(IngestionHistory)
                .filter_by(source_type=source_type, source_name=source_name)
                .first()
            )

            if ingestion:
                ingestion.last_successful_ingestion = now  # type: ignore
                ingestion.updated_at = func.now()  # type: ignore
            else:
                ingestion = IngestionHistory(
                    source_type=source_type,
                    source_name=source_name,
                    last_successful_ingestion=now,
                    status="success",
                    created_at=now,
                    updated_at=func.now(),
                )
                session.add(ingestion)

            session.commit()
            return ingestion.last_successful_ingestion  # type: ignore

    def update_and_get_document_state(
        self, source_type: str, source_name: str, document_id: str, last_updated: datetime
    ) -> DocumentStateRecord:
        """Update and get the state of a document."""
        with self.Session() as session:
            now = datetime.now(UTC)

            state = (
                session.query(DocumentStateRecord)
                .filter_by(
                    source_type=source_type, source_name=source_name, document_id=document_id
                )
                .first()
            )

            if state:
                state.last_updated = last_updated  # type: ignore
                state.last_ingested = now  # type: ignore
                state.updated_at = func.now()  # type: ignore
            else:
                state = DocumentStateRecord(
                    source_type=source_type,
                    source_name=source_name,
                    document_id=document_id,
                    last_updated=last_updated,
                    last_ingested=now,
                    created_at=now,
                    updated_at=func.now(),
                )
                session.add(state)

            session.commit()
            session.refresh(state)
            return state

    def mark_document_deleted_sync(
        self, source_type: str, source_name: str, document_id: str
    ) -> None:
        """Mark a document as deleted."""
        with self.Session() as session:
            now = datetime.now(UTC)
            state = (
                session.query(DocumentStateRecord)
                .filter_by(
                    source_type=source_type, source_name=source_name, document_id=document_id
                )
                .first()
            )

            if state:
                state.is_deleted = True  # type: ignore
                state.last_updated = now  # type: ignore
                state.updated_at = func.now()  # type: ignore
                session.commit()

    async def get_document_states(
        self, source_type: str, source_name: str, since: datetime | None
    ) -> list[DocumentStateRecord]:
        """Get all document states for a source, optionally filtered by last update time."""
        async with self.AsyncSession() as session:
            query = select(DocumentStateRecord).filter(
                DocumentStateRecord.source_type == source_type,
                DocumentStateRecord.source_name == source_name,
            )

            if since:
                query = query.filter(DocumentStateRecord.last_updated >= since)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_last_ingestion(
        self, source_type: str, source_name: str
    ) -> IngestionHistory | None:
        """Get the last ingestion record for a source."""
        async with self.AsyncSession() as session:
            result = await session.execute(
                select(IngestionHistory)
                .filter(
                    IngestionHistory.source_type == source_type,
                    IngestionHistory.source_name == source_name,
                )
                .order_by(IngestionHistory.timestamp.desc())
            )
            return result.scalar_one_or_none()

    async def update_ingestion(
        self, source_type: str, source_name: str, status: str, count: int
    ) -> IngestionHistory:
        """Update ingestion history for a source."""
        async with self.AsyncSession() as session:
            history = IngestionHistory(
                source_type=source_type,
                source_name=source_name,
                status=status,
                document_count=count,
                timestamp=datetime.now(UTC),
            )
            session.add(history)
            await session.commit()
            return history

    async def get_document_state(
        self, source_type: str, source_name: str, document_id: str
    ) -> DocumentStateRecord | None:
        """Get the state of a document."""
        async with self.AsyncSession() as session:
            result = await session.execute(
                select(DocumentStateRecord).filter(
                    DocumentStateRecord.source_type == source_type,
                    DocumentStateRecord.source_name == source_name,
                    DocumentStateRecord.document_id == document_id,
                )
            )
            return result.scalar_one_or_none()

    async def update_document_state(self, state: DocumentStateRecord) -> DocumentStateRecord:
        """Update the state of a document."""
        async with self.AsyncSession() as session:
            result = await session.execute(
                select(DocumentStateRecord).filter(
                    DocumentStateRecord.source_type == state.source_type,
                    DocumentStateRecord.source_name == state.source_name,
                    DocumentStateRecord.document_id == state.document_id,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing record
                existing.last_updated = state.last_updated  # type: ignore
                existing.last_ingested = state.last_ingested  # type: ignore
                existing.is_deleted = state.is_deleted  # type: ignore
                existing.updated_at = func.now()  # type: ignore
                state = existing
            else:
                # Create new record
                state.created_at = datetime.now(UTC)  # type: ignore
                state.updated_at = func.now()  # type: ignore
                session.add(state)

            await session.commit()
            return state

    async def mark_document_deleted(
        self, source_type: str, source_name: str, document_id: str
    ) -> DocumentStateRecord:
        """Mark a document as deleted."""
        async with self.AsyncSession() as session:
            result = await session.execute(
                select(DocumentStateRecord).filter(
                    DocumentStateRecord.source_type == source_type,
                    DocumentStateRecord.source_name == source_name,
                    DocumentStateRecord.document_id == document_id,
                )
            )
            state = result.scalar_one_or_none()
            if state:
                state.is_deleted = True  # type: ignore
                state.last_updated = datetime.now(UTC)  # type: ignore
                state.updated_at = func.now()  # type: ignore
                await session.commit()
            return state

    async def get_document_by_url(
        self, source_type: str, source_name: str, url: str
    ) -> Document | None:
        """Get a document by its URL.

        Args:
            source_type: Type of source (e.g., 'confluence', 'public_docs')
            source_name: Name of the source (e.g., base URL)
            url: Document URL

        Returns:
            Document if found, None otherwise
        """
        async with self.AsyncSession() as session:
            try:
                result = await session.execute(
                    select(DocumentStateRecord).where(
                        and_(
                            DocumentStateRecord.source_type == source_type,
                            DocumentStateRecord.source_name == source_name,
                            DocumentStateRecord.url == url,
                        )
                    )
                )
                state = result.scalar_one_or_none()
                if state:
                    return Document(
                        id=state.document_id,
                        content=state.content,
                        source=state.source_name,
                        source_type=state.source_type,
                        metadata={
                            "url": state.url,
                            "title": state.title,
                            "content_hash": state.content_hash,
                            "last_modified": state.last_updated.isoformat(),
                            "version": state.version,
                        },
                    )
                return None
            except SQLAlchemyError as e:
                logger.error("Error getting document by URL: %s", e)
                raise DatabaseError(f"Error getting document by URL: {e}") from e

    async def get_document_by_key(
        self, source_type: str, source_name: str, key: str
    ) -> Document | None:
        """Get a document by its key.

        Args:
            source_type: Type of source (e.g., 'jira')
            source_name: Name of the source (e.g., base URL)
            key: Document key

        Returns:
            Document if found, None otherwise
        """
        async with self.AsyncSession() as session:
            try:
                result = await session.execute(
                    select(DocumentStateRecord).where(
                        and_(
                            DocumentStateRecord.source_type == source_type,
                            DocumentStateRecord.source_name == source_name,
                            DocumentStateRecord.key == key,
                        )
                    )
                )
                state = result.scalar_one_or_none()
                if state:
                    return Document(
                        id=state.document_id,
                        content=state.content,
                        source=state.source_name,
                        source_type=state.source_type,
                        metadata={
                            "key": state.key,
                            "title": state.title,
                            "content_hash": state.content_hash,
                            "last_modified": state.last_updated.isoformat(),
                            "version": state.version,
                        },
                    )
                return None
            except SQLAlchemyError as e:
                logger.error("Error getting document by key: %s", e)
                raise DatabaseError(f"Error getting document by key: {e}") from e
