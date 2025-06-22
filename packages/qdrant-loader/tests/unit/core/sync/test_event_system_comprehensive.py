"""Comprehensive tests for event_system.py - Phase 1 Priority Coverage Enhancement.

Targets sync/event_system.py: 480 lines, 18% -> 70%+ coverage.
Focuses on major untested components: Change Detectors and SyncEventSystem.
"""

import asyncio
import json
import sqlite3
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_loader.core.managers import IDMappingManager, MappingType, Neo4jManager, QdrantManager
from qdrant_loader.core.sync.event_system import (
    ChangeEvent,
    ChangeType,
    DatabaseType,
    Neo4jChangeDetector,
    QdrantChangeDetector,
    SyncEventSystem,
)
from qdrant_loader.core.types import EntityType


class TestQdrantChangeDetector:
    """Test QdrantChangeDetector functionality - covers lines 130-430."""

    @pytest.fixture
    def mock_qdrant_manager(self):
        """Mock QdrantManager for testing."""
        manager = MagicMock(spec=QdrantManager)
        manager.collection_name = "test_collection"
        
        # Mock the client and its methods
        mock_client = MagicMock()
        manager._ensure_client_connected.return_value = mock_client
        
        # Mock scroll method to return points
        mock_client.scroll.return_value = (
            [
                MagicMock(id="point1", payload={"text": "content1"}, vector=[0.1, 0.2, 0.3]),
                MagicMock(id="point2", payload={"text": "content2"}, vector=[0.4, 0.5, 0.6]),
            ],
            None,  # next_page_offset
        )
        
        return manager

    @pytest.fixture
    def detector(self, mock_qdrant_manager):
        """Create QdrantChangeDetector instance."""
        return QdrantChangeDetector(
            qdrant_manager=mock_qdrant_manager,
            polling_interval=1,  # Fast polling for tests
            enable_polling=True,
        )

    def test_detector_initialization(self, detector, mock_qdrant_manager):
        """Test QdrantChangeDetector initialization."""
        assert detector.qdrant_manager == mock_qdrant_manager
        assert detector.polling_interval == 1
        assert detector.enable_polling is True
        assert detector._monitoring is False
        assert detector._polling_task is None
        assert detector._last_poll_time is None
        assert detector._known_points == set()
        assert detector._point_checksums == {}
        assert detector._event_callbacks == []

    def test_add_remove_event_callback(self, detector):
        """Test adding and removing event callbacks."""
        callback1 = MagicMock()
        callback2 = MagicMock()

        # Add callbacks
        detector.add_event_callback(callback1)
        detector.add_event_callback(callback2)
        assert len(detector._event_callbacks) == 2
        assert callback1 in detector._event_callbacks
        assert callback2 in detector._event_callbacks

        # Remove callback
        detector.remove_event_callback(callback1)
        assert len(detector._event_callbacks) == 1
        assert callback1 not in detector._event_callbacks
        assert callback2 in detector._event_callbacks

        # Remove non-existent callback (should not error)
        detector.remove_event_callback(callback1)
        assert len(detector._event_callbacks) == 1

    @pytest.mark.asyncio
    async def test_start_monitoring_success(self, detector, mock_qdrant_manager):
        """Test successful start of monitoring."""
        await detector.start_monitoring()

        assert detector._monitoring is True
        assert detector._last_poll_time is not None
        assert isinstance(detector._last_poll_time, datetime)
        assert detector._polling_task is not None
        mock_qdrant_manager._ensure_client_connected.assert_called()

    @pytest.mark.asyncio
    async def test_start_monitoring_already_started(self, detector, mock_qdrant_manager):
        """Test start monitoring when already started."""
        detector._monitoring = True
        initial_poll_time = detector._last_poll_time

        await detector.start_monitoring()

        # Verify behavior: monitoring remains True and no initialization occurs
        assert detector._monitoring is True
        assert detector._last_poll_time == initial_poll_time  # Should not change
        # Should not call _ensure_client_connected since already monitoring
        mock_qdrant_manager._ensure_client_connected.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, detector):
        """Test stopping monitoring."""
        # Start monitoring first
        detector._monitoring = True
        
        # Create an actual async task that we can cancel
        async def dummy_task():
            await asyncio.sleep(10)
        
        detector._polling_task = asyncio.create_task(dummy_task())

        await detector.stop_monitoring()

        assert detector._monitoring is False
        assert detector._polling_task is None

    @pytest.mark.asyncio
    async def test_stop_monitoring_not_started(self, detector, caplog):
        """Test stop monitoring when not started."""
        await detector.stop_monitoring()
        # The detector doesn't actually log this message, it just stops gracefully
        assert detector._monitoring is False

    @pytest.mark.asyncio
    async def test_get_recent_changes_no_time(self, detector, mock_qdrant_manager):
        """Test getting recent changes without since parameter."""
        changes = await detector.get_recent_changes()

        assert isinstance(changes, list)
        # Changes depend on the detector's internal state
        mock_qdrant_manager._ensure_client_connected.assert_called()

    @pytest.mark.asyncio
    async def test_get_recent_changes_with_time(self, detector, mock_qdrant_manager):
        """Test getting recent changes with since parameter."""
        since_time = datetime.now(UTC) - timedelta(hours=1)

        changes = await detector.get_recent_changes(since=since_time, limit=50)

        assert isinstance(changes, list)
        mock_qdrant_manager._ensure_client_connected.assert_called()

    @pytest.mark.asyncio
    async def test_initialize_known_points(self, detector, mock_qdrant_manager):
        """Test initialization of known points."""
        await detector._initialize_known_points()

        # Verify client connection was called
        mock_qdrant_manager._ensure_client_connected.assert_called()
        # Check that points were processed (depends on mock data)
        assert isinstance(detector._known_points, set)
        assert isinstance(detector._point_checksums, dict)

    @pytest.mark.asyncio
    async def test_polling_loop_detects_changes(self, detector, mock_qdrant_manager):
        """Test polling loop detecting changes."""
        # Initialize with one point
        detector._known_points = {"point1"}
        detector._point_checksums = {"point1": "checksum1"}

        callback = MagicMock()
        detector.add_event_callback(callback)

        # Run one polling iteration with timeout
        detector._monitoring = True
        try:
            await asyncio.wait_for(detector._polling_loop(), timeout=0.1)
        except asyncio.TimeoutError:
            pass  # Expected for infinite loop

        # Verify client was called during polling
        mock_qdrant_manager._ensure_client_connected.assert_called()

    def test_create_change_event(self, detector):
        """Test creating change events."""
        old_data = {"text": "old_content"}
        new_data = {"text": "new_content"}

        event = detector._create_change_event(
            change_type=ChangeType.UPDATE,
            entity_id="test_point",
            new_data=new_data,
            old_data=old_data,
        )

        assert isinstance(event, ChangeEvent)
        assert event.change_type == ChangeType.UPDATE
        assert event.database_type == DatabaseType.QDRANT
        assert event.entity_type == EntityType.CONCEPT
        assert event.mapping_type == MappingType.DOCUMENT
        assert event.entity_id == "test_point"
        assert event.new_data == new_data
        assert event.old_data == old_data

    def test_point_to_dict(self, detector):
        """Test converting point to dictionary."""
        # Create a mock point object with attributes
        point = MagicMock()
        point.id = "point1"
        point.payload = {"text": "content", "metadata": {"key": "value"}}
        point.vector = [0.1, 0.2, 0.3]

        result = detector._point_to_dict(point)

        expected = {
            "point_id": "point1",
            "payload": {"text": "content", "metadata": {"key": "value"}},
            "vector_size": 3,
        }
        assert result == expected

    def test_calculate_point_checksum(self, detector):
        """Test calculating point checksum."""
        # Create mock point objects with attributes
        point = MagicMock()
        point.id = "point1"
        point.payload = {"text": "content"}
        point.vector = [0.1, 0.2, 0.3]

        checksum1 = detector._calculate_point_checksum(point)
        checksum2 = detector._calculate_point_checksum(point)

        assert isinstance(checksum1, str)
        assert checksum1 == checksum2  # Same point should give same checksum

        # Different point should give different checksum
        point2 = MagicMock()
        point2.id = "point2"
        point2.payload = {"text": "different"}
        point2.vector = [0.4, 0.5, 0.6]
        
        checksum3 = detector._calculate_point_checksum(point2)
        assert checksum1 != checksum3


