"""Persistent queue backend for webhook events (WS-4)."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any

from qdrant_loader.config import get_settings
from qdrant_loader.core.state.session import (
    create_tables,
    dispose_engine,
    initialize_engine_and_session,
)
from qdrant_loader.core.worker.job_types import JobType
from qdrant_loader.core.worker.queue import SQLiteJobQueue
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)

# Re-export for backward compatibility
SINGLE_UPSERT = JobType.SINGLE_UPSERT.value
SINGLE_DELETE = JobType.SINGLE_DELETE.value
FULL_SCAN = "FULL_SCAN"  # Not yet in JobType; reserved for future use


@dataclass
class ChangeEvent:
    """Webhook event enqueued for durable processing."""

    source: str
    source_type: str | None
    project_id: str | None
    operation: str
    entity_id: str | None = None
    payload: Any = None
    force: bool = False

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> ChangeEvent:
        return cls(
            source=data["source"],
            source_type=data["source_type"],
            project_id=data.get("project_id"),
            operation=data["operation"],
            entity_id=data.get("entity_id"),
            payload=data.get("payload"),
            force=bool(data.get("force", False)),
        )


class QueueBackend(ABC):
    """Abstract webhook event queue."""

    @abstractmethod
    async def enqueue(self, event: ChangeEvent) -> str:
        """Enqueue an event. Returns a message/job id string."""

    @abstractmethod
    async def close(self) -> None:
        """Release queue resources."""


class SQLiteChangeEventQueue(QueueBackend):
    """SQLite-backed durable queue using the WS-4.1 jobs table."""

    def __init__(self, job_queue: SQLiteJobQueue):
        self._job_queue = job_queue

    async def enqueue(self, event: ChangeEvent) -> str:
        job = await self._job_queue.enqueue(
            event.operation,
            event.to_payload(),
        )
        logger.info(
            "Enqueued webhook event",
            job_id=job.id,
            operation=event.operation,
            source_type=event.source_type,
            source=event.source,
            entity_id=event.entity_id,
        )
        return str(job.id)

    @property
    def job_queue(self) -> SQLiteJobQueue:
        return self._job_queue

    async def close(self) -> None:
        return None


class QueueBackendManager:
    """Factory and lifecycle for the webhook queue backend."""

    _backend: QueueBackend | None = None
    _job_queue: SQLiteJobQueue | None = None
    _engine = None

    @classmethod
    async def initialize(cls) -> QueueBackend:
        if cls._backend is not None:
            return cls._backend

        settings = get_settings()
        state_config = settings.global_config.state_management
        engine, session_factory = initialize_engine_and_session(state_config)
        await create_tables(engine)

        cls._engine = engine
        cls._job_queue = SQLiteJobQueue(session_factory)
        cls._backend = SQLiteChangeEventQueue(cls._job_queue)
        logger.info(
            "Initialized persistent webhook queue",
            database_path=state_config.database_path,
        )
        return cls._backend

    @classmethod
    def get_backend(cls) -> QueueBackend:
        if cls._backend is None:
            raise RuntimeError(
                "Webhook queue is not initialized. Call QueueBackendManager.initialize() "
                "during server startup."
            )
        return cls._backend

    @classmethod
    def get_job_queue(cls) -> SQLiteJobQueue:
        if cls._job_queue is None:
            raise RuntimeError("Webhook job queue is not initialized.")
        return cls._job_queue

    @classmethod
    async def shutdown(cls) -> None:
        if cls._engine is not None:
            await dispose_engine(cls._engine)
        cls._engine = None
        cls._job_queue = None
        cls._backend = None

    @classmethod
    def set_backend(
        cls, backend: QueueBackend, job_queue: SQLiteJobQueue | None = None
    ) -> None:
        """Override backend for testing."""
        cls._backend = backend
        cls._job_queue = job_queue

    @classmethod
    def reset(cls) -> None:
        """Reset manager state (for tests)."""
        cls._engine = None
        cls._job_queue = None
        cls._backend = None


def parse_job_payload(job) -> ChangeEvent:
    """Deserialize a Job row into a ChangeEvent."""
    data = json.loads(job.payload_json)
    return ChangeEvent.from_payload(data)
