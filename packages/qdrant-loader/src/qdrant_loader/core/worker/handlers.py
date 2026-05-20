"""Job handlers for queue-based ingestion workflows."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Protocol

from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


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
            raise ValueError(f"Unknown job type: {job_type}")

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
            raise ValueError(f"No handler registered for job type: {job_type}")
        handler = self._handlers[job_type]
        await handler(job_type, payload)

    def list_handlers(self) -> dict[str, str]:
        """List all registered handlers."""
        return {jt: h.__class__.__name__ for jt, h in self._handlers.items()}


class JobHandlerError(Exception):
    """Base exception for job handler errors."""

    pass


class TransientJobError(JobHandlerError):
    """Transient error (may succeed on retry)."""

    pass


class PermanentJobError(JobHandlerError):
    """Permanent error (will not succeed on retry)."""

    pass
