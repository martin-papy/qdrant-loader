"""
State management service for tracking document ingestion state.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.config.state import IngestionStatus, StateManagementConfig
from qdrant_loader.core.document import Document
from qdrant_loader.core.state import transitions as _transitions
from qdrant_loader.core.state.models import DocumentStateRecord, IngestionHistory
from qdrant_loader.core.state.session import create_tables as _create_tables
from qdrant_loader.core.state.session import dispose_engine as _dispose_engine
from qdrant_loader.core.state.session import (
    initialize_engine_and_session as _init_engine_session,
)
from qdrant_loader.core.state.utils import generate_sqlite_aiosqlite_url as _gen_url
from qdrant_loader.utils.logging import LoggingConfig

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

logger = LoggingConfig.get_logger(__name__)


class StateManager:
    """Manages state for document ingestion."""

    def __init__(self, config: StateManagementConfig):
        """Initialize the state manager with configuration."""
        self.config = config
        self._initialized = False
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self.logger = LoggingConfig.get_logger(__name__)

    @property
    def is_initialized(self) -> bool:
        """Public accessor for initialization state used by callers/tests."""
        return self._initialized

    async def get_session(self) -> "AsyncSession":
        """Return an async session context manager, initializing if needed.

        This method allows callers to use:
            async with await state_manager.get_session() as session:
                ...
        """
        if not self._initialized:
            await self.initialize()
        if self._session_factory is None:
            raise RuntimeError("State manager session factory is not available")
        return self._session_factory()

    async def create_session(self) -> "AsyncSession":
        """Alias for get_session for backward compatibility."""
        return await self.get_session()

    async def __aenter__(self):
        """Async context manager entry."""
        self.logger.debug("=== StateManager.__aenter__() called ===")
        self.logger.debug(f"Current initialization state: {self._initialized}")

        # Initialize if not already initialized
        if not self._initialized:
            self.logger.debug("StateManager not initialized, calling initialize()")
            await self.initialize()
        else:
            self.logger.debug("StateManager already initialized")

        return self

    async def __aexit__(self, exc_type, exc_val, _exc_tb):
        """Async context manager exit."""
        await self.dispose()

    async def initialize(self) -> None:
        """Initialize the database and create tables if they don't exist."""
        if self._initialized:
            self.logger.debug("StateManager already initialized, skipping")
            return

        try:
            self.logger.debug("Starting StateManager initialization")

            # Process database path with enhanced Windows debugging
            db_path_str = self.config.database_path
            self.logger.debug(f"Original database path: {db_path_str}")

            # Handle special databases and generate URL
            database_url = _gen_url(db_path_str)
            self.logger.debug(f"Generated database URL: {database_url}")

            # Create database engine and session factory
            self.logger.debug("Creating database engine and session factory")
            self._engine, self._session_factory = _init_engine_session(self.config)
            self.logger.debug("Engine and session factory created successfully")

            # Create tables
            self.logger.debug("Creating database tables")
            await _create_tables(self._engine)
            self.logger.debug("Database tables created successfully")

            self._initialized = True
            self.logger.debug("StateManager initialization completed successfully")

        except Exception as e:
            self.logger.error(f"StateManager initialization failed: {e}", exc_info=True)
            # Ensure we clean up any partial initialization
            if hasattr(self, "_engine") and self._engine:
                try:
                    await _dispose_engine(self._engine)
                except Exception as cleanup_error:
                    self.logger.error(
                        f"Failed to cleanup engine during error handling: {cleanup_error}"
                    )
            self._initialized = False
            raise

    async def dispose(self):
        """Clean up resources."""
        if self._engine:
            self.logger.debug("Disposing database engine")
            await _dispose_engine(self._engine)
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
            await _transitions.update_last_ingestion(
                self._session_factory,  # type: ignore[arg-type]
                source_type=source_type,
                source=source,
                status=status,
                error_message=error_message,
                document_count=document_count,
                project_id=project_id,
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
            return await _transitions.get_last_ingestion(
                self._session_factory,  # type: ignore[arg-type]
                source_type=source_type,
                source=source,
                project_id=project_id,
            )
        except Exception as e:
            self.logger.error(
                f"Error getting last ingestion for {source_type}:{source}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_project_document_count(self, project_id: str) -> int:
        """Get the count of non-deleted documents for a project.

        Returns 0 on failure to avoid breaking CLI status output.
        """
        try:
            session_factory = getattr(self, "_session_factory", None)
            if session_factory is None:
                ctx = await self.get_session()
            else:
                ctx = (
                    session_factory() if callable(session_factory) else session_factory
                )
            async with ctx as session:  # type: ignore
                result = await session.execute(
                    select(func.count(DocumentStateRecord.id))
                    .filter_by(project_id=project_id)
                    .filter_by(is_deleted=False)
                )
                count = result.scalar() or 0
                return count
        except Exception as e:  # pragma: no cover - fallback path
            self.logger.error(
                f"Error getting project document count for {project_id}: {str(e)}",
                exc_info=True,
            )
            return 0

    async def get_project_latest_ingestion(self, project_id: str) -> str | None:
        """Get the latest ingestion timestamp (ISO) for a project.

        Returns None on failure or when no ingestion exists.
        """
        try:
            session_factory = getattr(self, "_session_factory", None)
            if session_factory is None:
                ctx = await self.get_session()
            else:
                ctx = (
                    session_factory() if callable(session_factory) else session_factory
                )
            async with ctx as session:  # type: ignore
                result = await session.execute(
                    select(IngestionHistory.last_successful_ingestion)
                    .filter_by(project_id=project_id)
                    .order_by(IngestionHistory.last_successful_ingestion.desc())
                    .limit(1)
                )
                timestamp = result.scalar_one_or_none()
                return timestamp.isoformat() if timestamp else None
        except Exception as e:  # pragma: no cover - fallback path
            self.logger.error(
                f"Error getting project latest ingestion for {project_id}: {str(e)}",
                exc_info=True,
            )
            return None

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
            await _transitions.mark_document_deleted(
                self._session_factory,  # type: ignore[arg-type]
                source_type=source_type,
                source=source,
                document_id=document_id,
                project_id=project_id,
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
            return await _transitions.get_document_state_record(
                self._session_factory,  # type: ignore[arg-type]
                source_type=source_type,
                source=source,
                document_id=document_id,
                project_id=project_id,
            )
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
            return await _transitions.get_document_state_records(
                self._session_factory,  # type: ignore[arg-type]
                source_type=source_config.source_type,
                source=source_config.source,
                since=since,
            )
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
            return await _transitions.update_document_state(
                self._session_factory,  # type: ignore[arg-type]
                document=document,
                project_id=project_id,
            )
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
            await _transitions.update_conversion_metrics(
                self._session_factory,  # type: ignore[arg-type]
                source_type=source_type,
                source=source,
                converted_files_count=converted_files_count,
                conversion_failures_count=conversion_failures_count,
                attachments_processed_count=attachments_processed_count,
                total_conversion_time=total_conversion_time,
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
            return await _transitions.get_conversion_metrics(
                self._session_factory,  # type: ignore[arg-type]
                source_type=source_type,
                source=source,
            )
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
            return await _transitions.get_attachment_documents(
                self._session_factory,  # type: ignore[arg-type]
                parent_document_id=parent_document_id,
            )
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
            return await _transitions.get_converted_documents(
                self._session_factory,  # type: ignore[arg-type]
                source_type=source_type,
                source=source,
                conversion_method=conversion_method,
            )
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
            await _dispose_engine(self._engine)
            self.logger.debug("Database connections closed")
