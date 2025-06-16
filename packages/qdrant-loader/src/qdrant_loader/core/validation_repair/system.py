"""
Main validation and repair system orchestrator.

This module contains the primary ValidationRepairSystem class that coordinates
validation scanning and repair operations across QDrant and Neo4j databases.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from ..managers import IDMappingManager, Neo4jManager, QdrantManager
from .models import (
    RepairAction,
    RepairResult,
    ValidationCategory,
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
)
from .repair_handlers import RepairHandlers
from .scanners import ValidationScanners

logger = logging.getLogger(__name__)


class ValidationRepairSystem:
    """Comprehensive validation and repair system for QDrant-Neo4j synchronization."""

    def __init__(
        self,
        id_mapping_manager: IDMappingManager,
        neo4j_manager: Neo4jManager,
        qdrant_manager: QdrantManager,
        conflict_resolution_system=None,
        auto_repair_enabled: bool = False,
        max_auto_repair_batch_size: int = 100,
    ):
        self.id_mapping_manager = id_mapping_manager
        self.neo4j_manager = neo4j_manager
        self.qdrant_manager = qdrant_manager
        self.conflict_resolution_system = conflict_resolution_system
        self.auto_repair_enabled = auto_repair_enabled
        self.max_auto_repair_batch_size = max_auto_repair_batch_size

        # Initialize scanners and repair handlers
        self.scanners = ValidationScanners(
            id_mapping_manager, neo4j_manager, qdrant_manager
        )
        self.repair_handlers = RepairHandlers(
            id_mapping_manager,
            neo4j_manager,
            qdrant_manager,
            conflict_resolution_system,
        )

        # Validation scanners registry
        self._scanners: dict[str, Callable] = {
            "missing_mappings": self.scanners.scan_missing_mappings,
            "orphaned_records": self.scanners.scan_orphaned_records,
            "data_mismatches": self.scanners.scan_data_mismatches,
            "version_inconsistencies": self.scanners.scan_version_inconsistencies,
            "sync_failures": self.scanners.scan_sync_failures,
            "constraint_violations": self.scanners.scan_constraint_violations,
            "performance_issues": self.scanners.scan_performance_issues,
        }

        # Repair handlers registry
        self._repair_handlers: dict[RepairAction, Callable] = {
            RepairAction.CREATE_MAPPING: self.repair_handlers.repair_create_mapping,
            RepairAction.DELETE_ORPHANED: self.repair_handlers.repair_delete_orphaned,
            RepairAction.UPDATE_DATA: self.repair_handlers.repair_update_data,
            RepairAction.SYNC_ENTITIES: self.repair_handlers.repair_sync_entities,
            RepairAction.RESOLVE_CONFLICT: self.repair_handlers.repair_resolve_conflict,
            RepairAction.REBUILD_INDEX: self.repair_handlers.repair_rebuild_index,
        }

        logger.info("ValidationRepairSystem initialized")

    async def run_full_validation(
        self,
        scanners: list[str] | None = None,
        max_entities_per_scanner: int | None = None,
    ) -> ValidationReport:
        """Run comprehensive validation across all systems."""
        start_time = datetime.now(UTC)
        report = ValidationReport()

        # Use all scanners if none specified
        if scanners is None:
            scanners = list(self._scanners.keys())

        logger.info(f"Starting full validation with scanners: {scanners}")

        # Check database connectivity first
        report.database_connectivity = await self._check_database_connectivity()

        # Run each scanner
        for scanner_name in scanners:
            if scanner_name not in self._scanners:
                logger.warning(f"Unknown scanner: {scanner_name}")
                continue

            try:
                logger.info(f"Running scanner: {scanner_name}")
                scanner_func = self._scanners[scanner_name]
                issues = await scanner_func(max_entities_per_scanner)

                for issue in issues:
                    report.add_issue(issue)

                logger.info(f"Scanner {scanner_name} found {len(issues)} issues")

            except Exception as e:
                logger.error(f"Scanner {scanner_name} failed: {e}")
                # Add scanner failure as critical issue
                issue = ValidationIssue(
                    category=ValidationCategory.SYNC_FAILURE,
                    severity=ValidationSeverity.CRITICAL,
                    title=f"Scanner Failure: {scanner_name}",
                    description=f"Validation scanner failed with error: {str(e)}",
                    metadata={"scanner": scanner_name, "error": str(e)},
                )
                report.add_issue(issue)

        # Calculate final metrics
        end_time = datetime.now(UTC)
        report.validation_duration_ms = (end_time - start_time).total_seconds() * 1000
        report.calculate_health_score()

        # Get performance metrics
        report.performance_metrics = await self._collect_performance_metrics()

        logger.info(
            f"Validation complete: {report.total_issues} issues found "
            f"(Critical: {report.critical_issues}, Error: {report.error_issues}, "
            f"Warning: {report.warning_issues}, Info: {report.info_issues})"
        )

        return report

    async def auto_repair_issues(
        self,
        issues: list[ValidationIssue],
        max_repairs: int | None = None,
    ) -> list[RepairResult]:
        """Automatically repair issues that are marked as auto-repairable."""
        if not self.auto_repair_enabled:
            logger.warning("Auto-repair is disabled")
            return []

        # Filter auto-repairable issues and sort by priority
        auto_repairable = [issue for issue in issues if issue.auto_repairable]
        auto_repairable.sort(key=lambda x: x.repair_priority, reverse=True)

        # Limit repairs if specified
        if max_repairs:
            auto_repairable = auto_repairable[:max_repairs]

        logger.info(f"Starting auto-repair for {len(auto_repairable)} issues")

        results = []
        for issue in auto_repairable:
            for action in issue.suggested_actions:
                if action in self._repair_handlers:
                    try:
                        result = await self._repair_handlers[action](issue)
                        results.append(result)

                        if result.success:
                            issue.resolved_at = datetime.now(UTC)
                            issue.resolution_notes = (
                                f"Auto-repaired with action: {action.value}"
                            )
                            break  # Move to next issue after successful repair

                    except Exception as e:
                        logger.error(
                            f"Auto-repair failed for issue {issue.issue_id}: {e}"
                        )
                        result = RepairResult(
                            issue_id=issue.issue_id,
                            action_taken=action,
                            success=False,
                            error_message=str(e),
                        )
                        results.append(result)

        successful_repairs = sum(1 for r in results if r.success)
        logger.info(
            f"Auto-repair completed: {successful_repairs}/{len(results)} successful"
        )

        return results

    # Helper Methods

    async def _check_database_connectivity(self) -> dict[str, bool]:
        """Check connectivity to both databases."""
        connectivity = {}

        try:
            # Test Neo4j connectivity
            result = self.neo4j_manager.execute_read_query("RETURN 1 as test", {})
            connectivity["neo4j"] = len(result) > 0
        except Exception as e:
            logger.error(f"Neo4j connectivity check failed: {e}")
            connectivity["neo4j"] = False

        try:
            # Test QDrant connectivity
            client = self.qdrant_manager._ensure_client_connected()
            collection_info = client.get_collection(self.qdrant_manager.collection_name)
            connectivity["qdrant"] = collection_info is not None
        except Exception as e:
            logger.error(f"QDrant connectivity check failed: {e}")
            connectivity["qdrant"] = False

        return connectivity

    async def _collect_performance_metrics(self) -> dict[str, Any]:
        """Collect performance metrics from both databases."""
        return await self.scanners._collect_performance_metrics()

    # Convenience methods for individual operations

    async def validate_missing_mappings(
        self, max_entities: int | None = None
    ) -> list[ValidationIssue]:
        """Run only the missing mappings validation."""
        return await self.scanners.scan_missing_mappings(max_entities)

    async def validate_orphaned_records(
        self, max_entities: int | None = None
    ) -> list[ValidationIssue]:
        """Run only the orphaned records validation."""
        return await self.scanners.scan_orphaned_records(max_entities)

    async def validate_data_mismatches(
        self, max_entities: int | None = None
    ) -> list[ValidationIssue]:
        """Run only the data mismatches validation."""
        return await self.scanners.scan_data_mismatches(max_entities)

    async def validate_version_inconsistencies(
        self, max_entities: int | None = None
    ) -> list[ValidationIssue]:
        """Run only the version inconsistencies validation."""
        return await self.scanners.scan_version_inconsistencies(max_entities)

    async def validate_sync_failures(
        self, max_entities: int | None = None
    ) -> list[ValidationIssue]:
        """Run only the sync failures validation."""
        return await self.scanners.scan_sync_failures(max_entities)

    async def validate_constraint_violations(
        self, max_entities: int | None = None
    ) -> list[ValidationIssue]:
        """Run only the constraint violations validation."""
        return await self.scanners.scan_constraint_violations(max_entities)

    async def validate_performance_issues(
        self, max_entities: int | None = None
    ) -> list[ValidationIssue]:
        """Run only the performance issues validation."""
        return await self.scanners.scan_performance_issues(max_entities)

    # Repair convenience methods

    async def repair_issue(self, issue: ValidationIssue) -> list[RepairResult]:
        """Repair a single issue using its suggested actions."""
        results = []

        for action in issue.suggested_actions:
            if action in self._repair_handlers:
                try:
                    result = await self._repair_handlers[action](issue)
                    results.append(result)

                    if result.success:
                        issue.resolved_at = datetime.now(UTC)
                        issue.resolution_notes = f"Repaired with action: {action.value}"
                        break  # Stop after first successful repair

                except Exception as e:
                    logger.error(f"Repair failed for issue {issue.issue_id}: {e}")
                    result = RepairResult(
                        issue_id=issue.issue_id,
                        action_taken=action,
                        success=False,
                        error_message=str(e),
                    )
                    results.append(result)

        return results
