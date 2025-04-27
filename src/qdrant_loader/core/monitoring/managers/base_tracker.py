"""
Base tracker for performance monitoring.
"""

from typing import Dict, Optional, AsyncGenerator
from contextlib import asynccontextmanager
from qdrant_loader.core.monitoring.managers.storage_manager import MetricsStorage
from qdrant_loader.core.monitoring.managers.lock_manager import AsyncLockManager
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class BaseTracker:
    """Base class for operation tracking."""
    def __init__(self, storage: MetricsStorage):
        self.storage = storage
        self.lock_manager = AsyncLockManager()

    async def cleanup_operation(self, operation_id: str, success: bool = True, error: Optional[str] = None):
        """Clean up an operation. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement cleanup_operation") 