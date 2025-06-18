"""Tests for version types and data structures."""

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from qdrant_loader.core.versioning.version_types import (
    VersionConfig,
    VersionDiff,
    VersionMetadata,
    VersionOperation,
    VersionSnapshot,
    VersionStatistics,
    VersionStatus,
    VersionType,
)


class TestVersionType:
    """Test VersionType enum."""

    def test_version_type_values(self):
        """Test VersionType enum values."""
        assert VersionType.DOCUMENT.value == "document"
        assert VersionType.ENTITY.value == "entity"
        assert VersionType.RELATIONSHIP.value == "relationship"
        assert VersionType.MAPPING.value == "mapping"
        assert VersionType.SYSTEM.value == "system"

    def test_version_type_count(self):
        """Test VersionType enum has expected number of values."""
        assert len(VersionType) == 5


class TestVersionOperation:
    """Test VersionOperation enum."""

    def test_version_operation_values(self):
        """Test VersionOperation enum values."""
        assert VersionOperation.CREATE.value == "create"
        assert VersionOperation.UPDATE.value == "update"
        assert VersionOperation.DELETE.value == "delete"
        assert VersionOperation.MERGE.value == "merge"
        assert VersionOperation.BRANCH.value == "branch"
        assert VersionOperation.ROLLBACK.value == "rollback"

    def test_version_operation_count(self):
        """Test VersionOperation enum has expected number of values."""
        assert len(VersionOperation) == 6


class TestVersionStatus:
    """Test VersionStatus enum."""

    def test_version_status_values(self):
        """Test VersionStatus enum values."""
        assert VersionStatus.ACTIVE.value == "active"
        assert VersionStatus.SUPERSEDED.value == "superseded"
        assert VersionStatus.ARCHIVED.value == "archived"
        assert VersionStatus.DELETED.value == "deleted"
        assert VersionStatus.PENDING.value == "pending"

    def test_version_status_count(self):
        """Test VersionStatus enum has expected number of values."""
        assert len(VersionStatus) == 5


