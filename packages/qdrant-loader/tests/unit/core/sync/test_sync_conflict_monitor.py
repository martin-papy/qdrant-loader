"""
Unit tests for SyncConflictMonitor.

Tests comprehensive sync monitoring with conflict resolution, content hash synchronization,
operation metrics tracking, health monitoring, and background task management.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC, timedelta
from typing import Dict, Any, List

from qdrant_loader.core.sync import (
    SyncConflictMonitor,
    SyncMonitoringLevel,
    ContentHashStatus,
    ContentHashComparison,
    SyncOperationMetrics,
    EnhancedSyncOperation,
    SyncOperationType,
    SyncOperationStatus,
    ChangeEvent,
    ChangeType,
    DatabaseType,
)
from qdrant_loader.core.conflict_resolution import (
    ConflictResolutionSystem,
    ConflictRecord,
    ConflictType,
    ConflictStatus,
)
from qdrant_loader.core.managers import IDMapping, MappingType
from qdrant_loader.core.types import EntityType
from qdrant_loader.core.monitoring.ingestion_metrics import IngestionMonitor


@pytest.fixture
def mock_enhanced_sync_system():
    """Create mock enhanced sync system."""
    mock = AsyncMock()
    mock.queue_operation = AsyncMock()
    return mock


@pytest.fixture
def mock_conflict_resolution_system():
    """Create mock conflict resolution system."""
    mock = AsyncMock()
    mock.detect_conflict = AsyncMock(return_value=None)
    mock.resolve_conflict = AsyncMock(return_value=True)
    mock.get_conflict_statistics = AsyncMock(
        return_value={
            "total_conflicts": 0,
            "resolved_conflicts": 0,
            "pending_conflicts": 0,
        }
    )
    mock.health_check = AsyncMock(return_value={"status": "healthy"})
    return mock


@pytest.fixture
def mock_qdrant_manager():
    """Create mock QDrant manager."""
    mock = AsyncMock()
    mock.collection_name = "test_collection"
    mock._ensure_client_connected = MagicMock()

    # Mock client with retrieve method
    mock_client = MagicMock()
    mock_client.retrieve = MagicMock(
        return_value=[
            MagicMock(payload={"content": "test content", "metadata": {"key": "value"}})
        ]
    )
    mock._ensure_client_connected.return_value = mock_client

    return mock


@pytest.fixture
def mock_neo4j_manager():
    """Create mock Neo4j manager."""
    mock = AsyncMock()
    mock.execute_query = MagicMock(
        return_value=[
            {"props": {"content": "test content", "metadata": {"key": "value"}}}
        ]
    )
    return mock


@pytest.fixture
def mock_id_mapping_manager():
    """Create mock ID mapping manager."""
    mock = AsyncMock()

    # Create sample mapping
    sample_mapping = IDMapping(
        mapping_id="mapping_001",
        qdrant_point_id="point_001",
        neo4j_node_id="123",
        entity_type=EntityType.CONCEPT,
        mapping_type=MappingType.DOCUMENT,
        last_update_time=datetime.now(UTC),
        update_source="qdrant",
    )

    mock.get_mapping_by_qdrant_id = AsyncMock(return_value=sample_mapping)
    mock.get_mapping_by_neo4j_id = AsyncMock(return_value=sample_mapping)
    mock.get_mappings_by_entity_type = AsyncMock(return_value=[sample_mapping])

    return mock


@pytest.fixture
def mock_ingestion_monitor():
    """Create mock ingestion monitor."""
    mock = MagicMock()
    mock.start_operation = MagicMock()
    mock.end_operation = MagicMock()
    return mock


@pytest.fixture
def sync_conflict_monitor(
    mock_enhanced_sync_system,
    mock_conflict_resolution_system,
    mock_qdrant_manager,
    mock_neo4j_manager,
    mock_id_mapping_manager,
    mock_ingestion_monitor,
):
    """Create SyncConflictMonitor instance with mocks."""
    return SyncConflictMonitor(
        enhanced_sync_system=mock_enhanced_sync_system,
        conflict_resolution_system=mock_conflict_resolution_system,
        qdrant_manager=mock_qdrant_manager,
        neo4j_manager=mock_neo4j_manager,
        id_mapping_manager=mock_id_mapping_manager,
        ingestion_monitor=mock_ingestion_monitor,
        monitoring_level=SyncMonitoringLevel.STANDARD,
        enable_content_hash_sync=True,
        enable_automatic_conflict_resolution=True,
        content_hash_check_interval_hours=1,  # Short interval for testing
        max_concurrent_hash_checks=5,
    )


@pytest.fixture
def sample_sync_operation():
    """Create sample sync operation."""
    return EnhancedSyncOperation(
        operation_type=SyncOperationType.CREATE_DOCUMENT,
        entity_id="doc_001",
        operation_data={"content": "test content"},
        metadata={"source": "test"},
    )


class TestSyncConflictMonitor:
    """Test suite for SyncConflictMonitor."""

    def test_initialization_basic(self, sync_conflict_monitor):
        """Test basic initialization of sync conflict monitor."""
        monitor = sync_conflict_monitor

        assert monitor.monitoring_level == SyncMonitoringLevel.STANDARD
        assert monitor.enable_content_hash_sync is True
        assert monitor.enable_automatic_conflict_resolution is True
        assert monitor.content_hash_check_interval_hours == 1
        assert monitor.max_concurrent_hash_checks == 5
        assert not monitor._running
        assert len(monitor._operation_metrics) == 0
        assert len(monitor._content_hash_cache) == 0
        assert len(monitor._conflict_history) == 0
        assert len(monitor._monitoring_tasks) == 0

    def test_initialization_with_custom_settings(
        self,
        mock_enhanced_sync_system,
        mock_conflict_resolution_system,
        mock_qdrant_manager,
        mock_neo4j_manager,
        mock_id_mapping_manager,
    ):
        """Test initialization with custom settings."""
        monitor = SyncConflictMonitor(
            enhanced_sync_system=mock_enhanced_sync_system,
            conflict_resolution_system=mock_conflict_resolution_system,
            qdrant_manager=mock_qdrant_manager,
            neo4j_manager=mock_neo4j_manager,
            id_mapping_manager=mock_id_mapping_manager,
            monitoring_level=SyncMonitoringLevel.DEBUG,
            enable_content_hash_sync=False,
            enable_automatic_conflict_resolution=False,
            content_hash_check_interval_hours=48,
            conflict_resolution_timeout_seconds=600,
            max_concurrent_hash_checks=20,
        )

        assert monitor.monitoring_level == SyncMonitoringLevel.DEBUG
        assert monitor.enable_content_hash_sync is False
        assert monitor.enable_automatic_conflict_resolution is False
        assert monitor.content_hash_check_interval_hours == 48
        assert monitor.conflict_resolution_timeout_seconds == 600
        assert monitor.max_concurrent_hash_checks == 20

    @pytest.mark.asyncio
    async def test_start_stop_monitoring_basic(self, sync_conflict_monitor):
        """Test basic start and stop monitoring functionality."""
        monitor = sync_conflict_monitor

        # Start monitoring
        await monitor.start_monitoring()
        assert monitor._running is True
        assert len(monitor._monitoring_tasks) == 1  # Periodic hash check task

        # Stop monitoring
        await monitor.stop_monitoring()
        assert monitor._running is False
        assert len(monitor._monitoring_tasks) == 0

    @pytest.mark.asyncio
    async def test_start_monitoring_already_running(self, sync_conflict_monitor):
        """Test starting monitoring when already running."""
        monitor = sync_conflict_monitor

        await monitor.start_monitoring()
        assert monitor._running is True

        # Try to start again
        await monitor.start_monitoring()
        assert monitor._running is True  # Should still be running

    @pytest.mark.asyncio
    async def test_stop_monitoring_not_running(self, sync_conflict_monitor):
        """Test stopping monitoring when not running."""
        monitor = sync_conflict_monitor

        # Should not raise error
        await monitor.stop_monitoring()
        assert monitor._running is False

    @pytest.mark.asyncio
    async def test_monitor_sync_operation_basic(
        self, sync_conflict_monitor, sample_sync_operation
    ):
        """Test basic sync operation monitoring."""
        monitor = sync_conflict_monitor
        operation = sample_sync_operation
        operation.status = SyncOperationStatus.COMPLETED

        metrics = await monitor.monitor_sync_operation(operation)

        assert metrics.operation_id == operation.operation_id
        assert metrics.operation_type == operation.operation_type
        assert metrics.status == SyncOperationStatus.COMPLETED
        assert metrics.duration_seconds is not None
        assert operation.operation_id in monitor._operation_metrics
        assert monitor._stats["operations_monitored"] == 1

    @pytest.mark.asyncio
    async def test_monitor_sync_operation_with_content_hash(
        self, sync_conflict_monitor, sample_sync_operation
    ):
        """Test sync operation monitoring with content hash comparison."""
        monitor = sync_conflict_monitor
        operation = sample_sync_operation
        operation.status = SyncOperationStatus.COMPLETED

        metrics = await monitor.monitor_sync_operation(operation)

        assert metrics.content_hash_comparison is not None
        assert metrics.content_hash_comparison.entity_id == operation.entity_id
        assert metrics.content_hash_comparison.status in [
            ContentHashStatus.MATCH,
            ContentHashStatus.MISMATCH,
            ContentHashStatus.MISSING_SOURCE,
            ContentHashStatus.MISSING_TARGET,
        ]

    @pytest.mark.asyncio
    async def test_monitor_sync_operation_with_conflict_detection(
        self,
        sync_conflict_monitor,
        sample_sync_operation,
        mock_conflict_resolution_system,
    ):
        """Test sync operation monitoring with conflict detection."""
        monitor = sync_conflict_monitor
        operation = sample_sync_operation
        operation.status = SyncOperationStatus.COMPLETED

        # Mock conflict detection
        mock_conflict = ConflictRecord(
            conflict_id="conflict_001",
            conflict_type=ConflictType.DATA_MISMATCH,
            status=ConflictStatus.DETECTED,
        )
        mock_conflict_resolution_system.detect_conflict.return_value = mock_conflict

        metrics = await monitor.monitor_sync_operation(operation)

        assert metrics.conflicts_detected == 1
        assert metrics.conflicts_resolved == 1  # Should be resolved automatically
        assert monitor._stats["conflicts_detected"] == 1
        assert monitor._stats["conflicts_resolved"] == 1

    @pytest.mark.asyncio
    async def test_monitor_sync_operation_conflict_resolution_failure(
        self,
        sync_conflict_monitor,
        sample_sync_operation,
        mock_conflict_resolution_system,
    ):
        """Test sync operation monitoring with conflict resolution failure."""
        monitor = sync_conflict_monitor
        operation = sample_sync_operation
        operation.status = SyncOperationStatus.COMPLETED

        # Mock conflict detection and failed resolution
        mock_conflict = ConflictRecord(
            conflict_id="conflict_001",
            conflict_type=ConflictType.DATA_MISMATCH,
            status=ConflictStatus.DETECTED,
        )
        mock_conflict.requires_manual_review = MagicMock(return_value=True)
        mock_conflict_resolution_system.detect_conflict.return_value = mock_conflict
        mock_conflict_resolution_system.resolve_conflict.return_value = False

        metrics = await monitor.monitor_sync_operation(operation)

        assert metrics.conflicts_detected == 1
        assert metrics.conflicts_failed == 1
        assert metrics.manual_interventions_required == 1
        assert monitor._stats["manual_interventions_required"] == 1

    @pytest.mark.asyncio
    async def test_monitor_sync_operation_exception_handling(
        self, sync_conflict_monitor, sample_sync_operation, mock_id_mapping_manager
    ):
        """Test sync operation monitoring with exception handling."""
        monitor = sync_conflict_monitor
        operation = sample_sync_operation

        # Mock exception in ID mapping
        mock_id_mapping_manager.get_mapping_by_qdrant_id.side_effect = Exception(
            "Database error"
        )

        metrics = await monitor.monitor_sync_operation(operation)

        assert metrics.status == SyncOperationStatus.FAILED
        assert len(metrics.errors) > 0
        assert "Error monitoring sync operation" in metrics.errors[0]
        assert monitor._stats["monitoring_errors"] == 1

    @pytest.mark.asyncio
    async def test_content_hash_comparison_match(
        self, sync_conflict_monitor, mock_qdrant_manager, mock_neo4j_manager
    ):
        """Test content hash comparison with matching hashes."""
        monitor = sync_conflict_monitor

        # Mock identical content in both databases
        mock_qdrant_manager._ensure_client_connected.return_value.retrieve.return_value = [
            MagicMock(payload={"content": "identical content"})
        ]
        mock_neo4j_manager.execute_query.return_value = [
            {"props": {"content": "identical content"}}
        ]

        comparison = await monitor._perform_content_hash_comparison("doc_001")

        assert comparison.status == ContentHashStatus.MATCH
        assert comparison.qdrant_hash == comparison.neo4j_hash
        assert not comparison.requires_sync

    @pytest.mark.asyncio
    async def test_content_hash_comparison_mismatch(
        self, sync_conflict_monitor, mock_qdrant_manager, mock_neo4j_manager
    ):
        """Test content hash comparison with mismatched hashes."""
        monitor = sync_conflict_monitor

        # Mock different content in databases
        mock_qdrant_manager._ensure_client_connected.return_value.retrieve.return_value = [
            MagicMock(payload={"content": "qdrant content"})
        ]
        mock_neo4j_manager.execute_query.return_value = [
            {"props": {"content": "neo4j content"}}
        ]

        comparison = await monitor._perform_content_hash_comparison("doc_001")

        assert comparison.status == ContentHashStatus.MISMATCH
        assert comparison.qdrant_hash != comparison.neo4j_hash
        assert comparison.requires_sync
        assert comparison.sync_direction is not None

    @pytest.mark.asyncio
    async def test_content_hash_comparison_missing_target(
        self, sync_conflict_monitor, mock_qdrant_manager, mock_neo4j_manager
    ):
        """Test content hash comparison with missing target data."""
        monitor = sync_conflict_monitor

        # Mock QDrant has data, Neo4j doesn't
        mock_qdrant_manager._ensure_client_connected.return_value.retrieve.return_value = [
            MagicMock(payload={"content": "qdrant content"})
        ]
        mock_neo4j_manager.execute_query.return_value = []

        comparison = await monitor._perform_content_hash_comparison("doc_001")

        assert comparison.status == ContentHashStatus.MISSING_TARGET
        assert comparison.qdrant_hash is not None
        assert comparison.neo4j_hash is None
        assert comparison.requires_sync
        assert comparison.sync_direction == DatabaseType.NEO4J

    @pytest.mark.asyncio
    async def test_content_hash_comparison_missing_source(
        self, sync_conflict_monitor, mock_qdrant_manager, mock_neo4j_manager
    ):
        """Test content hash comparison with missing source data."""
        monitor = sync_conflict_monitor

        # Mock Neo4j has data, QDrant doesn't
        mock_qdrant_manager._ensure_client_connected.return_value.retrieve.return_value = (
            []
        )
        mock_neo4j_manager.execute_query.return_value = [
            {"props": {"content": "neo4j content"}}
        ]

        comparison = await monitor._perform_content_hash_comparison("doc_001")

        assert comparison.status == ContentHashStatus.MISSING_SOURCE
        assert comparison.qdrant_hash is None
        assert comparison.neo4j_hash is not None
        assert comparison.requires_sync
        assert comparison.sync_direction == DatabaseType.QDRANT

    @pytest.mark.asyncio
    async def test_content_hash_comparison_both_missing(
        self, sync_conflict_monitor, mock_qdrant_manager, mock_neo4j_manager
    ):
        """Test content hash comparison with both databases missing data."""
        monitor = sync_conflict_monitor

        # Mock both databases have no data
        mock_qdrant_manager._ensure_client_connected.return_value.retrieve.return_value = (
            []
        )
        mock_neo4j_manager.execute_query.return_value = []

        comparison = await monitor._perform_content_hash_comparison("doc_001")

        assert comparison.status == ContentHashStatus.BOTH_MISSING
        assert comparison.qdrant_hash is None
        assert comparison.neo4j_hash is None
        assert not comparison.requires_sync

    @pytest.mark.asyncio
    async def test_content_hash_comparison_no_mapping(
        self, sync_conflict_monitor, mock_id_mapping_manager
    ):
        """Test content hash comparison with no mapping found."""
        monitor = sync_conflict_monitor

        # Mock no mapping found
        mock_id_mapping_manager.get_mapping_by_qdrant_id.return_value = None
        mock_id_mapping_manager.get_mapping_by_neo4j_id.return_value = None

        comparison = await monitor._perform_content_hash_comparison("doc_001")

        assert comparison.status == ContentHashStatus.MISSING_SOURCE
        assert comparison.error_message == "No mapping found for entity"

    @pytest.mark.asyncio
    async def test_content_hash_comparison_error_handling(
        self, sync_conflict_monitor, mock_qdrant_manager
    ):
        """Test content hash comparison with error handling."""
        monitor = sync_conflict_monitor

        # Mock exception in QDrant retrieval
        mock_qdrant_manager._ensure_client_connected.side_effect = Exception(
            "Connection error"
        )

        comparison = await monitor._perform_content_hash_comparison("doc_001")

        # Connection errors are treated as missing source data, not hash errors
        assert comparison.status == ContentHashStatus.MISSING_SOURCE
        assert comparison.qdrant_hash is None

    @pytest.mark.asyncio
    async def test_handle_content_hash_mismatch(
        self, sync_conflict_monitor, sample_sync_operation, mock_enhanced_sync_system
    ):
        """Test handling of content hash mismatch."""
        monitor = sync_conflict_monitor
        operation = sample_sync_operation

        comparison = ContentHashComparison(
            mapping_id="mapping_001",
            entity_id="doc_001",
            status=ContentHashStatus.MISMATCH,
            requires_sync=True,
            sync_direction=DatabaseType.NEO4J,
        )

        await monitor._handle_content_hash_mismatch(operation, comparison)

        # Should queue a sync operation
        mock_enhanced_sync_system.queue_operation.assert_called_once()
        queued_op = mock_enhanced_sync_system.queue_operation.call_args[0][0]
        assert queued_op.operation_type == SyncOperationType.UPDATE_DOCUMENT
        assert queued_op.entity_id == "doc_001"
        assert DatabaseType.NEO4J in queued_op.target_databases
        assert monitor._stats["hash_syncs_performed"] == 1

    @pytest.mark.asyncio
    async def test_get_monitoring_statistics(
        self, sync_conflict_monitor, sample_sync_operation
    ):
        """Test getting monitoring statistics."""
        monitor = sync_conflict_monitor

        # Add some test data
        await monitor.monitor_sync_operation(sample_sync_operation)
        monitor._stats["conflicts_detected"] = 5
        monitor._stats["conflicts_resolved"] = 3

        stats = await monitor.get_monitoring_statistics()

        assert stats["monitoring_status"] == "stopped"
        assert stats["monitoring_level"] == "standard"
        assert stats["total_operations_monitored"] == 1
        assert stats["conflicts_detected"] == 5
        assert stats["conflicts_resolved"] == 3
        assert "conflict_resolution_stats" in stats
        assert "cache_sizes" in stats

    @pytest.mark.asyncio
    async def test_get_recent_operations(
        self, sync_conflict_monitor, sample_sync_operation
    ):
        """Test getting recent operations."""
        monitor = sync_conflict_monitor

        # Add test operation
        await monitor.monitor_sync_operation(sample_sync_operation)

        recent_ops = await monitor.get_recent_operations(hours=24, limit=10)

        assert len(recent_ops) == 1
        assert recent_ops[0]["operation_id"] == sample_sync_operation.operation_id
        assert (
            recent_ops[0]["operation_type"]
            == sample_sync_operation.operation_type.value
        )

    @pytest.mark.asyncio
    async def test_get_content_hash_mismatches(self, sync_conflict_monitor):
        """Test getting content hash mismatches."""
        monitor = sync_conflict_monitor

        # Add test mismatch to cache
        mismatch = ContentHashComparison(
            mapping_id="mapping_001",
            entity_id="doc_001",
            status=ContentHashStatus.MISMATCH,
            qdrant_hash="hash1",
            neo4j_hash="hash2",
        )
        monitor._content_hash_cache["mapping_001"] = mismatch

        mismatches = await monitor.get_content_hash_mismatches(limit=10)

        assert len(mismatches) == 1
        assert mismatches[0]["status"] == "mismatch"
        assert mismatches[0]["entity_id"] == "doc_001"

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, sync_conflict_monitor):
        """Test health check when system is healthy."""
        monitor = sync_conflict_monitor
        await monitor.start_monitoring()

        health = await monitor.health_check()

        assert health["status"] == "healthy"
        assert health["running"] is True
        assert health["monitoring_level"] == "standard"
        assert len(health["issues"]) == 0

    @pytest.mark.asyncio
    async def test_health_check_no_background_tasks(self, sync_conflict_monitor):
        """Test health check when running but no background tasks."""
        monitor = sync_conflict_monitor
        monitor._running = True  # Set running without starting tasks

        health = await monitor.health_check()

        assert health["status"] == "degraded"
        assert "No background monitoring tasks running" in health["issues"]

    @pytest.mark.asyncio
    async def test_health_check_high_error_rate(
        self, sync_conflict_monitor, sample_sync_operation
    ):
        """Test health check with high error rate."""
        monitor = sync_conflict_monitor

        # Add operations with errors
        for i in range(10):
            op = EnhancedSyncOperation(
                operation_type=SyncOperationType.CREATE_DOCUMENT,
                entity_id=f"doc_{i}",
                operation_data={"content": f"content {i}"},
            )
            metrics = await monitor.monitor_sync_operation(op)
            if i < 5:  # 50% error rate
                metrics.add_error("Test error")

        health = await monitor.health_check()

        assert "High error rate" in str(health["issues"])

    @pytest.mark.asyncio
    async def test_health_check_conflict_system_unhealthy(
        self, sync_conflict_monitor, mock_conflict_resolution_system
    ):
        """Test health check when conflict resolution system is unhealthy."""
        monitor = sync_conflict_monitor

        mock_conflict_resolution_system.health_check.return_value = {
            "status": "unhealthy"
        }

        health = await monitor.health_check()

        assert "Conflict resolution system unhealthy" in health["issues"]

    @pytest.mark.asyncio
    async def test_health_check_exception_handling(
        self, sync_conflict_monitor, mock_conflict_resolution_system
    ):
        """Test health check with exception handling."""
        monitor = sync_conflict_monitor

        mock_conflict_resolution_system.health_check.side_effect = Exception(
            "Health check error"
        )

        health = await monitor.health_check()

        assert health["status"] == "unhealthy"
        assert "Health check error" in str(health["issues"])

    @pytest.mark.asyncio
    async def test_periodic_content_hash_check_task(self, sync_conflict_monitor):
        """Test periodic content hash check background task."""
        monitor = sync_conflict_monitor
        monitor.content_hash_check_interval_hours = 0.001  # Very short for testing

        await monitor.start_monitoring()

        # Let the task run briefly
        await asyncio.sleep(0.1)

        await monitor.stop_monitoring()

        # Task should have been created and cancelled
        assert len(monitor._monitoring_tasks) == 0

    def test_sync_operation_metrics_creation(self):
        """Test SyncOperationMetrics creation and methods."""
        metrics = SyncOperationMetrics(
            operation_id="op_001",
            operation_type=SyncOperationType.CREATE_DOCUMENT,
        )

        assert metrics.operation_id == "op_001"
        assert metrics.operation_type == SyncOperationType.CREATE_DOCUMENT
        assert metrics.status == SyncOperationStatus.PENDING
        assert metrics.duration_seconds is None

        # Test adding error and warning
        metrics.add_error("Test error")
        metrics.add_warning("Test warning")

        assert len(metrics.errors) == 1
        assert len(metrics.warnings) == 1
        assert "Test error" in metrics.errors[0]
        assert "Test warning" in metrics.warnings[0]

        # Test marking completed
        metrics.mark_completed(SyncOperationStatus.COMPLETED)

        assert metrics.status == SyncOperationStatus.COMPLETED
        assert metrics.end_time is not None
        assert metrics.duration_seconds is not None

    def test_sync_operation_metrics_to_dict(self):
        """Test SyncOperationMetrics to_dict conversion."""
        metrics = SyncOperationMetrics(
            operation_id="op_001",
            operation_type=SyncOperationType.CREATE_DOCUMENT,
        )
        metrics.add_error("Test error")
        metrics.mark_completed(SyncOperationStatus.COMPLETED)

        data = metrics.to_dict()

        assert data["operation_id"] == "op_001"
        assert data["operation_type"] == "create_document"
        assert data["status"] == "completed"
        assert data["duration_seconds"] is not None
        assert len(data["errors"]) == 1

    def test_content_hash_comparison_creation(self):
        """Test ContentHashComparison creation and methods."""
        comparison = ContentHashComparison(
            mapping_id="mapping_001",
            entity_id="doc_001",
            qdrant_hash="hash1",
            neo4j_hash="hash2",
            status=ContentHashStatus.MISMATCH,
        )

        assert comparison.mapping_id == "mapping_001"
        assert comparison.entity_id == "doc_001"
        assert comparison.status == ContentHashStatus.MISMATCH

        data = comparison.to_dict()

        assert data["mapping_id"] == "mapping_001"
        assert data["status"] == "mismatch"
        assert data["qdrant_hash"] == "hash1"
        assert data["neo4j_hash"] == "hash2"

    def test_monitoring_level_enum_values(self):
        """Test SyncMonitoringLevel enum values."""
        assert SyncMonitoringLevel.MINIMAL.value == "minimal"
        assert SyncMonitoringLevel.STANDARD.value == "standard"
        assert SyncMonitoringLevel.DETAILED.value == "detailed"
        assert SyncMonitoringLevel.DEBUG.value == "debug"

    def test_content_hash_status_enum_values(self):
        """Test ContentHashStatus enum values."""
        assert ContentHashStatus.MATCH.value == "match"
        assert ContentHashStatus.MISMATCH.value == "mismatch"
        assert ContentHashStatus.MISSING_SOURCE.value == "missing_source"
        assert ContentHashStatus.MISSING_TARGET.value == "missing_target"
        assert ContentHashStatus.BOTH_MISSING.value == "both_missing"
        assert ContentHashStatus.HASH_ERROR.value == "hash_error"

    @pytest.mark.asyncio
    async def test_monitoring_disabled_features(
        self,
        mock_enhanced_sync_system,
        mock_conflict_resolution_system,
        mock_qdrant_manager,
        mock_neo4j_manager,
        mock_id_mapping_manager,
        sample_sync_operation,
    ):
        """Test monitoring with disabled features."""
        monitor = SyncConflictMonitor(
            enhanced_sync_system=mock_enhanced_sync_system,
            conflict_resolution_system=mock_conflict_resolution_system,
            qdrant_manager=mock_qdrant_manager,
            neo4j_manager=mock_neo4j_manager,
            id_mapping_manager=mock_id_mapping_manager,
            enable_content_hash_sync=False,
            enable_automatic_conflict_resolution=False,
        )

        operation = sample_sync_operation
        operation.status = SyncOperationStatus.COMPLETED

        metrics = await monitor.monitor_sync_operation(operation)

        # Should not perform content hash comparison or conflict resolution
        assert metrics.content_hash_comparison is None
        assert metrics.conflicts_detected == 0
        assert metrics.conflicts_resolved == 0

    @pytest.mark.asyncio
    async def test_concurrent_hash_checks_semaphore(self, sync_conflict_monitor):
        """Test concurrent hash checks are limited by semaphore."""
        monitor = sync_conflict_monitor
        monitor.max_concurrent_hash_checks = 2
        monitor._hash_check_semaphore = asyncio.Semaphore(2)

        # Start multiple hash checks concurrently
        tasks = [monitor._perform_content_hash_comparison(f"doc_{i}") for i in range(5)]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete successfully
        assert len(results) == 5
        for result in results:
            assert isinstance(result, ContentHashComparison)
