"""Sync Conflict Monitor and Content Hash Synchronization System.

This module provides comprehensive monitoring, conflict resolution, and content hash
synchronization for the enhanced sync event system, integrating with existing
conflict resolution and monitoring infrastructure.
"""

import asyncio
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from ...utils.logging import LoggingConfig
from ..conflict_resolution import (
    ConflictRecord,
    ConflictResolutionSystem,
)
from ..managers import IDMapping, IDMappingManager, Neo4jManager, QdrantManager
from ..monitoring.ingestion_metrics import IngestionMonitor
from ..types import EntityType
from .enhanced_event_system import EnhancedSyncEventSystem, EnhancedSyncOperation
from .event_system import ChangeEvent, ChangeType, DatabaseType
from .types import SyncOperationStatus, SyncOperationType

logger = LoggingConfig.get_logger(__name__)


class SyncMonitoringLevel(Enum):
    """Levels of sync monitoring detail."""

    MINIMAL = "minimal"  # Only critical events
    STANDARD = "standard"  # Standard operational events
    DETAILED = "detailed"  # Detailed operation tracking
    DEBUG = "debug"  # Full debug information


class ContentHashStatus(Enum):
    """Status of content hash comparison."""

    MATCH = "match"  # Content hashes match
    MISMATCH = "mismatch"  # Content hashes differ
    MISSING_SOURCE = "missing_source"  # Source hash missing
    MISSING_TARGET = "missing_target"  # Target hash missing
    BOTH_MISSING = "both_missing"  # Both hashes missing
    HASH_ERROR = "hash_error"  # Error computing hash


@dataclass
class ContentHashComparison:
    """Result of content hash comparison between databases."""

    mapping_id: str
    entity_id: str
    qdrant_hash: str | None = None
    neo4j_hash: str | None = None
    status: ContentHashStatus = ContentHashStatus.BOTH_MISSING
    comparison_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    requires_sync: bool = False
    sync_direction: DatabaseType | None = None  # Which DB should be updated
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "mapping_id": self.mapping_id,
            "entity_id": self.entity_id,
            "qdrant_hash": self.qdrant_hash,
            "neo4j_hash": self.neo4j_hash,
            "status": self.status.value,
            "comparison_time": self.comparison_time.isoformat(),
            "requires_sync": self.requires_sync,
            "sync_direction": (
                self.sync_direction.value if self.sync_direction else None
            ),
            "error_message": self.error_message,
        }


