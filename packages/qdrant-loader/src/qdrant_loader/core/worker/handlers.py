"""Job handlers for queue-based ingestion workflows."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any, Protocol

from qdrant_loader.core.state.transitions import get_last_ingestion
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)

AsyncSessionFactory = Callable[[], Awaitable[Any]]


# ---------------------------------------------------------------------------
# Exceptions (defined first — used by classes below)
# ---------------------------------------------------------------------------


class JobHandlerError(Exception):
    """Base exception for job handler errors."""

    pass


class TransientJobError(JobHandlerError):
    """Transient error (may succeed on retry)."""

    pass


class PermanentJobError(JobHandlerError):
    """Permanent error (will not succeed on retry)."""

    pass


# ---------------------------------------------------------------------------
# Protocol / Abstract base
# ---------------------------------------------------------------------------


class JobHandler(Protocol):
    """Protocol for job handlers invoked by QueueWorkerPool."""

    async def __call__(self, job_type: str, payload: dict[str, Any]) -> None:
        """Execute a job of the given type with the provided payload."""
        ...


class BaseJobHandler(ABC):
    """Base class for job handlers."""

    async def __call__(self, job_type: str, payload: dict[str, Any]) -> None:
        """Dispatch to handler method based on job_type."""
        if job_type == "BULK_INGEST":
            return await self.handle_bulk_ingest(payload)
        elif job_type == "INCREMENTAL_PULL":
            return await self.handle_incremental_pull(payload)
        else:
            raise PermanentJobError(f"Unknown job type: {job_type}")

    @abstractmethod
    async def handle_bulk_ingest(self, payload: dict[str, Any]) -> None:
        """Handle BULK_INGEST job."""
        ...

    @abstractmethod
    async def handle_incremental_pull(self, payload: dict[str, Any]) -> None:
        """Handle INCREMENTAL_PULL job."""
        ...

    @staticmethod
    def _calculate_since_timestamp(last_ingestion: datetime | None) -> datetime | None:
        """Calculate the 'since' timestamp for incremental pulls (last_ingestion - 5min)."""
        if last_ingestion is None:
            return None
        return last_ingestion - timedelta(minutes=5)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class HandlerRegistry:
    """Registry for mapping job types to handler implementations."""

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._handlers: dict[str, BaseJobHandler] = {}

    def register(self, job_type: str, handler: BaseJobHandler) -> None:
        """Register a handler for a specific job type."""
        self._handlers[job_type] = handler
        logger.debug(
            "Registered handler", job_type=job_type, handler=handler.__class__.__name__
        )

    async def handle(self, job_type: str, payload: dict[str, Any]) -> None:
        """Execute a job by dispatching to the registered handler."""
        if job_type not in self._handlers:
            raise PermanentJobError(f"Unknown job type: {job_type}")
        handler = self._handlers[job_type]
        await handler(job_type, payload)

    def list_handlers(self) -> dict[str, str]:
        """List all registered handlers."""
        return {jt: h.__class__.__name__ for jt, h in self._handlers.items()}


# ---------------------------------------------------------------------------
# Concrete handler
# ---------------------------------------------------------------------------


class IngestionJobHandler(BaseJobHandler):
    """Concrete handler for BULK_INGEST and INCREMENTAL_PULL jobs.

    Delegates to PipelineOrchestrator for document processing.
    """

    def __init__(
        self,
        orchestrator: Any,
        session_factory: AsyncSessionFactory,
    ) -> None:
        self._orchestrator = orchestrator
        self._session_factory = session_factory

    @staticmethod
    def _validated_required_fields(payload: dict[str, Any]) -> tuple[str, str, str]:
        """Validate required payload fields and return normalized values."""
        required_fields = ("source_type", "source", "project_id")
        missing_or_invalid = [
            field
            for field in required_fields
            if not isinstance(payload.get(field), str) or not payload.get(field).strip()
        ]
        if missing_or_invalid:
            fields = ", ".join(missing_or_invalid)
            raise PermanentJobError(
                f"Invalid job payload: missing or invalid required field(s): {fields}"
            )

        source_type = payload["source_type"].strip()
        source = payload["source"].strip()
        project_id = payload["project_id"].strip()
        return source_type, source, project_id

    @staticmethod
    def _extract_optional_fields(
        payload: dict[str, Any],
    ) -> tuple[str | None, str | None, str | None]:
        """Extract source fields that may be absent (blank string → None = 'all')."""

        def _clean(key: str) -> str | None:
            v = payload.get(key)
            return v.strip() or None if isinstance(v, str) else None

        return _clean("source_type"), _clean("source"), _clean("project_id")

    async def handle_bulk_ingest(self, payload: dict[str, Any]) -> None:
        """Run a full ingestion, optionally scoped to a specific source.

        source_type / source / project_id may be absent or blank, in which case
        the orchestrator processes all configured sources (used by /ingest API).
        """
        try:
            source_type, source, project_id = self._extract_optional_fields(payload)
            force = bool(payload.get("force", True))
            await self._orchestrator.process_documents(
                source_type=source_type,
                source=source,
                project_id=project_id,
                force=force,
            )
        except PermanentJobError:
            raise
        except Exception as exc:
            raise TransientJobError(str(exc)) from exc

    async def handle_incremental_pull(self, payload: dict[str, Any]) -> None:
        """Run an incremental ingestion since last_ingestion - 5 min."""
        try:
            source_type, source, project_id = self._validated_required_fields(payload)
            last = await get_last_ingestion(
                self._session_factory,
                source_type=source_type,
                source=source,
                project_id=project_id,
            )
            since = self._calculate_since_timestamp(
                last.last_successful_ingestion if last else None
            )
            logger.info(
                "incremental_pull.since",
                source_type=source_type,
                source=source,
                since=since.isoformat() if since else None,
            )
            await self._orchestrator.process_documents(
                source_type=source_type,
                source=source,
                project_id=project_id,
                force=False,
                since=since,
            )
        except PermanentJobError:
            raise
        except Exception as exc:
            raise TransientJobError(str(exc)) from exc
