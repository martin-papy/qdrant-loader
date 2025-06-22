"""Tests for validation repair models."""

from datetime import UTC, datetime

from qdrant_loader.core.types import EntityType
from qdrant_loader.core.validation_repair.models import (
    RepairAction,
    RepairResult,
    ValidationCategory,
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
)


class TestValidationSeverity:
    """Test ValidationSeverity enum."""

    def test_severity_values(self):
        """Test ValidationSeverity enum values."""
        assert ValidationSeverity.INFO.value == "info"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.CRITICAL.value == "critical"

    def test_severity_count(self):
        """Test that all expected severities are present."""
        assert len(ValidationSeverity) == 4


class TestValidationCategory:
    """Test ValidationCategory enum."""

    def test_category_values(self):
        """Test ValidationCategory enum values."""
        assert ValidationCategory.MISSING_MAPPING.value == "missing_mapping"
        assert ValidationCategory.ORPHANED_RECORD.value == "orphaned_record"
        assert ValidationCategory.DATA_MISMATCH.value == "data_mismatch"
        assert ValidationCategory.VERSION_INCONSISTENCY.value == "version_inconsistency"
        assert ValidationCategory.SYNC_FAILURE.value == "sync_failure"
        assert ValidationCategory.CONSTRAINT_VIOLATION.value == "constraint_violation"
        assert ValidationCategory.PERFORMANCE_ISSUE.value == "performance_issue"

    def test_category_count(self):
        """Test that all expected categories are present."""
        assert len(ValidationCategory) == 7


class TestRepairAction:
    """Test RepairAction enum."""

    def test_action_values(self):
        """Test RepairAction enum values."""
        assert RepairAction.CREATE_MAPPING.value == "create_mapping"
        assert RepairAction.DELETE_ORPHANED.value == "delete_orphaned"
        assert RepairAction.UPDATE_DATA.value == "update_data"
        assert RepairAction.SYNC_ENTITIES.value == "sync_entities"
        assert RepairAction.RESOLVE_CONFLICT.value == "resolve_conflict"
        assert RepairAction.REBUILD_INDEX.value == "rebuild_index"
        assert RepairAction.MANUAL_INTERVENTION.value == "manual_intervention"

    def test_action_count(self):
        """Test that all expected actions are present."""
        assert len(RepairAction) == 7


