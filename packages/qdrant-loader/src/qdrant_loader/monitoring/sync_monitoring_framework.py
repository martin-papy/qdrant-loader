"""
Comprehensive monitoring and alerting framework for the enhanced synchronization system.

This module provides real-time monitoring capabilities including:
- Health check endpoints and system status monitoring
- Real-time metrics collection and dashboards
- Alert systems for critical failures and performance degradation
- Comprehensive logging and audit trails
- Performance monitoring with threshold-based alerting
"""

import asyncio
import time
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Callable, Set, Union, Awaitable
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
import aiofiles
from collections import defaultdict, deque

from qdrant_loader.core.sync.enhanced_event_system import EnhancedSyncEventSystem
from qdrant_loader.core.atomic_transactions import AtomicTransactionManager
from qdrant_loader.core.sync.conflict_monitor import SyncConflictMonitor
from qdrant_loader.core.operation_differentiation import OperationDifferentiationManager
from qdrant_loader.core.sync.types import SyncOperationType


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealthStatus(Enum):
    """System health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics collected."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Alert:
    """Represents a system alert."""

    id: str
    severity: AlertSeverity
    title: str
    description: str
    component: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    component: str
    status: HealthStatus
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    response_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Metric:
    """Represents a system metric."""

    name: str
    type: MetricType
    value: Union[int, float]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class SystemStatus:
    """Overall system status."""

    overall_health: HealthStatus
    component_health: Dict[str, HealthCheckResult]
    active_alerts: List[Alert]
    metrics_summary: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MonitoringConfig:
    """Configuration for the monitoring system."""

    health_check_interval: int = 30  # seconds
    metrics_collection_interval: int = 10  # seconds
    alert_retention_days: int = 30
    metrics_retention_days: int = 7
    log_level: str = "INFO"
    enable_file_logging: bool = True
    log_file_path: str = "logs/sync_monitoring.log"
    enable_dashboard: bool = True
    dashboard_port: int = 8080
    alert_thresholds: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: {
            "operation_latency": {"warning": 1000.0, "critical": 5000.0},  # ms
            "error_rate": {"warning": 0.05, "critical": 0.10},  # percentage
            "memory_usage": {"warning": 80.0, "critical": 95.0},  # percentage
            "queue_size": {"warning": 1000, "critical": 5000},  # count
            "transaction_failure_rate": {
                "warning": 0.02,
                "critical": 0.05,
            },  # percentage
        }
    )


class SyncMonitoringFramework:
    """
    Comprehensive monitoring and alerting framework for the sync system.

    Provides real-time monitoring, health checks, alerting, and metrics collection
    for all sync system components.
    """

    def __init__(
        self,
        sync_system: EnhancedSyncEventSystem,
        atomic_transaction_manager: AtomicTransactionManager,
        sync_conflict_monitor: SyncConflictMonitor,
        operation_diff_manager: OperationDifferentiationManager,
        config: Optional[MonitoringConfig] = None,
    ):
        self.sync_system = sync_system
        self.atomic_transaction_manager = atomic_transaction_manager
        self.sync_conflict_monitor = sync_conflict_monitor
        self.operation_diff_manager = operation_diff_manager
        self.config = config or MonitoringConfig()

        # Internal state
        self.alerts: Dict[str, Alert] = {}
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.health_checks: Dict[str, HealthCheckResult] = {}
        self.alert_handlers: List[Callable[[Alert], None]] = []
        self.metric_collectors: Dict[str, Callable[[], Awaitable[Metric]]] = {}

        # Monitoring tasks
        self.monitoring_tasks: Set[asyncio.Task] = set()
        self.is_monitoring = False

        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)

        # Register default health checks
        self._register_default_health_checks()

        # Register default metric collectors
        self._register_default_metric_collectors()

    def _setup_logging(self):
        """Setup logging configuration."""
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, self.config.log_level))

        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler
        if self.config.enable_file_logging:
            log_path = Path(self.config.log_file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_path)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

    def _register_default_health_checks(self):
        """Register default health check functions."""
        self.health_check_functions = {
            "sync_system": self._check_sync_system_health,
            "atomic_transactions": self._check_atomic_transaction_health,
            "conflict_monitor": self._check_conflict_monitor_health,
            "operation_differentiation": self._check_operation_diff_health,
        }

    def _register_default_metric_collectors(self):
        """Register default metric collection functions."""
        self.metric_collectors = {
            "operation_queue_size": self._collect_queue_size_metric,
            "operation_latency": self._collect_operation_latency_metric,
            "error_rate": self._collect_error_rate_metric,
            "transaction_success_rate": self._collect_transaction_success_rate_metric,
            "conflict_detection_rate": self._collect_conflict_detection_rate_metric,
            "memory_usage": self._collect_memory_usage_metric,
        }

    async def start_monitoring(self):
        """Start the monitoring system."""
        if self.is_monitoring:
            self.logger.warning("Monitoring system is already running")
            return

        self.is_monitoring = True
        self.logger.info("Starting sync monitoring framework")

        # Start monitoring tasks
        health_check_task = asyncio.create_task(self._health_check_loop())
        metrics_collection_task = asyncio.create_task(self._metrics_collection_loop())
        alert_cleanup_task = asyncio.create_task(self._alert_cleanup_loop())

        self.monitoring_tasks.update(
            [health_check_task, metrics_collection_task, alert_cleanup_task]
        )

        self.logger.info("Sync monitoring framework started successfully")

    async def stop_monitoring(self):
        """Stop the monitoring system."""
        if not self.is_monitoring:
            return

        self.is_monitoring = False
        self.logger.info("Stopping sync monitoring framework")

        # Cancel all monitoring tasks
        for task in self.monitoring_tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        self.monitoring_tasks.clear()

        self.logger.info("Sync monitoring framework stopped")

    async def _health_check_loop(self):
        """Main health check monitoring loop."""
        while self.is_monitoring:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying

    async def _metrics_collection_loop(self):
        """Main metrics collection loop."""
        while self.is_monitoring:
            try:
                await self._collect_metrics()
                await asyncio.sleep(self.config.metrics_collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying

    async def _alert_cleanup_loop(self):
        """Clean up old alerts and metrics."""
        while self.is_monitoring:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(3600)  # Run cleanup every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in alert cleanup loop: {e}")
                await asyncio.sleep(300)  # Brief pause before retrying

    async def _perform_health_checks(self):
        """Perform all registered health checks."""
        for component, check_func in self.health_check_functions.items():
            try:
                start_time = time.time()
                result = await check_func()
                response_time = (time.time() - start_time) * 1000  # Convert to ms

                result.response_time_ms = response_time
                self.health_checks[component] = result

                # Check if we need to generate alerts
                await self._evaluate_health_alerts(result)

            except Exception as e:
                self.logger.error(f"Health check failed for {component}: {e}")
                error_result = HealthCheckResult(
                    component=component,
                    status=HealthStatus.CRITICAL,
                    message=f"Health check failed: {str(e)}",
                    response_time_ms=0.0,
                )
                self.health_checks[component] = error_result
                await self._create_alert(
                    f"health_check_{component}",
                    AlertSeverity.CRITICAL,
                    f"Health Check Failed: {component}",
                    f"Health check for {component} failed with error: {str(e)}",
                    component,
                )

    async def _collect_metrics(self):
        """Collect all registered metrics."""
        for metric_name, collector_func in self.metric_collectors.items():
            try:
                metric = await collector_func()
                self.metrics[metric_name].append(metric)

                # Check if we need to generate alerts based on thresholds
                await self._evaluate_metric_alerts(metric)

            except Exception as e:
                self.logger.error(f"Metric collection failed for {metric_name}: {e}")

    async def _cleanup_old_data(self):
        """Clean up old alerts and metrics."""
        current_time = datetime.now(timezone.utc)

        # Clean up old alerts
        alert_cutoff = current_time - timedelta(days=self.config.alert_retention_days)
        alerts_to_remove = [
            alert_id
            for alert_id, alert in self.alerts.items()
            if alert.timestamp < alert_cutoff and alert.resolved
        ]

        for alert_id in alerts_to_remove:
            del self.alerts[alert_id]

        if alerts_to_remove:
            self.logger.info(f"Cleaned up {len(alerts_to_remove)} old alerts")

        # Clean up old metrics (already handled by deque maxlen)
        self.logger.debug("Metrics cleanup completed (handled by deque maxlen)")

    async def _check_sync_system_health(self) -> HealthCheckResult:
        """Check the health of the sync system."""
        try:
            # Check if sync system is running and responsive
            stats = await self.sync_system.get_operation_statistics()

            # Determine health based on error rates and queue sizes
            total_ops = stats.get("total_operations", 0)
            failed_ops = stats.get("failed_operations", 0)
            queue_size = stats.get("queue_size", 0)

            error_rate = failed_ops / max(total_ops, 1)

            if error_rate > 0.1 or queue_size > 5000:
                status = HealthStatus.CRITICAL
                message = (
                    f"High error rate ({error_rate:.2%}) or large queue ({queue_size})"
                )
            elif error_rate > 0.05 or queue_size > 1000:
                status = HealthStatus.DEGRADED
                message = f"Elevated error rate ({error_rate:.2%}) or queue size ({queue_size})"
            else:
                status = HealthStatus.HEALTHY
                message = "Sync system operating normally"

            return HealthCheckResult(
                component="sync_system", status=status, message=message, metadata=stats
            )

        except Exception as e:
            return HealthCheckResult(
                component="sync_system",
                status=HealthStatus.CRITICAL,
                message=f"Failed to check sync system health: {str(e)}",
            )

    async def _check_atomic_transaction_health(self) -> HealthCheckResult:
        """Check the health of the atomic transaction manager."""
        try:
            # Get transaction statistics
            stats = await self.atomic_transaction_manager.health_check()

            active_transactions = stats.get("active_transactions", 0)
            failed_transactions = stats.get("failed_transactions", 0)
            total_transactions = stats.get("total_transactions", 0)

            failure_rate = failed_transactions / max(total_transactions, 1)

            if failure_rate > 0.05 or active_transactions > 100:
                status = HealthStatus.CRITICAL
                message = f"High transaction failure rate ({failure_rate:.2%}) or too many active transactions ({active_transactions})"
            elif failure_rate > 0.02 or active_transactions > 50:
                status = HealthStatus.DEGRADED
                message = f"Elevated transaction failure rate ({failure_rate:.2%}) or active transactions ({active_transactions})"
            else:
                status = HealthStatus.HEALTHY
                message = "Transaction manager operating normally"

            return HealthCheckResult(
                component="atomic_transactions",
                status=status,
                message=message,
                metadata=stats,
            )

        except Exception as e:
            return HealthCheckResult(
                component="atomic_transactions",
                status=HealthStatus.CRITICAL,
                message=f"Failed to check transaction manager health: {str(e)}",
            )

    async def _check_conflict_monitor_health(self) -> HealthCheckResult:
        """Check the health of the conflict monitor."""
        try:
            # Check conflict monitor status
            health_result = await self.sync_conflict_monitor.health_check()
            is_healthy = health_result.get("status") == "healthy"

            if is_healthy:
                status = HealthStatus.HEALTHY
                message = "Conflict monitor operating normally"
            else:
                status = HealthStatus.DEGRADED
                message = "Conflict monitor reporting issues"

            return HealthCheckResult(
                component="conflict_monitor", status=status, message=message
            )

        except Exception as e:
            return HealthCheckResult(
                component="conflict_monitor",
                status=HealthStatus.CRITICAL,
                message=f"Failed to check conflict monitor health: {str(e)}",
            )

    async def _check_operation_diff_health(self) -> HealthCheckResult:
        """Check the health of the operation differentiation manager."""
        try:
            # Check operation differentiation manager
            # This is a simple check since the manager is mostly stateless
            status = HealthStatus.HEALTHY
            message = "Operation differentiation manager operating normally"

            return HealthCheckResult(
                component="operation_differentiation", status=status, message=message
            )

        except Exception as e:
            return HealthCheckResult(
                component="operation_differentiation",
                status=HealthStatus.CRITICAL,
                message=f"Failed to check operation differentiation health: {str(e)}",
            )

    async def _collect_queue_size_metric(self) -> Metric:
        """Collect queue size metric."""
        try:
            stats = await self.sync_system.get_operation_statistics()
            queue_size = stats.get("queue_size", 0)

            return Metric(
                name="operation_queue_size",
                type=MetricType.GAUGE,
                value=queue_size,
                unit="count",
            )
        except Exception:
            return Metric(
                name="operation_queue_size",
                type=MetricType.GAUGE,
                value=0,
                unit="count",
            )

    async def _collect_operation_latency_metric(self) -> Metric:
        """Collect operation latency metric."""
        try:
            stats = await self.sync_system.get_operation_statistics()
            avg_latency = stats.get("average_operation_time", 0) * 1000  # Convert to ms

            return Metric(
                name="operation_latency",
                type=MetricType.HISTOGRAM,
                value=avg_latency,
                unit="ms",
            )
        except Exception:
            return Metric(
                name="operation_latency", type=MetricType.HISTOGRAM, value=0, unit="ms"
            )

    async def _collect_error_rate_metric(self) -> Metric:
        """Collect error rate metric."""
        try:
            stats = await self.sync_system.get_operation_statistics()
            total_ops = stats.get("total_operations", 0)
            failed_ops = stats.get("failed_operations", 0)
            error_rate = failed_ops / max(total_ops, 1)

            return Metric(
                name="error_rate",
                type=MetricType.GAUGE,
                value=error_rate,
                unit="percentage",
            )
        except Exception:
            return Metric(
                name="error_rate", type=MetricType.GAUGE, value=0, unit="percentage"
            )

    async def _collect_transaction_success_rate_metric(self) -> Metric:
        """Collect transaction success rate metric."""
        try:
            stats = await self.atomic_transaction_manager.health_check()
            total_transactions = stats.get("total_transactions", 0)
            successful_transactions = stats.get("successful_transactions", 0)
            success_rate = successful_transactions / max(total_transactions, 1)

            return Metric(
                name="transaction_success_rate",
                type=MetricType.GAUGE,
                value=success_rate,
                unit="percentage",
            )
        except Exception:
            return Metric(
                name="transaction_success_rate",
                type=MetricType.GAUGE,
                value=1.0,
                unit="percentage",
            )

    async def _collect_conflict_detection_rate_metric(self) -> Metric:
        """Collect conflict detection rate metric."""
        try:
            # This would need to be implemented based on conflict monitor capabilities
            # For now, return a placeholder
            return Metric(
                name="conflict_detection_rate",
                type=MetricType.GAUGE,
                value=0.0,
                unit="percentage",
            )
        except Exception:
            return Metric(
                name="conflict_detection_rate",
                type=MetricType.GAUGE,
                value=0.0,
                unit="percentage",
            )

    async def _collect_memory_usage_metric(self) -> Metric:
        """Collect memory usage metric."""
        try:
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024  # Convert to MB

            return Metric(
                name="memory_usage", type=MetricType.GAUGE, value=memory_mb, unit="MB"
            )
        except Exception:
            return Metric(
                name="memory_usage", type=MetricType.GAUGE, value=0, unit="MB"
            )

    async def _evaluate_health_alerts(self, health_result: HealthCheckResult):
        """Evaluate if health check results should trigger alerts."""
        alert_id = f"health_{health_result.component}"

        if health_result.status in [HealthStatus.CRITICAL, HealthStatus.UNHEALTHY]:
            severity = (
                AlertSeverity.CRITICAL
                if health_result.status == HealthStatus.CRITICAL
                else AlertSeverity.ERROR
            )
            await self._create_alert(
                alert_id,
                severity,
                f"Health Check Alert: {health_result.component}",
                health_result.message,
                health_result.component,
                health_result.metadata,
            )
        elif health_result.status == HealthStatus.DEGRADED:
            await self._create_alert(
                alert_id,
                AlertSeverity.WARNING,
                f"Health Degraded: {health_result.component}",
                health_result.message,
                health_result.component,
                health_result.metadata,
            )
        else:
            # Health is good, resolve any existing alerts
            await self._resolve_alert(alert_id)

    async def _evaluate_metric_alerts(self, metric: Metric):
        """Evaluate if metric values should trigger alerts."""
        thresholds = self.config.alert_thresholds.get(metric.name)
        if not thresholds:
            return

        alert_id = f"metric_{metric.name}"

        if metric.value >= thresholds.get("critical", float("inf")):
            await self._create_alert(
                alert_id,
                AlertSeverity.CRITICAL,
                f"Critical Metric Alert: {metric.name}",
                f"{metric.name} has reached critical level: {metric.value} {metric.unit}",
                "metrics",
                {"metric": asdict(metric), "threshold": thresholds["critical"]},
            )
        elif metric.value >= thresholds.get("warning", float("inf")):
            await self._create_alert(
                alert_id,
                AlertSeverity.WARNING,
                f"Warning Metric Alert: {metric.name}",
                f"{metric.name} has reached warning level: {metric.value} {metric.unit}",
                "metrics",
                {"metric": asdict(metric), "threshold": thresholds["warning"]},
            )
        else:
            # Metric is within normal range, resolve any existing alerts
            await self._resolve_alert(alert_id)

    async def _create_alert(
        self,
        alert_id: str,
        severity: AlertSeverity,
        title: str,
        description: str,
        component: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Create or update an alert."""
        existing_alert = self.alerts.get(alert_id)

        if existing_alert and not existing_alert.resolved:
            # Update existing alert
            existing_alert.description = description
            existing_alert.timestamp = datetime.now(timezone.utc)
            existing_alert.metadata.update(metadata or {})
        else:
            # Create new alert
            alert = Alert(
                id=alert_id,
                severity=severity,
                title=title,
                description=description,
                component=component,
                metadata=metadata or {},
            )
            self.alerts[alert_id] = alert

            # Log the alert
            log_level = {
                AlertSeverity.INFO: logging.INFO,
                AlertSeverity.WARNING: logging.WARNING,
                AlertSeverity.ERROR: logging.ERROR,
                AlertSeverity.CRITICAL: logging.CRITICAL,
            }[severity]

            self.logger.log(
                log_level, f"ALERT [{severity.value.upper()}] {title}: {description}"
            )

            # Notify alert handlers
            for handler in self.alert_handlers:
                try:
                    handler(alert)
                except Exception as e:
                    self.logger.error(f"Error in alert handler: {e}")

    async def _resolve_alert(self, alert_id: str):
        """Resolve an existing alert."""
        alert = self.alerts.get(alert_id)
        if alert and not alert.resolved:
            alert.resolved = True
            alert.resolved_at = datetime.now(timezone.utc)
            self.logger.info(f"RESOLVED: Alert {alert_id} - {alert.title}")

    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add an alert handler function."""
        self.alert_handlers.append(handler)

    def remove_alert_handler(self, handler: Callable[[Alert], None]):
        """Remove an alert handler function."""
        if handler in self.alert_handlers:
            self.alert_handlers.remove(handler)

    def get_system_status(self) -> SystemStatus:
        """Get the current system status."""
        # Determine overall health
        component_statuses = [result.status for result in self.health_checks.values()]

        if not component_statuses:
            overall_health = HealthStatus.HEALTHY
        elif HealthStatus.CRITICAL in component_statuses:
            overall_health = HealthStatus.CRITICAL
        elif HealthStatus.UNHEALTHY in component_statuses:
            overall_health = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in component_statuses:
            overall_health = HealthStatus.DEGRADED
        else:
            overall_health = HealthStatus.HEALTHY

        # Get active alerts
        active_alerts = [alert for alert in self.alerts.values() if not alert.resolved]

        # Create metrics summary
        metrics_summary = {}
        for metric_name, metric_deque in self.metrics.items():
            if metric_deque:
                latest_metric = metric_deque[-1]
                metrics_summary[metric_name] = {
                    "value": latest_metric.value,
                    "unit": latest_metric.unit,
                    "timestamp": latest_metric.timestamp.isoformat(),
                }

        return SystemStatus(
            overall_health=overall_health,
            component_health=self.health_checks.copy(),
            active_alerts=active_alerts,
            metrics_summary=metrics_summary,
        )

    async def export_metrics(self, format: str = "json") -> str:
        """Export metrics in the specified format."""
        if format.lower() == "json":
            metrics_data = {}
            for metric_name, metric_deque in self.metrics.items():
                metrics_data[metric_name] = [asdict(metric) for metric in metric_deque]
            return json.dumps(metrics_data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    async def export_alerts(self, format: str = "json") -> str:
        """Export alerts in the specified format."""
        if format.lower() == "json":
            alerts_data = [asdict(alert) for alert in self.alerts.values()]
            return json.dumps(alerts_data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Utility functions for monitoring setup
async def create_monitoring_framework(
    sync_system: EnhancedSyncEventSystem,
    atomic_transaction_manager: AtomicTransactionManager,
    sync_conflict_monitor: SyncConflictMonitor,
    operation_diff_manager: OperationDifferentiationManager,
    config: Optional[MonitoringConfig] = None,
) -> SyncMonitoringFramework:
    """Create and configure a monitoring framework instance."""
    framework = SyncMonitoringFramework(
        sync_system=sync_system,
        atomic_transaction_manager=atomic_transaction_manager,
        sync_conflict_monitor=sync_conflict_monitor,
        operation_diff_manager=operation_diff_manager,
        config=config,
    )

    return framework


def create_default_alert_handler() -> Callable[[Alert], None]:
    """Create a default alert handler that logs alerts."""

    def handler(alert: Alert):
        print(f"🚨 ALERT [{alert.severity.value.upper()}] {alert.title}")
        print(f"   Component: {alert.component}")
        print(f"   Description: {alert.description}")
        print(f"   Time: {alert.timestamp.isoformat()}")
        if alert.metadata:
            print(f"   Metadata: {json.dumps(alert.metadata, indent=2, default=str)}")
        print()

    return handler


async def run_monitoring_demo(
    sync_system: EnhancedSyncEventSystem,
    atomic_transaction_manager: AtomicTransactionManager,
    sync_conflict_monitor: SyncConflictMonitor,
    operation_diff_manager: OperationDifferentiationManager,
    duration_seconds: int = 60,
):
    """Run a monitoring demonstration."""
    print("🔍 Starting Sync Monitoring Framework Demo")

    # Create monitoring framework
    config = MonitoringConfig(
        health_check_interval=10, metrics_collection_interval=5, log_level="INFO"
    )

    framework = await create_monitoring_framework(
        sync_system=sync_system,
        atomic_transaction_manager=atomic_transaction_manager,
        sync_conflict_monitor=sync_conflict_monitor,
        operation_diff_manager=operation_diff_manager,
        config=config,
    )

    # Add default alert handler
    framework.add_alert_handler(create_default_alert_handler())

    try:
        # Start monitoring
        await framework.start_monitoring()

        print(f"📊 Monitoring active for {duration_seconds} seconds...")

        # Let it run for the specified duration
        await asyncio.sleep(duration_seconds)

        # Get final system status
        status = framework.get_system_status()
        print(f"\n📈 Final System Status:")
        print(f"   Overall Health: {status.overall_health.value}")
        print(f"   Active Alerts: {len(status.active_alerts)}")
        print(f"   Components Monitored: {len(status.component_health)}")

        # Export metrics
        metrics_json = await framework.export_metrics()
        print(f"\n📊 Metrics collected: {len(json.loads(metrics_json))} metric types")

    finally:
        # Stop monitoring
        await framework.stop_monitoring()
        print("🛑 Monitoring framework stopped")
