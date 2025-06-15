"""Enhanced Sync Event System with Operation Differentiation.

This module provides an enhanced event-driven synchronization system that builds
on the atomic transaction layer to provide ACID properties for cross-database
operations with operation-specific handling for CREATE, UPDATE, and DELETE.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set, Union

if TYPE_CHECKING:
    from .graphiti_temporal_integration import GraphitiTemporalIntegration
    from .sync_conflict_monitor import SyncConflictMonitor

from ..utils.logging import LoggingConfig
from .atomic_transactions import (
    AtomicTransactionManager,
    OperationType,
    TransactionContext,
)

# Avoid circular import - GraphitiTemporalIntegration will be imported at runtime
from .id_mapping_manager import IDMapping, IDMappingManager, MappingStatus, MappingType
from .neo4j_manager import Neo4jManager
from .qdrant_manager import QdrantManager
from .sync_event_system import ChangeEvent, ChangeType, DatabaseType, SyncEventSystem
from .types import EntityType

logger = LoggingConfig.get_logger(__name__)


class SyncOperationStatus(Enum):
    """Status of synchronization operations."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class SyncOperationType(Enum):
    """Types of synchronization operations."""

    CREATE_DOCUMENT = "create_document"
    UPDATE_DOCUMENT = "update_document"
    DELETE_DOCUMENT = "delete_document"
    CREATE_ENTITY = "create_entity"
    UPDATE_ENTITY = "update_entity"
    DELETE_ENTITY = "delete_entity"
    CASCADE_DELETE = "cascade_delete"
    VERSION_UPDATE = "version_update"


@dataclass
class EnhancedSyncOperation:
    """Enhanced synchronization operation with atomic transaction support."""

    # Operation identification
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Operation details
    operation_type: SyncOperationType = SyncOperationType.UPDATE_DOCUMENT
    source_event: Optional[ChangeEvent] = None
    target_databases: Set[DatabaseType] = field(default_factory=set)

    # Entity information
    entity_id: Optional[str] = None
    entity_uuid: Optional[str] = None
    entity_type: EntityType = EntityType.CONCEPT
    mapping_type: MappingType = MappingType.DOCUMENT

    # Operation data
    operation_data: Dict[str, Any] = field(default_factory=dict)
    previous_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Versioning information
    document_version: int = 1
    previous_version: Optional[int] = None
    content_hash: Optional[str] = None

    # Processing status
    status: SyncOperationStatus = SyncOperationStatus.PENDING
    transaction_id: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    # Relationships and dependencies
    related_operations: List[str] = field(default_factory=list)
    dependent_operations: List[str] = field(default_factory=list)

    def mark_processing(self, transaction_id: str) -> None:
        """Mark operation as processing with transaction ID."""
        self.status = SyncOperationStatus.PROCESSING
        self.transaction_id = transaction_id

    def mark_completed(self) -> None:
        """Mark operation as completed."""
        self.status = SyncOperationStatus.COMPLETED

    def mark_failed(self, error: str) -> None:
        """Mark operation as failed with error message."""
        self.status = SyncOperationStatus.FAILED
        self.error_message = error
        self.retry_count += 1

    def mark_rolled_back(self) -> None:
        """Mark operation as rolled back."""
        self.status = SyncOperationStatus.ROLLED_BACK

    def can_retry(self) -> bool:
        """Check if operation can be retried."""
        return (
            self.retry_count < self.max_retries
            and self.status == SyncOperationStatus.FAILED
        )


