"""Bi-directional Synchronization Engine for QDrant and Neo4j.

This module provides the core synchronization service that processes change events
and propagates updates between QDrant vector database and Neo4j graph database,
ensuring data consistency with transaction management and batch processing.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from qdrant_client.http.models import PointStruct

from qdrant_loader.core.sync.event_system import (
    ChangeEvent,
    ChangeType,
    DatabaseType,
    SyncEventSystem,
)

from ...utils.logging import LoggingConfig
from ..managers import (
    IDMapping,
    IDMappingManager,
    MappingStatus,
    Neo4jManager,
    QdrantManager,
)

logger = LoggingConfig.get_logger(__name__)


class SyncDirection(Enum):
    """Direction of synchronization."""

    QDRANT_TO_NEO4J = "qdrant_to_neo4j"
    NEO4J_TO_QDRANT = "neo4j_to_qdrant"
    BIDIRECTIONAL = "bidirectional"


class SyncStrategy(Enum):
    """Synchronization strategy."""

    IMMEDIATE = "immediate"  # Process events immediately
    BATCH = "batch"  # Process events in batches
    SCHEDULED = "scheduled"  # Process events on schedule


@dataclass
class SyncOperation:
    """Container for synchronization operations."""

    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event: ChangeEvent = field(default_factory=ChangeEvent)
    direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    mapping: IDMapping | None = None

    # Operation status
    started_at: datetime | None = None
    completed_at: datetime | None = None
    success: bool = False
    error_message: str | None = None
    retry_count: int = 0

    # Transaction tracking
    transaction_id: str | None = None
    rollback_data: dict[str, Any] | None = None

    def mark_started(self) -> None:
        """Mark operation as started."""
        self.started_at = datetime.now(UTC)

    def mark_completed(self, success: bool = True, error: str | None = None) -> None:
        """Mark operation as completed."""
        self.completed_at = datetime.now(UTC)
        self.success = success
        if error:
            self.error_message = error

    def duration_ms(self) -> float | None:
        """Get operation duration in milliseconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return None


@dataclass
class SyncBatch:
    """Container for batch synchronization operations."""

    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operations: list[SyncOperation] = field(default_factory=list)
    direction: SyncDirection = SyncDirection.BIDIRECTIONAL

    # Batch status
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Results
    successful_operations: int = 0
    failed_operations: int = 0
    total_operations: int = 0

    def add_operation(self, operation: SyncOperation) -> None:
        """Add operation to batch."""
        self.operations.append(operation)
        self.total_operations = len(self.operations)

    def mark_started(self) -> None:
        """Mark batch as started."""
        self.started_at = datetime.now(UTC)

    def mark_completed(self) -> None:
        """Mark batch as completed and calculate results."""
        self.completed_at = datetime.now(UTC)
        self.successful_operations = sum(1 for op in self.operations if op.success)
        self.failed_operations = sum(1 for op in self.operations if not op.success)

    def success_rate(self) -> float:
        """Get batch success rate."""
        if self.total_operations == 0:
            return 0.0
        return self.successful_operations / self.total_operations


