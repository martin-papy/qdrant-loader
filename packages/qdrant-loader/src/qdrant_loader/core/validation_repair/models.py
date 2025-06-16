"""
Data models for the validation and repair system.

Contains enums, dataclasses, and other data structures used throughout
the validation and repair workflow.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from ..types import EntityType


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
    entity_id: str | None = None
    entity_type: EntityType | None = None
    qdrant_point_id: str | None = None
    neo4j_node_id: str | None = None
    mapping_id: str | None = None

    # Issue details
    expected_value: Any | None = None
    actual_value: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Resolution information
    suggested_actions: list[RepairAction] = field(default_factory=list)
    auto_repairable: bool = False
    repair_priority: int = 5  # 1-10, higher is more urgent

    # Tracking
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None
    resolution_notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
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
    error_message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
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
    issues_by_category: dict[ValidationCategory, int] = field(default_factory=dict)
    issues: list[ValidationIssue] = field(default_factory=list)

    # System health metrics
    system_health_score: float = 100.0  # 0-100
    database_connectivity: dict[str, bool] = field(default_factory=dict)
    performance_metrics: dict[str, Any] = field(default_factory=dict)

    # Execution details
    validation_duration_ms: float = 0.0
    scanned_entities: dict[str, int] = field(default_factory=dict)

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

    def to_dict(self) -> dict[str, Any]:
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