class EnhancedSyncEventSystem:
    """Enhanced event system with atomic transaction support and operation differentiation."""

    def __init__(
        self,
        qdrant_manager: QdrantManager,
        neo4j_manager: Neo4jManager,
        id_mapping_manager: IDMappingManager,
        atomic_transaction_manager: AtomicTransactionManager,
        graphiti_temporal_integration: Optional["GraphitiTemporalIntegration"] = None,
        base_sync_system: Optional[SyncEventSystem] = None,
        sync_conflict_monitor: Optional["SyncConflictMonitor"] = None,
        max_concurrent_operations: int = 10,
        operation_timeout_seconds: int = 300,
        enable_cascading_deletes: bool = True,
        enable_versioned_updates: bool = True,
        enable_graphiti_temporal_features: bool = True,
    ):
        """Initialize the enhanced sync event system.

        Args:
            qdrant_manager: QDrant manager instance
            neo4j_manager: Neo4j manager instance
            id_mapping_manager: ID mapping manager instance
            atomic_transaction_manager: Atomic transaction manager instance
            graphiti_temporal_integration: Optional Graphiti temporal integration
            base_sync_system: Optional base sync event system for change detection
            sync_conflict_monitor: Optional sync conflict monitor for comprehensive monitoring
            max_concurrent_operations: Maximum concurrent sync operations
            operation_timeout_seconds: Timeout for sync operations
            enable_cascading_deletes: Whether to enable cascading deletions
            enable_versioned_updates: Whether to enable versioned updates
            enable_graphiti_temporal_features: Whether to enable Graphiti temporal features
        """
        self.qdrant_manager = qdrant_manager
        self.neo4j_manager = neo4j_manager
        self.id_mapping_manager = id_mapping_manager
        self.atomic_transaction_manager = atomic_transaction_manager
        self.graphiti_temporal_integration = graphiti_temporal_integration
        self.base_sync_system = base_sync_system
        self.sync_conflict_monitor = sync_conflict_monitor
        self.max_concurrent_operations = max_concurrent_operations
        self.operation_timeout_seconds = operation_timeout_seconds
        self.enable_cascading_deletes = enable_cascading_deletes
        self.enable_versioned_updates = enable_versioned_updates
        self.enable_graphiti_temporal_features = enable_graphiti_temporal_features

        # Operation management
        self._pending_operations: asyncio.Queue[EnhancedSyncOperation] = asyncio.Queue()
        self._active_operations: Dict[str, EnhancedSyncOperation] = {}
        self._completed_operations: Dict[str, EnhancedSyncOperation] = {}
        self._failed_operations: Dict[str, EnhancedSyncOperation] = {}

        # Processing control
        self._running = False
        self._processing_tasks: List[asyncio.Task] = []
        self._semaphore = asyncio.Semaphore(max_concurrent_operations)

        # Event handlers
        self._operation_handlers: Dict[SyncOperationType, Callable] = {
            SyncOperationType.CREATE_DOCUMENT: self._handle_create_document,
            SyncOperationType.UPDATE_DOCUMENT: self._handle_update_document,
            SyncOperationType.DELETE_DOCUMENT: self._handle_delete_document,
            SyncOperationType.CREATE_ENTITY: self._handle_create_entity,
            SyncOperationType.UPDATE_ENTITY: self._handle_update_entity,
            SyncOperationType.DELETE_ENTITY: self._handle_delete_entity,
            SyncOperationType.CASCADE_DELETE: self._handle_cascade_delete,
            SyncOperationType.VERSION_UPDATE: self._handle_version_update,
        }

        # Statistics
        self._stats = {
            "operations_processed": 0,
            "operations_failed": 0,
            "operations_rolled_back": 0,
            "create_operations": 0,
            "update_operations": 0,
            "delete_operations": 0,
            "cascade_operations": 0,
            "version_operations": 0,
        }

        # Setup base system integration
        if self.base_sync_system:
            self._setup_base_system_integration()

    def _setup_base_system_integration(self) -> None:
        """Setup integration with base sync event system."""
        if self.base_sync_system:
            # Register handlers for change events
            self.base_sync_system.add_event_handler("*", self._on_base_change_event)

    def _on_base_change_event(self, event: ChangeEvent) -> None:
        """Handle change events from base sync system."""
        if not self._running:
            return

        # Convert change event to enhanced sync operation
        operation = self._create_operation_from_event(event)
        if operation:
            asyncio.create_task(self.queue_operation(operation))

    def _create_operation_from_event(
        self, event: ChangeEvent
    ) -> Optional[EnhancedSyncOperation]:
        """Create enhanced sync operation from change event."""
        try:
            # Determine operation type based on change type and mapping type
            if event.mapping_type == MappingType.DOCUMENT:
                if event.change_type == ChangeType.CREATE:
                    operation_type = SyncOperationType.CREATE_DOCUMENT
                elif event.change_type == ChangeType.UPDATE:
                    operation_type = SyncOperationType.UPDATE_DOCUMENT
                elif event.change_type == ChangeType.DELETE:
                    operation_type = SyncOperationType.DELETE_DOCUMENT
                else:
                    logger.warning(
                        f"Unsupported change type for document: {event.change_type}"
                    )
                    return None
            else:
                # Entity operations
                if event.change_type == ChangeType.CREATE:
                    operation_type = SyncOperationType.CREATE_ENTITY
                elif event.change_type == ChangeType.UPDATE:
                    operation_type = SyncOperationType.UPDATE_ENTITY
                elif event.change_type == ChangeType.DELETE:
                    operation_type = SyncOperationType.DELETE_ENTITY
                else:
                    logger.warning(
                        f"Unsupported change type for entity: {event.change_type}"
                    )
                    return None

            # Determine target databases (opposite of source)
            target_databases = set()
            if event.database_type == DatabaseType.QDRANT:
                target_databases.add(DatabaseType.NEO4J)
            elif event.database_type == DatabaseType.NEO4J:
                target_databases.add(DatabaseType.QDRANT)

            operation = EnhancedSyncOperation(
                operation_type=operation_type,
                source_event=event,
                target_databases=target_databases,
                entity_id=event.entity_id,
                entity_uuid=event.entity_uuid,
                entity_type=event.entity_type,
                mapping_type=event.mapping_type,
                operation_data=event.new_data or {},
                previous_data=event.old_data,
                metadata={
                    "source_database": event.database_type.value,
                    "source_event_id": event.event_id,
                    "affected_fields": list(event.affected_fields),
                },
            )

            return operation

        except Exception as e:
            logger.error(f"Error creating operation from event {event.event_id}: {e}")
            return None

    async def start(self) -> None:
        """Start the enhanced sync event system."""
        if self._running:
            logger.warning("Enhanced sync event system already running")
            return

        self._running = True

        # Start base sync system if provided
        if self.base_sync_system:
            await self.base_sync_system.start()

        # Start processing tasks
        for i in range(self.max_concurrent_operations):
            task = asyncio.create_task(self._operation_processor())
            self._processing_tasks.append(task)

        logger.info("Enhanced sync event system started")

    async def stop(self) -> None:
        """Stop the enhanced sync event system."""
        self._running = False

        # Stop base sync system
        if self.base_sync_system:
            await self.base_sync_system.stop()

        # Cancel processing tasks
        for task in self._processing_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._processing_tasks:
            await asyncio.gather(*self._processing_tasks, return_exceptions=True)

        self._processing_tasks.clear()

        logger.info("Enhanced sync event system stopped")

    async def queue_operation(self, operation: EnhancedSyncOperation) -> None:
        """Queue a sync operation for processing."""
        try:
            await self._pending_operations.put(operation)
            logger.debug(
                f"Queued operation {operation.operation_id} of type {operation.operation_type}"
            )
        except Exception as e:
            logger.error(f"Error queuing operation {operation.operation_id}: {e}")

    async def _operation_processor(self) -> None:
        """Main operation processing loop."""
        while self._running:
            try:
                # Get operation from queue with timeout
                operation = await asyncio.wait_for(
                    self._pending_operations.get(), timeout=1.0
                )

                # Process operation with semaphore
                async with self._semaphore:
                    await self._process_operation(operation)

            except asyncio.TimeoutError:
                # No operations to process, continue
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in operation processor: {e}")

    async def _process_operation(self, operation: EnhancedSyncOperation) -> None:
        """Process a single sync operation."""
        operation_id = operation.operation_id
        self._active_operations[operation_id] = operation

        # Initialize sync conflict monitoring if available
        sync_metrics = None
        if self.sync_conflict_monitor:
            try:
                sync_metrics = await self.sync_conflict_monitor.monitor_sync_operation(
                    operation
                )
            except Exception as e:
                logger.warning(
                    f"Sync conflict monitoring failed for {operation_id}: {e}"
                )

        try:
            logger.info(
                f"Processing operation {operation_id} of type {operation.operation_type}"
            )

            # Process with Graphiti temporal features if enabled
            if (
                self.enable_graphiti_temporal_features
                and self.graphiti_temporal_integration
            ):
                try:
                    temporal_operations = (
                        await self.graphiti_temporal_integration.process_sync_operation(
                            operation
                        )
                    )
                    logger.debug(
                        f"Created {len(temporal_operations)} temporal operations for {operation_id}"
                    )

                    # Store temporal operation references in metadata
                    operation.metadata["temporal_operations"] = [
                        op.operation_id for op in temporal_operations
                    ]
                except Exception as e:
                    logger.warning(
                        f"Graphiti temporal processing failed for {operation_id}: {e}"
                    )

            # Get operation handler
            handler = self._operation_handlers.get(operation.operation_type)
            if not handler:
                raise ValueError(
                    f"No handler for operation type: {operation.operation_type}"
                )

            # Process operation with timeout
            await asyncio.wait_for(
                handler(operation), timeout=self.operation_timeout_seconds
            )

            # Mark as completed
            operation.mark_completed()
            self._completed_operations[operation_id] = operation
            self._stats["operations_processed"] += 1

            logger.info(f"Completed operation {operation_id}")

        except Exception as e:
            logger.error(f"Error processing operation {operation_id}: {e}")
            operation.mark_failed(str(e))
            self._failed_operations[operation_id] = operation
            self._stats["operations_failed"] += 1

            # Retry if possible
            if operation.can_retry():
                logger.info(
                    f"Retrying operation {operation_id} (attempt {operation.retry_count + 1})"
                )
                await self.queue_operation(operation)

        finally:
            # Update sync metrics with final operation status
            if sync_metrics and self.sync_conflict_monitor:
                try:
                    sync_metrics.mark_completed(operation.status)
                    if operation.error_message:
                        sync_metrics.add_error(operation.error_message)
                except Exception as e:
                    logger.warning(
                        f"Error updating sync metrics for {operation_id}: {e}"
                    )

            # Remove from active operations
            if operation_id in self._active_operations:
                del self._active_operations[operation_id]

    async def _handle_create_document(self, operation: EnhancedSyncOperation) -> None:
        """Handle CREATE document operation."""
        logger.debug(f"Handling CREATE document operation {operation.operation_id}")

        async with self.atomic_transaction_manager.transaction() as tx:
            operation.mark_processing(tx.transaction.transaction_id)

            # Create mapping if it doesn't exist
            mapping = await self._ensure_mapping_exists(operation)

            # Add operations to both databases
            if DatabaseType.QDRANT in operation.target_databases:
                await self._add_qdrant_create_operation(tx, operation, mapping)

            if DatabaseType.NEO4J in operation.target_databases:
                await self._add_neo4j_create_operation(tx, operation, mapping)

            # Update mapping version
            if mapping:
                await self._update_mapping_version(mapping, operation)

        self._stats["create_operations"] += 1

    async def _handle_update_document(self, operation: EnhancedSyncOperation) -> None:
        """Handle UPDATE document operation with versioning."""
        logger.debug(f"Handling UPDATE document operation {operation.operation_id}")

        async with self.atomic_transaction_manager.transaction() as tx:
            operation.mark_processing(tx.transaction.transaction_id)

            # Get existing mapping
            mapping = await self._get_mapping_for_operation(operation)
            if not mapping:
                raise ValueError(f"No mapping found for entity {operation.entity_id}")

            # Handle versioned updates if enabled
            if self.enable_versioned_updates:
                await self._handle_versioned_update(tx, operation, mapping)
            else:
                await self._handle_simple_update(tx, operation, mapping)

            # Update mapping version
            await self._update_mapping_version(mapping, operation)

        self._stats["update_operations"] += 1

    async def _handle_delete_document(self, operation: EnhancedSyncOperation) -> None:
        """Handle DELETE document operation with cascading."""
        logger.debug(f"Handling DELETE document operation {operation.operation_id}")

        async with self.atomic_transaction_manager.transaction() as tx:
            operation.mark_processing(tx.transaction.transaction_id)

            # Get existing mapping
            mapping = await self._get_mapping_for_operation(operation)
            if not mapping:
                logger.warning(f"No mapping found for entity {operation.entity_id}")
                return

            # Handle cascading deletes if enabled
            if self.enable_cascading_deletes:
                await self._handle_cascading_delete(tx, operation, mapping)
            else:
                await self._handle_simple_delete(tx, operation, mapping)

            # Remove mapping
            await self.id_mapping_manager.delete_mapping(mapping.mapping_id)

        self._stats["delete_operations"] += 1

    async def _handle_create_entity(self, operation: EnhancedSyncOperation) -> None:
        """Handle CREATE entity operation."""
        # Similar to create document but for entities
        await self._handle_create_document(operation)

    async def _handle_update_entity(self, operation: EnhancedSyncOperation) -> None:
        """Handle UPDATE entity operation."""
        # Similar to update document but for entities
        await self._handle_update_document(operation)

    async def _handle_delete_entity(self, operation: EnhancedSyncOperation) -> None:
        """Handle DELETE entity operation."""
        # Similar to delete document but for entities
        await self._handle_delete_document(operation)

    async def _handle_cascade_delete(self, operation: EnhancedSyncOperation) -> None:
        """Handle CASCADE delete operation."""
        logger.debug(f"Handling CASCADE delete operation {operation.operation_id}")

        async with self.atomic_transaction_manager.transaction() as tx:
            operation.mark_processing(tx.transaction.transaction_id)

            # Get existing mapping
            mapping = await self._get_mapping_for_operation(operation)
            if not mapping:
                logger.warning(
                    f"No mapping found for cascade delete of entity {operation.entity_id}"
                )
                return

            # Perform cascading delete
            await self._handle_cascading_delete(tx, operation, mapping)

            # Remove mapping
            await self.id_mapping_manager.delete_mapping(mapping.mapping_id)

        self._stats["cascade_operations"] += 1

    async def _handle_version_update(self, operation: EnhancedSyncOperation) -> None:
        """Handle VERSION update operation."""
        logger.debug(f"Handling VERSION update operation {operation.operation_id}")

        async with self.atomic_transaction_manager.transaction() as tx:
            operation.mark_processing(tx.transaction.transaction_id)

            # Get existing mapping
            mapping = await self._get_mapping_for_operation(operation)
            if not mapping:
                raise ValueError(
                    f"No mapping found for version update of entity {operation.entity_id}"
                )

            # Handle versioned update
            await self._handle_versioned_update(tx, operation, mapping)

            # Update mapping version
            await self._update_mapping_version(mapping, operation)

        self._stats["version_operations"] += 1

    # Helper methods for operation processing

    async def _ensure_mapping_exists(
        self, operation: EnhancedSyncOperation
    ) -> Optional[IDMapping]:
        """Ensure mapping exists for the operation."""
        if not operation.entity_id:
            return None

        # Try to get existing mapping
        mapping = await self._get_mapping_for_operation(operation)
        if mapping:
            return mapping

        # Create new mapping
        mapping = await self.id_mapping_manager.create_mapping(
            qdrant_point_id=(
                operation.entity_id
                if operation.source_event
                and operation.source_event.database_type == DatabaseType.QDRANT
                else None
            ),
            neo4j_node_id=(
                operation.entity_id
                if operation.source_event
                and operation.source_event.database_type == DatabaseType.NEO4J
                else None
            ),
            entity_type=operation.entity_type,
            mapping_type=operation.mapping_type,
            metadata=operation.metadata,
        )

        return mapping

    async def _get_mapping_for_operation(
        self, operation: EnhancedSyncOperation
    ) -> Optional[IDMapping]:
        """Get mapping for the operation."""
        if not operation.entity_id:
            return None

        # Try different lookup methods based on source
        if operation.source_event:
            if operation.source_event.database_type == DatabaseType.QDRANT:
                return await self.id_mapping_manager.get_mapping_by_qdrant_id(
                    operation.entity_id
                )
            elif operation.source_event.database_type == DatabaseType.NEO4J:
                return await self.id_mapping_manager.get_mapping_by_neo4j_id(
                    operation.entity_id
                )

        # Try UUID lookup
        if operation.entity_uuid:
            return await self.id_mapping_manager.get_mapping_by_neo4j_uuid(
                operation.entity_uuid
            )

        return None

    async def _add_qdrant_create_operation(
        self,
        tx: TransactionContext,
        operation: EnhancedSyncOperation,
        mapping: Optional[IDMapping],
    ) -> None:
        """Add QDrant create operation to transaction."""
        if not mapping or not mapping.qdrant_point_id:
            return

        await tx.add_qdrant_operation(
            operation_type=OperationType.CREATE,
            entity_id=mapping.qdrant_point_id,
            operation_data=operation.operation_data,
        )

    async def _add_neo4j_create_operation(
        self,
        tx: TransactionContext,
        operation: EnhancedSyncOperation,
        mapping: Optional[IDMapping],
    ) -> None:
        """Add Neo4j create operation to transaction."""
        if not mapping:
            return

        node_data = {
            "labels": (
                ["Document"]
                if operation.mapping_type == MappingType.DOCUMENT
                else ["Entity"]
            ),
            "properties": {
                "uuid": mapping.neo4j_node_uuid or mapping.mapping_id,
                **operation.operation_data,
            },
        }

        await tx.add_neo4j_operation(
            operation_type=OperationType.CREATE,
            entity_id=mapping.neo4j_node_uuid or mapping.mapping_id,
            operation_data=node_data,
        )

    async def _handle_versioned_update(
        self,
        tx: TransactionContext,
        operation: EnhancedSyncOperation,
        mapping: IDMapping,
    ) -> None:
        """Handle versioned update with relationship preservation."""
        # Create new version node in Neo4j
        if DatabaseType.NEO4J in operation.target_databases:
            new_version_uuid = str(uuid.uuid4())
            node_data = {
                "labels": ["Document", "Version"],
                "properties": {
                    "uuid": new_version_uuid,
                    "version": mapping.document_version + 1,
                    "previous_version": mapping.document_version,
                    "original_uuid": mapping.neo4j_node_uuid,
                    **operation.operation_data,
                },
            }

            await tx.add_neo4j_operation(
                operation_type=OperationType.CREATE,
                entity_id=new_version_uuid,
                operation_data=node_data,
            )

            # Create relationship to previous version
            relationship_data = {
                "type": "PREVIOUS_VERSION",
                "from_uuid": new_version_uuid,
                "to_uuid": mapping.neo4j_node_uuid,
                "properties": {
                    "created_at": datetime.now(UTC).isoformat(),
                    "version_increment": 1,
                },
            }

            await tx.add_neo4j_operation(
                operation_type=OperationType.CREATE,
                entity_id=f"{new_version_uuid}_rel_{mapping.neo4j_node_uuid}",
                operation_data=relationship_data,
            )

        # Update QDrant if needed
        if (
            DatabaseType.QDRANT in operation.target_databases
            and mapping.qdrant_point_id
        ):
            await tx.add_qdrant_operation(
                operation_type=OperationType.UPDATE,
                entity_id=mapping.qdrant_point_id,
                operation_data=operation.operation_data,
            )

    async def _handle_simple_update(
        self,
        tx: TransactionContext,
        operation: EnhancedSyncOperation,
        mapping: IDMapping,
    ) -> None:
        """Handle simple update without versioning."""
        if DatabaseType.NEO4J in operation.target_databases and mapping.neo4j_node_uuid:
            await tx.add_neo4j_operation(
                operation_type=OperationType.UPDATE,
                entity_id=mapping.neo4j_node_uuid,
                operation_data={"properties": operation.operation_data},
            )

        if (
            DatabaseType.QDRANT in operation.target_databases
            and mapping.qdrant_point_id
        ):
            await tx.add_qdrant_operation(
                operation_type=OperationType.UPDATE,
                entity_id=mapping.qdrant_point_id,
                operation_data=operation.operation_data,
            )

    async def _handle_cascading_delete(
        self,
        tx: TransactionContext,
        operation: EnhancedSyncOperation,
        mapping: IDMapping,
    ) -> None:
        """Handle cascading delete with cleanup."""
        # Delete from Neo4j with all relationships
        if DatabaseType.NEO4J in operation.target_databases and mapping.neo4j_node_uuid:
            await tx.add_neo4j_operation(
                operation_type=OperationType.DELETE,
                entity_id=mapping.neo4j_node_uuid,
                operation_data={"cascade": True},
            )

        # Delete from QDrant
        if (
            DatabaseType.QDRANT in operation.target_databases
            and mapping.qdrant_point_id
        ):
            await tx.add_qdrant_operation(
                operation_type=OperationType.DELETE,
                entity_id=mapping.qdrant_point_id,
                operation_data={},
            )

    async def _handle_simple_delete(
        self,
        tx: TransactionContext,
        operation: EnhancedSyncOperation,
        mapping: IDMapping,
    ) -> None:
        """Handle simple delete without cascading."""
        if DatabaseType.NEO4J in operation.target_databases and mapping.neo4j_node_uuid:
            await tx.add_neo4j_operation(
                operation_type=OperationType.DELETE,
                entity_id=mapping.neo4j_node_uuid,
                operation_data={},
            )

        if (
            DatabaseType.QDRANT in operation.target_databases
            and mapping.qdrant_point_id
        ):
            await tx.add_qdrant_operation(
                operation_type=OperationType.DELETE,
                entity_id=mapping.qdrant_point_id,
                operation_data={},
            )

    async def _update_mapping_version(
        self, mapping: IDMapping, operation: EnhancedSyncOperation
    ) -> None:
        """Update mapping version information."""
        source_db = "unknown"
        if operation.source_event:
            source_db = operation.source_event.database_type.value

        await self.id_mapping_manager.update_document_version(
            mapping_id=mapping.mapping_id,
            update_source=source_db,
            content_hash=operation.content_hash,
            metadata={
                "operation_id": operation.operation_id,
                "operation_type": operation.operation_type.value,
                "timestamp": operation.timestamp.isoformat(),
            },
        )

    async def get_operation_statistics(self) -> Dict[str, Any]:
        """Get operation statistics."""
        stats = self._stats.copy()
        stats.update(
            {
                "pending_operations": self._pending_operations.qsize(),
                "active_operations": len(self._active_operations),
                "completed_operations": len(self._completed_operations),
                "failed_operations": len(self._failed_operations),
                "running": self._running,
            }
        )
        return stats

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the enhanced sync system."""
        try:
            stats = await self.get_operation_statistics()

            # Check base system health
            base_health = {}
            if self.base_sync_system:
                base_health = await self.base_sync_system.health_check()

            # Check atomic transaction manager health
            tx_health = await self.atomic_transaction_manager.health_check()

            # Check Graphiti temporal integration health
            graphiti_health = {}
            if self.graphiti_temporal_integration:
                try:
                    graphiti_health = (
                        await self.graphiti_temporal_integration.health_check()
                    )
                except Exception as e:
                    graphiti_health = {
                        "healthy": False,
                        "error": str(e),
                    }

            # Check sync conflict monitor health
            sync_monitor_health = {}
            if self.sync_conflict_monitor:
                try:
                    sync_monitor_health = (
                        await self.sync_conflict_monitor.health_check()
                    )
                except Exception as e:
                    sync_monitor_health = {
                        "status": "unhealthy",
                        "error": str(e),
                    }

            return {
                "healthy": self._running
                and base_health.get("healthy", True)
                and tx_health.get("healthy", True)
                and graphiti_health.get("healthy", True)
                and sync_monitor_health.get("status", "healthy") == "healthy",
                "enhanced_system_running": self._running,
                "graphiti_temporal_features_enabled": self.enable_graphiti_temporal_features,
                "base_system_health": base_health,
                "transaction_manager_health": tx_health,
                "graphiti_temporal_health": graphiti_health,
                "sync_conflict_monitor_health": sync_monitor_health,
                "operation_stats": stats,
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "running": self._running,
            }
