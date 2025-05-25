"""
Simple ingestion metrics tracking and reporting.
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from qdrant_loader.core.monitoring.batch_summary import BatchSummary
from qdrant_loader.core.monitoring.processing_stats import ProcessingStats
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


@dataclass
class IngestionMetrics:
    """Metrics for a single ingestion operation."""

    start_time: float
    end_time: float | None = None
    duration: float | None = None
    success: bool = True
    error: str | None = None
    metadata: dict = field(default_factory=dict)
    is_completed: bool = False


@dataclass
class BatchMetrics:
    """Metrics for a batch of documents."""

    batch_size: int
    start_time: float
    end_time: float | None = None
    duration: float | None = None
    success_count: int = 0
    error_count: int = 0
    errors: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    is_completed: bool = False
    summary: BatchSummary | None = None


class IngestionMonitor:
    """Simple monitor for tracking ingestion metrics."""

    def __init__(self, metrics_dir: str):
        """Initialize the monitor.

        Args:
            metrics_dir: Directory to store metrics files
        """
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

        # Initialize metrics storage
        self.ingestion_metrics: dict[str, IngestionMetrics] = {}
        self.batch_metrics: dict[str, BatchMetrics] = {}

        # Initialize new metrics components
        self.processing_stats = ProcessingStats()
        self.batch_summary = BatchSummary()

        # Track current operation
        self.current_operation: str | None = None
        self.current_batch: str | None = None

    def start_operation(self, operation_id: str, metadata: dict | None = None) -> None:
        """Start tracking an operation.

        Args:
            operation_id: Unique identifier for the operation
            metadata: Optional metadata about the operation
        """
        self.ingestion_metrics[operation_id] = IngestionMetrics(
            start_time=time.time(), metadata=metadata or {}
        )
        self.current_operation = operation_id
        logger.debug(f"Started tracking operation {operation_id}")

    def end_operation(
        self, operation_id: str, success: bool = True, error: str | None = None
    ) -> None:
        """End tracking an operation.

        Args:
            operation_id: Unique identifier for the operation
            success: Whether the operation succeeded
            error: Error message if operation failed
        """
        if operation_id not in self.ingestion_metrics:
            logger.warning(f"Attempted to end untracked operation {operation_id}")
            return

        metrics = self.ingestion_metrics[operation_id]
        metrics.end_time = time.time()
        metrics.duration = metrics.end_time - metrics.start_time
        metrics.success = success
        metrics.error = error
        metrics.is_completed = True

        if self.current_operation == operation_id:
            self.current_operation = None

        logger.debug(f"Ended tracking operation {operation_id}")

    def start_batch(
        self, batch_id: str, batch_size: int, metadata: dict | None = None
    ) -> None:
        """Start tracking a batch.

        Args:
            batch_id: Unique identifier for the batch
            batch_size: Number of documents in the batch
            metadata: Optional metadata about the batch
        """
        self.batch_metrics[batch_id] = BatchMetrics(
            batch_size=batch_size,
            start_time=time.time(),
            metadata=metadata or {},
            summary=BatchSummary(),
        )
        self.current_batch = batch_id
        logger.debug(f"Started tracking batch {batch_id}")

    def end_batch(
        self,
        batch_id: str,
        success_count: int,
        error_count: int,
        errors: list[str] | None = None,
        document_sizes: list[int] | None = None,
        chunk_sizes: list[int] | None = None,
        source: str | None = None,
    ) -> None:
        """End tracking a batch.

        Args:
            batch_id: Unique identifier for the batch
            success_count: Number of successful operations
            error_count: Number of failed operations
            errors: List of error messages
            document_sizes: List of document sizes in bytes
            chunk_sizes: List of chunk sizes in bytes
            source: Source identifier for the batch
        """
        if batch_id not in self.batch_metrics:
            logger.warning(f"Attempted to end untracked batch {batch_id}")
            return

        metrics = self.batch_metrics[batch_id]
        metrics.end_time = time.time()
        metrics.duration = metrics.end_time - metrics.start_time
        metrics.success_count = success_count
        metrics.error_count = error_count
        metrics.errors = errors or []
        metrics.is_completed = True

        # Calculate total chunks from document metadata
        total_chunks = 0
        for doc_id, doc_metrics in self.ingestion_metrics.items():
            if doc_id.startswith("doc_") and doc_metrics.metadata.get("num_chunks"):
                total_chunks += doc_metrics.metadata["num_chunks"]

        # Calculate total size from document metadata
        total_size = 0
        for doc_id, doc_metrics in self.ingestion_metrics.items():
            if doc_id.startswith("doc_") and doc_metrics.metadata.get("size"):
                total_size += doc_metrics.metadata["size"]

        # Update processing stats
        self.processing_stats.update_rates(
            num_documents=metrics.batch_size,
            num_chunks=total_chunks,
            processing_time=metrics.duration,
        )

        # Update source metrics if available
        if source:
            self.processing_stats.update_source_metrics(
                source=source,
                num_documents=metrics.batch_size,
                processing_time=metrics.duration,
            )

        # Update batch summary
        if metrics.summary:
            metrics.summary.update_batch_stats(
                num_documents=metrics.batch_size,
                num_chunks=total_chunks,
                total_size=total_size,
                processing_time=metrics.duration,
                success_count=success_count,
                error_count=error_count,
                document_sizes=document_sizes,
                chunk_sizes=chunk_sizes,
                source=source,
            )

        if self.current_batch == batch_id:
            self.current_batch = None

        logger.debug(f"Ended tracking batch {batch_id}")

    def save_metrics(self) -> None:
        """Save all metrics to a JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_file = self.metrics_dir / f"ingestion_metrics_{timestamp}.json"

        metrics_data = {
            "ingestion_metrics": {
                op_id: {
                    "start_time": m.start_time,
                    "end_time": m.end_time,
                    "duration": m.duration,
                    "success": m.success,
                    "error": m.error,
                    "metadata": m.metadata,
                    "is_completed": m.is_completed,
                }
                for op_id, m in self.ingestion_metrics.items()
            },
            "batch_metrics": {
                batch_id: {
                    "batch_size": m.batch_size,
                    "start_time": m.start_time,
                    "end_time": m.end_time,
                    "duration": m.duration,
                    "success_count": m.success_count,
                    "error_count": m.error_count,
                    "errors": m.errors,
                    "metadata": m.metadata,
                    "is_completed": m.is_completed,
                    "summary": m.summary.get_summary() if m.summary else None,
                }
                for batch_id, m in self.batch_metrics.items()
            },
            "processing_stats": {
                "overall_metrics": {
                    "total_documents": self.processing_stats.total_documents,
                    "total_chunks": self.processing_stats.total_chunks,
                    "total_processing_time": self.processing_stats.total_processing_time,
                },
                "rates": self.processing_stats.get_latest_rates(),
                "source_metrics": self.processing_stats.source_metrics,
            },
        }

        try:
            with open(metrics_file, "w", encoding="utf-8") as f:
                json.dump(metrics_data, f, indent=2, default=str)
            logger.info(f"Metrics saved to {metrics_file}")
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to save metrics: {str(e)}")

    def clear_metrics(self) -> None:
        """Clear all collected metrics."""
        self.ingestion_metrics.clear()
        self.batch_metrics.clear()
        self.processing_stats = ProcessingStats()
        self.batch_summary = BatchSummary()
        self.current_operation = None
        self.current_batch = None
        logger.debug("Cleared all metrics")
