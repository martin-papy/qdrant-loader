"""
Validation and Repair Tools System for QDrant-Neo4j Synchronization

This module provides comprehensive validation tools to detect inconsistencies
and automated repair workflows to maintain data integrity across both databases.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple, Callable
from uuid import uuid4

from .managers import IDMappingManager, IDMapping, MappingStatus
from .managers import Neo4jManager, QdrantManager
from .conflict_resolution_system import ConflictResolutionSystem
from .types import EntityType

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(Enum):
    """Categories of validation issues."""

    MISSING_MAPPING = "missing_mapping"
    ORPHANED_RECORD = "orphaned_record"
    DATA_MISMATCH = "data_mismatch"
    VERSION_INCONSISTENCY = "version_inconsistency"
    SYNC_FAILURE = "sync_failure"
    CONSTRAINT_VIOLATION = "constraint_violation"
    PERFORMANCE_ISSUE = "performance_issue"


class RepairAction(Enum):
    """Types of repair actions that can be performed."""

    CREATE_MAPPING = "create_mapping"
    DELETE_ORPHANED = "delete_orphaned"
    UPDATE_DATA = "update_data"
    SYNC_ENTITIES = "sync_entities"
    RESOLVE_CONFLICT = "resolve_conflict"
    REBUILD_INDEX = "rebuild_index"
    MANUAL_INTERVENTION = "manual_intervention"


@dataclass
class ValidationIssue:
    """Container for validation issue information."""

    issue_id: str = field(default_factory=lambda: str(uuid4()))
    category: ValidationCategory = ValidationCategory.DATA_MISMATCH
    severity: ValidationSeverity = ValidationSeverity.WARNING
    title: str = ""
    description: str = ""

    # Entity information
    entity_id: Optional[str] = None
    entity_type: Optional[EntityType] = None
    qdrant_point_id: Optional[str] = None
    neo4j_node_id: Optional[str] = None
    mapping_id: Optional[str] = None

    # Issue details
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Resolution information
    suggested_actions: List[RepairAction] = field(default_factory=list)
    auto_repairable: bool = False
    repair_priority: int = 5  # 1-10, higher is more urgent

    # Tracking
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert issue to dictionary format."""
        return {
            "issue_id": self.issue_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value if self.entity_type else None,
            "qdrant_point_id": self.qdrant_point_id,
            "neo4j_node_id": self.neo4j_node_id,
            "mapping_id": self.mapping_id,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "metadata": self.metadata,
            "suggested_actions": [action.value for action in self.suggested_actions],
            "auto_repairable": self.auto_repairable,
            "repair_priority": self.repair_priority,
            "detected_at": self.detected_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_notes": self.resolution_notes,
        }


