"""Tests for VersionStorage class.

This module tests the version storage operations including storing,
retrieving, and querying version data in Neo4j.
"""

import json
import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from qdrant_loader.core.versioning import (
    VersionConfig,
    VersionMetadata,
    VersionSnapshot,
    VersionStatistics,
    VersionStatus,
    VersionType,
    VersionOperation,
)
from qdrant_loader.core.versioning.version_storage import VersionStorage


class TestVersionStorage:
    """Test suite for VersionStorage class."""

    def setup_session_mock(
        self, session, result_data=None, single_result=None, data_result=None
    ):
        """Helper method to properly setup session mocks."""
        result = AsyncMock()

        if single_result is not None:
            result.single = AsyncMock(return_value=single_result)

        if data_result is not None:
            result.data = AsyncMock(return_value=data_result)

        session.run = AsyncMock(return_value=result)
        return result

    @pytest.fixture
    def mock_driver(self):
        """Create a mock Neo4j driver for testing."""
        driver = AsyncMock()
        session = AsyncMock()

        # Create a proper async context manager mock
        class MockAsyncContextManager:
            def __init__(self, session):
                self.session = session

            async def __aenter__(self):
                return self.session

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        # Make driver.session() return the async context manager
        driver.session = MagicMock(return_value=MockAsyncContextManager(session))

        return driver, session

    @pytest.fixture
    def version_config(self):
        """Create a version config for testing."""
        return VersionConfig(retention_days=30)

    @pytest.fixture
    def version_storage(self, mock_driver, version_config):
        """Create a VersionStorage instance for testing."""
        driver, _ = mock_driver
        return VersionStorage(driver=driver, config=version_config)

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
            parent_version_id="parent_123",
            supersedes="old_version",
            created_by="user123",
            tags={"test", "important"},
            is_milestone=True,
        )

    @pytest.fixture
    def sample_version_snapshot(self):
        """Sample version snapshot for testing."""
        return VersionSnapshot(
            description="Test snapshot",
            created_by="user123",
            tags={"backup", "test"},
            entities={"entity_1": {"data": "test"}},
            relationships={"rel_1": {"type": "KNOWS"}},
            mappings={"mapping_1": {"id": "test"}},
        )

    def test_init(self, mock_driver, version_config):
        """Test VersionStorage initialization."""
        driver, _ = mock_driver

        storage = VersionStorage(driver=driver, config=version_config)

        assert storage.driver == driver
        assert storage.config == version_config
        assert storage.logger is not None

    @pytest.mark.asyncio
    async def test_store_version_metadata_success(
        self, version_storage, mock_driver, sample_version_metadata
    ):
        """Test successful version metadata storage."""
        _, session = mock_driver

        # Setup mock
        record = {"version_id": sample_version_metadata.version_id}
        self.setup_session_mock(session, single_result=record)

        # Test storage
        success = await version_storage.store_version_metadata(sample_version_metadata)

        # Verify result
        assert success is True

        # Verify session.run was called with correct query and parameters
        session.run.assert_called_once()
        call_args = session.run.call_args
        assert "MERGE (v:Version {version_id: $version_id})" in call_args[0][0]
        # Parameters are passed as the second positional argument
        params = call_args[0][1]
        assert params["version_id"] == sample_version_metadata.version_id
        assert params["parent_version_id"] == sample_version_metadata.parent_version_id
        assert params["supersedes"] == sample_version_metadata.supersedes

    @pytest.mark.asyncio
    async def test_store_version_metadata_no_record(
        self, version_storage, mock_driver, sample_version_metadata
    ):
        """Test version metadata storage when no record is returned."""
        _, session = mock_driver

        # Setup mock to return no record
        result = AsyncMock()
        result.single.return_value = None
        session.run.return_value = result

        # Test storage
        success = await version_storage.store_version_metadata(sample_version_metadata)

        # Verify result
        assert success is False

    @pytest.mark.asyncio
    async def test_store_version_metadata_exception(
        self, version_storage, mock_driver, sample_version_metadata
    ):
        """Test version metadata storage with exception."""
        _, session = mock_driver

        # Setup mock to raise exception
        session.run.side_effect = Exception("Database error")

        # Test storage
        success = await version_storage.store_version_metadata(sample_version_metadata)

        # Verify result
        assert success is False

    @pytest.mark.asyncio
    async def test_get_version_metadata_success(
        self, version_storage, mock_driver, sample_version_metadata
    ):
        """Test successful version metadata retrieval."""
        _, session = mock_driver

        # Setup mock
        result = AsyncMock()
        version_data = sample_version_metadata.to_dict()
        record = {"v": version_data}
        result.single = AsyncMock(return_value=record)
        session.run = AsyncMock(return_value=result)

        # Test retrieval
        metadata = await version_storage.get_version_metadata(
            sample_version_metadata.version_id
        )

        # Verify result
        assert metadata is not None
        assert metadata.version_id == sample_version_metadata.version_id
        assert metadata.entity_id == sample_version_metadata.entity_id

        # Verify query
        session.run.assert_called_once()
        call_args = session.run.call_args
        assert "MATCH (v:Version {version_id: $version_id})" in call_args[0][0]
        # Parameters are passed as the second positional argument
        params = call_args[0][1]
        assert params["version_id"] == sample_version_metadata.version_id

    @pytest.mark.asyncio
    async def test_get_version_metadata_not_found(self, version_storage, mock_driver):
        """Test version metadata retrieval when not found."""
        _, session = mock_driver

        # Setup mock to return no record
        result = AsyncMock()
        result.single.return_value = None
        session.run.return_value = result

        # Test retrieval
        metadata = await version_storage.get_version_metadata("nonexistent")

        # Verify result
        assert metadata is None

    @pytest.mark.asyncio
    async def test_get_version_metadata_exception(self, version_storage, mock_driver):
        """Test version metadata retrieval with exception."""
        _, session = mock_driver

        # Setup mock to raise exception
        session.run.side_effect = Exception("Database error")

        # Test retrieval
        metadata = await version_storage.get_version_metadata("test_id")

        # Verify result
        assert metadata is None

    @pytest.mark.asyncio
    async def test_get_entity_versions_success(
        self, version_storage, mock_driver, sample_version_metadata
    ):
        """Test successful entity versions retrieval."""
        _, session = mock_driver

        # Setup mock
        result = AsyncMock()
        version_data = sample_version_metadata.to_dict()
        records = [{"v": version_data}, {"v": version_data}]
        result.data.return_value = records
        session.run.return_value = result

        # Test retrieval
        versions = await version_storage.get_entity_versions("test_entity")

        # Verify result
        assert len(versions) == 2
        assert all(isinstance(v, VersionMetadata) for v in versions)

        # Verify query
        session.run.assert_called_once()
        call_args = session.run.call_args
        assert "MATCH (v:Version {entity_id: $entity_id})" in call_args[0][0]
        # Parameters are passed as the second positional argument
        params = call_args[0][1]
        assert params["entity_id"] == "test_entity"

    @pytest.mark.asyncio
    async def test_get_entity_versions_with_type_filter(
        self, version_storage, mock_driver
    ):
        """Test entity versions retrieval with version type filter."""
        _, session = mock_driver

        # Setup mock
        result = AsyncMock()
        result.data.return_value = []
        session.run.return_value = result

        # Test retrieval with type filter
        versions = await version_storage.get_entity_versions(
            "test_entity", version_type=VersionType.DOCUMENT
        )

        # Verify result
        assert len(versions) == 0

        # Verify query includes type filter
        session.run.assert_called_once()
        call_args = session.run.call_args
        params = call_args[0][1]
        assert params["version_type"] == VersionType.DOCUMENT.value

    @pytest.mark.asyncio
    async def test_get_entity_versions_with_limit(self, version_storage, mock_driver):
        """Test entity versions retrieval with limit."""
        _, session = mock_driver

        # Setup mock
        result = AsyncMock()
        result.data.return_value = []
        session.run.return_value = result

        # Test retrieval with limit
        versions = await version_storage.get_entity_versions("test_entity", limit=5)

        # Verify result
        assert len(versions) == 0

        # Verify query includes limit
        session.run.assert_called_once()
        call_args = session.run.call_args
        params = call_args[0][1]
        assert params["limit"] == 5

    @pytest.mark.asyncio
    async def test_get_entity_versions_exception(self, version_storage, mock_driver):
        """Test entity versions retrieval with exception."""
        _, session = mock_driver

        # Setup mock to raise exception
        session.run.side_effect = Exception("Database error")

        # Test retrieval
        versions = await version_storage.get_entity_versions("test_entity")

        # Verify result
        assert len(versions) == 0

    @pytest.mark.asyncio
    async def test_get_version_history_success(
        self, version_storage, mock_driver, sample_version_metadata
    ):
        """Test successful version history retrieval."""
        _, session = mock_driver

        # Setup mock
        result = AsyncMock()
        version_data = sample_version_metadata.to_dict()
        records = [{"v": version_data}]
        result.data.return_value = records
        session.run.return_value = result

        # Test retrieval
        history = await version_storage.get_version_history("test_entity")

        # Verify result
        assert len(history) == 1
        assert isinstance(history[0], VersionMetadata)

        # Verify query
        session.run.assert_called_once()
        call_args = session.run.call_args
        assert "MATCH (v:Version {entity_id: $entity_id})" in call_args[0][0]
        assert "ORDER BY v.created_at ASC" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_version_history_with_time_range(
        self, version_storage, mock_driver
    ):
        """Test version history retrieval with time range."""
        _, session = mock_driver

        # Setup mock
        result = AsyncMock()
        result.data.return_value = []
        session.run.return_value = result

        # Test retrieval with time range
        start_time = datetime.now(UTC) - timedelta(days=7)
        end_time = datetime.now(UTC)

        history = await version_storage.get_version_history(
            "test_entity", start_time=start_time, end_time=end_time
        )

        # Verify result
        assert len(history) == 0

        # Verify query includes time filters
        session.run.assert_called_once()
        call_args = session.run.call_args
        params = call_args[0][1]
        assert params["start_time"] == start_time.isoformat()
        assert params["end_time"] == end_time.isoformat()

    @pytest.mark.asyncio
    async def test_get_version_history_exception(self, version_storage, mock_driver):
        """Test version history retrieval with exception."""
        _, session = mock_driver

        # Setup mock to raise exception
        session.run.side_effect = Exception("Database error")

        # Test retrieval
        history = await version_storage.get_version_history("test_entity")

        # Verify result
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_store_version_snapshot_success(
        self, version_storage, mock_driver, sample_version_snapshot
    ):
        """Test successful version snapshot storage."""
        _, session = mock_driver

        # Setup mock
        result = AsyncMock()
        record = {"snapshot_id": sample_version_snapshot.snapshot_id}
        result.single.return_value = record
        session.run.return_value = result

        # Test storage
        success = await version_storage.store_version_snapshot(sample_version_snapshot)

        # Verify result
        assert success is True

        # Verify session.run was called with correct parameters
        session.run.assert_called_once()
        call_args = session.run.call_args
        params = call_args[0][1]
        assert params["snapshot_id"] == sample_version_snapshot.snapshot_id
        assert params["description"] == sample_version_snapshot.description
        assert params["created_by"] == sample_version_snapshot.created_by

    @pytest.mark.asyncio
    async def test_store_version_snapshot_no_record(
        self, version_storage, mock_driver, sample_version_snapshot
    ):
        """Test version snapshot storage when no record is returned."""
        _, session = mock_driver

        # Setup mock to return no record
        result = AsyncMock()
        result.single.return_value = None
        session.run.return_value = result

        # Test storage
        success = await version_storage.store_version_snapshot(sample_version_snapshot)

        # Verify result
        assert success is False

    @pytest.mark.asyncio
    async def test_store_version_snapshot_exception(
        self, version_storage, mock_driver, sample_version_snapshot
    ):
        """Test version snapshot storage with exception."""
        _, session = mock_driver

        # Setup mock to raise exception
        session.run.side_effect = Exception("Database error")

        # Test storage
        success = await version_storage.store_version_snapshot(sample_version_snapshot)

        # Verify result
        assert success is False

    @pytest.mark.asyncio
    async def test_get_version_snapshot_success(
        self, version_storage, mock_driver, sample_version_snapshot
    ):
        """Test successful version snapshot retrieval."""
        _, session = mock_driver

        # Setup mock data
        snapshot_data = {
            "snapshot_id": sample_version_snapshot.snapshot_id,
            "timestamp": sample_version_snapshot.timestamp.isoformat(),
            "description": sample_version_snapshot.description,
            "created_by": sample_version_snapshot.created_by,
            "entity_count": sample_version_snapshot.entity_count,
            "relationship_count": sample_version_snapshot.relationship_count,
            "mapping_count": sample_version_snapshot.mapping_count,
            "entities": json.dumps(sample_version_snapshot.entities),
            "relationships": json.dumps(sample_version_snapshot.relationships),
            "mappings": json.dumps(sample_version_snapshot.mappings),
            "tags": list(sample_version_snapshot.tags),
        }

        # Setup mock
        result = AsyncMock()
        record = {"s": snapshot_data}
        result.single.return_value = record
        session.run.return_value = result

        # Test retrieval
        snapshot = await version_storage.get_version_snapshot(
            sample_version_snapshot.snapshot_id
        )

        # Verify result
        assert snapshot is not None
        assert snapshot.snapshot_id == sample_version_snapshot.snapshot_id
        assert snapshot.description == sample_version_snapshot.description
        assert snapshot.created_by == sample_version_snapshot.created_by

        # Verify query
        session.run.assert_called_once()
        call_args = session.run.call_args
        assert (
            "MATCH (s:VersionSnapshot {snapshot_id: $snapshot_id})" in call_args[0][0]
        )
        params = call_args[0][1]
        assert params["snapshot_id"] == sample_version_snapshot.snapshot_id

    @pytest.mark.asyncio
    async def test_get_version_snapshot_not_found(self, version_storage, mock_driver):
        """Test version snapshot retrieval when not found."""
        _, session = mock_driver

        # Setup mock to return no record
        result = AsyncMock()
        result.single.return_value = None
        session.run.return_value = result

        # Test retrieval
        snapshot = await version_storage.get_version_snapshot("nonexistent")

        # Verify result
        assert snapshot is None

    @pytest.mark.asyncio
    async def test_get_version_snapshot_exception(self, version_storage, mock_driver):
        """Test version snapshot retrieval with exception."""
        _, session = mock_driver

        # Setup mock to raise exception
        session.run.side_effect = Exception("Database error")

        # Test retrieval
        snapshot = await version_storage.get_version_snapshot("test_id")

        # Verify result
        assert snapshot is None

    @pytest.mark.asyncio
    async def test_delete_version_success(self, version_storage, mock_driver):
        """Test successful version deletion."""
        _, session = mock_driver

        # Setup mock
        result = AsyncMock()
        record = {"deleted_count": 1}
        result.single.return_value = record
        session.run.return_value = result

        # Test deletion
        success = await version_storage.delete_version("test_version")

        # Verify result
        assert success is True

        # Verify query
        session.run.assert_called_once()
        call_args = session.run.call_args
        assert "MATCH (v:Version {version_id: $version_id})" in call_args[0][0]
        assert "DETACH DELETE v" in call_args[0][0]
        params = call_args[0][1]
        assert params["version_id"] == "test_version"

    @pytest.mark.asyncio
    async def test_delete_version_not_found(self, version_storage, mock_driver):
        """Test version deletion when version not found."""
        _, session = mock_driver

        # Setup mock to return zero deleted count
        result = AsyncMock()
        record = {"deleted_count": 0}
        result.single.return_value = record
        session.run.return_value = result

        # Test deletion
        success = await version_storage.delete_version("nonexistent")

        # Verify result
        assert success is False

    @pytest.mark.asyncio
    async def test_delete_version_exception(self, version_storage, mock_driver):
        """Test version deletion with exception."""
        _, session = mock_driver

        # Setup mock to raise exception
        session.run.side_effect = Exception("Database error")

        # Test deletion
        success = await version_storage.delete_version("test_version")

        # Verify result
        assert success is False

    @pytest.mark.asyncio
    async def test_cleanup_old_versions_success(self, version_storage, mock_driver):
        """Test successful old versions cleanup."""
        _, session = mock_driver

        # Setup mock
        result = AsyncMock()
        record = {"deleted_count": 5}
        result.single.return_value = record
        session.run.return_value = result

        # Test cleanup
        deleted_count = await version_storage.cleanup_old_versions()

        # Verify result
        assert deleted_count == 5

        # Verify query
        session.run.assert_called_once()
        call_args = session.run.call_args
        assert (
            "WHERE datetime(v.created_at) < datetime($cutoff_date)" in call_args[0][0]
        )
        assert "AND v.status <> 'active'" in call_args[0][0]
        assert "AND NOT v.is_milestone" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_cleanup_old_versions_with_custom_retention(
        self, version_storage, mock_driver
    ):
        """Test old versions cleanup with custom retention days."""
        _, session = mock_driver

        # Setup mock
        result = AsyncMock()
        record = {"deleted_count": 3}
        result.single.return_value = record
        session.run.return_value = result

        # Test cleanup with custom retention
        deleted_count = await version_storage.cleanup_old_versions(retention_days=60)

        # Verify result
        assert deleted_count == 3

        # Verify cutoff date calculation (should be 60 days ago, not the default 30)
        session.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_old_versions_no_records(self, version_storage, mock_driver):
        """Test old versions cleanup when no record is returned."""
        _, session = mock_driver

        # Setup mock to return no record
        result = AsyncMock()
        result.single.return_value = None
        session.run.return_value = result

        # Test cleanup
        deleted_count = await version_storage.cleanup_old_versions()

        # Verify result
        assert deleted_count == 0

    @pytest.mark.asyncio
    async def test_cleanup_old_versions_exception(self, version_storage, mock_driver):
        """Test old versions cleanup with exception."""
        _, session = mock_driver

        # Setup mock to raise exception
        session.run.side_effect = Exception("Database error")

        # Test cleanup
        deleted_count = await version_storage.cleanup_old_versions()

        # Verify result
        assert deleted_count == 0

    @pytest.mark.asyncio
    async def test_get_version_statistics_success(self, version_storage, mock_driver):
        """Test successful version statistics retrieval."""
        _, session = mock_driver

        # Setup mock for main query
        main_result = AsyncMock()
        main_record = {
            "total_versions": 100,
            "total_entities": 50,
            "avg_versions_per_entity": 2.0,
            "max_versions_per_entity": 5,
            "oldest_version": datetime.now(UTC) - timedelta(days=30),
            "newest_version": datetime.now(UTC),
            "version_types": ["document", "entity"],
            "version_statuses": ["active", "superseded"],
        }
        main_result.single.return_value = main_record

        # Setup mock for type counts query
        type_result = AsyncMock()
        type_records = [
            {"type": "document", "count": 60},
            {"type": "entity", "count": 40},
        ]

        async def type_async_iter():
            for record in type_records:
                yield record

        type_result.__aiter__ = lambda *args, **kwargs: type_async_iter()

        # Setup mock for status counts query
        status_result = AsyncMock()
        status_records = [
            {"status": "active", "count": 80},
            {"status": "superseded", "count": 20},
        ]

        async def status_async_iter():
            for record in status_records:
                yield record

        status_result.__aiter__ = lambda *args, **kwargs: status_async_iter()

        # Configure session.run to return different results based on query
        def run_side_effect(query, *args, **kwargs):
            if "v.version_type as type" in query:
                return type_result
            elif "v.status as status" in query:
                return status_result
            else:
                return main_result

        session.run.side_effect = run_side_effect

        # Test statistics retrieval
        stats = await version_storage.get_version_statistics()

        # Verify result
        assert isinstance(stats, VersionStatistics)
        assert stats.total_versions == 100
        assert stats.total_entities == 50
        assert stats.average_versions_per_entity == 2.0
        assert stats.max_versions_per_entity == 5
        assert stats.version_types == {"document": 60, "entity": 40}
        assert stats.version_statuses == {"active": 80, "superseded": 20}

        # Verify all three queries were called
        assert session.run.call_count == 3

    @pytest.mark.asyncio
    async def test_get_version_statistics_no_record(self, version_storage, mock_driver):
        """Test version statistics retrieval when no record is returned."""
        _, session = mock_driver

        # Setup mock to return no record
        result = AsyncMock()
        result.single.return_value = None
        session.run.return_value = result

        # Test statistics retrieval
        stats = await version_storage.get_version_statistics()

        # Verify result is default empty statistics
        assert isinstance(stats, VersionStatistics)
        assert stats.total_versions == 0
        assert stats.total_entities == 0

    @pytest.mark.asyncio
    async def test_get_version_statistics_exception(self, version_storage, mock_driver):
        """Test version statistics retrieval with exception."""
        _, session = mock_driver

        # Setup mock to raise exception
        session.run.side_effect = Exception("Database error")

        # Test statistics retrieval
        stats = await version_storage.get_version_statistics()

        # Verify result is default empty statistics
        assert isinstance(stats, VersionStatistics)
        assert stats.total_versions == 0

    @pytest.mark.asyncio
    async def test_create_indexes_success(self, version_storage, mock_driver):
        """Test successful index creation."""
        _, session = mock_driver

        # Setup mock
        session.run.return_value = AsyncMock()

        # Test index creation
        success = await version_storage.create_indexes()

        # Verify result
        assert success is True

        # Verify multiple index creation queries were called
        assert session.run.call_count == 7  # 7 different indexes

        # Verify some of the index creation queries
        calls = session.run.call_args_list
        index_queries = [call[0][0] for call in calls]

        assert any("version_id_index" in query for query in index_queries)
        assert any("entity_id_index" in query for query in index_queries)
        assert any("snapshot_id_index" in query for query in index_queries)

    @pytest.mark.asyncio
    async def test_create_indexes_exception(self, version_storage, mock_driver):
        """Test index creation with exception."""
        _, session = mock_driver

        # Setup mock to raise exception
        session.run.side_effect = Exception("Database error")

        # Test index creation
        success = await version_storage.create_indexes()

        # Verify result
        assert success is False
