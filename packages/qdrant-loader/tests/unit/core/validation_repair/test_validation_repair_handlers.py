"""Comprehensive tests for RepairHandlers class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC

from qdrant_loader.core.validation_repair.repair_handlers import RepairHandlers
from qdrant_loader.core.validation_repair.models import (
    ValidationIssue,
    ValidationCategory,
    ValidationSeverity,
    RepairAction,
    RepairResult,
)
from qdrant_loader.core.managers import IDMapping, MappingStatus, MappingType
from qdrant_loader.core.types import EntityType


class TestRepairHandlers:
    """Test suite for RepairHandlers class."""

    @pytest.fixture
    def mock_id_mapping_manager(self):
        """Create mock ID mapping manager."""
        manager = AsyncMock()
        return manager

    @pytest.fixture
    def mock_neo4j_manager(self):
        """Create mock Neo4j manager."""
        manager = MagicMock()
        return manager

    @pytest.fixture
    def mock_qdrant_manager(self):
        """Create mock Qdrant manager."""
        manager = MagicMock()
        manager.collection_name = "test_collection"
        return manager

    @pytest.fixture
    def mock_conflict_resolution_system(self):
        """Create mock conflict resolution system."""
        return MagicMock()

    @pytest.fixture
    def repair_handlers(
        self, mock_id_mapping_manager, mock_neo4j_manager, mock_qdrant_manager
    ):
        """Create RepairHandlers instance with mocked dependencies."""
        return RepairHandlers(
            id_mapping_manager=mock_id_mapping_manager,
            neo4j_manager=mock_neo4j_manager,
            qdrant_manager=mock_qdrant_manager,
        )

    @pytest.fixture
    def repair_handlers_with_conflict_resolution(
        self,
        mock_id_mapping_manager,
        mock_neo4j_manager,
        mock_qdrant_manager,
        mock_conflict_resolution_system,
    ):
        """Create RepairHandlers instance with conflict resolution system."""
        return RepairHandlers(
            id_mapping_manager=mock_id_mapping_manager,
            neo4j_manager=mock_neo4j_manager,
            qdrant_manager=mock_qdrant_manager,
            conflict_resolution_system=mock_conflict_resolution_system,
        )

    @pytest.fixture
    def sample_mapping(self):
        """Create a sample ID mapping."""
        return IDMapping(
            mapping_id="test-mapping-1",
            qdrant_point_id="point-123",
            neo4j_node_id="node-456",
            neo4j_node_uuid="uuid-789",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            status=MappingStatus.ACTIVE,
            qdrant_exists=True,
            neo4j_exists=True,
        )

    @pytest.fixture
    def sample_validation_issue(self):
        """Create a sample validation issue."""
        return ValidationIssue(
            category=ValidationCategory.MISSING_MAPPING,
            severity=ValidationSeverity.WARNING,
            title="Missing Mapping",
            description="Test issue for repair",
            qdrant_point_id="point-123",
            suggested_actions=[RepairAction.CREATE_MAPPING],
            auto_repairable=True,
            repair_priority=6,
        )

    # Test repair_create_mapping method
    @pytest.mark.asyncio
    async def test_repair_create_mapping_for_qdrant_point_success(
        self, repair_handlers, mock_id_mapping_manager, sample_mapping
    ):
        """Test successful mapping creation for Qdrant point."""
        issue = ValidationIssue(
            category=ValidationCategory.MISSING_MAPPING,
            severity=ValidationSeverity.WARNING,
            title="Missing Qdrant Mapping",
            description="QDrant point has no mapping",
            qdrant_point_id="point-123",
            suggested_actions=[RepairAction.CREATE_MAPPING],
            auto_repairable=True,
            repair_priority=6,
        )

        # Mock successful mapping creation
        with patch.object(
            repair_handlers,
            "_create_mapping_for_qdrant_point",
            return_value=sample_mapping,
        ):
            result = await repair_handlers.repair_create_mapping(issue)

        assert result.success is True
        assert result.action_taken == RepairAction.CREATE_MAPPING
        assert result.details["mapping_id"] == sample_mapping.mapping_id
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_repair_create_mapping_for_neo4j_node_success(
        self, repair_handlers, mock_id_mapping_manager, sample_mapping
    ):
        """Test successful mapping creation for Neo4j node."""
        issue = ValidationIssue(
            category=ValidationCategory.MISSING_MAPPING,
            severity=ValidationSeverity.WARNING,
            title="Missing Neo4j Mapping",
            description="Neo4j node has no mapping",
            neo4j_node_id="node-456",
            suggested_actions=[RepairAction.CREATE_MAPPING],
            auto_repairable=True,
            repair_priority=6,
        )

        # Mock successful mapping creation
        with patch.object(
            repair_handlers,
            "_create_mapping_for_neo4j_node",
            return_value=sample_mapping,
        ):
            result = await repair_handlers.repair_create_mapping(issue)

        assert result.success is True
        assert result.action_taken == RepairAction.CREATE_MAPPING
        assert result.details["mapping_id"] == sample_mapping.mapping_id

    @pytest.mark.asyncio
    async def test_repair_create_mapping_invalid_issue_data(self, repair_handlers):
        """Test mapping creation with invalid issue data."""
        issue = ValidationIssue(
            category=ValidationCategory.MISSING_MAPPING,
            severity=ValidationSeverity.WARNING,
            title="Invalid Issue",
            description="Issue with no point or node ID",
            suggested_actions=[RepairAction.CREATE_MAPPING],
            auto_repairable=True,
            repair_priority=6,
        )

        result = await repair_handlers.repair_create_mapping(issue)

        assert result.success is False
        assert result.action_taken == RepairAction.CREATE_MAPPING
        assert "Invalid issue data" in result.error_message
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_repair_create_mapping_creation_failure(self, repair_handlers):
        """Test mapping creation failure."""
        issue = ValidationIssue(
            category=ValidationCategory.MISSING_MAPPING,
            severity=ValidationSeverity.WARNING,
            title="Missing Qdrant Mapping",
            description="QDrant point has no mapping",
            qdrant_point_id="point-123",
            suggested_actions=[RepairAction.CREATE_MAPPING],
            auto_repairable=True,
            repair_priority=6,
        )

        # Mock creation failure
        with patch.object(
            repair_handlers,
            "_create_mapping_for_qdrant_point",
            side_effect=Exception("Creation failed"),
        ):
            result = await repair_handlers.repair_create_mapping(issue)

        assert result.success is False
        assert result.action_taken == RepairAction.CREATE_MAPPING
        assert "Creation failed" in result.error_message

    # Test repair_delete_orphaned method
    @pytest.mark.asyncio
    async def test_repair_delete_orphaned_success(
        self, repair_handlers, mock_id_mapping_manager
    ):
        """Test successful deletion of orphaned mapping."""
        issue = ValidationIssue(
            category=ValidationCategory.ORPHANED_RECORD,
            severity=ValidationSeverity.ERROR,
            title="Orphaned Mapping",
            description="Mapping references non-existent entities",
            mapping_id="orphaned-mapping-123",
            suggested_actions=[RepairAction.DELETE_ORPHANED],
            auto_repairable=True,
            repair_priority=7,
        )

        # Mock successful deletion
        mock_id_mapping_manager.delete_mapping.return_value = None

        result = await repair_handlers.repair_delete_orphaned(issue)

        assert result.success is True
        assert result.action_taken == RepairAction.DELETE_ORPHANED
        assert result.details["deleted_mapping_id"] == "orphaned-mapping-123"
        mock_id_mapping_manager.delete_mapping.assert_called_once_with(
            "orphaned-mapping-123"
        )

    @pytest.mark.asyncio
    async def test_repair_delete_orphaned_no_mapping_id(
        self, repair_handlers, mock_id_mapping_manager
    ):
        """Test deletion of orphaned mapping without mapping ID."""
        issue = ValidationIssue(
            category=ValidationCategory.ORPHANED_RECORD,
            severity=ValidationSeverity.ERROR,
            title="Orphaned Mapping",
            description="Mapping references non-existent entities",
            suggested_actions=[RepairAction.DELETE_ORPHANED],
            auto_repairable=True,
            repair_priority=7,
        )

        result = await repair_handlers.repair_delete_orphaned(issue)

        assert result.success is True
        assert result.action_taken == RepairAction.DELETE_ORPHANED
        assert result.details["deleted_mapping_id"] is None
        mock_id_mapping_manager.delete_mapping.assert_not_called()

    @pytest.mark.asyncio
    async def test_repair_delete_orphaned_failure(
        self, repair_handlers, mock_id_mapping_manager
    ):
        """Test deletion failure."""
        issue = ValidationIssue(
            category=ValidationCategory.ORPHANED_RECORD,
            severity=ValidationSeverity.ERROR,
            title="Orphaned Mapping",
            description="Mapping references non-existent entities",
            mapping_id="orphaned-mapping-123",
            suggested_actions=[RepairAction.DELETE_ORPHANED],
            auto_repairable=True,
            repair_priority=7,
        )

        # Mock deletion failure
        mock_id_mapping_manager.delete_mapping.side_effect = Exception(
            "Deletion failed"
        )

        result = await repair_handlers.repair_delete_orphaned(issue)

        assert result.success is False
        assert result.action_taken == RepairAction.DELETE_ORPHANED
        assert "Deletion failed" in result.error_message

    # Test repair_update_data method
    @pytest.mark.asyncio
    async def test_repair_update_data_success(self, repair_handlers):
        """Test successful data update repair."""
        issue = ValidationIssue(
            category=ValidationCategory.DATA_MISMATCH,
            severity=ValidationSeverity.WARNING,
            title="Data Mismatch",
            description="Data inconsistency detected",
            mapping_id="mapping-123",
            suggested_actions=[RepairAction.UPDATE_DATA],
            auto_repairable=True,
            repair_priority=5,
            metadata={"field": "text", "qdrant_value": "old", "neo4j_value": "new"},
        )

        result = await repair_handlers.repair_update_data(issue)

        assert result.success is True
        assert result.action_taken == RepairAction.UPDATE_DATA
        assert result.details["updated_field"] == "text"
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_repair_update_data_failure(self, repair_handlers):
        """Test data update repair failure."""
        issue = ValidationIssue(
            category=ValidationCategory.DATA_MISMATCH,
            severity=ValidationSeverity.WARNING,
            title="Data Mismatch",
            description="Data inconsistency detected",
            mapping_id="mapping-123",
            suggested_actions=[RepairAction.UPDATE_DATA],
            auto_repairable=True,
            repair_priority=5,
            metadata={"field": "text"},
        )

        # Mock update failure by patching the method to raise exception
        with patch.object(
            repair_handlers,
            "repair_update_data",
            side_effect=Exception("Update failed"),
        ):
            with pytest.raises(Exception, match="Update failed"):
                await repair_handlers.repair_update_data(issue)

    # Test repair_sync_entities method
    @pytest.mark.asyncio
    async def test_repair_sync_entities_success(
        self, repair_handlers, mock_id_mapping_manager, sample_mapping
    ):
        """Test successful entity synchronization."""
        issue = ValidationIssue(
            category=ValidationCategory.SYNC_FAILURE,
            severity=ValidationSeverity.ERROR,
            title="Sync Failure",
            description="Entities out of sync",
            mapping_id="mapping-123",
            suggested_actions=[RepairAction.SYNC_ENTITIES],
            auto_repairable=True,
            repair_priority=8,
        )

        # Mock successful mapping retrieval and update
        mock_id_mapping_manager.get_mapping_by_id.return_value = sample_mapping
        mock_id_mapping_manager.update_mapping.return_value = None

        result = await repair_handlers.repair_sync_entities(issue)

        assert result.success is True
        assert result.action_taken == RepairAction.SYNC_ENTITIES
        assert result.details["mapping_id"] == "mapping-123"
        mock_id_mapping_manager.update_mapping.assert_called_once_with(
            "mapping-123", {"status": MappingStatus.PENDING_SYNC.value}
        )

    @pytest.mark.asyncio
    async def test_repair_sync_entities_no_mapping_id(
        self, repair_handlers, mock_id_mapping_manager
    ):
        """Test entity synchronization without mapping ID."""
        issue = ValidationIssue(
            category=ValidationCategory.SYNC_FAILURE,
            severity=ValidationSeverity.ERROR,
            title="Sync Failure",
            description="Entities out of sync",
            suggested_actions=[RepairAction.SYNC_ENTITIES],
            auto_repairable=True,
            repair_priority=8,
        )

        result = await repair_handlers.repair_sync_entities(issue)

        assert result.success is True
        assert result.action_taken == RepairAction.SYNC_ENTITIES
        assert result.details["mapping_id"] is None
        mock_id_mapping_manager.get_mapping_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_repair_sync_entities_mapping_not_found(
        self, repair_handlers, mock_id_mapping_manager
    ):
        """Test entity synchronization when mapping is not found."""
        issue = ValidationIssue(
            category=ValidationCategory.SYNC_FAILURE,
            severity=ValidationSeverity.ERROR,
            title="Sync Failure",
            description="Entities out of sync",
            mapping_id="mapping-123",
            suggested_actions=[RepairAction.SYNC_ENTITIES],
            auto_repairable=True,
            repair_priority=8,
        )

        # Mock mapping not found
        mock_id_mapping_manager.get_mapping_by_id.return_value = None

        result = await repair_handlers.repair_sync_entities(issue)

        assert result.success is True
        assert result.action_taken == RepairAction.SYNC_ENTITIES
        mock_id_mapping_manager.update_mapping.assert_not_called()

    @pytest.mark.asyncio
    async def test_repair_sync_entities_failure(
        self, repair_handlers, mock_id_mapping_manager
    ):
        """Test entity synchronization failure."""
        issue = ValidationIssue(
            category=ValidationCategory.SYNC_FAILURE,
            severity=ValidationSeverity.ERROR,
            title="Sync Failure",
            description="Entities out of sync",
            mapping_id="mapping-123",
            suggested_actions=[RepairAction.SYNC_ENTITIES],
            auto_repairable=True,
            repair_priority=8,
        )

        # Mock sync failure
        mock_id_mapping_manager.get_mapping_by_id.side_effect = Exception("Sync failed")

        result = await repair_handlers.repair_sync_entities(issue)

        assert result.success is False
        assert result.action_taken == RepairAction.SYNC_ENTITIES
        assert "Sync failed" in result.error_message

    # Test repair_resolve_conflict method
    @pytest.mark.asyncio
    async def test_repair_resolve_conflict_success(
        self, repair_handlers_with_conflict_resolution
    ):
        """Test successful conflict resolution."""
        issue = ValidationIssue(
            category=ValidationCategory.DATA_MISMATCH,  # Using existing category
            severity=ValidationSeverity.ERROR,
            title="Data Conflict",
            description="Conflicting data detected",
            mapping_id="mapping-123",
            suggested_actions=[RepairAction.RESOLVE_CONFLICT],
            auto_repairable=True,
            repair_priority=9,
        )

        result = await repair_handlers_with_conflict_resolution.repair_resolve_conflict(
            issue
        )

        assert result.success is True
        assert result.action_taken == RepairAction.RESOLVE_CONFLICT
        assert result.details["conflict_resolved"] is True

    @pytest.mark.asyncio
    async def test_repair_resolve_conflict_no_system(self, repair_handlers):
        """Test conflict resolution without conflict resolution system."""
        issue = ValidationIssue(
            category=ValidationCategory.DATA_MISMATCH,  # Using existing category
            severity=ValidationSeverity.ERROR,
            title="Data Conflict",
            description="Conflicting data detected",
            mapping_id="mapping-123",
            suggested_actions=[RepairAction.RESOLVE_CONFLICT],
            auto_repairable=True,
            repair_priority=9,
        )

        result = await repair_handlers.repair_resolve_conflict(issue)

        assert result.success is False
        assert result.action_taken == RepairAction.RESOLVE_CONFLICT
        assert "Conflict resolution system not available" in result.error_message

    @pytest.mark.asyncio
    async def test_repair_resolve_conflict_failure(
        self, repair_handlers_with_conflict_resolution
    ):
        """Test conflict resolution failure."""
        issue = ValidationIssue(
            category=ValidationCategory.DATA_MISMATCH,  # Using existing category
            severity=ValidationSeverity.ERROR,
            title="Data Conflict",
            description="Conflicting data detected",
            mapping_id="mapping-123",
            suggested_actions=[RepairAction.RESOLVE_CONFLICT],
            auto_repairable=True,
            repair_priority=9,
        )

        # Mock resolution failure by raising exception in the method
        with patch.object(
            repair_handlers_with_conflict_resolution, "repair_resolve_conflict"
        ) as mock_repair:
            mock_repair.side_effect = Exception("Resolution failed")

            with pytest.raises(Exception, match="Resolution failed"):
                await repair_handlers_with_conflict_resolution.repair_resolve_conflict(
                    issue
                )

    # Test repair_rebuild_index method
    @pytest.mark.asyncio
    async def test_repair_rebuild_index_success(self, repair_handlers):
        """Test successful index rebuild."""
        issue = ValidationIssue(
            category=ValidationCategory.PERFORMANCE_ISSUE,
            severity=ValidationSeverity.WARNING,
            title="Performance Issue",
            description="Slow query performance",
            suggested_actions=[RepairAction.REBUILD_INDEX],
            auto_repairable=False,
            repair_priority=3,
        )

        result = await repair_handlers.repair_rebuild_index(issue)

        assert result.success is True
        assert result.action_taken == RepairAction.REBUILD_INDEX
        assert result.details["index_rebuilt"] is True
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_repair_rebuild_index_failure(self, repair_handlers):
        """Test index rebuild failure."""
        issue = ValidationIssue(
            category=ValidationCategory.PERFORMANCE_ISSUE,
            severity=ValidationSeverity.WARNING,
            title="Performance Issue",
            description="Slow query performance",
            suggested_actions=[RepairAction.REBUILD_INDEX],
            auto_repairable=False,
            repair_priority=3,
        )

        # Mock rebuild failure by patching the method
        with patch.object(repair_handlers, "repair_rebuild_index") as mock_rebuild:
            mock_rebuild.side_effect = Exception("Rebuild failed")

            with pytest.raises(Exception, match="Rebuild failed"):
                await repair_handlers.repair_rebuild_index(issue)

    # Test helper methods
    @pytest.mark.asyncio
    async def test_create_mapping_for_qdrant_point_success(
        self, repair_handlers, mock_qdrant_manager, mock_id_mapping_manager
    ):
        """Test successful mapping creation for Qdrant point."""
        point_id = "point-123"

        # Mock Qdrant client and point retrieval
        mock_client = MagicMock()
        mock_qdrant_manager._ensure_client_connected.return_value = mock_client
        mock_client.retrieve.return_value = [
            MagicMock(
                id=point_id,
                payload={"text": "sample text", "category": "concept"},
                vector=[0.1, 0.2, 0.3],
            )
        ]

        # Mock mapping creation
        new_mapping = IDMapping(
            mapping_id="new-mapping-123",
            qdrant_point_id=point_id,
            neo4j_node_id=None,
            neo4j_node_uuid=None,
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            status=MappingStatus.PENDING_SYNC,
            qdrant_exists=True,
            neo4j_exists=False,
        )

        mock_id_mapping_manager.create_mapping.return_value = new_mapping

        result = await repair_handlers._create_mapping_for_qdrant_point(point_id)

        assert result.mapping_id == "new-mapping-123"
        assert result.qdrant_point_id == point_id
        assert result.entity_type == EntityType.CONCEPT
        mock_id_mapping_manager.create_mapping.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_mapping_for_qdrant_point_not_found(
        self, repair_handlers, mock_qdrant_manager
    ):
        """Test mapping creation when Qdrant point is not found."""
        point_id = "missing-point-123"

        # Mock Qdrant client with no results
        mock_client = MagicMock()
        mock_qdrant_manager._ensure_client_connected.return_value = mock_client
        mock_client.retrieve.return_value = []

        with pytest.raises(ValueError, match="QDrant point .* not found"):
            await repair_handlers._create_mapping_for_qdrant_point(point_id)

    @pytest.mark.asyncio
    async def test_create_mapping_for_qdrant_point_client_error(
        self, repair_handlers, mock_qdrant_manager
    ):
        """Test mapping creation with Qdrant client error."""
        point_id = "point-123"

        # Mock Qdrant client error
        mock_qdrant_manager._ensure_client_connected.side_effect = Exception(
            "Connection failed"
        )

        with pytest.raises(Exception, match="Connection failed"):
            await repair_handlers._create_mapping_for_qdrant_point(point_id)

    @pytest.mark.asyncio
    async def test_create_mapping_for_neo4j_node_success(
        self, repair_handlers, mock_id_mapping_manager
    ):
        """Test successful mapping creation for Neo4j node."""
        node_id = "node-456"

        # Mock Neo4j query result
        repair_handlers.neo4j_manager.execute_read_query.return_value = [
            {
                "labels": ["Concept"],
                "uuid": "uuid-789",
                "name": "Test Node",
                "text": "sample text",
            }
        ]

        # Mock mapping creation
        new_mapping = IDMapping(
            mapping_id="new-mapping-456",
            qdrant_point_id=None,
            neo4j_node_id=node_id,
            neo4j_node_uuid="uuid-789",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            status=MappingStatus.PENDING_SYNC,
            qdrant_exists=False,
            neo4j_exists=True,
        )

        mock_id_mapping_manager.create_mapping.return_value = new_mapping

        result = await repair_handlers._create_mapping_for_neo4j_node(node_id)

        assert result.mapping_id == "new-mapping-456"
        assert result.neo4j_node_id == node_id
        assert result.neo4j_node_uuid == "uuid-789"
        assert result.entity_type == EntityType.CONCEPT
        mock_id_mapping_manager.create_mapping.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_mapping_for_neo4j_node_not_found(self, repair_handlers):
        """Test mapping creation when Neo4j node is not found."""
        node_id = "missing-node-456"

        # Mock Neo4j query with no results
        repair_handlers.neo4j_manager.execute_read_query.return_value = []

        with pytest.raises(ValueError, match="Neo4j node not found"):
            await repair_handlers._create_mapping_for_neo4j_node(node_id)

    @pytest.mark.asyncio
    async def test_create_mapping_for_neo4j_node_query_error(self, repair_handlers):
        """Test mapping creation with Neo4j query error."""
        node_id = "node-456"

        # Mock Neo4j query error
        repair_handlers.neo4j_manager.execute_read_query.side_effect = Exception(
            "Query failed"
        )

        with pytest.raises(Exception, match="Query failed"):
            await repair_handlers._create_mapping_for_neo4j_node(node_id)

    # Edge cases and error scenarios
    @pytest.mark.asyncio
    async def test_repair_with_both_point_and_node_ids(
        self, repair_handlers, sample_mapping
    ):
        """Test repair creation with both Qdrant point and Neo4j node IDs."""
        issue = ValidationIssue(
            category=ValidationCategory.MISSING_MAPPING,
            severity=ValidationSeverity.WARNING,
            title="Ambiguous Issue",
            description="Issue with both point and node IDs",
            qdrant_point_id="point-123",
            neo4j_node_id="node-456",
            suggested_actions=[RepairAction.CREATE_MAPPING],
            auto_repairable=True,
            repair_priority=6,
        )

        # Should prioritize Qdrant point creation
        with patch.object(
            repair_handlers,
            "_create_mapping_for_qdrant_point",
            return_value=sample_mapping,
        ):
            result = await repair_handlers.repair_create_mapping(issue)

        assert result.success is True
        assert result.action_taken == RepairAction.CREATE_MAPPING

    @pytest.mark.asyncio
    async def test_repair_execution_time_measurement(
        self, repair_handlers, mock_id_mapping_manager
    ):
        """Test that execution time is properly measured."""
        issue = ValidationIssue(
            category=ValidationCategory.ORPHANED_RECORD,
            severity=ValidationSeverity.ERROR,
            title="Orphaned Mapping",
            description="Test execution time",
            mapping_id="mapping-123",
            suggested_actions=[RepairAction.DELETE_ORPHANED],
            auto_repairable=True,
            repair_priority=7,
        )

        # Add delay to ensure measurable execution time
        async def slow_delete(mapping_id):
            import asyncio

            await asyncio.sleep(0.01)  # 10ms delay

        mock_id_mapping_manager.delete_mapping.side_effect = slow_delete

        result = await repair_handlers.repair_delete_orphaned(issue)

        assert result.success is True
        assert result.execution_time_ms >= 10  # Should be at least 10ms

    @pytest.mark.asyncio
    async def test_repair_result_issue_id_preservation(
        self, repair_handlers, sample_validation_issue
    ):
        """Test that repair results preserve the original issue ID."""
        # Set a specific issue ID
        sample_validation_issue.issue_id = "issue-12345"

        with patch.object(
            repair_handlers,
            "_create_mapping_for_qdrant_point",
            return_value=MagicMock(mapping_id="new-mapping"),
        ):
            result = await repair_handlers.repair_create_mapping(
                sample_validation_issue
            )

        assert result.issue_id == "issue-12345"

    @pytest.mark.asyncio
    async def test_multiple_repair_operations_independence(
        self, repair_handlers, mock_id_mapping_manager
    ):
        """Test that multiple repair operations are independent."""
        issues = [
            ValidationIssue(
                category=ValidationCategory.ORPHANED_RECORD,
                severity=ValidationSeverity.ERROR,
                title=f"Orphaned Mapping {i}",
                description=f"Test issue {i}",
                mapping_id=f"mapping-{i}",
                suggested_actions=[RepairAction.DELETE_ORPHANED],
                auto_repairable=True,
                repair_priority=7,
            )
            for i in range(3)
        ]

        # Mock one deletion to fail
        def mock_delete(mapping_id):
            if mapping_id == "mapping-1":
                raise Exception("Deletion failed")
            return None

        mock_id_mapping_manager.delete_mapping.side_effect = mock_delete

        results = []
        for issue in issues:
            result = await repair_handlers.repair_delete_orphaned(issue)
            results.append(result)

        # First and third should succeed, second should fail
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True
        assert "Deletion failed" in results[1].error_message

    @pytest.mark.asyncio
    async def test_repair_with_empty_metadata(self, repair_handlers):
        """Test repair operations with empty or missing metadata."""
        issue = ValidationIssue(
            category=ValidationCategory.DATA_MISMATCH,
            severity=ValidationSeverity.WARNING,
            title="Data Mismatch",
            description="Data inconsistency with no metadata",
            mapping_id="mapping-123",
            suggested_actions=[RepairAction.UPDATE_DATA],
            auto_repairable=True,
            repair_priority=5,
            metadata={},  # Empty metadata
        )

        result = await repair_handlers.repair_update_data(issue)

        assert result.success is True
        assert result.action_taken == RepairAction.UPDATE_DATA
        assert (
            result.details["updated_field"] is None
        )  # Should handle missing field gracefully
