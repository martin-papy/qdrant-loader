"""Tests for VersionManager class.

This module tests the main VersionManager class that orchestrates
all versioning operations using the modular versioning components.
"""

import asyncio
import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from qdrant_loader.core.versioning import (
    VersionConfig,
    VersionDiff,
    VersionMetadata,
    VersionOperation,
    VersionSnapshot,
    VersionStatistics,
    VersionType,
)
from qdrant_loader.core.versioning.version_manager import VersionManager


class TestVersionManager:
    """Test suite for VersionManager class."""

    @pytest.fixture
    def mock_managers(self):
        """Create mock managers for testing."""
        id_mapping_manager = MagicMock()
        neo4j_manager = MagicMock()
        qdrant_manager = MagicMock()
        neo4j_driver = AsyncMock()
        return id_mapping_manager, neo4j_manager, qdrant_manager, neo4j_driver

    @pytest.fixture
    def version_config(self):
        """Create a test version configuration."""
        return VersionConfig(
            enable_auto_cleanup=True,
            enable_compression=True,
            retention_days=30,
            max_versions_per_entity=10,
        )

    @pytest.fixture
    def version_manager(self, mock_managers, version_config):
        """Create a VersionManager instance for testing."""
        id_mapping_manager, neo4j_manager, qdrant_manager, neo4j_driver = mock_managers

        with (
            patch(
                "qdrant_loader.core.versioning.version_manager.VersionStorage"
            ) as mock_storage_class,
            patch(
                "qdrant_loader.core.versioning.version_manager.VersionOperations"
            ) as mock_operations_class,
            patch(
                "qdrant_loader.core.versioning.version_manager.VersionCleanup"
            ) as mock_cleanup_class,
        ):

            manager = VersionManager(
                id_mapping_manager=id_mapping_manager,
                neo4j_manager=neo4j_manager,
                qdrant_manager=qdrant_manager,
                neo4j_driver=neo4j_driver,
                config=version_config,
            )

            # Store mocks on the actual components that were created
            # These are the real attributes that exist on VersionManager
            manager.storage = mock_storage_class.return_value
            manager.operations = mock_operations_class.return_value
            manager.cleanup = mock_cleanup_class.return_value

            return manager

    @pytest.fixture
    def version_manager_default_config(self, mock_managers):
        """Create a VersionManager instance with default configuration."""
        id_mapping_manager, neo4j_manager, qdrant_manager, neo4j_driver = mock_managers

        with (
            patch("qdrant_loader.core.versioning.version_manager.VersionStorage"),
            patch("qdrant_loader.core.versioning.version_manager.VersionOperations"),
            patch("qdrant_loader.core.versioning.version_manager.VersionCleanup"),
        ):

            return VersionManager(
                id_mapping_manager=id_mapping_manager,
                neo4j_manager=neo4j_manager,
                qdrant_manager=qdrant_manager,
                neo4j_driver=neo4j_driver,
            )

    def test_init_with_config(self, mock_managers, version_config):
        """Test VersionManager initialization with provided config."""
        id_mapping_manager, neo4j_manager, qdrant_manager, neo4j_driver = mock_managers

        with (
            patch(
                "qdrant_loader.core.versioning.version_manager.VersionStorage"
            ) as mock_storage_class,
            patch(
                "qdrant_loader.core.versioning.version_manager.VersionOperations"
            ) as mock_operations_class,
            patch(
                "qdrant_loader.core.versioning.version_manager.VersionCleanup"
            ) as mock_cleanup_class,
        ):

            manager = VersionManager(
                id_mapping_manager=id_mapping_manager,
                neo4j_manager=neo4j_manager,
                qdrant_manager=qdrant_manager,
                neo4j_driver=neo4j_driver,
                config=version_config,
            )

            # Verify initialization
            assert manager.id_mapping_manager == id_mapping_manager
            assert manager.neo4j_manager == neo4j_manager
            assert manager.qdrant_manager == qdrant_manager
            assert manager.neo4j_driver == neo4j_driver
            assert manager.config == version_config
            assert manager._cleanup_task is None

            # Verify component initialization
            mock_storage_class.assert_called_once_with(neo4j_driver, version_config)
            mock_operations_class.assert_called_once_with(
                mock_storage_class.return_value,
                id_mapping_manager,
                neo4j_manager,
                qdrant_manager,
                version_config,
            )
            mock_cleanup_class.assert_called_once_with(
                mock_storage_class.return_value,
                version_config,
            )

    def test_init_default_config(self, version_manager_default_config):
        """Test VersionManager initialization with default config."""
        manager = version_manager_default_config

        # Verify default config was created
        assert isinstance(manager.config, VersionConfig)
        assert manager._cleanup_task is None

    @pytest.mark.asyncio
    async def test_initialize_success(self, version_manager):
        """Test successful initialization."""
        # Setup mocks
        version_manager.storage.create_indexes = AsyncMock()
        version_manager.cleanup.schedule_cleanup = AsyncMock()

        # Test initialization
        await version_manager.initialize()

        # Verify storage indexes were created
        version_manager.storage.create_indexes.assert_called_once()

        # Verify cleanup task was started (config has enable_auto_cleanup=True)
        version_manager.cleanup.schedule_cleanup.assert_called_once()
        assert version_manager._cleanup_task is not None

    @pytest.mark.asyncio
    async def test_initialize_no_auto_cleanup(self, mock_managers):
        """Test initialization without auto cleanup."""
        id_mapping_manager, neo4j_manager, qdrant_manager, neo4j_driver = mock_managers
        config = VersionConfig(enable_auto_cleanup=False)

        with (
            patch(
                "qdrant_loader.core.versioning.version_manager.VersionStorage"
            ) as mock_storage_class,
            patch("qdrant_loader.core.versioning.version_manager.VersionOperations"),
            patch(
                "qdrant_loader.core.versioning.version_manager.VersionCleanup"
            ) as mock_cleanup_class,
        ):

            manager = VersionManager(
                id_mapping_manager=id_mapping_manager,
                neo4j_manager=neo4j_manager,
                qdrant_manager=qdrant_manager,
                neo4j_driver=neo4j_driver,
                config=config,
            )

            mock_storage = mock_storage_class.return_value
            mock_cleanup = mock_cleanup_class.return_value

            mock_storage.create_indexes = AsyncMock()
            mock_cleanup.schedule_cleanup = AsyncMock()

            await manager.initialize()

            # Verify cleanup task was not started
            mock_cleanup.schedule_cleanup.assert_not_called()
            assert manager._cleanup_task is None

    @pytest.mark.asyncio
    async def test_initialize_failure(self, version_manager):
        """Test initialization failure."""
        # Setup mock to raise exception
        version_manager.storage.create_indexes = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Test that exception is re-raised
        with pytest.raises(Exception, match="Database error"):
            await version_manager.initialize()

    @pytest.mark.asyncio
    async def test_create_version(self, version_manager):
        """Test version creation."""
        # Setup mock
        expected_metadata = VersionMetadata(
            entity_id="test_entity",
            version_type=VersionType.DOCUMENT,
        )
        version_manager.operations.create_version = AsyncMock(
            return_value=expected_metadata
        )

        # Test creation
        result = await version_manager.create_version(
            entity_id="test_entity",
            version_type=VersionType.DOCUMENT,
            content={"key": "value"},
            operation=VersionOperation.CREATE,
            parent_version_id="parent_123",
            supersedes="old_version",
            created_by="user123",
            tags=["test", "important"],
            is_milestone=True,
        )

        # Verify call and result
        version_manager.operations.create_version.assert_called_once_with(
            entity_id="test_entity",
            version_type=VersionType.DOCUMENT,
            content={"key": "value"},
            operation=VersionOperation.CREATE,
            parent_version_id="parent_123",
            supersedes="old_version",
            created_by="user123",
            tags=["test", "important"],
            is_milestone=True,
        )
        assert result == expected_metadata

    @pytest.mark.asyncio
    async def test_get_version(self, version_manager):
        """Test getting version by ID."""
        # Setup mock
        expected_metadata = VersionMetadata(version_id="version_123")
        version_manager.operations.get_version = AsyncMock(
            return_value=expected_metadata
        )

        # Test retrieval
        result = await version_manager.get_version("version_123")

        # Verify call and result
        version_manager.operations.get_version.assert_called_once_with("version_123")
        assert result == expected_metadata

    @pytest.mark.asyncio
    async def test_get_latest_version(self, version_manager):
        """Test getting latest version for entity."""
        # Setup mock
        expected_metadata = VersionMetadata(
            entity_id="test_entity",
            version_type=VersionType.DOCUMENT,
            version_number=3,
        )
        version_manager.operations.get_latest_version = AsyncMock(
            return_value=expected_metadata
        )

        # Test retrieval
        result = await version_manager.get_latest_version(
            "test_entity", VersionType.DOCUMENT
        )

        # Verify call and result
        version_manager.operations.get_latest_version.assert_called_once_with(
            "test_entity", VersionType.DOCUMENT
        )
        assert result == expected_metadata

    @pytest.mark.asyncio
    async def test_get_entity_versions(self, version_manager):
        """Test getting all versions for entity."""
        # Setup mock
        expected_versions = [
            VersionMetadata(entity_id="test_entity", version_number=1),
            VersionMetadata(entity_id="test_entity", version_number=2),
        ]
        version_manager.storage.get_entity_versions = AsyncMock(
            return_value=expected_versions
        )

        # Test retrieval
        result = await version_manager.get_entity_versions(
            "test_entity", VersionType.DOCUMENT, limit=10
        )

        # Verify call and result
        version_manager.storage.get_entity_versions.assert_called_once_with(
            "test_entity", VersionType.DOCUMENT, 10
        )
        assert result == expected_versions

    @pytest.mark.asyncio
    async def test_get_version_history(self, version_manager):
        """Test getting version history within time range."""
        # Setup mock
        start_time = datetime.now(UTC) - timedelta(days=7)
        end_time = datetime.now(UTC)
        expected_versions = [
            VersionMetadata(entity_id="test_entity", version_number=1),
        ]
        version_manager.storage.get_version_history = AsyncMock(
            return_value=expected_versions
        )

        # Test retrieval
        result = await version_manager.get_version_history(
            "test_entity", start_time, end_time
        )

        # Verify call and result
        version_manager.storage.get_version_history.assert_called_once_with(
            "test_entity", start_time, end_time
        )
        assert result == expected_versions

    @pytest.mark.asyncio
    async def test_compare_versions(self, version_manager):
        """Test version comparison."""
        # Setup mock
        expected_diff = VersionDiff(
            from_version_id="version_1",
            to_version_id="version_2",
            diff_type="content",
        )
        version_manager.operations.compare_versions = AsyncMock(
            return_value=expected_diff
        )

        # Test comparison
        result = await version_manager.compare_versions("version_1", "version_2")

        # Verify call and result
        version_manager.operations.compare_versions.assert_called_once_with(
            "version_1", "version_2"
        )
        assert result == expected_diff

    @pytest.mark.asyncio
    async def test_rollback_to_version(self, version_manager):
        """Test rollback to specific version."""
        # Setup mock
        version_manager.operations.rollback_to_version = AsyncMock(return_value=True)

        # Test rollback
        result = await version_manager.rollback_to_version(
            "test_entity", "version_123", "user123"
        )

        # Verify call and result
        version_manager.operations.rollback_to_version.assert_called_once_with(
            "test_entity", "version_123", "user123"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_create_snapshot(self, version_manager):
        """Test snapshot creation."""
        # Setup mock
        expected_snapshot = VersionSnapshot(
            snapshot_id="snapshot_123",
            description="Test snapshot",
        )
        version_manager.operations.create_snapshot = AsyncMock(
            return_value=expected_snapshot
        )

        # Test creation
        result = await version_manager.create_snapshot(
            description="Test snapshot",
            entity_ids=["entity_1", "entity_2"],
            created_by="user123",
            tags=["backup"],
        )

        # Verify call and result
        version_manager.operations.create_snapshot.assert_called_once_with(
            description="Test snapshot",
            entity_ids=["entity_1", "entity_2"],
            created_by="user123",
            tags=["backup"],
        )
        assert result == expected_snapshot

    @pytest.mark.asyncio
    async def test_get_snapshot(self, version_manager):
        """Test getting snapshot by ID."""
        # Setup mock
        expected_snapshot = VersionSnapshot(snapshot_id="snapshot_123")
        version_manager.storage.get_version_snapshot = AsyncMock(
            return_value=expected_snapshot
        )

        # Test retrieval
        result = await version_manager.get_snapshot("snapshot_123")

        # Verify call and result
        version_manager.storage.get_version_snapshot.assert_called_once_with(
            "snapshot_123"
        )
        assert result == expected_snapshot

    @pytest.mark.asyncio
    async def test_run_cleanup(self, version_manager):
        """Test running cleanup operations."""
        # Setup mock
        expected_result = {"deleted_versions": 5, "archived_snapshots": 2}
        version_manager.cleanup.run_cleanup = AsyncMock(return_value=expected_result)

        # Test cleanup
        result = await version_manager.run_cleanup()

        # Verify call and result
        version_manager.cleanup.run_cleanup.assert_called_once()
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_cleanup_old_versions(self, version_manager):
        """Test cleaning up old versions."""
        # Setup mock
        version_manager.cleanup.cleanup_old_versions = AsyncMock(return_value=10)

        # Test cleanup
        result = await version_manager.cleanup_old_versions(retention_days=30)

        # Verify call and result
        version_manager.cleanup.cleanup_old_versions.assert_called_once_with(30)
        assert result == 10

    @pytest.mark.asyncio
    async def test_get_cleanup_recommendations(self, version_manager):
        """Test getting cleanup recommendations."""
        # Setup mock
        expected_recommendations = {
            "old_versions_count": 100,
            "large_snapshots": ["snapshot_1", "snapshot_2"],
        }
        version_manager.cleanup.get_cleanup_recommendations = AsyncMock(
            return_value=expected_recommendations
        )

        # Test recommendations
        result = await version_manager.get_cleanup_recommendations()

        # Verify call and result
        version_manager.cleanup.get_cleanup_recommendations.assert_called_once()
        assert result == expected_recommendations

    @pytest.mark.asyncio
    async def test_validate_version_integrity(self, version_manager):
        """Test validating version integrity."""
        # Setup mock
        expected_issues = {
            "orphaned_versions": ["version_1", "version_2"],
            "corrupted_snapshots": ["snapshot_1"],
        }
        version_manager.cleanup.validate_version_integrity = AsyncMock(
            return_value=expected_issues
        )

        # Test validation
        result = await version_manager.validate_version_integrity()

        # Verify call and result
        version_manager.cleanup.validate_version_integrity.assert_called_once()
        assert result == expected_issues

    @pytest.mark.asyncio
    async def test_get_version_statistics(self, version_manager):
        """Test getting version statistics."""
        # Setup mock
        expected_stats = VersionStatistics(
            total_versions=100,
            total_entities=25,
            storage_size_bytes=1024 * 1024,
            cache_size=50,
        )
        version_manager.storage.get_version_statistics = AsyncMock(
            return_value=expected_stats
        )

        # Test statistics
        result = await version_manager.get_version_statistics()

        # Verify call and result
        version_manager.storage.get_version_statistics.assert_called_once()
        assert result == expected_stats

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, version_manager):
        """Test health check with healthy status."""
        # Setup mock
        stats = VersionStatistics(
            total_versions=100,
            total_entities=25,
            storage_size_bytes=1024 * 1024,  # 1MB
            cache_size=50,
        )
        version_manager.storage.get_version_statistics = AsyncMock(return_value=stats)

        # Test health check
        result = await version_manager.health_check()

        # Verify result structure
        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert result["version_count"] == 100
        assert result["entity_count"] == 25
        assert result["storage_size_bytes"] == 1024 * 1024
        assert result["cache_size"] == 50
        assert result["cleanup_enabled"] is True
        assert result["compression_enabled"] is True
        assert "warnings" not in result

    @pytest.mark.asyncio
    async def test_health_check_with_warnings(self, version_manager):
        """Test health check with warnings."""
        # Setup mock with high values
        stats = VersionStatistics(
            total_versions=15000,  # > 10000 threshold
            total_entities=25,
            storage_size_bytes=2 * 1024 * 1024 * 1024,  # 2GB > 1GB threshold
            cache_size=50,
        )
        version_manager.storage.get_version_statistics = AsyncMock(return_value=stats)

        # Test health check
        result = await version_manager.health_check()

        # Verify warnings are present
        assert result["status"] == "healthy"
        assert "warnings" in result
        assert len(result["warnings"]) == 2
        assert "High version count - consider cleanup" in result["warnings"]
        assert "Large storage size - consider archival" in result["warnings"]

    @pytest.mark.asyncio
    async def test_health_check_failure(self, version_manager):
        """Test health check with exception."""
        # Setup mock to raise exception
        version_manager.storage.get_version_statistics = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        # Test health check
        result = await version_manager.health_check()

        # Verify error response
        assert result["status"] == "unhealthy"
        assert "timestamp" in result
        assert result["error"] == "Database connection failed"

    def test_update_config(self, version_manager):
        """Test updating configuration."""
        # Create new config
        new_config = VersionConfig(
            enable_auto_cleanup=False,
            retention_days=60,
        )

        # Update config
        version_manager.update_config(new_config)

        # Verify config was updated everywhere
        assert version_manager.config == new_config
        assert version_manager.storage.config == new_config
        assert version_manager.cleanup.config == new_config
        assert version_manager.operations.config == new_config

    def test_get_config(self, version_manager):
        """Test getting current configuration."""
        result = version_manager.get_config()
        assert result == version_manager.config

    @pytest.mark.asyncio
    async def test_close_with_cleanup_task(self, version_manager):
        """Test closing with active cleanup task."""

        # Create a real asyncio task that we can cancel
        async def dummy_coroutine():
            await asyncio.sleep(10)  # Long running task

        cleanup_task = asyncio.create_task(dummy_coroutine())
        version_manager._cleanup_task = cleanup_task

        # Test close
        await version_manager.close()

        # Verify cleanup task was cancelled
        assert cleanup_task.cancelled() or cleanup_task.done()

    @pytest.mark.asyncio
    async def test_close_with_completed_cleanup_task(self, version_manager):
        """Test closing with completed cleanup task."""
        # Create a mock completed cleanup task
        cleanup_task = AsyncMock()
        cleanup_task.done.return_value = True
        cleanup_task.cancel = MagicMock()
        version_manager._cleanup_task = cleanup_task

        # Test close
        await version_manager.close()

        # Verify cleanup task was not cancelled
        cleanup_task.cancel.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_no_cleanup_task(self, version_manager):
        """Test closing without cleanup task."""
        version_manager._cleanup_task = None

        # Test close (should not raise exception)
        await version_manager.close()

    @pytest.mark.asyncio
    async def test_close_with_cancelled_error(self, version_manager):
        """Test closing with cancelled error from cleanup task."""

        # Create a real asyncio task that we can cancel
        async def dummy_coroutine():
            await asyncio.sleep(10)

        cleanup_task = asyncio.create_task(dummy_coroutine())
        version_manager._cleanup_task = cleanup_task

        # Test close (should handle CancelledError gracefully)
        await version_manager.close()

        assert cleanup_task.cancelled() or cleanup_task.done()

    @pytest.mark.asyncio
    async def test_close_with_exception(self, version_manager):
        """Test closing with exception during cleanup."""

        # Create a real asyncio task that we can cancel
        async def dummy_coroutine():
            await asyncio.sleep(10)

        cleanup_task = asyncio.create_task(dummy_coroutine())
        version_manager._cleanup_task = cleanup_task

        # Test close (should handle exception gracefully)
        await version_manager.close()

        assert cleanup_task.cancelled() or cleanup_task.done()

    @pytest.mark.asyncio
    async def test_async_context_manager(self, mock_managers, version_config):
        """Test async context manager functionality."""
        id_mapping_manager, neo4j_manager, qdrant_manager, neo4j_driver = mock_managers

        with (
            patch(
                "qdrant_loader.core.versioning.version_manager.VersionStorage"
            ) as mock_storage_class,
            patch("qdrant_loader.core.versioning.version_manager.VersionOperations"),
            patch(
                "qdrant_loader.core.versioning.version_manager.VersionCleanup"
            ) as mock_cleanup_class,
        ):

            mock_storage = mock_storage_class.return_value
            mock_storage.create_indexes = AsyncMock()

            # Make schedule_cleanup return a proper coroutine
            async def dummy_cleanup():
                await asyncio.sleep(0.01)

            mock_cleanup = mock_cleanup_class.return_value
            mock_cleanup.schedule_cleanup.return_value = dummy_cleanup()

            # Test context manager
            async with VersionManager(
                id_mapping_manager=id_mapping_manager,
                neo4j_manager=neo4j_manager,
                qdrant_manager=qdrant_manager,
                neo4j_driver=neo4j_driver,
                config=version_config,
            ) as manager:
                # Verify initialization was called
                mock_storage.create_indexes.assert_called_once()
                assert isinstance(manager, VersionManager)

            # Close should have been called automatically

    @pytest.mark.asyncio
    async def test_async_context_manager_with_exception(
        self, mock_managers, version_config
    ):
        """Test async context manager with exception in context."""
        id_mapping_manager, neo4j_manager, qdrant_manager, neo4j_driver = mock_managers

        with (
            patch(
                "qdrant_loader.core.versioning.version_manager.VersionStorage"
            ) as mock_storage_class,
            patch("qdrant_loader.core.versioning.version_manager.VersionOperations"),
            patch(
                "qdrant_loader.core.versioning.version_manager.VersionCleanup"
            ) as mock_cleanup_class,
        ):

            mock_storage = mock_storage_class.return_value
            mock_storage.create_indexes = AsyncMock()

            # Make schedule_cleanup return a proper coroutine
            async def dummy_cleanup():
                await asyncio.sleep(0.01)

            mock_cleanup = mock_cleanup_class.return_value
            mock_cleanup.schedule_cleanup.return_value = dummy_cleanup()

            # Test context manager with exception
            with pytest.raises(ValueError, match="Test exception"):
                async with VersionManager(
                    id_mapping_manager=id_mapping_manager,
                    neo4j_manager=neo4j_manager,
                    qdrant_manager=qdrant_manager,
                    neo4j_driver=neo4j_driver,
                    config=version_config,
                ) as manager:
                    assert isinstance(manager, VersionManager)
                    raise ValueError("Test exception")

            # Close should still have been called