class TestVersionMetadata:
    """Test VersionMetadata dataclass."""

    def test_default_values(self):
        """Test VersionMetadata default values."""
        metadata = VersionMetadata()

        # Check that UUID is generated
        assert isinstance(metadata.version_id, str)
        assert len(metadata.version_id) == 36  # UUID length

        # Check defaults
        assert metadata.entity_id == ""
        assert metadata.version_type == VersionType.DOCUMENT
        assert metadata.version_number == 1
        assert isinstance(metadata.created_at, datetime)
        assert isinstance(metadata.valid_from, datetime)
        assert metadata.valid_to is None
        assert metadata.parent_version_id is None
        assert metadata.child_version_ids == []
        assert metadata.supersedes is None
        assert metadata.superseded_by is None
        assert metadata.operation == VersionOperation.CREATE
        assert metadata.operation_source == "system"
        assert metadata.operation_metadata == {}
        assert metadata.content_hash is None
        assert metadata.content_size == 0
        assert metadata.status == VersionStatus.ACTIVE
        assert metadata.is_milestone is False
        assert metadata.tags == set()
        assert metadata.created_by is None
        assert metadata.modified_by is None

    def test_custom_values(self):
        """Test VersionMetadata with custom values."""
        created_time = datetime(2024, 1, 1, tzinfo=UTC)
        valid_from_time = datetime(2024, 1, 2, tzinfo=UTC)
        valid_to_time = datetime(2024, 12, 31, tzinfo=UTC)

        metadata = VersionMetadata(
            version_id="test-version-id",
            entity_id="test-entity-id",
            version_type=VersionType.ENTITY,
            version_number=5,
            created_at=created_time,
            valid_from=valid_from_time,
            valid_to=valid_to_time,
            parent_version_id="parent-id",
            child_version_ids=["child1", "child2"],
            supersedes="supersedes-id",
            superseded_by="superseded-by-id",
            operation=VersionOperation.UPDATE,
            operation_source="user",
            operation_metadata={"key": "value"},
            content_hash="hash123",
            content_size=1024,
            status=VersionStatus.SUPERSEDED,
            is_milestone=True,
            tags={"tag1", "tag2"},
            created_by="user1",
            modified_by="user2",
        )

        assert metadata.version_id == "test-version-id"
        assert metadata.entity_id == "test-entity-id"
        assert metadata.version_type == VersionType.ENTITY
        assert metadata.version_number == 5
        assert metadata.created_at == created_time
        assert metadata.valid_from == valid_from_time
        assert metadata.valid_to == valid_to_time
        assert metadata.parent_version_id == "parent-id"
        assert metadata.child_version_ids == ["child1", "child2"]
        assert metadata.supersedes == "supersedes-id"
        assert metadata.superseded_by == "superseded-by-id"
        assert metadata.operation == VersionOperation.UPDATE
        assert metadata.operation_source == "user"
        assert metadata.operation_metadata == {"key": "value"}
        assert metadata.content_hash == "hash123"
        assert metadata.content_size == 1024
        assert metadata.status == VersionStatus.SUPERSEDED
        assert metadata.is_milestone is True
        assert metadata.tags == {"tag1", "tag2"}
        assert metadata.created_by == "user1"
        assert metadata.modified_by == "user2"

    def test_to_dict_complete(self):
        """Test conversion to dictionary with all fields."""
        created_time = datetime(2024, 1, 1, tzinfo=UTC)
        valid_from_time = datetime(2024, 1, 2, tzinfo=UTC)
        valid_to_time = datetime(2024, 12, 31, tzinfo=UTC)

        metadata = VersionMetadata(
            version_id="test-version-id",
            entity_id="test-entity-id",
            version_type=VersionType.RELATIONSHIP,
            version_number=3,
            created_at=created_time,
            valid_from=valid_from_time,
            valid_to=valid_to_time,
            parent_version_id="parent-id",
            child_version_ids=["child1", "child2"],
            supersedes="supersedes-id",
            superseded_by="superseded-by-id",
            operation=VersionOperation.MERGE,
            operation_source="api",
            operation_metadata={"merge_type": "automatic"},
            content_hash="abc123",
            content_size=2048,
            status=VersionStatus.ARCHIVED,
            is_milestone=True,
            tags={"milestone", "important"},
            created_by="admin",
            modified_by="system",
        )

        result = metadata.to_dict()

        expected_keys = {
            "version_id",
            "entity_id",
            "version_type",
            "version_number",
            "created_at",
            "valid_from",
            "valid_to",
            "parent_version_id",
            "child_version_ids",
            "supersedes",
            "superseded_by",
            "operation",
            "operation_source",
            "operation_metadata",
            "content_hash",
            "content_size",
            "status",
            "is_milestone",
            "tags",
            "created_by",
            "modified_by",
        }

        assert set(result.keys()) == expected_keys
        assert result["version_id"] == "test-version-id"
        assert result["entity_id"] == "test-entity-id"
        assert result["version_type"] == "relationship"
        assert result["version_number"] == 3
        assert result["created_at"] == created_time.isoformat()
        assert result["valid_from"] == valid_from_time.isoformat()
        assert result["valid_to"] == valid_to_time.isoformat()
        assert result["parent_version_id"] == "parent-id"
        assert result["child_version_ids"] == ["child1", "child2"]
        assert result["supersedes"] == "supersedes-id"
        assert result["superseded_by"] == "superseded-by-id"
        assert result["operation"] == "merge"
        assert result["operation_source"] == "api"
        assert result["operation_metadata"] == {"merge_type": "automatic"}
        assert result["content_hash"] == "abc123"
        assert result["content_size"] == 2048
        assert result["status"] == "archived"
        assert result["is_milestone"] is True
        assert set(result["tags"]) == {"milestone", "important"}
        assert result["created_by"] == "admin"
        assert result["modified_by"] == "system"

    def test_to_dict_minimal(self):
        """Test conversion to dictionary with minimal fields."""
        metadata = VersionMetadata(entity_id="minimal-entity")

        result = metadata.to_dict()

        assert result["entity_id"] == "minimal-entity"
        assert result["version_type"] == "document"
        assert result["version_number"] == 1
        assert result["valid_to"] is None
        assert result["parent_version_id"] is None
        assert result["child_version_ids"] == []
        assert result["supersedes"] is None
        assert result["superseded_by"] is None
        assert result["operation"] == "create"
        assert result["operation_source"] == "system"
        assert result["operation_metadata"] == {}
        assert result["content_hash"] is None
        assert result["content_size"] == 0
        assert result["status"] == "active"
        assert result["is_milestone"] is False
        assert result["tags"] == []
        assert result["created_by"] is None
        assert result["modified_by"] is None

    def test_from_dict_complete(self):
        """Test creation from dictionary with all fields."""
        data = {
            "version_id": "test-version-id",
            "entity_id": "test-entity-id",
            "version_type": "mapping",
            "version_number": 7,
            "created_at": "2024-01-01T00:00:00+00:00",
            "valid_from": "2024-01-02T00:00:00+00:00",
            "valid_to": "2024-12-31T23:59:59+00:00",
            "parent_version_id": "parent-id",
            "child_version_ids": ["child1", "child2", "child3"],
            "supersedes": "supersedes-id",
            "superseded_by": "superseded-by-id",
            "operation": "branch",
            "operation_source": "migration",
            "operation_metadata": {"branch_name": "feature"},
            "content_hash": "def456",
            "content_size": 4096,
            "status": "pending",
            "is_milestone": True,
            "tags": ["feature", "experimental"],
            "created_by": "developer",
            "modified_by": "reviewer",
        }

        metadata = VersionMetadata.from_dict(data)

        assert metadata.version_id == "test-version-id"
        assert metadata.entity_id == "test-entity-id"
        assert metadata.version_type == VersionType.MAPPING
        assert metadata.version_number == 7
        assert metadata.created_at == datetime(2024, 1, 1, tzinfo=UTC)
        assert metadata.valid_from == datetime(2024, 1, 2, tzinfo=UTC)
        assert metadata.valid_to == datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC)
        assert metadata.parent_version_id == "parent-id"
        assert metadata.child_version_ids == ["child1", "child2", "child3"]
        assert metadata.supersedes == "supersedes-id"
        assert metadata.superseded_by == "superseded-by-id"
        assert metadata.operation == VersionOperation.BRANCH
        assert metadata.operation_source == "migration"
        assert metadata.operation_metadata == {"branch_name": "feature"}
        assert metadata.content_hash == "def456"
        assert metadata.content_size == 4096
        assert metadata.status == VersionStatus.PENDING
        assert metadata.is_milestone is True
        assert metadata.tags == {"feature", "experimental"}
        assert metadata.created_by == "developer"
        assert metadata.modified_by == "reviewer"

    def test_from_dict_minimal(self):
        """Test creation from dictionary with minimal fields."""
        data = {
            "version_id": "minimal-id",
            "entity_id": "minimal-entity",
            "version_type": "system",
            "version_number": 1,
            "created_at": "2024-01-01T12:00:00+00:00",
            "valid_from": "2024-01-01T12:00:00+00:00",
            "operation": "create",
            "operation_source": "system",
            "status": "active",
        }

        metadata = VersionMetadata.from_dict(data)

        assert metadata.version_id == "minimal-id"
        assert metadata.entity_id == "minimal-entity"
        assert metadata.version_type == VersionType.SYSTEM
        assert metadata.version_number == 1
        assert metadata.created_at == datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        assert metadata.valid_from == datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        assert metadata.valid_to is None
        assert metadata.parent_version_id is None
        assert metadata.child_version_ids == []
        assert metadata.supersedes is None
        assert metadata.superseded_by is None
        assert metadata.operation == VersionOperation.CREATE
        assert metadata.operation_source == "system"
        assert metadata.operation_metadata == {}
        assert metadata.content_hash is None
        assert metadata.content_size == 0
        assert metadata.status == VersionStatus.ACTIVE
        assert metadata.is_milestone is False
        assert metadata.tags == set()
        assert metadata.created_by is None
        assert metadata.modified_by is None