class BidirectionalSyncEngine:
    """Core synchronization engine for QDrant and Neo4j databases."""

    def __init__(
        self,
        qdrant_manager: QdrantManager,
        neo4j_manager: Neo4jManager,
        id_mapping_manager: IDMappingManager,
        sync_event_system: SyncEventSystem,
        sync_strategy: SyncStrategy = SyncStrategy.IMMEDIATE,
        batch_size: int = 100,
        batch_timeout_seconds: int = 30,
        max_retry_attempts: int = 3,
        enable_transaction_rollback: bool = True,
    ):
        """Initialize the bidirectional sync engine.

        Args:
            qdrant_manager: QDrant manager instance
            neo4j_manager: Neo4j manager instance
            id_mapping_manager: ID mapping manager instance
            sync_event_system: Sync event system instance
            sync_strategy: Synchronization strategy
            batch_size: Maximum batch size for batch processing
            batch_timeout_seconds: Timeout for batch processing
            max_retry_attempts: Maximum retry attempts for failed operations
            enable_transaction_rollback: Whether to enable transaction rollback
        """
        self.qdrant_manager = qdrant_manager
        self.neo4j_manager = neo4j_manager
        self.id_mapping_manager = id_mapping_manager
        self.sync_event_system = sync_event_system
        self.sync_strategy = sync_strategy
        self.batch_size = batch_size
        self.batch_timeout_seconds = batch_timeout_seconds
        self.max_retry_attempts = max_retry_attempts
        self.enable_transaction_rollback = enable_transaction_rollback

        # Engine state
        self._running = False
        self._sync_task: asyncio.Task | None = None
        self._pending_operations: list[SyncOperation] = []
        self._current_batch: SyncBatch | None = None
        self._batch_timer: asyncio.Task | None = None

        # Statistics
        self._total_operations = 0
        self._successful_operations = 0
        self._failed_operations = 0
        self._total_batches = 0

        # Register event handlers
        self._register_event_handlers()

    def _register_event_handlers(self) -> None:
        """Register event handlers with the sync event system."""
        # Handle all change events
        self.sync_event_system.add_event_handler("*", self._on_change_event)

    def _on_change_event(self, event: ChangeEvent) -> None:
        """Handle incoming change events."""
        if not self._running:
            logger.debug(f"Sync engine not running, ignoring event {event.event_id}")
            return

        # Create sync operation
        operation = SyncOperation(event=event)

        # Determine sync direction based on source database
        if event.database_type == DatabaseType.QDRANT:
            operation.direction = SyncDirection.QDRANT_TO_NEO4J
        elif event.database_type == DatabaseType.NEO4J:
            operation.direction = SyncDirection.NEO4J_TO_QDRANT
        else:
            logger.warning(f"Unknown database type: {event.database_type}")
            return

        # Process based on strategy
        if self.sync_strategy == SyncStrategy.IMMEDIATE:
            asyncio.create_task(self._process_operation_immediate(operation))
        else:
            self._add_to_batch(operation)

    async def start(self) -> None:
        """Start the synchronization engine."""
        if self._running:
            logger.warning("Sync engine already running")
            return

        self._running = True
        logger.info("Starting bidirectional sync engine")

        # Start batch processing if needed
        if self.sync_strategy in [SyncStrategy.BATCH, SyncStrategy.SCHEDULED]:
            self._sync_task = asyncio.create_task(self._batch_processing_loop())

    async def stop(self) -> None:
        """Stop the synchronization engine."""
        if not self._running:
            return

        self._running = False
        logger.info("Stopping bidirectional sync engine")

        # Cancel running tasks
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        if self._batch_timer:
            self._batch_timer.cancel()

        # Process any remaining operations
        if self._pending_operations:
            await self._process_pending_operations()

    async def _process_operation_immediate(self, operation: SyncOperation) -> None:
        """Process a single operation immediately."""
        try:
            operation.mark_started()
            await self._execute_sync_operation(operation)
            self._total_operations += 1
            if operation.success:
                self._successful_operations += 1
            else:
                self._failed_operations += 1
        except Exception as e:
            logger.error(
                f"Error processing immediate operation {operation.operation_id}: {e}"
            )
            operation.mark_completed(success=False, error=str(e))

    def _add_to_batch(self, operation: SyncOperation) -> None:
        """Add operation to current batch."""
        self._pending_operations.append(operation)

        # Check if batch is full
        if len(self._pending_operations) >= self.batch_size:
            asyncio.create_task(self._process_pending_operations())

    async def _batch_processing_loop(self) -> None:
        """Main batch processing loop."""
        while self._running:
            try:
                # Wait for batch timeout or until stopped
                await asyncio.sleep(self.batch_timeout_seconds)

                if self._pending_operations:
                    await self._process_pending_operations()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch processing loop: {e}")
                await asyncio.sleep(1)  # Brief pause before retrying

    async def _process_pending_operations(self) -> None:
        """Process all pending operations as a batch."""
        if not self._pending_operations:
            return

        # Create batch
        batch = SyncBatch()
        batch.operations = self._pending_operations.copy()
        batch.total_operations = len(batch.operations)
        self._pending_operations.clear()

        # Process batch
        await self._process_batch(batch)

    async def _process_batch(self, batch: SyncBatch) -> None:
        """Process a batch of sync operations."""
        batch.mark_started()
        logger.info(
            f"Processing batch {batch.batch_id} with {batch.total_operations} operations"
        )

        # Group operations by direction for efficient processing
        qdrant_to_neo4j_ops = [
            op
            for op in batch.operations
            if op.direction == SyncDirection.QDRANT_TO_NEO4J
        ]
        neo4j_to_qdrant_ops = [
            op
            for op in batch.operations
            if op.direction == SyncDirection.NEO4J_TO_QDRANT
        ]

        # Process each direction
        if qdrant_to_neo4j_ops:
            await self._process_qdrant_to_neo4j_batch(qdrant_to_neo4j_ops)

        if neo4j_to_qdrant_ops:
            await self._process_neo4j_to_qdrant_batch(neo4j_to_qdrant_ops)

        batch.mark_completed()
        self._total_batches += 1
        self._total_operations += batch.total_operations
        self._successful_operations += batch.successful_operations
        self._failed_operations += batch.failed_operations

        logger.info(
            f"Completed batch {batch.batch_id}: "
            f"{batch.successful_operations}/{batch.total_operations} successful "
            f"({batch.success_rate():.1%} success rate)"
        )

    async def _process_qdrant_to_neo4j_batch(
        self, operations: list[SyncOperation]
    ) -> None:
        """Process a batch of QDrant-to-Neo4j operations."""
        for operation in operations:
            try:
                operation.mark_started()
                await self._sync_qdrant_to_neo4j(operation)
            except Exception as e:
                logger.error(
                    f"Error syncing QDrant to Neo4j for operation {operation.operation_id}: {e}"
                )
                operation.mark_completed(success=False, error=str(e))

    async def _process_neo4j_to_qdrant_batch(
        self, operations: list[SyncOperation]
    ) -> None:
        """Process a batch of Neo4j-to-QDrant operations."""
        for operation in operations:
            try:
                operation.mark_started()
                await self._sync_neo4j_to_qdrant(operation)
            except Exception as e:
                logger.error(
                    f"Error syncing Neo4j to QDrant for operation {operation.operation_id}: {e}"
                )
                operation.mark_completed(success=False, error=str(e))

    async def _execute_sync_operation(self, operation: SyncOperation) -> None:
        """Execute a single sync operation."""
        # Get or create mapping
        await self._resolve_mapping(operation)

        # Execute based on direction
        if operation.direction == SyncDirection.QDRANT_TO_NEO4J:
            await self._sync_qdrant_to_neo4j(operation)
        elif operation.direction == SyncDirection.NEO4J_TO_QDRANT:
            await self._sync_neo4j_to_qdrant(operation)
        else:
            raise ValueError(f"Unsupported sync direction: {operation.direction}")

    async def _resolve_mapping(self, operation: SyncOperation) -> None:
        """Resolve ID mapping for the operation."""
        event = operation.event

        # Try to find existing mapping
        if event.database_type == DatabaseType.QDRANT and event.entity_id:
            operation.mapping = await self.id_mapping_manager.get_mapping_by_qdrant_id(
                event.entity_id
            )
        elif event.database_type == DatabaseType.NEO4J and event.entity_id:
            operation.mapping = await self.id_mapping_manager.get_mapping_by_neo4j_id(
                event.entity_id
            )
        elif event.entity_uuid:
            operation.mapping = await self.id_mapping_manager.get_mapping_by_neo4j_uuid(
                event.entity_uuid
            )

        # Create mapping if needed for CREATE operations
        if not operation.mapping and event.change_type == ChangeType.CREATE:
            operation.mapping = await self._create_mapping_for_event(event)

    async def _create_mapping_for_event(self, event: ChangeEvent) -> IDMapping:
        """Create a new mapping for a change event."""
        mapping_kwargs = {
            "entity_type": event.entity_type,
            "mapping_type": event.mapping_type,
            "entity_name": event.entity_name,
            "metadata": event.metadata,
        }

        if event.database_type == DatabaseType.QDRANT:
            mapping_kwargs["qdrant_point_id"] = event.entity_id
        elif event.database_type == DatabaseType.NEO4J:
            mapping_kwargs["neo4j_node_id"] = event.entity_id
            if event.entity_uuid:
                mapping_kwargs["neo4j_node_uuid"] = event.entity_uuid

        return await self.id_mapping_manager.create_mapping(**mapping_kwargs)

    async def _sync_qdrant_to_neo4j(self, operation: SyncOperation) -> None:
        """Sync changes from QDrant to Neo4j."""
        event = operation.event
        mapping = operation.mapping

        if not mapping:
            operation.mark_completed(
                success=False, error="No mapping found for QDrant entity"
            )
            return

        try:
            if event.change_type == ChangeType.CREATE:
                await self._create_neo4j_node_from_qdrant(operation)
            elif event.change_type == ChangeType.UPDATE:
                await self._update_neo4j_node_from_qdrant(operation)
            elif event.change_type == ChangeType.DELETE:
                await self._delete_neo4j_node_from_qdrant(operation)
            else:
                raise ValueError(f"Unsupported change type: {event.change_type}")

            operation.mark_completed(success=True)

        except Exception as e:
            logger.error(f"Error syncing QDrant to Neo4j: {e}")
            operation.mark_completed(success=False, error=str(e))

            # Mark mapping as sync failed
            if mapping:
                mapping.mark_sync_failed(str(e))
                await self.id_mapping_manager.update_mapping(
                    mapping.mapping_id,
                    {
                        "status": mapping.status.value,
                        "sync_errors": mapping.sync_errors,
                    },
                )

    async def _sync_neo4j_to_qdrant(self, operation: SyncOperation) -> None:
        """Sync changes from Neo4j to QDrant."""
        event = operation.event
        mapping = operation.mapping

        if not mapping:
            operation.mark_completed(
                success=False, error="No mapping found for Neo4j entity"
            )
            return

        try:
            if event.change_type == ChangeType.CREATE:
                await self._create_qdrant_point_from_neo4j(operation)
            elif event.change_type == ChangeType.UPDATE:
                await self._update_qdrant_point_from_neo4j(operation)
            elif event.change_type == ChangeType.DELETE:
                await self._delete_qdrant_point_from_neo4j(operation)
            else:
                raise ValueError(f"Unsupported change type: {event.change_type}")

            operation.mark_completed(success=True)

        except Exception as e:
            logger.error(f"Error syncing Neo4j to QDrant: {e}")
            operation.mark_completed(success=False, error=str(e))

            # Mark mapping as sync failed
            if mapping:
                mapping.mark_sync_failed(str(e))
                await self.id_mapping_manager.update_mapping(
                    mapping.mapping_id,
                    {
                        "status": mapping.status.value,
                        "sync_errors": mapping.sync_errors,
                    },
                )

    async def _create_neo4j_node_from_qdrant(self, operation: SyncOperation) -> None:
        """Create Neo4j node from QDrant point data."""
        event = operation.event
        mapping = operation.mapping

        if not event.new_data or not mapping:
            raise ValueError("Missing data or mapping for Neo4j node creation")

        # Extract node properties from QDrant point data
        node_properties = self._extract_neo4j_properties_from_qdrant_data(
            event.new_data
        )

        # Add mapping metadata
        node_properties.update(
            {
                "entity_type": event.entity_type.value,
                "entity_name": event.entity_name,
                "qdrant_point_id": mapping.qdrant_point_id,
                "created_at": datetime.now(UTC).isoformat(),
                "last_synced": datetime.now(UTC).isoformat(),
            }
        )

        # Create node in Neo4j
        create_query = f"""
        CREATE (n:{event.entity_type.value} $properties)
        RETURN id(n) as node_id, n.uuid as node_uuid
        """

        result = self.neo4j_manager.execute_write_query(
            create_query, parameters=node_properties
        )

        if result:
            record = result[0]
            # Update mapping with Neo4j node ID
            await self.id_mapping_manager.update_mapping(
                mapping.mapping_id,
                {
                    "neo4j_node_id": str(record["node_id"]),
                    "neo4j_node_uuid": record.get("node_uuid"),
                    "status": MappingStatus.ACTIVE.value,
                },
            )

    async def _update_neo4j_node_from_qdrant(self, operation: SyncOperation) -> None:
        """Update Neo4j node from QDrant point data."""
        event = operation.event
        mapping = operation.mapping

        if not event.new_data or not mapping or not mapping.neo4j_node_id:
            raise ValueError("Missing data, mapping, or Neo4j node ID for update")

        # Extract updated properties
        updated_properties = self._extract_neo4j_properties_from_qdrant_data(
            event.new_data
        )
        updated_properties["last_synced"] = datetime.now(UTC).isoformat()

        # Update node in Neo4j
        update_query = """
        MATCH (n) WHERE id(n) = $node_id
        SET n += $properties
        RETURN n
        """

        self.neo4j_manager.execute_write_query(
            update_query,
            parameters={
                "node_id": int(mapping.neo4j_node_id),
                "properties": updated_properties,
            },
        )

    async def _delete_neo4j_node_from_qdrant(self, operation: SyncOperation) -> None:
        """Delete Neo4j node when QDrant point is deleted."""
        mapping = operation.mapping

        if not mapping or not mapping.neo4j_node_id:
            raise ValueError("Missing mapping or Neo4j node ID for deletion")

        # Delete node and its relationships
        delete_query = """
        MATCH (n) WHERE id(n) = $node_id
        DETACH DELETE n
        """

        self.neo4j_manager.execute_write_query(
            delete_query, parameters={"node_id": int(mapping.neo4j_node_id)}
        )

        # Mark mapping as inactive
        await self.id_mapping_manager.update_mapping(
            mapping.mapping_id, {"status": MappingStatus.INACTIVE.value}
        )

    async def _create_qdrant_point_from_neo4j(self, operation: SyncOperation) -> None:
        """Create QDrant point from Neo4j node data."""
        event = operation.event
        mapping = operation.mapping

        if not event.new_data or not mapping:
            raise ValueError("Missing data or mapping for QDrant point creation")

        # Extract vector and payload from Neo4j node data
        vector_data = self._extract_qdrant_data_from_neo4j_properties(event.new_data)

        if not vector_data.get("vector"):
            raise ValueError(
                "No vector data found in Neo4j node for QDrant point creation"
            )

        # Create point in QDrant
        point_id = mapping.qdrant_point_id or str(uuid.uuid4())
        point = PointStruct(
            id=point_id,
            vector=vector_data["vector"],
            payload=vector_data.get("payload", {}),
        )

        await self.qdrant_manager.upsert_points([point])

        # Update mapping with QDrant point ID
        await self.id_mapping_manager.update_mapping(
            mapping.mapping_id,
            {
                "qdrant_point_id": point_id,
                "status": MappingStatus.ACTIVE.value,
            },
        )

    async def _update_qdrant_point_from_neo4j(self, operation: SyncOperation) -> None:
        """Update QDrant point from Neo4j node data."""
        event = operation.event
        mapping = operation.mapping

        if not event.new_data or not mapping or not mapping.qdrant_point_id:
            raise ValueError("Missing data, mapping, or QDrant point ID for update")

        # Extract updated vector and payload
        vector_data = self._extract_qdrant_data_from_neo4j_properties(event.new_data)

        # Update point in QDrant
        if vector_data.get("vector"):
            point = PointStruct(
                id=mapping.qdrant_point_id,
                vector=vector_data["vector"],
                payload=vector_data.get("payload", {}),
            )
            await self.qdrant_manager.upsert_points([point])
        elif vector_data.get("payload"):
            # Update only payload if no vector
            await self.qdrant_manager.set_payload(
                mapping.qdrant_point_id, vector_data["payload"]
            )

    async def _delete_qdrant_point_from_neo4j(self, operation: SyncOperation) -> None:
        """Delete QDrant point when Neo4j node is deleted."""
        mapping = operation.mapping

        if not mapping or not mapping.qdrant_point_id:
            raise ValueError("Missing mapping or QDrant point ID for deletion")

        # Delete point from QDrant
        await self.qdrant_manager.delete_points([mapping.qdrant_point_id])

        # Mark mapping as inactive
        await self.id_mapping_manager.update_mapping(
            mapping.mapping_id, {"status": MappingStatus.INACTIVE.value}
        )

    def _extract_neo4j_properties_from_qdrant_data(
        self, qdrant_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract Neo4j node properties from QDrant point data."""
        properties = {}

        # Extract payload data
        if "payload" in qdrant_data:
            payload = qdrant_data["payload"]
            for key, value in payload.items():
                # Skip vector-specific fields
                if key not in ["vector", "embedding"]:
                    properties[key] = value

        # Add vector metadata if available
        if "vector" in qdrant_data:
            properties["has_vector"] = True
            properties["vector_dimension"] = len(qdrant_data["vector"])

        return properties

    def _extract_qdrant_data_from_neo4j_properties(
        self, neo4j_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract QDrant point data from Neo4j node properties."""
        qdrant_data = {}
        payload = {}

        for key, value in neo4j_data.items():
            # Extract vector if present
            if key in ["vector", "embedding"] and isinstance(value, list):
                qdrant_data["vector"] = value
            # Skip internal Neo4j fields
            elif key not in [
                "id",
                "elementId",
                "labels",
                "has_vector",
                "vector_dimension",
            ]:
                payload[key] = value

        if payload:
            qdrant_data["payload"] = payload

        return qdrant_data

    async def get_sync_statistics(self) -> dict[str, Any]:
        """Get synchronization statistics."""
        return {
            "total_operations": self._total_operations,
            "successful_operations": self._successful_operations,
            "failed_operations": self._failed_operations,
            "success_rate": (
                self._successful_operations / self._total_operations
                if self._total_operations > 0
                else 0.0
            ),
            "total_batches": self._total_batches,
            "pending_operations": len(self._pending_operations),
            "sync_strategy": self.sync_strategy.value,
            "batch_size": self.batch_size,
            "is_running": self._running,
        }

    async def health_check(self) -> dict[str, Any]:
        """Perform health check of the sync engine."""
        stats = await self.get_sync_statistics()

        # Check component health
        qdrant_healthy = await self.qdrant_manager.health_check()
        neo4j_healthy = self.neo4j_manager.health_check()
        mapping_healthy = await self.id_mapping_manager.health_check()

        return {
            "sync_engine": {
                "status": "healthy" if self._running else "stopped",
                "statistics": stats,
            },
            "components": {
                "qdrant": qdrant_healthy,
                "neo4j": neo4j_healthy,
                "id_mapping": mapping_healthy,
            },
            "overall_health": (
                "healthy"
                if self._running
                and all(
                    [
                        qdrant_healthy.get("status") == "healthy",
                        neo4j_healthy.get("status") == "healthy",
                        mapping_healthy.get("status") == "healthy",
                    ]
                )
                else "unhealthy"
            ),
        }

    async def force_sync_entity(
        self,
        entity_id: str,
        database_type: DatabaseType,
        direction: SyncDirection | None = None,
    ) -> bool:
        """Force synchronization of a specific entity."""
        try:
            # Find mapping
            mapping = None
            if database_type == DatabaseType.QDRANT:
                mapping = await self.id_mapping_manager.get_mapping_by_qdrant_id(
                    entity_id
                )
            elif database_type == DatabaseType.NEO4J:
                mapping = await self.id_mapping_manager.get_mapping_by_neo4j_id(
                    entity_id
                )

            if not mapping:
                logger.error(
                    f"No mapping found for entity {entity_id} in {database_type.value}"
                )
                return False

            # Create synthetic change event
            event = ChangeEvent(
                change_type=ChangeType.UPDATE,
                database_type=database_type,
                entity_type=mapping.entity_type,
                mapping_type=mapping.mapping_type,
                entity_id=entity_id,
                entity_name=mapping.entity_name,
            )

            # Determine direction
            if direction is None:
                direction = (
                    SyncDirection.QDRANT_TO_NEO4J
                    if database_type == DatabaseType.QDRANT
                    else SyncDirection.NEO4J_TO_QDRANT
                )

            # Create and execute operation
            operation = SyncOperation(event=event, direction=direction, mapping=mapping)
            await self._execute_sync_operation(operation)

            return operation.success

        except Exception as e:
            logger.error(f"Error forcing sync for entity {entity_id}: {e}")
            return False
