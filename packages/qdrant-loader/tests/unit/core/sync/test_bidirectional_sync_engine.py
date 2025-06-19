"""Comprehensive tests for BidirectionalSyncEngine.

Tests cover all enums, dataclasses, and the main sync engine functionality
with proper mocking of external dependencies.
"""

import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_client.http.models import PointStruct

from qdrant_loader.core.managers import IDMapping, MappingStatus, MappingType
from qdrant_loader.core.sync.bidirectional_sync_engine import (
    BidirectionalSyncEngine,
    SyncBatch,
    SyncDirection,
    SyncOperation,
    SyncStrategy,
)
from qdrant_loader.core.sync.event_system import (
    ChangeEvent,
    ChangeType,
    DatabaseType,
    SyncEventSystem,
)
from qdrant_loader.core.types import EntityType


class TestSyncDirection:
    """Test SyncDirection enum."""

    def test_sync_direction_values(self):
        """Test SyncDirection enum values."""
        assert SyncDirection.QDRANT_TO_NEO4J.value == "qdrant_to_neo4j"
        assert SyncDirection.NEO4J_TO_QDRANT.value == "neo4j_to_qdrant"
        assert SyncDirection.BIDIRECTIONAL.value == "bidirectional"

    def test_sync_direction_members(self):
        """Test SyncDirection enum members."""
        directions = list(SyncDirection)
        assert len(directions) == 3
        assert SyncDirection.QDRANT_TO_NEO4J in directions
        assert SyncDirection.NEO4J_TO_QDRANT in directions
        assert SyncDirection.BIDIRECTIONAL in directions


class TestSyncStrategy:
    """Test SyncStrategy enum."""

    def test_sync_strategy_values(self):
        """Test SyncStrategy enum values."""
        assert SyncStrategy.IMMEDIATE.value == "immediate"
        assert SyncStrategy.BATCH.value == "batch"
        assert SyncStrategy.SCHEDULED.value == "scheduled"

    def test_sync_strategy_members(self):
        """Test SyncStrategy enum members."""
        strategies = list(SyncStrategy)
        assert len(strategies) == 3
        assert SyncStrategy.IMMEDIATE in strategies
        assert SyncStrategy.BATCH in strategies
        assert SyncStrategy.SCHEDULED in strategies


class TestSyncOperation:
    """Test SyncOperation dataclass."""

    def test_sync_operation_creation(self):
        """Test SyncOperation creation with defaults."""
        operation = SyncOperation()

        assert operation.operation_id is not None
        assert len(operation.operation_id) > 0
        assert operation.event is not None
        assert operation.direction == SyncDirection.BIDIRECTIONAL
        assert operation.mapping is None
        assert operation.started_at is None
        assert operation.completed_at is None
        assert operation.success is False
        assert operation.error_message is None
        assert operation.retry_count == 0
        assert operation.transaction_id is None
        assert operation.rollback_data is None

    def test_sync_operation_with_custom_values(self):
        """Test SyncOperation creation with custom values."""
        event = ChangeEvent(
            change_type=ChangeType.CREATE,
            database_type=DatabaseType.QDRANT,
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            entity_id="test_id",
            entity_name="test_doc",
        )
        mapping = IDMapping(
            mapping_id="test_mapping",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            entity_name="test_doc",
        )

        operation = SyncOperation(
            event=event, direction=SyncDirection.QDRANT_TO_NEO4J, mapping=mapping
        )

        assert operation.event == event
        assert operation.direction == SyncDirection.QDRANT_TO_NEO4J
        assert operation.mapping == mapping

    def test_mark_started(self):
        """Test mark_started method."""
        operation = SyncOperation()
        assert operation.started_at is None

        operation.mark_started()

        assert operation.started_at is not None
        assert isinstance(operation.started_at, datetime)
        assert operation.started_at.tzinfo == UTC

    def test_mark_completed_success(self):
        """Test mark_completed method with success."""
        operation = SyncOperation()
        assert operation.completed_at is None
        assert operation.success is False

        operation.mark_completed(success=True)

        assert operation.completed_at is not None
        assert isinstance(operation.completed_at, datetime)
        assert operation.completed_at.tzinfo == UTC
        assert operation.success is True
        assert operation.error_message is None

    def test_mark_completed_failure(self):
        """Test mark_completed method with failure."""
        operation = SyncOperation()
        error_msg = "Test error"

        operation.mark_completed(success=False, error=error_msg)

        assert operation.completed_at is not None
        assert operation.success is False
        assert operation.error_message == error_msg

    def test_duration_ms_without_times(self):
        """Test duration_ms when times not set."""
        operation = SyncOperation()
        assert operation.duration_ms() is None

    def test_duration_ms_with_times(self):
        """Test duration_ms calculation."""
        operation = SyncOperation()
        operation.mark_started()
        # Simulate some time passing
        import time

        time.sleep(0.01)
        operation.mark_completed()

        duration = operation.duration_ms()
        assert duration is not None
        assert duration > 0
        assert duration >= 10  # At least 10ms