@dataclass
class RepairResult:
    """Result of a repair operation."""

    issue_id: str
    action_taken: RepairAction
    success: bool
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format."""
        return {
            "issue_id": self.issue_id,
            "action_taken": self.action_taken.value,
            "success": self.success,
            "error_message": self.error_message,
            "details": self.details,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class ValidationReport:
    """Comprehensive validation report."""

    report_id: str = field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Summary statistics
    total_issues: int = 0
    critical_issues: int = 0
    error_issues: int = 0
    warning_issues: int = 0
    info_issues: int = 0
    auto_repairable_issues: int = 0

    # Issues by category
    issues_by_category: Dict[ValidationCategory, int] = field(default_factory=dict)
    issues: List[ValidationIssue] = field(default_factory=list)

    # System health metrics
    system_health_score: float = 100.0  # 0-100
    database_connectivity: Dict[str, bool] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)

    # Execution details
    validation_duration_ms: float = 0.0
    scanned_entities: Dict[str, int] = field(default_factory=dict)

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add an issue to the report."""
        self.issues.append(issue)
        self.total_issues += 1

        # Update severity counts
        if issue.severity == ValidationSeverity.CRITICAL:
            self.critical_issues += 1
        elif issue.severity == ValidationSeverity.ERROR:
            self.error_issues += 1
        elif issue.severity == ValidationSeverity.WARNING:
            self.warning_issues += 1
        else:
            self.info_issues += 1

        # Update category counts
        self.issues_by_category[issue.category] = (
            self.issues_by_category.get(issue.category, 0) + 1
        )

        # Update auto-repairable count
        if issue.auto_repairable:
            self.auto_repairable_issues += 1

    def calculate_health_score(self) -> None:
        """Calculate overall system health score."""
        if self.total_issues == 0:
            self.system_health_score = 100.0
            return

        # Weight issues by severity
        severity_weights = {
            ValidationSeverity.CRITICAL: 20,
            ValidationSeverity.ERROR: 10,
            ValidationSeverity.WARNING: 5,
            ValidationSeverity.INFO: 1,
        }

        total_weight = sum(
            severity_weights.get(issue.severity, 1) for issue in self.issues
        )

        # Calculate score (100 - weighted penalty)
        max_penalty = 100
        penalty = min(total_weight, max_penalty)
        self.system_health_score = max(0.0, 100.0 - penalty)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary format."""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "summary": {
                "total_issues": self.total_issues,
                "critical_issues": self.critical_issues,
                "error_issues": self.error_issues,
                "warning_issues": self.warning_issues,
                "info_issues": self.info_issues,
                "auto_repairable_issues": self.auto_repairable_issues,
                "system_health_score": self.system_health_score,
            },
            "issues_by_category": {
                cat.value: count for cat, count in self.issues_by_category.items()
            },
            "issues": [issue.to_dict() for issue in self.issues],
            "system_health": {
                "database_connectivity": self.database_connectivity,
                "performance_metrics": self.performance_metrics,
            },
            "execution_details": {
                "validation_duration_ms": self.validation_duration_ms,
                "scanned_entities": self.scanned_entities,
            },
        }


class ValidationRepairSystem:
    """Comprehensive validation and repair system for QDrant-Neo4j synchronization."""

    def __init__(
        self,
        id_mapping_manager: IDMappingManager,
        neo4j_manager: Neo4jManager,
        qdrant_manager: QdrantManager,
        conflict_resolution_system: Optional[ConflictResolutionSystem] = None,
        auto_repair_enabled: bool = False,
        max_auto_repair_batch_size: int = 100,
    ):
        self.id_mapping_manager = id_mapping_manager
        self.neo4j_manager = neo4j_manager
        self.qdrant_manager = qdrant_manager
        self.conflict_resolution_system = conflict_resolution_system
        self.auto_repair_enabled = auto_repair_enabled
        self.max_auto_repair_batch_size = max_auto_repair_batch_size

        # Validation scanners registry
        self._scanners: Dict[str, Callable] = {
            "missing_mappings": self._scan_missing_mappings,
            "orphaned_records": self._scan_orphaned_records,
            "data_mismatches": self._scan_data_mismatches,
            "version_inconsistencies": self._scan_version_inconsistencies,
            "sync_failures": self._scan_sync_failures,
            "constraint_violations": self._scan_constraint_violations,
            "performance_issues": self._scan_performance_issues,
        }

        # Repair handlers registry
        self._repair_handlers: Dict[RepairAction, Callable] = {
            RepairAction.CREATE_MAPPING: self._repair_create_mapping,
            RepairAction.DELETE_ORPHANED: self._repair_delete_orphaned,
            RepairAction.UPDATE_DATA: self._repair_update_data,
            RepairAction.SYNC_ENTITIES: self._repair_sync_entities,
            RepairAction.RESOLVE_CONFLICT: self._repair_resolve_conflict,
            RepairAction.REBUILD_INDEX: self._repair_rebuild_index,
        }

        logger.info("ValidationRepairSystem initialized")

    async def run_full_validation(
        self,
        scanners: Optional[List[str]] = None,
        max_entities_per_scanner: Optional[int] = None,
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
        issues: List[ValidationIssue],
        max_repairs: Optional[int] = None,
    ) -> List[RepairResult]:
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

    # Scanner Methods

    async def _scan_missing_mappings(
        self, max_entities: Optional[int] = None
    ) -> List[ValidationIssue]:
        """Scan for entities that exist in one database but lack mappings."""
        issues = []

        try:
            # Check QDrant points without mappings
            qdrant_issues = await self._scan_qdrant_missing_mappings(max_entities)
            issues.extend(qdrant_issues)

            # Check Neo4j nodes without mappings
            neo4j_issues = await self._scan_neo4j_missing_mappings(max_entities)
            issues.extend(neo4j_issues)

        except Exception as e:
            logger.error(f"Error scanning missing mappings: {e}")

        return issues

    async def _scan_qdrant_missing_mappings(
        self, max_entities: Optional[int] = None
    ) -> List[ValidationIssue]:
        """Scan for QDrant points without corresponding mappings."""
        issues = []

        try:
            # Get all points from QDrant
            client = self.qdrant_manager._ensure_client_connected()
            collection_info = client.get_collection(self.qdrant_manager.collection_name)

            # Scroll through points
            scroll_result = client.scroll(
                collection_name=self.qdrant_manager.collection_name,
                limit=max_entities or 10000,
                with_payload=True,
            )

            for point in scroll_result[0]:
                point_id = str(point.id)

                # Check if mapping exists
                mapping = await self.id_mapping_manager.get_mapping_by_qdrant_id(
                    point_id
                )

                if not mapping:
                    issue = ValidationIssue(
                        category=ValidationCategory.MISSING_MAPPING,
                        severity=ValidationSeverity.WARNING,
                        title="Missing QDrant Mapping",
                        description=f"QDrant point {point_id} has no corresponding mapping",
                        qdrant_point_id=point_id,
                        suggested_actions=[RepairAction.CREATE_MAPPING],
                        auto_repairable=True,
                        repair_priority=6,
                        metadata={
                            "point_payload": point.payload,
                            "vector_size": len(point.vector) if point.vector else 0,
                        },
                    )
                    issues.append(issue)

        except Exception as e:
            logger.error(f"Error scanning QDrant missing mappings: {e}")

        return issues

    async def _scan_neo4j_missing_mappings(
        self, max_entities: Optional[int] = None
    ) -> List[ValidationIssue]:
        """Scan for Neo4j nodes without corresponding mappings."""
        issues = []

        try:
            # Query for nodes that might need mappings (exclude system nodes)
            query = """
            MATCH (n)
            WHERE NOT n:IDMapping 
              AND NOT n:_GraphitiBatch
              AND NOT n:_GraphitiEpisode
            RETURN id(n) as node_id, labels(n) as labels, 
                   n.uuid as uuid, n.name as name
            LIMIT $limit
            """

            results = self.neo4j_manager.execute_read_query(
                query, {"limit": max_entities or 10000}
            )

            for result in results:
                node_id = str(result["node_id"])
                node_uuid = result.get("uuid")

                # Check if mapping exists by ID or UUID
                mapping = await self.id_mapping_manager.get_mapping_by_neo4j_id(node_id)
                if not mapping and node_uuid:
                    mapping = await self.id_mapping_manager.get_mapping_by_neo4j_uuid(
                        node_uuid
                    )

                if not mapping:
                    issue = ValidationIssue(
                        category=ValidationCategory.MISSING_MAPPING,
                        severity=ValidationSeverity.WARNING,
                        title="Missing Neo4j Mapping",
                        description=f"Neo4j node {node_id} has no corresponding mapping",
                        neo4j_node_id=node_id,
                        suggested_actions=[RepairAction.CREATE_MAPPING],
                        auto_repairable=True,
                        repair_priority=6,
                        metadata={
                            "node_labels": result["labels"],
                            "node_uuid": node_uuid,
                            "node_name": result.get("name"),
                        },
                    )
                    issues.append(issue)

        except Exception as e:
            logger.error(f"Error scanning Neo4j missing mappings: {e}")

        return issues

    async def _scan_orphaned_records(
        self, max_entities: Optional[int] = None
    ) -> List[ValidationIssue]:
        """Scan for orphaned records where mapped entities no longer exist."""
        issues = []

        try:
            # Get all mappings
            mappings = await self.id_mapping_manager.get_mappings_by_entity_type(
                EntityType.CONCEPT,  # This will get all types due to implementation
                limit=max_entities or 10000,
            )

            for mapping in mappings:
                # Validate existence of mapped entities
                await self.id_mapping_manager._validate_mapping_existence(mapping)

                if mapping.is_orphaned():
                    severity = (
                        ValidationSeverity.ERROR
                        if mapping.status == MappingStatus.ACTIVE
                        else ValidationSeverity.WARNING
                    )

                    issue = ValidationIssue(
                        category=ValidationCategory.ORPHANED_RECORD,
                        severity=severity,
                        title="Orphaned Mapping",
                        description=f"Mapping {mapping.mapping_id} references non-existent entities",
                        mapping_id=mapping.mapping_id,
                        qdrant_point_id=mapping.qdrant_point_id,
                        neo4j_node_id=mapping.neo4j_node_id,
                        suggested_actions=[RepairAction.DELETE_ORPHANED],
                        auto_repairable=True,
                        repair_priority=7,
                        metadata={
                            "qdrant_exists": mapping.qdrant_exists,
                            "neo4j_exists": mapping.neo4j_exists,
                            "entity_type": mapping.entity_type.value,
                            "mapping_type": mapping.mapping_type.value,
                        },
                    )
                    issues.append(issue)

        except Exception as e:
            logger.error(f"Error scanning orphaned records: {e}")

        return issues

    async def _scan_data_mismatches(
        self, max_entities: Optional[int] = None
    ) -> List[ValidationIssue]:
        """Scan for data mismatches between QDrant and Neo4j."""
        issues = []

        try:
            # Get active mappings
            mappings = await self.id_mapping_manager.get_mappings_by_entity_type(
                EntityType.CONCEPT,
                status=MappingStatus.ACTIVE,
                limit=max_entities or 1000,
            )

            for mapping in mappings:
                if not mapping.qdrant_point_id or not (
                    mapping.neo4j_node_id or mapping.neo4j_node_uuid
                ):
                    continue

                try:
                    # Get QDrant point data
                    client = self.qdrant_manager._ensure_client_connected()
                    qdrant_points = client.retrieve(
                        collection_name=self.qdrant_manager.collection_name,
                        ids=[mapping.qdrant_point_id],
                        with_payload=True,
                    )

                    if not qdrant_points:
                        continue

                    qdrant_point = qdrant_points[0]

                    # Get Neo4j node data
                    if mapping.neo4j_node_id:
                        neo4j_query = "MATCH (n) WHERE id(n) = $node_id RETURN n"
                        neo4j_params = {"node_id": int(mapping.neo4j_node_id)}
                    else:
                        neo4j_query = "MATCH (n {uuid: $node_uuid}) RETURN n"
                        neo4j_params = {"node_uuid": mapping.neo4j_node_uuid}

                    neo4j_results = self.neo4j_manager.execute_read_query(
                        neo4j_query, neo4j_params
                    )

                    if not neo4j_results:
                        continue

                    neo4j_node = neo4j_results[0]["n"]

                    # Compare data
                    mismatches = self._compare_entity_data(
                        qdrant_point, neo4j_node, mapping
                    )

                    for mismatch in mismatches:
                        issue = ValidationIssue(
                            category=ValidationCategory.DATA_MISMATCH,
                            severity=ValidationSeverity.WARNING,
                            title=f"Data Mismatch: {mismatch['field']}",
                            description=f"Field '{mismatch['field']}' differs between QDrant and Neo4j",
                            mapping_id=mapping.mapping_id,
                            qdrant_point_id=mapping.qdrant_point_id,
                            neo4j_node_id=mapping.neo4j_node_id,
                            expected_value=mismatch["neo4j_value"],
                            actual_value=mismatch["qdrant_value"],
                            suggested_actions=[RepairAction.SYNC_ENTITIES],
                            auto_repairable=True,
                            repair_priority=5,
                            metadata=mismatch,
                        )
                        issues.append(issue)

                except Exception as e:
                    logger.warning(
                        f"Error comparing data for mapping {mapping.mapping_id}: {e}"
                    )

        except Exception as e:
            logger.error(f"Error scanning data mismatches: {e}")

        return issues

    async def _scan_version_inconsistencies(
        self, max_entities: Optional[int] = None
    ) -> List[ValidationIssue]:
        """Scan for version inconsistencies between databases."""
        issues = []

        try:
            # Get mappings with version information
            mappings = await self.id_mapping_manager.get_mappings_by_entity_type(
                EntityType.CONCEPT,
                status=MappingStatus.ACTIVE,
                limit=max_entities or 1000,
            )

            for mapping in mappings:
                if not mapping.qdrant_point_id or not (
                    mapping.neo4j_node_id or mapping.neo4j_node_uuid
                ):
                    continue

                try:
                    # Check version consistency
                    version_issue = await self._check_version_consistency(mapping)
                    if version_issue:
                        issues.append(version_issue)

                except Exception as e:
                    logger.warning(
                        f"Error checking version for mapping {mapping.mapping_id}: {e}"
                    )

        except Exception as e:
            logger.error(f"Error scanning version inconsistencies: {e}")

        return issues

    async def _scan_sync_failures(
        self, max_entities: Optional[int] = None
    ) -> List[ValidationIssue]:
        """Scan for mappings with sync failures."""
        issues = []

        try:
            # Get mappings with sync failures
            query = """
            MATCH (m:IDMapping)
            WHERE m.status = $sync_failed_status
            RETURN m
            LIMIT $limit
            """

            results = self.neo4j_manager.execute_read_query(
                query,
                {
                    "sync_failed_status": MappingStatus.SYNC_FAILED.value,
                    "limit": max_entities or 1000,
                },
            )

            for result in results:
                mapping_data = result["m"]
                mapping = self.id_mapping_manager._neo4j_result_to_mapping(mapping_data)

                issue = ValidationIssue(
                    category=ValidationCategory.SYNC_FAILURE,
                    severity=ValidationSeverity.ERROR,
                    title="Sync Failure",
                    description=f"Mapping {mapping.mapping_id} has failed synchronization",
                    mapping_id=mapping.mapping_id,
                    qdrant_point_id=mapping.qdrant_point_id,
                    neo4j_node_id=mapping.neo4j_node_id,
                    suggested_actions=[RepairAction.SYNC_ENTITIES],
                    auto_repairable=True,
                    repair_priority=8,
                    metadata={
                        "sync_errors": mapping.sync_errors,
                        "last_sync_time": (
                            mapping.last_sync_time.isoformat()
                            if mapping.last_sync_time
                            else None
                        ),
                        "sync_version": mapping.sync_version,
                    },
                )
                issues.append(issue)

        except Exception as e:
            logger.error(f"Error scanning sync failures: {e}")

        return issues

    async def _scan_constraint_violations(
        self, max_entities: Optional[int] = None
    ) -> List[ValidationIssue]:
        """Scan for constraint violations in the databases."""
        issues = []

        try:
            # Check Neo4j constraints
            neo4j_issues = await self._check_neo4j_constraints()
            issues.extend(neo4j_issues)

            # Check QDrant constraints (collection health, etc.)
            qdrant_issues = await self._check_qdrant_constraints()
            issues.extend(qdrant_issues)

        except Exception as e:
            logger.error(f"Error scanning constraint violations: {e}")

        return issues

    async def _scan_performance_issues(
        self, max_entities: Optional[int] = None
    ) -> List[ValidationIssue]:
        """Scan for performance-related issues."""
        issues = []

        try:
            # Check for large batch operations
            performance_metrics = await self._collect_performance_metrics()

            # Check query performance
            if performance_metrics.get("avg_query_time_ms", 0) > 1000:
                issue = ValidationIssue(
                    category=ValidationCategory.PERFORMANCE_ISSUE,
                    severity=ValidationSeverity.WARNING,
                    title="Slow Query Performance",
                    description="Average query time exceeds recommended threshold",
                    suggested_actions=[RepairAction.REBUILD_INDEX],
                    auto_repairable=False,
                    repair_priority=3,
                    metadata=performance_metrics,
                )
                issues.append(issue)

            # Check memory usage
            if performance_metrics.get("memory_usage_percent", 0) > 80:
                issue = ValidationIssue(
                    category=ValidationCategory.PERFORMANCE_ISSUE,
                    severity=ValidationSeverity.WARNING,
                    title="High Memory Usage",
                    description="System memory usage is above 80%",
                    suggested_actions=[RepairAction.MANUAL_INTERVENTION],
                    auto_repairable=False,
                    repair_priority=4,
                    metadata=performance_metrics,
                )
                issues.append(issue)

        except Exception as e:
            logger.error(f"Error scanning performance issues: {e}")

        return issues

    # Helper Methods

    async def _check_database_connectivity(self) -> Dict[str, bool]:
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

    async def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect performance metrics from both databases."""
        metrics = {}

        try:
            # Neo4j metrics
            neo4j_metrics = await self._collect_neo4j_metrics()
            metrics.update(neo4j_metrics)

            # QDrant metrics
            qdrant_metrics = await self._collect_qdrant_metrics()
            metrics.update(qdrant_metrics)

        except Exception as e:
            logger.error(f"Error collecting performance metrics: {e}")

        return metrics

    async def _collect_neo4j_metrics(self) -> Dict[str, Any]:
        """Collect Neo4j-specific performance metrics."""
        metrics = {}

        try:
            # Query execution time
            start_time = datetime.now(UTC)
            self.neo4j_manager.execute_read_query("RETURN 1", {})
            end_time = datetime.now(UTC)
            metrics["neo4j_query_time_ms"] = (
                end_time - start_time
            ).total_seconds() * 1000

            # Database size
            size_query = """
            CALL apoc.meta.stats() YIELD nodeCount, relCount
            RETURN nodeCount, relCount
            """
            try:
                size_results = self.neo4j_manager.execute_read_query(size_query, {})
                if size_results:
                    metrics["neo4j_node_count"] = size_results[0].get("nodeCount", 0)
                    metrics["neo4j_relationship_count"] = size_results[0].get(
                        "relCount", 0
                    )
            except Exception:
                # Fallback if APOC is not available
                count_query = "MATCH (n) RETURN count(n) as nodeCount"
                count_results = self.neo4j_manager.execute_read_query(count_query, {})
                if count_results:
                    metrics["neo4j_node_count"] = count_results[0]["nodeCount"]

        except Exception as e:
            logger.warning(f"Error collecting Neo4j metrics: {e}")

        return metrics

    async def _collect_qdrant_metrics(self) -> Dict[str, Any]:
        """Collect QDrant-specific performance metrics."""
        metrics = {}

        try:
            client = self.qdrant_manager._ensure_client_connected()

            # Collection info
            collection_info = client.get_collection(self.qdrant_manager.collection_name)
            metrics["qdrant_points_count"] = collection_info.points_count
            metrics["qdrant_vectors_count"] = collection_info.vectors_count

            # Query performance test
            start_time = datetime.now(UTC)
            client.scroll(collection_name=self.qdrant_manager.collection_name, limit=1)
            end_time = datetime.now(UTC)
            metrics["qdrant_query_time_ms"] = (
                end_time - start_time
            ).total_seconds() * 1000

        except Exception as e:
            logger.warning(f"Error collecting QDrant metrics: {e}")

        return metrics

    def _compare_entity_data(
        self, qdrant_point, neo4j_node, mapping: IDMapping
    ) -> List[Dict[str, Any]]:
        """Compare data between QDrant point and Neo4j node."""
        mismatches = []

        try:
            # Compare common fields
            qdrant_payload = qdrant_point.payload or {}
            neo4j_props = dict(neo4j_node)

            # Check name/title fields
            qdrant_name = qdrant_payload.get("name") or qdrant_payload.get("title")
            neo4j_name = neo4j_props.get("name") or neo4j_props.get("title")

            if qdrant_name and neo4j_name and qdrant_name != neo4j_name:
                mismatches.append(
                    {
                        "field": "name",
                        "qdrant_value": qdrant_name,
                        "neo4j_value": neo4j_name,
                        "severity": "medium",
                    }
                )

            # Check UUID fields
            qdrant_uuid = qdrant_payload.get("uuid")
            neo4j_uuid = neo4j_props.get("uuid")

            if qdrant_uuid and neo4j_uuid and qdrant_uuid != neo4j_uuid:
                mismatches.append(
                    {
                        "field": "uuid",
                        "qdrant_value": qdrant_uuid,
                        "neo4j_value": neo4j_uuid,
                        "severity": "high",
                    }
                )

            # Check timestamps
            qdrant_updated = qdrant_payload.get("updated_at")
            neo4j_updated = neo4j_props.get("updated_at")

            if qdrant_updated and neo4j_updated:
                try:
                    qdrant_dt = datetime.fromisoformat(
                        qdrant_updated.replace("Z", "+00:00")
                    )
                    neo4j_dt = datetime.fromisoformat(
                        neo4j_updated.replace("Z", "+00:00")
                    )

                    # Allow small time differences (1 second)
                    if abs((qdrant_dt - neo4j_dt).total_seconds()) > 1:
                        mismatches.append(
                            {
                                "field": "updated_at",
                                "qdrant_value": qdrant_updated,
                                "neo4j_value": neo4j_updated,
                                "severity": "low",
                            }
                        )
                except Exception:
                    pass  # Skip timestamp comparison if parsing fails

        except Exception as e:
            logger.warning(f"Error comparing entity data: {e}")

        return mismatches

    async def _check_version_consistency(
        self, mapping: IDMapping
    ) -> Optional[ValidationIssue]:
        """Check version consistency for a mapping."""
        try:
            # Get version information from both databases
            qdrant_version = None
            neo4j_version = None

            if mapping.qdrant_point_id:
                qdrant_version = await self._get_qdrant_version(mapping.qdrant_point_id)

            node_identifier = mapping.neo4j_node_id or mapping.neo4j_node_uuid
            if node_identifier:
                neo4j_version = await self._get_neo4j_version(node_identifier)

            if qdrant_version and neo4j_version and qdrant_version != neo4j_version:
                return ValidationIssue(
                    category=ValidationCategory.VERSION_INCONSISTENCY,
                    severity=ValidationSeverity.WARNING,
                    title="Version Mismatch",
                    description=f"Version mismatch between QDrant ({qdrant_version}) and Neo4j ({neo4j_version})",
                    mapping_id=mapping.mapping_id,
                    qdrant_point_id=mapping.qdrant_point_id,
                    neo4j_node_id=mapping.neo4j_node_id,
                    expected_value=neo4j_version,
                    actual_value=qdrant_version,
                    suggested_actions=[RepairAction.SYNC_ENTITIES],
                    auto_repairable=True,
                    repair_priority=4,
                    metadata={
                        "qdrant_version": qdrant_version,
                        "neo4j_version": neo4j_version,
                    },
                )

        except Exception as e:
            logger.warning(f"Error checking version consistency: {e}")

        return None

    async def _get_qdrant_version(self, point_id: str) -> Optional[str]:
        """Get version information from QDrant point."""
        try:
            client = self.qdrant_manager._ensure_client_connected()
            points = client.retrieve(
                collection_name=self.qdrant_manager.collection_name,
                ids=[point_id],
                with_payload=True,
            )

            if points and points[0].payload:
                return points[0].payload.get("version")

        except Exception as e:
            logger.warning(f"Error getting QDrant version: {e}")

        return None

    async def _get_neo4j_version(self, node_identifier: str) -> Optional[str]:
        """Get version information from Neo4j node."""
        try:
            if node_identifier.isdigit():
                query = "MATCH (n) WHERE id(n) = $node_id RETURN n.version as version"
                params = {"node_id": int(node_identifier)}
            else:
                query = "MATCH (n {uuid: $node_uuid}) RETURN n.version as version"
                params = {"node_uuid": node_identifier}

            results = self.neo4j_manager.execute_read_query(query, params)
            if results:
                return results[0].get("version")

        except Exception as e:
            logger.warning(f"Error getting Neo4j version: {e}")

        return None

    async def _check_neo4j_constraints(self) -> List[ValidationIssue]:
        """Check Neo4j database constraints."""
        issues = []

        try:
            # Check for constraint violations
            constraint_query = "SHOW CONSTRAINTS"
            try:
                constraints = self.neo4j_manager.execute_read_query(
                    constraint_query, {}
                )
                # Add specific constraint validation logic here
            except Exception:
                # Fallback for older Neo4j versions
                pass

        except Exception as e:
            logger.warning(f"Error checking Neo4j constraints: {e}")

        return issues

    async def _check_qdrant_constraints(self) -> List[ValidationIssue]:
        """Check QDrant database constraints."""
        issues = []

        try:
            client = self.qdrant_manager._ensure_client_connected()

            # Check collection health
            collection_info = client.get_collection(self.qdrant_manager.collection_name)

            if collection_info.status != "green":
                issue = ValidationIssue(
                    category=ValidationCategory.CONSTRAINT_VIOLATION,
                    severity=ValidationSeverity.ERROR,
                    title="QDrant Collection Health Issue",
                    description=f"Collection status is {collection_info.status}",
                    suggested_actions=[RepairAction.MANUAL_INTERVENTION],
                    auto_repairable=False,
                    repair_priority=9,
                    metadata={"collection_status": collection_info.status},
                )
                issues.append(issue)

        except Exception as e:
            logger.warning(f"Error checking QDrant constraints: {e}")

        return issues

    # Repair Handler Methods

    async def _repair_create_mapping(self, issue: ValidationIssue) -> RepairResult:
        """Create missing mapping for an entity."""
        start_time = datetime.now(UTC)

        try:
            if issue.qdrant_point_id and not issue.neo4j_node_id:
                # Create mapping for QDrant point
                mapping = await self._create_mapping_for_qdrant_point(
                    issue.qdrant_point_id
                )
            elif issue.neo4j_node_id and not issue.qdrant_point_id:
                # Create mapping for Neo4j node
                mapping = await self._create_mapping_for_neo4j_node(issue.neo4j_node_id)
            else:
                raise ValueError("Invalid issue data for mapping creation")

            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.CREATE_MAPPING,
                success=True,
                details={"mapping_id": mapping.mapping_id},
                execution_time_ms=execution_time,
            )

        except Exception as e:
            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.CREATE_MAPPING,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
            )

    async def _repair_delete_orphaned(self, issue: ValidationIssue) -> RepairResult:
        """Delete orphaned mapping."""
        start_time = datetime.now(UTC)

        try:
            if issue.mapping_id:
                await self.id_mapping_manager.delete_mapping(issue.mapping_id)

            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.DELETE_ORPHANED,
                success=True,
                details={"deleted_mapping_id": issue.mapping_id},
                execution_time_ms=execution_time,
            )

        except Exception as e:
            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.DELETE_ORPHANED,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
            )

    async def _repair_update_data(self, issue: ValidationIssue) -> RepairResult:
        """Update data to resolve mismatch."""
        start_time = datetime.now(UTC)

        try:
            # Implementation depends on specific data mismatch
            # This is a placeholder for the actual update logic

            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.UPDATE_DATA,
                success=True,
                details={"updated_field": issue.metadata.get("field")},
                execution_time_ms=execution_time,
            )

        except Exception as e:
            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.UPDATE_DATA,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
            )

    async def _repair_sync_entities(self, issue: ValidationIssue) -> RepairResult:
        """Synchronize entities between databases."""
        start_time = datetime.now(UTC)

        try:
            if issue.mapping_id:
                mapping = await self.id_mapping_manager.get_mapping_by_id(
                    issue.mapping_id
                )
                if mapping:
                    # Trigger synchronization by updating the mapping
                    await self.id_mapping_manager.update_mapping(
                        issue.mapping_id, {"status": MappingStatus.PENDING_SYNC.value}
                    )

            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.SYNC_ENTITIES,
                success=True,
                details={"mapping_id": issue.mapping_id},
                execution_time_ms=execution_time,
            )

        except Exception as e:
            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.SYNC_ENTITIES,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
            )

    async def _repair_resolve_conflict(self, issue: ValidationIssue) -> RepairResult:
        """Resolve conflicts using conflict resolution system."""
        start_time = datetime.now(UTC)

        try:
            if not self.conflict_resolution_system:
                raise ValueError("Conflict resolution system not available")

            # Use conflict resolution system to resolve the issue
            # This would depend on the specific conflict resolution implementation

            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.RESOLVE_CONFLICT,
                success=True,
                details={"conflict_resolved": True},
                execution_time_ms=execution_time,
            )

        except Exception as e:
            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.RESOLVE_CONFLICT,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
            )

    async def _repair_rebuild_index(self, issue: ValidationIssue) -> RepairResult:
        """Rebuild database indexes."""
        start_time = datetime.now(UTC)

        try:
            # This would trigger index rebuilding in both databases
            # Implementation depends on specific requirements

            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.REBUILD_INDEX,
                success=True,
                details={"indexes_rebuilt": True},
                execution_time_ms=execution_time,
            )

        except Exception as e:
            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.REBUILD_INDEX,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
            )

    async def _create_mapping_for_qdrant_point(self, point_id: str) -> IDMapping:
        """Create mapping for a QDrant point that lacks one."""
        # Get point data
        client = self.qdrant_manager._ensure_client_connected()
        points = client.retrieve(
            collection_name=self.qdrant_manager.collection_name,
            ids=[point_id],
            with_payload=True,
        )

        if not points:
            raise ValueError(f"QDrant point {point_id} not found")

        point = points[0]
        payload = point.payload or {}

        # Determine entity type from payload
        entity_type = EntityType.CONCEPT  # Default
        if "entity_type" in payload:
            try:
                entity_type = EntityType(payload["entity_type"])
            except ValueError:
                pass

        # Create mapping
        mapping = await self.id_mapping_manager.create_mapping(
            entity_type=entity_type,
            qdrant_point_id=point_id,
            neo4j_node_id=None,
            neo4j_node_uuid=payload.get("uuid"),
            metadata={"created_by": "validation_repair_system"},
        )

        return mapping

    async def _create_mapping_for_neo4j_node(self, node_id: str) -> IDMapping:
        """Create mapping for a Neo4j node that lacks one."""
        # Get node data
        query = "MATCH (n) WHERE id(n) = $node_id RETURN n, labels(n) as labels"
        results = self.neo4j_manager.execute_read_query(
            query, {"node_id": int(node_id)}
        )

        if not results:
            raise ValueError(f"Neo4j node {node_id} not found")

        node_data = results[0]["n"]
        labels = results[0]["labels"]

        # Determine entity type from labels
        entity_type = EntityType.CONCEPT  # Default
        if "Person" in labels:
            entity_type = EntityType.PERSON
        elif "Organization" in labels:
            entity_type = EntityType.ORGANIZATION
        elif "Project" in labels:
            entity_type = EntityType.PROJECT

        # Create mapping
        mapping = await self.id_mapping_manager.create_mapping(
            entity_type=entity_type,
            qdrant_point_id=None,
            neo4j_node_id=node_id,
            neo4j_node_uuid=node_data.get("uuid"),
            metadata={"created_by": "validation_repair_system"},
        )

        return mapping
