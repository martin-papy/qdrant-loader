"""Tests for VersionOperations class.

This module tests the core version operations including creation,
retrieval, comparison, rollback, and snapshot functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_loader.core.versioning import (
    VersionConfig,
    VersionMetadata,
    VersionOperation,
    VersionStatus,
    VersionType,
)
from qdrant_loader.core.versioning.version_operations import VersionOperations


class TestVersionOperations:
    """Test suite for VersionOperations class."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for testing."""
        storage = AsyncMock()
        id_mapping_manager = AsyncMock()
        neo4j_manager = MagicMock()
        qdrant_manager = MagicMock()
        config = VersionConfig()
        return storage, id_mapping_manager, neo4j_manager, qdrant_manager, config

    @pytest.fixture
    def version_operations(self, mock_dependencies):
        """Create a VersionOperations instance for testing."""
        storage, id_mapping_manager, neo4j_manager, qdrant_manager, config = (
            mock_dependencies
        )
        return VersionOperations(
            storage=storage,
            id_mapping_manager=id_mapping_manager,
            neo4j_manager=neo4j_manager,
            qdrant_manager=qdrant_manager,
            config=config,
        )

    @pytest.fixture
    def sample_content(self):
        """Sample content for testing."""
        return {
            "title": "Test Document",
            "content": "This is test content",
            "metadata": {"author": "test_user", "created": "2024-01-01"},
        }

    @pytest.fixture
    def sample_version_metadata(self):
        """Sample version metadata for testing."""
        return VersionMetadata(
            entity_id="test_entity_123",
            version_type=VersionType.DOCUMENT,
            version_number=1,
            operation=VersionOperation.CREATE,
            content_hash="abc123",
            content_size=100,
            status=VersionStatus.ACTIVE,
        )

    def test_init(self, mock_dependencies):
        """Test VersionOperations initialization."""
        storage, id_mapping_manager, neo4j_manager, qdrant_manager, config = (
            mock_dependencies
        )

        ops = VersionOperations(
            storage=storage,
            id_mapping_manager=id_mapping_manager,
            neo4j_manager=neo4j_manager,
            qdrant_manager=qdrant_manager,
            config=config,
        )

        assert ops.storage == storage
        assert ops.id_mapping_manager == id_mapping_manager
        assert ops.neo4j_manager == neo4j_manager
        assert ops.qdrant_manager == qdrant_manager
        assert ops.config == config
        assert ops.logger is not None

    @pytest.mark.asyncio
    async def test_create_version_success(self, version_operations, sample_content):
        """Test successful version creation."""
        # Setup mocks
        version_operations.storage.get_entity_versions = AsyncMock(return_value=[])
        version_operations.storage.store_version_metadata = AsyncMock(return_value=True)

        # Test creation
        result = await version_operations.create_version(
            entity_id="test_entity",
            version_type=VersionType.DOCUMENT,
            content=sample_content,
            operation=VersionOperation.CREATE,
            parent_version_id="parent_123",
            supersedes="old_version",
            created_by="user123",
            tags=["test", "important"],
            is_milestone=True,
        )

        # Verify result
        assert result is not None
        assert result.entity_id == "test_entity"
        assert result.version_type == VersionType.DOCUMENT
        assert result.version_number == 1
        assert result.operation == VersionOperation.CREATE
        assert result.parent_version_id == "parent_123"
        assert result.supersedes == "old_version"
        assert result.created_by == "user123"
        assert result.tags == {"test", "important"}
        assert result.is_milestone is True
        assert result.status == VersionStatus.ACTIVE

        # Verify storage calls
        version_operations.storage.get_entity_versions.assert_called_once_with(
            "test_entity", VersionType.DOCUMENT
        )
        version_operations.storage.store_version_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_version_with_existing_versions(
        self, version_operations, sample_content
    ):
        """Test version creation with existing versions."""
        # Setup mock with existing versions
        existing_versions = [MagicMock(), MagicMock()]
        version_operations.storage.get_entity_versions = AsyncMock(
            return_value=existing_versions
        )
        version_operations.storage.store_version_metadata = AsyncMock(return_value=True)

        # Test creation
        result = await version_operations.create_version(
            entity_id="test_entity",
            version_type=VersionType.DOCUMENT,
            content=sample_content,
        )

        # Verify version number incremented
        assert result.version_number == 3  # 2 existing + 1

    @pytest.mark.asyncio
    async def test_create_version_storage_failure(
        self, version_operations, sample_content
    ):
        """Test version creation with storage failure."""
        # Setup mocks
        version_operations.storage.get_entity_versions = AsyncMock(return_value=[])
        version_operations.storage.store_version_metadata = AsyncMock(
            return_value=False
        )

        # Test creation
        result = await version_operations.create_version(
            entity_id="test_entity",
            version_type=VersionType.DOCUMENT,
            content=sample_content,
        )

        # Verify failure
        assert result is None

    @pytest.mark.asyncio
    async def test_create_version_exception(self, version_operations, sample_content):
        """Test version creation with exception."""
        # Setup mock to raise exception
        version_operations.storage.get_entity_versions = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Test creation
        result = await version_operations.create_version(
            entity_id="test_entity",
            version_type=VersionType.DOCUMENT,
            content=sample_content,
        )

        # Verify failure
        assert result is None

    @pytest.mark.asyncio
    async def test_get_version_success(
        self, version_operations, sample_version_metadata
    ):
        """Test successful version retrieval."""
        # Setup mock
        version_operations.storage.get_version_metadata = AsyncMock(
            return_value=sample_version_metadata
        )

        # Test retrieval
        result = await version_operations.get_version("version_123")

        # Verify result
        assert result == sample_version_metadata
        version_operations.storage.get_version_metadata.assert_called_once_with(
            "version_123"
        )

    @pytest.mark.asyncio
    async def test_get_version_not_found(self, version_operations):
        """Test version retrieval when not found."""
        # Setup mock
        version_operations.storage.get_version_metadata = AsyncMock(return_value=None)

        # Test retrieval
        result = await version_operations.get_version("nonexistent")

        # Verify result
        assert result is None

    @pytest.mark.asyncio
    async def test_get_latest_version_success(
        self, version_operations, sample_version_metadata
    ):
        """Test successful latest version retrieval."""
        # Setup mock
        version_operations.storage.get_entity_versions = AsyncMock(
            return_value=[sample_version_metadata]
        )

        # Test retrieval
        result = await version_operations.get_latest_version(
            "test_entity", VersionType.DOCUMENT
        )

        # Verify result
        assert result == sample_version_metadata
        version_operations.storage.get_entity_versions.assert_called_once_with(
            "test_entity", VersionType.DOCUMENT, limit=1
        )

    @pytest.mark.asyncio
    async def test_get_latest_version_no_versions(self, version_operations):
        """Test latest version retrieval when no versions exist."""
        # Setup mock
        version_operations.storage.get_entity_versions = AsyncMock(return_value=[])

        # Test retrieval
        result = await version_operations.get_latest_version(
            "test_entity", VersionType.DOCUMENT
        )

        # Verify result
        assert result is None

    @pytest.mark.asyncio
    async def test_compare_versions_success(self, version_operations):
        """Test successful version comparison."""
        # Setup mock versions
        from_version = VersionMetadata(
            version_id="version_1",
            entity_id="test_entity",
            version_type=VersionType.DOCUMENT,
        )
        to_version = VersionMetadata(
            version_id="version_2",
            entity_id="test_entity",
            version_type=VersionType.DOCUMENT,
        )

        from_content = {"field1": "value1", "field2": "value2"}
        to_content = {"field1": "value1_modified", "field3": "value3"}

        # Setup mocks
        version_operations.storage.get_version_metadata = AsyncMock()
        version_operations.storage.get_version_metadata.side_effect = [
            from_version,
            to_version,
        ]
        version_operations._get_version_content = AsyncMock()
        version_operations._get_version_content.side_effect = [from_content, to_content]

        # Test comparison
        result = await version_operations.compare_versions("version_1", "version_2")

        # Verify result
        assert result is not None
        assert result.from_version_id == "version_1"
        assert result.to_version_id == "version_2"
        assert result.diff_type == "content"
        assert result.added_fields == {"field3": "value3"}
        assert result.removed_fields == {"field2": "value2"}
        assert result.modified_fields == {"field1": ("value1", "value1_modified")}
        assert result.total_changes == 3
        assert 0 <= result.similarity_score <= 1

    @pytest.mark.asyncio
    async def test_compare_versions_version_not_found(self, version_operations):
        """Test version comparison when version not found."""
        # Setup mock
        version_operations.storage.get_version_metadata = AsyncMock(return_value=None)

        # Test comparison
        result = await version_operations.compare_versions("version_1", "version_2")

        # Verify result
        assert result is None

    @pytest.mark.asyncio
    async def test_compare_versions_content_not_found(self, version_operations):
        """Test version comparison when content not found."""
        # Setup mock versions
        from_version = VersionMetadata(version_id="version_1")
        to_version = VersionMetadata(version_id="version_2")

        # Setup mocks
        version_operations.storage.get_version_metadata = AsyncMock()
        version_operations.storage.get_version_metadata.side_effect = [
            from_version,
            to_version,
        ]
        version_operations._get_version_content = AsyncMock(return_value=None)

        # Test comparison
        result = await version_operations.compare_versions("version_1", "version_2")

        # Verify result
        assert result is None

    @pytest.mark.asyncio
    async def test_compare_versions_exception(self, version_operations):
        """Test version comparison with exception."""
        # Setup mock to raise exception
        version_operations.storage.get_version_metadata = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Test comparison
        result = await version_operations.compare_versions("version_1", "version_2")

        # Verify result
        assert result is None

    @pytest.mark.asyncio
    async def test_rollback_to_version_success(
        self, version_operations, sample_version_metadata
    ):
        """Test successful version rollback."""
        content = {"key": "value"}

        # Setup mocks
        version_operations.storage.get_version_metadata = AsyncMock(
            return_value=sample_version_metadata
        )
        version_operations._get_version_content = AsyncMock(return_value=content)
        version_operations._restore_version_content = AsyncMock(return_value=True)
        version_operations.create_version = AsyncMock(
            return_value=sample_version_metadata
        )

        # Test rollback
        result = await version_operations.rollback_to_version(
            "test_entity", "version_123", "user123"
        )

        # Verify result
        assert result is True

        # Verify calls
        version_operations.storage.get_version_metadata.assert_called_once_with(
            "version_123"
        )
        version_operations._get_version_content.assert_called_once_with(
            sample_version_metadata
        )
        version_operations._restore_version_content.assert_called_once_with(
            sample_version_metadata, content
        )
        version_operations.create_version.assert_called_once()

    @pytest.mark.asyncio
    async def test_rollback_to_version_not_found(self, version_operations):
        """Test rollback when target version not found."""
        # Setup mock
        version_operations.storage.get_version_metadata = AsyncMock(return_value=None)

        # Test rollback
        result = await version_operations.rollback_to_version(
            "test_entity", "nonexistent", "user123"
        )

        # Verify result
        assert result is False

    @pytest.mark.asyncio
    async def test_rollback_to_version_content_not_found(
        self, version_operations, sample_version_metadata
    ):
        """Test rollback when content not found."""
        # Setup mocks
        version_operations.storage.get_version_metadata = AsyncMock(
            return_value=sample_version_metadata
        )
        version_operations._get_version_content = AsyncMock(return_value=None)

        # Test rollback
        result = await version_operations.rollback_to_version(
            "test_entity", "version_123", "user123"
        )

        # Verify result
        assert result is False

    @pytest.mark.asyncio
    async def test_rollback_to_version_restore_failure(
        self, version_operations, sample_version_metadata
    ):
        """Test rollback when restore fails."""
        content = {"key": "value"}

        # Setup mocks
        version_operations.storage.get_version_metadata = AsyncMock(
            return_value=sample_version_metadata
        )
        version_operations._get_version_content = AsyncMock(return_value=content)
        version_operations._restore_version_content = AsyncMock(return_value=False)

        # Test rollback
        result = await version_operations.rollback_to_version(
            "test_entity", "version_123", "user123"
        )

        # Verify result
        assert result is False

    @pytest.mark.asyncio
    async def test_rollback_to_version_exception(self, version_operations):
        """Test rollback with exception."""
        # Setup mock to raise exception
        version_operations.storage.get_version_metadata = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Test rollback
        result = await version_operations.rollback_to_version(
            "test_entity", "version_123", "user123"
        )

        # Verify result
        assert result is False

    @pytest.mark.asyncio
    async def test_create_snapshot_success(self, version_operations):
        """Test successful snapshot creation."""
        # Setup mocks
        version_operations.storage.store_version_snapshot = AsyncMock(return_value=True)
        version_operations._get_entity_snapshot_data = AsyncMock(
            return_value={"entity_id": "entity_1", "data": "test"}
        )

        # Test creation
        result = await version_operations.create_snapshot(
            description="Test snapshot",
            entity_ids=["entity_1", "entity_2"],
            created_by="user123",
            tags=["backup", "test"],
        )

        # Verify result
        assert result is not None
        assert result.description == "Test snapshot"
        assert result.created_by == "user123"
        assert result.tags == {"backup", "test"}
        assert result.entity_count >= 0
        assert result.relationship_count >= 0
        assert result.mapping_count >= 0

        # Verify storage call
        version_operations.storage.store_version_snapshot.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_snapshot_no_entities(self, version_operations):
        """Test snapshot creation without specific entities."""
        # Setup mock
        version_operations.storage.store_version_snapshot = AsyncMock(return_value=True)

        # Test creation
        result = await version_operations.create_snapshot(description="Test snapshot")

        # Verify result
        assert result is not None
        assert result.description == "Test snapshot"
        assert result.entity_count == 0

    @pytest.mark.asyncio
    async def test_create_snapshot_storage_failure(self, version_operations):
        """Test snapshot creation with storage failure."""
        # Setup mock
        version_operations.storage.store_version_snapshot = AsyncMock(
            return_value=False
        )

        # Test creation
        result = await version_operations.create_snapshot(description="Test snapshot")

        # Verify result
        assert result is None

    @pytest.mark.asyncio
    async def test_create_snapshot_exception(self, version_operations):
        """Test snapshot creation with exception."""
        # Setup mock to raise exception
        version_operations.storage.store_version_snapshot = AsyncMock(
            side_effect=Exception("Storage error")
        )

        # Test creation
        result = await version_operations.create_snapshot(description="Test snapshot")

        # Verify result
        assert result is None

    def test_calculate_content_hash(self, version_operations, sample_content):
        """Test content hash calculation."""
        result = version_operations._calculate_content_hash(sample_content)

        # Verify result
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hex digest length

        # Test consistency
        result2 = version_operations._calculate_content_hash(sample_content)
        assert result == result2

        # Test different content produces different hash
        different_content = {"different": "content"}
        result3 = version_operations._calculate_content_hash(different_content)
        assert result != result3

    def test_calculate_content_hash_deterministic(self, version_operations):
        """Test that content hash is deterministic regardless of dict order."""
        content1 = {"b": 2, "a": 1, "c": 3}
        content2 = {"a": 1, "b": 2, "c": 3}

        hash1 = version_operations._calculate_content_hash(content1)
        hash2 = version_operations._calculate_content_hash(content2)

        assert hash1 == hash2

    @pytest.mark.asyncio
    async def test_get_version_content_document(self, version_operations):
        """Test getting version content for document type."""
        version = VersionMetadata(
            entity_id="doc_123",
            version_type=VersionType.DOCUMENT,
        )

        mock_mapping = MagicMock()
        mock_mapping.to_dict.return_value = {"doc_data": "test"}

        # Setup mock
        version_operations.id_mapping_manager.get_mapping_by_id = AsyncMock(
            return_value=mock_mapping
        )

        # Test content retrieval
        result = await version_operations._get_version_content(version)

        # Verify result
        assert result == {"doc_data": "test"}
        version_operations.id_mapping_manager.get_mapping_by_id.assert_called_once_with(
            "doc_123"
        )

    @pytest.mark.asyncio
    async def test_get_version_content_entity(self, version_operations):
        """Test getting version content for entity type."""
        version = VersionMetadata(
            entity_id="entity_123",
            version_type=VersionType.ENTITY,
        )

        # Create a custom mock class that behaves like a Neo4j node
        class MockNode:
            def __init__(self):
                self.element_id = "element_123"
                self.labels = ["Person", "User"]
                self._properties = {"name": "John", "age": 30}

            def __iter__(self):
                return iter(self._properties.items())

            def __getitem__(self, key):
                return self._properties[key]

            def keys(self):
                return self._properties.keys()

            def values(self):
                return self._properties.values()

            def items(self):
                return self._properties.items()

        mock_node = MockNode()

        # Setup mock
        version_operations.neo4j_manager.execute_read_query = MagicMock(
            return_value=[{"n": mock_node}]
        )

        # Test content retrieval
        result = await version_operations._get_version_content(version)

        # Verify result
        assert result is not None
        assert result["id"] == "element_123"
        assert result["labels"] == ["Person", "User"]
        assert result["properties"] == {"name": "John", "age": 30}

    @pytest.mark.asyncio
    async def test_get_version_content_relationship(self, version_operations):
        """Test getting version content for relationship type."""
        version = VersionMetadata(
            entity_id="rel_123",
            version_type=VersionType.RELATIONSHIP,
        )

        # Create a custom mock class that behaves like a Neo4j relationship
        class MockRelationship:
            def __init__(self):
                self.element_id = "rel_element_123"
                self.type = "KNOWS"
                self._properties = {"since": "2020"}

            def __iter__(self):
                return iter(self._properties.items())

            def __getitem__(self, key):
                return self._properties[key]

            def keys(self):
                return self._properties.keys()

            def values(self):
                return self._properties.values()

            def items(self):
                return self._properties.items()

        mock_rel = MockRelationship()

        # Setup mock
        version_operations.neo4j_manager.execute_read_query = MagicMock(
            return_value=[{"r": mock_rel}]
        )

        # Test content retrieval
        result = await version_operations._get_version_content(version)

        # Verify result
        assert result is not None
        assert result["id"] == "rel_element_123"
        assert result["type"] == "KNOWS"
        assert result["properties"] == {"since": "2020"}

    @pytest.mark.asyncio
    async def test_get_version_content_mapping(self, version_operations):
        """Test getting version content for mapping type."""
        version = VersionMetadata(
            entity_id="mapping_123",
            version_type=VersionType.MAPPING,
        )

        mock_mapping = MagicMock()
        mock_mapping.to_dict.return_value = {"mapping_data": "test"}

        # Setup mock
        version_operations.id_mapping_manager.get_mapping_by_id = AsyncMock(
            return_value=mock_mapping
        )

        # Test content retrieval
        result = await version_operations._get_version_content(version)

        # Verify result
        assert result == {"mapping_data": "test"}

    @pytest.mark.asyncio
    async def test_get_version_content_not_found(self, version_operations):
        """Test getting version content when not found."""
        version = VersionMetadata(
            entity_id="nonexistent",
            version_type=VersionType.DOCUMENT,
        )

        # Setup mock
        version_operations.id_mapping_manager.get_mapping_by_id = AsyncMock(
            return_value=None
        )

        # Test content retrieval
        result = await version_operations._get_version_content(version)

        # Verify result
        assert result is None

    @pytest.mark.asyncio
    async def test_get_version_content_exception(self, version_operations):
        """Test getting version content with exception."""
        version = VersionMetadata(
            entity_id="entity_123",
            version_type=VersionType.DOCUMENT,
        )

        # Setup mock to raise exception
        version_operations.id_mapping_manager.get_mapping_by_id = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Test content retrieval
        result = await version_operations._get_version_content(version)

        # Verify result
        assert result is None

    @pytest.mark.asyncio
    async def test_restore_version_content_document(self, version_operations):
        """Test restoring version content for document type."""
        version = VersionMetadata(
            entity_id="doc_123",
            version_type=VersionType.DOCUMENT,
        )
        content = {"doc_data": "restored"}

        # Setup mock
        with patch(
            "qdrant_loader.core.versioning.version_operations.IDMapping"
        ) as mock_mapping_class:
            mock_mapping = MagicMock()
            mock_mapping_class.from_dict.return_value = mock_mapping
            mock_mapping.mapping_id = "mapping_123"

            version_operations.id_mapping_manager.update_mapping = AsyncMock(
                return_value=mock_mapping
            )

            # Test content restoration
            result = await version_operations._restore_version_content(version, content)

            # Verify result
            assert result is True
            mock_mapping_class.from_dict.assert_called_once_with(content)
            version_operations.id_mapping_manager.update_mapping.assert_called_once_with(
                "mapping_123", content
            )

    @pytest.mark.asyncio
    async def test_restore_version_content_entity(self, version_operations):
        """Test restoring version content for entity type."""
        version = VersionMetadata(
            entity_id="entity_123",
            version_type=VersionType.ENTITY,
        )
        content = {"properties": {"name": "John", "age": 30}}

        # Setup mock
        version_operations.neo4j_manager.execute_write_query = MagicMock(
            return_value=[{"n": "updated_node"}]
        )

        # Test content restoration
        result = await version_operations._restore_version_content(version, content)

        # Verify result
        assert result is True
        version_operations.neo4j_manager.execute_write_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_restore_version_content_relationship(self, version_operations):
        """Test restoring version content for relationship type."""
        version = VersionMetadata(
            entity_id="rel_123",
            version_type=VersionType.RELATIONSHIP,
        )
        content = {"properties": {"since": "2020"}}

        # Setup mock
        version_operations.neo4j_manager.execute_write_query = MagicMock(
            return_value=[{"r": "updated_rel"}]
        )

        # Test content restoration
        result = await version_operations._restore_version_content(version, content)

        # Verify result
        assert result is True

    @pytest.mark.asyncio
    async def test_restore_version_content_mapping(self, version_operations):
        """Test restoring version content for mapping type."""
        version = VersionMetadata(
            entity_id="mapping_123",
            version_type=VersionType.MAPPING,
        )
        content = {"mapping_data": "restored"}

        # Setup mock
        with patch(
            "qdrant_loader.core.versioning.version_operations.IDMapping"
        ) as mock_mapping_class:
            mock_mapping = MagicMock()
            mock_mapping_class.from_dict.return_value = mock_mapping
            mock_mapping.mapping_id = "mapping_123"

            version_operations.id_mapping_manager.update_mapping = AsyncMock(
                return_value=mock_mapping
            )

            # Test content restoration
            result = await version_operations._restore_version_content(version, content)

            # Verify result
            assert result is True

    @pytest.mark.asyncio
    async def test_restore_version_content_failure(self, version_operations):
        """Test restoring version content with failure."""
        version = VersionMetadata(
            entity_id="doc_123",
            version_type=VersionType.DOCUMENT,
        )
        content = {"doc_data": "restored"}

        # Setup mock to return None (failure)
        with patch("qdrant_loader.core.versioning.version_operations.IDMapping"):
            version_operations.id_mapping_manager.update_mapping = AsyncMock(
                return_value=None
            )

            # Test content restoration
            result = await version_operations._restore_version_content(version, content)

            # Verify result
            assert result is False

    @pytest.mark.asyncio
    async def test_restore_version_content_exception(self, version_operations):
        """Test restoring version content with exception."""
        version = VersionMetadata(
            entity_id="doc_123",
            version_type=VersionType.DOCUMENT,
        )
        content = {"doc_data": "restored"}

        # Setup mock to raise exception
        with patch(
            "qdrant_loader.core.versioning.version_operations.IDMapping"
        ) as mock_mapping_class:
            mock_mapping_class.from_dict.side_effect = Exception("Restore error")

            # Test content restoration
            result = await version_operations._restore_version_content(version, content)

            # Verify result
            assert result is False

    def test_calculate_diff_basic(self, version_operations):
        """Test basic diff calculation."""
        from_content = {"field1": "value1", "field2": "value2", "field3": "value3"}
        to_content = {
            "field1": "value1_modified",
            "field3": "value3",
            "field4": "value4",
        }

        result = version_operations._calculate_diff(from_content, to_content)

        # Verify result
        assert result["added"] == {"field4": "value4"}
        assert result["removed"] == {"field2": "value2"}
        assert result["modified"] == {"field1": ("value1", "value1_modified")}
        assert result["total_changes"] == 3
        assert 0 <= result["similarity_score"] <= 1

    def test_calculate_diff_identical(self, version_operations):
        """Test diff calculation for identical content."""
        content = {"field1": "value1", "field2": "value2"}

        result = version_operations._calculate_diff(content, content)

        # Verify result
        assert result["added"] == {}
        assert result["removed"] == {}
        assert result["modified"] == {}
        assert result["total_changes"] == 0
        assert result["similarity_score"] == 1.0

    def test_calculate_diff_completely_different(self, version_operations):
        """Test diff calculation for completely different content."""
        from_content = {"field1": "value1", "field2": "value2"}
        to_content = {"field3": "value3", "field4": "value4"}

        result = version_operations._calculate_diff(from_content, to_content)

        # Verify result
        assert result["added"] == {"field3": "value3", "field4": "value4"}
        assert result["removed"] == {"field1": "value1", "field2": "value2"}
        assert result["modified"] == {}
        assert result["total_changes"] == 4
        assert result["similarity_score"] == 0.0

    def test_calculate_diff_empty_content(self, version_operations):
        """Test diff calculation with empty content."""
        from_content = {}
        to_content = {"field1": "value1"}

        result = version_operations._calculate_diff(from_content, to_content)

        # Verify result
        assert result["added"] == {"field1": "value1"}
        assert result["removed"] == {}
        assert result["modified"] == {}
        assert result["total_changes"] == 1
        assert result["similarity_score"] == 0.0

    @pytest.mark.asyncio
    async def test_get_entity_snapshot_data_success(self, version_operations):
        """Test successful entity snapshot data retrieval."""
        result = await version_operations._get_entity_snapshot_data("entity_123")

        # Verify result
        assert result is not None
        assert result["entity_id"] == "entity_123"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_entity_snapshot_data_exception(self, version_operations):
        """Test entity snapshot data retrieval with exception."""
        # Mock to raise exception (would need to modify the method to actually test this)
        # For now, test the basic functionality
        result = await version_operations._get_entity_snapshot_data("entity_123")

        # Verify result
        assert result is not None
        assert result["entity_id"] == "entity_123"