class TestSyncBatch:
    """Test SyncBatch dataclass."""

    def test_sync_batch_creation(self):
        """Test SyncBatch creation with defaults."""
        batch = SyncBatch()

        assert batch.batch_id is not None
        assert len(batch.batch_id) > 0
        assert batch.operations == []
        assert batch.direction == SyncDirection.BIDIRECTIONAL
        assert batch.created_at is not None
        assert isinstance(batch.created_at, datetime)
        assert batch.started_at is None
        assert batch.completed_at is None
        assert batch.successful_operations == 0
        assert batch.failed_operations == 0
        assert batch.total_operations == 0

    def test_add_operation(self):
        """Test adding operations to batch."""
        batch = SyncBatch()
        operation1 = SyncOperation()
        operation2 = SyncOperation()

        batch.add_operation(operation1)
        assert len(batch.operations) == 1
        assert batch.total_operations == 1
        assert batch.operations[0] == operation1

        batch.add_operation(operation2)
        assert len(batch.operations) == 2
        assert batch.total_operations == 2

    def test_mark_started(self):
        """Test mark_started method."""
        batch = SyncBatch()
        assert batch.started_at is None

        batch.mark_started()

        assert batch.started_at is not None
        assert isinstance(batch.started_at, datetime)

    def test_mark_completed(self):
        """Test mark_completed method."""
        batch = SyncBatch()

        # Add some operations with different success states
        op1 = SyncOperation()
        op1.success = True
        op2 = SyncOperation()
        op2.success = False
        op3 = SyncOperation()
        op3.success = True

        batch.add_operation(op1)
        batch.add_operation(op2)
        batch.add_operation(op3)

        batch.mark_completed()

        assert batch.completed_at is not None
        assert batch.successful_operations == 2
        assert batch.failed_operations == 1

    def test_success_rate_empty_batch(self):
        """Test success_rate with empty batch."""
        batch = SyncBatch()
        assert batch.success_rate() == 0.0

    def test_success_rate_with_operations(self):
        """Test success_rate calculation."""
        batch = SyncBatch()

        # Add operations with mixed success
        for i in range(5):
            op = SyncOperation()
            op.success = i < 3  # First 3 succeed, last 2 fail
            batch.add_operation(op)

        batch.mark_completed()
        rate = batch.success_rate()

        assert rate == 0.6  # 3/5 = 0.6


