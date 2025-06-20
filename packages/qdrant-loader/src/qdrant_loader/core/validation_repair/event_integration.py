"""Event System Integration for Validation Operations.

This module provides comprehensive integration between the validation/repair system
and the sync event system, enabling automatic validation triggers and event-driven
validation workflows.
"""

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from ..sync.enhanced_event_system import EnhancedSyncEventSystem
    from ..sync.event_system import SyncEventSystem
    from .integrator import ValidationRepairSystemIntegrator

from ...utils.logging import LoggingConfig
from ..sync.event_system import ChangeEvent, ChangeType, DatabaseType
from ..types import EntityType
from .metrics import ValidationMetricsCollector
from .models import ValidationReport

logger = LoggingConfig.get_logger(__name__)


class ValidationEventIntegrator:
    """Integrates validation operations with the sync event system."""

    def __init__(
        self,
        validation_integrator: "ValidationRepairSystemIntegrator",
        sync_event_system: Optional["SyncEventSystem"] = None,
        enhanced_sync_system: Optional["EnhancedSyncEventSystem"] = None,
        metrics_collector: Optional[ValidationMetricsCollector] = None,
        auto_validation_enabled: bool = True,
        validation_delay_seconds: float = 5.0,
        batch_validation_threshold: int = 10,
    ):
        """Initialize the validation event integrator.

        Args:
            validation_integrator: ValidationRepairSystemIntegrator instance
            sync_event_system: Base sync event system for event subscription
            enhanced_sync_system: Enhanced sync event system for advanced features
            metrics_collector: Metrics collector for validation operations
            auto_validation_enabled: Whether to enable automatic validation triggers
            validation_delay_seconds: Delay before triggering validation after events
            batch_validation_threshold: Number of events to batch before validation
        """
        self.validation_integrator = validation_integrator
        self.sync_event_system = sync_event_system
        self.enhanced_sync_system = enhanced_sync_system
        self.metrics_collector = metrics_collector
        self.auto_validation_enabled = auto_validation_enabled
        self.validation_delay_seconds = validation_delay_seconds
        self.batch_validation_threshold = batch_validation_threshold

        # Event tracking
        self._pending_events: list[ChangeEvent] = []
        self._event_handlers: dict[str, list[Callable]] = {}
        self._validation_triggers: dict[str, datetime] = {}
        self._batch_validation_timer: Optional[asyncio.Task] = None

        # Integration state
        self._initialized = False
        self._running = False

        # Statistics
        self._stats = {
            "events_received": 0,
            "validations_triggered": 0,
            "auto_validations": 0,
            "manual_validations": 0,
            "batch_validations": 0,
            "validation_events_emitted": 0,
        }

        logger.info("ValidationEventIntegrator initialized")

    async def initialize(self) -> None:
        """Initialize the event integrator and set up event subscriptions."""
        if self._initialized:
            logger.warning("ValidationEventIntegrator already initialized")
            return

        try:
            # Set up event system subscriptions
            await self._setup_event_subscriptions()

            # Set up validation event handlers
            await self._setup_validation_event_handlers()

            self._initialized = True
            logger.info("ValidationEventIntegrator initialization completed")

        except Exception as e:
            logger.error(f"Failed to initialize ValidationEventIntegrator: {e}")
            raise

    async def start(self) -> None:
        """Start the event integrator."""
        if not self._initialized:
            await self.initialize()

        if self._running:
            logger.warning("ValidationEventIntegrator already running")
            return

        self._running = True
        logger.info("ValidationEventIntegrator started")

    async def stop(self) -> None:
        """Stop the event integrator."""
        if not self._running:
            return

        self._running = False

        # Cancel batch validation timer
        if self._batch_validation_timer:
            self._batch_validation_timer.cancel()
            try:
                await self._batch_validation_timer
            except asyncio.CancelledError:
                pass
            self._batch_validation_timer = None

        logger.info("ValidationEventIntegrator stopped")

    async def _setup_event_subscriptions(self) -> None:
        """Set up subscriptions to sync events that should trigger validation."""
        if not self.auto_validation_enabled:
            logger.info("Auto validation disabled, skipping event subscriptions")
            return

        # Subscribe to base sync event system
        if self.sync_event_system:
            # Subscribe to data ingestion events
            self.sync_event_system.add_event_handler(
                "qdrant.create", self._on_data_ingested
            )
            self.sync_event_system.add_event_handler(
                "qdrant.update", self._on_data_ingested
            )

            # Subscribe to entity extraction events
            self.sync_event_system.add_event_handler(
                "neo4j.create", self._on_entity_extracted
            )
            self.sync_event_system.add_event_handler(
                "neo4j.update", self._on_entity_extracted
            )

            logger.info("Subscribed to base sync event system")

        # Subscribe to enhanced sync event system
        if self.enhanced_sync_system:
            # Get the base sync event system for event subscriptions
            base_sync_system = self.enhanced_sync_system.base_sync_system
            if base_sync_system:
                # Subscribe to data ingestion events
                base_sync_system.add_event_handler(
                    "qdrant.create", self._on_data_ingested
                )
                base_sync_system.add_event_handler(
                    "qdrant.update", self._on_data_ingested
                )

                # Subscribe to entity extraction events
                base_sync_system.add_event_handler(
                    "neo4j.create", self._on_entity_extracted
                )
                base_sync_system.add_event_handler(
                    "neo4j.update", self._on_entity_extracted
                )

                logger.info("Subscribed to enhanced sync system's base event system")
            else:
                logger.warning(
                    "Enhanced sync system has no base sync system for event integration"
                )

            # The enhanced system will automatically trigger validation through
            # the ValidationIntegrationManager, so we mainly listen for completion events
            logger.info("Enhanced sync system integration available")

    async def _setup_validation_event_handlers(self) -> None:
        """Set up handlers for validation events from the integrator."""
        if not self.validation_integrator:
            return

        # Add event handlers to the validation integrator
        self.validation_integrator.add_event_handler(
            "validation_started", self._on_validation_started
        )
        self.validation_integrator.add_event_handler(
            "validation_completed", self._on_validation_completed
        )
        self.validation_integrator.add_event_handler(
            "validation_failed", self._on_validation_failed
        )
        self.validation_integrator.add_event_handler(
            "repair_started", self._on_repair_started
        )
        self.validation_integrator.add_event_handler(
            "repair_completed", self._on_repair_completed
        )
        self.validation_integrator.add_event_handler(
            "repair_failed", self._on_repair_failed
        )

        logger.info("Validation event handlers configured")

    # Event handlers for sync events

    def _on_data_ingested(self, event: ChangeEvent) -> None:
        """Handle data ingestion events."""
        if not self._running or not self.auto_validation_enabled:
            return

        logger.debug(f"Data ingested event received: {event.event_id}")
        self._stats["events_received"] += 1

        # Add to pending events for batch processing
        self._pending_events.append(event)

        # Trigger validation if threshold reached or start timer
        asyncio.create_task(self._handle_pending_validation())

    def _on_entity_extracted(self, event: ChangeEvent) -> None:
        """Handle entity extraction events."""
        if not self._running or not self.auto_validation_enabled:
            return

        logger.debug(f"Entity extracted event received: {event.event_id}")
        self._stats["events_received"] += 1

        # Add to pending events for batch processing
        self._pending_events.append(event)

        # Trigger validation if threshold reached or start timer
        asyncio.create_task(self._handle_pending_validation())

    async def _handle_pending_validation(self) -> None:
        """Handle pending validation based on batch threshold or timer."""
        if len(self._pending_events) >= self.batch_validation_threshold:
            # Trigger immediate batch validation
            await self._trigger_batch_validation()
        elif not self._batch_validation_timer:
            # Start timer for delayed validation
            self._batch_validation_timer = asyncio.create_task(
                self._delayed_validation_trigger()
            )

    async def _delayed_validation_trigger(self) -> None:
        """Trigger validation after delay."""
        try:
            await asyncio.sleep(self.validation_delay_seconds)
            await self._trigger_batch_validation()
        except asyncio.CancelledError:
            logger.debug("Delayed validation trigger cancelled")
        finally:
            self._batch_validation_timer = None

    async def _trigger_batch_validation(self) -> None:
        """Trigger validation for batched events."""
        if not self._pending_events:
            return

        try:
            # Cancel existing timer
            if self._batch_validation_timer:
                self._batch_validation_timer.cancel()
                self._batch_validation_timer = None

            # Get events to process
            events_to_process = self._pending_events.copy()
            self._pending_events.clear()

            logger.info(
                f"Triggering batch validation for {len(events_to_process)} events"
            )

            # Determine validation context from events
            validation_context = self._create_validation_context(events_to_process)

            # Trigger validation
            await self.validation_integrator.trigger_validation(
                validation_id=f"batch_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
                metadata=validation_context,
                auto_repair=True,  # Enable auto-repair for batch validations
            )

            self._stats["validations_triggered"] += 1
            self._stats["auto_validations"] += 1
            self._stats["batch_validations"] += 1

        except Exception as e:
            logger.error(f"Error triggering batch validation: {e}")

    def _create_validation_context(self, events: list[ChangeEvent]) -> dict[str, Any]:
        """Create validation context from events."""
        context = {
            "trigger_type": "batch_events",
            "event_count": len(events),
            "event_types": list(
                set(f"{e.database_type.value}.{e.change_type.value}" for e in events)
            ),
            "entity_types": list(set(e.entity_type.value for e in events)),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Add database-specific context
        qdrant_events = [e for e in events if e.database_type == DatabaseType.QDRANT]
        neo4j_events = [e for e in events if e.database_type == DatabaseType.NEO4J]

        if qdrant_events:
            context["qdrant_events"] = {
                "count": len(qdrant_events),
                "entity_ids": [e.entity_id for e in qdrant_events if e.entity_id],
            }

        if neo4j_events:
            context["neo4j_events"] = {
                "count": len(neo4j_events),
                "entity_ids": [e.entity_id for e in neo4j_events if e.entity_id],
            }

        return context

    # Event handlers for validation events

    async def _on_validation_started(self, event_data: dict[str, Any]) -> None:
        """Handle validation started events."""
        validation_id = event_data.get("validation_id")
        scanners = event_data.get("scanners", [])
        metadata = event_data.get("metadata", {})

        logger.info(f"Validation started: {validation_id}")
        self._stats["validation_events_emitted"] += 1

        # Record metrics if collector available
        if self.metrics_collector and validation_id and isinstance(validation_id, str):
            self.metrics_collector.record_validation_started(
                validation_id=validation_id,
                scanners=scanners,
                metadata=metadata,
            )

        # Emit custom event handlers
        await self._emit_custom_event("validation_started", event_data)

    async def _on_validation_completed(self, event_data: dict[str, Any]) -> None:
        """Handle validation completed events."""
        validation_id = event_data.get("validation_id")
        report = event_data.get("report")
        metadata = event_data.get("metadata", {})

        logger.info(f"Validation completed: {validation_id}")
        self._stats["validation_events_emitted"] += 1

        # Calculate duration if possible
        duration_seconds = 0.0
        if isinstance(report, ValidationReport):
            duration_seconds = getattr(report, "duration_seconds", 0.0)

        # Record metrics if collector available
        if (
            self.metrics_collector
            and validation_id
            and isinstance(validation_id, str)
            and report
            and isinstance(report, ValidationReport)
        ):
            self.metrics_collector.record_validation_completed(
                validation_id=validation_id,
                report=report,
                duration_seconds=duration_seconds,
                success=True,
            )

        # Emit custom event handlers
        await self._emit_custom_event("validation_completed", event_data)

    async def _on_validation_failed(self, event_data: dict[str, Any]) -> None:
        """Handle validation failed events."""
        validation_id = event_data.get("validation_id")
        error = event_data.get("error", "Unknown error")
        metadata = event_data.get("metadata", {})

        logger.warning(f"Validation failed: {validation_id} - {error}")
        self._stats["validation_events_emitted"] += 1

        # Record metrics if collector available
        if self.metrics_collector and validation_id and isinstance(validation_id, str):
            self.metrics_collector.record_validation_failed(
                validation_id=validation_id,
                error=error,
                duration_seconds=0.0,  # Duration not available for failed validations
            )

        # Emit custom event handlers
        await self._emit_custom_event("validation_failed", event_data)

    async def _on_repair_started(self, event_data: dict[str, Any]) -> None:
        """Handle repair started events."""
        repair_id = event_data.get("repair_id")
        issue_count = event_data.get("issue_count", 0)
        metadata = event_data.get("metadata", {})

        logger.info(f"Repair started: {repair_id} ({issue_count} issues)")
        self._stats["validation_events_emitted"] += 1

        # Record metrics if collector available
        if self.metrics_collector and repair_id and isinstance(repair_id, str):
            # Note: We don't have the actual issues list here, so we create a placeholder
            self.metrics_collector.record_repair_started(
                repair_id=repair_id,
                issues=[],  # Issues not available in event data
                metadata=metadata,
            )

        # Emit custom event handlers
        await self._emit_custom_event("repair_started", event_data)

    async def _on_repair_completed(self, event_data: dict[str, Any]) -> None:
        """Handle repair completed events."""
        repair_id = event_data.get("repair_id")
        repair_results = event_data.get("repair_results", [])
        successful_repairs = event_data.get("successful_repairs", 0)
        metadata = event_data.get("metadata", {})

        logger.info(f"Repair completed: {repair_id} ({successful_repairs} successful)")
        self._stats["validation_events_emitted"] += 1

        # Record metrics if collector available
        if self.metrics_collector and repair_id and isinstance(repair_id, str):
            self.metrics_collector.record_repair_completed(
                repair_id=repair_id,
                results=repair_results,
                duration_seconds=0.0,  # Duration not available in event data
            )

        # Emit custom event handlers
        await self._emit_custom_event("repair_completed", event_data)

    async def _on_repair_failed(self, event_data: dict[str, Any]) -> None:
        """Handle repair failed events."""
        repair_id = event_data.get("repair_id")
        error = event_data.get("error", "Unknown error")
        metadata = event_data.get("metadata", {})

        logger.warning(f"Repair failed: {repair_id} - {error}")
        self._stats["validation_events_emitted"] += 1

        # Record metrics if collector available
        if self.metrics_collector and repair_id and isinstance(repair_id, str):
            self.metrics_collector.record_repair_failed(
                repair_id=repair_id,
                error=error,
                duration_seconds=0.0,  # Duration not available for failed repairs
            )

        # Emit custom event handlers
        await self._emit_custom_event("repair_failed", event_data)

    # Custom event handling

    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """Add a custom event handler.

        Args:
            event_type: Type of event to handle
            handler: Async callable to handle the event
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []

        self._event_handlers[event_type].append(handler)
        logger.debug(f"Added custom event handler for {event_type}")

    def remove_event_handler(self, event_type: str, handler: Callable) -> None:
        """Remove a custom event handler.

        Args:
            event_type: Type of event
            handler: Handler to remove
        """
        if event_type in self._event_handlers:
            try:
                self._event_handlers[event_type].remove(handler)
                logger.debug(f"Removed custom event handler for {event_type}")
            except ValueError:
                logger.warning(f"Handler not found for event type {event_type}")

    async def _emit_custom_event(
        self, event_type: str, event_data: dict[str, Any]
    ) -> None:
        """Emit event to custom handlers.

        Args:
            event_type: Type of event to emit
            event_data: Event data to pass to handlers
        """
        if event_type not in self._event_handlers:
            return

        handlers = self._event_handlers[event_type].copy()

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_data)
                else:
                    handler(event_data)
            except Exception as e:
                logger.error(f"Custom event handler failed for {event_type}: {e}")

    # Manual validation triggers

    async def trigger_manual_validation(
        self,
        validation_id: Optional[str] = None,
        scanners: Optional[list[str]] = None,
        auto_repair: bool = False,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ValidationReport:
        """Trigger a manual validation operation.

        Args:
            validation_id: Optional validation ID
            scanners: Optional list of scanners to use
            auto_repair: Whether to enable auto-repair
            metadata: Optional metadata for the validation

        Returns:
            ValidationReport from the validation operation
        """
        if not self.validation_integrator:
            raise RuntimeError("ValidationRepairSystemIntegrator not available")

        # Generate validation ID if not provided
        if validation_id is None:
            validation_id = f"manual_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

        # Add manual trigger context
        if metadata is None:
            metadata = {}
        metadata.update(
            {
                "trigger_type": "manual",
                "triggered_by": "ValidationEventIntegrator",
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        logger.info(f"Triggering manual validation: {validation_id}")

        try:
            report = await self.validation_integrator.trigger_validation(
                validation_id=validation_id,
                scanners=scanners,
                auto_repair=auto_repair,
                metadata=metadata,
            )

            self._stats["validations_triggered"] += 1
            self._stats["manual_validations"] += 1

            return report

        except Exception as e:
            logger.error(f"Manual validation failed: {e}")
            raise

    # Statistics and monitoring

    def get_integration_statistics(self) -> dict[str, Any]:
        """Get integration statistics.

        Returns:
            Dictionary containing integration statistics
        """
        stats: dict[str, Any] = self._stats.copy()
        stats.update(
            {
                "initialized": self._initialized,
                "running": self._running,
                "pending_events": len(self._pending_events),
                "custom_handlers": sum(
                    len(handlers) for handlers in self._event_handlers.values()
                ),
                "auto_validation_enabled": self.auto_validation_enabled,
                "batch_threshold": self.batch_validation_threshold,
                "validation_delay": self.validation_delay_seconds,
            }
        )

        return stats

    def get_pending_events_summary(self) -> dict[str, Any]:
        """Get summary of pending events.

        Returns:
            Dictionary containing pending events summary
        """
        if not self._pending_events:
            return {"count": 0, "events": []}

        summary = {
            "count": len(self._pending_events),
            "database_types": {},
            "change_types": {},
            "entity_types": {},
            "oldest_event": None,
            "newest_event": None,
        }

        # Analyze pending events
        timestamps = []
        for event in self._pending_events:
            # Count by database type
            db_type = event.database_type.value
            summary["database_types"][db_type] = (
                summary["database_types"].get(db_type, 0) + 1
            )

            # Count by change type
            change_type = event.change_type.value
            summary["change_types"][change_type] = (
                summary["change_types"].get(change_type, 0) + 1
            )

            # Count by entity type
            entity_type = event.entity_type.value
            summary["entity_types"][entity_type] = (
                summary["entity_types"].get(entity_type, 0) + 1
            )

            timestamps.append(event.timestamp)

        if timestamps:
            summary["oldest_event"] = min(timestamps).isoformat()
            summary["newest_event"] = max(timestamps).isoformat()

        return summary

    async def force_validation_trigger(self) -> None:
        """Force immediate validation of pending events."""
        if self._pending_events:
            logger.info("Forcing immediate validation trigger")
            await self._trigger_batch_validation()
        else:
            logger.info("No pending events to validate")

    async def clear_pending_events(self) -> int:
        """Clear all pending events without triggering validation.

        Returns:
            Number of events that were cleared
        """
        count = len(self._pending_events)
        self._pending_events.clear()

        if self._batch_validation_timer:
            self._batch_validation_timer.cancel()
            self._batch_validation_timer = None

        logger.info(f"Cleared {count} pending events")
        return count
