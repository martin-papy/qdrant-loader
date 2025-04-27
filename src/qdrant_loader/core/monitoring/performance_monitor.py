"""
Performance monitoring module for tracking and analyzing ingestion performance metrics.
"""

import asyncio
import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Optional, Any
from weakref import WeakKeyDictionary
from contextlib import asynccontextmanager

from qdrant_loader.core.monitoring.models import MonitorConfig
from qdrant_loader.core.monitoring.managers.storage_manager import MetricsStorage
from qdrant_loader.core.monitoring.managers.resource_manager import ResourceManager
from qdrant_loader.core.monitoring.managers.operation_tracker import OperationTracker
from qdrant_loader.core.monitoring.managers.batch_tracker import BatchTracker
from qdrant_loader.core.monitoring.collectors.metrics_collector import MetricsCollector
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class PerformanceMonitor:
    """Main class coordinating metrics collection."""
    _monitors = WeakKeyDictionary()

    def __init__(self, config: MonitorConfig):
        """Initialize the performance monitor."""
        self.config = config
        self.storage = MetricsStorage()
        self.resource_manager = ResourceManager(self.storage, config)
        self.operation_tracker = OperationTracker(self.storage)
        self.batch_tracker = BatchTracker(self.storage)
        self.metrics_collector = MetricsCollector(self.storage)

        # Set up resource manager
        self.resource_manager.set_operation_tracker(self.operation_tracker)

        if config.metrics_dir:
            Path(config.metrics_dir).mkdir(parents=True, exist_ok=True)
            logger.debug(f"Initialized metrics directory at {config.metrics_dir}")

    @classmethod
    def get_monitor(cls, metrics_dir: Optional[Path] = None) -> 'PerformanceMonitor':
        """Get a monitor instance for the current event loop."""
        loop = asyncio.get_event_loop()
        if loop not in cls._monitors:
            config = MonitorConfig(metrics_dir=str(metrics_dir) if metrics_dir else None)
            cls._monitors[loop] = cls(config)
            logger.debug("Created new monitor instance for current event loop")
        return cls._monitors[loop]

    async def initialize(self):
        """Initialize the monitor."""
        await self.resource_manager.start_cleanup_task()
        logger.debug("Performance monitor initialized")

    async def dispose(self):
        """Clean up resources."""
        try:
            await self.resource_manager.stop_cleanup_task()
            await self.operation_tracker.cleanup()
            await self.batch_tracker.cleanup()
            logger.debug("Performance monitor resources cleaned up")
        except Exception as e:
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

    async def save_metrics(self, filename: Optional[str] = None):
        """Save collected metrics to a file."""
        if not self.config.metrics_dir:
            logger.warning("No metrics directory specified, skipping metrics save")
            return

        if not filename:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            filename = f"metrics_{timestamp}.json"

        metrics_file = Path(self.config.metrics_dir) / filename
        summary = await self.get_metrics_summary()

        try:
            with open(metrics_file, 'w') as f:
                json.dump(summary, f, indent=2)
            logger.info(f"Metrics saved to {metrics_file}")
        except Exception as e:
            logger.error(f"Failed to save metrics: {str(e)}")

    async def clear_metrics(self):
        """Clear all collected metrics."""
        try:
            async with self.operation_tracker.lock_manager, self.batch_tracker.lock_manager:
                self.storage.operations = {
                    'document_processing': [],
                    'chunking': [],
                    'embedding': [],
                    'upserting': [],
                    'state_update': []
                }
                self.storage.batches = {
                    'document_batch': [],
                    'embedding_batch': [],
                    'upsert_batch': []
                }
                self.storage.current_operations.clear()
                self.storage.current_batches.clear()
                logger.debug("Metrics cleared")
        except Exception as e:
            logger.error(f"Failed to clear metrics: {str(e)}", exc_info=True)
            raise 