class TestValidationIssue:
    """Test ValidationIssue dataclass."""

    def test_default_values(self):
        """Test default validation issue values."""
        issue = ValidationIssue()

        # UUID should be generated
        assert issue.issue_id is not None
        assert len(issue.issue_id) == 36  # UUID length

        # Default values
        assert issue.category == ValidationCategory.DATA_MISMATCH
        assert issue.severity == ValidationSeverity.WARNING
        assert issue.title == ""
        assert issue.description == ""
        assert issue.entity_id is None
        assert issue.entity_type is None
        assert issue.qdrant_point_id is None
        assert issue.neo4j_node_id is None
        assert issue.mapping_id is None
        assert issue.expected_value is None
        assert issue.actual_value is None
        assert issue.metadata == {}
        assert issue.suggested_actions == []
        assert issue.auto_repairable is False
        assert issue.repair_priority == 5
        assert isinstance(issue.detected_at, datetime)
        assert issue.resolved_at is None
        assert issue.resolution_notes is None

    def test_custom_values(self):
        """Test validation issue with custom values."""
        detected_time = datetime(2024, 1, 1, tzinfo=UTC)
        resolved_time = datetime(2024, 1, 2, tzinfo=UTC)

        issue = ValidationIssue(
            category=ValidationCategory.MISSING_MAPPING,
            severity=ValidationSeverity.CRITICAL,
            title="Critical Issue",
            description="A critical validation issue",
            entity_id="entity_123",
            entity_type=EntityType.PROJECT,
            qdrant_point_id="point_456",
            neo4j_node_id="node_789",
            mapping_id="mapping_101",
            expected_value="expected",
            actual_value="actual",
            metadata={"key": "value"},
            suggested_actions=[RepairAction.CREATE_MAPPING, RepairAction.SYNC_ENTITIES],
            auto_repairable=True,
            repair_priority=9,
            detected_at=detected_time,
            resolved_at=resolved_time,
            resolution_notes="Fixed manually",
        )

        assert issue.category == ValidationCategory.MISSING_MAPPING
        assert issue.severity == ValidationSeverity.CRITICAL
        assert issue.title == "Critical Issue"
        assert issue.description == "A critical validation issue"
        assert issue.entity_id == "entity_123"
        assert issue.entity_type == EntityType.PROJECT
        assert issue.qdrant_point_id == "point_456"
        assert issue.neo4j_node_id == "node_789"
        assert issue.mapping_id == "mapping_101"
        assert issue.expected_value == "expected"
        assert issue.actual_value == "actual"
        assert issue.metadata == {"key": "value"}
        assert issue.suggested_actions == [
            RepairAction.CREATE_MAPPING,
            RepairAction.SYNC_ENTITIES,
        ]
        assert issue.auto_repairable is True
        assert issue.repair_priority == 9
        assert issue.detected_at == detected_time
        assert issue.resolved_at == resolved_time
        assert issue.resolution_notes == "Fixed manually"

    def test_to_dict_complete(self):
        """Test conversion to dictionary with all fields."""
        detected_time = datetime(2024, 1, 1, tzinfo=UTC)
        resolved_time = datetime(2024, 1, 2, tzinfo=UTC)

        issue = ValidationIssue(
            category=ValidationCategory.ORPHANED_RECORD,
            severity=ValidationSeverity.ERROR,
            title="Orphaned Record",
            description="Record has no mapping",
            entity_id="entity_456",
            entity_type=EntityType.PERSON,
            qdrant_point_id="point_789",
            neo4j_node_id="node_123",
            mapping_id="mapping_456",
            expected_value={"status": "active"},
            actual_value={"status": "inactive"},
            metadata={"source": "migration"},
            suggested_actions=[RepairAction.DELETE_ORPHANED],
            auto_repairable=True,
            repair_priority=7,
            detected_at=detected_time,
            resolved_at=resolved_time,
            resolution_notes="Automatically resolved",
        )

        result = issue.to_dict()

        expected_keys = {
            "issue_id",
            "category",
            "severity",
            "title",
            "description",
            "entity_id",
            "entity_type",
            "qdrant_point_id",
            "neo4j_node_id",
            "mapping_id",
            "expected_value",
            "actual_value",
            "metadata",
            "suggested_actions",
            "auto_repairable",
            "repair_priority",
            "detected_at",
            "resolved_at",
            "resolution_notes",
        }

        assert set(result.keys()) == expected_keys
        assert result["category"] == "orphaned_record"
        assert result["severity"] == "error"
        assert result["title"] == "Orphaned Record"
        assert result["entity_type"] == "Person"
        assert result["suggested_actions"] == ["delete_orphaned"]
        assert result["detected_at"] == detected_time.isoformat()
        assert result["resolved_at"] == resolved_time.isoformat()

    def test_to_dict_minimal(self):
        """Test conversion to dictionary with minimal fields."""
        issue = ValidationIssue(title="Basic Issue", description="A basic issue")

        result = issue.to_dict()

        assert result["title"] == "Basic Issue"
        assert result["description"] == "A basic issue"
        assert result["entity_type"] is None
        assert result["resolved_at"] is None
        assert result["suggested_actions"] == []


class TestRepairResult:
    """Test RepairResult dataclass."""

    def test_default_values(self):
        """Test default repair result values."""
        result = RepairResult(
            issue_id="issue_123", action_taken=RepairAction.UPDATE_DATA, success=True
        )

        assert result.issue_id == "issue_123"
        assert result.action_taken == RepairAction.UPDATE_DATA
        assert result.success is True
        assert result.error_message is None
        assert result.details == {}
        assert result.execution_time_ms == 0.0

    def test_custom_values(self):
        """Test repair result with custom values."""
        result = RepairResult(
            issue_id="issue_456",
            action_taken=RepairAction.CREATE_MAPPING,
            success=False,
            error_message="Connection failed",
            details={"retry_count": 3, "last_error": "timeout"},
            execution_time_ms=150.5,
        )

        assert result.issue_id == "issue_456"
        assert result.action_taken == RepairAction.CREATE_MAPPING
        assert result.success is False
        assert result.error_message == "Connection failed"
        assert result.details == {"retry_count": 3, "last_error": "timeout"}
        assert result.execution_time_ms == 150.5

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = RepairResult(
            issue_id="issue_789",
            action_taken=RepairAction.SYNC_ENTITIES,
            success=True,
            details={"entities_synced": 42},
            execution_time_ms=75.25,
        )

        dict_result = result.to_dict()

        expected_keys = {
            "issue_id",
            "action_taken",
            "success",
            "error_message",
            "details",
            "execution_time_ms",
        }

        assert set(dict_result.keys()) == expected_keys
        assert dict_result["issue_id"] == "issue_789"
        assert dict_result["action_taken"] == "sync_entities"
        assert dict_result["success"] is True
        assert dict_result["error_message"] is None
        assert dict_result["details"] == {"entities_synced": 42}
        assert dict_result["execution_time_ms"] == 75.25


