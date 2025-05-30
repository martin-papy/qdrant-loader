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

    # File conversion metrics
    conversion_attempted: bool = False
    conversion_success: bool = False
    conversion_time: float | None = None
    conversion_method: str | None = None
    original_file_type: str | None = None
    file_size: int | None = None


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

    # File conversion metrics
    converted_files_count: int = 0
    conversion_failures_count: int = 0
    attachments_processed_count: int = 0
    total_conversion_time: float = 0.0


@dataclass
class ConversionMetrics:
    """Metrics specifically for file conversion operations."""

    total_files_processed: int = 0
    successful_conversions: int = 0
    failed_conversions: int = 0
    total_conversion_time: float = 0.0
    average_conversion_time: float = 0.0
    attachments_processed: int = 0
    conversion_methods: dict[str, int] = field(default_factory=dict)
    file_types_processed: dict[str, int] = field(default_factory=dict)
    error_types: dict[str, int] = field(default_factory=dict)


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
        self.conversion_metrics = ConversionMetrics()

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

    def start_conversion(
        self,
        operation_id: str,
        file_path: str,
        file_type: str,
        file_size: int | None = None,
    ) -> None:
        """Start tracking a file conversion operation.

        Args:
            operation_id: Unique identifier for the conversion operation
            file_path: Path to the file being converted
            file_type: Type/extension of the file
            file_size: Size of the file in bytes
        """
        if operation_id not in self.ingestion_metrics:
            self.ingestion_metrics[operation_id] = IngestionMetrics(
                start_time=time.time(),
                metadata={
                    "file_path": file_path,
                    "file_type": file_type,
                    "file_size": file_size,
                },
            )

        metrics = self.ingestion_metrics[operation_id]
        metrics.conversion_attempted = True
        metrics.original_file_type = file_type
        metrics.file_size = file_size

        logger.debug(f"Started tracking conversion for {operation_id}: {file_path}")

    def end_conversion(
        self,
        operation_id: str,
        success: bool = True,
        conversion_method: str | None = None,
        error: str | None = None,
    ) -> None:
        """End tracking a file conversion operation.

        Args:
            operation_id: Unique identifier for the conversion operation
            success: Whether the conversion succeeded
            conversion_method: Method used for conversion (e.g., 'markitdown')
            error: Error message if conversion failed
        """
        if operation_id not in self.ingestion_metrics:
            logger.warning(f"Attempted to end untracked conversion {operation_id}")
            return

        metrics = self.ingestion_metrics[operation_id]
        end_time = time.time()
        conversion_time = end_time - metrics.start_time

        metrics.conversion_success = success
        metrics.conversion_time = conversion_time
        metrics.conversion_method = conversion_method
        if not success and error:
            metrics.error = error

        # Update global conversion metrics
        self.conversion_metrics.total_files_processed += 1
        if success:
            self.conversion_metrics.successful_conversions += 1
        else:
            self.conversion_metrics.failed_conversions += 1
            if error:
                error_type = (
                    type(error).__name__ if isinstance(error, Exception) else "Unknown"
                )
                self.conversion_metrics.error_types[error_type] = (
                    self.conversion_metrics.error_types.get(error_type, 0) + 1
                )

        self.conversion_metrics.total_conversion_time += conversion_time

        # Update average conversion time
        if self.conversion_metrics.total_files_processed > 0:
            self.conversion_metrics.average_conversion_time = (
                self.conversion_metrics.total_conversion_time
                / self.conversion_metrics.total_files_processed
            )

        # Track conversion methods
        if conversion_method:
            self.conversion_metrics.conversion_methods[conversion_method] = (
                self.conversion_metrics.conversion_methods.get(conversion_method, 0) + 1
            )

        # Track file types
        if metrics.original_file_type:
            self.conversion_metrics.file_types_processed[metrics.original_file_type] = (
                self.conversion_metrics.file_types_processed.get(
                    metrics.original_file_type, 0
                )
                + 1
            )

        logger.debug(f"Ended tracking conversion for {operation_id}: success={success}")

    def record_attachment_processed(self) -> None:
        """Record that an attachment was processed."""
        self.conversion_metrics.attachments_processed += 1

    def update_batch_conversion_metrics(
        self,
        batch_id: str,
        converted_files_count: int = 0,
        conversion_failures_count: int = 0,
        attachments_processed_count: int = 0,
        total_conversion_time: float = 0.0,
    ) -> None:
        """Update conversion metrics for a batch.

        Args:
            batch_id: Unique identifier for the batch
            converted_files_count: Number of files successfully converted
            conversion_failures_count: Number of conversion failures
            attachments_processed_count: Number of attachments processed
            total_conversion_time: Total time spent on conversions
        """
        if batch_id not in self.batch_metrics:
            logger.warning(
                f"Attempted to update conversion metrics for untracked batch {batch_id}"
            )
            return

        metrics = self.batch_metrics[batch_id]
        metrics.converted_files_count += converted_files_count
        metrics.conversion_failures_count += conversion_failures_count
        metrics.attachments_processed_count += attachments_processed_count
        metrics.total_conversion_time += total_conversion_time

        logger.debug(f"Updated conversion metrics for batch {batch_id}")

    def get_conversion_summary(self) -> dict:
        """Get a summary of all conversion metrics."""
        return {
            "total_files_processed": self.conversion_metrics.total_files_processed,
            "successful_conversions": self.conversion_metrics.successful_conversions,
            "failed_conversions": self.conversion_metrics.failed_conversions,
            "success_rate": (
                self.conversion_metrics.successful_conversions
                / max(self.conversion_metrics.total_files_processed, 1)
            )
            * 100,
            "total_conversion_time": self.conversion_metrics.total_conversion_time,
            "average_conversion_time": self.conversion_metrics.average_conversion_time,
            "attachments_processed": self.conversion_metrics.attachments_processed,
            "conversion_methods": dict(self.conversion_metrics.conversion_methods),
            "file_types_processed": dict(self.conversion_metrics.file_types_processed),
            "error_types": dict(self.conversion_metrics.error_types),
        }

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
                    # File conversion metrics
                    "conversion_attempted": m.conversion_attempted,
                    "conversion_success": m.conversion_success,
                    "conversion_time": m.conversion_time,
                    "conversion_method": m.conversion_method,
                    "original_file_type": m.original_file_type,
                    "file_size": m.file_size,
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
                    # File conversion metrics
                    "converted_files_count": m.converted_files_count,
                    "conversion_failures_count": m.conversion_failures_count,
                    "attachments_processed_count": m.attachments_processed_count,
                    "total_conversion_time": m.total_conversion_time,
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
            "conversion_metrics": {
                "total_files_processed": self.conversion_metrics.total_files_processed,
                "successful_conversions": self.conversion_metrics.successful_conversions,
                "failed_conversions": self.conversion_metrics.failed_conversions,
                "total_conversion_time": self.conversion_metrics.total_conversion_time,
                "average_conversion_time": self.conversion_metrics.average_conversion_time,
                "attachments_processed": self.conversion_metrics.attachments_processed,
                "conversion_methods": dict(self.conversion_metrics.conversion_methods),
                "file_types_processed": dict(
                    self.conversion_metrics.file_types_processed
                ),
                "error_types": dict(self.conversion_metrics.error_types),
                "summary": self.get_conversion_summary(),
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
        self.conversion_metrics = ConversionMetrics()
        self.current_operation = None
        self.current_batch = None
        logger.debug("Cleared all metrics")
