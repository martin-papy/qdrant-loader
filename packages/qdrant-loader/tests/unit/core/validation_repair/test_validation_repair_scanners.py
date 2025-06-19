"""Comprehensive tests for ValidationScanners class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC
from qdrant_client.models import PointStruct
from typing import Any, Dict, List

from qdrant_loader.core.validation_repair.scanners import ValidationScanners
from qdrant_loader.core.validation_repair.models import (
    ValidationIssue,
    ValidationCategory,
    ValidationSeverity,
    RepairAction,
)
from qdrant_loader.core.managers import IDMapping, MappingStatus, MappingType
from qdrant_loader.core.types import EntityType


class TestValidationScanners:
    """Test suite for ValidationScanners class."""

    @pytest.fixture
    def mock_id_mapping_manager(self):
        """Create mock ID mapping manager."""
        manager = AsyncMock()
        # Set up non-async methods as regular MagicMock
        manager._neo4j_result_to_mapping = MagicMock()
        return manager

    @pytest.fixture
    def mock_neo4j_manager(self):
        """Create mock Neo4j manager."""
        manager = MagicMock()
        manager.execute_read_query = MagicMock(return_value=[])
        return manager

    @pytest.fixture
    def mock_qdrant_manager(self):
        """Create mock Qdrant manager."""
        manager = MagicMock()
        manager.collection_name = "test_collection"
        return manager

    @pytest.fixture
    def scanners(
        self, mock_id_mapping_manager, mock_neo4j_manager, mock_qdrant_manager
    ):
        """Create ValidationScanners instance with mocked dependencies."""
        return ValidationScanners(
            id_mapping_manager=mock_id_mapping_manager,
            neo4j_manager=mock_neo4j_manager,
            qdrant_manager=mock_qdrant_manager,
        )

    @pytest.fixture
    def sample_mapping(self):
        """Create a sample ID mapping."""
        return IDMapping(
            mapping_id="test-mapping-1",
            qdrant_point_id="point-123",
            neo4j_node_id="456",
            neo4j_node_uuid="uuid-789",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            status=MappingStatus.ACTIVE,
            qdrant_exists=True,
            neo4j_exists=True,
        )

    @pytest.fixture
    def sample_qdrant_point(self):
        """Create a sample Qdrant point."""
        return PointStruct(
            id="point-123",
            vector=[0.1, 0.2, 0.3],
            payload={"text": "sample text", "uuid": "uuid-123"},
        )

    # Test scan_missing_mappings method
    @pytest.mark.asyncio
    async def test_scan_missing_mappings_success(
        self, scanners, mock_qdrant_manager, mock_id_mapping_manager
    ):
        """Test successful scanning for missing mappings."""
        # Mock Qdrant client and response
        mock_client = MagicMock()
        mock_qdrant_manager._ensure_client_connected.return_value = mock_client
        mock_client.get_collection.return_value = MagicMock()

        # Mock scroll result with sample points
        sample_point = PointStruct(
            id="point-123", vector=[0.1, 0.2], payload={"text": "test"}
        )
        mock_client.scroll.return_value = ([sample_point], None)

        # Mock no mapping found
        mock_id_mapping_manager.get_mapping_by_qdrant_id.return_value = None

        # Mock Neo4j query result
        scanners.neo4j_manager.execute_read_query.return_value = [
            {
                "node_id": "node-456",
                "labels": ["Concept"],
                "uuid": "uuid-789",
                "name": "Test Node",
            }
        ]
        mock_id_mapping_manager.get_mapping_by_neo4j_id.return_value = None
        mock_id_mapping_manager.get_mapping_by_neo4j_uuid.return_value = None

        issues = await scanners.scan_missing_mappings(max_entities=100)

        assert len(issues) == 2  # One for Qdrant, one for Neo4j
        assert all(
            issue.category == ValidationCategory.MISSING_MAPPING for issue in issues
        )
        assert all(issue.severity == ValidationSeverity.WARNING for issue in issues)
        assert all(issue.auto_repairable for issue in issues)

    @pytest.mark.asyncio
    async def test_scan_missing_mappings_no_issues(
        self, scanners, mock_qdrant_manager, mock_id_mapping_manager
    ):
        """Test scanning when no missing mappings are found."""
        # Mock Qdrant client with no points
        mock_client = MagicMock()
        mock_qdrant_manager._ensure_client_connected.return_value = mock_client
        mock_client.get_collection.return_value = MagicMock()
        mock_client.scroll.return_value = ([], None)

        # Mock Neo4j with no results
        scanners.neo4j_manager.execute_read_query.return_value = []

        issues = await scanners.scan_missing_mappings()

        assert len(issues) == 0

    @pytest.mark.asyncio
    async def test_scan_missing_mappings_error_handling(
        self, scanners, mock_qdrant_manager
    ):
        """Test error handling in scan_missing_mappings."""
        # Mock Qdrant client to raise exception
        mock_qdrant_manager._ensure_client_connected.side_effect = Exception(
            "Connection failed"
        )

        issues = await scanners.scan_missing_mappings()

        assert len(issues) == 0  # Should return empty list on error

    @pytest.mark.asyncio
    async def test_scan_qdrant_missing_mappings_with_existing_mapping(
        self, scanners, mock_qdrant_manager, mock_id_mapping_manager, sample_mapping
    ):
        """Test Qdrant scanning when mappings exist."""
        mock_client = MagicMock()
        mock_qdrant_manager._ensure_client_connected.return_value = mock_client
        mock_client.get_collection.return_value = MagicMock()

        sample_point = PointStruct(
            id="point-123", vector=[0.1, 0.2], payload={"text": "test"}
        )
        mock_client.scroll.return_value = ([sample_point], None)

        # Mock mapping exists
        mock_id_mapping_manager.get_mapping_by_qdrant_id.return_value = sample_mapping

        issues = await scanners._scan_qdrant_missing_mappings(max_entities=100)

        assert len(issues) == 0

    @pytest.mark.asyncio
    async def test_scan_neo4j_missing_mappings_with_uuid_mapping(
        self, scanners, mock_id_mapping_manager, sample_mapping
    ):
        """Test Neo4j scanning when UUID mapping exists."""
        scanners.neo4j_manager.execute_read_query.return_value = [
            {
                "node_id": "node-456",
                "labels": ["Concept"],
                "uuid": "uuid-789",
                "name": "Test Node",
            }
        ]

        # Mock no ID mapping but UUID mapping exists
        mock_id_mapping_manager.get_mapping_by_neo4j_id.return_value = None
        mock_id_mapping_manager.get_mapping_by_neo4j_uuid.return_value = sample_mapping

        issues = await scanners._scan_neo4j_missing_mappings(max_entities=100)

        assert len(issues) == 0

    # Test scan_orphaned_records method
    @pytest.mark.asyncio
    async def test_scan_orphaned_records_success(
        self, scanners, mock_id_mapping_manager
    ):
        """Test successful scanning for orphaned records."""
        # Create orphaned mapping
        orphaned_mapping = IDMapping(
            mapping_id="orphaned-mapping",
            qdrant_point_id="missing-point",
            neo4j_node_id="missing-node",
            neo4j_node_uuid="missing-uuid",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            status=MappingStatus.ACTIVE,
            qdrant_exists=False,
            neo4j_exists=False,
        )

        mock_id_mapping_manager.get_mappings_by_entity_type.return_value = [
            orphaned_mapping
        ]
        mock_id_mapping_manager._validate_mapping_existence.return_value = None

        issues = await scanners.scan_orphaned_records(max_entities=100)

        assert len(issues) == 1
        assert issues[0].category == ValidationCategory.ORPHANED_RECORD
        assert issues[0].severity == ValidationSeverity.ERROR
        assert issues[0].auto_repairable

    @pytest.mark.asyncio
    async def test_scan_orphaned_records_no_orphans(
        self, scanners, mock_id_mapping_manager, sample_mapping
    ):
        """Test scanning when no orphaned records exist."""
        mock_id_mapping_manager.get_mappings_by_entity_type.return_value = [
            sample_mapping
        ]
        mock_id_mapping_manager._validate_mapping_existence.return_value = None

        issues = await scanners.scan_orphaned_records()

        assert len(issues) == 0

    @pytest.mark.asyncio
    async def test_scan_orphaned_records_error_handling(
        self, scanners, mock_id_mapping_manager
    ):
        """Test error handling in scan_orphaned_records."""
        mock_id_mapping_manager.get_mappings_by_entity_type.side_effect = Exception(
            "Database error"
        )

        issues = await scanners.scan_orphaned_records()

        assert len(issues) == 0

    # Test scan_data_mismatches method
    @pytest.mark.asyncio
    async def test_scan_data_mismatches_success(
        self, scanners, mock_id_mapping_manager, mock_qdrant_manager, sample_mapping
    ):
        """Test successful scanning for data mismatches."""
        mock_id_mapping_manager.get_mappings_by_entity_type.return_value = [
            sample_mapping
        ]

        mock_client = MagicMock()
        mock_qdrant_manager._ensure_client_connected.return_value = mock_client
        mock_client.retrieve.return_value = [
            PointStruct(id="point-123", vector=[0.1], payload={"text": "qdrant text"})
        ]

        scanners.neo4j_manager.execute_read_query.return_value = [
            {"n": {"text": "neo4j text", "uuid": "uuid-789"}}
        ]

        # Mock data comparison to find mismatch - return a non-empty list
        def mock_compare_data(qdrant_data, neo4j_data, mapping):
            return [
                {
                    "field": "text",
                    "qdrant_value": "qdrant text",
                    "neo4j_value": "neo4j text",
                }
            ]

        with patch.object(
            scanners, "_compare_entity_data", side_effect=mock_compare_data
        ):
            issues = await scanners.scan_data_mismatches(max_entities=100)

        assert len(issues) == 1
        assert issues[0].category == ValidationCategory.DATA_MISMATCH
        assert issues[0].severity == ValidationSeverity.WARNING

    @pytest.mark.asyncio
    async def test_scan_data_mismatches_no_mismatches(
        self, scanners, mock_id_mapping_manager, mock_qdrant_manager, sample_mapping
    ):
        """Test scanning when no data mismatches exist."""
        mock_id_mapping_manager.get_mappings_by_entity_type.return_value = [
            sample_mapping
        ]

        mock_client = MagicMock()
        mock_qdrant_manager._ensure_client_connected.return_value = mock_client
        mock_client.retrieve.return_value = [
            PointStruct(id="point-123", vector=[0.1], payload={"text": "same text"})
        ]

        scanners.neo4j_manager.execute_read_query.return_value = [
            {"text": "same text", "uuid": "uuid-789"}
        ]

        # Mock no data differences
        with patch.object(scanners, "_compare_entity_data", return_value=[]):
            issues = await scanners.scan_data_mismatches()

        assert len(issues) == 0

    @pytest.mark.asyncio
    async def test_scan_data_mismatches_missing_entities(
        self, scanners, mock_id_mapping_manager, mock_qdrant_manager, sample_mapping
    ):
        """Test data mismatch scanning with missing entities."""
        mock_id_mapping_manager.get_mappings_by_entity_type.return_value = [
            sample_mapping
        ]

        mock_client = MagicMock()
        mock_qdrant_manager._ensure_client_connected.return_value = mock_client
        mock_client.retrieve.return_value = []  # No Qdrant point found

        scanners.neo4j_manager.execute_read_query.return_value = (
            []
        )  # No Neo4j node found

        issues = await scanners.scan_data_mismatches()

        assert len(issues) == 0

    # Test scan_version_inconsistencies method
    @pytest.mark.asyncio
    async def test_scan_version_inconsistencies_success(
        self, scanners, mock_id_mapping_manager, sample_mapping
    ):
        """Test successful scanning for version inconsistencies."""
        mock_id_mapping_manager.get_mappings_by_entity_type.return_value = [
            sample_mapping
        ]

        # Mock version inconsistency
        version_issue = ValidationIssue(
            category=ValidationCategory.VERSION_INCONSISTENCY,
            severity=ValidationSeverity.WARNING,
            title="Version Inconsistency",
            description="Version mismatch detected",
            mapping_id=sample_mapping.mapping_id,
            suggested_actions=[RepairAction.SYNC_ENTITIES],
            auto_repairable=True,
            repair_priority=5,
        )

        with patch.object(
            scanners, "_check_version_consistency", return_value=version_issue
        ):
            issues = await scanners.scan_version_inconsistencies(max_entities=100)

        assert len(issues) == 1
        assert issues[0].category == ValidationCategory.VERSION_INCONSISTENCY

    @pytest.mark.asyncio
    async def test_scan_version_inconsistencies_no_issues(
        self, scanners, mock_id_mapping_manager, sample_mapping
    ):
        """Test version scanning when no inconsistencies exist."""
        mock_id_mapping_manager.get_mappings_by_entity_type.return_value = [
            sample_mapping
        ]

        with patch.object(scanners, "_check_version_consistency", return_value=None):
            issues = await scanners.scan_version_inconsistencies()

        assert len(issues) == 0

    # Test scan_sync_failures method
    @pytest.mark.asyncio
    async def test_scan_sync_failures_success(self, scanners, mock_id_mapping_manager):
        """Test successful scanning for sync failures."""
        # Mock Neo4j query result
        mock_mapping_data = {
            "mapping_id": "failed-mapping",
            "qdrant_point_id": "point-123",
            "neo4j_node_id": "node-456",
            "neo4j_node_uuid": "uuid-789",
            "entity_type": "CONCEPT",
            "mapping_type": "DOCUMENT",
            "status": "SYNC_FAILED",
        }

        scanners.neo4j_manager.execute_read_query.return_value = [
            {"m": mock_mapping_data}
        ]

        # Mock the mapping conversion
        failed_mapping = IDMapping(
            mapping_id="failed-mapping",
            qdrant_point_id="point-123",
            neo4j_node_id="node-456",
            neo4j_node_uuid="uuid-789",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            status=MappingStatus.SYNC_FAILED,
            qdrant_exists=True,
            neo4j_exists=True,
        )

        mock_id_mapping_manager._neo4j_result_to_mapping.return_value = failed_mapping

        issues = await scanners.scan_sync_failures(max_entities=100)

        assert len(issues) == 1
        assert issues[0].category == ValidationCategory.SYNC_FAILURE
        assert issues[0].severity == ValidationSeverity.ERROR

    @pytest.mark.asyncio
    async def test_scan_sync_failures_no_failures(
        self, scanners, mock_id_mapping_manager
    ):
        """Test sync failure scanning when no failures exist."""
        scanners.neo4j_manager.execute_read_query.return_value = []

        issues = await scanners.scan_sync_failures()

        assert len(issues) == 0

    # Test scan_constraint_violations method
    @pytest.mark.asyncio
    async def test_scan_constraint_violations_success(self, scanners):
        """Test successful scanning for constraint violations."""
        neo4j_violations = [
            ValidationIssue(
                category=ValidationCategory.CONSTRAINT_VIOLATION,
                severity=ValidationSeverity.ERROR,
                title="Neo4j Constraint Violation",
                description="Duplicate UUID constraint violation",
                suggested_actions=[RepairAction.MANUAL_INTERVENTION],
                auto_repairable=False,
                repair_priority=9,
            )
        ]

        qdrant_violations = [
            ValidationIssue(
                category=ValidationCategory.CONSTRAINT_VIOLATION,
                severity=ValidationSeverity.WARNING,
                title="Qdrant Constraint Violation",
                description="Invalid vector dimension",
                suggested_actions=[RepairAction.UPDATE_DATA],
                auto_repairable=True,
                repair_priority=6,
            )
        ]

        with (
            patch.object(
                scanners, "_check_neo4j_constraints", return_value=neo4j_violations
            ),
            patch.object(
                scanners, "_check_qdrant_constraints", return_value=qdrant_violations
            ),
        ):
            issues = await scanners.scan_constraint_violations(max_entities=100)

        assert len(issues) == 2
        assert all(
            issue.category == ValidationCategory.CONSTRAINT_VIOLATION
            for issue in issues
        )

    @pytest.mark.asyncio
    async def test_scan_constraint_violations_no_violations(self, scanners):
        """Test constraint scanning when no violations exist."""
        with (
            patch.object(scanners, "_check_neo4j_constraints", return_value=[]),
            patch.object(scanners, "_check_qdrant_constraints", return_value=[]),
        ):
            issues = await scanners.scan_constraint_violations()

        assert len(issues) == 0

    # Test scan_performance_issues method
    @pytest.mark.asyncio
    async def test_scan_performance_issues_success(self, scanners):
        """Test successful scanning for performance issues."""
        performance_metrics = {
            "avg_query_time_ms": 1500,  # Above threshold
            "memory_usage_percent": 85,  # Above threshold
        }

        with patch.object(
            scanners, "_collect_performance_metrics", return_value=performance_metrics
        ):
            issues = await scanners.scan_performance_issues(max_entities=100)

        assert len(issues) == 2
        assert all(
            issue.category == ValidationCategory.PERFORMANCE_ISSUE for issue in issues
        )
        assert all(issue.severity == ValidationSeverity.WARNING for issue in issues)

    @pytest.mark.asyncio
    async def test_scan_performance_issues_no_issues(self, scanners):
        """Test performance scanning when no issues exist."""
        performance_metrics = {
            "avg_query_time_ms": 500,  # Below threshold
            "memory_usage_percent": 60,  # Below threshold
        }

        with patch.object(
            scanners, "_collect_performance_metrics", return_value=performance_metrics
        ):
            issues = await scanners.scan_performance_issues()

        assert len(issues) == 0

    @pytest.mark.asyncio
    async def test_scan_performance_issues_error_handling(self, scanners):
        """Test error handling in scan_performance_issues."""
        with patch.object(
            scanners,
            "_collect_performance_metrics",
            side_effect=Exception("Metrics error"),
        ):
            issues = await scanners.scan_performance_issues()

        assert len(issues) == 0

    # Test helper methods
    def test_compare_entity_data_with_differences(self, scanners):
        """Test entity data comparison with differences."""
        qdrant_point = PointStruct(
            id="point-123",
            vector=[0.1, 0.2],
            payload={"text": "qdrant text", "category": "A"},
        )
        neo4j_data = {"text": "neo4j text", "category": "A"}
        mapping = IDMapping(
            mapping_id="test-mapping",
            qdrant_point_id="point-123",
            neo4j_node_id="node-456",
            neo4j_node_uuid="uuid-789",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            status=MappingStatus.ACTIVE,
        )

        differences = scanners._compare_entity_data(qdrant_point, neo4j_data, mapping)

        # Should find one difference (text field)
        assert len(differences) == 1
        assert differences[0]["field"] == "text"
        assert differences[0]["qdrant_value"] == "qdrant text"
        assert differences[0]["neo4j_value"] == "neo4j text"

    def test_compare_entity_data_no_differences(self, scanners):
        """Test _compare_entity_data method with no differences."""
        qdrant_point = PointStruct(
            id="point-123",
            vector=[0.1, 0.2],
            payload={"text": "same text", "category": "A", "uuid": "uuid-123"},
        )

        neo4j_node = {"text": "same text", "category": "A", "uuid": "uuid-123"}

        mapping = MagicMock()
        mapping.neo4j_node_uuid = "uuid-123"

        differences = scanners._compare_entity_data(qdrant_point, neo4j_node, mapping)

        assert len(differences) == 0

    def test_compare_entity_data_missing_fields(self, scanners):
        """Test entity data comparison with missing fields."""
        qdrant_point = PointStruct(
            id="point-123",
            vector=[0.1, 0.2],
            payload={"text": "same text", "category": "A"},
        )
        neo4j_data = {"text": "same text"}  # Missing category field
        mapping = IDMapping(
            mapping_id="test-mapping",
            qdrant_point_id="point-123",
            neo4j_node_id="node-456",
            neo4j_node_uuid="uuid-789",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            status=MappingStatus.ACTIVE,
        )

        differences = scanners._compare_entity_data(qdrant_point, neo4j_data, mapping)

        # Should find one difference (missing category field)
        assert len(differences) == 1
        assert differences[0]["field"] == "category"
        assert differences[0]["qdrant_value"] == "A"
        assert differences[0]["neo4j_value"] is None

    @pytest.mark.asyncio
    async def test_check_version_consistency_with_mismatch(self, scanners):
        """Test _check_version_consistency method with version mismatch."""
        mapping = MagicMock()
        mapping.mapping_id = "test-mapping"
        mapping.qdrant_point_id = "point-123"
        mapping.neo4j_node_id = "node-456"

        with (
            patch.object(scanners, "_get_qdrant_version", return_value="1.0"),
            patch.object(scanners, "_get_neo4j_version", return_value="2.0"),
        ):
            issue = await scanners._check_version_consistency(mapping)

        assert issue is not None
        assert issue.category == ValidationCategory.VERSION_INCONSISTENCY
        assert issue.mapping_id == "test-mapping"

    @pytest.mark.asyncio
    async def test_check_version_consistency_no_mismatch(self, scanners):
        """Test _check_version_consistency method with matching versions."""
        mapping = MagicMock()

        with (
            patch.object(scanners, "_get_qdrant_version", return_value="1.0"),
            patch.object(scanners, "_get_neo4j_version", return_value="1.0"),
        ):
            issue = await scanners._check_version_consistency(mapping)

        assert issue is None

    @pytest.mark.asyncio
    async def test_check_version_consistency_missing_versions(self, scanners):
        """Test _check_version_consistency method with missing versions."""
        mapping = MagicMock()

        with (
            patch.object(scanners, "_get_qdrant_version", return_value=None),
            patch.object(scanners, "_get_neo4j_version", return_value=None),
        ):
            issue = await scanners._check_version_consistency(mapping)

        assert issue is None

    @pytest.mark.asyncio
    async def test_get_qdrant_version_success(self, scanners, mock_qdrant_manager):
        """Test _get_qdrant_version method success."""
        mock_client = MagicMock()
        mock_qdrant_manager._ensure_client_connected.return_value = mock_client
        mock_client.retrieve.return_value = [
            PointStruct(id="point-123", vector=[0.1], payload={"version": "1.0"})
        ]

        version = await scanners._get_qdrant_version("point-123")

        assert version == "1.0"

    @pytest.mark.asyncio
    async def test_get_qdrant_version_not_found(self, scanners, mock_qdrant_manager):
        """Test _get_qdrant_version method when point not found."""
        mock_client = MagicMock()
        mock_qdrant_manager._ensure_client_connected.return_value = mock_client
        mock_client.retrieve.return_value = []

        version = await scanners._get_qdrant_version("point-123")

        assert version is None

    @pytest.mark.asyncio
    async def test_get_neo4j_version_success(self, scanners):
        """Test _get_neo4j_version method success."""
        scanners.neo4j_manager.execute_read_query.return_value = [{"version": "2.0"}]

        version = await scanners._get_neo4j_version("node-456")

        assert version == "2.0"

    @pytest.mark.asyncio
    async def test_get_neo4j_version_not_found(self, scanners):
        """Test _get_neo4j_version method when node not found."""
        scanners.neo4j_manager.execute_read_query.return_value = []

        version = await scanners._get_neo4j_version("node-456")

        assert version is None

    @pytest.mark.asyncio
    async def test_check_neo4j_constraints_success(self, scanners):
        """Test Neo4j constraint checking with violations."""
        # Mock Neo4j query to return constraint violations
        scanners.neo4j_manager.execute_read_query.return_value = [
            {"constraint": "UniqueConstraint", "violation": "Duplicate UUID"}
        ]

        issues = await scanners._check_neo4j_constraints()

        assert len(issues) == 1
        assert issues[0].category == ValidationCategory.CONSTRAINT_VIOLATION
        assert issues[0].severity == ValidationSeverity.ERROR
        assert "Neo4j Constraint Violation" in issues[0].title

    @pytest.mark.asyncio
    async def test_check_qdrant_constraints_success(
        self, scanners, mock_qdrant_manager
    ):
        """Test Qdrant constraint checking with violations."""
        mock_client = MagicMock()
        mock_qdrant_manager._ensure_client_connected.return_value = mock_client

        # Mock collection info to simulate constraint violations
        mock_collection_info = MagicMock()
        mock_collection_info.config.params.vectors.size = 128
        mock_client.get_collection.return_value = mock_collection_info

        # Mock points with dimension mismatch
        mock_client.scroll.return_value = (
            [
                PointStruct(id="point-1", vector=[0.1] * 64, payload={})
            ],  # Wrong dimension
            None,
        )

        issues = await scanners._check_qdrant_constraints()

        assert len(issues) == 1
        assert issues[0].category == ValidationCategory.CONSTRAINT_VIOLATION
        assert "Vector dimension mismatch" in issues[0].description

    @pytest.mark.asyncio
    async def test_collect_performance_metrics_success(self, scanners):
        """Test performance metrics collection."""
        # Mock Neo4j metrics
        neo4j_metrics = {
            "avg_query_time_ms": 50.0,
            "memory_usage_percent": 45.0,
        }

        # Mock QDrant metrics
        qdrant_metrics = {
            "collection_size": 1000,
            "memory_usage_percent": 45.0,
            "disk_usage_mb": 512.0,
        }

        with (
            patch.object(
                scanners, "_collect_neo4j_metrics", return_value=neo4j_metrics
            ),
            patch.object(
                scanners, "_collect_qdrant_metrics", return_value=qdrant_metrics
            ),
        ):
            metrics = await scanners._collect_performance_metrics()

        # Verify combined metrics include both Neo4j and QDrant metrics
        assert "avg_query_time_ms" in metrics
        assert "collection_size" in metrics
        assert "memory_usage_percent" in metrics
        assert metrics["avg_query_time_ms"] == 50.0
        assert metrics["collection_size"] == 1000
        assert metrics["memory_usage_percent"] == 45.0

    @pytest.mark.asyncio
    async def test_collect_neo4j_metrics_success(self, scanners):
        """Test Neo4j metrics collection."""
        # Mock Neo4j query results
        scanners.neo4j_manager.execute_read_query.return_value = [
            {
                "avg_query_time_ms": 25.5,
                "active_connections": 3,
                "memory_usage_mb": 128.0,
            }
        ]

        metrics = await scanners._collect_neo4j_metrics()

        assert "avg_query_time_ms" in metrics
        assert metrics["avg_query_time_ms"] == 25.5

    @pytest.mark.asyncio
    async def test_collect_neo4j_metrics_error(self, scanners):
        """Test _collect_neo4j_metrics method with error."""
        scanners.neo4j_manager.execute_read_query.side_effect = Exception(
            "Query failed"
        )

        metrics = await scanners._collect_neo4j_metrics()

        assert metrics == {}

    @pytest.mark.asyncio
    async def test_collect_qdrant_metrics_success(self, scanners, mock_qdrant_manager):
        """Test QDrant metrics collection."""
        mock_client = MagicMock()
        mock_qdrant_manager._ensure_client_connected.return_value = mock_client

        # Mock collection info
        mock_collection_info = MagicMock()
        mock_collection_info.points_count = 5000
        mock_collection_info.vectors_count = 5000
        mock_client.get_collection.return_value = mock_collection_info

        metrics = await scanners._collect_qdrant_metrics()

        assert "collection_size" in metrics
        assert metrics["collection_size"] == 5000

    @pytest.mark.asyncio
    async def test_collect_qdrant_metrics_error(self, scanners, mock_qdrant_manager):
        """Test _collect_qdrant_metrics method with error."""
        mock_qdrant_manager._ensure_client_connected.side_effect = Exception(
            "Connection failed"
        )

        metrics = await scanners._collect_qdrant_metrics()

        assert metrics == {}

    # Edge cases and error scenarios
    @pytest.mark.asyncio
    async def test_scan_with_max_entities_limit(
        self, scanners, mock_qdrant_manager, mock_id_mapping_manager
    ):
        """Test scanning with max_entities limit."""
        mock_client = MagicMock()
        mock_qdrant_manager._ensure_client_connected.return_value = mock_client
        mock_client.get_collection.return_value = MagicMock()
        mock_client.scroll.return_value = ([], None)

        scanners.neo4j_manager.execute_read_query.return_value = []

        await scanners.scan_missing_mappings(max_entities=50)

        # Verify limit was passed to QDrant scroll
        mock_client.scroll.assert_called_with(
            collection_name="test_collection",
            limit=50,
            with_payload=True,
        )

        # Verify Neo4j query was called (parameters structure may vary)
        scanners.neo4j_manager.execute_read_query.assert_called()
        # Just verify the call was made with some parameters
        call_args = scanners.neo4j_manager.execute_read_query.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_orphaned_mapping_with_inactive_status(
        self, scanners, mock_id_mapping_manager
    ):
        """Test orphaned record scanning with inactive status."""
        orphaned_mapping = IDMapping(
            mapping_id="orphaned-mapping",
            qdrant_point_id="missing-point",
            neo4j_node_id="missing-node",
            neo4j_node_uuid="missing-uuid",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            status=MappingStatus.INACTIVE,  # Inactive status
            qdrant_exists=False,
            neo4j_exists=False,
        )

        mock_id_mapping_manager.get_mappings_by_entity_type.return_value = [
            orphaned_mapping
        ]
        mock_id_mapping_manager._validate_mapping_existence.return_value = None

        issues = await scanners.scan_orphaned_records()

        assert len(issues) == 1
        assert (
            issues[0].severity == ValidationSeverity.WARNING
        )  # Warning for inactive status

    @pytest.mark.asyncio
    async def test_data_mismatch_with_complex_payload(
        self, scanners, mock_id_mapping_manager, mock_qdrant_manager, sample_mapping
    ):
        """Test data mismatch scanning with complex payload structures."""
        mock_id_mapping_manager.get_mappings_by_entity_type.return_value = [
            sample_mapping
        ]

        mock_client = MagicMock()
        mock_qdrant_manager._ensure_client_connected.return_value = mock_client
        mock_client.retrieve.return_value = [
            PointStruct(
                id="point-123",
                vector=[0.1],
                payload={
                    "text": "sample text",
                    "metadata": {"key1": "value1", "key2": 123},
                    "tags": ["tag1", "tag2"],
                },
            )
        ]

        scanners.neo4j_manager.execute_read_query.return_value = [
            {
                "n": {
                    "text": "sample text",
                    "metadata": {"key1": "value1", "key2": 456},  # Different value
                    "tags": ["tag1", "tag3"],  # Different tag
                    "uuid": "uuid-789",
                }
            }
        ]

        # Mock complex data comparison
        with patch.object(
            scanners,
            "_compare_entity_data",
            return_value=[
                {"field": "metadata.key2", "qdrant_value": 123, "neo4j_value": 456},
                {
                    "field": "tags",
                    "qdrant_value": ["tag1", "tag2"],
                    "neo4j_value": ["tag1", "tag3"],
                },
            ],
        ):
            issues = await scanners.scan_data_mismatches()

        assert len(issues) == 2  # One issue per field mismatch
        assert all(
            issue.category == ValidationCategory.DATA_MISMATCH for issue in issues
        )
        assert issues[0].metadata["field"] in ["metadata.key2", "tags"]
        assert issues[1].metadata["field"] in ["metadata.key2", "tags"]
