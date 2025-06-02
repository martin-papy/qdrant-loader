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
            self.logger.debug("StateManager initialized successfully")
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
        project_id: str | None = None,
    ) -> None:
        """Update and get the last successful ingestion time for a source."""
        self.logger.debug(
            f"Updating last ingestion for {source_type}:{source} (project: {project_id})"
        )
        try:
            async with self._session_factory() as session:  # type: ignore
                self.logger.debug(
                    f"Created database session for {source_type}:{source}"
                )
                now = datetime.now(UTC)
                self.logger.debug(
                    f"Executing query to find ingestion history for {source_type}:{source}"
                )

                # Build query with optional project filter
                query = select(IngestionHistory).filter_by(
                    source_type=source_type, source=source
                )
                if project_id is not None:
                    query = query.filter_by(project_id=project_id)

                result = await session.execute(query)
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

                self.logger.debug(f"Committing changes for {source_type}:{source}")
                await session.commit()
                self.logger.debug(
                    f"Successfully committed changes for {source_type}:{source}"
                )

                self.logger.debug(
                    "Ingestion history updated",
                    extra={
                        "project_id": project_id,
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
        self, source_type: str, source: str, project_id: str | None = None
    ) -> IngestionHistory | None:
        """Get the last ingestion record for a source."""
        self.logger.debug(
            f"Getting last ingestion for {source_type}:{source} (project: {project_id})"
        )
        try:
            async with self._session_factory() as session:  # type: ignore
                self.logger.debug(
                    f"Created database session for {source_type}:{source}"
                )
                self.logger.debug(
                    f"Executing query to find last ingestion for {source_type}:{source}"
                )

                # Build query with optional project filter
                query = select(IngestionHistory).filter(
                    IngestionHistory.source_type == source_type,
                    IngestionHistory.source == source,
                )
                if project_id is not None:
                    query = query.filter(IngestionHistory.project_id == project_id)

                query = query.order_by(
                    IngestionHistory.last_successful_ingestion.desc()
                )
                result = await session.execute(query)
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
        self,
        source_type: str,
        source: str,
        document_id: str,
        project_id: str | None = None,
    ) -> None:
        """Mark a document as deleted."""
        self.logger.debug(
            f"Marking document as deleted: {source_type}:{source}:{document_id} (project: {project_id})"
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
                        "project_id": project_id,
                    },
                )
                self.logger.debug(
                    f"Executing query to find document {source_type}:{source}:{document_id}"
                )

                # Build query with optional project filter
                query = select(DocumentStateRecord).filter(
                    DocumentStateRecord.source_type == source_type,
                    DocumentStateRecord.source == source,
                    DocumentStateRecord.document_id == document_id,
                )
                if project_id is not None:
                    query = query.filter(DocumentStateRecord.project_id == project_id)

                result = await session.execute(query)
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
                            "project_id": project_id,
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
        self,
        source_type: str,
        source: str,
        document_id: str,
        project_id: str | None = None,
    ) -> DocumentStateRecord | None:
        """Get the state of a document."""
        self.logger.debug(
            f"Getting document state for {source_type}:{source}:{document_id} (project: {project_id})"
        )
        try:
            async with self._session_factory() as session:  # type: ignore
                self.logger.debug(
                    f"Created database session for {source_type}:{source}:{document_id}"
                )
                self.logger.debug(
                    f"Executing query to find document state for {source_type}:{source}:{document_id}"
                )

                # Build query with optional project filter
                query = select(DocumentStateRecord).filter(
                    DocumentStateRecord.source_type == source_type,
                    DocumentStateRecord.source == source,
                    DocumentStateRecord.document_id == document_id,
                )
                if project_id is not None:
                    query = query.filter(DocumentStateRecord.project_id == project_id)

                result = await session.execute(query)
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

    async def update_document_state(
        self, document: Document, project_id: str | None = None
    ) -> DocumentStateRecord:
        """Update the state of a document."""
        if not self._initialized:
            raise RuntimeError("StateManager not initialized. Call initialize() first.")

        self.logger.debug(
            f"Updating document state for {document.source_type}:{document.source}:{document.id} (project: {project_id})"
        )
        try:
            async with self._session_factory() as session:  # type: ignore
                self.logger.debug(
                    f"Created database session for {document.source_type}:{document.source}:{document.id}"
                )
                self.logger.debug(
                    f"Executing query to find document state for {document.source_type}:{document.source}:{document.id}"
                )

                # Build query with optional project filter
                query = select(DocumentStateRecord).filter(
                    DocumentStateRecord.source_type == document.source_type,
                    DocumentStateRecord.source == document.source,
                    DocumentStateRecord.document_id == document.id,
                )
                if project_id is not None:
                    query = query.filter(DocumentStateRecord.project_id == project_id)

                result = await session.execute(query)
                document_state_record = result.scalar_one_or_none()
                self.logger.debug(
                    f"Query result: {'Found' if document_state_record else 'Not found'} document state for {document.source_type}:{document.source}:{document.id}"
                )

                now = datetime.now(UTC)

                # Extract file conversion metadata from document
                metadata = document.metadata
                conversion_method = metadata.get("conversion_method")
                is_converted = conversion_method is not None
                conversion_failed = metadata.get("conversion_failed", False)

                # Extract attachment metadata
                is_attachment = metadata.get("is_attachment", False)
                parent_document_id = metadata.get("parent_document_id")
                attachment_id = metadata.get("attachment_id")

                if document_state_record:
                    # Update existing record
                    self.logger.debug(
                        f"Updating existing document state for {document.source_type}:{document.source}:{document.id}"
                    )
                    document_state_record.title = document.title  # type: ignore
                    document_state_record.content_hash = document.content_hash  # type: ignore
                    document_state_record.is_deleted = False  # type: ignore
                    document_state_record.updated_at = now  # type: ignore

                    # Update file conversion metadata
                    document_state_record.is_converted = is_converted  # type: ignore
                    document_state_record.conversion_method = conversion_method  # type: ignore
                    document_state_record.original_file_type = metadata.get("original_file_type")  # type: ignore
                    document_state_record.original_filename = metadata.get("original_filename")  # type: ignore
                    document_state_record.file_size = metadata.get("file_size")  # type: ignore
                    document_state_record.conversion_failed = conversion_failed  # type: ignore
                    document_state_record.conversion_error = metadata.get("conversion_error")  # type: ignore
                    document_state_record.conversion_time = metadata.get("conversion_time")  # type: ignore

                    # Update attachment metadata
                    document_state_record.is_attachment = is_attachment  # type: ignore
                    document_state_record.parent_document_id = parent_document_id  # type: ignore
                    document_state_record.attachment_id = attachment_id  # type: ignore
                    document_state_record.attachment_filename = metadata.get("attachment_filename")  # type: ignore
                    document_state_record.attachment_mime_type = metadata.get("attachment_mime_type")  # type: ignore
                    document_state_record.attachment_download_url = metadata.get("attachment_download_url")  # type: ignore
                    document_state_record.attachment_author = metadata.get("attachment_author")  # type: ignore

                    # Handle attachment creation date
                    attachment_created_str = metadata.get("attachment_created_at")
                    if attachment_created_str:
                        try:
                            if isinstance(attachment_created_str, str):
                                document_state_record.attachment_created_at = datetime.fromisoformat(attachment_created_str.replace("Z", "+00:00"))  # type: ignore
                            elif isinstance(attachment_created_str, datetime):
                                document_state_record.attachment_created_at = attachment_created_str  # type: ignore
                        except (ValueError, TypeError) as e:
                            self.logger.warning(
                                f"Failed to parse attachment_created_at: {e}"
                            )
                            document_state_record.attachment_created_at = None  # type: ignore
                else:
                    # Create new record
                    self.logger.debug(
                        f"Creating new document state for {document.source_type}:{document.source}:{document.id}"
                    )

                    # Handle attachment creation date for new records
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
                        except (ValueError, TypeError) as e:
                            self.logger.warning(
                                f"Failed to parse attachment_created_at: {e}"
                            )

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
                        # File conversion metadata
                        is_converted=is_converted,
                        conversion_method=conversion_method,
                        original_file_type=metadata.get("original_file_type"),
                        original_filename=metadata.get("original_filename"),
                        file_size=metadata.get("file_size"),
                        conversion_failed=conversion_failed,
                        conversion_error=metadata.get("conversion_error"),
                        conversion_time=metadata.get("conversion_time"),
                        # Attachment metadata
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
                        "project_id": project_id,
                        "document_id": document_state_record.document_id,
                        "content_hash": document_state_record.content_hash,
                        "updated_at": document_state_record.updated_at,
                        "is_converted": document_state_record.is_converted,
                        "is_attachment": document_state_record.is_attachment,
                        "conversion_method": document_state_record.conversion_method,
                    },
                )
                return document_state_record
        except Exception as e:
            self.logger.error(
                "Failed to update document state",
                extra={
                    "project_id": project_id,
                    "document_id": document.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def update_conversion_metrics(
        self,
        source_type: str,
        source: str,
        converted_files_count: int = 0,
        conversion_failures_count: int = 0,
        attachments_processed_count: int = 0,
        total_conversion_time: float = 0.0,
    ) -> None:
        """Update file conversion metrics for a source."""
        self.logger.debug(f"Updating conversion metrics for {source_type}:{source}")
        try:
            async with self._session_factory() as session:  # type: ignore
                result = await session.execute(
                    select(IngestionHistory).filter_by(
                        source_type=source_type, source=source
                    )
                )
                ingestion = result.scalar_one_or_none()

                if ingestion:
                    # Update existing metrics
                    ingestion.converted_files_count = (ingestion.converted_files_count or 0) + converted_files_count  # type: ignore
                    ingestion.conversion_failures_count = (ingestion.conversion_failures_count or 0) + conversion_failures_count  # type: ignore
                    ingestion.attachments_processed_count = (ingestion.attachments_processed_count or 0) + attachments_processed_count  # type: ignore
                    ingestion.total_conversion_time = (ingestion.total_conversion_time or 0.0) + total_conversion_time  # type: ignore
                    ingestion.updated_at = datetime.now(UTC)  # type: ignore
                else:
                    # Create new record with conversion metrics
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
                self.logger.debug(
                    "Conversion metrics updated",
                    extra={
                        "source_type": source_type,
                        "source": source,
                        "converted_files": ingestion.converted_files_count,
                        "conversion_failures": ingestion.conversion_failures_count,
                        "attachments_processed": ingestion.attachments_processed_count,
                        "total_conversion_time": ingestion.total_conversion_time,
                    },
                )
        except Exception as e:
            self.logger.error(
                f"Error updating conversion metrics for {source_type}:{source}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_conversion_metrics(
        self, source_type: str, source: str
    ) -> dict[str, int | float]:
        """Get file conversion metrics for a source."""
        self.logger.debug(f"Getting conversion metrics for {source_type}:{source}")
        try:
            async with self._session_factory() as session:  # type: ignore
                result = await session.execute(
                    select(IngestionHistory).filter_by(
                        source_type=source_type, source=source
                    )
                )
                ingestion = result.scalar_one_or_none()

                if ingestion:
                    # Access the actual values from the SQLAlchemy model instance
                    converted_files: int | None = ingestion.converted_files_count  # type: ignore
                    conversion_failures: int | None = ingestion.conversion_failures_count  # type: ignore
                    attachments_processed: int | None = ingestion.attachments_processed_count  # type: ignore
                    total_time: float | None = ingestion.total_conversion_time  # type: ignore

                    return {
                        "converted_files_count": (
                            converted_files if converted_files is not None else 0
                        ),
                        "conversion_failures_count": (
                            conversion_failures
                            if conversion_failures is not None
                            else 0
                        ),
                        "attachments_processed_count": (
                            attachments_processed
                            if attachments_processed is not None
                            else 0
                        ),
                        "total_conversion_time": (
                            total_time if total_time is not None else 0.0
                        ),
                    }
                else:
                    return {
                        "converted_files_count": 0,
                        "conversion_failures_count": 0,
                        "attachments_processed_count": 0,
                        "total_conversion_time": 0.0,
                    }
        except Exception as e:
            self.logger.error(
                f"Error getting conversion metrics for {source_type}:{source}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_attachment_documents(
        self, parent_document_id: str
    ) -> list[DocumentStateRecord]:
        """Get all attachment documents for a parent document."""
        self.logger.debug(
            f"Getting attachment documents for parent {parent_document_id}"
        )
        try:
            async with self._session_factory() as session:  # type: ignore
                result = await session.execute(
                    select(DocumentStateRecord).filter(
                        DocumentStateRecord.parent_document_id == parent_document_id,
                        DocumentStateRecord.is_attachment == True,
                        DocumentStateRecord.is_deleted == False,
                    )
                )
                attachments = list(result.scalars().all())
                self.logger.debug(
                    f"Found {len(attachments)} attachments for parent {parent_document_id}"
                )
                return attachments
        except Exception as e:
            self.logger.error(
                f"Error getting attachment documents for {parent_document_id}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_converted_documents(
        self, source_type: str, source: str, conversion_method: str | None = None
    ) -> list[DocumentStateRecord]:
        """Get all converted documents for a source, optionally filtered by conversion method."""
        self.logger.debug(f"Getting converted documents for {source_type}:{source}")
        try:
            async with self._session_factory() as session:  # type: ignore
                query = select(DocumentStateRecord).filter(
                    DocumentStateRecord.source_type == source_type,
                    DocumentStateRecord.source == source,
                    DocumentStateRecord.is_converted == True,
                    DocumentStateRecord.is_deleted == False,
                )
                if conversion_method:
                    query = query.filter(
                        DocumentStateRecord.conversion_method == conversion_method
                    )

                result = await session.execute(query)
                documents = list(result.scalars().all())
                self.logger.debug(
                    f"Found {len(documents)} converted documents for {source_type}:{source}"
                )
                return documents
        except Exception as e:
            self.logger.error(
                f"Error getting converted documents for {source_type}:{source}: {str(e)}",
                exc_info=True,
            )
            raise

    async def close(self):
        """Close all database connections."""
        if hasattr(self, "_engine") and self._engine is not None:
            self.logger.debug("Closing database connections")
            await self._engine.dispose()
            self.logger.debug("Database connections closed")
