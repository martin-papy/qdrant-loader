"""Change Detection and Event System for Database Synchronization.

This module provides event-driven change detection for QDrant and Neo4j databases,
enabling real-time synchronization through a unified event system.
"""

import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

from neo4j import Session
from qdrant_client.http.models import PointStruct

from ...utils.logging import LoggingConfig
from ..managers import IDMappingManager, MappingType, Neo4jManager, QdrantManager
from ..types import EntityType

logger = LoggingConfig.get_logger(__name__)


class ChangeType(Enum):
    """Types of database changes."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BULK_CREATE = "bulk_create"
    BULK_UPDATE = "bulk_update"
    BULK_DELETE = "bulk_delete"


class DatabaseType(Enum):
    """Source database types."""

    QDRANT = "qdrant"
    NEO4J = "neo4j"
    GRAPHITI = "graphiti"


@dataclass
class ChangeEvent:
    """Container for database change events."""

    # Event identification
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Change information
    change_type: ChangeType = ChangeType.UPDATE
    database_type: DatabaseType = DatabaseType.QDRANT
    entity_type: EntityType = EntityType.CONCEPT
    mapping_type: MappingType = MappingType.DOCUMENT

    # Entity identification
    entity_id: Optional[str] = None  # Primary ID in source database
    entity_uuid: Optional[str] = None  # UUID for cross-database tracking
    entity_name: Optional[str] = None

    # Change data
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    affected_fields: Set[str] = field(default_factory=set)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_transaction_id: Optional[str] = None
    batch_id: Optional[str] = None  # For bulk operations

    # Processing status
    processed: bool = False
    processing_errors: List[str] = field(default_factory=list)
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary format."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "change_type": self.change_type.value,
            "database_type": self.database_type.value,
            "entity_type": self.entity_type.value,
            "mapping_type": self.mapping_type.value,
            "entity_id": self.entity_id,
            "entity_uuid": self.entity_uuid,
            "entity_name": self.entity_name,
            "old_data": self.old_data,
            "new_data": self.new_data,
            "affected_fields": list(self.affected_fields),
            "metadata": self.metadata,
            "source_transaction_id": self.source_transaction_id,
            "batch_id": self.batch_id,
            "processed": self.processed,
            "processing_errors": self.processing_errors,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChangeEvent":
        """Create ChangeEvent from dictionary."""
        event = cls(
            event_id=data["event_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            change_type=ChangeType(data["change_type"]),
            database_type=DatabaseType(data["database_type"]),
            entity_type=EntityType(data["entity_type"]),
            mapping_type=MappingType(data["mapping_type"]),
            entity_id=data.get("entity_id"),
            entity_uuid=data.get("entity_uuid"),
            entity_name=data.get("entity_name"),
            old_data=data.get("old_data"),
            new_data=data.get("new_data"),
            affected_fields=set(data.get("affected_fields", [])),
            metadata=data.get("metadata", {}),
            source_transaction_id=data.get("source_transaction_id"),
            batch_id=data.get("batch_id"),
            processed=data.get("processed", False),
            processing_errors=data.get("processing_errors", []),
            retry_count=data.get("retry_count", 0),
        )
        return event


class ChangeDetector(ABC):
    """Abstract base class for database change detectors."""

    @abstractmethod
    async def start_monitoring(self) -> None:
        """Start monitoring for changes."""
        pass

    @abstractmethod
    async def stop_monitoring(self) -> None:
        """Stop monitoring for changes."""
        pass

    @abstractmethod
    async def get_recent_changes(
        self, since: Optional[datetime] = None, limit: int = 1000
    ) -> List[ChangeEvent]:
        """Get recent changes since specified time."""
        pass


class QdrantChangeDetector(ChangeDetector):
    """Change detector for QDrant database."""

    def __init__(
        self,
        qdrant_manager: QdrantManager,
        polling_interval: int = 30,
        enable_polling: bool = True,
    ):
        """Initialize QDrant change detector.

        Args:
            qdrant_manager: QDrant manager instance
            polling_interval: Polling interval in seconds
            enable_polling: Whether to enable polling-based detection
        """
        self.qdrant_manager = qdrant_manager
        self.polling_interval = polling_interval
        self.enable_polling = enable_polling

        self._monitoring = False
        self._polling_task: Optional[asyncio.Task] = None
        self._last_poll_time: Optional[datetime] = None
        self._known_points: Set[str] = set()
        self._point_checksums: Dict[str, str] = {}

        # Event callbacks
        self._event_callbacks: List[Callable[[ChangeEvent], None]] = []

    def add_event_callback(self, callback: Callable[[ChangeEvent], None]) -> None:
        """Add callback for change events."""
        self._event_callbacks.append(callback)

    def remove_event_callback(self, callback: Callable[[ChangeEvent], None]) -> None:
        """Remove callback for change events."""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)

    async def start_monitoring(self) -> None:
        """Start monitoring QDrant for changes."""
        if self._monitoring:
            logger.warning("QDrant monitoring already started")
            return

        self._monitoring = True
        self._last_poll_time = datetime.now(UTC)

        # Initialize known points
        await self._initialize_known_points()

        if self.enable_polling:
            self._polling_task = asyncio.create_task(self._polling_loop())
            logger.info(
                f"Started QDrant change monitoring with {self.polling_interval}s polling"
            )
        else:
            logger.info("QDrant change monitoring started (polling disabled)")

    async def stop_monitoring(self) -> None:
        """Stop monitoring QDrant for changes."""
        self._monitoring = False

        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None

        logger.info("Stopped QDrant change monitoring")

    async def get_recent_changes(
        self, since: Optional[datetime] = None, limit: int = 1000
    ) -> List[ChangeEvent]:
        """Get recent changes by comparing current state with known state."""
        if since is None:
            since = self._last_poll_time or datetime.now(UTC)

        changes = []

        try:
            # Get current points
            client = self.qdrant_manager._ensure_client_connected()

            # Scroll through all points (QDrant doesn't have native change tracking)
            current_points = {}
            offset = None

            while len(current_points) < limit:
                scroll_result = client.scroll(
                    collection_name=self.qdrant_manager.collection_name,
                    limit=min(100, limit - len(current_points)),
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,  # Don't need vectors for change detection
                )

                if not scroll_result[0]:  # No more points
                    break

                for point in scroll_result[0]:
                    point_id = str(point.id)
                    current_points[point_id] = point

                offset = scroll_result[1]  # Next offset
                if offset is None:
                    break

            # Detect changes
            current_point_ids = set(current_points.keys())

            # Detect new points (CREATE)
            new_points = current_point_ids - self._known_points
            for point_id in new_points:
                point = current_points[point_id]
                event = self._create_change_event(
                    change_type=ChangeType.CREATE,
                    entity_id=point_id,
                    new_data=self._point_to_dict(point),
                )
                changes.append(event)

            # Detect deleted points (DELETE)
            deleted_points = self._known_points - current_point_ids
            for point_id in deleted_points:
                event = self._create_change_event(
                    change_type=ChangeType.DELETE,
                    entity_id=point_id,
                    old_data={"point_id": point_id},
                )
                changes.append(event)

            # Detect updated points (UPDATE)
            common_points = current_point_ids & self._known_points
            for point_id in common_points:
                point = current_points[point_id]
                current_checksum = self._calculate_point_checksum(point)
                old_checksum = self._point_checksums.get(point_id)

                if old_checksum and current_checksum != old_checksum:
                    event = self._create_change_event(
                        change_type=ChangeType.UPDATE,
                        entity_id=point_id,
                        new_data=self._point_to_dict(point),
                        old_data={"checksum": old_checksum},
                    )
                    changes.append(event)

            # Update known state
            self._known_points = current_point_ids
            self._point_checksums = {
                point_id: self._calculate_point_checksum(point)
                for point_id, point in current_points.items()
            }

        except Exception as e:
            logger.error(f"Error detecting QDrant changes: {e}")

        return changes[:limit]

    async def _initialize_known_points(self) -> None:
        """Initialize the set of known points."""
        try:
            client = self.qdrant_manager._ensure_client_connected()

            # Get all current points
            offset = None
            while True:
                scroll_result = client.scroll(
                    collection_name=self.qdrant_manager.collection_name,
                    limit=1000,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )

                if not scroll_result[0]:
                    break

                for point in scroll_result[0]:
                    point_id = str(point.id)
                    self._known_points.add(point_id)
                    self._point_checksums[point_id] = self._calculate_point_checksum(
                        point
                    )

                offset = scroll_result[1]
                if offset is None:
                    break

            logger.info(
                f"Initialized QDrant monitoring with {len(self._known_points)} known points"
            )

        except Exception as e:
            logger.error(f"Error initializing QDrant known points: {e}")

    async def _polling_loop(self) -> None:
        """Main polling loop for change detection."""
        while self._monitoring:
            try:
                # Get recent changes
                changes = await self.get_recent_changes()

                # Notify callbacks
                for change in changes:
                    for callback in self._event_callbacks:
                        try:
                            callback(change)
                        except Exception as e:
                            logger.error(f"Error in change event callback: {e}")

                self._last_poll_time = datetime.now(UTC)

                # Wait for next poll
                await asyncio.sleep(self.polling_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in QDrant polling loop: {e}")
                await asyncio.sleep(min(self.polling_interval, 60))  # Back off on error

    def _create_change_event(
        self,
        change_type: ChangeType,
        entity_id: str,
        new_data: Optional[Dict[str, Any]] = None,
        old_data: Optional[Dict[str, Any]] = None,
    ) -> ChangeEvent:
        """Create a change event for QDrant."""
        # Extract entity information from payload
        entity_name = None
        entity_type = EntityType.CONCEPT
        mapping_type = MappingType.DOCUMENT

        if new_data and "payload" in new_data:
            payload = new_data["payload"]
            entity_name = payload.get("entity_name") or payload.get("title")

            # Try to determine entity type from payload
            if "entity_type" in payload:
                try:
                    entity_type = EntityType(payload["entity_type"])
                except ValueError:
                    pass

            # Try to determine mapping type
            if "document_id" in payload:
                mapping_type = MappingType.DOCUMENT
            elif "entity_id" in payload:
                mapping_type = MappingType.ENTITY

        return ChangeEvent(
            change_type=change_type,
            database_type=DatabaseType.QDRANT,
            entity_type=entity_type,
            mapping_type=mapping_type,
            entity_id=entity_id,
            entity_name=entity_name,
            old_data=old_data,
            new_data=new_data,
            metadata={
                "collection_name": self.qdrant_manager.collection_name,
                "detection_method": "polling",
            },
        )

    def _point_to_dict(self, point) -> Dict[str, Any]:
        """Convert QDrant point to dictionary."""
        return {
            "point_id": str(point.id),
            "payload": point.payload or {},
            "vector_size": len(point.vector) if point.vector else 0,
        }

    def _calculate_point_checksum(self, point) -> str:
        """Calculate checksum for a QDrant point."""
        # Create a simple checksum based on payload
        payload_str = json.dumps(point.payload or {}, sort_keys=True)
        return str(hash(payload_str))


class Neo4jChangeDetector(ChangeDetector):
    """Change detector for Neo4j database."""

    def __init__(
        self,
        neo4j_manager: Neo4jManager,
        polling_interval: int = 30,
        enable_polling: bool = True,
        track_node_types: Optional[List[str]] = None,
    ):
        """Initialize Neo4j change detector.

        Args:
            neo4j_manager: Neo4j manager instance
            polling_interval: Polling interval in seconds
            enable_polling: Whether to enable polling-based detection
            track_node_types: Specific node types to track (None for all)
        """
        self.neo4j_manager = neo4j_manager
        self.polling_interval = polling_interval
        self.enable_polling = enable_polling
        self.track_node_types = track_node_types or []

        self._monitoring = False
        self._polling_task: Optional[asyncio.Task] = None
        self._last_poll_time: Optional[datetime] = None
        self._known_nodes: Dict[str, Dict[str, Any]] = {}

        # Event callbacks
        self._event_callbacks: List[Callable[[ChangeEvent], None]] = []

    def add_event_callback(self, callback: Callable[[ChangeEvent], None]) -> None:
        """Add callback for change events."""
        self._event_callbacks.append(callback)

    def remove_event_callback(self, callback: Callable[[ChangeEvent], None]) -> None:
        """Remove callback for change events."""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)

    async def start_monitoring(self) -> None:
        """Start monitoring Neo4j for changes."""
        if self._monitoring:
            logger.warning("Neo4j monitoring already started")
            return

        self._monitoring = True
        self._last_poll_time = datetime.now(UTC)

        # Initialize known nodes
        await self._initialize_known_nodes()

        if self.enable_polling:
            self._polling_task = asyncio.create_task(self._polling_loop())
            logger.info(
                f"Started Neo4j change monitoring with {self.polling_interval}s polling"
            )
        else:
            logger.info("Neo4j change monitoring started (polling disabled)")

    async def stop_monitoring(self) -> None:
        """Stop monitoring Neo4j for changes."""
        self._monitoring = False

        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None

        logger.info("Stopped Neo4j change monitoring")

    async def get_recent_changes(
        self, since: Optional[datetime] = None, limit: int = 1000
    ) -> List[ChangeEvent]:
        """Get recent changes by comparing current state with known state."""
        if since is None:
            since = self._last_poll_time or datetime.now(UTC)

        changes = []

        try:
            # Build query based on tracked node types
            if self.track_node_types:
                labels_filter = " OR ".join(
                    [f"n:{label}" for label in self.track_node_types]
                )
                query = f"""
                MATCH (n)
                WHERE {labels_filter}
                RETURN id(n) as node_id, labels(n) as labels, properties(n) as properties
                LIMIT $limit
                """
            else:
                query = """
                MATCH (n)
                WHERE NOT n:IDMapping  // Exclude our mapping nodes
                RETURN id(n) as node_id, labels(n) as labels, properties(n) as properties
                LIMIT $limit
                """

            results = self.neo4j_manager.execute_read_query(query, {"limit": limit})

            # Build current state
            current_nodes = {}
            for result in results:
                node_id = str(result["node_id"])
                node_data = {
                    "labels": result["labels"],
                    "properties": result["properties"],
                }
                current_nodes[node_id] = node_data

            current_node_ids = set(current_nodes.keys())
            known_node_ids = set(self._known_nodes.keys())

            # Detect new nodes (CREATE)
            new_nodes = current_node_ids - known_node_ids
            for node_id in new_nodes:
                node_data = current_nodes[node_id]
                event = self._create_change_event(
                    change_type=ChangeType.CREATE,
                    entity_id=node_id,
                    new_data=node_data,
                )
                changes.append(event)

            # Detect deleted nodes (DELETE)
            deleted_nodes = known_node_ids - current_node_ids
            for node_id in deleted_nodes:
                old_data = self._known_nodes[node_id]
                event = self._create_change_event(
                    change_type=ChangeType.DELETE,
                    entity_id=node_id,
                    old_data=old_data,
                )
                changes.append(event)

            # Detect updated nodes (UPDATE)
            common_nodes = current_node_ids & known_node_ids
            for node_id in common_nodes:
                current_data = current_nodes[node_id]
                old_data = self._known_nodes[node_id]

                if current_data != old_data:
                    # Find affected fields
                    affected_fields = set()
                    old_props = old_data.get("properties", {})
                    new_props = current_data.get("properties", {})

                    all_keys = set(old_props.keys()) | set(new_props.keys())
                    for key in all_keys:
                        if old_props.get(key) != new_props.get(key):
                            affected_fields.add(key)

                    event = self._create_change_event(
                        change_type=ChangeType.UPDATE,
                        entity_id=node_id,
                        new_data=current_data,
                        old_data=old_data,
                        affected_fields=affected_fields,
                    )
                    changes.append(event)

            # Update known state
            self._known_nodes = current_nodes

        except Exception as e:
            logger.error(f"Error detecting Neo4j changes: {e}")

        return changes[:limit]

    async def _initialize_known_nodes(self) -> None:
        """Initialize the set of known nodes."""
        try:
            # Get all current nodes (excluding our mapping nodes)
            if self.track_node_types:
                labels_filter = " OR ".join(
                    [f"n:{label}" for label in self.track_node_types]
                )
                query = f"""
                MATCH (n)
                WHERE {labels_filter}
                RETURN id(n) as node_id, labels(n) as labels, properties(n) as properties
                """
            else:
                query = """
                MATCH (n)
                WHERE NOT n:IDMapping
                RETURN id(n) as node_id, labels(n) as labels, properties(n) as properties
                """

            results = self.neo4j_manager.execute_read_query(query)

            for result in results:
                node_id = str(result["node_id"])
                node_data = {
                    "labels": result["labels"],
                    "properties": result["properties"],
                }
                self._known_nodes[node_id] = node_data

            logger.info(
                f"Initialized Neo4j monitoring with {len(self._known_nodes)} known nodes"
            )

        except Exception as e:
            logger.error(f"Error initializing Neo4j known nodes: {e}")

    async def _polling_loop(self) -> None:
        """Main polling loop for change detection."""
        while self._monitoring:
            try:
                # Get recent changes
                changes = await self.get_recent_changes()

                # Notify callbacks
                for change in changes:
                    for callback in self._event_callbacks:
                        try:
                            callback(change)
                        except Exception as e:
                            logger.error(f"Error in change event callback: {e}")

                self._last_poll_time = datetime.now(UTC)

                # Wait for next poll
                await asyncio.sleep(self.polling_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Neo4j polling loop: {e}")
                await asyncio.sleep(min(self.polling_interval, 60))  # Back off on error

    def _create_change_event(
        self,
        change_type: ChangeType,
        entity_id: str,
        new_data: Optional[Dict[str, Any]] = None,
        old_data: Optional[Dict[str, Any]] = None,
        affected_fields: Optional[Set[str]] = None,
    ) -> ChangeEvent:
        """Create a change event for Neo4j."""
        # Extract entity information
        entity_name = None
        entity_type = EntityType.CONCEPT
        mapping_type = MappingType.ENTITY
        entity_uuid = None

        # Try to extract from new data first, then old data
        data_to_check = new_data or old_data
        if data_to_check and "properties" in data_to_check:
            properties = data_to_check["properties"]
            entity_name = (
                properties.get("name")
                or properties.get("title")
                or properties.get("entity_name")
            )
            entity_uuid = properties.get("uuid")

            # Try to determine entity type from labels
            labels = data_to_check.get("labels", [])
            for label in labels:
                try:
                    entity_type = EntityType(label)
                    break
                except ValueError:
                    continue

            # Determine mapping type based on properties
            if "document_id" in properties:
                mapping_type = MappingType.DOCUMENT
            elif "episode_id" in properties:
                mapping_type = MappingType.EPISODE
            elif any(label in ["Entity", "Person", "Organization"] for label in labels):
                mapping_type = MappingType.ENTITY
            elif any(label in ["Relationship"] for label in labels):
                mapping_type = MappingType.RELATIONSHIP

        return ChangeEvent(
            change_type=change_type,
            database_type=DatabaseType.NEO4J,
            entity_type=entity_type,
            mapping_type=mapping_type,
            entity_id=entity_id,
            entity_uuid=entity_uuid,
            entity_name=entity_name,
            old_data=old_data,
            new_data=new_data,
            affected_fields=affected_fields or set(),
            metadata={
                "detection_method": "polling",
                "tracked_node_types": self.track_node_types,
            },
        )


class SyncEventSystem:
    """Unified event system for database synchronization."""

    def __init__(
        self,
        qdrant_manager: QdrantManager,
        neo4j_manager: Neo4jManager,
        id_mapping_manager: IDMappingManager,
        qdrant_polling_interval: int = 30,
        neo4j_polling_interval: int = 30,
        max_event_queue_size: int = 10000,
        enable_event_persistence: bool = True,
    ):
        """Initialize the sync event system.

        Args:
            qdrant_manager: QDrant manager instance
            neo4j_manager: Neo4j manager instance
            id_mapping_manager: ID mapping manager instance
            qdrant_polling_interval: QDrant polling interval in seconds
            neo4j_polling_interval: Neo4j polling interval in seconds
            max_event_queue_size: Maximum size of event queue
            enable_event_persistence: Whether to persist events to database
        """
        self.qdrant_manager = qdrant_manager
        self.neo4j_manager = neo4j_manager
        self.id_mapping_manager = id_mapping_manager
        self.max_event_queue_size = max_event_queue_size
        self.enable_event_persistence = enable_event_persistence

        # Initialize change detectors
        self.qdrant_detector = QdrantChangeDetector(
            qdrant_manager=qdrant_manager,
            polling_interval=qdrant_polling_interval,
        )

        self.neo4j_detector = Neo4jChangeDetector(
            neo4j_manager=neo4j_manager,
            polling_interval=neo4j_polling_interval,
        )

        # Event queue and processing
        self._event_queue: asyncio.Queue[ChangeEvent] = asyncio.Queue(
            maxsize=max_event_queue_size
        )
        self._event_handlers: Dict[str, List[Callable[[ChangeEvent], None]]] = {}
        self._processing_task: Optional[asyncio.Task] = None
        self._running = False

        # Statistics
        self._stats = {
            "events_processed": 0,
            "events_failed": 0,
            "events_queued": 0,
            "last_event_time": None,
        }

        # Setup event callbacks
        self.qdrant_detector.add_event_callback(self._on_change_event)
        self.neo4j_detector.add_event_callback(self._on_change_event)

        # Ensure event persistence table
        if self.enable_event_persistence:
            self._ensure_event_table()

    def _ensure_event_table(self) -> None:
        """Ensure the event persistence table exists in Neo4j."""
        try:
            create_event_query = """
            CREATE CONSTRAINT sync_event_unique IF NOT EXISTS
            FOR (e:SyncEvent) REQUIRE e.event_id IS UNIQUE
            """
            self.neo4j_manager.execute_write_query(create_event_query)

            # Create indexes
            indexes = [
                "CREATE INDEX idx_sync_event_timestamp IF NOT EXISTS FOR (e:SyncEvent) ON (e.timestamp)",
                "CREATE INDEX idx_sync_event_type IF NOT EXISTS FOR (e:SyncEvent) ON (e.change_type)",
                "CREATE INDEX idx_sync_event_database IF NOT EXISTS FOR (e:SyncEvent) ON (e.database_type)",
                "CREATE INDEX idx_sync_event_processed IF NOT EXISTS FOR (e:SyncEvent) ON (e.processed)",
            ]

            for index_query in indexes:
                self.neo4j_manager.execute_write_query(index_query)

            logger.info("Sync event table and indexes ensured in Neo4j")

        except Exception as e:
            logger.error(f"Failed to ensure sync event table: {e}")

    async def start(self) -> None:
        """Start the event system."""
        if self._running:
            logger.warning("Event system already running")
            return

        self._running = True

        # Start change detectors
        await self.qdrant_detector.start_monitoring()
        await self.neo4j_detector.start_monitoring()

        # Start event processing
        self._processing_task = asyncio.create_task(self._process_events())

        logger.info("Sync event system started")

    async def stop(self) -> None:
        """Stop the event system."""
        self._running = False

        # Stop change detectors
        await self.qdrant_detector.stop_monitoring()
        await self.neo4j_detector.stop_monitoring()

        # Stop event processing
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None

        logger.info("Sync event system stopped")

    def add_event_handler(
        self,
        event_type: str,
        handler: Callable[[ChangeEvent], None],
    ) -> None:
        """Add an event handler for specific event types.

        Args:
            event_type: Event type pattern (e.g., "qdrant.create", "neo4j.*", "*")
            handler: Handler function
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def remove_event_handler(
        self,
        event_type: str,
        handler: Callable[[ChangeEvent], None],
    ) -> None:
        """Remove an event handler."""
        if event_type in self._event_handlers:
            if handler in self._event_handlers[event_type]:
                self._event_handlers[event_type].remove(handler)

    async def publish_event(self, event: ChangeEvent) -> None:
        """Publish an event to the system."""
        try:
            await self._event_queue.put(event)
            self._stats["events_queued"] += 1
        except asyncio.QueueFull:
            logger.error("Event queue full, dropping event")
            self._stats["events_failed"] += 1

    def _on_change_event(self, event: ChangeEvent) -> None:
        """Handle change events from detectors."""
        # Use asyncio.create_task to avoid blocking the detector
        asyncio.create_task(self.publish_event(event))

    async def _process_events(self) -> None:
        """Main event processing loop."""
        while self._running:
            try:
                # Get event from queue with timeout
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)

                # Process the event
                await self._handle_event(event)

                # Update statistics
                self._stats["events_processed"] += 1
                self._stats["last_event_time"] = datetime.now(UTC)

            except asyncio.TimeoutError:
                # No events to process, continue
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                self._stats["events_failed"] += 1

    async def _handle_event(self, event: ChangeEvent) -> None:
        """Handle a single change event."""
        try:
            # Persist event if enabled
            if self.enable_event_persistence:
                await self._persist_event(event)

            # Find matching handlers
            event_type_key = f"{event.database_type.value}.{event.change_type.value}"

            handlers_to_call = []

            # Exact match
            if event_type_key in self._event_handlers:
                handlers_to_call.extend(self._event_handlers[event_type_key])

            # Database wildcard (e.g., "qdrant.*")
            db_wildcard = f"{event.database_type.value}.*"
            if db_wildcard in self._event_handlers:
                handlers_to_call.extend(self._event_handlers[db_wildcard])

            # Global wildcard
            if "*" in self._event_handlers:
                handlers_to_call.extend(self._event_handlers["*"])

            # Call handlers
            for handler in handlers_to_call:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")
                    event.processing_errors.append(str(e))

            # Mark as processed
            event.processed = True

        except Exception as e:
            logger.error(f"Error handling event {event.event_id}: {e}")
            event.processing_errors.append(str(e))
            event.retry_count += 1

    async def _persist_event(self, event: ChangeEvent) -> None:
        """Persist event to Neo4j."""
        try:
            query = """
            CREATE (e:SyncEvent)
            SET e += $properties
            """

            properties = event.to_dict()

            self.neo4j_manager.execute_write_query(query, {"properties": properties})

        except Exception as e:
            logger.error(f"Error persisting event {event.event_id}: {e}")

    async def get_event_statistics(self) -> Dict[str, Any]:
        """Get event system statistics."""
        stats = self._stats.copy()
        stats.update(
            {
                "queue_size": self._event_queue.qsize(),
                "max_queue_size": self.max_event_queue_size,
                "running": self._running,
                "handlers_registered": sum(
                    len(handlers) for handlers in self._event_handlers.values()
                ),
            }
        )
        return stats

    async def get_recent_events(
        self,
        limit: int = 100,
        event_type: Optional[str] = None,
        database_type: Optional[DatabaseType] = None,
    ) -> List[ChangeEvent]:
        """Get recent events from persistence store."""
        if not self.enable_event_persistence:
            return []

        try:
            query_parts = ["MATCH (e:SyncEvent)"]
            params: Dict[str, Any] = {"limit": limit}

            where_conditions = []
            if event_type:
                where_conditions.append("e.change_type = $event_type")
                params["event_type"] = event_type

            if database_type:
                where_conditions.append("e.database_type = $database_type")
                params["database_type"] = database_type.value

            if where_conditions:
                query_parts.append("WHERE " + " AND ".join(where_conditions))

            query_parts.extend(
                ["RETURN e", "ORDER BY e.timestamp DESC", "LIMIT $limit"]
            )

            query = " ".join(query_parts)
            results = self.neo4j_manager.execute_read_query(query, params)

            events = []
            for result in results:
                event_data = result["e"]
                event = ChangeEvent.from_dict(event_data)
                events.append(event)

            return events

        except Exception as e:
            logger.error(f"Error retrieving recent events: {e}")
            return []

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the event system."""
        try:
            qdrant_healthy = True
            neo4j_healthy = self.neo4j_manager.test_connection()

            try:
                self.qdrant_manager._ensure_client_connected()
            except Exception:
                qdrant_healthy = False

            stats = await self.get_event_statistics()

            return {
                "healthy": qdrant_healthy and neo4j_healthy and self._running,
                "qdrant_healthy": qdrant_healthy,
                "neo4j_healthy": neo4j_healthy,
                "running": self._running,
                "queue_size": stats["queue_size"],
                "events_processed": stats["events_processed"],
                "events_failed": stats["events_failed"],
                "last_event_time": stats["last_event_time"],
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "running": self._running,
            }
