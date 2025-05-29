"""
Unit tests for monitoring extensions - file conversion tracking and metrics.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

from qdrant_loader.core.monitoring.ingestion_metrics import (
    IngestionMonitor,
    IngestionMetrics,
    BatchMetrics,
    ConversionMetrics,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def monitor(temp_dir):
    """Create an ingestion monitor for testing."""
    return IngestionMonitor(temp_dir)


class TestConversionMetricsDataClass:
    """Test the new ConversionMetrics data class."""

    def test_conversion_metrics_initialization(self):
        """Test ConversionMetrics initialization with default values."""
        metrics = ConversionMetrics()

        assert metrics.total_files_processed == 0
        assert metrics.successful_conversions == 0
        assert metrics.failed_conversions == 0
        assert metrics.total_conversion_time == 0.0
        assert metrics.attachments_processed == 0
        assert metrics.conversion_methods == {}
        assert metrics.file_types_processed == {}
        assert metrics.error_types == {}

    def test_conversion_metrics_with_values(self):
        """Test ConversionMetrics initialization with custom values."""
        metrics = ConversionMetrics(
            total_files_processed=10,
            successful_conversions=8,
            failed_conversions=2,
            total_conversion_time=25.5,
            attachments_processed=5,
            conversion_methods={"markitdown": 8, "markitdown_fallback": 2},
            file_types_processed={"pdf": 5, "docx": 3, "xlsx": 2},
            error_types={"password_protected": 1, "corrupted": 1},
        )

        assert metrics.total_files_processed == 10
        assert metrics.successful_conversions == 8
        assert metrics.failed_conversions == 2
        assert metrics.total_conversion_time == 25.5
        assert metrics.attachments_processed == 5
        assert metrics.conversion_methods["markitdown"] == 8
        assert metrics.file_types_processed["pdf"] == 5
        assert metrics.error_types["password_protected"] == 1


class TestEnhancedIngestionMetrics:
    """Test the enhanced IngestionMetrics with conversion fields."""

    def test_ingestion_metrics_conversion_fields(self):
        """Test that IngestionMetrics includes conversion fields."""
        metrics = IngestionMetrics(
            start_time=1234567890.0,
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

    def test_ingestion_metrics_default_conversion_fields(self):
        """Test default values for conversion fields."""
        metrics = IngestionMetrics(
            start_time=1234567890.0,
        )

        assert metrics.conversion_attempted is False
        assert metrics.conversion_success is False
        assert metrics.conversion_time is None
        assert metrics.conversion_method is None
        assert metrics.original_file_type is None
        assert metrics.file_size is None


class TestEnhancedBatchMetrics:
    """Test the enhanced BatchMetrics with conversion fields."""

    def test_batch_metrics_conversion_fields(self):
        """Test that BatchMetrics includes conversion fields."""
        metrics = BatchMetrics(
            batch_size=10,
            start_time=1234567890.0,
            converted_files_count=5,
            conversion_failures_count=2,
            attachments_processed_count=3,
            total_conversion_time=15.5,
        )

        assert metrics.converted_files_count == 5
        assert metrics.conversion_failures_count == 2
        assert metrics.attachments_processed_count == 3
        assert metrics.total_conversion_time == 15.5

    def test_batch_metrics_default_conversion_fields(self):
        """Test default values for conversion fields."""
        metrics = BatchMetrics(
            batch_size=10,
            start_time=1234567890.0,
        )

        assert metrics.converted_files_count == 0
        assert metrics.conversion_failures_count == 0
        assert metrics.attachments_processed_count == 0
        assert metrics.total_conversion_time == 0.0


class TestConversionTracking:
    """Test file conversion tracking methods."""

    def test_start_conversion(self, monitor):
        """Test starting conversion tracking."""
        monitor.start_conversion("conv_001", "/path/to/file.pdf", "pdf", 1024000)

        assert "conv_001" in monitor.ingestion_metrics
        metrics = monitor.ingestion_metrics["conv_001"]
        assert metrics.conversion_attempted is True
        assert metrics.original_file_type == "pdf"
        assert metrics.file_size == 1024000

    def test_end_conversion_success(self, monitor):
        """Test ending conversion tracking with success."""
        # Start conversion first
        monitor.start_conversion("conv_001", "/path/to/file.pdf", "pdf", 1024000)

        # End conversion successfully
        monitor.end_conversion("conv_001", success=True, conversion_method="markitdown")

        metrics = monitor.ingestion_metrics["conv_001"]
        assert metrics.conversion_success is True
        assert metrics.conversion_method == "markitdown"
        assert metrics.conversion_time is not None
        assert metrics.conversion_time > 0

    def test_end_conversion_failure(self, monitor):
        """Test ending conversion tracking with failure."""
        # Start conversion first
        monitor.start_conversion("conv_001", "/path/to/file.pdf", "pdf", 1024000)

        # End conversion with failure
        monitor.end_conversion(
            "conv_001",
            success=False,
            conversion_method="markitdown_fallback",
            error="Password protected file",
        )

        metrics = monitor.ingestion_metrics["conv_001"]
        assert metrics.conversion_success is False
        assert metrics.conversion_method == "markitdown_fallback"
        assert metrics.error == "Password protected file"

    def test_end_conversion_without_start(self, monitor):
        """Test ending conversion without starting (should handle gracefully)."""
        # This should not raise an exception
        monitor.end_conversion("nonexistent_conv", success=True)

        # Should not create a metrics entry
        assert "nonexistent_conv" not in monitor.ingestion_metrics

    def test_multiple_conversions(self, monitor):
        """Test tracking multiple conversions."""
        conversions = [
            ("conv_001", "file1.pdf", "pdf", True, "markitdown"),
            ("conv_002", "file2.docx", "docx", False, "markitdown_fallback"),
            ("conv_003", "file3.xlsx", "xlsx", True, "markitdown"),
        ]

        for conv_id, filename, file_type, success, method in conversions:
            monitor.start_conversion(conv_id, f"/path/{filename}", file_type, 1024000)
            monitor.end_conversion(conv_id, success=success, conversion_method=method)

        assert len(monitor.ingestion_metrics) == 3

        # Check success/failure counts
        successful = sum(
            1 for m in monitor.ingestion_metrics.values() if m.conversion_success
        )
        failed = sum(
            1 for m in monitor.ingestion_metrics.values() if not m.conversion_success
        )

        assert successful == 2
        assert failed == 1


class TestAttachmentProcessingTracking:
    """Test attachment processing tracking."""

    def test_record_attachment_processed(self, monitor):
        """Test recording attachment processing."""
        initial_count = monitor.conversion_metrics.attachments_processed

        monitor.record_attachment_processed()

        assert monitor.conversion_metrics.attachments_processed == initial_count + 1

    def test_multiple_attachments_processed(self, monitor):
        """Test recording multiple attachment processing."""
        initial_count = monitor.conversion_metrics.attachments_processed

        for _ in range(5):
            monitor.record_attachment_processed()

        assert monitor.conversion_metrics.attachments_processed == initial_count + 5


class TestBatchConversionMetrics:
    """Test batch-level conversion metrics."""

    def test_update_batch_conversion_metrics(self, monitor):
        """Test updating batch conversion metrics."""
        batch_id = "test_batch"
        monitor.start_batch(batch_id, batch_size=10)

        monitor.update_batch_conversion_metrics(
            batch_id,
            converted_files_count=5,
            conversion_failures_count=2,
            attachments_processed_count=3,
            total_conversion_time=15.5,
        )

        batch_metrics = monitor.batch_metrics[batch_id]
        assert batch_metrics.converted_files_count == 5
        assert batch_metrics.conversion_failures_count == 2
        assert batch_metrics.attachments_processed_count == 3
        assert batch_metrics.total_conversion_time == 15.5

    def test_update_batch_conversion_metrics_accumulation(self, monitor):
        """Test that batch conversion metrics accumulate correctly."""
        batch_id = "test_batch"
        monitor.start_batch(batch_id, batch_size=10)

        # First update
        monitor.update_batch_conversion_metrics(
            batch_id,
            converted_files_count=3,
            conversion_failures_count=1,
            total_conversion_time=8.0,
        )

        # Second update
        monitor.update_batch_conversion_metrics(
            batch_id,
            converted_files_count=2,
            conversion_failures_count=1,
            attachments_processed_count=2,
            total_conversion_time=7.5,
        )

        batch_metrics = monitor.batch_metrics[batch_id]
        assert batch_metrics.converted_files_count == 5
        assert batch_metrics.conversion_failures_count == 2
        assert batch_metrics.attachments_processed_count == 2
        assert batch_metrics.total_conversion_time == 15.5

    def test_update_nonexistent_batch(self, monitor):
        """Test updating metrics for nonexistent batch (should handle gracefully)."""
        # This should not raise an exception
        monitor.update_batch_conversion_metrics(
            "nonexistent_batch", converted_files_count=1
        )

        # Should not create a batch entry
        assert "nonexistent_batch" not in monitor.batch_metrics


class TestConversionSummary:
    """Test conversion summary generation."""

    def test_get_conversion_summary_empty(self, monitor):
        """Test conversion summary with no data."""
        summary = monitor.get_conversion_summary()

        assert summary["total_files_processed"] == 0
        assert summary["successful_conversions"] == 0
        assert summary["failed_conversions"] == 0
        assert summary["success_rate"] == 0.0
        assert summary["average_conversion_time"] == 0.0
        assert summary["attachments_processed"] == 0
        assert summary["conversion_methods"] == {}
        assert summary["file_types_processed"] == {}
        assert summary["error_types"] == {}

    def test_get_conversion_summary_with_data(self, monitor):
        """Test conversion summary with conversion data."""
        # Add some conversion data
        conversions = [
            ("conv_001", "file1.pdf", "pdf", True, "markitdown", None),
            (
                "conv_002",
                "file2.docx",
                "docx",
                False,
                "markitdown_fallback",
                "Password protected",
            ),
            ("conv_003", "file3.xlsx", "xlsx", True, "markitdown", None),
            (
                "conv_004",
                "file4.pptx",
                "pptx",
                False,
                "markitdown_fallback",
                "Corrupted file",
            ),
        ]

        for conv_id, filename, file_type, success, method, error in conversions:
            monitor.start_conversion(conv_id, f"/path/{filename}", file_type, 1024000)
            monitor.end_conversion(
                conv_id, success=success, conversion_method=method, error=error
            )

        # Add some attachment processing
        for _ in range(3):
            monitor.record_attachment_processed()

        summary = monitor.get_conversion_summary()

        assert summary["total_files_processed"] == 4
        assert summary["successful_conversions"] == 2
        assert summary["failed_conversions"] == 2
        assert summary["success_rate"] == 50.0
        assert summary["average_conversion_time"] > 0
        assert summary["attachments_processed"] == 3

        # Check method distribution
        assert summary["conversion_methods"]["markitdown"] == 2
        assert summary["conversion_methods"]["markitdown_fallback"] == 2

        # Check file type distribution
        assert summary["file_types_processed"]["pdf"] == 1
        assert summary["file_types_processed"]["docx"] == 1
        assert summary["file_types_processed"]["xlsx"] == 1
        assert summary["file_types_processed"]["pptx"] == 1

        # Check error types - the implementation tracks by error type name, not message
        # Since we're passing string errors, they get classified as "Unknown"
        assert summary["error_types"]["Unknown"] == 2

    def test_get_conversion_summary_success_rate_calculation(self, monitor):
        """Test success rate calculation in conversion summary."""
        # Add 7 successful and 3 failed conversions
        for i in range(10):
            conv_id = f"conv_{i:03d}"
            success = i < 7  # First 7 are successful
            method = "markitdown" if success else "markitdown_fallback"

            monitor.start_conversion(conv_id, f"/path/file{i}.pdf", "pdf", 1024000)
            monitor.end_conversion(conv_id, success=success, conversion_method=method)

        summary = monitor.get_conversion_summary()

        assert summary["total_files_processed"] == 10
        assert summary["successful_conversions"] == 7
        assert summary["failed_conversions"] == 3
        assert summary["success_rate"] == 70.0


class TestMetricsPersistence:
    """Test metrics persistence with conversion data."""

    def test_save_metrics_includes_conversion_data(self, monitor):
        """Test that saved metrics include conversion data."""
        # Add conversion data
        monitor.start_conversion("conv_001", "/path/file.pdf", "pdf", 1024000)
        monitor.end_conversion("conv_001", success=True, conversion_method="markitdown")

        # Add attachment processing
        monitor.record_attachment_processed()

        # Start a batch and add conversion metrics
        batch_id = "test_batch"
        monitor.start_batch(batch_id, batch_size=5)
        monitor.update_batch_conversion_metrics(
            batch_id,
            converted_files_count=1,
            attachments_processed_count=1,
            total_conversion_time=2.5,
        )
        monitor.end_batch(batch_id, success_count=1, error_count=0)

        # Save metrics
        monitor.save_metrics()

        # Find the saved file
        metrics_dir = Path(monitor.metrics_dir)
        metrics_files = list(metrics_dir.glob("ingestion_metrics_*.json"))
        assert len(metrics_files) == 1

        # Load and verify saved data
        with open(metrics_files[0], "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        # Check ingestion metrics include conversion data
        assert "ingestion_metrics" in saved_data
        conv_metrics = saved_data["ingestion_metrics"]["conv_001"]
        assert conv_metrics["conversion_attempted"] is True
        assert conv_metrics["conversion_success"] is True
        assert conv_metrics["conversion_method"] == "markitdown"
        assert conv_metrics["original_file_type"] == "pdf"

        # Check batch metrics include conversion data
        assert "batch_metrics" in saved_data
        batch_metrics = saved_data["batch_metrics"][batch_id]
        assert batch_metrics["converted_files_count"] == 1
        assert batch_metrics["attachments_processed_count"] == 1

        # Check conversion metrics summary
        assert "conversion_metrics" in saved_data
        conversion_summary = saved_data["conversion_metrics"]
        assert conversion_summary["total_files_processed"] == 1
        assert conversion_summary["successful_conversions"] == 1
        assert conversion_summary["attachments_processed"] == 1

    def test_clear_metrics_resets_conversion_data(self, monitor):
        """Test that clearing metrics resets conversion data."""
        # Add conversion data
        monitor.start_conversion("conv_001", "/path/file.pdf", "pdf", 1024000)
        monitor.end_conversion("conv_001", success=True, conversion_method="markitdown")
        monitor.record_attachment_processed()

        # Verify data exists
        assert len(monitor.ingestion_metrics) == 1
        assert monitor.conversion_metrics.attachments_processed == 1

        # Clear metrics
        monitor.clear_metrics()

        # Verify conversion data is reset
        assert len(monitor.ingestion_metrics) == 0
        assert monitor.conversion_metrics.total_files_processed == 0
        assert monitor.conversion_metrics.successful_conversions == 0
        assert monitor.conversion_metrics.failed_conversions == 0
        assert monitor.conversion_metrics.attachments_processed == 0
        assert monitor.conversion_metrics.conversion_methods == {}
        assert monitor.conversion_metrics.file_types_processed == {}
        assert monitor.conversion_metrics.error_types == {}


class TestIntegratedConversionWorkflow:
    """Test integrated conversion workflow with all features."""

    def test_complete_conversion_workflow(self, monitor):
        """Test a complete conversion workflow with all tracking features."""
        batch_id = "integration_batch"
        monitor.start_batch(batch_id, batch_size=5, metadata={"source": "confluence"})

        # Process multiple files with different outcomes
        files = [
            ("conv_001", "doc1.pdf", "pdf", True, "markitdown"),
            ("conv_002", "doc2.docx", "docx", False, "markitdown_fallback"),
            ("conv_003", "doc3.xlsx", "xlsx", True, "markitdown"),
        ]

        successful_conversions = 0
        failed_conversions = 0
        total_conversion_time = 0.0

        for conv_id, filename, file_type, success, method in files:
            # Start conversion tracking
            monitor.start_conversion(conv_id, f"/docs/{filename}", file_type, 1024000)

            # End conversion tracking
            error = "Password protected" if not success else None
            monitor.end_conversion(
                conv_id, success=success, conversion_method=method, error=error
            )

            # Track metrics
            if success:
                successful_conversions += 1
            else:
                failed_conversions += 1

            conversion_time = monitor.ingestion_metrics[conv_id].conversion_time
            if conversion_time:
                total_conversion_time += conversion_time

        # Process some attachments
        for _ in range(2):
            monitor.record_attachment_processed()

        # Update batch metrics
        monitor.update_batch_conversion_metrics(
            batch_id,
            converted_files_count=successful_conversions,
            conversion_failures_count=failed_conversions,
            attachments_processed_count=2,
            total_conversion_time=total_conversion_time,
        )

        monitor.end_batch(
            batch_id,
            success_count=successful_conversions,
            error_count=failed_conversions,
        )

        # Verify comprehensive tracking
        summary = monitor.get_conversion_summary()
        assert summary["total_files_processed"] == 3
        assert summary["successful_conversions"] == 2
        assert summary["failed_conversions"] == 1
        assert summary["success_rate"] == pytest.approx(66.7, rel=0.1)
        assert summary["attachments_processed"] == 2

        # Verify batch metrics
        batch_metrics = monitor.batch_metrics[batch_id]
        assert batch_metrics.converted_files_count == 2
        assert batch_metrics.conversion_failures_count == 1
        assert batch_metrics.attachments_processed_count == 2

        # Verify method and file type tracking
        assert summary["conversion_methods"]["markitdown"] == 2
        assert summary["conversion_methods"]["markitdown_fallback"] == 1
        assert summary["file_types_processed"]["pdf"] == 1
        assert summary["file_types_processed"]["docx"] == 1
        assert summary["file_types_processed"]["xlsx"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
