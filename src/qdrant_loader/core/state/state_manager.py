"""
State management service for tracking document ingestion state.
"""

from datetime import UTC, datetime
import os
import sqlite3

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from structlog import get_logger

from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.config.state import IngestionStatus, StateManagementConfig
from qdrant_loader.core.document import Document
from qdrant_loader.utils.logging import LoggingConfig
from qdrant_loader.core.state.models import Base, DocumentStateRecord, IngestionHistory
from qdrant_loader.core.state.exceptions import DatabaseError

logger = LoggingConfig.get_logger(__name__)


class StateManager:
    """Manages state for document ingestion."""

    def __init__(self, config: StateManagementConfig):
        """Initialize the state manager with configuration."""
        self.config = config
        self._initialized = False
        self._engine = None
        self._session_factory = None
        self.logger = LoggingConfig.get_logger(__name__)

    async def __aenter__(self):
        """Async context manager entry."""
        if not self._initialized:
            raise ValueError("StateManager not initialized. Call initialize() first.")
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.dispose()

    async def initialize(self):
        """Initialize the database schema and connection."""
        if self._initialized:
            return

        db_url = self.config.database_path
        if not db_url.startswith("sqlite:///"):
            db_url = f"sqlite:///{db_url}"

        # Extract the actual file path from the URL
        db_file = db_url.replace("sqlite:///", "")

        # Skip file permission check for in-memory database
        if db_file != ":memory:":
            # Check if the database file exists and is writable
            if os.path.exists(db_file) and not os.access(db_file, os.W_OK):
                raise DatabaseError(
                    f"Database file '{db_file}' exists but is not writable. "
                    "Please check file permissions."
                )
            # If file doesn't exist, check if directory is writable
            elif not os.path.exists(db_file):
                db_dir = os.path.dirname(db_file) or "."
                if not os.access(db_dir, os.W_OK):
                    raise DatabaseError(
                        f"Cannot create database file in '{db_dir}'. "
                        "Directory is not writable. Please check directory permissions."
                    )

        # Create async engine for async operations
        engine_args = {}
        if not db_url == "sqlite:///:memory:":
            engine_args.update(
                {
                    "pool_size": self.config.connection_pool["size"],
                    "pool_timeout": self.config.connection_pool["timeout"],
                    "pool_recycle": 3600,  # Recycle connections after 1 hour
                    "pool_pre_ping": True,  # Enable connection health checks
                }
            )

        try:
            self._engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", **engine_args)

            # Create async session factory
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                expire_on_commit=False,  # Prevent expired objects after commit
                autoflush=False,  # Disable autoflush for better control
            )

            # Initialize schema
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            self._initialized = True
            self.logger.info("StateManager initialized successfully")
        except sqlite3.OperationalError as e:
            # Handle specific SQLite errors
            if "readonly database" in str(e).lower():
                raise DatabaseError(
                    f"Cannot write to database '{db_file}'. Database is read-only."
                ) from e
            raise DatabaseError(f"Failed to initialize database: {e}") from e
        except Exception as e:
            raise DatabaseError(f"Unexpected error initializing database: {e}") from e

    async def dispose(self):
        """Clean up resources."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            self._initialized = False
            self.logger.info("StateManager resources disposed")

    async def update_last_ingestion(
        self,
        source_type: str,
        source: str,
        status: str = IngestionStatus.SUCCESS,
        error_message: str | None = None,
        document_count: int = 0,
    ) -> None:
        """Update and get the last successful ingestion time for a source."""
        async with self._session_factory() as session:  # type: ignore
            now = datetime.now(UTC)
            result = await session.execute(
                select(IngestionHistory).filter_by(source_type=source_type, source=source)
            )
            ingestion = result.scalar_one_or_none()

            if ingestion:
                ingestion.last_successful_ingestion = now if status == IngestionStatus.SUCCESS else ingestion.last_successful_ingestion  # type: ignore
                ingestion.status = status  # type: ignore
                ingestion.document_count = document_count if document_count else ingestion.document_count  # type: ignore
                ingestion.updated_at = now  # type: ignore
                ingestion.error_message = error_message  # type: ignore
            else:
                ingestion = IngestionHistory(
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
            self.logger.debug(
                "Ingestion history updated",
                extra={
                    "source_type": ingestion.source_type,
                    "source": ingestion.source,
                    "status": ingestion.status,
                    "document_count": ingestion.document_count,
                },
            )

    async def get_last_ingestion(self, source_type: str, source: str) -> IngestionHistory | None:
        """Get the last ingestion record for a source."""
        async with self._session_factory() as session:  # type: ignore
            result = await session.execute(
                select(IngestionHistory)
                .filter(
                    IngestionHistory.source_type == source_type,
                    IngestionHistory.source == source,
                )
                .order_by(IngestionHistory.last_successful_ingestion.desc())
            )
            return result.scalar_one_or_none()

    async def mark_document_deleted(self, source_type: str, source: str, document_id: str) -> None:
        """Mark a document as deleted."""
        async with self._session_factory() as session:  # type: ignore
            now = datetime.now(UTC)
            self.logger.debug(
                "Searching for document to be deleted.",
                extra={
                    "document_id": document_id,
                    "source_type": source_type,
                    "source": source,
                },
            )
            result = await session.execute(
                select(DocumentStateRecord).filter(
                    DocumentStateRecord.source_type == source_type,
                    DocumentStateRecord.source == source,
                    DocumentStateRecord.document_id == document_id,
                )
            )
            state = result.scalar_one_or_none()

            if state:
                state.is_deleted = True  # type: ignore
                state.updated_at = now  # type: ignore
                await session.commit()
                self.logger.debug(
                    "Document marked as deleted",
                    extra={
                        "document_id": document_id,
                        "source_type": source_type,
                        "source": source,
                    },
                )

    async def get_document_state_record(
        self, source_type: str, source: str, document_id: str
    ) -> DocumentStateRecord | None:
        """Get the state of a document."""
        async with self._session_factory() as session:  # type: ignore
            result = await session.execute(
                select(DocumentStateRecord).filter(
                    DocumentStateRecord.source_type == source_type,
                    DocumentStateRecord.source == source,
                    DocumentStateRecord.document_id == document_id,
                )
            )
            return result.scalar_one_or_none()

    async def get_document_state_records(
        self, source_config: SourceConfig, since: datetime | None = None
    ) -> list[DocumentStateRecord]:
        """Get all document states for a source, optionally filtered by date."""
        async with self._session_factory() as session:  # type: ignore
            query = select(DocumentStateRecord).filter(
                DocumentStateRecord.source_type == source_config.source_type,
                DocumentStateRecord.source == source_config.source,
            )
            if since:
                query = query.filter(DocumentStateRecord.updated_at >= since)
            result = await session.execute(query)
            return list(result.scalars().all())

    async def update_document_state(self, document: Document) -> DocumentStateRecord:
        """Update the state of a document."""
        if not self._initialized:
            raise RuntimeError("StateManager not initialized. Call initialize() first.")

        async with self._session_factory() as session:  # type: ignore
            try:
                result = await session.execute(
                    select(DocumentStateRecord).filter(
                        DocumentStateRecord.source_type == document.source_type,
                        DocumentStateRecord.source == document.source,
                        DocumentStateRecord.document_id == document.id,
                    )
                )
                document_state_record = result.scalar_one_or_none()

                now = datetime.now(UTC)

                if document_state_record:
                    # Update existing record
                    document_state_record.title = document.title  # type: ignore
                    document_state_record.content_hash = document.content_hash  # type: ignore
                    document_state_record.is_deleted = False  # type: ignore
                    document_state_record.updated_at = now  # type: ignore
                else:
                    # Create new record
                    document_state_record = DocumentStateRecord(
                        document_id=document.id,
                        source_type=document.source_type,
                        source=document.source,
                        url=document.url,
                        title=document.title,
                        content_hash=document.content_hash,
                        is_deleted=False,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(document_state_record)

                await session.commit()

                self.logger.debug(
                    "Document state updated",
                    extra={
                        "document_id": document_state_record.document_id,
                        "content_hash": document_state_record.content_hash,
                        "updated_at": document_state_record.updated_at,
                    },
                )
                return document_state_record

            except Exception as e:
                await session.rollback()
                self.logger.error(
                    "Failed to update document state",
                    extra={
                        "document_id": document.id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                raise

    async def close(self):
        """Close all database connections."""
        if hasattr(self, "_engine") and self._engine is not None:
            await self._engine.dispose()
