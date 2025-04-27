"""
Operation tracker for performance monitoring.
"""

import time
from typing import Dict, Optional, AsyncGenerator, Set
from contextlib import asynccontextmanager
from qdrant_loader.core.monitoring.models import OperationMetrics
from qdrant_loader.core.monitoring.managers.storage_manager import MetricsStorage
from qdrant_loader.core.monitoring.managers.base_tracker import BaseTracker
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class OperationTracker(BaseTracker):
    """Handles tracking of individual operations."""
    def __init__(self, storage: MetricsStorage):
        super().__init__(storage)
        self.active_operations: Set[str] = set()

    async def cleanup(self):
        """Clean up resources."""
        await self.lock_manager.cleanup()
        logger.debug("Operation tracker resources cleaned up")

    @asynccontextmanager
    async def track_operation(self, operation_type: str, metadata: Optional[Dict] = None) -> AsyncGenerator[str, None]:
        """Context manager for tracking operations."""
        operation_id = f"{operation_type}_{int(time.time() * 1000)}"
        logger.debug(f"Starting to track operation {operation_id} of type {operation_type}")
        try:
            await self.start_operation(operation_type, metadata)
            logger.debug(f"Successfully started tracking operation {operation_id}")
            yield operation_id
        except Exception as e:
            logger.error(f"Error in operation {operation_id}: {str(e)}", exc_info=True)
            raise
        finally:
            try:
                logger.debug(f"Attempting to end operation {operation_id}")
                if operation_id in self.storage.current_operations and not self.storage.current_operations[operation_id].is_completed:
                    await self.end_operation(operation_id)
                    logger.debug(f"Successfully ended operation {operation_id}")
                else:
                    logger.debug(f"Operation {operation_id} not found or already completed")
            except Exception as e:
                logger.error(f"Error ending operation {operation_id}: {str(e)}", exc_info=True)

    async def start_operation(self, operation_type: str, metadata: Optional[Dict] = None) -> str:
        """Start tracking an operation."""
        operation_id = f"{operation_type}_{int(time.time() * 1000)}"
        try:
            await self.lock_manager.acquire(holder=f"start_operation_{operation_id}")
            try:
                self.storage.current_operations[operation_id] = OperationMetrics(
                    start_time=time.time(),
                    metadata=metadata or {}
                )
                self.active_operations.add(operation_id)
                logger.debug(f"Started operation {operation_id}")
                return operation_id
            finally:
                await self.lock_manager.release()
        except Exception as e:
            logger.error(f"Failed to start operation {operation_id}: {str(e)}", exc_info=True)
            raise

    async def end_operation(self, operation_id: str, success: bool = True, error: Optional[str] = None):
        """End tracking an operation."""
        try:
            await self.lock_manager.acquire(holder=f"end_operation_{operation_id}")
            try:
                if operation_id not in self.storage.current_operations:
                    logger.debug(f"Operation {operation_id} not found in current operations")
                    return

                operation = self.storage.current_operations[operation_id]
                if operation.is_completed:
                    logger.debug(f"Operation {operation_id} already completed")
                    return

                operation.end_time = time.time()
                operation.duration = operation.end_time - operation.start_time
                operation.success = success
                operation.error = error
                operation.is_completed = True

                # Store the operation metrics
                operation_type = operation_id.split('_')[0]
                if operation_type not in self.storage.operations:
                    self.storage.operations[operation_type] = []
                self.storage.operations[operation_type].append(operation)

                # Log the operation
                self._log_operation(operation_id, operation)

                # Remove from current operations
                del self.storage.current_operations[operation_id]
                self.active_operations.remove(operation_id)
                logger.debug(f"Ended operation {operation_id}")
            finally:
                await self.lock_manager.release()
        except Exception as e:
            logger.error(f"Failed to end operation {operation_id}: {str(e)}", exc_info=True)
            raise

    def _log_operation(self, operation_id: str, operation: OperationMetrics):
        """Log operation metrics."""
        log_data = {
            'operation_id': operation_id,
            'duration': operation.duration,
            'success': operation.success,
            'error': operation.error,
            'metadata': operation.metadata
        }
        if operation.success:
            logger.info('Operation completed', **log_data)
        else:
            logger.error('Operation failed', **log_data)

    async def cleanup_operation(self, operation_id: str, success: bool = True, error: Optional[str] = None):
        """Clean up an operation."""
        await self.end_operation(operation_id, success, error)
        logger.debug(f"Cleaned up operation {operation_id}") 