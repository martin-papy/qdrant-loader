"""
Comprehensive unit tests for IDMappingManager and IDMapping.

This test suite covers:
- IDMapping dataclass functionality
- IDMappingManager core operations
- Cross-database ID mapping
- Temporal tracking and versioning
- Cache management
- Validation and cleanup operations
- Error handling and edge cases
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Any

import pytest

from qdrant_loader.core.managers.id_mapping_manager import (
    IDMapping,
    IDMappingManager,
    MappingStatus,
    MappingType,
)
from qdrant_loader.core.managers.neo4j_manager import Neo4jManager
from qdrant_loader.core.managers.qdrant_manager import QdrantManager
from qdrant_loader.core.types import EntityType, TemporalInfo


class TestIDMapping:
    """Test cases for IDMapping dataclass."""

    @pytest.fixture
    def sample_mapping(self):
        """Create a sample IDMapping for testing."""
        return IDMapping(
            mapping_id="test_id_123",
            qdrant_point_id="qdrant_456",
            neo4j_node_id="neo4j_789",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            entity_name="Test Entity",
            metadata={"source": "test"},
        )

    def test_id_mapping_creation(self):
        """Test basic IDMapping creation."""
        mapping = IDMapping()

        assert mapping.mapping_id is not None
        assert mapping.entity_type == EntityType.CONCEPT
        assert mapping.mapping_type == MappingType.DOCUMENT
        assert mapping.status == MappingStatus.ACTIVE
        assert mapping.sync_version == 1
        assert mapping.document_version == 1
        assert mapping.update_frequency == 0
        assert isinstance(mapping.metadata, dict)
        assert isinstance(mapping.sync_errors, list)
        assert isinstance(mapping.version_history, list)
        assert isinstance(mapping.temporal_info, TemporalInfo)

    def test_id_mapping_creation_with_values(self, sample_mapping):
        """Test IDMapping creation with specific values."""
        assert sample_mapping.mapping_id == "test_id_123"
        assert sample_mapping.qdrant_point_id == "qdrant_456"
        assert sample_mapping.neo4j_node_id == "neo4j_789"
        assert sample_mapping.entity_type == EntityType.CONCEPT
        assert sample_mapping.entity_name == "Test Entity"
        assert sample_mapping.metadata["source"] == "test"

    def test_is_valid_method(self, sample_mapping):
        """Test the is_valid method."""
        # Initially not valid (exists flags are False)
        assert not sample_mapping.is_valid()

        # Set exists flags to True
        sample_mapping.qdrant_exists = True
        sample_mapping.neo4j_exists = True
        sample_mapping.status = MappingStatus.ACTIVE

        # Should be valid now
        assert sample_mapping.is_valid()

    def test_is_orphaned_method(self, sample_mapping):
        """Test the is_orphaned method."""
        # Initially orphaned (exists flags are False)
        assert sample_mapping.is_orphaned()

        # Set one exists flag to True
        sample_mapping.qdrant_exists = True
        assert sample_mapping.is_orphaned()  # Still orphaned

        # Set both exists flags to True
        sample_mapping.neo4j_exists = True
        assert not sample_mapping.is_orphaned()  # No longer orphaned

    def test_mark_sync_failed(self, sample_mapping):
        """Test marking sync as failed."""
        error_msg = "Connection timeout"
        sample_mapping.mark_sync_failed(error_msg)

        assert sample_mapping.status == MappingStatus.SYNC_FAILED
        assert len(sample_mapping.sync_errors) == 1
        assert error_msg in sample_mapping.sync_errors[0]

    def test_mark_sync_success(self, sample_mapping):
        """Test marking sync as successful."""
        # First mark as failed
        sample_mapping.mark_sync_failed("Test error")
        initial_version = sample_mapping.sync_version

        # Then mark as successful
        sample_mapping.mark_sync_success()

        assert sample_mapping.status == MappingStatus.ACTIVE
        assert sample_mapping.last_sync_time is not None
        assert sample_mapping.sync_version == initial_version + 1
        assert len(sample_mapping.sync_errors) == 0

    def test_increment_document_version(self, sample_mapping):
        """Test document version increment."""
        initial_version = sample_mapping.document_version
        initial_frequency = sample_mapping.update_frequency

        sample_mapping.increment_document_version(
            update_source="test_source",
            content_hash="hash123",
            metadata={"update": "test"},
        )

        assert sample_mapping.document_version == initial_version + 1
        assert sample_mapping.update_frequency == initial_frequency + 1
        assert sample_mapping.update_source == "test_source"
        assert sample_mapping.content_hash == "hash123"
        assert sample_mapping.last_update_time is not None
        assert len(sample_mapping.version_history) == 1

    def test_get_version_at_time(self, sample_mapping):
        """Test getting version at specific time."""
        # Update version to create history
        sample_mapping.increment_document_version("source1", "hash1")

        # Get version at current time (should return current version)
        current_time = datetime.now(UTC)
        version_info = sample_mapping.get_version_at_time(current_time)

        assert version_info is not None
        assert version_info["version"] == sample_mapping.document_version
        assert version_info["is_current"] is True

    def test_get_update_statistics(self, sample_mapping):
        """Test getting update statistics."""
        # Update version a few times
        for i in range(3):
            sample_mapping.increment_document_version(f"source_{i}", f"hash_{i}")

        stats = sample_mapping.get_update_statistics()

        assert stats["current_version"] == 4  # Started at 1, incremented 3 times
        assert stats["total_updates"] == 3
        assert "created_time" in stats
        assert "last_update_time" in stats
        assert "update_rate_per_day" in stats

    def test_to_dict(self, sample_mapping):
        """Test converting mapping to dictionary."""
        mapping_dict = sample_mapping.to_dict()

        assert mapping_dict["mapping_id"] == sample_mapping.mapping_id
        assert mapping_dict["qdrant_point_id"] == sample_mapping.qdrant_point_id
        assert mapping_dict["neo4j_node_id"] == sample_mapping.neo4j_node_id
        assert mapping_dict["entity_type"] == sample_mapping.entity_type.value
        assert mapping_dict["mapping_type"] == sample_mapping.mapping_type.value
        assert mapping_dict["status"] == sample_mapping.status.value
        assert "temporal_info" in mapping_dict

    def test_from_dict(self, sample_mapping):
        """Test creating mapping from dictionary."""
        mapping_dict = sample_mapping.to_dict()
        reconstructed = IDMapping.from_dict(mapping_dict)

        assert reconstructed.mapping_id == sample_mapping.mapping_id
        assert reconstructed.qdrant_point_id == sample_mapping.qdrant_point_id
        assert reconstructed.neo4j_node_id == sample_mapping.neo4j_node_id
        assert reconstructed.entity_type == sample_mapping.entity_type
        assert reconstructed.mapping_type == sample_mapping.mapping_type
        assert reconstructed.status == sample_mapping.status


class TestIDMappingManager:
    """Test cases for IDMappingManager."""

    @pytest.fixture
    def mock_neo4j_manager(self):
        """Create a mock Neo4j manager."""
        mock_manager = Mock(spec=Neo4jManager)
        mock_manager.execute_read_query = Mock(return_value=[])
        mock_manager.execute_write_query = Mock(return_value=[])
        mock_manager.test_connection = Mock(return_value=True)
        return mock_manager

    @pytest.fixture
    def mock_qdrant_manager(self):
        """Create a mock Qdrant manager."""
        mock_manager = Mock(spec=QdrantManager)
        mock_manager.collection_name = "test_collection"
        mock_manager._ensure_client_connected = Mock()
        # Configure the client mock to be returned by _ensure_client_connected
        mock_client = Mock()
        mock_client.retrieve = Mock()
        mock_manager._ensure_client_connected.return_value = mock_client
        return mock_manager

    @pytest.fixture
    def id_mapping_manager(self, mock_neo4j_manager, mock_qdrant_manager):
        """Create an IDMappingManager instance with mocked dependencies."""
        with patch.object(IDMappingManager, "_ensure_mapping_table"):
            return IDMappingManager(
                neo4j_manager=mock_neo4j_manager, qdrant_manager=mock_qdrant_manager
            )

    @pytest.fixture
    def sample_neo4j_result(self):
        """Create a sample Neo4j query result."""
        return {
            "m": {
                "mapping_id": "test_mapping_id",
                "qdrant_point_id": "qdrant_123",
                "neo4j_node_id": "neo4j_456",
                "neo4j_node_uuid": "uuid_789",
                "entity_type": "Concept",
                "mapping_type": "document",
                "entity_name": "Test Entity",
                "status": "active",
                "metadata": {"key": "value"},
                "sync_version": 1,
                "sync_errors": [],
                "document_version": 1,
                "update_frequency": 0,
                "qdrant_exists": True,
                "neo4j_exists": True,
                "created_time": datetime.now(UTC).isoformat(),
                "temporal_info": {
                    "valid_from": datetime.now(UTC).isoformat(),
                    "valid_to": None,
                    "transaction_time": datetime.now(UTC).isoformat(),
                    "version": 1,
                    "superseded_by": None,
                    "supersedes": None,
                },
            }
        }

    def test_init(self, mock_neo4j_manager, mock_qdrant_manager):
        """Test IDMappingManager initialization."""
        with patch.object(IDMappingManager, "_ensure_mapping_table") as mock_ensure:
            manager = IDMappingManager(
                neo4j_manager=mock_neo4j_manager,
                qdrant_manager=mock_qdrant_manager,
                enable_validation=True,
                validation_interval_hours=12,
            )

            assert manager.neo4j_manager == mock_neo4j_manager
            assert manager.qdrant_manager == mock_qdrant_manager
            assert isinstance(manager._mapping_cache, dict)
            mock_ensure.assert_called_once()

    def test_ensure_mapping_table(self, mock_neo4j_manager, mock_qdrant_manager):
        """Test ensuring mapping table exists."""
        manager = IDMappingManager(
            neo4j_manager=mock_neo4j_manager, qdrant_manager=mock_qdrant_manager
        )

        # Should have called execute_write_query multiple times for constraints and indexes
        assert mock_neo4j_manager.execute_write_query.call_count >= 7

    def test_ensure_mapping_table_error(self, mock_neo4j_manager, mock_qdrant_manager):
        """Test error handling in ensure_mapping_table."""
        mock_neo4j_manager.execute_write_query.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            IDMappingManager(
                neo4j_manager=mock_neo4j_manager, qdrant_manager=mock_qdrant_manager
            )

    @pytest.mark.asyncio
    async def test_create_mapping_success(self, id_mapping_manager):
        """Test successful mapping creation."""
        with (
            patch.object(
                id_mapping_manager, "_validate_mapping_existence"
            ) as mock_validate,
            patch.object(id_mapping_manager, "_store_mapping") as mock_store,
            patch.object(id_mapping_manager, "_cache_mapping") as mock_cache,
        ):

            mapping = await id_mapping_manager.create_mapping(
                qdrant_point_id="qdrant_123",
                neo4j_node_id="neo4j_456",
                entity_type=EntityType.CONCEPT,
                entity_name="Test Entity",
            )

            assert mapping.qdrant_point_id == "qdrant_123"
            assert mapping.neo4j_node_id == "neo4j_456"
            assert mapping.entity_type == EntityType.CONCEPT
            assert mapping.entity_name == "Test Entity"
            mock_validate.assert_called_once_with(mapping)
            mock_store.assert_called_once_with(mapping)
            mock_cache.assert_called_once_with(mapping)

    @pytest.mark.asyncio
    async def test_create_mapping_no_ids_error(self, id_mapping_manager):
        """Test error when creating mapping without any IDs."""
        with pytest.raises(ValueError, match="At least one ID must be provided"):
            await id_mapping_manager.create_mapping()

    @pytest.mark.asyncio
    async def test_create_mapping_no_validation(self, id_mapping_manager):
        """Test mapping creation without validation."""
        with (
            patch.object(
                id_mapping_manager, "_validate_mapping_existence"
            ) as mock_validate,
            patch.object(id_mapping_manager, "_store_mapping") as mock_store,
            patch.object(id_mapping_manager, "_cache_mapping") as mock_cache,
        ):

            mapping = await id_mapping_manager.create_mapping(
                qdrant_point_id="qdrant_123", validate_existence=False
            )

            assert mapping.qdrant_point_id == "qdrant_123"
            mock_validate.assert_not_called()
            mock_store.assert_called_once_with(mapping)
            mock_cache.assert_called_once_with(mapping)

    @pytest.mark.asyncio
    async def test_get_mapping_by_qdrant_id_cached(self, id_mapping_manager):
        """Test getting mapping by Qdrant ID from cache."""
        # Create a mapping and add to cache
        test_mapping = IDMapping(qdrant_point_id="qdrant_123")
        id_mapping_manager._mapping_cache["test_id"] = test_mapping

        result = await id_mapping_manager.get_mapping_by_qdrant_id("qdrant_123")

        assert result == test_mapping
        # Should not query Neo4j
        id_mapping_manager.neo4j_manager.execute_read_query.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_mapping_by_qdrant_id_from_db(
        self, id_mapping_manager, sample_neo4j_result
    ):
        """Test getting mapping by Qdrant ID from database."""
        id_mapping_manager.neo4j_manager.execute_read_query.return_value = [
            sample_neo4j_result
        ]

        with (
            patch.object(
                id_mapping_manager, "_neo4j_result_to_mapping"
            ) as mock_convert,
            patch.object(id_mapping_manager, "_cache_mapping") as mock_cache,
        ):

            mock_mapping = IDMapping(qdrant_point_id="qdrant_123")
            mock_convert.return_value = mock_mapping

            result = await id_mapping_manager.get_mapping_by_qdrant_id("qdrant_123")

            assert result == mock_mapping
            id_mapping_manager.neo4j_manager.execute_read_query.assert_called_once()
            mock_convert.assert_called_once_with(sample_neo4j_result["m"])
            mock_cache.assert_called_once_with(mock_mapping)

    @pytest.mark.asyncio
    async def test_get_mapping_by_qdrant_id_not_found(self, id_mapping_manager):
        """Test getting mapping by Qdrant ID when not found."""
        id_mapping_manager.neo4j_manager.execute_read_query.return_value = []

        result = await id_mapping_manager.get_mapping_by_qdrant_id("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_mapping_by_neo4j_id_cached(self, id_mapping_manager):
        """Test getting mapping by Neo4j ID from cache."""
        test_mapping = IDMapping(neo4j_node_id="neo4j_456")
        id_mapping_manager._mapping_cache["test_id"] = test_mapping

        result = await id_mapping_manager.get_mapping_by_neo4j_id("neo4j_456")

        assert result == test_mapping
        id_mapping_manager.neo4j_manager.execute_read_query.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_mapping_by_neo4j_id_from_db(
        self, id_mapping_manager, sample_neo4j_result
    ):
        """Test getting mapping by Neo4j ID from database."""
        id_mapping_manager.neo4j_manager.execute_read_query.return_value = [
            sample_neo4j_result
        ]

        with (
            patch.object(
                id_mapping_manager, "_neo4j_result_to_mapping"
            ) as mock_convert,
            patch.object(id_mapping_manager, "_cache_mapping") as mock_cache,
        ):

            mock_mapping = IDMapping(neo4j_node_id="neo4j_456")
            mock_convert.return_value = mock_mapping

            result = await id_mapping_manager.get_mapping_by_neo4j_id("neo4j_456")

            assert result == mock_mapping
            id_mapping_manager.neo4j_manager.execute_read_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_mapping_by_neo4j_uuid_cached(self, id_mapping_manager):
        """Test getting mapping by Neo4j UUID from cache."""
        test_mapping = IDMapping(neo4j_node_uuid="uuid_789")
        id_mapping_manager._mapping_cache["test_id"] = test_mapping

        result = await id_mapping_manager.get_mapping_by_neo4j_uuid("uuid_789")

        assert result == test_mapping
        id_mapping_manager.neo4j_manager.execute_read_query.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_mapping_by_id_cached(self, id_mapping_manager):
        """Test getting mapping by ID from cache."""
        test_mapping = IDMapping(mapping_id="test_mapping_id")
        id_mapping_manager._mapping_cache["test_mapping_id"] = test_mapping

        result = await id_mapping_manager.get_mapping_by_id("test_mapping_id")

        assert result == test_mapping
        id_mapping_manager.neo4j_manager.execute_read_query.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_mapping_by_id_from_db(
        self, id_mapping_manager, sample_neo4j_result
    ):
        """Test getting mapping by ID from database."""
        id_mapping_manager.neo4j_manager.execute_read_query.return_value = [
            sample_neo4j_result
        ]

        with (
            patch.object(
                id_mapping_manager, "_neo4j_result_to_mapping"
            ) as mock_convert,
            patch.object(id_mapping_manager, "_cache_mapping") as mock_cache,
        ):

            mock_mapping = IDMapping(mapping_id="test_mapping_id")
            mock_convert.return_value = mock_mapping

            result = await id_mapping_manager.get_mapping_by_id("test_mapping_id")

            assert result == mock_mapping
            id_mapping_manager.neo4j_manager.execute_read_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_mapping_success(self, id_mapping_manager):
        """Test successful mapping update."""
        test_mapping = IDMapping(mapping_id="test_id", entity_name="Old Name")

        with (
            patch.object(id_mapping_manager, "get_mapping_by_id") as mock_get,
            patch.object(
                id_mapping_manager, "_validate_mapping_existence"
            ) as mock_validate,
            patch.object(id_mapping_manager, "_store_mapping") as mock_store,
            patch.object(id_mapping_manager, "_cache_mapping") as mock_cache,
        ):

            mock_get.return_value = test_mapping

            updates = {"entity_name": "New Name", "metadata": {"updated": True}}
            result = await id_mapping_manager.update_mapping("test_id", updates)

            assert result.entity_name == "New Name"
            assert result.metadata == {"updated": True}
            mock_validate.assert_called_once()
            mock_store.assert_called_once()
            mock_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_mapping_not_found(self, id_mapping_manager):
        """Test updating non-existent mapping."""
        with patch.object(id_mapping_manager, "get_mapping_by_id") as mock_get:
            mock_get.return_value = None

            result = await id_mapping_manager.update_mapping(
                "nonexistent", {"entity_name": "New"}
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_update_document_version_success(self, id_mapping_manager):
        """Test successful document version update."""
        test_mapping = IDMapping(mapping_id="test_id", document_version=1)

        with (
            patch.object(id_mapping_manager, "get_mapping_by_id") as mock_get,
            patch.object(
                id_mapping_manager, "_validate_mapping_existence"
            ) as mock_validate,
            patch.object(id_mapping_manager, "_store_mapping") as mock_store,
            patch.object(id_mapping_manager, "_cache_mapping") as mock_cache,
        ):

            mock_get.return_value = test_mapping

            result = await id_mapping_manager.update_document_version(
                "test_id", "test_source", "hash123", {"test": "data"}
            )

            assert result.document_version == 2
            assert result.update_source == "test_source"
            assert result.content_hash == "hash123"
            assert result.update_frequency == 1
            mock_validate.assert_called_once()
            mock_store.assert_called_once()
            mock_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_mapping_success(self, id_mapping_manager):
        """Test successful mapping deletion."""
        # Add mapping to cache first
        id_mapping_manager._mapping_cache["test_id"] = IDMapping(mapping_id="test_id")
        id_mapping_manager.neo4j_manager.execute_write_query.return_value = [
            {"deleted_count": 1}
        ]

        result = await id_mapping_manager.delete_mapping("test_id")

        assert result is True
        id_mapping_manager.neo4j_manager.execute_write_query.assert_called_once()
        # Should remove from cache
        assert "test_id" not in id_mapping_manager._mapping_cache

    @pytest.mark.asyncio
    async def test_delete_mapping_not_found(self, id_mapping_manager):
        """Test deleting non-existent mapping."""
        id_mapping_manager.neo4j_manager.execute_write_query.return_value = [
            {"deleted_count": 0}
        ]

        result = await id_mapping_manager.delete_mapping("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_mappings_by_entity_type(
        self, id_mapping_manager, sample_neo4j_result
    ):
        """Test getting mappings by entity type."""
        id_mapping_manager.neo4j_manager.execute_read_query.return_value = [
            sample_neo4j_result
        ]

        with patch.object(
            id_mapping_manager, "_neo4j_result_to_mapping"
        ) as mock_convert:
            mock_mapping = IDMapping(entity_type=EntityType.CONCEPT)
            mock_convert.return_value = mock_mapping

            result = await id_mapping_manager.get_mappings_by_entity_type(
                EntityType.CONCEPT, MappingStatus.ACTIVE, 100
            )

            assert len(result) == 1
            assert result[0] == mock_mapping
            id_mapping_manager.neo4j_manager.execute_read_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_orphaned_mappings(self, id_mapping_manager, sample_neo4j_result):
        """Test getting orphaned mappings."""
        id_mapping_manager.neo4j_manager.execute_read_query.return_value = [
            sample_neo4j_result
        ]

        with patch.object(
            id_mapping_manager, "_neo4j_result_to_mapping"
        ) as mock_convert:
            mock_mapping = IDMapping()
            mock_mapping.qdrant_exists = False
            mock_convert.return_value = mock_mapping

            result = await id_mapping_manager.get_orphaned_mappings(50)

            assert len(result) == 1
            assert result[0] == mock_mapping
            id_mapping_manager.neo4j_manager.execute_read_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_all_mappings(self, id_mapping_manager):
        """Test validating all mappings."""
        # Mock Neo4j to return sample mappings
        sample_results = [
            {
                "m": {
                    "mapping_id": "valid_1",
                    "qdrant_point_id": "q1",
                    "neo4j_node_id": "n1",
                    "entity_type": "Concept",
                    "mapping_type": "document",
                    "status": "active",
                    "metadata": {},
                    "sync_version": 1,
                    "document_version": 1,
                    "created_time": datetime.now(UTC).isoformat(),
                    "temporal_info": {
                        "valid_from": datetime.now(UTC).isoformat(),
                        "valid_to": None,
                        "transaction_time": datetime.now(UTC).isoformat(),
                        "version": 1,
                    },
                }
            },
            {
                "m": {
                    "mapping_id": "invalid_1",
                    "qdrant_point_id": "q2",
                    "neo4j_node_id": "n2",
                    "entity_type": "Concept",
                    "mapping_type": "document",
                    "status": "orphaned",
                    "metadata": {},
                    "sync_version": 1,
                    "document_version": 1,
                    "created_time": datetime.now(UTC).isoformat(),
                    "temporal_info": {
                        "valid_from": datetime.now(UTC).isoformat(),
                        "valid_to": None,
                        "transaction_time": datetime.now(UTC).isoformat(),
                        "version": 1,
                    },
                }
            },
        ]

        id_mapping_manager.neo4j_manager.execute_read_query.return_value = (
            sample_results
        )

        with (
            patch.object(
                id_mapping_manager, "_neo4j_result_to_mapping"
            ) as mock_convert,
            patch.object(
                id_mapping_manager, "_validate_mapping_existence"
            ) as mock_validate,
            patch.object(id_mapping_manager, "_store_mapping") as mock_store,
        ):

            # Create mock mappings
            mapping1 = IDMapping(mapping_id="valid_1")
            mapping1.qdrant_exists = True
            mapping1.neo4j_exists = True
            mapping1.status = MappingStatus.ACTIVE

            mapping2 = IDMapping(mapping_id="invalid_1")
            mapping2.qdrant_exists = False
            mapping2.neo4j_exists = False
            mapping2.status = MappingStatus.ORPHANED

            mock_convert.side_effect = [mapping1, mapping2]

            result = await id_mapping_manager.validate_all_mappings(
                batch_size=10, max_mappings=2
            )

            assert "total_validated" in result
            assert "valid_mappings" in result
            assert "orphaned_mappings" in result
            assert result["total_validated"] == 2

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_mappings_dry_run(self, id_mapping_manager):
        """Test cleanup orphaned mappings in dry run mode."""
        orphaned_results = [
            {
                "m": {
                    "mapping_id": "orphan_1",
                    "last_validation_time": (
                        datetime.now(UTC) - timedelta(days=10)
                    ).isoformat(),
                }
            },
        ]

        id_mapping_manager.neo4j_manager.execute_read_query.return_value = (
            orphaned_results
        )

        result = await id_mapping_manager.cleanup_orphaned_mappings(
            dry_run=True, max_age_days=7
        )

        assert result["found_orphaned"] == 1
        assert result["deleted"] == 0
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_mappings_actual(self, id_mapping_manager):
        """Test actual cleanup of orphaned mappings."""
        orphaned_results = [
            {
                "m": {
                    "mapping_id": "orphan_1",
                    "last_validation_time": (
                        datetime.now(UTC) - timedelta(days=10)
                    ).isoformat(),
                }
            },
        ]

        id_mapping_manager.neo4j_manager.execute_read_query.return_value = (
            orphaned_results
        )

        with patch.object(id_mapping_manager, "delete_mapping") as mock_delete:
            mock_delete.return_value = True

            result = await id_mapping_manager.cleanup_orphaned_mappings(
                dry_run=False, max_age_days=7
            )

            assert result["found_orphaned"] == 1
            assert result["deleted"] == 1
            assert result["errors"] == 0
            mock_delete.assert_called_once_with("orphan_1")

    @pytest.mark.asyncio
    async def test_get_mapping_statistics(self, id_mapping_manager):
        """Test getting mapping statistics."""
        mock_stats = [
            {
                "total_mappings": 15,
                "active_mappings": 10,
                "orphaned_mappings": 3,
                "sync_failed_mappings": 2,
                "qdrant_missing": 1,
                "neo4j_missing": 2,
                "entity_types": ["Concept", "Person"],
                "mapping_types": ["document", "entity"],
            }
        ]

        id_mapping_manager.neo4j_manager.execute_read_query.return_value = mock_stats

        result = await id_mapping_manager.get_mapping_statistics()

        assert result["total_mappings"] == 15
        assert result["active_mappings"] == 10
        assert result["orphaned_mappings"] == 3
        assert "cache_size" in result
        assert "cache_max_size" in result

    @pytest.mark.asyncio
    async def test_validate_mapping_existence_qdrant_success(self, id_mapping_manager):
        """Test successful Qdrant existence validation."""
        mapping = IDMapping(qdrant_point_id="qdrant_123")

        # Mock Qdrant client to return point exists
        mock_client = (
            id_mapping_manager.qdrant_manager._ensure_client_connected.return_value
        )
        mock_client.retrieve.return_value = [
            Mock()
        ]  # Non-empty list means point exists

        await id_mapping_manager._validate_mapping_existence(mapping)

        assert mapping.qdrant_exists is True
        assert mapping.last_validation_time is not None

    @pytest.mark.asyncio
    async def test_validate_mapping_existence_qdrant_not_found(
        self, id_mapping_manager
    ):
        """Test Qdrant point not found validation."""
        mapping = IDMapping(qdrant_point_id="qdrant_123")

        # Mock Qdrant client to return empty response
        mock_client = (
            id_mapping_manager.qdrant_manager._ensure_client_connected.return_value
        )
        mock_client.retrieve.return_value = []  # Empty list means point doesn't exist

        await id_mapping_manager._validate_mapping_existence(mapping)

        assert mapping.qdrant_exists is False

    @pytest.mark.asyncio
    async def test_validate_mapping_existence_neo4j_success(self, id_mapping_manager):
        """Test successful Neo4j existence validation."""
        mapping = IDMapping(neo4j_node_id="123")  # Use numeric ID

        # Mock Neo4j to return node exists
        id_mapping_manager.neo4j_manager.execute_read_query.return_value = [
            {"count": 1}
        ]

        await id_mapping_manager._validate_mapping_existence(mapping)

        assert mapping.neo4j_exists is True

    @pytest.mark.asyncio
    async def test_validate_mapping_existence_neo4j_not_found(self, id_mapping_manager):
        """Test Neo4j node not found validation."""
        mapping = IDMapping(neo4j_node_id="123")  # Use numeric ID

        # Mock Neo4j to return empty result
        id_mapping_manager.neo4j_manager.execute_read_query.return_value = [
            {"count": 0}
        ]

        await id_mapping_manager._validate_mapping_existence(mapping)

        assert mapping.neo4j_exists is False

    @pytest.mark.asyncio
    async def test_store_mapping(self, id_mapping_manager):
        """Test storing mapping in Neo4j."""
        mapping = IDMapping(mapping_id="test_id", entity_name="Test")

        await id_mapping_manager._store_mapping(mapping)

        id_mapping_manager.neo4j_manager.execute_write_query.assert_called_once()
        # Verify the query contains the mapping data
        call_args = id_mapping_manager.neo4j_manager.execute_write_query.call_args
        assert "MERGE" in call_args[0][0]  # Query should use MERGE
        # Parameters should include mapping data
        assert call_args[1] is not None  # Parameters dict exists

    def test_cache_mapping(self, id_mapping_manager):
        """Test caching mapping."""
        mapping = IDMapping(mapping_id="test_id")

        id_mapping_manager._cache_mapping(mapping)

        assert "test_id" in id_mapping_manager._mapping_cache
        assert id_mapping_manager._mapping_cache["test_id"] == mapping

    def test_cache_mapping_size_limit(self, id_mapping_manager):
        """Test cache size limit enforcement."""
        # Set a small cache limit for testing
        id_mapping_manager._cache_max_size = 2

        # Add mappings beyond the limit
        for i in range(3):
            mapping = IDMapping(mapping_id=f"test_id_{i}")
            id_mapping_manager._cache_mapping(mapping)

        # Cache should not exceed the limit
        assert len(id_mapping_manager._mapping_cache) <= 2

    def test_neo4j_result_to_mapping(self, id_mapping_manager):
        """Test converting Neo4j result to mapping."""
        node_data = {
            "mapping_id": "test_id",
            "qdrant_point_id": "qdrant_123",
            "neo4j_node_id": "neo4j_456",
            "entity_type": "Concept",
            "mapping_type": "document",
            "status": "active",
            "metadata": {"key": "value"},
            "sync_version": 1,
            "document_version": 1,
            "created_time": datetime.now(UTC).isoformat(),
            "temporal_info": {
                "valid_from": datetime.now(UTC).isoformat(),
                "valid_to": None,
                "transaction_time": datetime.now(UTC).isoformat(),
                "version": 1,
                "superseded_by": None,
                "supersedes": None,
            },
        }

        mapping = id_mapping_manager._neo4j_result_to_mapping(node_data)

        assert mapping.mapping_id == "test_id"
        assert mapping.qdrant_point_id == "qdrant_123"
        assert mapping.neo4j_node_id == "neo4j_456"
        assert mapping.entity_type == EntityType.CONCEPT
        assert mapping.mapping_type == MappingType.DOCUMENT
        assert mapping.status == MappingStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_clear_cache(self, id_mapping_manager):
        """Test clearing the cache."""
        # Add some mappings to cache
        id_mapping_manager._mapping_cache["test1"] = IDMapping(mapping_id="test1")
        id_mapping_manager._mapping_cache["test2"] = IDMapping(mapping_id="test2")

        await id_mapping_manager.clear_cache()

        assert len(id_mapping_manager._mapping_cache) == 0

    @pytest.mark.asyncio
    async def test_health_check(self, id_mapping_manager):
        """Test health check functionality."""
        # Mock some statistics
        id_mapping_manager._mapping_cache["test1"] = IDMapping()

        # Mock get_mapping_statistics
        with patch.object(id_mapping_manager, "get_mapping_statistics") as mock_stats:
            mock_stats.return_value = {
                "total_mappings": 100,
                "active_mappings": 80,
                "orphaned_mappings": 20,
            }

            # Mock Neo4j test_connection
            id_mapping_manager.neo4j_manager.test_connection.return_value = True

            result = await id_mapping_manager.health_check()

            assert "healthy" in result
            assert "cache_size" in result
            assert "total_mappings" in result
            assert "neo4j_healthy" in result
            assert "qdrant_healthy" in result
            assert result["cache_size"] == 1

    @pytest.mark.asyncio
    async def test_get_mappings_by_version_range_success(
        self, id_mapping_manager, sample_neo4j_result
    ):
        """Test getting mappings by version range."""
        # Mock Neo4j response - need to fix the structure
        id_mapping_manager.neo4j_manager.execute_read_query.return_value = [
            {"m": sample_neo4j_result["m"]}
        ]

        # Test version range query
        mappings = await id_mapping_manager.get_mappings_by_version_range(
            min_version=1, max_version=5, entity_type=EntityType.CONCEPT, limit=100
        )

        # Verify query was called with correct parameters
        id_mapping_manager.neo4j_manager.execute_read_query.assert_called_once()
        call_args = id_mapping_manager.neo4j_manager.execute_read_query.call_args[0][0]
        assert "document_version >= 1" in call_args
        assert "document_version <= 5" in call_args
        assert f"entity_type = '{EntityType.CONCEPT.value}'" in call_args
        assert "LIMIT 100" in call_args

        # Verify results
        assert len(mappings) == 1
        assert isinstance(mappings[0], IDMapping)

    @pytest.mark.asyncio
    async def test_get_mappings_by_version_range_no_max_version(
        self, id_mapping_manager, sample_neo4j_result
    ):
        """Test getting mappings by version range without max version."""
        id_mapping_manager.neo4j_manager.execute_read_query.return_value = [
            {"m": sample_neo4j_result["m"]}
        ]

        mappings = await id_mapping_manager.get_mappings_by_version_range(
            min_version=3, max_version=None
        )

        # Verify query was called with correct parameters
        call_args = id_mapping_manager.neo4j_manager.execute_read_query.call_args[0][0]
        assert "document_version >= 3" in call_args
        assert "document_version <=" not in call_args

        assert len(mappings) == 1

    @pytest.mark.asyncio
    async def test_get_mappings_by_version_range_no_entity_type(
        self, id_mapping_manager, sample_neo4j_result
    ):
        """Test getting mappings by version range without entity type filter."""
        id_mapping_manager.neo4j_manager.execute_read_query.return_value = [
            {"m": sample_neo4j_result["m"]}
        ]

        mappings = await id_mapping_manager.get_mappings_by_version_range(
            min_version=1, max_version=10, entity_type=None
        )

        # Verify query was called without entity type filter
        call_args = id_mapping_manager.neo4j_manager.execute_read_query.call_args[0][0]
        assert "entity_type =" not in call_args

        assert len(mappings) == 1

    @pytest.mark.asyncio
    async def test_get_mappings_by_version_range_error_handling(
        self, id_mapping_manager
    ):
        """Test error handling in get_mappings_by_version_range."""
        # Mock Neo4j to raise exception
        id_mapping_manager.neo4j_manager.execute_read_query.side_effect = Exception(
            "Database error"
        )

        mappings = await id_mapping_manager.get_mappings_by_version_range(min_version=1)

        # Should return empty list on error
        assert mappings == []

    @pytest.mark.asyncio
    async def test_get_recently_updated_mappings_success(
        self, id_mapping_manager, sample_neo4j_result
    ):
        """Test getting recently updated mappings."""
        # Mock Neo4j response
        id_mapping_manager.neo4j_manager.execute_read_query.return_value = [
            {"m": sample_neo4j_result["m"]}
        ]

        # Test recent updates query
        mappings = await id_mapping_manager.get_recently_updated_mappings(
            hours=24, update_source="test_source", limit=50
        )

        # Verify query was called with correct parameters
        id_mapping_manager.neo4j_manager.execute_read_query.assert_called_once()
        call_args = id_mapping_manager.neo4j_manager.execute_read_query.call_args[0][0]
        assert "last_update_time >=" in call_args
        assert "update_source = 'test_source'" in call_args
        assert "LIMIT 50" in call_args

        # Verify results
        assert len(mappings) == 1
        assert isinstance(mappings[0], IDMapping)

    @pytest.mark.asyncio
    async def test_get_recently_updated_mappings_no_source_filter(
        self, id_mapping_manager, sample_neo4j_result
    ):
        """Test getting recently updated mappings without source filter."""
        id_mapping_manager.neo4j_manager.execute_read_query.return_value = [
            {"m": sample_neo4j_result["m"]}
        ]

        mappings = await id_mapping_manager.get_recently_updated_mappings(
            hours=48, update_source=None
        )

        # Verify query was called without source filter
        call_args = id_mapping_manager.neo4j_manager.execute_read_query.call_args[0][0]
        assert "update_source =" not in call_args

        assert len(mappings) == 1

    @pytest.mark.asyncio
    async def test_get_recently_updated_mappings_error_handling(
        self, id_mapping_manager
    ):
        """Test error handling in get_recently_updated_mappings."""
        # Mock Neo4j to raise exception
        id_mapping_manager.neo4j_manager.execute_read_query.side_effect = Exception(
            "Database error"
        )

        mappings = await id_mapping_manager.get_recently_updated_mappings(hours=24)

        # Should return empty list on error
        assert mappings == []


class TestMappingEnums:
    """Test cases for mapping enums."""

    def test_mapping_status_enum(self):
        """Test MappingStatus enum values."""
        assert MappingStatus.ACTIVE.value == "active"
        assert MappingStatus.INACTIVE.value == "inactive"
        assert MappingStatus.PENDING_SYNC.value == "pending_sync"
        assert MappingStatus.SYNC_FAILED.value == "sync_failed"
        assert MappingStatus.ORPHANED.value == "orphaned"

    def test_mapping_type_enum(self):
        """Test MappingType enum values."""
        assert MappingType.DOCUMENT.value == "document"
        assert MappingType.ENTITY.value == "entity"
        assert MappingType.RELATIONSHIP.value == "relationship"
        assert MappingType.EPISODE.value == "episode"


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.fixture
    def mock_neo4j_manager(self):
        """Create a mock Neo4j manager."""
        return Mock(spec=Neo4jManager)

    @pytest.fixture
    def mock_qdrant_manager(self):
        """Create a mock Qdrant manager."""
        mock_manager = Mock(spec=QdrantManager)
        mock_manager._ensure_client_connected = Mock()
        mock_client = Mock()
        mock_client.retrieve = Mock()
        mock_manager._ensure_client_connected.return_value = mock_client
        return mock_manager

    @pytest.fixture
    def id_mapping_manager(self, mock_neo4j_manager, mock_qdrant_manager):
        """Create an IDMappingManager instance with mocked dependencies."""
        with patch.object(IDMappingManager, "_ensure_mapping_table"):
            return IDMappingManager(
                neo4j_manager=mock_neo4j_manager, qdrant_manager=mock_qdrant_manager
            )

    @pytest.mark.asyncio
    async def test_validate_mapping_existence_qdrant_error(self, id_mapping_manager):
        """Test handling Qdrant validation errors."""
        mapping = IDMapping(qdrant_point_id="qdrant_123")

        # Mock Qdrant client to raise an exception
        mock_client = (
            id_mapping_manager.qdrant_manager._ensure_client_connected.return_value
        )
        mock_client.retrieve.side_effect = Exception("Qdrant error")

        await id_mapping_manager._validate_mapping_existence(mapping)

        # Should handle error gracefully and set exists to False
        assert mapping.qdrant_exists is False

    @pytest.mark.asyncio
    async def test_validate_mapping_existence_neo4j_error(self, id_mapping_manager):
        """Test handling Neo4j validation errors."""
        mapping = IDMapping(neo4j_node_id="neo4j_456")

        # Mock Neo4j to raise an exception
        id_mapping_manager.neo4j_manager.execute_read_query.side_effect = Exception(
            "Neo4j error"
        )

        await id_mapping_manager._validate_mapping_existence(mapping)

        # Should handle error gracefully and set exists to False
        assert mapping.neo4j_exists is False

    @pytest.mark.asyncio
    async def test_store_mapping_error(self, id_mapping_manager):
        """Test handling storage errors."""
        mapping = IDMapping(mapping_id="test_id")

        # Mock Neo4j to raise an exception
        id_mapping_manager.neo4j_manager.execute_write_query.side_effect = Exception(
            "Storage error"
        )

        with pytest.raises(Exception, match="Storage error"):
            await id_mapping_manager._store_mapping(mapping)