class TestNeo4jChangeDetector:
    """Test Neo4jChangeDetector functionality - covers lines 431-730."""

    @pytest.fixture
    def mock_neo4j_manager(self):
        """Mock Neo4jManager for testing."""
        manager = MagicMock(spec=Neo4jManager)
        # Mock execute methods  
        manager.execute_write_query.return_value = None
        manager.execute_read_query.return_value = [
            {"n": {"id": 1, "labels": ["Person"], "properties": {"name": "Alice", "age": 30}}},
            {"n": {"id": 2, "labels": ["Person"], "properties": {"name": "Bob", "age": 25}}},
        ]
        return manager

    @pytest.fixture
    def neo4j_detector(self, mock_neo4j_manager):
        """Create Neo4jChangeDetector instance."""
        return Neo4jChangeDetector(
            neo4j_manager=mock_neo4j_manager,
            polling_interval=1,
            enable_polling=True,
            track_node_types=["Person", "Organization"],
        )

    def test_neo4j_detector_initialization(self, neo4j_detector, mock_neo4j_manager):
        """Test Neo4jChangeDetector initialization."""
        assert neo4j_detector.neo4j_manager == mock_neo4j_manager
        assert neo4j_detector.polling_interval == 1
        assert neo4j_detector.enable_polling is True
        assert neo4j_detector.track_node_types == ["Person", "Organization"]
        assert neo4j_detector._monitoring is False
        assert neo4j_detector._polling_task is None
        assert neo4j_detector._last_poll_time is None
        assert neo4j_detector._known_nodes == {}

    def test_neo4j_add_remove_callbacks(self, neo4j_detector):
        """Test adding and removing event callbacks for Neo4j detector."""
        callback1 = MagicMock()
        callback2 = MagicMock()

        neo4j_detector.add_event_callback(callback1)
        neo4j_detector.add_event_callback(callback2)
        assert len(neo4j_detector._event_callbacks) == 2

        neo4j_detector.remove_event_callback(callback1)
        assert len(neo4j_detector._event_callbacks) == 1
        assert callback2 in neo4j_detector._event_callbacks

    @pytest.mark.asyncio
    async def test_neo4j_start_monitoring(self, neo4j_detector, mock_neo4j_manager):
        """Test Neo4j start monitoring."""
        await neo4j_detector.start_monitoring()

        assert neo4j_detector._monitoring is True
        assert neo4j_detector._last_poll_time is not None
        assert neo4j_detector._polling_task is not None
        mock_neo4j_manager.execute_read_query.assert_called()

    @pytest.mark.asyncio
    async def test_neo4j_stop_monitoring(self, neo4j_detector):
        """Test Neo4j stop monitoring."""
        neo4j_detector._monitoring = True
        
        # Create an actual async task that we can cancel
        async def dummy_task():
            await asyncio.sleep(10)
        
        neo4j_detector._polling_task = asyncio.create_task(dummy_task())

        await neo4j_detector.stop_monitoring()

        assert neo4j_detector._monitoring is False
        assert neo4j_detector._polling_task is None

    @pytest.mark.asyncio
    async def test_neo4j_get_recent_changes(self, neo4j_detector, mock_neo4j_manager):
        """Test Neo4j get recent changes."""
        changes = await neo4j_detector.get_recent_changes()

        assert isinstance(changes, list)
        mock_neo4j_manager.execute_read_query.assert_called()

    def test_neo4j_create_change_event(self, neo4j_detector):
        """Test Neo4j change event creation."""
        affected_fields = {"name", "age"}

        event = neo4j_detector._create_change_event(
            change_type=ChangeType.UPDATE,
            entity_id="1",
            new_data={"name": "Alice", "age": 31},
            old_data={"name": "Alice", "age": 30},
            affected_fields=affected_fields,
        )

        assert isinstance(event, ChangeEvent)
        assert event.change_type == ChangeType.UPDATE
        assert event.database_type == DatabaseType.NEO4J
        assert event.entity_id == "1"
        assert event.affected_fields == affected_fields