class TestVersionDiff:
    """Test VersionDiff dataclass."""

    def test_default_values(self):
        """Test VersionDiff default values."""
        diff = VersionDiff(
            from_version_id="from-id",
            to_version_id="to-id",
            diff_type="content",
        )

        assert diff.from_version_id == "from-id"
        assert diff.to_version_id == "to-id"
        assert diff.diff_type == "content"
        assert diff.added_fields == {}
        assert diff.removed_fields == {}
        assert diff.modified_fields == {}
        assert diff.total_changes == 0
        assert diff.similarity_score == 0.0
        assert isinstance(diff.generated_at, datetime)
        assert diff.generated_by == "system"

    def test_custom_values(self):
        """Test VersionDiff with custom values."""
        generated_time = datetime(2024, 1, 1, tzinfo=UTC)

        diff = VersionDiff(
            from_version_id="v1",
            to_version_id="v2",
            diff_type="metadata",
            added_fields={"new_field": "value"},
            removed_fields={"old_field": "old_value"},
            modified_fields={"changed_field": ("old", "new")},
            total_changes=3,
            similarity_score=0.85,
            generated_at=generated_time,
            generated_by="analyzer",
        )

        assert diff.from_version_id == "v1"
        assert diff.to_version_id == "v2"
        assert diff.diff_type == "metadata"
        assert diff.added_fields == {"new_field": "value"}
        assert diff.removed_fields == {"old_field": "old_value"}
        assert diff.modified_fields == {"changed_field": ("old", "new")}
        assert diff.total_changes == 3
        assert diff.similarity_score == 0.85
        assert diff.generated_at == generated_time
        assert diff.generated_by == "analyzer"


