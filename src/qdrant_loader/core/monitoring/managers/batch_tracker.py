"""
Batch tracker for performance monitoring.
"""

import time
from typing import Dict, List, Optional, AsyncGenerator
from contextlib import asynccontextmanager
from qdrant_loader.core.monitoring.models import BatchMetrics
from qdrant_loader.core.monitoring.managers.storage_manager import MetricsStorage
from qdrant_loader.core.monitoring.managers.lock_manager import AsyncLockManager
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class BatchTracker:
    """Handles tracking of batches."""
    def __init__(self, storage: MetricsStorage):
        self.storage = storage
        self.lock_manager = AsyncLockManager()

    async def cleanup(self):
        """Clean up resources."""
        await self.lock_manager.cleanup()

    @asynccontextmanager
    async def track_batch(self, batch_type: str, batch_size: int, metadata: Optional[Dict] = None) -> AsyncGenerator[str, None]:
        """Context manager for tracking batches."""
        batch_id = f"{batch_type}_{int(time.time() * 1000)}"
        try:
            await self.start_batch(batch_type, batch_size, metadata)
            yield batch_id
        except Exception as e:
            logger.error(f"Error in batch {batch_id}: {str(e)}")
            raise
        finally:
            try:
                async with self.lock_manager:
                    if batch_id in self.storage.current_batches and not self.storage.current_batches[batch_id].is_completed:
                        await self.end_batch(batch_id, 0, 0)  # Default values if not set
            except Exception as e:
                logger.error(f"Error ending batch {batch_id}: {str(e)}")

    async def start_batch(self, batch_type: str, batch_size: int, metadata: Optional[Dict] = None) -> str:
        """Start tracking a batch."""
        batch_id = f"{batch_type}_{int(time.time() * 1000)}"
        async with self.lock_manager:
            self.storage.current_batches[batch_id] = BatchMetrics(
                batch_size=batch_size,
                start_time=time.time(),
                metadata=metadata or {}
            )
        return batch_id

    async def end_batch(self, batch_id: str, success_count: int, error_count: int, errors: Optional[List[str]] = None):
        """End tracking a batch."""
        async with self.lock_manager:
            if batch_id not in self.storage.current_batches:
                logger.warning(f"Batch {batch_id} not found in current batches")
                return

            batch = self.storage.current_batches[batch_id]
            if batch.is_completed:
                logger.warning(f"Batch {batch_id} already completed")
                return

            batch.end_time = time.time()
            batch.duration = batch.end_time - batch.start_time
            batch.success_count = success_count
            batch.error_count = error_count
            batch.errors = errors or []
            batch.is_completed = True

            # Store the batch metrics
            batch_type = batch_id.split('_')[0]
            if batch_type not in self.storage.batches:
                self.storage.batches[batch_type] = []
            self.storage.batches[batch_type].append(batch)

            # Log the batch
            self._log_batch(batch_id, batch)

            # Remove from current batches
            del self.storage.current_batches[batch_id]

    def _log_batch(self, batch_id: str, batch: BatchMetrics):
        """Log batch metrics."""
        log_data = {
            'batch_id': batch_id,
            'duration': batch.duration,
            'success_count': batch.success_count,
            'error_count': batch.error_count,
            'errors': batch.errors,
            'metadata': batch.metadata
        }
        logger.info('Batch completed', **log_data) 