class TestValidationReport:
    """Test ValidationReport dataclass."""

    def test_default_values(self):
        """Test default validation report values."""
        report = ValidationReport()

        # UUID should be generated
        assert report.report_id is not None
        assert len(report.report_id) == 36  # UUID length

        # Default values
        assert isinstance(report.generated_at, datetime)
        assert report.total_issues == 0
        assert report.critical_issues == 0
        assert report.error_issues == 0
        assert report.warning_issues == 0
        assert report.info_issues == 0
        assert report.auto_repairable_issues == 0
        assert report.issues_by_category == {}
        assert report.issues == []
        assert report.system_health_score == 100.0
        assert report.database_connectivity == {}
        assert report.performance_metrics == {}
        assert report.validation_duration_ms == 0.0
        assert report.scanned_entities == {}

    def test_add_issue_critical(self):
        """Test adding a critical issue to report."""
        report = ValidationReport()
        issue = ValidationIssue(
            category=ValidationCategory.SYNC_FAILURE,
            severity=ValidationSeverity.CRITICAL,
            auto_repairable=True,
        )

        report.add_issue(issue)

        assert report.total_issues == 1
        assert report.critical_issues == 1
        assert report.error_issues == 0
        assert report.warning_issues == 0
        assert report.info_issues == 0
        assert report.auto_repairable_issues == 1
        assert report.issues_by_category[ValidationCategory.SYNC_FAILURE] == 1
        assert len(report.issues) == 1
        assert report.issues[0] == issue

    def test_add_issue_error(self):
        """Test adding an error issue to report."""
        report = ValidationReport()
        issue = ValidationIssue(
            category=ValidationCategory.DATA_MISMATCH,
            severity=ValidationSeverity.ERROR,
            auto_repairable=False,
        )

        report.add_issue(issue)

        assert report.total_issues == 1
        assert report.critical_issues == 0
        assert report.error_issues == 1
        assert report.warning_issues == 0
        assert report.info_issues == 0
        assert report.auto_repairable_issues == 0
        assert report.issues_by_category[ValidationCategory.DATA_MISMATCH] == 1

    def test_add_issue_warning(self):
        """Test adding a warning issue to report."""
        report = ValidationReport()
        issue = ValidationIssue(
            category=ValidationCategory.PERFORMANCE_ISSUE,
            severity=ValidationSeverity.WARNING,
        )

        report.add_issue(issue)

        assert report.total_issues == 1
        assert report.critical_issues == 0
        assert report.error_issues == 0
        assert report.warning_issues == 1
        assert report.info_issues == 0
        assert report.issues_by_category[ValidationCategory.PERFORMANCE_ISSUE] == 1

    def test_add_issue_info(self):
        """Test adding an info issue to report."""
        report = ValidationReport()
        issue = ValidationIssue(
            category=ValidationCategory.VERSION_INCONSISTENCY,
            severity=ValidationSeverity.INFO,
        )

        report.add_issue(issue)

        assert report.total_issues == 1
        assert report.critical_issues == 0
        assert report.error_issues == 0
        assert report.warning_issues == 0
        assert report.info_issues == 1
        assert report.issues_by_category[ValidationCategory.VERSION_INCONSISTENCY] == 1

    def test_add_multiple_issues_same_category(self):
        """Test adding multiple issues of the same category."""
        report = ValidationReport()

        issue1 = ValidationIssue(
            category=ValidationCategory.MISSING_MAPPING,
            severity=ValidationSeverity.ERROR,
        )
        issue2 = ValidationIssue(
            category=ValidationCategory.MISSING_MAPPING,
            severity=ValidationSeverity.WARNING,
        )

        report.add_issue(issue1)
        report.add_issue(issue2)

        assert report.total_issues == 2
        assert report.error_issues == 1
        assert report.warning_issues == 1
        assert report.issues_by_category[ValidationCategory.MISSING_MAPPING] == 2

    def test_calculate_health_score_no_issues(self):
        """Test health score calculation with no issues."""
        report = ValidationReport()
        report.calculate_health_score()

        assert report.system_health_score == 100.0

    def test_calculate_health_score_with_issues(self):
        """Test health score calculation with various issues."""
        report = ValidationReport()

        # Add issues with different severities
        critical_issue = ValidationIssue(severity=ValidationSeverity.CRITICAL)
        error_issue = ValidationIssue(severity=ValidationSeverity.ERROR)
        warning_issue = ValidationIssue(severity=ValidationSeverity.WARNING)
        info_issue = ValidationIssue(severity=ValidationSeverity.INFO)

        report.add_issue(critical_issue)
        report.add_issue(error_issue)
        report.add_issue(warning_issue)
        report.add_issue(info_issue)

        report.calculate_health_score()

        # Score should be reduced based on weighted severity
        # Critical=20, Error=10, Warning=5, Info=1 = 36 total penalty
        expected_score = 100.0 - 36.0
        assert report.system_health_score == expected_score

    def test_calculate_health_score_capped_at_zero(self):
        """Test health score calculation doesn't go below zero."""
        report = ValidationReport()

        # Add many critical issues to exceed max penalty
        for _ in range(10):
            critical_issue = ValidationIssue(severity=ValidationSeverity.CRITICAL)
            report.add_issue(critical_issue)

        report.calculate_health_score()

        # Score should be capped at 0
        assert report.system_health_score >= 0.0

    def test_to_dict_complete(self):
        """Test conversion to dictionary with complete data."""
        report = ValidationReport(
            total_issues=2,
            critical_issues=1,
            error_issues=1,
            system_health_score=75.0,
            database_connectivity={"neo4j": True, "qdrant": False},
            performance_metrics={"avg_query_time": 150.5},
            validation_duration_ms=5000.0,
            scanned_entities={"documents": 100, "persons": 50},
        )

        # Add some issues
        issue1 = ValidationIssue(
            category=ValidationCategory.SYNC_FAILURE,
            severity=ValidationSeverity.CRITICAL,
        )
        issue2 = ValidationIssue(
            category=ValidationCategory.DATA_MISMATCH, severity=ValidationSeverity.ERROR
        )

        report.issues = [issue1, issue2]
        report.issues_by_category = {
            ValidationCategory.SYNC_FAILURE: 1,
            ValidationCategory.DATA_MISMATCH: 1,
        }

        result = report.to_dict()

        # Check structure
        assert "report_id" in result
        assert "generated_at" in result
        assert "summary" in result
        assert "issues_by_category" in result
        assert "issues" in result
        assert "system_health" in result
        assert "execution_details" in result

        # Check summary
        summary = result["summary"]
        assert summary["total_issues"] == 2
        assert summary["critical_issues"] == 1
        assert summary["error_issues"] == 1
        assert summary["system_health_score"] == 75.0

        # Check issues by category
        assert result["issues_by_category"]["sync_failure"] == 1
        assert result["issues_by_category"]["data_mismatch"] == 1

        # Check issues list
        assert len(result["issues"]) == 2

        # Check system health
        system_health = result["system_health"]
        assert system_health["database_connectivity"] == {
            "neo4j": True,
            "qdrant": False,
        }
        assert system_health["performance_metrics"] == {"avg_query_time": 150.5}

        # Check execution details
        execution = result["execution_details"]
        assert execution["validation_duration_ms"] == 5000.0
        assert execution["scanned_entities"] == {"documents": 100, "persons": 50}

    def test_to_dict_minimal(self):
        """Test conversion to dictionary with minimal data."""
        report = ValidationReport()

        result = report.to_dict()

        # Should have all required keys even with minimal data
        assert "report_id" in result
        assert "generated_at" in result
        assert result["summary"]["total_issues"] == 0
        assert result["issues_by_category"] == {}
        assert result["issues"] == []
        assert result["system_health"]["database_connectivity"] == {}
        assert result["execution_details"]["scanned_entities"] == {}
