"""
Performance monitoring module for tracking and analyzing ingestion performance metrics.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, ClassVar
from weakref import WeakKeyDictionary
from contextlib import asynccontextmanager
import logging

from qdrant_loader.core.monitoring.models import MonitorConfig
from qdrant_loader.core.monitoring.managers.storage_manager import MetricsStorage
from qdrant_loader.core.monitoring.managers.resource_manager import ResourceManager
from qdrant_loader.core.monitoring.managers.operation_tracker import OperationTracker
from qdrant_loader.core.monitoring.managers.batch_tracker import BatchTracker
from qdrant_loader.core.monitoring.collectors.metrics_collector import MetricsCollector
from qdrant_loader.utils.logging import LoggingConfig
from qdrant_loader.core.monitoring.models import OperationMetrics, BatchMetrics

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitor and collect performance metrics during ingestion."""

    _monitors: ClassVar[WeakKeyDictionary] = WeakKeyDictionary()

    def __init__(self, metrics_dir: str):
        """Initialize the performance monitor.

        Args:
            metrics_dir: Directory to store metrics files
        """
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize storage and trackers
        self.storage = MetricsStorage()
        self.metrics_collector = MetricsCollector(self.storage)
        self.operation_tracker = OperationTracker(self.storage)
        self.batch_tracker = BatchTracker(self.storage)
        self.resource_manager = ResourceManager(self.storage, MonitorConfig())
        
        # Initialize tracking state
        self.is_disposed = False
        self.current_operation: Optional[str] = None
        self.current_batch: Optional[str] = None

    def _reset_metrics(self) -> None:
        """Reset all metrics to initial state."""
        self._reset_operation_metrics()
        self._reset_document_metrics()
        self._reset_chunk_metrics()

    def _reset_operation_metrics(self) -> None:
        """Reset operation-related metrics."""
        self.storage.operations = {}
        self.storage.durations = {}
        self.storage.errors = {}

    def _reset_document_metrics(self) -> None:
        """Reset document-related metrics."""
        self.storage.document_counts = {}
        self.storage.document_errors = {}
        self.storage.document_sizes = {}

    def _reset_chunk_metrics(self) -> None:
        """Reset chunk-related metrics."""
        self.storage.chunk_counts = {}
        self.storage.chunk_sizes = {}
        self.storage.chunk_tokens = {}

    async def _dispose(self) -> None:
        """Dispose of the monitor and save metrics."""
        if not self.is_disposed:
            try:
                await self._save_metrics()
                self.is_disposed = True
            except (IOError, json.JSONDecodeError) as e:
                logger.error(f"Failed to save metrics: {str(e)}")

    async def _track_operation(
        self,
        operation_type: str,
        operation_id: str,
        start_time: datetime,
        end_time: datetime,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Track an operation's performance metrics.

        Args:
            operation_type: Type of operation
            operation_id: Unique identifier for the operation
            start_time: Operation start time
            end_time: Operation end time
            success: Whether operation succeeded
            error: Error message if operation failed
        """
        try:
            await self.operation_tracker.end_operation(
                operation_id=operation_id,
                success=success,
                error=error
            )
        except (asyncio.CancelledError, RuntimeError) as e:
            logger.error(f"Failed to track operation: {str(e)}")

    async def _track_batch(
        self,
        batch_type: str,
        batch_id: str,
        start_time: datetime,
        end_time: datetime,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Track a batch processing metrics.

        Args:
            batch_type: Type of batch
            batch_id: Unique identifier for the batch
            start_time: Batch start time
            end_time: Batch end time
            success: Whether batch succeeded
            error: Error message if batch failed
        """
        try:
            await self.batch_tracker.end_batch(
                batch_id=batch_id,
                success_count=1 if success else 0,
                error_count=0 if success else 1,
                errors=[error] if error else None
            )
        except (asyncio.CancelledError, RuntimeError) as e:
            logger.error(f"Failed to track batch: {str(e)}")

    def track_document(
        self,
        operation_type: str,
        document_id: str,
        size: int,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Track document processing metrics.

        Args:
            operation_type: Type of operation
            document_id: Document identifier
            size: Document size in bytes
            success: Whether processing succeeded
            error: Error message if processing failed
        """
        try:
            self._update_document_metrics(
                operation_type,
                document_id,
                size,
                success,
                error
            )
        except (asyncio.CancelledError, RuntimeError) as e:
            logger.error(f"Failed to track document: {str(e)}")

    def _update_document_metrics(
        self,
        operation_type: str,
        document_id: str,
        size: int,
        success: bool,
        error: Optional[str]
    ) -> None:
        """Update document metrics in storage.

        Args:
            operation_type: Type of operation
            document_id: Document identifier
            size: Document size in bytes
            success: Whether processing succeeded
            error: Error message if processing failed
        """
        if operation_type not in self.storage.document_counts:
            self.storage.document_counts[operation_type] = 0
            self.storage.document_errors[operation_type] = []
            self.storage.document_sizes[operation_type] = []

        self.storage.document_counts[operation_type] += 1
        self.storage.document_sizes[operation_type].append(size)

        if not success and error:
            self.storage.document_errors[operation_type].append(
                {"document_id": document_id, "error": error}
            )

    def track_chunks(
        self,
        operation_type: str,
        num_chunks: int,
        chunk_sizes: List[int],
        chunk_tokens: List[int]
    ) -> None:
        """Track chunk processing metrics.

        Args:
            operation_type: Type of operation
            num_chunks: Number of chunks
            chunk_sizes: List of chunk sizes
            chunk_tokens: List of token counts per chunk
        """
        try:
            self._update_chunk_metrics(
                operation_type,
                num_chunks,
                chunk_sizes,
                chunk_tokens
            )
        except (asyncio.CancelledError, RuntimeError) as e:
            logger.error(f"Failed to track chunks: {str(e)}")

    def _update_chunk_metrics(
        self,
        operation_type: str,
        num_chunks: int,
        chunk_sizes: List[int],
        chunk_tokens: List[int]
    ) -> None:
        """Update chunk metrics in storage.

        Args:
            operation_type: Type of operation
            num_chunks: Number of chunks
            chunk_sizes: List of chunk sizes
            chunk_tokens: List of token counts per chunk
        """
        if operation_type not in self.storage.chunk_counts:
            self.storage.chunk_counts[operation_type] = 0
            self.storage.chunk_sizes[operation_type] = []
            self.storage.chunk_tokens[operation_type] = []

        self.storage.chunk_counts[operation_type] += num_chunks
        self.storage.chunk_sizes[operation_type].extend(chunk_sizes)
        self.storage.chunk_tokens[operation_type].extend(chunk_tokens)

    async def _save_metrics(self) -> None:
        """Save collected metrics to a file."""
        metrics = await self.metrics_collector.collect_metrics()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_file = self.metrics_dir / f"metrics_{timestamp}.json"
        
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, default=str)

    @classmethod
    def get_monitor(cls, metrics_dir: Optional[Path] = None) -> 'PerformanceMonitor':
        """Get a monitor instance for the current event loop."""
        loop = asyncio.get_event_loop()
        if loop not in cls._monitors:
            metrics_dir_str = str(metrics_dir.absolute()) if metrics_dir else "."
            config = MonitorConfig(metrics_dir=metrics_dir_str)
            # Ensure we always pass a valid string to the constructor
            monitor_metrics_dir = config.metrics_dir if config.metrics_dir is not None else "."
            cls._monitors[loop] = cls(monitor_metrics_dir)
            logger.debug("Created new monitor instance for current event loop")
        return cls._monitors[loop]

    async def initialize(self):
        """Initialize the monitor."""
        await self.resource_manager.start_cleanup_task()
        logger.debug("Performance monitor initialized")

    async def dispose(self):
        """Clean up resources."""
        if not self.is_disposed:
            try:
                await self._save_metrics()
                await self.resource_manager.stop_cleanup_task()
                await self.operation_tracker.cleanup()
                await self.batch_tracker.cleanup()
                self.is_disposed = True
                logger.debug("Performance monitor resources cleaned up")
            except (asyncio.CancelledError, RuntimeError) as e:
                logger.error(f"Error during monitor disposal: {str(e)}", exc_info=True)

    @asynccontextmanager
    async def track_operation(self, operation_type: str, metadata: Optional[Dict] = None):
        """Context manager for tracking operations."""
        async with self.operation_tracker.track_operation(operation_type, metadata) as operation_id:
            logger.debug(f"Started tracking operation {operation_id} of type {operation_type}")
            yield operation_id

    @asynccontextmanager
    async def track_batch(self, batch_type: str, batch_size: int, metadata: Optional[Dict] = None):
        """Context manager for tracking batches."""
        async with self.batch_tracker.track_batch(batch_type, batch_size, metadata) as batch_id:
            logger.debug(f"Started tracking batch {batch_id} of type {batch_type} with size {batch_size}")
            yield batch_id

    async def get_metrics_summary(self) -> Dict:
        """Get a summary of all collected metrics."""
        summary = await self.metrics_collector.collect_metrics()
        logger.debug("Collected metrics summary")
        return summary

    async def save_metrics(self) -> None:
        """Save metrics to a file."""
        if not self.metrics_dir:
            logger.warning("No metrics directory configured, skipping metrics save")
            return

        try:
            await self._save_metrics()
            logger.info(f"Metrics saved to {self.metrics_dir}")
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to save metrics: {str(e)}")

    async def clear_metrics(self):
        """Clear all collected metrics."""
        try:
            async with self.operation_tracker.lock_manager, self.batch_tracker.lock_manager:
                self.storage.current_operations.clear()
                self.storage.current_batches.clear()
                logger.debug("Current operations and batches cleared")
        except RuntimeError as e:
            logger.error(f"Failed to clear metrics: {str(e)}", exc_info=True)
            raise

    async def reset_metrics(self):
        """Reset all metrics for a new run."""
        try:
            async with self.operation_tracker.lock_manager, self.batch_tracker.lock_manager:
                self._reset_operation_metrics()
                self._reset_document_metrics()
                self._reset_chunk_metrics()
                logger.info("Metrics reset for new ingestion run")
        except RuntimeError as e:
            logger.error(f"Failed to reset metrics: {str(e)}", exc_info=True)
            raise

    async def track_operation_metrics(
        self,
        operation_type: str,
        start_time: float,
        duration: float,
        error: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Track an operation's metrics."""
        logger.debug(
            "Tracking operation",
            extra={
                "operation_type": operation_type,
                "start_time": start_time,
                "duration": duration,
                "error": error,
                "metadata": metadata
            }
        )
        metrics = OperationMetrics(
            start_time=start_time,
            duration=duration,
            error=error,
            metadata=metadata or {}
        )
        if operation_type not in self.storage.operations:
            self.storage.operations[operation_type] = []
        self.storage.operations[operation_type].append(metrics)

    async def track_batch_metrics(
        self,
        batch_type: str,
        batch_size: int,
        start_time: float,
        duration: float,
        metadata: Optional[Dict] = None
    ):
        """Track a batch's metrics."""
        logger.debug(
            "Tracking batch",
            extra={
                "batch_type": batch_type,
                "batch_size": batch_size,
                "start_time": start_time,
                "duration": duration,
                "metadata": metadata
            }
        )
        metrics = BatchMetrics(
            batch_size=batch_size,
            start_time=start_time,
            duration=duration,
            metadata=metadata or {}
        )
        if batch_type not in self.storage.batches:
            self.storage.batches[batch_type] = []
        self.storage.batches[batch_type].append(metrics)

    async def track_document_metrics(
        self,
        source: str,
        doc_type: str,
        size: int,
        processing_time: float
    ):
        """Track document metrics."""
        logger.debug(
            "Tracking document",
            extra={
                "source": source,
                "doc_type": doc_type,
                "size": size,
                "processing_time": processing_time
            }
        )
        self.storage.document_metrics['total_documents'] += 1

        if source not in self.storage.document_metrics['documents_by_source']:
            self.storage.document_metrics['documents_by_source'][source] = 0
        self.storage.document_metrics['documents_by_source'][source] += 1

        if doc_type not in self.storage.document_metrics['documents_by_type']:
            self.storage.document_metrics['documents_by_type'][doc_type] = 0
        self.storage.document_metrics['documents_by_type'][doc_type] += 1

        self.storage.document_metrics['document_sizes'].append(size)
        self.storage.document_metrics['document_processing_times'].append(processing_time)

    async def track_chunk_metrics(
        self,
        doc_id: str,
        size: int,
        strategy: str,
        processing_time: float
    ):
        """Track chunk metrics."""
        logger.debug(
            "Tracking chunk",
            extra={
                "doc_id": doc_id,
                "size": size,
                "strategy": strategy,
                "processing_time": processing_time
            }
        )
        self.storage.chunk_metrics['total_chunks'] += 1

        if doc_id not in self.storage.chunk_metrics['chunks_per_document']:
            self.storage.chunk_metrics['chunks_per_document'][doc_id] = 0
        self.storage.chunk_metrics['chunks_per_document'][doc_id] += 1

        if strategy not in self.storage.chunk_metrics['chunk_strategies']:
            self.storage.chunk_metrics['chunk_strategies'][strategy] = 0
        self.storage.chunk_metrics['chunk_strategies'][strategy] += 1

        self.storage.chunk_metrics['chunk_sizes'].append(size)
        self.storage.chunk_metrics['chunk_processing_times'].append(processing_time) 