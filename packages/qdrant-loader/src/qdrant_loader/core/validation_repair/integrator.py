"""ValidationRepairSystem Integration Orchestrator.

This module provides the central ValidationRepairSystemIntegrator class that coordinates
validation operations across all application layers, serving as the main entry point
for validation workflows and integration with other system components.
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .metrics import ValidationMetricsCollector
    from .event_integration import ValidationEventIntegrator

from ...config import Settings
from ...utils.logging import LoggingConfig
from ..managers import IDMappingManager, Neo4jManager, QdrantManager
from ..sync.enhanced_event_system import EnhancedSyncEventSystem
from .models import ValidationReport, ValidationIssue, RepairResult
from .system import ValidationRepairSystem

logger = LoggingConfig.get_logger(__name__)


class ValidationRepairSystemIntegrator:
    """Central orchestrator for ValidationRepairSystem integration across application layers.

    This class serves as the main entry point for validation operations and coordinates
    between different components including the validation system, event system,
    configuration management, and monitoring.
    """

    def __init__(
        self,
        validation_repair_system: ValidationRepairSystem,
        settings: Settings,
        enhanced_sync_system: Optional[EnhancedSyncEventSystem] = None,
        metrics_collector: Optional["ValidationMetricsCollector"] = None,
        event_integrator: Optional["ValidationEventIntegrator"] = None,
        auto_validation_enabled: bool = True,
        validation_on_ingestion: bool = True,
        validation_on_extraction: bool = True,
        validation_batch_size: int = 1000,
        validation_timeout_seconds: int = 300,
    ):
        """Initialize the ValidationRepairSystemIntegrator.

        Args:
            validation_repair_system: The core validation and repair system
            settings: Application settings for configuration access
            enhanced_sync_system: Optional enhanced sync event system for event integration
            metrics_collector: Optional metrics collector for validation operations
            event_integrator: Optional event integrator for validation events
            auto_validation_enabled: Whether automatic validation is enabled
            validation_on_ingestion: Whether to validate after data ingestion
            validation_on_extraction: Whether to validate after entity extraction
            validation_batch_size: Batch size for validation operations
            validation_timeout_seconds: Timeout for validation operations
        """
        self.validation_repair_system = validation_repair_system
        self.settings = settings
        self.enhanced_sync_system = enhanced_sync_system
        self.metrics_collector = metrics_collector
        self.event_integrator = event_integrator
        self.auto_validation_enabled = auto_validation_enabled
        self.validation_on_ingestion = validation_on_ingestion
        self.validation_on_extraction = validation_on_extraction
        self.validation_batch_size = validation_batch_size
        self.validation_timeout_seconds = validation_timeout_seconds

        # Event handlers registry
        self._event_handlers: dict[str, list] = {
            "validation_started": [],
            "validation_completed": [],
            "validation_failed": [],
            "repair_started": [],
            "repair_completed": [],
            "repair_failed": [],
        }

        # Validation state tracking
        self._active_validations: dict[str, dict] = {}
        self._validation_history: list[dict] = []
        self._last_validation_report: Optional[ValidationReport] = None

        # Statistics
        self._stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "total_repairs": 0,
            "successful_repairs": 0,
            "failed_repairs": 0,
            "auto_repairs_performed": 0,
            "manual_repairs_performed": 0,
        }

        # Integration state
        self._initialized = False
        self._running = False

        logger.info("ValidationRepairSystemIntegrator initialized")

    async def initialize(self) -> None:
        """Initialize the integrator and set up event system integration."""
        if self._initialized:
            logger.warning("ValidationRepairSystemIntegrator already initialized")
            return

        try:
            # Set up event system integration if available
            if self.enhanced_sync_system:
                await self._setup_event_system_integration()

            # Initialize event integrator if available
            if self.event_integrator:
                await self.event_integrator.initialize()

            self._initialized = True
            logger.info("ValidationRepairSystemIntegrator initialization completed")

        except Exception as e:
            logger.error(f"Failed to initialize ValidationRepairSystemIntegrator: {e}")
            raise

    async def start(self) -> None:
        """Start the integrator and begin monitoring for validation triggers."""
        if not self._initialized:
            await self.initialize()

        if self._running:
            logger.warning("ValidationRepairSystemIntegrator already running")
            return

        # Start event integrator if available
        if self.event_integrator:
            await self.event_integrator.start()

        self._running = True
        logger.info("ValidationRepairSystemIntegrator started")

    async def stop(self) -> None:
        """Stop the integrator and clean up resources."""
        if not self._running:
            return

        # Cancel any active validations
        for validation_id in list(self._active_validations.keys()):
            await self._cancel_validation(validation_id)

        # Stop event integrator if available
        if self.event_integrator:
            await self.event_integrator.stop()

        self._running = False
        logger.info("ValidationRepairSystemIntegrator stopped")

    async def trigger_validation(
        self,
        validation_id: Optional[str] = None,
        scanners: Optional[list[str]] = None,
        max_entities_per_scanner: Optional[int] = None,
        auto_repair: bool = False,
        metadata: Optional[dict] = None,
    ) -> ValidationReport:
        """Trigger a validation operation.

        Args:
            validation_id: Optional unique identifier for this validation
            scanners: List of specific scanners to run
            max_entities_per_scanner: Maximum entities to scan per scanner
            auto_repair: Whether to automatically repair found issues
            metadata: Additional metadata for the validation

        Returns:
            ValidationReport with validation results
        """
        if not self._running:
            raise RuntimeError("ValidationRepairSystemIntegrator not running")

        # Generate validation ID if not provided
        if validation_id is None:
            validation_id = f"validation_{datetime.now(UTC).isoformat()}_{id(self)}"

        # Check if validation is already running
        if validation_id in self._active_validations:
            raise ValueError(f"Validation {validation_id} is already running")

        logger.info(f"Starting validation {validation_id}")

        # Track validation start
        validation_context = {
            "validation_id": validation_id,
            "start_time": datetime.now(UTC),
            "scanners": scanners,
            "max_entities_per_scanner": max_entities_per_scanner,
            "auto_repair": auto_repair,
            "metadata": metadata or {},
            "status": "running",
        }
        self._active_validations[validation_id] = validation_context

        try:
            # Record validation start in metrics collector
            if self.metrics_collector:
                self.metrics_collector.record_validation_started(
                    validation_id=validation_id,
                    scanners=scanners or [],
                    metadata=metadata,
                )

            # Emit validation started event
            await self._emit_event(
                "validation_started",
                {
                    "validation_id": validation_id,
                    "scanners": scanners,
                    "metadata": metadata,
                },
            )

            # Run the validation
            report = await asyncio.wait_for(
                self.validation_repair_system.run_full_validation(
                    scanners=scanners,
                    max_entities_per_scanner=max_entities_per_scanner,
                ),
                timeout=self.validation_timeout_seconds,
            )

            # Update validation context
            validation_context["end_time"] = datetime.now(UTC)
            validation_context["status"] = "completed"
            validation_context["report"] = report

            # Store the report
            self._last_validation_report = report

            # Update statistics
            self._stats["total_validations"] += 1
            self._stats["successful_validations"] += 1

            # Record validation completion in metrics collector
            if self.metrics_collector:
                duration = (
                    datetime.now(UTC) - validation_context["start_time"]
                ).total_seconds()
                self.metrics_collector.record_validation_completed(
                    validation_id=validation_id,
                    report=report,
                    duration_seconds=duration,
                    success=True,
                )

            # Perform auto-repair if requested and issues found
            repair_results = []
            if auto_repair and report.issues:
                logger.info(f"Auto-repair requested for {len(report.issues)} issues")
                repair_results = await self._perform_auto_repair(
                    validation_id, report.issues
                )
                validation_context["repair_results"] = repair_results

            # Emit validation completed event
            await self._emit_event(
                "validation_completed",
                {
                    "validation_id": validation_id,
                    "report": report,
                    "repair_results": repair_results,
                    "metadata": metadata,
                },
            )

            logger.info(f"Validation {validation_id} completed successfully")
            return report

        except asyncio.TimeoutError:
            logger.error(f"Validation {validation_id} timed out")
            validation_context["status"] = "timeout"
            validation_context["end_time"] = datetime.now(UTC)
            self._stats["failed_validations"] += 1

            # Record validation failure in metrics collector
            if self.metrics_collector:
                duration = (
                    datetime.now(UTC) - validation_context["start_time"]
                ).total_seconds()
                self.metrics_collector.record_validation_failed(
                    validation_id=validation_id,
                    error="Validation timed out",
                    duration_seconds=duration,
                )

            await self._emit_event(
                "validation_failed",
                {
                    "validation_id": validation_id,
                    "error": "Validation timed out",
                    "metadata": metadata,
                },
            )
            raise

        except Exception as e:
            logger.error(f"Validation {validation_id} failed: {e}")
            validation_context["status"] = "failed"
            validation_context["end_time"] = datetime.now(UTC)
            validation_context["error"] = str(e)
            self._stats["failed_validations"] += 1

            # Record validation failure in metrics collector
            if self.metrics_collector:
                duration = (
                    datetime.now(UTC) - validation_context["start_time"]
                ).total_seconds()
                self.metrics_collector.record_validation_failed(
                    validation_id=validation_id,
                    error=str(e),
                    duration_seconds=duration,
                )

            await self._emit_event(
                "validation_failed",
                {
                    "validation_id": validation_id,
                    "error": str(e),
                    "metadata": metadata,
                },
            )
            raise

        finally:
            # Move to history and remove from active
            self._validation_history.append(validation_context.copy())
            if validation_id in self._active_validations:
                del self._active_validations[validation_id]

    async def repair_issues(
        self,
        issues: list[ValidationIssue],
        repair_id: Optional[str] = None,
        max_repairs: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> list[RepairResult]:
        """Repair validation issues.

        Args:
            issues: List of validation issues to repair
            repair_id: Optional unique identifier for this repair operation
            max_repairs: Maximum number of repairs to perform
            metadata: Additional metadata for the repair

        Returns:
            List of repair results
        """
        if not self._running:
            raise RuntimeError("ValidationRepairSystemIntegrator not running")

        # Generate repair ID if not provided
        if repair_id is None:
            repair_id = f"repair_{datetime.now(UTC).isoformat()}_{id(self)}"

        logger.info(f"Starting repair operation {repair_id} for {len(issues)} issues")

        try:
            # Record repair start in metrics collector
            if self.metrics_collector:
                self.metrics_collector.record_repair_started(
                    repair_id=repair_id,
                    issues=issues,
                    metadata=metadata,
                )

            # Emit repair started event
            await self._emit_event(
                "repair_started",
                {
                    "repair_id": repair_id,
                    "issue_count": len(issues),
                    "metadata": metadata,
                },
            )

            # Perform repairs
            repair_start_time = datetime.now(UTC)
            repair_results = await self.validation_repair_system.auto_repair_issues(
                issues=issues,
                max_repairs=max_repairs,
            )
            repair_duration = (datetime.now(UTC) - repair_start_time).total_seconds()

            # Update statistics
            self._stats["total_repairs"] += len(repair_results)
            successful_repairs = sum(1 for r in repair_results if r.success)
            self._stats["successful_repairs"] += successful_repairs
            self._stats["failed_repairs"] += len(repair_results) - successful_repairs
            self._stats["manual_repairs_performed"] += len(repair_results)

            # Record repair completion in metrics collector
            if self.metrics_collector:
                self.metrics_collector.record_repair_completed(
                    repair_id=repair_id,
                    results=repair_results,
                    duration_seconds=repair_duration,
                )

            # Emit repair completed event
            await self._emit_event(
                "repair_completed",
                {
                    "repair_id": repair_id,
                    "repair_results": repair_results,
                    "successful_repairs": successful_repairs,
                    "metadata": metadata,
                },
            )

            logger.info(
                f"Repair operation {repair_id} completed: {successful_repairs}/{len(repair_results)} successful"
            )
            return repair_results

        except Exception as e:
            logger.error(f"Repair operation {repair_id} failed: {e}")

            # Record repair failure in metrics collector
            if self.metrics_collector:
                repair_duration = (
                    (datetime.now(UTC) - repair_start_time).total_seconds()
                    if "repair_start_time" in locals()
                    else 0.0
                )
                self.metrics_collector.record_repair_failed(
                    repair_id=repair_id,
                    error=str(e),
                    duration_seconds=repair_duration,
                )

            await self._emit_event(
                "repair_failed",
                {
                    "repair_id": repair_id,
                    "error": str(e),
                    "metadata": metadata,
                },
            )
            raise

    async def get_validation_status(self) -> dict[str, Any]:
        """Get current validation system status.

        Returns:
            Dictionary containing validation system status information
        """
        return {
            "initialized": self._initialized,
            "running": self._running,
            "active_validations": len(self._active_validations),
            "last_validation": (
                self._last_validation_report.to_dict()
                if self._last_validation_report
                else None
            ),
            "statistics": self._stats.copy(),
            "auto_validation_enabled": self.auto_validation_enabled,
            "validation_on_ingestion": self.validation_on_ingestion,
            "validation_on_extraction": self.validation_on_extraction,
        }

    async def get_validation_history(
        self,
        limit: Optional[int] = None,
        status_filter: Optional[str] = None,
    ) -> list[dict]:
        """Get validation history.

        Args:
            limit: Maximum number of records to return
            status_filter: Filter by validation status

        Returns:
            List of validation history records
        """
        history = self._validation_history.copy()

        # Apply status filter if provided
        if status_filter:
            history = [v for v in history if v.get("status") == status_filter]

        # Sort by start time (most recent first)
        history.sort(key=lambda x: x.get("start_time", datetime.min), reverse=True)

        # Apply limit if provided
        if limit:
            history = history[:limit]

        return history

    def add_event_handler(self, event_type: str, handler) -> None:
        """Add an event handler for validation events.

        Args:
            event_type: Type of event to handle
            handler: Async callable to handle the event
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []

        self._event_handlers[event_type].append(handler)
        logger.debug(f"Added event handler for {event_type}")

    def remove_event_handler(self, event_type: str, handler) -> None:
        """Remove an event handler.

        Args:
            event_type: Type of event
            handler: Handler to remove
        """
        if event_type in self._event_handlers:
            try:
                self._event_handlers[event_type].remove(handler)
                logger.debug(f"Removed event handler for {event_type}")
            except ValueError:
                logger.warning(f"Handler not found for event type {event_type}")

    # Private methods

    async def _setup_event_system_integration(self) -> None:
        """Set up integration with the enhanced sync event system."""
        if not self.enhanced_sync_system:
            return

        logger.info("Setting up event system integration")

        # Get the base sync event system for event subscriptions
        base_sync_system = self.enhanced_sync_system.base_sync_system
        if not base_sync_system:
            logger.warning("No base sync system available for event integration")
            return

        # Add handlers for sync events that should trigger validation
        if self.validation_on_ingestion:
            # Listen for data ingestion completion events (Qdrant creates/updates)
            base_sync_system.add_event_handler("qdrant.create", self._on_data_ingested)
            base_sync_system.add_event_handler("qdrant.update", self._on_data_ingested)
            logger.info("Registered handlers for data ingestion events")

        if self.validation_on_extraction:
            # Listen for entity extraction completion events (Neo4j creates/updates)
            base_sync_system.add_event_handler(
                "neo4j.create", self._on_entity_extracted
            )
            base_sync_system.add_event_handler(
                "neo4j.update", self._on_entity_extracted
            )
            logger.info("Registered handlers for entity extraction events")

        logger.info("Event system integration setup completed")

    async def _perform_auto_repair(
        self, validation_id: str, issues: list[ValidationIssue]
    ) -> list[RepairResult]:
        """Perform automatic repair for validation issues.

        Args:
            validation_id: ID of the validation that found the issues
            issues: List of issues to repair

        Returns:
            List of repair results
        """
        repair_id = f"{validation_id}_auto_repair"

        try:
            repair_results = await self.repair_issues(
                issues=issues,
                repair_id=repair_id,
                metadata={"auto_repair": True, "validation_id": validation_id},
            )

            # Update auto-repair statistics
            successful_auto_repairs = sum(1 for r in repair_results if r.success)
            self._stats["auto_repairs_performed"] += successful_auto_repairs

            return repair_results

        except Exception as e:
            logger.error(f"Auto-repair failed for validation {validation_id}: {e}")
            return []

    async def _cancel_validation(self, validation_id: str) -> None:
        """Cancel an active validation.

        Args:
            validation_id: ID of the validation to cancel
        """
        if validation_id in self._active_validations:
            validation_context = self._active_validations[validation_id]
            validation_context["status"] = "cancelled"
            validation_context["end_time"] = datetime.now(UTC)

            # Move to history
            self._validation_history.append(validation_context.copy())
            del self._active_validations[validation_id]

            logger.info(f"Cancelled validation {validation_id}")

    async def _emit_event(self, event_type: str, event_data: dict) -> None:
        """Emit an event to registered handlers.

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
                logger.error(f"Event handler failed for {event_type}: {e}")

    def _on_data_ingested(self, event) -> None:
        """Handle data ingestion events from the sync system.

        Args:
            event: ChangeEvent from the sync system
        """
        if not self.auto_validation_enabled or not self._running:
            return

        logger.debug(f"Data ingestion event received: {event.event_id}")

        # Schedule validation with a delay to allow for batch processing
        asyncio.create_task(
            self._schedule_validation_after_delay(
                trigger_type="data_ingested",
                event_id=event.event_id,
                entity_id=event.entity_id,
                entity_type=event.entity_type,
                delay_seconds=5.0,  # Allow time for batch processing
            )
        )

    def _on_entity_extracted(self, event) -> None:
        """Handle entity extraction events from the sync system.

        Args:
            event: ChangeEvent from the sync system
        """
        if not self.auto_validation_enabled or not self._running:
            return

        logger.debug(f"Entity extraction event received: {event.event_id}")

        # Schedule validation with a delay to allow for batch processing
        asyncio.create_task(
            self._schedule_validation_after_delay(
                trigger_type="entity_extracted",
                event_id=event.event_id,
                entity_id=event.entity_id,
                entity_type=event.entity_type,
                delay_seconds=3.0,  # Shorter delay for entity extraction
            )
        )

    async def _schedule_validation_after_delay(
        self,
        trigger_type: str,
        event_id: str,
        entity_id: str,
        entity_type: str,
        delay_seconds: float,
    ) -> None:
        """Schedule a validation operation after a delay.

        Args:
            trigger_type: Type of trigger that caused this validation
            event_id: ID of the triggering event
            entity_id: ID of the affected entity
            entity_type: Type of the affected entity
            delay_seconds: Delay before triggering validation
        """
        try:
            # Wait for the specified delay
            await asyncio.sleep(delay_seconds)

            # Check if we're still running
            if not self._running:
                return

            # Trigger validation with metadata about the trigger
            validation_id = (
                f"auto_{trigger_type}_{event_id}_{int(datetime.now(UTC).timestamp())}"
            )

            await self.trigger_validation(
                validation_id=validation_id,
                auto_repair=True,  # Enable auto-repair for event-triggered validations
                metadata={
                    "trigger_type": trigger_type,
                    "trigger_event_id": event_id,
                    "trigger_entity_id": entity_id,
                    "trigger_entity_type": entity_type,
                    "auto_triggered": True,
                },
            )

        except Exception as e:
            logger.error(
                f"Failed to schedule validation after {trigger_type} event: {e}"
            )

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
