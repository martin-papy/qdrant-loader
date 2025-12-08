"""
Tests for monitoring extensions - file conversion metrics tracking.
"""

import json
import tempfile
from pathlib import Path

import pytest
from qdrant_loader.core.monitoring.ingestion_metrics import (
    BatchMetrics,
    ConversionMetrics,
    IngestionMetrics,
    IngestionMonitor,
)


@pytest.fixture
def temp_metrics_dir():
    """Create a temporary directory for metrics files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def monitor(temp_metrics_dir):
    """Create an IngestionMonitor instance for testing."""
    return IngestionMonitor(temp_metrics_dir)


class TestConversionMetricsDataClasses:
    """Test the new conversion metrics data classes."""

    def test_ingestion_metrics_with_conversion_fields(self):
        """Test IngestionMetrics with file conversion fields."""
        metrics = IngestionMetrics(
            start_time=1000.0,
            end_time=1005.0,
            duration=5.0,
            success=True,
            conversion_attempted=True,
            conversion_success=True,
            conversion_time=2.5,
            conversion_method="markitdown",
            original_file_type="pdf",
            file_size=1024000,
        )

        assert metrics.conversion_attempted is True
        assert metrics.conversion_success is True
        assert metrics.conversion_time == 2.5
        assert metrics.conversion_method == "markitdown"
        assert metrics.original_file_type == "pdf"
        assert metrics.file_size == 1024000

    def test_batch_metrics_with_conversion_fields(self):
        """Test BatchMetrics with file conversion fields."""
        metrics = BatchMetrics(
            batch_size=10,
            start_time=1000.0,
            converted_files_count=7,
            conversion_failures_count=1,
            attachments_processed_count=3,
            total_conversion_time=15.5,
        )

        assert metrics.converted_files_count == 7
        assert metrics.conversion_failures_count == 1
        assert metrics.attachments_processed_count == 3
        assert metrics.total_conversion_time == 15.5

    def test_conversion_metrics_defaults(self):
        """Test ConversionMetrics with default values."""
        metrics = ConversionMetrics()

        assert metrics.total_files_processed == 0
        assert metrics.successful_conversions == 0
        assert metrics.failed_conversions == 0
        assert metrics.total_conversion_time == 0.0
        assert metrics.average_conversion_time == 0.0
        assert metrics.attachments_processed == 0
        assert metrics.conversion_methods == {}
        assert metrics.file_types_processed == {}
        assert metrics.error_types == {}


class TestConversionTracking:
    """Test file conversion tracking functionality."""

    def test_start_conversion_tracking(self, monitor):
        """Test starting conversion tracking for a file."""
        operation_id = "conv_test_001"
        file_path = "/path/to/document.pdf"
        file_type = "pdf"
        file_size = 2048000

        monitor.start_conversion(operation_id, file_path, file_type, file_size)

        assert operation_id in monitor.ingestion_metrics
        metrics = monitor.ingestion_metrics[operation_id]
        assert metrics.conversion_attempted is True
        assert metrics.original_file_type == "pdf"
        assert metrics.file_size == 2048000
        assert metrics.metadata["file_path"] == file_path
        assert metrics.metadata["file_type"] == file_type

    def test_end_successful_conversion(self, monitor):
        """Test ending a successful conversion operation."""
        operation_id = "conv_success_001"

        # Start conversion
        monitor.start_conversion(operation_id, "/path/to/doc.docx", "docx", 1024000)

        # End conversion successfully
        monitor.end_conversion(
            operation_id,
            success=True,
            conversion_method="markitdown",
        )

        metrics = monitor.ingestion_metrics[operation_id]
        assert metrics.conversion_success is True
        assert metrics.conversion_method == "markitdown"
        assert metrics.conversion_time is not None
        assert metrics.conversion_time >= 0  # Can be 0 if test runs very fast

        # Check global conversion metrics
        conv_metrics = monitor.conversion_metrics
        assert conv_metrics.total_files_processed == 1
        assert conv_metrics.successful_conversions == 1
        assert conv_metrics.failed_conversions == 0
        assert conv_metrics.conversion_methods["markitdown"] == 1
        assert conv_metrics.file_types_processed["docx"] == 1

    def test_end_failed_conversion(self, monitor):
        """Test ending a failed conversion operation."""
        operation_id = "conv_failure_001"
        error_message = "File is password protected"

        # Start conversion
        monitor.start_conversion(
            operation_id, "/path/to/encrypted.xlsx", "xlsx", 512000
        )

        # End conversion with failure
        monitor.end_conversion(
            operation_id,
            success=False,
            conversion_method="markitdown_fallback",
            error=error_message,
        )

        metrics = monitor.ingestion_metrics[operation_id]
        assert metrics.conversion_success is False
        assert metrics.conversion_method == "markitdown_fallback"
        assert metrics.error == error_message

        # Check global conversion metrics
        conv_metrics = monitor.conversion_metrics
        assert conv_metrics.total_files_processed == 1
        assert conv_metrics.successful_conversions == 0
        assert conv_metrics.failed_conversions == 1
        assert conv_metrics.conversion_methods["markitdown_fallback"] == 1
        assert conv_metrics.file_types_processed["xlsx"] == 1

    def test_multiple_conversions_tracking(self, monitor):
        """Test tracking multiple conversion operations."""
        conversions = [
            {
                "id": "conv_001",
                "file_type": "pdf",
                "success": True,
                "method": "markitdown",
            },
            {
                "id": "conv_002",
                "file_type": "docx",
                "success": True,
                "method": "markitdown",
            },
            {
                "id": "conv_003",
                "file_type": "pptx",
                "success": False,
                "method": "markitdown_fallback",
            },
            {
                "id": "conv_004",
                "file_type": "pdf",
                "success": True,
                "method": "markitdown",
            },
        ]

        for conv in conversions:
            monitor.start_conversion(
                conv["id"], f"/path/to/file.{conv['file_type']}", conv["file_type"]
            )
            monitor.end_conversion(
                conv["id"],
                success=conv["success"],
                conversion_method=conv["method"],
                error="Conversion failed" if not conv["success"] else None,
            )

        # Verify global metrics
        conv_metrics = monitor.conversion_metrics
        assert conv_metrics.total_files_processed == 4
        assert conv_metrics.successful_conversions == 3
        assert conv_metrics.failed_conversions == 1
        assert conv_metrics.conversion_methods["markitdown"] == 3
        assert conv_metrics.conversion_methods["markitdown_fallback"] == 1
        assert conv_metrics.file_types_processed["pdf"] == 2
        assert conv_metrics.file_types_processed["docx"] == 1
        assert conv_metrics.file_types_processed["pptx"] == 1

    def test_attachment_processing_tracking(self, monitor):
        """Test tracking attachment processing."""
        # Process multiple attachments
        for _ in range(5):
            monitor.record_attachment_processed()

        assert monitor.conversion_metrics.attachments_processed == 5

    def test_average_conversion_time_calculation(self, monitor):
        """Test that average conversion time is calculated correctly."""
        # Simulate conversions with known durations
        import time

        conversions = [
            {"id": "conv_time_001", "duration": 1.0},
            {"id": "conv_time_002", "duration": 2.0},
            {"id": "conv_time_003", "duration": 3.0},
        ]

        for conv in conversions:
            # Start conversion
            monitor.start_conversion(conv["id"], "/path/to/file.pdf", "pdf")

            # Manually set start time to control duration
            metrics = monitor.ingestion_metrics[conv["id"]]
            start_time = time.time()
            metrics.start_time = start_time - conv["duration"]

            # End conversion
            monitor.end_conversion(
                conv["id"], success=True, conversion_method="markitdown"
            )

        # Check average calculation (should be approximately 2.0)
        expected_average = 2.0
        actual_average = monitor.conversion_metrics.average_conversion_time
        assert abs(actual_average - expected_average) < 0.1  # Allow small tolerance


class TestBatchConversionMetrics:
    """Test batch-level conversion metrics tracking."""

    def test_update_batch_conversion_metrics(self, monitor):
        """Test updating conversion metrics for a batch."""
        batch_id = "batch_001"

        # Start a batch
        monitor.start_batch(batch_id, batch_size=10)

        # Update conversion metrics
        monitor.update_batch_conversion_metrics(
            batch_id,
            converted_files_count=7,
            conversion_failures_count=2,
            attachments_processed_count=3,
            total_conversion_time=25.5,
        )

        batch_metrics = monitor.batch_metrics[batch_id]
        assert batch_metrics.converted_files_count == 7
        assert batch_metrics.conversion_failures_count == 2
        assert batch_metrics.attachments_processed_count == 3
        assert batch_metrics.total_conversion_time == 25.5

    def test_accumulate_batch_conversion_metrics(self, monitor):
        """Test that batch conversion metrics accumulate correctly."""
        batch_id = "batch_accumulate"

        # Start a batch
        monitor.start_batch(batch_id, batch_size=20)

        # Update metrics multiple times
        monitor.update_batch_conversion_metrics(
            batch_id,
            converted_files_count=5,
            conversion_failures_count=1,
            total_conversion_time=10.0,
        )

        monitor.update_batch_conversion_metrics(
            batch_id,
            converted_files_count=3,
            conversion_failures_count=0,
            attachments_processed_count=2,
            total_conversion_time=8.5,
        )

        batch_metrics = monitor.batch_metrics[batch_id]
        assert batch_metrics.converted_files_count == 8
        assert batch_metrics.conversion_failures_count == 1
        assert batch_metrics.attachments_processed_count == 2
        assert batch_metrics.total_conversion_time == 18.5


class TestConversionSummary:
    """Test conversion summary generation."""

    def test_get_conversion_summary(self, monitor):
        """Test getting a comprehensive conversion summary."""
        # Set up some conversion data
        monitor.conversion_metrics.total_files_processed = 10
        monitor.conversion_metrics.successful_conversions = 8
        monitor.conversion_metrics.failed_conversions = 2
        monitor.conversion_metrics.total_conversion_time = 45.0
        # average_conversion_time is now calculated as a property (45.0 / 10 = 4.5)
        monitor.conversion_metrics.attachments_processed = 5
        monitor.conversion_metrics.conversion_methods = {
            "markitdown": 8,
            "markitdown_fallback": 2,
        }
        monitor.conversion_metrics.file_types_processed = {
            "pdf": 4,
            "docx": 3,
            "xlsx": 2,
            "pptx": 1,
        }
        monitor.conversion_metrics.error_types = {
            "PasswordProtectedError": 1,
            "CorruptedFileError": 1,
        }

        summary = monitor.get_conversion_summary()

        assert summary["total_files_processed"] == 10
        assert summary["successful_conversions"] == 8
        assert summary["failed_conversions"] == 2
        assert summary["success_rate"] == 80.0
        assert summary["total_conversion_time"] == 45.0
        assert summary["average_conversion_time"] == 4.5  # 45.0 / 10
        assert summary["attachments_processed"] == 5
        assert summary["conversion_methods"]["markitdown"] == 8
        assert summary["file_types_processed"]["pdf"] == 4
        assert summary["error_types"]["PasswordProtectedError"] == 1

    def test_conversion_summary_with_no_data(self, monitor):
        """Test conversion summary with no conversion data."""
        summary = monitor.get_conversion_summary()

        assert summary["total_files_processed"] == 0
        assert summary["successful_conversions"] == 0
        assert summary["failed_conversions"] == 0
        assert summary["success_rate"] == 0.0
        assert summary["total_conversion_time"] == 0.0
        assert summary["average_conversion_time"] == 0.0
        assert summary["attachments_processed"] == 0
        assert summary["conversion_methods"] == {}
        assert summary["file_types_processed"] == {}
        assert summary["error_types"] == {}


class TestMetricsPersistence:
    """Test saving and loading metrics with conversion data."""

    def test_save_metrics_with_conversion_data(self, monitor, temp_metrics_dir):
        """Test that conversion metrics are included in saved data."""
        # Set up some test data
        operation_id = "test_op_001"
        batch_id = "test_batch_001"

        # Add conversion operation
        monitor.start_conversion(operation_id, "/path/to/test.pdf", "pdf", 1024000)
        monitor.end_conversion(
            operation_id, success=True, conversion_method="markitdown"
        )

        # Add batch with conversion metrics
        monitor.start_batch(batch_id, batch_size=5)
        monitor.update_batch_conversion_metrics(
            batch_id,
            converted_files_count=4,
            conversion_failures_count=1,
            total_conversion_time=12.0,
        )
        monitor.end_batch(batch_id, success_count=4, error_count=1)

        # Save metrics
        monitor.save_metrics()

        # Find the saved file
        metrics_files = list(Path(temp_metrics_dir).glob("ingestion_metrics_*.json"))
        assert len(metrics_files) == 1

        # Load and verify the saved data
        with open(metrics_files[0], encoding="utf-8") as f:
            saved_data = json.load(f)

        # Check ingestion metrics include conversion fields
        assert operation_id in saved_data["ingestion_metrics"]
        op_data = saved_data["ingestion_metrics"][operation_id]
        assert op_data["conversion_attempted"] is True
        assert op_data["conversion_success"] is True
        assert op_data["conversion_method"] == "markitdown"
        assert op_data["original_file_type"] == "pdf"
        assert op_data["file_size"] == 1024000

        # Check batch metrics include conversion fields
        assert batch_id in saved_data["batch_metrics"]
        batch_data = saved_data["batch_metrics"][batch_id]
        assert batch_data["converted_files_count"] == 4
        assert batch_data["conversion_failures_count"] == 1
        assert batch_data["total_conversion_time"] == 12.0

        # Check conversion metrics section
        assert "conversion_metrics" in saved_data
        conv_data = saved_data["conversion_metrics"]
        assert conv_data["total_files_processed"] == 1
        assert conv_data["successful_conversions"] == 1
        assert conv_data["failed_conversions"] == 0
        assert "summary" in conv_data

    def test_clear_metrics_includes_conversion_data(self, monitor):
        """Test that clearing metrics also clears conversion data."""
        # Add some conversion data
        monitor.start_conversion("test_op", "/path/to/file.pdf", "pdf")
        monitor.end_conversion("test_op", success=True, conversion_method="markitdown")
        monitor.record_attachment_processed()

        # Verify data exists
        assert len(monitor.ingestion_metrics) > 0
        assert monitor.conversion_metrics.total_files_processed > 0
        assert monitor.conversion_metrics.attachments_processed > 0

        # Clear metrics
        monitor.clear_metrics()

        # Verify all data is cleared
        assert len(monitor.ingestion_metrics) == 0
        assert len(monitor.batch_metrics) == 0
        assert monitor.conversion_metrics.total_files_processed == 0
        assert monitor.conversion_metrics.successful_conversions == 0
        assert monitor.conversion_metrics.attachments_processed == 0
        assert monitor.conversion_metrics.conversion_methods == {}


class TestIntegratedConversionWorkflow:
    """Test integrated workflow with conversion tracking."""

    def test_complete_conversion_workflow(self, monitor):
        """Test a complete workflow with file conversions and batch processing."""
        batch_id = "workflow_batch"

        # Start batch
        monitor.start_batch(batch_id, batch_size=5, metadata={"source": "confluence"})

        # Process multiple files with conversions
        files = [
            {"id": "doc_001", "type": "pdf", "success": True, "method": "markitdown"},
            {"id": "doc_002", "type": "docx", "success": True, "method": "markitdown"},
            {
                "id": "doc_003",
                "type": "xlsx",
                "success": False,
                "method": "markitdown_fallback",
            },
            {"id": "doc_004", "type": "pptx", "success": True, "method": "markitdown"},
        ]

        successful_conversions = 0
        failed_conversions = 0
        total_conversion_time = 0.0

        for file_data in files:
            # Start conversion
            monitor.start_conversion(
                file_data["id"],
                f"/path/to/{file_data['id']}.{file_data['type']}",
                file_data["type"],
                1024000,
            )

            # End conversion
            monitor.end_conversion(
                file_data["id"],
                success=file_data["success"],
                conversion_method=file_data["method"],
                error="Conversion failed" if not file_data["success"] else None,
            )

            # Track metrics
            if file_data["success"]:
                successful_conversions += 1
            else:
                failed_conversions += 1

            # Add conversion time from metrics
            conversion_time = monitor.ingestion_metrics[file_data["id"]].conversion_time
            if conversion_time:
                total_conversion_time += conversion_time

        # Process some attachments
        for _ in range(2):
            monitor.record_attachment_processed()

        # Update batch conversion metrics
        monitor.update_batch_conversion_metrics(
            batch_id,
            converted_files_count=successful_conversions,
            conversion_failures_count=failed_conversions,
            attachments_processed_count=2,
            total_conversion_time=total_conversion_time,
        )

        # End batch
        monitor.end_batch(
            batch_id,
            success_count=successful_conversions,
            error_count=failed_conversions,
        )

        # Verify global conversion metrics
        conv_metrics = monitor.conversion_metrics
        assert conv_metrics.total_files_processed == 4
        assert conv_metrics.successful_conversions == 3
        assert conv_metrics.failed_conversions == 1
        assert conv_metrics.attachments_processed == 2

        # Verify batch metrics
        batch_metrics = monitor.batch_metrics[batch_id]
        assert batch_metrics.converted_files_count == 3
        assert batch_metrics.conversion_failures_count == 1
        assert batch_metrics.attachments_processed_count == 2

        # Verify conversion summary
        summary = monitor.get_conversion_summary()
        assert summary["success_rate"] == 75.0  # 3 out of 4 successful
        assert summary["conversion_methods"]["markitdown"] == 3
        assert summary["conversion_methods"]["markitdown_fallback"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
