"""Operation Processor for Enhanced Sync Event System.

This module contains the operation processing logic, extracted from the main
enhanced sync event system for better maintainability and separation of concerns.
"""

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..graphiti_temporal_integration import GraphitiTemporalIntegration
    from ..operation_differentiation import (
        OperationCharacteristics,
        OperationDifferentiationManager,
    )
    from .conflict_monitor import SyncConflictMonitor

from ...utils.logging import LoggingConfig
from ..atomic_transactions import AtomicTransactionManager
from .handlers import SyncOperationHandlers
from .operations import EnhancedSyncOperation
from .types import SyncOperationStatus, SyncOperationType

logger = LoggingConfig.get_logger(__name__)


class SyncOperationProcessor:
    """Processor for handling sync operations with intelligent prioritization."""

    def __init__(
        self,
        atomic_transaction_manager: AtomicTransactionManager,
        operation_handlers: SyncOperationHandlers,
        operation_differentiation_manager: Optional[
            "OperationDifferentiationManager"
        ] = None,
        graphiti_temporal_integration: Optional["GraphitiTemporalIntegration"] = None,
        sync_conflict_monitor: Optional["SyncConflictMonitor"] = None,
        operation_timeout_seconds: int = 300,
        enable_operation_differentiation: bool = True,
        enable_graphiti_temporal_features: bool = True,
    ):
        """Initialize the operation processor.

        Args:
            atomic_transaction_manager: Atomic transaction manager instance
            operation_handlers: Operation handlers instance
            operation_differentiation_manager: Optional operation differentiation manager
            graphiti_temporal_integration: Optional Graphiti temporal integration
            sync_conflict_monitor: Optional sync conflict monitor
            operation_timeout_seconds: Timeout for sync operations
            enable_operation_differentiation: Whether to enable intelligent operation differentiation
            enable_graphiti_temporal_features: Whether to enable Graphiti temporal features
        """
        self.atomic_transaction_manager = atomic_transaction_manager
        self.operation_handlers = operation_handlers
        self.operation_differentiation_manager = operation_differentiation_manager
        self.graphiti_temporal_integration = graphiti_temporal_integration
        self.sync_conflict_monitor = sync_conflict_monitor
        self.operation_timeout_seconds = operation_timeout_seconds
        self.enable_operation_differentiation = enable_operation_differentiation
        self.enable_graphiti_temporal_features = enable_graphiti_temporal_features

        # Operation handler mapping
        self._operation_handler_map = {
            SyncOperationType.CREATE_DOCUMENT: self.operation_handlers.handle_create_document,
            SyncOperationType.UPDATE_DOCUMENT: self.operation_handlers.handle_update_document,
            SyncOperationType.DELETE_DOCUMENT: self.operation_handlers.handle_delete_document,
            SyncOperationType.CREATE_ENTITY: self.operation_handlers.handle_create_entity,
            SyncOperationType.UPDATE_ENTITY: self.operation_handlers.handle_update_entity,
            SyncOperationType.DELETE_ENTITY: self.operation_handlers.handle_delete_entity,
            SyncOperationType.CASCADE_DELETE: self.operation_handlers.handle_cascade_delete,
            SyncOperationType.VERSION_UPDATE: self.operation_handlers.handle_version_update,
        }

    async def process_operation(
        self,
        operation: EnhancedSyncOperation,
        characteristics: Optional["OperationCharacteristics"] = None,
        stats: dict[str, int] | None = None,
    ) -> None:
        """Process a single sync operation.

        Args:
            operation: The sync operation to process
            characteristics: Optional operation characteristics from differentiation manager
            stats: Optional statistics dictionary to update
        """
        operation_id = operation.operation_id

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
            handler = self._operation_handler_map.get(operation.operation_type)
            if not handler:
                raise ValueError(
                    f"No handler for operation type: {operation.operation_type}"
                )

            # Process operation with timeout using atomic transaction
            async with self.atomic_transaction_manager.transaction() as tx:
                await asyncio.wait_for(
                    handler(tx, operation), timeout=self.operation_timeout_seconds
                )

            # Mark as completed
            operation.mark_completed()

            # Update statistics if provided
            if stats:
                stats["operations_processed"] += 1
                self._update_operation_type_stats(stats, operation.operation_type)

            logger.info(f"Completed operation {operation_id}")

        except Exception as e:
            logger.error(f"Error processing operation {operation_id}: {e}")
            operation.mark_failed(str(e))

            # Update statistics if provided
            if stats:
                stats["operations_failed"] += 1

        finally:
            # Complete operation in differentiation manager if enabled
            if (
                self.enable_operation_differentiation
                and self.operation_differentiation_manager
                and characteristics
            ):
                try:
                    # Calculate processing duration
                    processing_duration = (
                        datetime.now(UTC) - operation.timestamp
                    ).total_seconds()

                    # Report completion to differentiation manager
                    await self.operation_differentiation_manager.complete_operation(
                        operation_id,
                        success=(operation.status == SyncOperationStatus.COMPLETED),
                        duration=processing_duration,
                    )

                    logger.debug(
                        f"Reported operation {operation_id} completion to differentiation manager "
                        f"(success: {operation.status == SyncOperationStatus.COMPLETED}, duration: {processing_duration:.2f}s)"
                    )
                except Exception as e:
                    logger.warning(
                        f"Error reporting operation completion to differentiation manager: {e}"
                    )

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

    async def process_operation_with_priority(
        self,
        operation: EnhancedSyncOperation,
        characteristics: Optional["OperationCharacteristics"] = None,
        stats: dict[str, int] | None = None,
    ) -> None:
        """Process operation with intelligent priority handling.

        This method includes additional logic for priority-based processing
        and enhanced error handling for high-priority operations.

        Args:
            operation: The sync operation to process
            characteristics: Operation characteristics from differentiation manager
            stats: Optional statistics dictionary to update
        """
        if characteristics:
            # Log priority information
            logger.info(
                f"Processing priority operation {operation.operation_id} "
                f"(priority: {characteristics.priority.value}, "
                f"complexity: {characteristics.complexity.value}, "
                f"impact: {characteristics.impact.value}, "
                f"score: {characteristics.calculate_priority_score():.1f})"
            )

            # Store characteristics in operation metadata for tracking
            operation.metadata.update(
                {
                    "processing_characteristics": {
                        "priority": characteristics.priority.value,
                        "complexity": characteristics.complexity.value,
                        "impact": characteristics.impact.value,
                        "priority_score": characteristics.calculate_priority_score(),
                        "validation_level": characteristics.validation_level.value,
                    }
                }
            )

        # Process the operation
        await self.process_operation(operation, characteristics, stats)

    def _update_operation_type_stats(
        self, stats: dict[str, int], operation_type: SyncOperationType
    ) -> None:
        """Update statistics based on operation type."""
        if operation_type in [
            SyncOperationType.CREATE_DOCUMENT,
            SyncOperationType.CREATE_ENTITY,
        ]:
            stats["create_operations"] += 1
        elif operation_type in [
            SyncOperationType.UPDATE_DOCUMENT,
            SyncOperationType.UPDATE_ENTITY,
        ]:
            stats["update_operations"] += 1
        elif operation_type in [
            SyncOperationType.DELETE_DOCUMENT,
            SyncOperationType.DELETE_ENTITY,
        ]:
            stats["delete_operations"] += 1
        elif operation_type == SyncOperationType.CASCADE_DELETE:
            stats["cascade_operations"] += 1
        elif operation_type == SyncOperationType.VERSION_UPDATE:
            stats["version_operations"] += 1
