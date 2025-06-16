"""
Unit tests for EnhancedSyncEventSystem.

Tests event orchestration, operation queuing, statistics tracking, health monitoring,
and integration with atomic transactions and operation differentiation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from qdrant_loader.core.managers import MappingType
from qdrant_loader.core.operation_differentiation import (
    OperationCharacteristics,
    OperationComplexity,
    OperationImpact,
    OperationPriority,
    ValidationLevel,
    ValidationResult,
)
from qdrant_loader.core.sync import (
    ChangeEvent,
    ChangeType,
    DatabaseType,
    EnhancedSyncEventSystem,
    EnhancedSyncOperation,
    SyncOperationStatus,
    SyncOperationType,
)
from qdrant_loader.core.types import EntityType


class TestEnhancedSyncEventSystem:
    """Test suite for EnhancedSyncEventSystem."""

    @pytest.fixture
    def mock_qdrant_manager(self):
        """Create mock QdrantManager."""
        mock = AsyncMock()
        mock.upsert_points = AsyncMock(return_value=True)
        mock.delete_points = AsyncMock(return_value=True)
        mock.search = AsyncMock(return_value=[])
        mock.health_check = AsyncMock(return_value={"healthy": True})
        return mock

    @pytest.fixture
    def mock_neo4j_manager(self):
        """Create mock Neo4jManager."""
        mock = AsyncMock()
        mock.create_node = AsyncMock(return_value={"id": "test_node"})
        mock.update_node = AsyncMock(return_value=True)
        mock.delete_node = AsyncMock(return_value=True)
        mock.health_check = AsyncMock(return_value={"healthy": True})
        return mock

    @pytest.fixture
    def mock_id_mapping_manager(self):
        """Create mock IDMappingManager."""
        mock = AsyncMock()
        mock.get_mapping = AsyncMock(return_value=None)
        mock.create_mapping = AsyncMock(return_value=True)
        mock.update_mapping = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def mock_atomic_transaction_manager(self):
        """Create mock AtomicTransactionManager."""
        mock = AsyncMock()
        mock.transaction = AsyncMock()
        mock.health_check = AsyncMock(return_value={"healthy": True})
        return mock

    @pytest.fixture
    def mock_operation_differentiation_manager(self):
        """Create mock OperationDifferentiationManager."""
        mock = AsyncMock()

        # Create mock characteristics and validation result
        mock_characteristics = OperationCharacteristics(
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            priority=OperationPriority.MEDIUM,
            complexity=OperationComplexity.MODERATE,
            impact=OperationImpact.LOCAL,
            validation_level=ValidationLevel.STANDARD,
        )

        mock_validation = ValidationResult(
            is_valid=True,
            validation_level=ValidationLevel.STANDARD,
            errors=[],
            warnings=[],
            recommendations=[],
            validation_time=0.1,
        )

        mock.process_operation = AsyncMock(
            return_value=(mock_characteristics, mock_validation)
        )
        mock.get_statistics = AsyncMock(
            return_value={
                "operations_processed": 10,
                "high_priority_operations": 2,
                "medium_priority_operations": 5,
                "low_priority_operations": 3,
            }
        )
        mock.health_check = AsyncMock(return_value={"healthy": True})
        return mock

    @pytest.fixture
    def mock_base_sync_system(self):
        """Create mock base SyncEventSystem."""
        mock = AsyncMock()
        mock.start = AsyncMock()
        mock.stop = AsyncMock()
        mock.add_event_handler = MagicMock()
        mock.health_check = AsyncMock(return_value={"healthy": True})
        return mock

    @pytest.fixture
    def mock_graphiti_temporal_integration(self):
        """Create mock GraphitiTemporalIntegration."""
        mock = AsyncMock()
        mock.health_check = AsyncMock(return_value={"healthy": True})
        return mock

    @pytest.fixture
    def mock_sync_conflict_monitor(self):
        """Create mock SyncConflictMonitor."""
        mock = AsyncMock()
        mock.health_check = AsyncMock(return_value={"status": "healthy"})
        return mock

    @pytest.fixture
    def enhanced_sync_system(
        self,
        mock_qdrant_manager,
        mock_neo4j_manager,
        mock_id_mapping_manager,
        mock_atomic_transaction_manager,
    ):
        """Create EnhancedSyncEventSystem instance for testing."""
        return EnhancedSyncEventSystem(
            qdrant_manager=mock_qdrant_manager,
            neo4j_manager=mock_neo4j_manager,
            id_mapping_manager=mock_id_mapping_manager,
            atomic_transaction_manager=mock_atomic_transaction_manager,
            max_concurrent_operations=5,
            operation_timeout_seconds=30,
            enable_cascading_deletes=True,
            enable_versioned_updates=True,
            enable_graphiti_temporal_features=True,
            enable_operation_differentiation=True,
        )

    @pytest.fixture
    def enhanced_sync_system_with_mocks(
        self,
        mock_qdrant_manager,
        mock_neo4j_manager,
        mock_id_mapping_manager,
        mock_atomic_transaction_manager,
        mock_base_sync_system,
        mock_graphiti_temporal_integration,
        mock_sync_conflict_monitor,
    ):
        """Create EnhancedSyncEventSystem with all optional components mocked."""
        return EnhancedSyncEventSystem(
            qdrant_manager=mock_qdrant_manager,
            neo4j_manager=mock_neo4j_manager,
            id_mapping_manager=mock_id_mapping_manager,
            atomic_transaction_manager=mock_atomic_transaction_manager,
            graphiti_temporal_integration=mock_graphiti_temporal_integration,
            base_sync_system=mock_base_sync_system,
            sync_conflict_monitor=mock_sync_conflict_monitor,
            max_concurrent_operations=3,
            operation_timeout_seconds=60,
            enable_cascading_deletes=False,
            enable_versioned_updates=False,
            enable_graphiti_temporal_features=False,
            enable_operation_differentiation=False,
        )

    def test_initialization_basic(self, enhanced_sync_system):
        """Test basic initialization of EnhancedSyncEventSystem."""
        assert enhanced_sync_system.max_concurrent_operations == 5
        assert enhanced_sync_system.operation_timeout_seconds == 30
        assert enhanced_sync_system.enable_cascading_deletes is True
        assert enhanced_sync_system.enable_versioned_updates is True
        assert enhanced_sync_system.enable_graphiti_temporal_features is True
        assert enhanced_sync_system.enable_operation_differentiation is True
        assert enhanced_sync_system._running is False
        assert len(enhanced_sync_system._processing_tasks) == 0

    def test_initialization_with_all_components(self, enhanced_sync_system_with_mocks):
        """Test initialization with all optional components."""
        system = enhanced_sync_system_with_mocks
        assert system.graphiti_temporal_integration is not None
        assert system.base_sync_system is not None
        assert system.sync_conflict_monitor is not None
        assert system.max_concurrent_operations == 3
        assert system.operation_timeout_seconds == 60
        assert system.enable_cascading_deletes is False
        assert system.enable_versioned_updates is False
        assert system.enable_graphiti_temporal_features is False
        assert system.enable_operation_differentiation is False

    def test_operation_differentiation_manager_creation(self, enhanced_sync_system):
        """Test that OperationDifferentiationManager is created when enabled."""
        assert enhanced_sync_system.operation_differentiation_manager is not None
        assert enhanced_sync_system.enable_operation_differentiation is True

    def test_operation_differentiation_manager_disabled(
        self, enhanced_sync_system_with_mocks
    ):
        """Test that OperationDifferentiationManager is None when disabled."""
        assert enhanced_sync_system_with_mocks.operation_differentiation_manager is None
        assert enhanced_sync_system_with_mocks.enable_operation_differentiation is False

    @pytest.mark.asyncio
    async def test_start_stop_basic(self, enhanced_sync_system):
        """Test basic start and stop functionality."""
        # Test start
        await enhanced_sync_system.start()
        assert enhanced_sync_system._running is True
        assert (
            len(enhanced_sync_system._processing_tasks) == 5
        )  # max_concurrent_operations

        # Test stop
        await enhanced_sync_system.stop()
        assert enhanced_sync_system._running is False
        assert len(enhanced_sync_system._processing_tasks) == 0

    @pytest.mark.asyncio
    async def test_start_stop_with_base_system(self, enhanced_sync_system_with_mocks):
        """Test start and stop with base sync system integration."""
        system = enhanced_sync_system_with_mocks

        # Test start
        await system.start()
        assert system._running is True
        system.base_sync_system.start.assert_called_once()

        # Test stop
        await system.stop()
        assert system._running is False
        system.base_sync_system.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_already_running(self, enhanced_sync_system):
        """Test starting system when already running."""
        await enhanced_sync_system.start()
        initial_task_count = len(enhanced_sync_system._processing_tasks)

        # Try to start again
        await enhanced_sync_system.start()

        # Should not create additional tasks
        assert len(enhanced_sync_system._processing_tasks) == initial_task_count

        await enhanced_sync_system.stop()

    @pytest.mark.asyncio
    async def test_queue_operation_with_differentiation(
        self, enhanced_sync_system, mock_operation_differentiation_manager
    ):
        """Test queuing operation with operation differentiation enabled."""
        # Mock the operation differentiation manager
        enhanced_sync_system.operation_differentiation_manager = (
            mock_operation_differentiation_manager
        )

        operation = EnhancedSyncOperation(
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            entity_id="test_doc_001",
            operation_data={"content": "test content", "embedding": [0.1] * 384},
        )

        await enhanced_sync_system.queue_operation(operation)

        # Verify operation differentiation was called
        mock_operation_differentiation_manager.process_operation.assert_called_once()

        # Verify metadata was updated with characteristics and validation results
        assert "operation_characteristics" in operation.metadata
        assert "validation_result" in operation.metadata

        characteristics_data = operation.metadata["operation_characteristics"]
        assert "priority" in characteristics_data
        assert "complexity" in characteristics_data
        assert "impact" in characteristics_data
        assert "priority_score" in characteristics_data

    @pytest.mark.asyncio
    async def test_queue_operation_validation_failure(
        self, enhanced_sync_system, mock_operation_differentiation_manager
    ):
        """Test queuing operation with validation failure."""
        # Configure mock to return validation failure
        mock_validation = ValidationResult(
            is_valid=False,
            validation_level=ValidationLevel.STANDARD,
            errors=["Invalid operation data", "Missing required field"],
            warnings=[],
            recommendations=[],
            validation_time=0.1,
        )

        mock_characteristics = OperationCharacteristics(
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            priority=OperationPriority.LOW,
            complexity=OperationComplexity.SIMPLE,
            impact=OperationImpact.MINIMAL,
            validation_level=ValidationLevel.STANDARD,
        )

        mock_operation_differentiation_manager.process_operation = AsyncMock(
            return_value=(mock_characteristics, mock_validation)
        )
        enhanced_sync_system.operation_differentiation_manager = (
            mock_operation_differentiation_manager
        )

        operation = EnhancedSyncOperation(
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            entity_id="invalid_doc",
            operation_data={},  # Invalid/empty data
        )

        await enhanced_sync_system.queue_operation(operation)

        # Verify operation was marked as failed
        assert operation.status == SyncOperationStatus.FAILED
        assert operation.error_message is not None
        assert "validation failed" in operation.error_message.lower()

        # Verify operation was added to failed operations
        assert operation.operation_id in enhanced_sync_system._failed_operations

    @pytest.mark.asyncio
    async def test_queue_operation_without_differentiation(
        self, enhanced_sync_system_with_mocks
    ):
        """Test queuing operation without operation differentiation."""
        system = enhanced_sync_system_with_mocks  # Has differentiation disabled

        operation = EnhancedSyncOperation(
            operation_type=SyncOperationType.UPDATE_DOCUMENT,
            entity_id="test_doc_002",
            operation_data={"content": "updated content"},
        )

        await system.queue_operation(operation)

        # Verify operation was queued in legacy mode
        assert system._pending_operations.qsize() == 1

    @pytest.mark.asyncio
    async def test_queue_operation_with_warnings(
        self, enhanced_sync_system, mock_operation_differentiation_manager
    ):
        """Test queuing operation with validation warnings."""
        # Configure mock to return validation with warnings
        mock_validation = ValidationResult(
            is_valid=True,
            validation_level=ValidationLevel.STANDARD,
            errors=[],
            warnings=["Performance warning", "Deprecated field used"],
            recommendations=["Consider using new API"],
            validation_time=0.2,
        )

        mock_characteristics = OperationCharacteristics(
            operation_type=SyncOperationType.DELETE_DOCUMENT,
            priority=OperationPriority.HIGH,
            complexity=OperationComplexity.COMPLEX,
            impact=OperationImpact.REGIONAL,
            validation_level=ValidationLevel.STRICT,
        )

        mock_operation_differentiation_manager.process_operation = AsyncMock(
            return_value=(mock_characteristics, mock_validation)
        )
        enhanced_sync_system.operation_differentiation_manager = (
            mock_operation_differentiation_manager
        )

        operation = EnhancedSyncOperation(
            operation_type=SyncOperationType.DELETE_DOCUMENT,
            entity_id="test_doc_003",
            operation_data={"deprecated_field": "value"},
        )

        await enhanced_sync_system.queue_operation(operation)

        # Verify operation was processed successfully despite warnings
        assert operation.status == SyncOperationStatus.PENDING
        assert "validation_result" in operation.metadata

        validation_data = operation.metadata["validation_result"]
        assert validation_data["warnings_count"] == 2
        assert validation_data["recommendations_count"] == 1

    def test_create_operation_from_event_document_create(self, enhanced_sync_system):
        """Test creating operation from document create event."""
        event = ChangeEvent(
            event_id="test_event_001",
            database_type=DatabaseType.QDRANT,
            change_type=ChangeType.CREATE,
            entity_id="doc_001",
            entity_uuid="uuid_001",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            new_data={"content": "test document", "embedding": [0.1] * 384},
            affected_fields={"content", "embedding"},
        )

        operation = enhanced_sync_system._create_operation_from_event(event)

        assert operation is not None
        assert operation.operation_type == SyncOperationType.CREATE_DOCUMENT
        assert operation.entity_id == "doc_001"
        assert operation.entity_uuid == "uuid_001"
        assert DatabaseType.NEO4J in operation.target_databases
        assert operation.source_event == event

    def test_create_operation_from_event_entity_update(self, enhanced_sync_system):
        """Test creating operation from entity update event."""
        event = ChangeEvent(
            event_id="test_event_002",
            database_type=DatabaseType.NEO4J,
            change_type=ChangeType.UPDATE,
            entity_id="entity_001",
            entity_uuid="uuid_002",
            entity_type=EntityType.PERSON,
            mapping_type=MappingType.ENTITY,
            new_data={"name": "Updated Name", "properties": {"age": 30}},
            old_data={"name": "Old Name", "properties": {"age": 25}},
            affected_fields={"name", "properties.age"},
        )

        operation = enhanced_sync_system._create_operation_from_event(event)

        assert operation is not None
        assert operation.operation_type == SyncOperationType.UPDATE_ENTITY
        assert operation.entity_id == "entity_001"
        assert DatabaseType.QDRANT in operation.target_databases
        assert operation.previous_data == event.old_data

    def test_create_operation_from_event_unsupported_change_type(
        self, enhanced_sync_system
    ):
        """Test creating operation from event with unsupported change type."""
        # Mock an event with unsupported change type using patch
        with patch(
            "qdrant_loader.core.sync.enhanced_event_system.ChangeEvent"
        ) as mock_event_class:
            mock_event = MagicMock()
            mock_event.event_id = "test_event_003"
            mock_event.database_type = DatabaseType.QDRANT
            mock_event.change_type = "UNSUPPORTED_TYPE"  # Invalid change type
            mock_event.entity_id = "doc_002"
            mock_event.entity_type = EntityType.CONCEPT
            mock_event.mapping_type = MappingType.DOCUMENT

            operation = enhanced_sync_system._create_operation_from_event(mock_event)

            assert operation is None

    @pytest.mark.asyncio
    async def test_get_operation_statistics_basic(self, enhanced_sync_system):
        """Test getting basic operation statistics."""
        # Add some test operations to different collections
        test_op = EnhancedSyncOperation(
            operation_type=SyncOperationType.CREATE_DOCUMENT
        )
        enhanced_sync_system._completed_operations[test_op.operation_id] = test_op
        enhanced_sync_system._stats["operations_processed"] = 5
        enhanced_sync_system._stats["create_operations"] = 3

        stats = await enhanced_sync_system.get_operation_statistics()

        assert "operations_processed" in stats
        assert "pending_operations" in stats
        assert "active_operations" in stats
        assert "completed_operations" in stats
        assert "failed_operations" in stats
        assert "running" in stats
        assert "operation_differentiation_enabled" in stats

        assert stats["operations_processed"] == 5
        assert stats["create_operations"] == 3
        assert stats["completed_operations"] == 1
        assert stats["running"] is False
        assert stats["operation_differentiation_enabled"] is True

    @pytest.mark.asyncio
    async def test_get_operation_statistics_with_differentiation(
        self, enhanced_sync_system, mock_operation_differentiation_manager
    ):
        """Test getting statistics with operation differentiation enabled."""
        enhanced_sync_system.operation_differentiation_manager = (
            mock_operation_differentiation_manager
        )

        stats = await enhanced_sync_system.get_operation_statistics()

        assert "operation_differentiation" in stats
        differentiation_stats = stats["operation_differentiation"]
        assert "operations_processed" in differentiation_stats
        assert "high_priority_operations" in differentiation_stats

    @pytest.mark.asyncio
    async def test_get_operation_statistics_differentiation_error(
        self, enhanced_sync_system, mock_operation_differentiation_manager
    ):
        """Test getting statistics when operation differentiation throws error."""
        # Configure mock to raise exception
        mock_operation_differentiation_manager.get_statistics = AsyncMock(
            side_effect=Exception("Statistics error")
        )
        enhanced_sync_system.operation_differentiation_manager = (
            mock_operation_differentiation_manager
        )

        stats = await enhanced_sync_system.get_operation_statistics()

        assert "operation_differentiation" in stats
        assert "error" in stats["operation_differentiation"]
        assert stats["operation_differentiation"]["error"] == "Statistics error"

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, enhanced_sync_system_with_mocks):
        """Test health check when all components are healthy."""
        system = enhanced_sync_system_with_mocks
        system._running = True

        health = await system.health_check()

        assert health["healthy"] is True
        assert health["enhanced_system_running"] is True
        assert "base_system_health" in health
        assert "transaction_manager_health" in health
        assert "graphiti_temporal_health" in health
        assert "sync_conflict_monitor_health" in health
        assert "operation_stats" in health

    @pytest.mark.asyncio
    async def test_health_check_component_unhealthy(
        self, enhanced_sync_system_with_mocks
    ):
        """Test health check when a component is unhealthy."""
        system = enhanced_sync_system_with_mocks
        system._running = True

        # Make one component unhealthy
        system.sync_conflict_monitor.health_check = AsyncMock(
            return_value={"status": "unhealthy", "error": "Database connection failed"}
        )

        health = await system.health_check()

        assert health["healthy"] is False
        assert health["sync_conflict_monitor_health"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_check_component_exception(
        self, enhanced_sync_system_with_mocks
    ):
        """Test health check when a component throws exception."""
        system = enhanced_sync_system_with_mocks
        system._running = True

        # Make component throw exception
        system.graphiti_temporal_integration.health_check = AsyncMock(
            side_effect=Exception("Connection timeout")
        )

        health = await system.health_check()

        assert health["healthy"] is False
        assert "error" in health["graphiti_temporal_health"]
        assert health["graphiti_temporal_health"]["error"] == "Connection timeout"

    @pytest.mark.asyncio
    async def test_health_check_system_not_running(self, enhanced_sync_system):
        """Test health check when system is not running."""
        # System is not started
        health = await enhanced_sync_system.health_check()

        assert health["enhanced_system_running"] is False

    @pytest.mark.asyncio
    async def test_health_check_exception_handling(self, enhanced_sync_system):
        """Test health check exception handling."""
        # Mock get_operation_statistics to raise exception
        with patch.object(
            enhanced_sync_system,
            "get_operation_statistics",
            side_effect=Exception("Stats error"),
        ):
            health = await enhanced_sync_system.health_check()

            assert health["healthy"] is False
            assert "error" in health
            assert health["error"] == "Stats error"

    def test_base_system_integration_setup(self, enhanced_sync_system_with_mocks):
        """Test base system integration setup."""
        system = enhanced_sync_system_with_mocks

        # Verify event handler was registered
        system.base_sync_system.add_event_handler.assert_called_once_with(
            "*", system._on_base_change_event
        )

    def test_on_base_change_event_not_running(self, enhanced_sync_system_with_mocks):
        """Test handling base change event when system is not running."""
        system = enhanced_sync_system_with_mocks

        event = ChangeEvent(
            event_id="test_event",
            database_type=DatabaseType.QDRANT,
            change_type=ChangeType.CREATE,
            entity_id="test_entity",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
        )

        # Should return early since system is not running
        system._on_base_change_event(event)

        # No operations should be queued
        assert system._pending_operations.qsize() == 0

    @pytest.mark.asyncio
    async def test_queue_operation_exception_handling(
        self, enhanced_sync_system, mock_operation_differentiation_manager
    ):
        """Test queue operation exception handling."""
        # Configure mock to raise exception
        mock_operation_differentiation_manager.process_operation = AsyncMock(
            side_effect=Exception("Processing error")
        )
        enhanced_sync_system.operation_differentiation_manager = (
            mock_operation_differentiation_manager
        )

        operation = EnhancedSyncOperation(
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            entity_id="error_doc",
        )

        await enhanced_sync_system.queue_operation(operation)

        # Verify operation was marked as failed
        assert operation.status == SyncOperationStatus.FAILED
        assert operation.error_message is not None
        assert "Processing error" in operation.error_message
        assert operation.operation_id in enhanced_sync_system._failed_operations

    def test_operation_handlers_registration(self, enhanced_sync_system):
        """Test that operation handlers are properly registered."""
        handlers = enhanced_sync_system._operation_handlers

        expected_operations = [
            SyncOperationType.CREATE_DOCUMENT,
            SyncOperationType.UPDATE_DOCUMENT,
            SyncOperationType.DELETE_DOCUMENT,
            SyncOperationType.CREATE_ENTITY,
            SyncOperationType.UPDATE_ENTITY,
            SyncOperationType.DELETE_ENTITY,
            SyncOperationType.CASCADE_DELETE,
            SyncOperationType.VERSION_UPDATE,
        ]

        for operation_type in expected_operations:
            assert operation_type in handlers
            assert callable(handlers[operation_type])

    def test_statistics_initialization(self, enhanced_sync_system):
        """Test that statistics are properly initialized."""
        stats = enhanced_sync_system._stats

        expected_stats = [
            "operations_processed",
            "operations_failed",
            "operations_rolled_back",
            "create_operations",
            "update_operations",
            "delete_operations",
            "cascade_operations",
            "version_operations",
        ]

        for stat_key in expected_stats:
            assert stat_key in stats
            assert stats[stat_key] == 0

    def test_semaphore_initialization(self, enhanced_sync_system):
        """Test that semaphore is initialized with correct value."""
        assert (
            enhanced_sync_system._semaphore._value
            == enhanced_sync_system.max_concurrent_operations
        )

    @pytest.mark.asyncio
    async def test_multiple_operations_queuing(self, enhanced_sync_system_with_mocks):
        """Test queuing multiple operations."""
        # Use system with differentiation disabled for legacy queue testing
        system = enhanced_sync_system_with_mocks

        operations = []
        for i in range(5):
            operation = EnhancedSyncOperation(
                operation_type=SyncOperationType.CREATE_DOCUMENT,
                entity_id=f"doc_{i}",
                operation_data={"content": f"content {i}"},
            )
            operations.append(operation)
            await system.queue_operation(operation)

        # All operations should be queued (fallback mode since no differentiation manager)
        assert system._pending_operations.qsize() == 5

    def test_configuration_flags(self, enhanced_sync_system):
        """Test configuration flags are properly set."""
        assert enhanced_sync_system.enable_cascading_deletes is True
        assert enhanced_sync_system.enable_versioned_updates is True
        assert enhanced_sync_system.enable_graphiti_temporal_features is True
        assert enhanced_sync_system.enable_operation_differentiation is True
        assert enhanced_sync_system.max_concurrent_operations == 5
        assert enhanced_sync_system.operation_timeout_seconds == 30
