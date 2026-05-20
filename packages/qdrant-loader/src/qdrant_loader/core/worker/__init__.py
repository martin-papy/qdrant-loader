"""Worker queue abstractions and implementations."""

from qdrant_loader.core.worker.handlers import (
    BaseJobHandler,
    HandlerRegistry,
    IngestionJobHandler,
    JobHandler,
    PermanentJobError,
    TransientJobError,
)
from qdrant_loader.core.worker.pool import QueueWorkerPool
from qdrant_loader.core.worker.queue import JobQueue, SQLiteJobQueue

__all__ = [
    # Queue abstractions
    "JobQueue",
    "SQLiteJobQueue",
    # Pool
    "QueueWorkerPool",
    # Handlers
    "JobHandler",
    "BaseJobHandler",
    "IngestionJobHandler",
    "HandlerRegistry",
    "TransientJobError",
    "PermanentJobError",
]
