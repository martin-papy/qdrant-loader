"""Unit tests for sync monitoring framework.

This module tests the comprehensive monitoring and alerting capabilities including
health checks, metrics collection, alert management, and system status monitoring.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_loader.monitoring.sync_monitoring_framework import (
    Alert,
    AlertSeverity,
    HealthCheckResult,
    HealthStatus,
    Metric,
    MetricType,
    MonitoringConfig,
    SyncMonitoringFramework,
    create_default_alert_handler,
    create_monitoring_framework,
)


class TestMonitoringConfig:
    """Test suite for MonitoringConfig dataclass."""

    def test_monitoring_config_defaults(self):
        """Test MonitoringConfig with default values."""
        config = MonitoringConfig()

        assert config.health_check_interval == 30
        assert config.metrics_collection_interval == 10
        assert config.alert_retention_days == 30
        assert config.metrics_retention_days == 7
        assert config.log_level == "INFO"
        assert config.enable_file_logging is True
        assert config.log_file_path == "logs/sync_monitoring.log"
        assert config.enable_dashboard is True
        assert config.dashboard_port == 8080
        assert "operation_latency" in config.alert_thresholds
        assert "error_rate" in config.alert_thresholds

    def test_monitoring_config_custom_values(self):
        """Test MonitoringConfig with custom values."""
        custom_thresholds = {"custom_metric": {"warning": 10.0, "critical": 20.0}}

        config = MonitoringConfig(
            health_check_interval=60,
            metrics_collection_interval=30,
            alert_retention_days=60,
            log_level="DEBUG",
            enable_file_logging=False,
            alert_thresholds=custom_thresholds,
        )

        assert config.health_check_interval == 60
        assert config.metrics_collection_interval == 30
        assert config.alert_retention_days == 60
        assert config.log_level == "DEBUG"
        assert config.enable_file_logging is False
        assert config.alert_thresholds == custom_thresholds


class TestAlert:
    """Test suite for Alert dataclass."""

    def test_alert_creation(self):
        """Test Alert creation with required fields."""
        alert = Alert(
            id="test_alert_001",
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            description="Test alert description",
            component="test_component",
        )

        assert alert.id == "test_alert_001"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.title == "Test Alert"
        assert alert.description == "Test alert description"
        assert alert.component == "test_component"
        assert alert.resolved is False
        assert alert.resolved_at is None
        assert isinstance(alert.timestamp, datetime)
        assert isinstance(alert.metadata, dict)

    def test_alert_with_metadata(self):
        """Test Alert creation with metadata."""
        metadata = {"source": "test", "value": 42}
        alert = Alert(
            id="test_alert_002",
            severity=AlertSeverity.CRITICAL,
            title="Critical Alert",
            description="Critical alert description",
            component="critical_component",
            metadata=metadata,
        )

        assert alert.metadata == metadata


class TestHealthCheckResult:
    """Test suite for HealthCheckResult dataclass."""

    def test_health_check_result_creation(self):
        """Test HealthCheckResult creation."""
        result = HealthCheckResult(
            component="test_component",
            status=HealthStatus.HEALTHY,
            message="Component is healthy",
        )

        assert result.component == "test_component"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Component is healthy"
        assert isinstance(result.timestamp, datetime)
        assert result.response_time_ms == 0.0
        assert isinstance(result.metadata, dict)

    def test_health_check_result_with_metadata(self):
        """Test HealthCheckResult with metadata and response time."""
        metadata = {"cpu_usage": 45.2, "memory_usage": 67.8}
        result = HealthCheckResult(
            component="performance_component",
            status=HealthStatus.DEGRADED,
            message="Performance degraded",
            response_time_ms=150.5,
            metadata=metadata,
        )

        assert result.response_time_ms == 150.5
        assert result.metadata == metadata


class TestMetric:
    """Test suite for Metric dataclass."""

    def test_metric_creation(self):
        """Test Metric creation."""
        metric = Metric(
            name="test_metric", type=MetricType.GAUGE, value=42.5, unit="ms"
        )

        assert metric.name == "test_metric"
        assert metric.type == MetricType.GAUGE
        assert metric.value == 42.5
        assert metric.unit == "ms"
        assert isinstance(metric.timestamp, datetime)
        assert isinstance(metric.labels, dict)

    def test_metric_with_labels(self):
        """Test Metric creation with labels."""
        labels = {"component": "sync_system", "operation": "create"}
        metric = Metric(
            name="operation_latency",
            type=MetricType.HISTOGRAM,
            value=125.0,
            labels=labels,
            unit="ms",
        )

        assert metric.labels == labels


class TestSyncMonitoringFramework:
    """Test suite for SyncMonitoringFramework."""

    @pytest.fixture
    def mock_sync_system(self):
        """Create mock EnhancedSyncEventSystem."""
        mock = AsyncMock()
        mock.get_operation_statistics = AsyncMock(
            return_value={
                "total_operations": 100,
                "failed_operations": 5,
                "queue_size": 10,
                "average_operation_time": 0.5,
            }
        )
        return mock

    @pytest.fixture
    def mock_atomic_transaction_manager(self):
        """Create mock AtomicTransactionManager."""
        mock = AsyncMock()
        mock.health_check = AsyncMock(
            return_value={
                "status": "healthy",
                "active_transactions": 1,
                "total_transactions": 100,
                "successful_transactions": 98,
                "failed_transactions": 2,
            }
        )
        return mock

    @pytest.fixture
    def mock_sync_conflict_monitor(self):
        """Create mock SyncConflictMonitor."""
        mock = AsyncMock()
        mock.health_check = AsyncMock(
            return_value={"status": "healthy", "running": True}
        )
        return mock

    @pytest.fixture
    def mock_operation_diff_manager(self):
        """Create mock OperationDifferentiationManager."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def monitoring_framework(
        self,
        mock_sync_system,
        mock_atomic_transaction_manager,
        mock_sync_conflict_monitor,
        mock_operation_diff_manager,
    ):
        """Create SyncMonitoringFramework instance for testing."""
        config = MonitoringConfig(
            health_check_interval=1,  # Short intervals for testing
            metrics_collection_interval=1,
            log_level="DEBUG",
            enable_file_logging=False,
        )

        return SyncMonitoringFramework(
            sync_system=mock_sync_system,
            atomic_transaction_manager=mock_atomic_transaction_manager,
            sync_conflict_monitor=mock_sync_conflict_monitor,
            operation_diff_manager=mock_operation_diff_manager,
            config=config,
        )

    def test_initialization(self, monitoring_framework):
        """Test monitoring framework initialization."""
        framework = monitoring_framework

        assert framework.config.health_check_interval == 1
        assert framework.config.metrics_collection_interval == 1
        assert framework.is_monitoring is False
        assert len(framework.alerts) == 0
        assert len(framework.health_checks) == 0
        assert len(framework.monitoring_tasks) == 0
        assert len(framework.alert_handlers) == 0

    def test_health_check_functions_registration(self, monitoring_framework):
        """Test that health check functions are properly registered."""
        framework = monitoring_framework

        expected_components = [
            "sync_system",
            "atomic_transactions",
            "conflict_monitor",
            "operation_differentiation",
        ]

        for component in expected_components:
            assert component in framework.health_check_functions

    def test_metric_collectors_registration(self, monitoring_framework):
        """Test that metric collectors are properly registered."""
        framework = monitoring_framework

        expected_metrics = [
            "operation_queue_size",
            "operation_latency",
            "error_rate",
            "transaction_success_rate",
            "conflict_detection_rate",
            "memory_usage",
        ]

        for metric in expected_metrics:
            assert metric in framework.metric_collectors

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, monitoring_framework):
        """Test starting and stopping monitoring."""
        framework = monitoring_framework

        # Start monitoring
        await framework.start_monitoring()
        assert framework.is_monitoring is True
        assert len(framework.monitoring_tasks) == 3  # health, metrics, cleanup

        # Stop monitoring
        await framework.stop_monitoring()
        assert framework.is_monitoring is False
        assert len(framework.monitoring_tasks) == 0

    @pytest.mark.asyncio
    async def test_start_monitoring_already_running(self, monitoring_framework):
        """Test starting monitoring when already running."""
        framework = monitoring_framework

        await framework.start_monitoring()
        assert framework.is_monitoring is True

        # Try to start again - should not create duplicate tasks
        await framework.start_monitoring()
        assert framework.is_monitoring is True

    @pytest.mark.asyncio
    async def test_stop_monitoring_not_running(self, monitoring_framework):
        """Test stopping monitoring when not running."""
        framework = monitoring_framework

        # Should not raise error
        await framework.stop_monitoring()
        assert framework.is_monitoring is False

    @pytest.mark.asyncio
    async def test_sync_system_health_check(
        self, monitoring_framework, mock_sync_system
    ):
        """Test sync system health check."""
        framework = monitoring_framework

        result = await framework._check_sync_system_health()

        assert result.component == "sync_system"
        assert result.status == HealthStatus.HEALTHY
        assert "normally" in result.message
        assert result.response_time_ms == 0.0

    @pytest.mark.asyncio
    async def test_sync_system_health_check_degraded(
        self, monitoring_framework, mock_sync_system
    ):
        """Test sync system health check with degraded status."""
        framework = monitoring_framework

        # Mock elevated error rate
        mock_sync_system.get_operation_statistics.return_value = {
            "total_operations": 100,
            "failed_operations": 8,  # 8% error rate
            "queue_size": 1500,  # Large queue
        }

        result = await framework._check_sync_system_health()

        assert result.component == "sync_system"
        assert result.status == HealthStatus.DEGRADED
        assert "Elevated" in result.message

    @pytest.mark.asyncio
    async def test_sync_system_health_check_critical(
        self, monitoring_framework, mock_sync_system
    ):
        """Test sync system health check with critical status."""
        framework = monitoring_framework

        # Mock high error rate
        mock_sync_system.get_operation_statistics.return_value = {
            "total_operations": 100,
            "failed_operations": 15,  # 15% error rate
            "queue_size": 6000,  # Very large queue
        }

        result = await framework._check_sync_system_health()

        assert result.component == "sync_system"
        assert result.status == HealthStatus.CRITICAL
        assert "High error rate" in result.message

    @pytest.mark.asyncio
    async def test_atomic_transaction_health_check(
        self, monitoring_framework, mock_atomic_transaction_manager
    ):
        """Test atomic transaction manager health check."""
        framework = monitoring_framework

        result = await framework._check_atomic_transaction_health()

        assert result.component == "atomic_transactions"
        assert result.status == HealthStatus.HEALTHY
        assert "normally" in result.message

    @pytest.mark.asyncio
    async def test_conflict_monitor_health_check(
        self, monitoring_framework, mock_sync_conflict_monitor
    ):
        """Test conflict monitor health check."""
        framework = monitoring_framework

        result = await framework._check_conflict_monitor_health()

        assert result.component == "conflict_monitor"
        assert result.status == HealthStatus.HEALTHY
        assert "normally" in result.message

    @pytest.mark.asyncio
    async def test_operation_diff_health_check(self, monitoring_framework):
        """Test operation differentiation health check."""
        framework = monitoring_framework

        result = await framework._check_operation_diff_health()

        assert result.component == "operation_differentiation"
        assert result.status == HealthStatus.HEALTHY
        assert "normally" in result.message

    @pytest.mark.asyncio
    async def test_collect_queue_size_metric(
        self, monitoring_framework, mock_sync_system
    ):
        """Test queue size metric collection."""
        framework = monitoring_framework

        metric = await framework._collect_queue_size_metric()

        assert metric.name == "operation_queue_size"
        assert metric.type == MetricType.GAUGE
        assert metric.value == 10
        assert metric.unit == "count"

    @pytest.mark.asyncio
    async def test_collect_operation_latency_metric(
        self, monitoring_framework, mock_sync_system
    ):
        """Test operation latency metric collection."""
        framework = monitoring_framework

        metric = await framework._collect_operation_latency_metric()

        assert metric.name == "operation_latency"
        assert metric.type == MetricType.HISTOGRAM
        assert metric.value == 500.0  # 0.5 seconds * 1000 = 500ms
        assert metric.unit == "ms"

    @pytest.mark.asyncio
    async def test_collect_error_rate_metric(
        self, monitoring_framework, mock_sync_system
    ):
        """Test error rate metric collection."""
        framework = monitoring_framework

        metric = await framework._collect_error_rate_metric()

        assert metric.name == "error_rate"
        assert metric.type == MetricType.GAUGE
        assert metric.value == 0.05  # 5/100 = 0.05
        assert metric.unit == "percentage"

    @pytest.mark.asyncio
    async def test_collect_transaction_success_rate_metric(
        self, monitoring_framework, mock_atomic_transaction_manager
    ):
        """Test transaction success rate metric collection."""
        framework = monitoring_framework

        metric = await framework._collect_transaction_success_rate_metric()

        assert metric.name == "transaction_success_rate"
        assert metric.type == MetricType.GAUGE
        assert metric.value == 0.98  # 98/100 = 0.98
        assert metric.unit == "percentage"

    @pytest.mark.asyncio
    @patch("psutil.Process")
    async def test_collect_memory_usage_metric(
        self, mock_process, monitoring_framework
    ):
        """Test memory usage metric collection."""
        framework = monitoring_framework

        # Mock psutil
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 1024 * 1024 * 100  # 100 MB in bytes
        mock_process.return_value.memory_info.return_value = mock_memory_info

        metric = await framework._collect_memory_usage_metric()

        assert metric.name == "memory_usage"
        assert metric.type == MetricType.GAUGE
        assert metric.value == 100.0  # 100 MB
        assert metric.unit == "MB"

    @pytest.mark.asyncio
    async def test_create_alert(self, monitoring_framework):
        """Test alert creation."""
        framework = monitoring_framework

        await framework._create_alert(
            "test_alert",
            AlertSeverity.WARNING,
            "Test Alert",
            "Test alert description",
            "test_component",
            {"key": "value"},
        )

        assert "test_alert" in framework.alerts
        alert = framework.alerts["test_alert"]
        assert alert.severity == AlertSeverity.WARNING
        assert alert.title == "Test Alert"
        assert alert.description == "Test alert description"
        assert alert.component == "test_component"
        assert alert.metadata == {"key": "value"}
        assert alert.resolved is False

    @pytest.mark.asyncio
    async def test_resolve_alert(self, monitoring_framework):
        """Test alert resolution."""
        framework = monitoring_framework

        # Create an alert first
        await framework._create_alert(
            "test_alert",
            AlertSeverity.WARNING,
            "Test Alert",
            "Test alert description",
            "test_component",
        )

        # Resolve the alert
        await framework._resolve_alert("test_alert")

        alert = framework.alerts["test_alert"]
        assert alert.resolved is True
        assert alert.resolved_at is not None

    def test_add_remove_alert_handler(self, monitoring_framework):
        """Test adding and removing alert handlers."""
        framework = monitoring_framework

        def test_handler(alert):
            pass

        # Add handler
        framework.add_alert_handler(test_handler)
        assert test_handler in framework.alert_handlers

        # Remove handler
        framework.remove_alert_handler(test_handler)
        assert test_handler not in framework.alert_handlers

    def test_get_system_status(self, monitoring_framework):
        """Test getting system status."""
        framework = monitoring_framework

        # Add some test data
        framework.health_checks["test_component"] = HealthCheckResult(
            component="test_component",
            status=HealthStatus.HEALTHY,
            message="Test component healthy",
        )

        framework.alerts["test_alert"] = Alert(
            id="test_alert",
            severity=AlertSeverity.INFO,
            title="Test Alert",
            description="Test description",
            component="test_component",
        )

        # Add metrics
        metric = Metric(
            name="test_metric", type=MetricType.GAUGE, value=42.0, unit="count"
        )
        framework.metrics["test_metric"].append(metric)

        status = framework.get_system_status()

        assert status.overall_health == HealthStatus.HEALTHY
        assert len(status.component_health) == 1
        assert len(status.active_alerts) == 1
        assert "test_metric" in status.metrics_summary

    @pytest.mark.asyncio
    async def test_export_metrics(self, monitoring_framework):
        """Test metrics export."""
        framework = monitoring_framework

        # Add test metric
        metric = Metric(
            name="test_metric", type=MetricType.GAUGE, value=42.0, unit="count"
        )
        framework.metrics["test_metric"].append(metric)

        exported = await framework.export_metrics("json")

        assert "test_metric" in exported
        assert "42.0" in exported

    @pytest.mark.asyncio
    async def test_export_alerts(self, monitoring_framework):
        """Test alerts export."""
        framework = monitoring_framework

        # Add test alert
        framework.alerts["test_alert"] = Alert(
            id="test_alert",
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            description="Test description",
            component="test_component",
        )

        exported = await framework.export_alerts("json")

        assert "test_alert" in exported
        assert "Test Alert" in exported


class TestUtilityFunctions:
    """Test suite for utility functions."""

    @pytest.mark.asyncio
    async def test_create_monitoring_framework(self):
        """Test monitoring framework creation utility."""
        mock_sync_system = AsyncMock()
        mock_atomic_manager = AsyncMock()
        mock_conflict_monitor = AsyncMock()
        mock_operation_diff = AsyncMock()

        framework = await create_monitoring_framework(
            sync_system=mock_sync_system,
            atomic_transaction_manager=mock_atomic_manager,
            sync_conflict_monitor=mock_conflict_monitor,
            operation_diff_manager=mock_operation_diff,
        )

        assert isinstance(framework, SyncMonitoringFramework)
        assert framework.sync_system == mock_sync_system
        assert framework.atomic_transaction_manager == mock_atomic_manager

    def test_create_default_alert_handler(self):
        """Test default alert handler creation."""
        handler = create_default_alert_handler()

        assert callable(handler)

        # Test handler execution
        test_alert = Alert(
            id="test_alert",
            severity=AlertSeverity.CRITICAL,
            title="Test Alert",
            description="Test description",
            component="test_component",
        )

        # Should not raise exception
        handler(test_alert)