@dataclass
class SyncOperationMetrics:
    """Comprehensive metrics for sync operations."""

    operation_id: str
    operation_type: SyncOperationType
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    duration_seconds: float | None = None
    status: SyncOperationStatus = SyncOperationStatus.PENDING

    # Content hash metrics
    content_hash_comparison: ContentHashComparison | None = None
    hash_computation_time_ms: float | None = None

    # Conflict resolution metrics
    conflicts_detected: int = 0
    conflicts_resolved: int = 0
    conflicts_failed: int = 0
    manual_interventions_required: int = 0
    conflict_resolution_time_ms: float | None = None

    # Database operation metrics
    qdrant_operations: int = 0
    neo4j_operations: int = 0
    transaction_rollbacks: int = 0
    retry_attempts: int = 0

    # Data metrics
    entities_processed: int = 0
    relationships_processed: int = 0
    data_size_bytes: int | None = None

    # Error tracking
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def mark_completed(self, status: SyncOperationStatus) -> None:
        """Mark operation as completed with final status."""
        self.end_time = datetime.now(UTC)
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.status = status

    def add_error(self, error: str) -> None:
        """Add an error to the operation metrics."""
        self.errors.append(f"{datetime.now(UTC).isoformat()}: {error}")

    def add_warning(self, warning: str) -> None:
        """Add a warning to the operation metrics."""
        self.warnings.append(f"{datetime.now(UTC).isoformat()}: {warning}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage/logging."""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "status": self.status.value,
            "content_hash_comparison": (
                self.content_hash_comparison.to_dict()
                if self.content_hash_comparison
                else None
            ),
            "hash_computation_time_ms": self.hash_computation_time_ms,
            "conflicts_detected": self.conflicts_detected,
            "conflicts_resolved": self.conflicts_resolved,
            "conflicts_failed": self.conflicts_failed,
            "manual_interventions_required": self.manual_interventions_required,
            "conflict_resolution_time_ms": self.conflict_resolution_time_ms,
            "qdrant_operations": self.qdrant_operations,
            "neo4j_operations": self.neo4j_operations,
            "transaction_rollbacks": self.transaction_rollbacks,
            "retry_attempts": self.retry_attempts,
            "entities_processed": self.entities_processed,
            "relationships_processed": self.relationships_processed,
            "data_size_bytes": self.data_size_bytes,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class SyncConflictMonitor:
    """Comprehensive sync monitoring with conflict resolution and content hash synchronization."""

    def __init__(
        self,
        enhanced_sync_system: EnhancedSyncEventSystem,
        conflict_resolution_system: ConflictResolutionSystem,
        qdrant_manager: QdrantManager,
        neo4j_manager: Neo4jManager,
        id_mapping_manager: IDMappingManager,
        ingestion_monitor: IngestionMonitor | None = None,
        monitoring_level: SyncMonitoringLevel = SyncMonitoringLevel.STANDARD,
        enable_content_hash_sync: bool = True,
        enable_automatic_conflict_resolution: bool = True,
        content_hash_check_interval_hours: int = 24,
        conflict_resolution_timeout_seconds: int = 300,
        max_concurrent_hash_checks: int = 10,
    ):
        """Initialize the sync conflict monitor.

        Args:
            enhanced_sync_system: Enhanced sync event system instance
            conflict_resolution_system: Conflict resolution system instance
            qdrant_manager: QDrant manager instance
            neo4j_manager: Neo4j manager instance
            id_mapping_manager: ID mapping manager instance
            ingestion_monitor: Optional ingestion monitor for metrics
            monitoring_level: Level of monitoring detail
            enable_content_hash_sync: Whether to enable content hash synchronization
            enable_automatic_conflict_resolution: Whether to enable automatic conflict resolution
            content_hash_check_interval_hours: Interval for periodic hash checks
            conflict_resolution_timeout_seconds: Timeout for conflict resolution
            max_concurrent_hash_checks: Maximum concurrent hash check operations
        """
        self.enhanced_sync_system = enhanced_sync_system
        self.conflict_resolution_system = conflict_resolution_system
        self.qdrant_manager = qdrant_manager
        self.neo4j_manager = neo4j_manager
        self.id_mapping_manager = id_mapping_manager
        self.ingestion_monitor = ingestion_monitor
        self.monitoring_level = monitoring_level
        self.enable_content_hash_sync = enable_content_hash_sync
        self.enable_automatic_conflict_resolution = enable_automatic_conflict_resolution
        self.content_hash_check_interval_hours = content_hash_check_interval_hours
        self.conflict_resolution_timeout_seconds = conflict_resolution_timeout_seconds
        self.max_concurrent_hash_checks = max_concurrent_hash_checks

        # Monitoring state
        self._operation_metrics: dict[str, SyncOperationMetrics] = {}
        self._content_hash_cache: dict[str, ContentHashComparison] = {}
        self._conflict_history: dict[str, list[ConflictRecord]] = {}
        self._running = False

        # Background tasks
        self._monitoring_tasks: list[asyncio.Task] = []
        self._hash_check_semaphore = asyncio.Semaphore(max_concurrent_hash_checks)

        # Statistics
        self._stats = {
            "operations_monitored": 0,
            "conflicts_detected": 0,
            "conflicts_resolved": 0,
            "hash_mismatches_found": 0,
            "hash_syncs_performed": 0,
            "manual_interventions_required": 0,
            "monitoring_errors": 0,
        }

        logger.info(
            f"Initialized SyncConflictMonitor with monitoring level: {monitoring_level.value}"
        )

    async def start_monitoring(self) -> None:
        """Start the sync conflict monitoring system."""
        if self._running:
            logger.warning("Sync conflict monitor is already running")
            return

        self._running = True
        logger.info("Starting sync conflict monitoring system")

        # Start background monitoring tasks
        if self.enable_content_hash_sync:
            self._monitoring_tasks.append(
                asyncio.create_task(self._periodic_content_hash_check())
            )

        # Hook into the enhanced sync system
        await self._setup_sync_system_integration()

        logger.info("Sync conflict monitoring system started successfully")

    async def stop_monitoring(self) -> None:
        """Stop the sync conflict monitoring system."""
        if not self._running:
            return

        self._running = False
        logger.info("Stopping sync conflict monitoring system")

        # Cancel background tasks
        for task in self._monitoring_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)

        self._monitoring_tasks.clear()
        logger.info("Sync conflict monitoring system stopped")

    async def _setup_sync_system_integration(self) -> None:
        """Set up integration with the enhanced sync system."""
        # This would typically involve registering event handlers
        # For now, we'll implement monitoring through direct method calls
        logger.debug("Setting up sync system integration")

    async def monitor_sync_operation(
        self, operation: EnhancedSyncOperation
    ) -> SyncOperationMetrics:
        """Monitor a sync operation comprehensively.

        Args:
            operation: The sync operation to monitor

        Returns:
            Comprehensive metrics for the operation
        """
        metrics = SyncOperationMetrics(
            operation_id=operation.operation_id,
            operation_type=operation.operation_type,
        )

        self._operation_metrics[operation.operation_id] = metrics
        self._stats["operations_monitored"] += 1

        try:
            # Perform content hash comparison if enabled
            if self.enable_content_hash_sync and operation.entity_id:
                hash_comparison = await self._perform_content_hash_comparison(
                    operation.entity_id
                )
                metrics.content_hash_comparison = hash_comparison

                if hash_comparison.requires_sync:
                    await self._handle_content_hash_mismatch(operation, hash_comparison)

            # Check for conflicts
            if self.enable_automatic_conflict_resolution:
                await self._check_and_resolve_conflicts(operation, metrics)

            # Update operation metrics based on operation status
            metrics.mark_completed(operation.status)

            # Log based on monitoring level
            await self._log_operation_metrics(metrics)

        except Exception as e:
            error_msg = (
                f"Error monitoring sync operation {operation.operation_id}: {str(e)}"
            )
            logger.error(error_msg)
            metrics.add_error(error_msg)
            metrics.mark_completed(SyncOperationStatus.FAILED)
            self._stats["monitoring_errors"] += 1

        return metrics

    async def _perform_content_hash_comparison(
        self, entity_id: str
    ) -> ContentHashComparison:
        """Perform content hash comparison between QDrant and Neo4j.

        Args:
            entity_id: ID of the entity to compare

        Returns:
            Content hash comparison result
        """
        async with self._hash_check_semaphore:
            start_time = datetime.now(UTC)

            # Get mapping for the entity
            mapping = await self.id_mapping_manager.get_mapping_by_qdrant_id(entity_id)
            if not mapping:
                mapping = await self.id_mapping_manager.get_mapping_by_neo4j_id(
                    entity_id
                )

            if not mapping:
                return ContentHashComparison(
                    mapping_id="unknown",
                    entity_id=entity_id,
                    status=ContentHashStatus.MISSING_SOURCE,
                    error_message="No mapping found for entity",
                )

            comparison = ContentHashComparison(
                mapping_id=mapping.mapping_id, entity_id=entity_id
            )

            try:
                # Get content hashes from both databases
                qdrant_hash = await self._get_qdrant_content_hash(mapping)
                neo4j_hash = await self._get_neo4j_content_hash(mapping)

                comparison.qdrant_hash = qdrant_hash
                comparison.neo4j_hash = neo4j_hash

                # Determine status and sync requirements
                if qdrant_hash and neo4j_hash:
                    if qdrant_hash == neo4j_hash:
                        comparison.status = ContentHashStatus.MATCH
                    else:
                        comparison.status = ContentHashStatus.MISMATCH
                        comparison.requires_sync = True
                        # Determine sync direction based on timestamps
                        comparison.sync_direction = (
                            await self._determine_sync_direction(mapping)
                        )
                elif qdrant_hash and not neo4j_hash:
                    comparison.status = ContentHashStatus.MISSING_TARGET
                    comparison.requires_sync = True
                    comparison.sync_direction = DatabaseType.NEO4J
                elif neo4j_hash and not qdrant_hash:
                    comparison.status = ContentHashStatus.MISSING_SOURCE
                    comparison.requires_sync = True
                    comparison.sync_direction = DatabaseType.QDRANT
                else:
                    comparison.status = ContentHashStatus.BOTH_MISSING

                # Cache the comparison result
                self._content_hash_cache[mapping.mapping_id] = comparison

                # Update statistics
                if comparison.status == ContentHashStatus.MISMATCH:
                    self._stats["hash_mismatches_found"] += 1

            except Exception as e:
                comparison.status = ContentHashStatus.HASH_ERROR
                comparison.error_message = str(e)
                logger.error(f"Error comparing content hashes for {entity_id}: {e}")

            return comparison

    async def _get_qdrant_content_hash(self, mapping: IDMapping) -> str | None:
        """Get content hash from QDrant.

        Args:
            mapping: ID mapping for the entity

        Returns:
            Content hash or None if not available
        """
        if not mapping.qdrant_point_id:
            return None

        try:
            # Get point data from QDrant using search with ID filter
            # Since get_point method doesn't exist, we'll use search with exact ID match
            client = self.qdrant_manager._ensure_client_connected()
            points = await asyncio.to_thread(
                client.retrieve,
                collection_name=self.qdrant_manager.collection_name,
                ids=[mapping.qdrant_point_id],
                with_payload=True,
            )

            if not points or len(points) == 0:
                return None

            point = points[0]
            # Create hash from payload content
            content = json.dumps(point.payload, sort_keys=True)
            return hashlib.sha256(content.encode()).hexdigest()

        except Exception as e:
            logger.error(f"Error getting QDrant content hash: {e}")
            return None

    async def _get_neo4j_content_hash(self, mapping: IDMapping) -> str | None:
        """Get content hash from Neo4j.

        Args:
            mapping: ID mapping for the entity

        Returns:
            Content hash or None if not available
        """
        if not mapping.neo4j_node_id:
            return None

        try:
            # Get node data from Neo4j
            query = """
            MATCH (n) WHERE id(n) = $node_id
            RETURN properties(n) as props
            """
            result = self.neo4j_manager.execute_query(
                query, {"node_id": int(mapping.neo4j_node_id)}
            )

            if not result:
                return None

            # Create hash from node properties
            props = result[0]["props"] if result else {}
            content = json.dumps(props, sort_keys=True)
            return hashlib.sha256(content.encode()).hexdigest()

        except Exception as e:
            logger.error(f"Error getting Neo4j content hash: {e}")
            return None

    async def _determine_sync_direction(self, mapping: IDMapping) -> DatabaseType:
        """Determine which database should be the source for synchronization.

        Args:
            mapping: ID mapping for the entity

        Returns:
            Database type that should be the sync source
        """
        # Use last update time from mapping to determine direction
        # Default to QDrant if no clear preference
        if mapping.last_update_time and mapping.update_source:
            if mapping.update_source == "qdrant":
                return DatabaseType.NEO4J  # Sync TO Neo4j
            elif mapping.update_source == "neo4j":
                return DatabaseType.QDRANT  # Sync TO QDrant

        # Default to syncing to Neo4j (QDrant as source)
        return DatabaseType.NEO4J

    async def _handle_content_hash_mismatch(
        self, operation: EnhancedSyncOperation, comparison: ContentHashComparison
    ) -> None:
        """Handle content hash mismatch by triggering synchronization.

        Args:
            operation: The sync operation being monitored
            comparison: Content hash comparison result
        """
        if not comparison.requires_sync or not comparison.sync_direction:
            return

        logger.info(
            f"Content hash mismatch detected for {comparison.entity_id}, "
            f"syncing to {comparison.sync_direction.value}"
        )

        try:
            # Create a new sync operation for the mismatch
            sync_operation = EnhancedSyncOperation(
                operation_type=SyncOperationType.UPDATE_DOCUMENT,
                entity_id=comparison.entity_id,
                target_databases={comparison.sync_direction},
                metadata={
                    "triggered_by": "content_hash_mismatch",
                    "original_operation": operation.operation_id,
                    "hash_comparison": comparison.to_dict(),
                },
            )

            # Queue the sync operation
            await self.enhanced_sync_system.queue_operation(sync_operation)
            self._stats["hash_syncs_performed"] += 1

        except Exception as e:
            logger.error(f"Error handling content hash mismatch: {e}")

    async def _check_and_resolve_conflicts(
        self, operation: EnhancedSyncOperation, metrics: SyncOperationMetrics
    ) -> None:
        """Check for conflicts and attempt automatic resolution.

        Args:
            operation: The sync operation to check
            metrics: Operation metrics to update
        """
        if not operation.entity_id:
            return

        try:
            # Get mapping for conflict detection
            mapping = await self.id_mapping_manager.get_mapping_by_qdrant_id(
                operation.entity_id
            )
            if not mapping:
                return

            # Create a change event for conflict detection
            change_event = ChangeEvent(
                event_id=str(uuid.uuid4()),
                change_type=ChangeType(
                    operation.operation_type.value.replace("_document", "").replace(
                        "_entity", ""
                    )
                ),
                database_type=DatabaseType.QDRANT,  # Assume QDrant as source
                entity_id=operation.entity_id,
                timestamp=operation.timestamp,
                metadata=operation.metadata,
            )

            # Detect conflicts
            conflict = await self.conflict_resolution_system.detect_conflict(
                mapping, change_event
            )

            if conflict:
                metrics.conflicts_detected += 1
                self._stats["conflicts_detected"] += 1

                # Attempt automatic resolution
                resolution_start = datetime.now(UTC)
                resolved = await self.conflict_resolution_system.resolve_conflict(
                    conflict.conflict_id
                )
                resolution_time = (datetime.now(UTC) - resolution_start).total_seconds()
                metrics.conflict_resolution_time_ms = resolution_time * 1000

                if resolved:
                    metrics.conflicts_resolved += 1
                    self._stats["conflicts_resolved"] += 1
                    logger.info(
                        f"Automatically resolved conflict {conflict.conflict_id}"
                    )
                else:
                    metrics.conflicts_failed += 1
                    if conflict.requires_manual_review():
                        metrics.manual_interventions_required += 1
                        self._stats["manual_interventions_required"] += 1
                        logger.warning(
                            f"Conflict {conflict.conflict_id} requires manual intervention"
                        )

                # Store conflict history
                if mapping.mapping_id not in self._conflict_history:
                    self._conflict_history[mapping.mapping_id] = []
                self._conflict_history[mapping.mapping_id].append(conflict)

        except Exception as e:
            logger.error(
                f"Error checking conflicts for operation {operation.operation_id}: {e}"
            )
            metrics.add_error(f"Conflict check error: {str(e)}")

    async def _periodic_content_hash_check(self) -> None:
        """Periodic background task to check content hashes."""
        logger.info("Starting periodic content hash check task")

        while self._running:
            try:
                # Get all active mappings
                mappings = await self.id_mapping_manager.get_mappings_by_entity_type(
                    EntityType.CONCEPT, limit=1000
                )

                logger.info(
                    f"Performing periodic hash check on {len(mappings)} mappings"
                )

                # Check hashes in batches
                batch_size = 50
                for i in range(0, len(mappings), batch_size):
                    batch = mappings[i : i + batch_size]
                    tasks = [
                        self._perform_content_hash_comparison(mapping.qdrant_point_id)
                        for mapping in batch
                        if mapping.qdrant_point_id
                    ]

                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=True)

                    # Small delay between batches
                    await asyncio.sleep(1)

                logger.info("Completed periodic content hash check")

                # Wait for next check interval
                await asyncio.sleep(self.content_hash_check_interval_hours * 3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic content hash check: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry

        logger.info("Periodic content hash check task stopped")

    async def _log_operation_metrics(self, metrics: SyncOperationMetrics) -> None:
        """Log operation metrics based on monitoring level.

        Args:
            metrics: Operation metrics to log
        """
        if self.monitoring_level == SyncMonitoringLevel.MINIMAL:
            if metrics.status == SyncOperationStatus.FAILED or metrics.errors:
                logger.error(
                    f"Sync operation {metrics.operation_id} failed: {metrics.errors}"
                )
        elif self.monitoring_level == SyncMonitoringLevel.STANDARD:
            logger.info(
                f"Sync operation {metrics.operation_id} completed: "
                f"status={metrics.status.value}, duration={metrics.duration_seconds}s"
            )
        elif self.monitoring_level in [
            SyncMonitoringLevel.DETAILED,
            SyncMonitoringLevel.DEBUG,
        ]:
            logger.info(
                f"Detailed sync metrics: {json.dumps(metrics.to_dict(), indent=2)}"
            )

        # Also log to ingestion monitor if available
        if self.ingestion_monitor:
            self.ingestion_monitor.start_operation(
                metrics.operation_id, {"sync_operation": metrics.to_dict()}
            )
            self.ingestion_monitor.end_operation(
                metrics.operation_id,
                success=(metrics.status == SyncOperationStatus.COMPLETED),
                error="; ".join(metrics.errors) if metrics.errors else None,
            )

    async def get_monitoring_statistics(self) -> dict[str, Any]:
        """Get comprehensive monitoring statistics.

        Returns:
            Dictionary containing monitoring statistics
        """
        # Get conflict resolution statistics
        conflict_stats = await self.conflict_resolution_system.get_conflict_statistics()

        # Calculate additional metrics
        total_operations = len(self._operation_metrics)
        successful_operations = sum(
            1
            for m in self._operation_metrics.values()
            if m.status == SyncOperationStatus.COMPLETED
        )
        failed_operations = sum(
            1
            for m in self._operation_metrics.values()
            if m.status == SyncOperationStatus.FAILED
        )

        # Average operation duration
        completed_operations = [
            m
            for m in self._operation_metrics.values()
            if m.duration_seconds is not None
        ]
        avg_duration = (
            sum(
                m.duration_seconds
                for m in completed_operations
                if m.duration_seconds is not None
            )
            / len(completed_operations)
            if completed_operations
            else 0
        )

        return {
            "monitoring_status": "running" if self._running else "stopped",
            "monitoring_level": self.monitoring_level.value,
            "total_operations_monitored": total_operations,
            "successful_operations": successful_operations,
            "failed_operations": failed_operations,
            "average_operation_duration_seconds": avg_duration,
            "content_hash_checks_performed": len(self._content_hash_cache),
            "hash_mismatches_detected": self._stats["hash_mismatches_found"],
            "hash_syncs_performed": self._stats["hash_syncs_performed"],
            "conflicts_detected": self._stats["conflicts_detected"],
            "conflicts_resolved": self._stats["conflicts_resolved"],
            "manual_interventions_required": self._stats[
                "manual_interventions_required"
            ],
            "monitoring_errors": self._stats["monitoring_errors"],
            "conflict_resolution_stats": conflict_stats,
            "cache_sizes": {
                "operation_metrics": len(self._operation_metrics),
                "content_hash_cache": len(self._content_hash_cache),
                "conflict_history": len(self._conflict_history),
            },
        }

    async def get_recent_operations(
        self, hours: int = 24, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get recent sync operations with their metrics.

        Args:
            hours: Number of hours to look back
            limit: Maximum number of operations to return

        Returns:
            List of recent operation metrics
        """
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        recent_ops = [
            metrics.to_dict()
            for metrics in self._operation_metrics.values()
            if metrics.start_time >= cutoff_time
        ]

        # Sort by start time (most recent first)
        recent_ops.sort(key=lambda x: x["start_time"], reverse=True)
        return recent_ops[:limit]

    async def get_content_hash_mismatches(
        self, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get recent content hash mismatches.

        Args:
            limit: Maximum number of mismatches to return

        Returns:
            List of content hash mismatches
        """
        mismatches = [
            comparison.to_dict()
            for comparison in self._content_hash_cache.values()
            if comparison.status == ContentHashStatus.MISMATCH
        ]

        # Sort by comparison time (most recent first)
        mismatches.sort(key=lambda x: x["comparison_time"], reverse=True)
        return mismatches[:limit]

    async def health_check(self) -> dict[str, Any]:
        """Perform health check of the sync conflict monitor.

        Returns:
            Health check results
        """
        health = {
            "status": "healthy",
            "running": self._running,
            "monitoring_level": self.monitoring_level.value,
            "background_tasks": len(self._monitoring_tasks),
            "content_hash_sync_enabled": self.enable_content_hash_sync,
            "automatic_conflict_resolution_enabled": self.enable_automatic_conflict_resolution,
            "issues": [],
        }

        try:
            # Check if background tasks are running
            if self._running and not self._monitoring_tasks:
                health["issues"].append("No background monitoring tasks running")

            # Check recent error rates
            recent_ops = await self.get_recent_operations(hours=1)
            if recent_ops:
                error_rate = sum(1 for op in recent_ops if op["errors"]) / len(
                    recent_ops
                )
                if error_rate > 0.1:  # More than 10% error rate
                    health["issues"].append(f"High error rate: {error_rate:.1%}")

            # Check conflict resolution system health
            conflict_health = await self.conflict_resolution_system.health_check()
            if conflict_health.get("status") != "healthy":
                health["issues"].append("Conflict resolution system unhealthy")

            # Set overall status
            if health["issues"]:
                health["status"] = (
                    "degraded" if len(health["issues"]) < 3 else "unhealthy"
                )

        except Exception as e:
            health["status"] = "unhealthy"
            health["issues"].append(f"Health check error: {str(e)}")

        return health

    async def cleanup_old_data(self, days: int = 30) -> dict[str, int]:
        """Clean up old monitoring data.

        Args:
            days: Number of days of data to retain

        Returns:
            Cleanup statistics
        """
        cutoff_time = datetime.now(UTC) - timedelta(days=days)
        cleanup_stats = {"operations_cleaned": 0, "hash_comparisons_cleaned": 0}

        # Clean up old operation metrics
        old_operations = [
            op_id
            for op_id, metrics in self._operation_metrics.items()
            if metrics.start_time < cutoff_time
        ]
        for op_id in old_operations:
            del self._operation_metrics[op_id]
        cleanup_stats["operations_cleaned"] = len(old_operations)

        # Clean up old hash comparisons
        old_comparisons = [
            mapping_id
            for mapping_id, comparison in self._content_hash_cache.items()
            if comparison.comparison_time < cutoff_time
        ]
        for mapping_id in old_comparisons:
            del self._content_hash_cache[mapping_id]
        cleanup_stats["hash_comparisons_cleaned"] = len(old_comparisons)

        logger.info(f"Cleaned up old monitoring data: {cleanup_stats}")
        return cleanup_stats
