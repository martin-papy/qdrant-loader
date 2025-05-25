"""
State management service for tracking document ingestion state.
"""

import os
import sqlite3
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.config.state import IngestionStatus, StateManagementConfig
from qdrant_loader.core.document import Document
from qdrant_loader.core.state.exceptions import DatabaseError
from qdrant_loader.core.state.models import Base, DocumentStateRecord, IngestionHistory
from qdrant_loader.utils.logging import LoggingConfig

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
            self.logger.debug(f"Creating async engine for database: {db_file}")
            self._engine = create_async_engine(
                f"sqlite+aiosqlite:///{db_file}", **engine_args
            )

            # Create async session factory
            self.logger.debug("Creating async session factory")
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                expire_on_commit=False,  # Prevent expired objects after commit
                autoflush=False,  # Disable autoflush for better control
            )

            # Initialize schema
            self.logger.debug("Initializing database schema")
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
            self.logger.debug("Disposing database engine")
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            self._initialized = False
            self.logger.debug("StateManager resources disposed")

    async def update_last_ingestion(
        self,
        source_type: str,
        source: str,
        status: str = IngestionStatus.SUCCESS,
        error_message: str | None = None,
        document_count: int = 0,
    ) -> None:
        """Update and get the last successful ingestion time for a source."""
        self.logger.debug(f"Updating last ingestion for {source_type}:{source}")
        try:
            async with self._session_factory() as session:  # type: ignore
                self.logger.debug(
                    f"Created database session for {source_type}:{source}"
                )
                now = datetime.now(UTC)
                self.logger.debug(
                    f"Executing query to find ingestion history for {source_type}:{source}"
                )
                result = await session.execute(
                    select(IngestionHistory).filter_by(
                        source_type=source_type, source=source
                    )
                )
                ingestion = result.scalar_one_or_none()
                self.logger.debug(
                    f"Query result: {'Found' if ingestion else 'Not found'} ingestion history for {source_type}:{source}"
                )

                if ingestion:
                    self.logger.debug(
                        f"Updating existing ingestion history for {source_type}:{source}"
                    )
                    ingestion.last_successful_ingestion = now if status == IngestionStatus.SUCCESS else ingestion.last_successful_ingestion  # type: ignore
                    ingestion.status = status  # type: ignore
                    ingestion.document_count = document_count if document_count else ingestion.document_count  # type: ignore
                    ingestion.updated_at = now  # type: ignore
                    ingestion.error_message = error_message  # type: ignore
                else:
                    self.logger.debug(
                        f"Creating new ingestion history for {source_type}:{source}"
                    )
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

                self.logger.debug(f"Committing changes for {source_type}:{source}")
                await session.commit()
                self.logger.debug(
                    f"Successfully committed changes for {source_type}:{source}"
                )

                self.logger.debug(
                    "Ingestion history updated",
                    extra={
                        "source_type": ingestion.source_type,
                        "source": ingestion.source,
                        "status": ingestion.status,
                        "document_count": ingestion.document_count,
                    },
                )
        except Exception as e:
            self.logger.error(
                f"Error updating last ingestion for {source_type}:{source}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_last_ingestion(
        self, source_type: str, source: str
    ) -> IngestionHistory | None:
        """Get the last ingestion record for a source."""
        self.logger.debug(f"Getting last ingestion for {source_type}:{source}")
        try:
            async with self._session_factory() as session:  # type: ignore
                self.logger.debug(
                    f"Created database session for {source_type}:{source}"
                )
                self.logger.debug(
                    f"Executing query to find last ingestion for {source_type}:{source}"
                )
                result = await session.execute(
                    select(IngestionHistory)
                    .filter(
                        IngestionHistory.source_type == source_type,
                        IngestionHistory.source == source,
                    )
                    .order_by(IngestionHistory.last_successful_ingestion.desc())
                )
                ingestion = result.scalar_one_or_none()
                self.logger.debug(
                    f"Query result: {'Found' if ingestion else 'Not found'} last ingestion for {source_type}:{source}"
                )
                return ingestion
        except Exception as e:
            self.logger.error(
                f"Error getting last ingestion for {source_type}:{source}: {str(e)}",
                exc_info=True,
            )
            raise

    async def mark_document_deleted(
        self, source_type: str, source: str, document_id: str
    ) -> None:
        """Mark a document as deleted."""
        self.logger.debug(
            f"Marking document as deleted: {source_type}:{source}:{document_id}"
        )
        try:
            async with self._session_factory() as session:  # type: ignore
                self.logger.debug(
                    f"Created database session for {source_type}:{source}:{document_id}"
                )
                now = datetime.now(UTC)
                self.logger.debug(
                    "Searching for document to be deleted.",
                    extra={
                        "document_id": document_id,
                        "source_type": source_type,
                        "source": source,
                    },
                )
                self.logger.debug(
                    f"Executing query to find document {source_type}:{source}:{document_id}"
                )
                result = await session.execute(
                    select(DocumentStateRecord).filter(
                        DocumentStateRecord.source_type == source_type,
                        DocumentStateRecord.source == source,
                        DocumentStateRecord.document_id == document_id,
                    )
                )
                state = result.scalar_one_or_none()
                self.logger.debug(
                    f"Query result: {'Found' if state else 'Not found'} document {source_type}:{source}:{document_id}"
                )

                if state:
                    self.logger.debug(
                        f"Updating document state for {source_type}:{source}:{document_id}"
                    )
                    state.is_deleted = True  # type: ignore
                    state.updated_at = now  # type: ignore
                    self.logger.debug(
                        f"Committing changes for {source_type}:{source}:{document_id}"
                    )
                    await session.commit()
                    self.logger.debug(
                        f"Successfully committed changes for {source_type}:{source}:{document_id}"
                    )
                    self.logger.debug(
                        "Document marked as deleted",
                        extra={
                            "document_id": document_id,
                            "source_type": source_type,
                            "source": source,
                        },
                    )
                else:
                    self.logger.warning(
                        f"Document not found: {source_type}:{source}:{document_id}"
                    )
        except Exception as e:
            self.logger.error(
                f"Error marking document as deleted {source_type}:{source}:{document_id}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_document_state_record(
        self, source_type: str, source: str, document_id: str
    ) -> DocumentStateRecord | None:
        """Get the state of a document."""
        self.logger.debug(
            f"Getting document state for {source_type}:{source}:{document_id}"
        )
        try:
            async with self._session_factory() as session:  # type: ignore
                self.logger.debug(
                    f"Created database session for {source_type}:{source}:{document_id}"
                )
                self.logger.debug(
                    f"Executing query to find document state for {source_type}:{source}:{document_id}"
                )
                result = await session.execute(
                    select(DocumentStateRecord).filter(
                        DocumentStateRecord.source_type == source_type,
                        DocumentStateRecord.source == source,
                        DocumentStateRecord.document_id == document_id,
                    )
                )
                state = result.scalar_one_or_none()
                self.logger.debug(
                    f"Query result: {'Found' if state else 'Not found'} document state for {source_type}:{source}:{document_id}"
                )
                return state
        except Exception as e:
            self.logger.error(
                f"Error getting document state for {source_type}:{source}:{document_id}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_document_state_records(
        self, source_config: SourceConfig, since: datetime | None = None
    ) -> list[DocumentStateRecord]:
        """Get all document states for a source, optionally filtered by date."""
        self.logger.debug(
            f"Getting document state records for {source_config.source_type}:{source_config.source}"
        )
        try:
            async with self._session_factory() as session:  # type: ignore
                self.logger.debug(
                    f"Created database session for {source_config.source_type}:{source_config.source}"
                )
                query = select(DocumentStateRecord).filter(
                    DocumentStateRecord.source_type == source_config.source_type,
                    DocumentStateRecord.source == source_config.source,
                )
                if since:
                    query = query.filter(DocumentStateRecord.updated_at >= since)
                self.logger.debug(
                    f"Executing query for {source_config.source_type}:{source_config.source}"
                )
                result = await session.execute(query)
                self.logger.debug(
                    f"Query executed, getting all records for {source_config.source_type}:{source_config.source}"
                )
                records = list(result.scalars().all())
                self.logger.debug(
                    f"Got {len(records)} records for {source_config.source_type}:{source_config.source}"
                )
                return records
        except Exception as e:
            self.logger.error(
                f"Error getting document state records for {source_config.source_type}:{source_config.source}: {str(e)}",
                exc_info=True,
            )
            raise

    async def update_document_state(self, document: Document) -> DocumentStateRecord:
        """Update the state of a document."""
        if not self._initialized:
            raise RuntimeError("StateManager not initialized. Call initialize() first.")

        self.logger.debug(
            f"Updating document state for {document.source_type}:{document.source}:{document.id}"
        )
        try:
            async with self._session_factory() as session:  # type: ignore
                self.logger.debug(
                    f"Created database session for {document.source_type}:{document.source}:{document.id}"
                )
                self.logger.debug(
                    f"Executing query to find document state for {document.source_type}:{document.source}:{document.id}"
                )
                result = await session.execute(
                    select(DocumentStateRecord).filter(
                        DocumentStateRecord.source_type == document.source_type,
                        DocumentStateRecord.source == document.source,
                        DocumentStateRecord.document_id == document.id,
                    )
                )
                document_state_record = result.scalar_one_or_none()
                self.logger.debug(
                    f"Query result: {'Found' if document_state_record else 'Not found'} document state for {document.source_type}:{document.source}:{document.id}"
                )

                now = datetime.now(UTC)

                if document_state_record:
                    # Update existing record
                    self.logger.debug(
                        f"Updating existing document state for {document.source_type}:{document.source}:{document.id}"
                    )
                    document_state_record.title = document.title  # type: ignore
                    document_state_record.content_hash = document.content_hash  # type: ignore
                    document_state_record.is_deleted = False  # type: ignore
                    document_state_record.updated_at = now  # type: ignore
                else:
                    # Create new record
                    self.logger.debug(
                        f"Creating new document state for {document.source_type}:{document.source}:{document.id}"
                    )
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

                self.logger.debug(
                    f"Committing changes for {document.source_type}:{document.source}:{document.id}"
                )
                await session.commit()
                self.logger.debug(
                    f"Successfully committed changes for {document.source_type}:{document.source}:{document.id}"
                )

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
            self.logger.debug("Closing database connections")
            await self._engine.dispose()
            self.logger.debug("Database connections closed")
