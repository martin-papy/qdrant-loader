"""
Resource manager for performance monitoring.
"""

import asyncio
import time
from typing import Optional, Set
from qdrant_loader.core.monitoring.models import MonitorConfig
from qdrant_loader.core.monitoring.managers.storage_manager import MetricsStorage
from qdrant_loader.core.monitoring.managers.base_tracker import BaseTracker
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class ResourceManager:
    """Manages resources and cleanup."""
    def __init__(self, storage: MetricsStorage, config: MonitorConfig):
        self.storage = storage
        self.config = config
        self.cleanup_task: Optional[asyncio.Task] = None
        self.operation_tracker: Optional[BaseTracker] = None

    def set_operation_tracker(self, tracker: BaseTracker):
        """Set the operation tracker for cleanup."""
        self.operation_tracker = tracker

    async def start_cleanup_task(self):
        """Start the cleanup task."""
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._cleanup_stale_operations())
            # Ensure the task is started by yielding control
            await asyncio.sleep(0)

    async def stop_cleanup_task(self):
        """Stop the cleanup task."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None

    async def _cleanup_stale_operations(self):
        """Clean up stale operations periodically."""
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                await self.cleanup_stale_operations()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {str(e)}", exc_info=True)

    async def cleanup_stale_operations(self):
        """Clean up operations that have been running for too long."""
        if not self.operation_tracker:
            logger.error("Operation tracker not set, cannot clean up stale operations")
            return

        current_time = time.time()
        for op_id, operation in list(self.storage.current_operations.items()):
            if current_time - operation.start_time > self.config.max_operation_age:
                logger.warning(f"Cleaning up stale operation {op_id}")
                await self.operation_tracker.cleanup_operation(op_id, success=False, error="Operation timed out") 