class TestVersionSnapshot:
    """Test VersionSnapshot dataclass."""

    def test_default_values(self):
        """Test VersionSnapshot default values."""
        snapshot = VersionSnapshot()

        # Check that UUID is generated
        assert isinstance(snapshot.snapshot_id, str)
        assert len(snapshot.snapshot_id) == 36  # UUID length

        assert isinstance(snapshot.timestamp, datetime)
        assert snapshot.entities == {}
        assert snapshot.relationships == {}
        assert snapshot.mappings == {}
        assert snapshot.description == ""
        assert snapshot.tags == set()
        assert snapshot.created_by is None
        assert snapshot.entity_count == 0
        assert snapshot.relationship_count == 0
        assert snapshot.mapping_count == 0

    def test_custom_values(self):
        """Test VersionSnapshot with custom values."""
        timestamp = datetime(2024, 1, 1, tzinfo=UTC)

        snapshot = VersionSnapshot(
            snapshot_id="custom-snapshot-id",
            timestamp=timestamp,
            entities={"entity1": {"name": "test"}},
            relationships={"rel1": {"type": "contains"}},
            mappings={"map1": {"source": "test"}},
            description="Test snapshot",
            tags={"test", "milestone"},
            created_by="admin",
            entity_count=1,
            relationship_count=1,
            mapping_count=1,
        )

        assert snapshot.snapshot_id == "custom-snapshot-id"
        assert snapshot.timestamp == timestamp
        assert snapshot.entities == {"entity1": {"name": "test"}}
        assert snapshot.relationships == {"rel1": {"type": "contains"}}
        assert snapshot.mappings == {"map1": {"source": "test"}}
        assert snapshot.description == "Test snapshot"
        assert snapshot.tags == {"test", "milestone"}
        assert snapshot.created_by == "admin"
        assert snapshot.entity_count == 1
        assert snapshot.relationship_count == 1
        assert snapshot.mapping_count == 1


class TestVersionConfig:
    """Test VersionConfig dataclass."""

    def test_default_values(self):
        """Test VersionConfig default values."""
        config = VersionConfig()

        assert config.retention_days == 90
        assert config.max_versions_per_entity == 100
        assert config.enable_auto_cleanup is True
        assert config.cleanup_interval_hours == 24
        assert config.enable_compression is False
        assert config.compression_threshold_days == 30

    def test_custom_values(self):
        """Test VersionConfig with custom values."""
        config = VersionConfig(
            retention_days=365,
            max_versions_per_entity=50,
            enable_auto_cleanup=False,
            cleanup_interval_hours=12,
            enable_compression=True,
            compression_threshold_days=7,
        )

        assert config.retention_days == 365
        assert config.max_versions_per_entity == 50
        assert config.enable_auto_cleanup is False
        assert config.cleanup_interval_hours == 12
        assert config.enable_compression is True
        assert config.compression_threshold_days == 7

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = VersionConfig(
            retention_days=180,
            max_versions_per_entity=75,
            enable_auto_cleanup=True,
            cleanup_interval_hours=6,
            enable_compression=False,
            compression_threshold_days=14,
        )

        result = config.to_dict()

        expected = {
            "retention_days": 180,
            "max_versions_per_entity": 75,
            "enable_auto_cleanup": True,
            "cleanup_interval_hours": 6,
            "enable_compression": False,
            "compression_threshold_days": 14,
        }

        assert result == expected

    def test_from_dict_complete(self):
        """Test creation from dictionary with all fields."""
        data = {
            "retention_days": 120,
            "max_versions_per_entity": 200,
            "enable_auto_cleanup": False,
            "cleanup_interval_hours": 48,
            "enable_compression": True,
            "compression_threshold_days": 60,
        }

        config = VersionConfig.from_dict(data)

        assert config.retention_days == 120
        assert config.max_versions_per_entity == 200
        assert config.enable_auto_cleanup is False
        assert config.cleanup_interval_hours == 48
        assert config.enable_compression is True
        assert config.compression_threshold_days == 60

    def test_from_dict_with_defaults(self):
        """Test creation from dictionary using default values."""
        data = {"retention_days": 45}

        config = VersionConfig.from_dict(data)

        assert config.retention_days == 45
        assert config.max_versions_per_entity == 100  # default
        assert config.enable_auto_cleanup is True  # default
        assert config.cleanup_interval_hours == 24  # default
        assert config.enable_compression is False  # default
        assert config.compression_threshold_days == 30  # default

    def test_from_dict_empty(self):
        """Test creation from empty dictionary."""
        config = VersionConfig.from_dict({})

        assert config.retention_days == 90
        assert config.max_versions_per_entity == 100
        assert config.enable_auto_cleanup is True
        assert config.cleanup_interval_hours == 24
        assert config.enable_compression is False
        assert config.compression_threshold_days == 30


