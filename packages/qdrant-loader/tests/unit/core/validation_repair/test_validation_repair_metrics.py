"""Comprehensive tests for ValidationMetricsCollector class."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, UTC, timedelta
from typing import Any, Dict

from qdrant_loader.core.validation_repair.metrics import ValidationMetricsCollector
from qdrant_loader.core.validation_repair.models import (
    ValidationIssue,
    ValidationCategory,
    ValidationSeverity,
    RepairAction,
    RepairResult,
    ValidationReport,
)


class TestValidationMetricsCollector:
    """Test suite for ValidationMetricsCollector class."""

    @pytest.fixture
    def metrics_collector(self):
        """Create ValidationMetricsCollector instance with default settings."""
        return ValidationMetricsCollector(
            enable_prometheus=True,
            enable_statsd=False,
            metrics_retention_hours=24,
        )

    @pytest.fixture
    def metrics_collector_with_statsd(self):
        """Create ValidationMetricsCollector instance with StatsD enabled."""
        return ValidationMetricsCollector(
            enable_prometheus=True,
            enable_statsd=True,
            statsd_host="localhost",
            statsd_port=8125,
            metrics_retention_hours=24,
        )

    @pytest.fixture
    def metrics_collector_prometheus_disabled(self):
        """Create ValidationMetricsCollector instance with Prometheus disabled."""
        return ValidationMetricsCollector(
            enable_prometheus=False,
            enable_statsd=False,
            metrics_retention_hours=24,
        )

    @pytest.fixture
    def sample_validation_report(self):
        """Create a sample validation report."""
        report = ValidationReport()

        # Add sample issues
        issues = [
            ValidationIssue(
                category=ValidationCategory.MISSING_MAPPING,
                severity=ValidationSeverity.WARNING,
                title="Missing Mapping",
                description="Test issue 1",
                auto_repairable=True,
                repair_priority=6,
            ),
            ValidationIssue(
                category=ValidationCategory.DATA_MISMATCH,
                severity=ValidationSeverity.ERROR,
                title="Data Mismatch",
                description="Test issue 2",
                auto_repairable=False,
                repair_priority=8,
            ),
        ]

        for issue in issues:
            report.add_issue(issue)

        report.scanned_entities = {
            "missing_mapping_scanner": 100,
            "data_mismatch_scanner": 50,
        }

        report.system_health_score = 85.5
        report.validation_duration_ms = 1500.0

        return report

    @pytest.fixture
    def sample_repair_results(self):
        """Create sample repair results."""
        return [
            RepairResult(
                issue_id="issue-1",
                action_taken=RepairAction.CREATE_MAPPING,
                success=True,
                details={"mapping_id": "new-mapping-1"},
                execution_time_ms=150.0,
            ),
            RepairResult(
                issue_id="issue-2",
                action_taken=RepairAction.DELETE_ORPHANED,
                success=False,
                error_message="Deletion failed",
                execution_time_ms=75.0,
            ),
            RepairResult(
                issue_id="issue-3",
                action_taken=RepairAction.SYNC_ENTITIES,
                success=True,
                details={"synced_entities": 5},
                execution_time_ms=300.0,
            ),
        ]

    # Test initialization
    def test_init_default_settings(self):
        """Test initialization with default settings."""
        collector = ValidationMetricsCollector()

        assert collector.enable_prometheus is True
        assert collector.enable_statsd is False
        assert collector.statsd_host == "localhost"
        assert collector.statsd_port == 8125
        assert collector.metrics_retention_hours == 24
        assert collector._active_validations_count == 0
        assert collector._validation_queue_size == 0
        assert collector._last_health_score == 100.0
        assert len(collector._validation_history) == 0
        assert len(collector._repair_history) == 0

    @patch("qdrant_loader.core.validation_repair.metrics.statsd")
    def test_init_custom_settings(self, mock_statsd_module):
        """Test ValidationMetricsCollector initialization with custom settings."""
        mock_client_instance = MagicMock()
        mock_statsd_module.StatsClient.return_value = mock_client_instance

        collector = ValidationMetricsCollector(
            enable_prometheus=False,
            enable_statsd=True,
            statsd_host="custom-host",
            statsd_port=9125,
            metrics_retention_hours=48,
        )

        assert collector.enable_prometheus is False
        assert collector.enable_statsd is True
        assert collector.statsd_host == "custom-host"
        assert collector.statsd_port == 9125
        assert collector.metrics_retention_hours == 48
        mock_statsd_module.StatsClient.assert_called_once_with(host="custom-host", port=9125)

    @patch("qdrant_loader.core.validation_repair.metrics.statsd")
    def test_init_with_statsd_client_creation(self, mock_statsd_module):
        """Test StatsD client creation when enabled."""
        mock_client_instance = MagicMock()
        mock_statsd_module.StatsClient.return_value = mock_client_instance

        collector = ValidationMetricsCollector(enable_statsd=True)

        mock_statsd_module.StatsClient.assert_called_once_with(host="localhost", port=8125)
        assert collector._statsd_client == mock_client_instance

    # Test record_validation_started method
    @patch("qdrant_loader.core.validation_repair.metrics.ACTIVE_VALIDATIONS")
    def test_record_validation_started_success(
        self, mock_active_validations, metrics_collector
    ):
        """Test successful recording of validation start."""
        validation_id = "validation-123"
        scanners = ["missing_mapping", "data_mismatch"]
        metadata = {"user": "test", "project": "test-project"}

        metrics_collector.record_validation_started(validation_id, scanners, metadata)

        assert metrics_collector._active_validations_count == 1
        mock_active_validations.set.assert_called_once_with(1)

        # Check validation history
        assert len(metrics_collector._validation_history) == 1
        record = metrics_collector._validation_history[0]
        assert record["validation_id"] == validation_id
        assert record["scanners"] == scanners
        assert record["metadata"] == metadata
        assert record["status"] == "running"
        assert isinstance(record["start_time"], datetime)

    def test_record_validation_started_prometheus_disabled(
        self, metrics_collector_prometheus_disabled
    ):
        """Test validation start recording with Prometheus disabled."""
        validation_id = "validation-123"
        scanners = ["missing_mapping"]

        metrics_collector_prometheus_disabled.record_validation_started(
            validation_id, scanners
        )

        assert metrics_collector_prometheus_disabled._active_validations_count == 1
        assert len(metrics_collector_prometheus_disabled._validation_history) == 1

    @patch("qdrant_loader.core.validation_repair.metrics.statsd")
    def test_record_validation_started_with_statsd(
        self, mock_statsd_module, metrics_collector_with_statsd
    ):
        """Test validation start recording with StatsD enabled."""
        mock_client_instance = MagicMock()
        mock_statsd_module.StatsClient.return_value = mock_client_instance

        # Reinitialize to create StatsD client
        collector = ValidationMetricsCollector(enable_statsd=True)
        collector._statsd_client = mock_client_instance

        validation_id = "validation-123"
        scanners = ["missing_mapping", "data_mismatch"]

        collector.record_validation_started(validation_id, scanners)

        mock_client_instance.incr.assert_any_call("validation.started")
        mock_client_instance.incr.assert_any_call(
            "validation.scanner.missing_mapping.started"
        )
        mock_client_instance.incr.assert_any_call(
            "validation.scanner.data_mismatch.started"
        )

    def test_record_validation_started_empty_metadata(self, metrics_collector):
        """Test validation start recording with None metadata."""
        validation_id = "validation-123"
        scanners = ["missing_mapping"]

        metrics_collector.record_validation_started(validation_id, scanners, None)

        record = metrics_collector._validation_history[0]
        assert record["metadata"] == {}

    # Test record_validation_completed method
    @patch("qdrant_loader.core.validation_repair.metrics.VALIDATION_OPERATIONS_TOTAL")
    @patch("qdrant_loader.core.validation_repair.metrics.VALIDATION_DURATION_SECONDS")
    @patch("qdrant_loader.core.validation_repair.metrics.VALIDATION_ISSUES_FOUND")
    @patch("qdrant_loader.core.validation_repair.metrics.VALIDATION_HEALTH_SCORE")
    @patch("qdrant_loader.core.validation_repair.metrics.ACTIVE_VALIDATIONS")
    def test_record_validation_completed_success(
        self,
        mock_active_validations,
        mock_health_score,
        mock_issues_found,
        mock_duration,
        mock_operations_total,
        metrics_collector,
        sample_validation_report,
    ):
        """Test successful recording of validation completion."""
        # First start a validation
        validation_id = "validation-123"
        metrics_collector.record_validation_started(validation_id, ["test_scanner"])

        duration_seconds = 2.5

        metrics_collector.record_validation_completed(
            validation_id, sample_validation_report, duration_seconds, success=True
        )

        # Check active validations count decreased
        assert metrics_collector._active_validations_count == 0
        mock_active_validations.set.assert_called_with(0)

        # Check statistics updates
        assert metrics_collector._stats["total_validations"] == 1
        assert metrics_collector._stats["successful_validations"] == 1
        assert metrics_collector._stats["total_issues_found"] == 2

        # Check Prometheus metrics
        mock_operations_total.labels.assert_called()
        mock_duration.labels.assert_called()
        mock_issues_found.labels.assert_called()
        mock_health_score.set.assert_called_with(85.5)

        # Check validation history update
        record = metrics_collector._validation_history[0]
        assert record["status"] == "completed"
        assert record["duration_seconds"] == duration_seconds
        assert record["report"] == sample_validation_report
        assert record["issues_found"] == 2
        assert record["health_score"] == 85.5

    def test_record_validation_completed_failure(self, metrics_collector):
        """Test recording of failed validation completion."""
        validation_id = "validation-123"
        metrics_collector.record_validation_started(validation_id, ["test_scanner"])

        duration_seconds = 1.0
        sample_report = ValidationReport()

        metrics_collector.record_validation_completed(
            validation_id, sample_report, duration_seconds, success=False
        )

        assert metrics_collector._stats["total_validations"] == 1
        assert metrics_collector._stats["successful_validations"] == 0
        assert metrics_collector._stats["failed_validations"] == 1

        record = metrics_collector._validation_history[0]
        assert record["status"] == "failed"

    @patch("qdrant_loader.core.validation_repair.metrics.statsd")
    def test_record_validation_completed_with_statsd(
        self, mock_statsd_module, sample_validation_report
    ):
        """Test validation completion recording with StatsD."""
        mock_client_instance = MagicMock()
        mock_statsd_module.StatsClient.return_value = mock_client_instance

        collector = ValidationMetricsCollector(enable_statsd=True)
        collector._statsd_client = mock_client_instance

        validation_id = "validation-123"
        collector.record_validation_started(validation_id, ["test_scanner"])

        duration_seconds = 2.5
        collector.record_validation_completed(
            validation_id, sample_validation_report, duration_seconds, success=True
        )

        mock_client_instance.incr.assert_any_call("validation.completed.success")
        mock_client_instance.timing.assert_called_with("validation.duration", 2500.0)
        mock_client_instance.gauge.assert_any_call("validation.health_score", 85.5)
        mock_client_instance.gauge.assert_any_call("validation.issues_found", 2)

    def test_record_validation_completed_nonexistent_validation(
        self, metrics_collector, sample_validation_report
    ):
        """Test completion recording for non-existent validation."""
        validation_id = "nonexistent-validation"
        duration_seconds = 1.0

        # Should not raise exception
        metrics_collector.record_validation_completed(
            validation_id, sample_validation_report, duration_seconds, success=True
        )

        # Statistics should still be updated
        assert metrics_collector._stats["total_validations"] == 1

    # Test record_validation_failed method
    @patch("qdrant_loader.core.validation_repair.metrics.VALIDATION_OPERATIONS_TOTAL")
    @patch("qdrant_loader.core.validation_repair.metrics.ACTIVE_VALIDATIONS")
    def test_record_validation_failed_success(
        self, mock_active_validations, mock_operations_total, metrics_collector
    ):
        """Test successful recording of validation failure."""
        validation_id = "validation-123"
        metrics_collector.record_validation_started(validation_id, ["test_scanner"])

        error_message = "Connection timeout"
        duration_seconds = 1.5

        metrics_collector.record_validation_failed(
            validation_id, error_message, duration_seconds
        )

        # Check active validations count decreased
        assert metrics_collector._active_validations_count == 0
        mock_active_validations.set.assert_called_with(0)

        # Check statistics
        assert metrics_collector._stats["total_validations"] == 1
        assert metrics_collector._stats["failed_validations"] == 1

        # Check error tracking
        assert metrics_collector._error_tracking[error_message] == 1

        # Check validation history
        record = metrics_collector._validation_history[0]
        assert record["status"] == "failed"
        assert record["error"] == error_message
        assert record["duration_seconds"] == duration_seconds

    def test_record_validation_failed_multiple_same_errors(self, metrics_collector):
        """Test error tracking with multiple same errors."""
        error_message = "Database connection failed"

        for i in range(3):
            validation_id = f"validation-{i}"
            metrics_collector.record_validation_started(validation_id, ["test_scanner"])
            metrics_collector.record_validation_failed(
                validation_id, error_message, 1.0
            )

        assert metrics_collector._error_tracking[error_message] == 3

    # Test record_repair_started method
    def test_record_repair_started_success(self, metrics_collector):
        """Test successful recording of repair start."""
        repair_id = "repair-123"
        issues = [
            ValidationIssue(
                category=ValidationCategory.MISSING_MAPPING,
                severity=ValidationSeverity.WARNING,
                title="Test Issue 1",
                description="Test",
                auto_repairable=True,
                repair_priority=6,
            ),
            ValidationIssue(
                category=ValidationCategory.DATA_MISMATCH,
                severity=ValidationSeverity.ERROR,
                title="Test Issue 2",
                description="Test",
                auto_repairable=False,
                repair_priority=8,
            ),
        ]
        metadata = {"repair_type": "auto", "batch_size": 2}

        metrics_collector.record_repair_started(repair_id, issues, metadata)

        # Check repair history
        assert len(metrics_collector._repair_history) == 1
        record = metrics_collector._repair_history[0]
        assert record["repair_id"] == repair_id
        assert record["issues"] == issues
        assert record["issue_count"] == 2
        assert record["metadata"] == metadata
        assert record["status"] == "running"
        assert isinstance(record["start_time"], datetime)

    @patch("qdrant_loader.core.validation_repair.metrics.statsd")
    def test_record_repair_started_with_statsd(self, mock_statsd_module):
        """Test repair start recording with StatsD."""
        mock_client_instance = MagicMock()
        mock_statsd_module.StatsClient.return_value = mock_client_instance

        collector = ValidationMetricsCollector(enable_statsd=True)
        collector._statsd_client = mock_client_instance

        repair_id = "repair-123"
        issues = [
            ValidationIssue(
                category=ValidationCategory.MISSING_MAPPING,
                severity=ValidationSeverity.WARNING,
                title="Test Issue 1",
                description="Test",
                auto_repairable=True,
                repair_priority=6,
            ),
            ValidationIssue(
                category=ValidationCategory.DATA_MISMATCH,
                severity=ValidationSeverity.ERROR,
                title="Test Issue 2",
                description="Test",
                auto_repairable=False,
                repair_priority=8,
            ),
        ]

        collector.record_repair_started(repair_id, issues)

        mock_client_instance.incr.assert_called_with("repair.started")
        mock_client_instance.gauge.assert_called_with("repair.issues_count", 2)

    # Test record_repair_completed method
    @patch("qdrant_loader.core.validation_repair.metrics.REPAIR_OPERATIONS_TOTAL")
    @patch("qdrant_loader.core.validation_repair.metrics.REPAIR_DURATION_SECONDS")
    @patch("qdrant_loader.core.validation_repair.metrics.VALIDATION_ISSUES_RESOLVED")
    def test_record_repair_completed_success(
        self,
        mock_issues_resolved,
        mock_duration,
        mock_operations_total,
        metrics_collector,
        sample_repair_results,
    ):
        """Test successful recording of repair completion."""
        repair_id = "repair-123"
        issues = [MagicMock(), MagicMock(), MagicMock()]
        metrics_collector.record_repair_started(repair_id, issues)

        duration_seconds = 3.0

        with patch.object(metrics_collector, "_update_repair_success_rates"):
            metrics_collector.record_repair_completed(
                repair_id, sample_repair_results, duration_seconds
            )

        # Check statistics
        assert metrics_collector._stats["total_repairs"] == 3
        assert metrics_collector._stats["successful_repairs"] == 2
        assert metrics_collector._stats["failed_repairs"] == 1
        assert metrics_collector._stats["total_issues_resolved"] == 2

        # Check repair history
        record = metrics_collector._repair_history[0]
        assert record["status"] == "completed"
        assert record["results"] == sample_repair_results
        assert record["successful_repairs"] == 2
        assert record["failed_repairs"] == 1
        assert record["duration_seconds"] == duration_seconds

        # Check Prometheus metrics calls
        mock_operations_total.labels.assert_called()
        mock_duration.labels.assert_called()
        mock_issues_resolved.labels.assert_called()

    def test_record_repair_completed_empty_results(self, metrics_collector):
        """Test repair completion recording with empty results."""
        repair_id = "repair-123"
        metrics_collector.record_repair_started(repair_id, [])

        duration_seconds = 1.0
        results = []

        with patch.object(metrics_collector, "_update_repair_success_rates"):
            metrics_collector.record_repair_completed(
                repair_id, results, duration_seconds
            )

        assert metrics_collector._stats["total_repairs"] == 0
        assert metrics_collector._stats["successful_repairs"] == 0
        assert metrics_collector._stats["failed_repairs"] == 0

    @patch("qdrant_loader.core.validation_repair.metrics.statsd")
    def test_record_repair_completed_with_statsd(
        self, mock_statsd_module, sample_repair_results
    ):
        """Test repair completion recording with StatsD."""
        mock_client_instance = MagicMock()
        mock_statsd_module.StatsClient.return_value = mock_client_instance

        collector = ValidationMetricsCollector(enable_statsd=True)
        collector._statsd_client = mock_client_instance

        repair_id = "repair-123"
        collector.record_repair_started(repair_id, [])

        duration_seconds = 3.0

        with patch.object(collector, "_update_repair_success_rates"):
            collector.record_repair_completed(
                repair_id, sample_repair_results, duration_seconds
            )

        mock_client_instance.incr.assert_any_call("repair.completed")
        mock_client_instance.timing.assert_called_with("repair.duration", 3000.0)
        mock_client_instance.gauge.assert_any_call("repair.success_count", 2)
        mock_client_instance.gauge.assert_any_call("repair.failure_count", 1)

    # Test record_repair_failed method
    def test_record_repair_failed_success(self, metrics_collector):
        """Test successful recording of repair failure."""
        repair_id = "repair-123"
        metrics_collector.record_repair_started(repair_id, [])

        error_message = "Repair operation failed"
        duration_seconds = 0.5

        metrics_collector.record_repair_failed(
            repair_id, error_message, duration_seconds
        )

        # Check error tracking
        assert metrics_collector._error_tracking[error_message] == 1

        # Check repair history
        record = metrics_collector._repair_history[0]
        assert record["status"] == "failed"
        assert record["error"] == error_message
        assert record["duration_seconds"] == duration_seconds

    @patch("qdrant_loader.core.validation_repair.metrics.statsd")
    def test_record_repair_failed_with_statsd(self, mock_statsd_module):
        """Test repair failure recording with StatsD."""
        mock_client_instance = MagicMock()
        mock_statsd_module.StatsClient.return_value = mock_client_instance

        collector = ValidationMetricsCollector(enable_statsd=True)
        collector._statsd_client = mock_client_instance

        repair_id = "repair-123"
        collector.record_repair_started(repair_id, [])

        error_message = "Repair failed"
        duration_seconds = 0.5

        collector.record_repair_failed(repair_id, error_message, duration_seconds)

        mock_client_instance.incr.assert_called_with("repair.failed")
        mock_client_instance.timing.assert_called_with("repair.duration", 500.0)

    # Test get_validation_statistics method
    @patch("qdrant_loader.core.validation_repair.metrics.VALIDATION_ERROR_RATE")
    def test_get_validation_statistics_success(
        self, mock_error_rate, metrics_collector
    ):
        """Test successful retrieval of validation statistics."""
        # Setup some test data
        metrics_collector._stats.update(
            {
                "total_validations": 10,
                "successful_validations": 8,
                "failed_validations": 2,
                "total_repairs": 5,
                "successful_repairs": 4,
                "failed_repairs": 1,
                "total_issues_found": 15,
                "total_issues_resolved": 12,
            }
        )

        metrics_collector._active_validations_count = 2
        metrics_collector._validation_queue_size = 3
        metrics_collector._last_health_score = 92.5

        with patch.object(metrics_collector, "_count_recent_errors", return_value=1):
            stats = metrics_collector.get_validation_statistics()

        assert stats["total_validations"] == 10
        assert stats["successful_validations"] == 8
        assert stats["failed_validations"] == 2
        assert stats["active_validations"] == 2
        assert stats["validation_queue_size"] == 3
        assert stats["current_health_score"] == 92.5
        assert stats["error_rate_per_minute"] == 1.0 / 60.0
        assert stats["recent_errors"] == 1
        assert stats["validation_success_rate"] == 0.8
        assert stats["repair_success_rate"] == 0.8
        assert stats["issues_resolution_rate"] == 0.8

        mock_error_rate.set.assert_called_with(1.0 / 60.0)

    def test_get_validation_statistics_zero_division_handling(self, metrics_collector):
        """Test statistics calculation with zero totals."""
        # All stats are 0
        with patch.object(metrics_collector, "_count_recent_errors", return_value=0):
            stats = metrics_collector.get_validation_statistics()

        # Should not raise division by zero
        assert stats["validation_success_rate"] == 0.0
        assert stats["repair_success_rate"] == 0.0
        assert stats["issues_resolution_rate"] == 0.0

    # Test helper methods
    def test_update_average_validation_time_first_validation(self, metrics_collector):
        """Test average validation time calculation for first validation."""
        duration = 2.5
        metrics_collector._update_average_validation_time(duration)

        assert metrics_collector._stats["average_validation_time_seconds"] == 2.5

    def test_update_average_validation_time_multiple_validations(
        self, metrics_collector
    ):
        """Test average validation time calculation for multiple validations."""
        # First validation
        metrics_collector._update_average_validation_time(2.0)
        assert metrics_collector._stats["average_validation_time_seconds"] == 2.0

        # Second validation
        metrics_collector._update_average_validation_time(4.0)
        assert metrics_collector._stats["average_validation_time_seconds"] == 3.0

        # Third validation
        metrics_collector._update_average_validation_time(6.0)
        assert metrics_collector._stats["average_validation_time_seconds"] == 4.0

    def test_update_average_repair_time_first_repair(self, metrics_collector):
        """Test average repair time calculation for first repair."""
        duration = 1.5
        metrics_collector._update_average_repair_time(duration)

        assert metrics_collector._stats["average_repair_time_seconds"] == 1.5

    def test_update_average_repair_time_multiple_repairs(self, metrics_collector):
        """Test average repair time calculation for multiple repairs."""
        # First repair
        metrics_collector._update_average_repair_time(1.0)
        assert metrics_collector._stats["average_repair_time_seconds"] == 1.0

        # Second repair
        metrics_collector._update_average_repair_time(3.0)
        assert metrics_collector._stats["average_repair_time_seconds"] == 2.0

    @patch("qdrant_loader.core.validation_repair.metrics.REPAIR_SUCCESS_RATE")
    def test_update_repair_success_rates_success(
        self, mock_success_rate, metrics_collector, sample_repair_results
    ):
        """Test repair success rate calculation."""
        # Add repair history
        repair_record = {
            "repair_id": "repair-123",
            "status": "completed",
            "results": sample_repair_results,
        }
        metrics_collector._repair_history.append(repair_record)

        metrics_collector._update_repair_success_rates()

        # Check that success rates were set for each repair type
        mock_success_rate.labels.assert_any_call(
            repair_type=RepairAction.CREATE_MAPPING.value
        )
        mock_success_rate.labels.assert_any_call(
            repair_type=RepairAction.DELETE_ORPHANED.value
        )
        mock_success_rate.labels.assert_any_call(
            repair_type=RepairAction.SYNC_ENTITIES.value
        )

    def test_update_repair_success_rates_prometheus_disabled(
        self, metrics_collector_prometheus_disabled
    ):
        """Test repair success rate update with Prometheus disabled."""
        # Should not raise exception
        metrics_collector_prometheus_disabled._update_repair_success_rates()

    def test_count_recent_errors_within_timeframe(self, metrics_collector):
        """Test recent error counting within timeframe."""
        current_time = datetime.now(UTC)

        # Add validation errors within the last hour
        for i in range(3):
            error_time = current_time - timedelta(minutes=30)
            record = {
                "validation_id": f"validation-{i}",
                "status": "failed",
                "end_time": error_time,
            }
            metrics_collector._validation_history.append(record)

        # Add repair errors within the last hour
        for i in range(2):
            error_time = current_time - timedelta(minutes=45)
            record = {
                "repair_id": f"repair-{i}",
                "status": "failed",
                "end_time": error_time,
            }
            metrics_collector._repair_history.append(record)

        error_count = metrics_collector._count_recent_errors(hours=1)
        assert error_count == 5

    def test_count_recent_errors_outside_timeframe(self, metrics_collector):
        """Test recent error counting outside timeframe."""
        current_time = datetime.now(UTC)

        # Add errors outside the timeframe (2 hours ago)
        old_error_time = current_time - timedelta(hours=2)

        validation_record = {
            "validation_id": "old-validation",
            "status": "failed",
            "end_time": old_error_time,
        }
        metrics_collector._validation_history.append(validation_record)

        repair_record = {
            "repair_id": "old-repair",
            "status": "failed",
            "end_time": old_error_time,
        }
        metrics_collector._repair_history.append(repair_record)

        error_count = metrics_collector._count_recent_errors(hours=1)
        assert error_count == 0

    def test_count_recent_errors_mixed_timeframes(self, metrics_collector):
        """Test recent error counting with mixed timeframes."""
        current_time = datetime.now(UTC)

        # Recent error (30 minutes ago)
        recent_error = {
            "validation_id": "recent-validation",
            "status": "failed",
            "end_time": current_time - timedelta(minutes=30),
        }
        metrics_collector._validation_history.append(recent_error)

        # Old error (2 hours ago)
        old_error = {
            "validation_id": "old-validation",
            "status": "failed",
            "end_time": current_time - timedelta(hours=2),
        }
        metrics_collector._validation_history.append(old_error)

        # Successful validation (should not count)
        success_record = {
            "validation_id": "success-validation",
            "status": "completed",
            "end_time": current_time - timedelta(minutes=15),
        }
        metrics_collector._validation_history.append(success_record)

        error_count = metrics_collector._count_recent_errors(hours=1)
        assert error_count == 1

    def test_count_recent_errors_no_end_time(self, metrics_collector):
        """Test recent error counting with missing end_time."""
        # Add record without end_time (should not count)
        record = {
            "validation_id": "no-end-time",
            "status": "failed",
        }
        metrics_collector._validation_history.append(record)

        error_count = metrics_collector._count_recent_errors(hours=1)
        assert error_count == 0

    # Edge cases and error scenarios
    def test_record_validation_with_negative_active_count(self, metrics_collector):
        """Test handling of negative active validation count."""
        # Manually set negative count
        metrics_collector._active_validations_count = -1

        # Complete a validation (should not go below 0)
        metrics_collector.record_validation_completed("test", ValidationReport(), 1.0)

        assert metrics_collector._active_validations_count == 0

    def test_record_repair_with_no_results(self, metrics_collector):
        """Test repair completion recording with None results."""
        repair_id = "repair-123"
        metrics_collector.record_repair_started(repair_id, [])

        # This should not raise an exception
        with patch.object(metrics_collector, "_update_repair_success_rates"):
            metrics_collector.record_repair_completed(repair_id, [], 1.0)

        record = metrics_collector._repair_history[0]
        assert record["status"] == "completed"
        assert record["successful_repairs"] == 0
        assert record["failed_repairs"] == 0

    def test_metrics_with_very_large_numbers(self, metrics_collector):
        """Test metrics handling with very large numbers."""
        # Test with large duration
        large_duration = 999999.999
        validation_id = "large-validation"

        metrics_collector.record_validation_started(validation_id, ["test"])
        metrics_collector.record_validation_completed(
            validation_id, ValidationReport(), large_duration
        )

        record = metrics_collector._validation_history[0]
        assert record["duration_seconds"] == large_duration

    def test_concurrent_validation_tracking(self, metrics_collector):
        """Test tracking multiple concurrent validations."""
        # Start multiple validations
        for i in range(5):
            validation_id = f"validation-{i}"
            metrics_collector.record_validation_started(validation_id, ["test"])

        assert metrics_collector._active_validations_count == 5

        # Complete some validations
        for i in range(3):
            validation_id = f"validation-{i}"
            metrics_collector.record_validation_completed(
                validation_id, ValidationReport(), 1.0
            )

        assert metrics_collector._active_validations_count == 2

        # Fail remaining validations
        for i in range(3, 5):
            validation_id = f"validation-{i}"
            metrics_collector.record_validation_failed(validation_id, "Failed", 1.0)

        assert metrics_collector._active_validations_count == 0

    def test_memory_management_with_retention(self, metrics_collector):
        """Test that old records are properly managed based on retention policy."""
        # This is a basic test - in a real implementation, you might want to
        # test automatic cleanup of old records based on retention_hours

        # Add many records
        for i in range(1000):
            validation_id = f"validation-{i}"
            metrics_collector.record_validation_started(validation_id, ["test"])
            metrics_collector.record_validation_completed(
                validation_id, ValidationReport(), 1.0
            )

        # Verify records are stored
        assert len(metrics_collector._validation_history) == 1000

        # In a real implementation, you might test cleanup here
        # For now, just verify the data structure can handle large volumes
        stats = metrics_collector.get_validation_statistics()
        assert stats["total_validations"] == 1000