class TestBidirectionalSyncEngine:
    """Test BidirectionalSyncEngine class."""

    @pytest.fixture
    def mock_managers(self):
        """Create mock managers for testing."""
        qdrant_manager = AsyncMock()
        neo4j_manager = MagicMock()
        id_mapping_manager = AsyncMock()
        sync_event_system = MagicMock(spec=SyncEventSystem)

        return {
            "qdrant_manager": qdrant_manager,
            "neo4j_manager": neo4j_manager,
            "id_mapping_manager": id_mapping_manager,
            "sync_event_system": sync_event_system,
        }

    @pytest.fixture
    def sync_engine(self, mock_managers):
        """Create BidirectionalSyncEngine instance for testing."""
        return BidirectionalSyncEngine(**mock_managers)

    def test_initialization(self, mock_managers):
        """Test engine initialization."""
        engine = BidirectionalSyncEngine(**mock_managers)

        assert engine.qdrant_manager == mock_managers["qdrant_manager"]
        assert engine.neo4j_manager == mock_managers["neo4j_manager"]
        assert engine.id_mapping_manager == mock_managers["id_mapping_manager"]
        assert engine.sync_event_system == mock_managers["sync_event_system"]
        assert engine.sync_strategy == SyncStrategy.IMMEDIATE
        assert engine.batch_size == 100
        assert engine.batch_timeout_seconds == 30
        assert engine.max_retry_attempts == 3
        assert engine.enable_transaction_rollback is True
        assert engine._running is False
        assert engine._sync_task is None
        assert engine._pending_operations == []
        assert engine._current_batch is None
        assert engine._batch_timer is None

    def test_initialization_with_custom_params(self, mock_managers):
        """Test engine initialization with custom parameters."""
        engine = BidirectionalSyncEngine(
            **mock_managers,
            sync_strategy=SyncStrategy.BATCH,
            batch_size=50,
            batch_timeout_seconds=60,
            max_retry_attempts=5,
            enable_transaction_rollback=False,
        )

        assert engine.sync_strategy == SyncStrategy.BATCH
        assert engine.batch_size == 50
        assert engine.batch_timeout_seconds == 60
        assert engine.max_retry_attempts == 5
        assert engine.enable_transaction_rollback is False

    def test_register_event_handlers(self, sync_engine):
        """Test event handler registration."""
        # Verify the event system was called to add handler
        sync_engine.sync_event_system.add_event_handler.assert_called_once_with(
            "*", sync_engine._on_change_event
        )

    def test_on_change_event_not_running(self, sync_engine):
        """Test _on_change_event when engine not running."""
        event = ChangeEvent(
            change_type=ChangeType.CREATE,
            database_type=DatabaseType.QDRANT,
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            entity_id="test_id",
            entity_name="test_doc",
        )

        # Engine is not running by default
        sync_engine._on_change_event(event)

        # Should not add any operations
        assert len(sync_engine._pending_operations) == 0

    @pytest.mark.asyncio
    async def test_on_change_event_qdrant_source(self, sync_engine):
        """Test _on_change_event with QDrant source."""
        sync_engine._running = True
        event = ChangeEvent(
            change_type=ChangeType.CREATE,
            database_type=DatabaseType.QDRANT,
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            entity_id="test_id",
            entity_name="test_doc",
        )

        with patch.object(sync_engine, "_process_operation_immediate") as mock_process:
            mock_process.return_value = None
            sync_engine._on_change_event(event)
            # Wait for the async task to be created and executed
            await asyncio.sleep(0.01)

        # Should create operation with QDRANT_TO_NEO4J direction
        mock_process.assert_called_once()
        operation = mock_process.call_args[0][0]
        assert operation.direction == SyncDirection.QDRANT_TO_NEO4J

    def test_on_change_event_neo4j_source(self, sync_engine):
        """Test _on_change_event with Neo4j source."""
        sync_engine._running = True
        sync_engine.sync_strategy = SyncStrategy.BATCH
        event = ChangeEvent(
            change_type=ChangeType.CREATE,
            database_type=DatabaseType.NEO4J,
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            entity_id="test_id",
            entity_name="test_doc",
        )

        with patch.object(sync_engine, "_add_to_batch") as mock_batch:
            sync_engine._on_change_event(event)

        # Should create operation with NEO4J_TO_QDRANT direction
        mock_batch.assert_called_once()
        operation = mock_batch.call_args[0][0]
        assert operation.direction == SyncDirection.NEO4J_TO_QDRANT

    @pytest.mark.asyncio
    async def test_start_immediate_strategy(self, sync_engine):
        """Test starting engine with immediate strategy."""
        assert sync_engine._running is False

        await sync_engine.start()

        assert sync_engine._running is True
        # No batch processing task should be created for immediate strategy
        assert sync_engine._sync_task is None

    @pytest.mark.asyncio
    async def test_start_batch_strategy(self, sync_engine):
        """Test starting engine with batch strategy."""
        sync_engine.sync_strategy = SyncStrategy.BATCH

        with patch.object(sync_engine, "_batch_processing_loop") as mock_loop:
            # Mock the coroutine properly and ensure it's awaitable
            async def mock_batch_loop():
                await asyncio.sleep(0.001)  # Small delay to simulate work
                return None

            mock_loop.return_value = mock_batch_loop()

            await sync_engine.start()

            # Give the task a moment to start
            await asyncio.sleep(0.01)

            # Clean up the task
            if sync_engine._sync_task:
                sync_engine._sync_task.cancel()
                try:
                    await sync_engine._sync_task
                except asyncio.CancelledError:
                    pass

        assert sync_engine._running is True

    @pytest.mark.asyncio
    async def test_start_already_running(self, sync_engine):
        """Test starting engine when already running."""
        sync_engine._running = True

        await sync_engine.start()

        # Should remain running
        assert sync_engine._running is True

    @pytest.mark.asyncio
    async def test_stop(self, sync_engine):
        """Test stopping the engine."""
        sync_engine._running = True

        # Create a proper mock task that can be awaited
        async def mock_task_coro():
            return None

        mock_task = asyncio.create_task(mock_task_coro())
        # Mock the cancel method
        mock_task.cancel = MagicMock()

        sync_engine._sync_task = mock_task

        await sync_engine.stop()

        assert sync_engine._running is False
        mock_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_not_running(self, sync_engine):
        """Test stopping engine when not running."""
        assert sync_engine._running is False

        await sync_engine.stop()

        assert sync_engine._running is False

    @pytest.mark.asyncio
    async def test_process_operation_immediate(self, sync_engine):
        """Test immediate operation processing."""
        operation = SyncOperation()

        with patch.object(sync_engine, "_execute_sync_operation") as mock_execute:
            # Mock the coroutine properly using AsyncMock
            mock_execute.return_value = AsyncMock()

            await sync_engine._process_operation_immediate(operation)

        mock_execute.assert_called_once_with(operation)

    def test_add_to_batch_new_batch(self, sync_engine):
        """Test adding operation to batch (adds to pending operations)."""
        operation = SyncOperation()
        initial_count = len(sync_engine._pending_operations)

        sync_engine._add_to_batch(operation)

        # Should add to pending operations
        assert len(sync_engine._pending_operations) == initial_count + 1
        assert sync_engine._pending_operations[-1] == operation

    def test_add_to_batch_existing_batch(self, sync_engine):
        """Test adding multiple operations to batch."""
        operation1 = SyncOperation()
        operation2 = SyncOperation()

        sync_engine._add_to_batch(operation1)
        sync_engine._add_to_batch(operation2)

        assert len(sync_engine._pending_operations) == 2

    @pytest.mark.asyncio
    async def test_process_pending_operations_empty(self, sync_engine):
        """Test processing empty pending operations."""
        assert len(sync_engine._pending_operations) == 0

        await sync_engine._process_pending_operations()

        # Should not crash with empty list

    @pytest.mark.asyncio
    async def test_get_sync_statistics(self, sync_engine):
        """Test getting sync statistics."""
        sync_engine._total_operations = 100
        sync_engine._successful_operations = 80
        sync_engine._failed_operations = 20
        sync_engine._total_batches = 10
        sync_engine._pending_operations = [SyncOperation(), SyncOperation()]

        stats = await sync_engine.get_sync_statistics()

        assert stats["total_operations"] == 100
        assert stats["successful_operations"] == 80
        assert stats["failed_operations"] == 20
        assert stats["success_rate"] == 0.8
        assert stats["total_batches"] == 10
        assert stats["pending_operations"] == 2
        assert stats["sync_strategy"] == "immediate"
        assert stats["batch_size"] == 100
        assert stats["is_running"] is False

    @pytest.mark.asyncio
    async def test_health_check(self, sync_engine):
        """Test health check."""

        # Mock component health checks with proper async returns
        sync_engine.qdrant_manager.health_check = AsyncMock(
            return_value={"status": "healthy"}
        )

        sync_engine.neo4j_manager.health_check.return_value = {"status": "healthy"}

        sync_engine.id_mapping_manager.health_check = AsyncMock(
            return_value={"status": "healthy"}
        )

        sync_engine._running = True

        health = await sync_engine.health_check()

        assert health["sync_engine"]["status"] == "healthy"
        assert health["components"]["qdrant"]["status"] == "healthy"
        assert health["components"]["neo4j"]["status"] == "healthy"
        assert health["components"]["id_mapping"]["status"] == "healthy"
        assert health["overall_health"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, sync_engine):
        """Test health check with unhealthy components."""

        sync_engine.qdrant_manager.health_check = AsyncMock(
            return_value={"status": "unhealthy"}
        )

        sync_engine.neo4j_manager.health_check.return_value = {"status": "healthy"}

        sync_engine.id_mapping_manager.health_check = AsyncMock(
            return_value={"status": "healthy"}
        )

        health = await sync_engine.health_check()

        assert health["overall_health"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_force_sync_entity_qdrant_success(self, sync_engine):
        """Test force sync entity from QDrant."""
        entity_id = "test_entity"
        mapping = IDMapping(
            mapping_id="test_mapping",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            entity_name="test_doc",
        )

        sync_engine.id_mapping_manager.get_mapping_by_qdrant_id = AsyncMock(
            return_value=mapping
        )

        with patch.object(sync_engine, "_execute_sync_operation") as mock_execute:
            # Mock the async method properly
            async def mock_execute_operation(operation):
                operation.mark_completed(success=True)
                return None

            mock_execute.side_effect = mock_execute_operation

            result = await sync_engine.force_sync_entity(entity_id, DatabaseType.QDRANT)

        assert result is True  # Operation should succeed with our mock
        mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_sync_entity_no_mapping(self, sync_engine):
        """Test force sync entity with no mapping found."""
        entity_id = "test_entity"

        sync_engine.id_mapping_manager.get_mapping_by_qdrant_id = AsyncMock(
            return_value=None
        )

        result = await sync_engine.force_sync_entity(entity_id, DatabaseType.QDRANT)

        assert result is False

    @pytest.mark.asyncio
    async def test_force_sync_entity_exception(self, sync_engine):
        """Test force sync entity with exception."""
        entity_id = "test_entity"

        sync_engine.id_mapping_manager.get_mapping_by_qdrant_id.side_effect = Exception(
            "Test error"
        )

        result = await sync_engine.force_sync_entity(entity_id, DatabaseType.QDRANT)

        assert result is False

    def test_extract_neo4j_properties_from_qdrant_data(self, sync_engine):
        """Test extracting Neo4j properties from QDrant data."""
        qdrant_data = {
            "vector": [0.1, 0.2, 0.3],
            "payload": {
                "title": "Test Document",
                "content": "Test content",
                "author": "Test Author",
                "vector": "should_be_ignored",
                "embedding": "should_be_ignored",
            },
        }

        properties = sync_engine._extract_neo4j_properties_from_qdrant_data(qdrant_data)

        assert properties["title"] == "Test Document"
        assert properties["content"] == "Test content"
        assert properties["author"] == "Test Author"
        assert properties["has_vector"] is True
        assert properties["vector_dimension"] == 3
        assert "vector" not in properties
        assert "embedding" not in properties

    def test_extract_neo4j_properties_no_vector(self, sync_engine):
        """Test extracting Neo4j properties without vector."""
        qdrant_data = {"payload": {"title": "Test Document", "content": "Test content"}}

        properties = sync_engine._extract_neo4j_properties_from_qdrant_data(qdrant_data)

        assert properties["title"] == "Test Document"
        assert properties["content"] == "Test content"
        assert "has_vector" not in properties
        assert "vector_dimension" not in properties

    def test_extract_qdrant_data_from_neo4j_properties(self, sync_engine):
        """Test extracting QDrant data from Neo4j properties."""
        neo4j_data = {
            "id": "should_be_ignored",
            "elementId": "should_be_ignored",
            "labels": ["should_be_ignored"],
            "has_vector": "should_be_ignored",
            "vector_dimension": "should_be_ignored",
            "vector": [0.1, 0.2, 0.3],
            "title": "Test Document",
            "content": "Test content",
            "author": "Test Author",
        }

        qdrant_data = sync_engine._extract_qdrant_data_from_neo4j_properties(neo4j_data)

        assert qdrant_data["vector"] == [0.1, 0.2, 0.3]
        assert qdrant_data["payload"]["title"] == "Test Document"
        assert qdrant_data["payload"]["content"] == "Test content"
        assert qdrant_data["payload"]["author"] == "Test Author"
        assert "id" not in qdrant_data["payload"]
        assert "elementId" not in qdrant_data["payload"]
        assert "labels" not in qdrant_data["payload"]

    def test_extract_qdrant_data_with_embedding_field(self, sync_engine):
        """Test extracting QDrant data with embedding field."""
        neo4j_data = {"embedding": [0.4, 0.5, 0.6], "title": "Test Document"}

        qdrant_data = sync_engine._extract_qdrant_data_from_neo4j_properties(neo4j_data)

        assert qdrant_data["vector"] == [0.4, 0.5, 0.6]
        assert qdrant_data["payload"]["title"] == "Test Document"