class TestVersionStatistics:
    """Test VersionStatistics dataclass."""

    def test_default_values(self):
        """Test VersionStatistics default values."""
        stats = VersionStatistics()

        assert stats.total_versions == 0
        assert stats.total_entities == 0
        assert stats.average_versions_per_entity == 0.0
        assert stats.max_versions_per_entity == 0
        assert stats.oldest_version is None
        assert stats.newest_version is None
        assert stats.version_types == {}
        assert stats.version_statuses == {}
        assert stats.cache_size == 0
        assert stats.storage_size_bytes == 0

    def test_custom_values(self):
        """Test VersionStatistics with custom values."""
        oldest_time = datetime(2023, 1, 1, tzinfo=UTC)
        newest_time = datetime(2024, 1, 1, tzinfo=UTC)

        stats = VersionStatistics(
            total_versions=1000,
            total_entities=100,
            average_versions_per_entity=10.0,
            max_versions_per_entity=50,
            oldest_version=oldest_time,
            newest_version=newest_time,
            version_types={"document": 500, "entity": 300, "relationship": 200},
            version_statuses={"active": 800, "superseded": 150, "archived": 50},
            cache_size=1024,
            storage_size_bytes=1048576,
        )

        assert stats.total_versions == 1000
        assert stats.total_entities == 100
        assert stats.average_versions_per_entity == 10.0
        assert stats.max_versions_per_entity == 50
        assert stats.oldest_version == oldest_time
        assert stats.newest_version == newest_time
        assert stats.version_types == {
            "document": 500,
            "entity": 300,
            "relationship": 200,
        }
        assert stats.version_statuses == {
            "active": 800,
            "superseded": 150,
            "archived": 50,
        }
        assert stats.cache_size == 1024
        assert stats.storage_size_bytes == 1048576

    def test_to_dict_complete(self):
        """Test conversion to dictionary with all fields."""
        oldest_time = datetime(2023, 6, 1, tzinfo=UTC)
        newest_time = datetime(2024, 6, 1, tzinfo=UTC)

        stats = VersionStatistics(
            total_versions=2000,
            total_entities=200,
            average_versions_per_entity=10.0,
            max_versions_per_entity=100,
            oldest_version=oldest_time,
            newest_version=newest_time,
            version_types={"document": 1000, "entity": 600, "relationship": 400},
            version_statuses={"active": 1500, "superseded": 300, "archived": 200},
            cache_size=2048,
            storage_size_bytes=2097152,
        )

        result = stats.to_dict()

        expected_keys = {
            "total_versions",
            "total_entities",
            "average_versions_per_entity",
            "max_versions_per_entity",
            "oldest_version",
            "newest_version",
            "version_types",
            "version_statuses",
            "cache_size",
            "storage_size_bytes",
        }

        assert set(result.keys()) == expected_keys
        assert result["total_versions"] == 2000
        assert result["total_entities"] == 200
        assert result["average_versions_per_entity"] == 10.0
        assert result["max_versions_per_entity"] == 100
        assert result["oldest_version"] == oldest_time.isoformat()
        assert result["newest_version"] == newest_time.isoformat()
        assert result["version_types"] == {
            "document": 1000,
            "entity": 600,
            "relationship": 400,
        }
        assert result["version_statuses"] == {
            "active": 1500,
            "superseded": 300,
            "archived": 200,
        }
        assert result["cache_size"] == 2048
        assert result["storage_size_bytes"] == 2097152

    def test_to_dict_minimal(self):
        """Test conversion to dictionary with minimal fields."""
        stats = VersionStatistics(total_versions=5, total_entities=1)

        result = stats.to_dict()

        assert result["total_versions"] == 5
        assert result["total_entities"] == 1
        assert result["average_versions_per_entity"] == 0.0
        assert result["max_versions_per_entity"] == 0
        assert result["oldest_version"] is None
        assert result["newest_version"] is None
        assert result["version_types"] == {}
        assert result["version_statuses"] == {}
        assert result["cache_size"] == 0
        assert result["storage_size_bytes"] == 0
