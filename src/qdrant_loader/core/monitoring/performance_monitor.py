"""
Performance monitoring module for tracking and analyzing ingestion performance metrics.
"""

import time
from datetime import datetime, UTC
from typing import Dict, List, Optional, cast
import asyncio
from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
from threading import Lock

from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


@dataclass
class OperationMetrics:
    """Metrics for a single operation."""
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class BatchMetrics:
    """Metrics for a batch of operations."""
    batch_size: int
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success_count: int = 0
    error_count: int = 0
    errors: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


class PerformanceMonitor:
    """Monitors and tracks performance metrics for the ingestion process."""

    def __init__(self, metrics_dir: Optional[Path] = None):
        """Initialize the performance monitor.

        Args:
            metrics_dir: Directory to store metrics files. If None, metrics will only be logged.
        """
        self.metrics_dir = metrics_dir
        if metrics_dir:
            metrics_dir.mkdir(parents=True, exist_ok=True)
        
        self.operation_metrics: Dict[str, List[OperationMetrics]] = {}
        self.batch_metrics: Dict[str, List[BatchMetrics]] = {}
        self.current_operations: Dict[str, OperationMetrics] = {}
        self.current_batches: Dict[str, BatchMetrics] = {}
        
        # Add thread safety
        self._operation_lock = Lock()
        self._batch_lock = Lock()
        
        # Initialize metrics storage
        self._initialize_metrics_storage()

    def _initialize_metrics_storage(self):
        """Initialize the metrics storage structure."""
        self.operation_metrics = {
            'document_processing': [],
            'chunking': [],
            'embedding': [],
            'upserting': [],
            'state_update': []
        }
        self.batch_metrics = {
            'document_batch': [],
            'embedding_batch': [],
            'upsert_batch': []
        }

    async def start_operation(self, operation_type: str, metadata: Optional[Dict] = None) -> str:
        """Start tracking an operation.

        Args:
            operation_type: Type of operation being tracked
            metadata: Additional metadata for the operation

        Returns:
            Operation ID for tracking
        """
        operation_id = f"{operation_type}_{int(time.time() * 1000)}"
        with self._operation_lock:
            self.current_operations[operation_id] = OperationMetrics(
                start_time=time.time(),
                metadata=metadata or {}
            )
        return operation_id

    async def end_operation(self, operation_id: str, success: bool = True, error: Optional[str] = None):
        """End tracking an operation.

        Args:
            operation_id: ID of the operation to end
            success: Whether the operation was successful
            error: Error message if operation failed
        """
        with self._operation_lock:
            if operation_id not in self.current_operations:
                logger.warning(f"Operation {operation_id} not found in current operations")
                return

            operation = self.current_operations[operation_id]
            operation.end_time = time.time()
            operation.duration = operation.end_time - operation.start_time
            operation.success = success
            operation.error = error

            # Store the operation metrics
            operation_type = operation_id.split('_')[0]
            if operation_type not in self.operation_metrics:
                self.operation_metrics[operation_type] = []
            self.operation_metrics[operation_type].append(operation)

            # Log the operation
            self._log_operation(operation_id, operation)

            # Remove from current operations
            del self.current_operations[operation_id]

    async def start_batch(self, batch_type: str, batch_size: int, metadata: Optional[Dict] = None) -> str:
        """Start tracking a batch of operations.

        Args:
            batch_type: Type of batch being tracked
            batch_size: Number of items in the batch
            metadata: Additional metadata for the batch

        Returns:
            Batch ID for tracking
        """
        batch_id = f"{batch_type}_{int(time.time() * 1000)}"
        with self._batch_lock:
            self.current_batches[batch_id] = BatchMetrics(
                batch_size=batch_size,
                start_time=time.time(),
                metadata=metadata or {}
            )
        return batch_id

    async def end_batch(self, batch_id: str, success_count: int, error_count: int, errors: Optional[List[str]] = None):
        """End tracking a batch of operations.

        Args:
            batch_id: ID of the batch to end
            success_count: Number of successful operations
            error_count: Number of failed operations
            errors: List of error messages
        """
        with self._batch_lock:
            if batch_id not in self.current_batches:
                logger.warning(f"Batch {batch_id} not found in current batches")
                return

            batch = self.current_batches[batch_id]
            batch.end_time = time.time()
            batch.duration = batch.end_time - batch.start_time
            batch.success_count = success_count
            batch.error_count = error_count
            batch.errors = errors or []

            # Store the batch metrics
            batch_type = batch_id.split('_')[0]
            if batch_type not in self.batch_metrics:
                self.batch_metrics[batch_type] = []
            self.batch_metrics[batch_type].append(batch)

            # Log the batch
            self._log_batch(batch_id, batch)

            # Remove from current batches
            del self.current_batches[batch_id]

    def _log_operation(self, operation_id: str, operation: OperationMetrics):
        """Log operation metrics.

        Args:
            operation_id: ID of the operation
            operation: Operation metrics to log
        """
        log_data = {
            'operation_id': operation_id,
            'duration': operation.duration,
            'success': operation.success,
            'error': operation.error,
            'metadata': operation.metadata
        }
        logger.info('Operation completed', **log_data)

    def _log_batch(self, batch_id: str, batch: BatchMetrics):
        """Log batch metrics.

        Args:
            batch_id: ID of the batch
            batch: Batch metrics to log
        """
        log_data = {
            'batch_id': batch_id,
            'batch_size': batch.batch_size,
            'duration': batch.duration,
            'success_count': batch.success_count,
            'error_count': batch.error_count,
            'errors': batch.errors,
            'metadata': batch.metadata
        }
        logger.info('Batch completed', **log_data)

    async def get_metrics_summary(self) -> Dict:
        """Get a summary of all collected metrics.

        Returns:
            Dictionary containing metrics summary
        """
        summary = {
            'operations': {},
            'batches': {},
            'overall': {
                'total_operations': 0,
                'successful_operations': 0,
                'failed_operations': 0,
                'total_batches': 0,
                'successful_batches': 0,
                'failed_batches': 0,
                'average_operation_duration': 0,
                'average_batch_duration': 0
            }
        }

        # Calculate operation metrics
        for op_type, operations in self.operation_metrics.items():
            if not operations:
                continue

            # Filter out operations with None duration
            valid_operations = [op for op in operations if op.duration is not None]
            if not valid_operations:
                continue

            durations = [cast(float, op.duration) for op in valid_operations]
            op_metrics = {
                'count': len(valid_operations),
                'success_count': sum(1 for op in valid_operations if op.success),
                'error_count': sum(1 for op in valid_operations if not op.success),
                'average_duration': sum(durations) / len(durations),
                'min_duration': min(durations),
                'max_duration': max(durations),
                'durations': durations
            }
            summary['operations'][op_type] = op_metrics

            # Update overall metrics
            summary['overall']['total_operations'] += op_metrics['count']
            summary['overall']['successful_operations'] += op_metrics['success_count']
            summary['overall']['failed_operations'] += op_metrics['error_count']

        # Calculate batch metrics
        for batch_type, batches in self.batch_metrics.items():
            if not batches:
                continue

            # Filter out batches with None duration
            valid_batches = [b for b in batches if b.duration is not None]
            if not valid_batches:
                continue

            durations = [cast(float, b.duration) for b in valid_batches]
            batch_metrics = {
                'count': len(valid_batches),
                'success_count': sum(1 for b in valid_batches if b.error_count == 0),
                'error_count': sum(1 for b in valid_batches if b.error_count > 0),
                'average_duration': sum(durations) / len(durations),
                'min_duration': min(durations),
                'max_duration': max(durations),
                'average_batch_size': sum(b.batch_size for b in valid_batches) / len(valid_batches),
                'durations': durations
            }
            summary['batches'][batch_type] = batch_metrics

            # Update overall metrics
            summary['overall']['total_batches'] += batch_metrics['count']
            summary['overall']['successful_batches'] += batch_metrics['success_count']
            summary['overall']['failed_batches'] += batch_metrics['error_count']

        # Calculate overall averages
        if summary['overall']['total_operations'] > 0:
            all_durations = [
                cast(float, op.duration)
                for ops in self.operation_metrics.values()
                for op in ops
                if op.duration is not None
            ]
            if all_durations:
                summary['overall']['average_operation_duration'] = sum(all_durations) / len(all_durations)

        if summary['overall']['total_batches'] > 0:
            all_batch_durations = [
                cast(float, b.duration)
                for batches in self.batch_metrics.values()
                for b in batches
                if b.duration is not None
            ]
            if all_batch_durations:
                summary['overall']['average_batch_duration'] = sum(all_batch_durations) / len(all_batch_durations)

        return summary

    async def save_metrics(self, filename: Optional[str] = None):
        """Save collected metrics to a file.

        Args:
            filename: Name of the file to save metrics to. If None, a timestamp-based name will be used.
        """
        if not self.metrics_dir:
            logger.warning("No metrics directory specified, skipping metrics save")
            return

        if not filename:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            filename = f"metrics_{timestamp}.json"

        metrics_file = self.metrics_dir / filename
        summary = await self.get_metrics_summary()

        try:
            with open(metrics_file, 'w') as f:
                json.dump(summary, f, indent=2)
            logger.info(f"Metrics saved to {metrics_file}")
        except Exception as e:
            logger.error(f"Failed to save metrics: {str(e)}")

    async def clear_metrics(self):
        """Clear all collected metrics."""
        with self._operation_lock, self._batch_lock:
            self._initialize_metrics_storage()
            logger.info("Metrics cleared") 