"""Enhanced Sync Event System with Operation Differentiation.

This module provides an enhanced event-driven synchronization system that builds
on the atomic transaction layer to provide ACID properties for cross-database
operations with operation-specific handling for CREATE, UPDATE, and DELETE.
"""

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ..graphiti_temporal_integration import GraphitiTemporalIntegration
    from ..operation_differentiation import (
        OperationCharacteristics,
    )
    from .conflict_monitor import SyncConflictMonitor

from ...utils.logging import LoggingConfig
from ..atomic_transactions import (
    AtomicTransactionManager,
)
from ..managers import (
    IDMappingManager,
    MappingType,
    Neo4jManager,
    QdrantManager,
)
from .event_system import ChangeEvent, ChangeType, DatabaseType, SyncEventSystem
from .operations import EnhancedSyncOperation
from .processor import SyncOperationProcessor
from .types import SyncOperationType

logger = LoggingConfig.get_logger(__name__)


class EnhancedSyncEventSystem:
    """Enhanced event system with atomic transaction support and operation differentiation."""

    def __init__(
        self,
        qdrant_manager: QdrantManager,
        neo4j_manager: Neo4jManager,
        id_mapping_manager: IDMappingManager,
        atomic_transaction_manager: AtomicTransactionManager,
        graphiti_temporal_integration: Optional["GraphitiTemporalIntegration"] = None,
        base_sync_system: SyncEventSystem | None = None,
        sync_conflict_monitor: Optional["SyncConflictMonitor"] = None,
        max_concurrent_operations: int = 10,
        operation_timeout_seconds: int = 300,
        enable_cascading_deletes: bool = True,
        enable_versioned_updates: bool = True,
        enable_graphiti_temporal_features: bool = True,
        enable_operation_differentiation: bool = True,
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
            enable_operation_differentiation: Whether to enable intelligent operation differentiation
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
        self.enable_operation_differentiation = enable_operation_differentiation

        # Initialize Operation Differentiation Manager
        if self.enable_operation_differentiation:
            from ..operation_differentiation import OperationDifferentiationManager

            self.operation_differentiation_manager = OperationDifferentiationManager(
                max_concurrent_operations=max_concurrent_operations,
                enable_caching=True,
                cache_ttl_seconds=3600,
            )
        else:
            self.operation_differentiation_manager = None

        # Initialize the operation processor
        from .handlers import SyncOperationHandlers

        operation_handlers = SyncOperationHandlers(
            qdrant_manager=qdrant_manager,
            neo4j_manager=neo4j_manager,
            id_mapping_manager=id_mapping_manager,
            enable_cascading_deletes=enable_cascading_deletes,
            enable_versioned_updates=enable_versioned_updates,
        )

        self.operation_processor = SyncOperationProcessor(
            atomic_transaction_manager=atomic_transaction_manager,
            operation_handlers=operation_handlers,
            operation_differentiation_manager=self.operation_differentiation_manager,
            graphiti_temporal_integration=graphiti_temporal_integration,
            sync_conflict_monitor=sync_conflict_monitor,
            operation_timeout_seconds=operation_timeout_seconds,
            enable_operation_differentiation=enable_operation_differentiation,
            enable_graphiti_temporal_features=enable_graphiti_temporal_features,
        )

        # Operation management (legacy queue for fallback)
        self._pending_operations: asyncio.Queue[EnhancedSyncOperation] = asyncio.Queue()
        self._active_operations: dict[str, EnhancedSyncOperation] = {}
        self._completed_operations: dict[str, EnhancedSyncOperation] = {}
        self._failed_operations: dict[str, EnhancedSyncOperation] = {}

        # Processing control
        self._running = False
        self._processing_tasks: list[asyncio.Task] = []
        self._semaphore = asyncio.Semaphore(max_concurrent_operations)

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
    ) -> EnhancedSyncOperation | None:
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
        """Queue a sync operation for processing with intelligent differentiation."""
        try:
            if (
                self.enable_operation_differentiation
                and self.operation_differentiation_manager
            ):
                # Use intelligent operation differentiation
                characteristics, validation_result = (
                    await self.operation_differentiation_manager.process_operation(
                        operation, context={"sync_system": self}
                    )
                )

                # Check validation results
                if not validation_result.is_valid:
                    error_msg = f"Operation validation failed: {', '.join(validation_result.errors)}"
                    logger.error(
                        f"Operation {operation.operation_id} validation failed: {error_msg}"
                    )
                    operation.mark_failed(error_msg)
                    self._failed_operations[operation.operation_id] = operation
                    return

                # Log validation warnings if any
                if validation_result.warnings:
                    logger.warning(
                        f"Operation {operation.operation_id} warnings: {', '.join(validation_result.warnings)}"
                    )

                # Store characteristics and validation results in metadata
                operation.metadata.update(
                    {
                        "operation_characteristics": {
                            "priority": characteristics.priority.value,
                            "complexity": characteristics.complexity.value,
                            "impact": characteristics.impact.value,
                            "priority_score": characteristics.calculate_priority_score(),
                            "validation_level": characteristics.validation_level.value,
                        },
                        "validation_result": {
                            "validation_level": validation_result.validation_level.value,
                            "validation_time": validation_result.validation_time,
                            "warnings_count": len(validation_result.warnings),
                            "recommendations_count": len(
                                validation_result.recommendations
                            ),
                        },
                    }
                )

                logger.info(
                    f"Queued operation {operation.operation_id} with {characteristics.priority.value} priority "
                    f"({characteristics.complexity.value} complexity, {characteristics.impact.value} impact)"
                )
            else:
                # Fallback to legacy queue system
                await self._pending_operations.put(operation)
                logger.debug(
                    f"Queued operation {operation.operation_id} of type {operation.operation_type} (legacy mode, queue size now: {self._pending_operations.qsize()})"
                )

        except Exception as e:
            logger.error(f"Error queuing operation {operation.operation_id}: {e}")
            operation.mark_failed(str(e))
            self._failed_operations[operation.operation_id] = operation

    async def get_operation_statistics(self) -> dict[str, Any]:
        """Get operation statistics."""
        # Create a new dictionary with all statistics
        result = {
            # Copy existing integer stats
            **self._stats,
            # Add additional statistics
            "pending_operations": self._pending_operations.qsize(),
            "active_operations": len(self._active_operations),
            "completed_operations": len(self._completed_operations),
            "failed_operations": len(self._failed_operations),
            "running": self._running,
            "operation_differentiation_enabled": self.enable_operation_differentiation,
        }

        # Add operation differentiation statistics if enabled
        if (
            self.enable_operation_differentiation
            and self.operation_differentiation_manager
        ):
            try:
                differentiation_stats = (
                    await self.operation_differentiation_manager.get_statistics()
                )
                result["operation_differentiation"] = differentiation_stats
            except Exception as e:
                logger.warning(
                    f"Error getting operation differentiation statistics: {e}"
                )
                result["operation_differentiation"] = {"error": str(e)}

        return result

    async def health_check(self) -> dict[str, Any]:
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

            # Check operation differentiation manager health
            operation_diff_health = {}
            if (
                self.enable_operation_differentiation
                and self.operation_differentiation_manager
            ):
                try:
                    operation_diff_health = (
                        await self.operation_differentiation_manager.health_check()
                    )
                except Exception as e:
                    operation_diff_health = {
                        "healthy": False,
                        "error": str(e),
                    }

            return {
                "healthy": self._running
                and base_health.get("healthy", True)
                and tx_health.get("healthy", True)
                and graphiti_health.get("healthy", True)
                and sync_monitor_health.get("status", "healthy") == "healthy"
                and operation_diff_health.get("healthy", True),
                "enhanced_system_running": self._running,
                "operation_differentiation_enabled": self.enable_operation_differentiation,
                "graphiti_temporal_features_enabled": self.enable_graphiti_temporal_features,
                "base_system_health": base_health,
                "transaction_manager_health": tx_health,
                "graphiti_temporal_health": graphiti_health,
                "sync_conflict_monitor_health": sync_monitor_health,
                "operation_differentiation_health": operation_diff_health,
                "operation_stats": stats,
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "running": self._running,
            }

    async def _operation_processor(self) -> None:
        """Main operation processing loop with intelligent priority handling."""
        logger.debug("Operation processor started")
        while self._running:
            try:
                operation = None
                characteristics = None

                # Try to get operation from differentiation manager first if enabled
                if (
                    self.enable_operation_differentiation
                    and self.operation_differentiation_manager
                ):
                    try:
                        result = (
                            await self.operation_differentiation_manager.get_next_operation()
                        )
                        if result:
                            operation, characteristics = result
                            logger.debug(
                                f"Got operation {operation.operation_id} from differentiation manager"
                            )
                    except Exception as e:
                        logger.warning(
                            f"Error getting operation from differentiation manager: {e}"
                        )

                # Fallback to legacy queue if no operation from differentiation manager
                if not operation:
                    try:
                        logger.debug(
                            f"Waiting for operation from legacy queue (queue size: {self._pending_operations.qsize()})"
                        )
                        operation = await asyncio.wait_for(
                            self._pending_operations.get(), timeout=1.0
                        )
                        logger.debug(
                            f"Got operation {operation.operation_id} from legacy queue"
                        )
                    except asyncio.TimeoutError:
                        logger.debug("Operation processor timeout, continuing...")
                        continue

                # Acquire semaphore for concurrent processing
                async with self._semaphore:
                    # Move operation to active
                    self._active_operations[operation.operation_id] = operation

                    try:
                        # If we don't have characteristics from differentiation manager,
                        # try to extract from metadata (for legacy operations)
                        if (
                            not characteristics
                            and self.enable_operation_differentiation
                            and self.operation_differentiation_manager
                            and "operation_characteristics" in operation.metadata
                        ):
                            # Extract characteristics from metadata
                            char_data = operation.metadata["operation_characteristics"]
                            from ..operation_differentiation import (
                                OperationCharacteristics,
                                OperationComplexity,
                                OperationImpact,
                                OperationPriority,
                                ValidationLevel,
                            )

                            characteristics = OperationCharacteristics(
                                operation_type=operation.operation_type,
                                priority=OperationPriority(char_data["priority"]),
                                complexity=OperationComplexity(char_data["complexity"]),
                                impact=OperationImpact(char_data["impact"]),
                                validation_level=ValidationLevel(
                                    char_data["validation_level"]
                                ),
                            )

                        # Process the operation using the processor
                        await self.operation_processor.process_operation(
                            operation, characteristics, self._stats
                        )

                        # Move to completed operations
                        self._completed_operations[operation.operation_id] = operation

                    except Exception as e:
                        logger.error(
                            f"Error processing operation {operation.operation_id}: {e}"
                        )
                        operation.mark_failed(str(e))
                        self._failed_operations[operation.operation_id] = operation
                        self._stats["operations_failed"] += 1

                    finally:
                        # Remove from active operations
                        self._active_operations.pop(operation.operation_id, None)

            except Exception as e:
                logger.error(f"Error in operation processor: {e}")
                await asyncio.sleep(1)  # Brief pause before retrying