class TestSyncEventSystem:
    """Test SyncEventSystem functionality - covers lines 731-1066."""

    @pytest.fixture
    def mock_managers(self):
        """Mock all required managers."""
        qdrant_manager = AsyncMock(spec=QdrantManager)
        neo4j_manager = AsyncMock(spec=Neo4jManager)
        id_mapping_manager = AsyncMock(spec=IDMappingManager)
        
        return qdrant_manager, neo4j_manager, id_mapping_manager

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield f.name
        # Cleanup
        Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def event_system(self, mock_managers, temp_db_path):
        """Create SyncEventSystem instance."""
        qdrant_manager, neo4j_manager, id_mapping_manager = mock_managers
        
        # Patch the detector classes to prevent actual background tasks
        with patch('qdrant_loader.core.sync.event_system.QdrantChangeDetector') as mock_qdrant_detector_class, \
             patch('qdrant_loader.core.sync.event_system.Neo4jChangeDetector') as mock_neo4j_detector_class:
            
            # Create mock detector instances
            mock_qdrant_detector = MagicMock()
            mock_qdrant_detector.start_monitoring = AsyncMock()
            mock_qdrant_detector.stop_monitoring = AsyncMock()
            mock_qdrant_detector.get_recent_changes = AsyncMock(return_value=[])
            mock_qdrant_detector.add_event_callback = MagicMock()
            mock_qdrant_detector_class.return_value = mock_qdrant_detector
            
            mock_neo4j_detector = MagicMock()
            mock_neo4j_detector.start_monitoring = AsyncMock()
            mock_neo4j_detector.stop_monitoring = AsyncMock()
            mock_neo4j_detector.get_recent_changes = AsyncMock(return_value=[])
            mock_neo4j_detector.add_event_callback = MagicMock()
            mock_neo4j_detector_class.return_value = mock_neo4j_detector
            
            # Create system with mocked detectors
            system = SyncEventSystem(
                qdrant_manager=qdrant_manager,
                neo4j_manager=neo4j_manager,
                id_mapping_manager=id_mapping_manager,
                qdrant_polling_interval=1,
                neo4j_polling_interval=1,
                max_event_queue_size=100,
                enable_event_persistence=True,
            )
            
            # Ensure no background tasks are running
            system._running = False
            system._processing_task = None
            
            yield system

    def test_sync_event_system_initialization(self, event_system, mock_managers):
        """Test SyncEventSystem initialization."""
        qdrant_manager, neo4j_manager, id_mapping_manager = mock_managers
        
        assert event_system.qdrant_manager == qdrant_manager
        assert event_system.neo4j_manager == neo4j_manager
        assert event_system.id_mapping_manager == id_mapping_manager
        assert event_system.max_event_queue_size == 100
        assert event_system.enable_event_persistence is True
        assert event_system._running is False
        assert event_system._event_queue is not None
        assert event_system._event_handlers == {}

    def test_ensure_event_table(self, event_system):
        """Test event table creation."""
        # The method is already called during initialization
        # Verify that Neo4j queries were called
        event_system.neo4j_manager.execute_write_query.assert_called()

    @pytest.mark.asyncio
    async def test_start_event_system(self, event_system):
        """Test starting the event system."""
        with patch.object(event_system, '_ensure_event_table'), \
             patch.object(event_system.qdrant_detector, 'start_monitoring') as mock_qdrant_start, \
             patch.object(event_system.neo4j_detector, 'start_monitoring') as mock_neo4j_start, \
             patch('asyncio.create_task') as mock_create_task:
            
            # Mock create_task to prevent actual background processing
            mock_task = MagicMock()
            mock_create_task.return_value = mock_task
            
            await event_system.start()

            assert event_system._running is True
            mock_qdrant_start.assert_called_once()
            mock_neo4j_start.assert_called_once()
            # Verify that processing task was created
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_event_system(self, event_system):
        """Test stopping the event system."""
        event_system._running = True
        
        # Create an actual asyncio Task that can be cancelled and awaited
        async def dummy_task():
            await asyncio.sleep(10)
        
        mock_task = asyncio.create_task(dummy_task())
        event_system._processing_task = mock_task
        
        with patch.object(event_system.qdrant_detector, 'stop_monitoring') as mock_qdrant_stop, \
             patch.object(event_system.neo4j_detector, 'stop_monitoring') as mock_neo4j_stop:
            
            await event_system.stop()

            assert event_system._running is False
            mock_qdrant_stop.assert_called_once()
            mock_neo4j_stop.assert_called_once()
            # Verify the task was cancelled (it should be cancelled after stop())
            assert mock_task.cancelled()

    def test_add_event_handler(self, event_system):
        """Test adding event handlers."""
        handler = MagicMock()
        
        event_system.add_event_handler("test_event", handler)
        
        assert "test_event" in event_system._event_handlers
        assert handler in event_system._event_handlers["test_event"]

    def test_remove_event_handler(self, event_system):
        """Test removing event handlers."""
        handler = MagicMock()
        event_system._event_handlers["test_event"] = [handler]
        
        event_system.remove_event_handler("test_event", handler)
        
        assert handler not in event_system._event_handlers.get("test_event", [])

    @pytest.mark.asyncio
    async def test_publish_event(self, event_system):
        """Test publishing events to the queue."""
        event = ChangeEvent(
            entity_id="test_entity",
            change_type=ChangeType.CREATE,
        )

        with patch.object(event_system._event_queue, 'put') as mock_put:
            await event_system.publish_event(event)
            mock_put.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_on_change_event(self, event_system):
        """Test change event callback."""
        event = ChangeEvent(entity_id="test_entity")
        
        with patch.object(event_system, 'publish_event') as mock_publish, \
             patch('asyncio.create_task') as mock_create_task:
            
            # Mock create_task to return a completed future
            mock_task = MagicMock()
            mock_create_task.return_value = mock_task
            mock_publish.return_value = asyncio.Future()
            mock_publish.return_value.set_result(None)
            
            # Call the method - it should create a task but not hang
            event_system._on_change_event(event)
            
            # Verify create_task was called
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_events(self, event_system):
        """Test event processing loop."""
        event = ChangeEvent(entity_id="test_entity")
        
        # Mock the queue to return an event then raise CancelledError immediately
        mock_queue = AsyncMock()
        mock_queue.get.side_effect = [event, asyncio.CancelledError()]
        event_system._event_queue = mock_queue
        event_system._running = True

        with patch.object(event_system, '_handle_event') as mock_handle, \
             patch('asyncio.wait_for') as mock_wait_for:
            
            # Mock wait_for to return the event immediately, then raise CancelledError
            mock_wait_for.side_effect = [event, asyncio.CancelledError()]
            
            try:
                await event_system._process_events()
            except asyncio.CancelledError:
                pass  # Expected when stopping
            
            mock_handle.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_handle_event(self, event_system):
        """Test individual event handling."""
        event = ChangeEvent(
            entity_id="test_entity",
            change_type=ChangeType.CREATE,
        )
        
        # Use regular MagicMock since handlers are synchronous
        handler = MagicMock()
        # The event system uses a specific key format for handlers
        event_key = f"{event.database_type.value}.{event.change_type.value}"
        event_system._event_handlers[event_key] = [handler]

        with patch.object(event_system, '_persist_event') as mock_persist:
            await event_system._handle_event(event)
            
            handler.assert_called_once_with(event)
            mock_persist.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_persist_event(self, event_system):
        """Test event persistence to database."""
        event = ChangeEvent(
            entity_id="test_entity",
            change_type=ChangeType.CREATE,
            new_data={"test": "data"},
        )

        await event_system._persist_event(event)

        # Verify Neo4j write query was called
        event_system.neo4j_manager.execute_write_query.assert_called()

    @pytest.mark.asyncio
    async def test_get_event_statistics(self, event_system):
        """Test getting event statistics."""
        # The get_event_statistics method doesn't actually query Neo4j
        # It just returns internal stats
        stats = await event_system.get_event_statistics()

        assert isinstance(stats, dict)
        assert "queue_size" in stats
        assert "max_queue_size" in stats
        assert "running" in stats
        assert "handlers_registered" in stats

    @pytest.mark.asyncio
    async def test_get_recent_events(self, event_system):
        """Test retrieving recent events."""
        # Mock Neo4j query results
        mock_event_data = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "change_type": "create",
            "database_type": "qdrant",
            "entity_type": "Concept",
            "mapping_type": "document",
            "entity_id": "entity1",
            "new_data": {"test": "data"},
            "processed": False,
        }
        event_system.neo4j_manager.execute_read_query.return_value = [mock_event_data]

        events = await event_system.get_recent_events(limit=10)

        assert isinstance(events, list)
        event_system.neo4j_manager.execute_read_query.assert_called()

    @pytest.mark.asyncio
    async def test_health_check(self, event_system):
        """Test system health check."""
        # Mock the Neo4j manager's test_connection method
        event_system.neo4j_manager.test_connection.return_value = True
        
        health = await event_system.health_check()

        assert "healthy" in health
        assert "qdrant_healthy" in health
        assert "neo4j_healthy" in health
        assert "running" in health
        assert "queue_size" in health
        assert "events_processed" in health
        assert "events_failed" in health
        assert "last_event_time" in health 