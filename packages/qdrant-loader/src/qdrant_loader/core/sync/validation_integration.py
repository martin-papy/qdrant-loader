"""Validation Integration for Sync Operations.

This module provides integration between the sync system and the validation/repair system,
enabling automatic validation triggers after data ingestion and sync operations.
"""

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ..validation_repair.integrator import ValidationRepairSystemIntegrator
    from ..validation_repair.models import ValidationReport

from ...config.validation import ValidationConfig
from ...utils.logging import LoggingConfig
from .event_system import ChangeEvent, ChangeType, DatabaseType
from .operations import EnhancedSyncOperation
from .types import SyncOperationType

logger = LoggingConfig.get_logger(__name__)


class ValidationIntegrationManager:
    """Manager for integrating validation with sync operations."""

    def __init__(
        self,
        validation_config: ValidationConfig,
        validation_integrator: Optional["ValidationRepairSystemIntegrator"] = None,
    ):
        """Initialize the validation integration manager.

        Args:
            validation_config: Configuration for validation behavior
            validation_integrator: Optional validation integrator instance
        """
        self.config = validation_config
        self.validation_integrator = validation_integrator

        # Track validation operations to prevent duplicate triggers
        self._active_validations: set[str] = set()
        self._validation_history: dict[str, datetime] = {}
        self._validation_semaphore = asyncio.Semaphore(
            self.config.max_concurrent_validations
        )

        # Statistics
        self._stats = {
            "validations_triggered": 0,
            "validations_completed": 0,
            "validations_failed": 0,
            "auto_repairs_triggered": 0,
            "auto_repairs_completed": 0,
        }

    async def trigger_post_ingestion_validation(
        self,
        documents_processed: int,
        project_id: str | None = None,
        source_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Trigger validation after document ingestion.

        Args:
            documents_processed: Number of documents processed
            project_id: Optional project ID
            source_type: Optional source type
            metadata: Optional metadata

        Returns:
            True if validation was triggered successfully
        """
        if (
            not self.config.enable_auto_validation
            or not self.config.enable_post_ingestion_validation
        ):
            logger.debug("Post-ingestion validation disabled")
            return False

        if not self.validation_integrator:
            logger.warning(
                "Validation integrator not available for post-ingestion validation"
            )
            return False

        # Create validation context
        validation_context = {
            "trigger_type": "post_ingestion",
            "documents_processed": documents_processed,
            "project_id": project_id,
            "source_type": source_type,
            "timestamp": datetime.now(UTC).isoformat(),
            **(metadata or {}),
        }

        return await self._trigger_validation_with_delay(
            context=validation_context,
            validation_key=f"ingestion_{project_id}_{source_type}_{datetime.now(UTC).timestamp()}",
        )

    async def trigger_post_sync_validation(
        self,
        operation: EnhancedSyncOperation,
        operation_success: bool = True,
    ) -> bool:
        """Trigger validation after sync operation.

        Args:
            operation: The sync operation that completed
            operation_success: Whether the operation was successful

        Returns:
            True if validation was triggered successfully
        """
        if (
            not self.config.enable_auto_validation
            or not self.config.enable_post_sync_validation
        ):
            logger.debug("Post-sync validation disabled")
            return False

        if not self.validation_integrator:
            logger.warning(
                "Validation integrator not available for post-sync validation"
            )
            return False

        if not operation_success:
            logger.debug(
                f"Skipping validation for failed operation {operation.operation_id}"
            )
            return False

        # Check if we should validate based on operation type
        should_validate = self._should_validate_operation(operation)
        if not should_validate:
            logger.debug(
                f"Skipping validation for operation type {operation.operation_type}"
            )
            return False

        # Create validation context
        validation_context = {
            "trigger_type": "post_sync",
            "operation_id": operation.operation_id,
            "operation_type": operation.operation_type.value,
            "entity_id": operation.entity_id,
            "entity_uuid": operation.entity_uuid,
            "target_databases": [db.value for db in operation.target_databases],
            "timestamp": datetime.now(UTC).isoformat(),
            "operation_metadata": operation.metadata,
        }

        return await self._trigger_validation_with_delay(
            context=validation_context, validation_key=f"sync_{operation.operation_id}"
        )

    async def trigger_change_event_validation(
        self,
        event: ChangeEvent,
    ) -> bool:
        """Trigger validation based on change event.

        Args:
            event: The change event that occurred

        Returns:
            True if validation was triggered successfully
        """
        if not self.config.enable_auto_validation:
            logger.debug("Auto validation disabled")
            return False

        if not self.validation_integrator:
            logger.warning(
                "Validation integrator not available for change event validation"
            )
            return False

        # Check if we should validate based on change type
        should_validate = self._should_validate_change_event(event)
        if not should_validate:
            logger.debug(f"Skipping validation for change type {event.change_type}")
            return False

        # Create validation context
        validation_context = {
            "trigger_type": "change_event",
            "event_id": event.event_id,
            "change_type": event.change_type.value,
            "database_type": event.database_type.value,
            "entity_type": event.entity_type.value,
            "entity_id": event.entity_id,
            "entity_uuid": event.entity_uuid,
            "timestamp": datetime.now(UTC).isoformat(),
            "event_metadata": event.metadata,
        }

        return await self._trigger_validation_with_delay(
            context=validation_context, validation_key=f"event_{event.event_id}"
        )

    async def _trigger_validation_with_delay(
        self,
        context: dict[str, Any],
        validation_key: str,
    ) -> bool:
        """Trigger validation with configured delay and deduplication.

        Args:
            context: Validation context
            validation_key: Unique key for deduplication

        Returns:
            True if validation was triggered successfully
        """
        # Check for duplicate validation
        if validation_key in self._active_validations:
            logger.debug(f"Validation already active for key: {validation_key}")
            return False

        # Add to active validations
        self._active_validations.add(validation_key)

        try:
            # Apply delay if configured
            if self.config.validation_delay_seconds > 0:
                logger.debug(
                    f"Delaying validation by {self.config.validation_delay_seconds}s"
                )
                await asyncio.sleep(self.config.validation_delay_seconds)

            # Trigger validation asynchronously
            asyncio.create_task(
                self._execute_validation_with_retry(context, validation_key)
            )

            self._stats["validations_triggered"] += 1

            if self.config.log_validation_events:
                logger.info(
                    f"Triggered validation for {context.get('trigger_type', 'unknown')}",
                    validation_key=validation_key,
                    context=context,
                )

            return True

        except Exception as e:
            logger.error(f"Error triggering validation: {e}", exc_info=True)
            self._active_validations.discard(validation_key)
            return False

    async def _execute_validation_with_retry(
        self,
        context: dict[str, Any],
        validation_key: str,
    ) -> None:
        """Execute validation with retry logic.

        Args:
            context: Validation context
            validation_key: Unique validation key
        """
        async with self._validation_semaphore:
            retry_count = 0
            last_error = None

            while retry_count <= self.config.max_validation_retries:
                try:
                    # Execute validation
                    await self._execute_validation(context, validation_key)

                    self._stats["validations_completed"] += 1
                    self._validation_history[validation_key] = datetime.now(UTC)

                    if self.config.log_validation_events:
                        logger.info(
                            f"Validation completed successfully",
                            validation_key=validation_key,
                            retry_count=retry_count,
                        )

                    break

                except Exception as e:
                    last_error = e
                    retry_count += 1

                    if retry_count <= self.config.max_validation_retries:
                        logger.warning(
                            f"Validation attempt {retry_count} failed, retrying in {self.config.validation_retry_delay_seconds}s: {e}",
                            validation_key=validation_key,
                        )
                        await asyncio.sleep(self.config.validation_retry_delay_seconds)
                    else:
                        logger.error(
                            f"Validation failed after {retry_count} attempts: {e}",
                            validation_key=validation_key,
                            exc_info=True,
                        )
                        self._stats["validations_failed"] += 1

            # Clean up
            self._active_validations.discard(validation_key)

    async def _execute_validation(
        self,
        context: dict[str, Any],
        validation_key: str,
    ) -> None:
        """Execute the actual validation.

        Args:
            context: Validation context
            validation_key: Unique validation key
        """
        if not self.validation_integrator:
            raise ValueError("Validation integrator not available")

        # Trigger validation
        validation_result = await asyncio.wait_for(
            self.validation_integrator.trigger_validation(
                scanners=None,  # Use default scanners
                auto_repair=self.config.enable_auto_repair,
                metadata=context,
            ),
            timeout=self.config.validation_timeout_seconds,
        )

        # Handle auto-repair if enabled and issues found
        if (
            self.config.enable_auto_repair
            and validation_result
            and validation_result.total_issues > 0
        ):
            await self._trigger_auto_repair(context, validation_key, validation_result)

    async def _trigger_auto_repair(
        self,
        context: dict[str, Any],
        validation_key: str,
        validation_result: "ValidationReport",
    ) -> None:
        """Trigger automatic repair if enabled.

        Args:
            context: Validation context
            validation_key: Unique validation key
            validation_result: Result from validation
        """
        try:
            self._stats["auto_repairs_triggered"] += 1

            logger.info(
                f"Triggering auto-repair for validation issues",
                validation_key=validation_key,
                issues_found=validation_result.total_issues,
            )

            if not self.validation_integrator:
                raise ValueError("Validation integrator not available for repair")

            repair_results = await asyncio.wait_for(
                self.validation_integrator.repair_issues(
                    issues=validation_result.issues,
                    max_repairs=self.config.auto_repair_max_attempts,
                    metadata=context,
                ),
                timeout=self.config.auto_repair_timeout_seconds,
            )

            if repair_results:
                successful_repairs = sum(1 for r in repair_results if r.success)
                if successful_repairs > 0:
                    self._stats["auto_repairs_completed"] += 1
                    logger.info(
                        f"Auto-repair completed successfully",
                        validation_key=validation_key,
                        repairs_successful=successful_repairs,
                    )

        except Exception as e:
            logger.error(
                f"Auto-repair failed: {e}", validation_key=validation_key, exc_info=True
            )

    def _should_validate_operation(self, operation: EnhancedSyncOperation) -> bool:
        """Check if validation should be triggered for the operation.

        Args:
            operation: The sync operation

        Returns:
            True if validation should be triggered
        """
        # Check document operations
        if operation.operation_type in [
            SyncOperationType.CREATE_DOCUMENT,
            SyncOperationType.UPDATE_DOCUMENT,
            SyncOperationType.DELETE_DOCUMENT,
        ]:
            return self.config.validate_after_document_operations

        # Check entity operations
        if operation.operation_type in [
            SyncOperationType.CREATE_ENTITY,
            SyncOperationType.UPDATE_ENTITY,
            SyncOperationType.DELETE_ENTITY,
        ]:
            return self.config.validate_after_entity_operations

        # Check bulk operations
        if operation.operation_type in [
            SyncOperationType.CASCADE_DELETE,
            SyncOperationType.VERSION_UPDATE,
        ]:
            return self.config.validate_after_bulk_operations

        return True  # Default to validating unknown operation types

    def _should_validate_change_event(self, event: ChangeEvent) -> bool:
        """Check if validation should be triggered for the change event.

        Args:
            event: The change event

        Returns:
            True if validation should be triggered
        """
        # Check bulk operations
        if event.change_type in [
            ChangeType.BULK_CREATE,
            ChangeType.BULK_UPDATE,
            ChangeType.BULK_DELETE,
        ]:
            return self.config.validate_after_bulk_operations

        # Check regular operations (treat as document/entity operations)
        return (
            self.config.validate_after_document_operations
            or self.config.validate_after_entity_operations
        )

    def get_statistics(self) -> dict[str, Any]:
        """Get validation integration statistics.

        Returns:
            Dictionary containing statistics
        """
        return {
            **self._stats,
            "active_validations": len(self._active_validations),
            "validation_history_count": len(self._validation_history),
            "config": {
                "auto_validation_enabled": self.config.enable_auto_validation,
                "post_ingestion_enabled": self.config.enable_post_ingestion_validation,
                "post_sync_enabled": self.config.enable_post_sync_validation,
                "auto_repair_enabled": self.config.enable_auto_repair,
                "max_concurrent_validations": self.config.max_concurrent_validations,
            },
        }

    async def cleanup(self) -> None:
        """Clean up resources and cancel active validations."""
        logger.info("Cleaning up validation integration manager")

        # Wait for active validations to complete (with timeout)
        if self._active_validations:
            logger.info(
                f"Waiting for {len(self._active_validations)} active validations to complete"
            )

            # Wait up to 30 seconds for validations to complete
            timeout = 30
            start_time = datetime.now(UTC)

            while (
                self._active_validations
                and (datetime.now(UTC) - start_time).total_seconds() < timeout
            ):
                await asyncio.sleep(1)

            if self._active_validations:
                logger.warning(
                    f"Timed out waiting for {len(self._active_validations)} validations to complete"
                )

        logger.info("Validation integration manager cleanup completed")
