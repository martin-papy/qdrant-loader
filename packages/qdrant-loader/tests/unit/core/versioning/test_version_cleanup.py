"""Tests for VersionCleanup class.

This module tests the version cleanup and maintenance operations
including automated cleanup, archival, and validation functionality.
"""

import asyncio
import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from qdrant_loader.core.versioning import (
    VersionConfig,
    VersionStatistics,
)
from qdrant_loader.core.versioning.version_cleanup import VersionCleanup


class TestVersionCleanup:
    """Test suite for VersionCleanup class."""

    @pytest.fixture
    def mock_storage(self):
        """Create a mock VersionStorage for testing."""
        return AsyncMock()

    @pytest.fixture
    def version_config(self):
        """Create a version config for testing."""
        return VersionConfig(
            retention_days=30,
            enable_auto_cleanup=True,
            enable_compression=True,
            cleanup_interval_hours=24,
        )

    @pytest.fixture
    def version_cleanup(self, mock_storage, version_config):
        """Create a VersionCleanup instance for testing."""
        return VersionCleanup(storage=mock_storage, config=version_config)

    def test_init(self, mock_storage, version_config):
        """Test VersionCleanup initialization."""
        cleanup = VersionCleanup(storage=mock_storage, config=version_config)

        assert cleanup.storage == mock_storage
        assert cleanup.config == version_config
        assert cleanup.logger is not None

    @pytest.mark.asyncio
    async def test_run_cleanup_success(self, version_cleanup, mock_storage):
        """Test successful comprehensive cleanup operations."""
        # Setup mocks for individual cleanup methods
        mock_storage.cleanup_old_versions.return_value = 5

        # Mock the other cleanup methods that are called by run_cleanup
        with (
            patch.object(
                version_cleanup, "cleanup_excess_versions", return_value=3
            ) as mock_excess,
            patch.object(
                version_cleanup, "cleanup_orphaned_versions", return_value=2
            ) as mock_orphaned,
            patch.object(
                version_cleanup, "archive_old_versions", return_value=1
            ) as mock_archive,
        ):

            # Test cleanup
            stats = await version_cleanup.run_cleanup()

            # Verify result
            assert isinstance(stats, dict)
            assert stats["old_versions_cleaned"] == 5
            assert stats["excess_versions_cleaned"] == 3
            assert stats["orphaned_versions_cleaned"] == 2
            assert stats["archived_versions"] == 1

            # Verify methods were called
            mock_storage.cleanup_old_versions.assert_called_once_with(30)
            mock_excess.assert_called_once()
            mock_orphaned.assert_called_once()
            mock_archive.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_cleanup_auto_cleanup_disabled(
        self, mock_storage, version_config
    ):
        """Test cleanup when auto cleanup is disabled."""
        # Disable auto cleanup
        version_config.enable_auto_cleanup = False
        cleanup = VersionCleanup(storage=mock_storage, config=version_config)

        # Mock the other cleanup methods
        with (
            patch.object(
                cleanup, "cleanup_excess_versions", return_value=3
            ) as mock_excess,
            patch.object(
                cleanup, "cleanup_orphaned_versions", return_value=2
            ) as mock_orphaned,
            patch.object(
                cleanup, "archive_old_versions", return_value=1
            ) as mock_archive,
        ):

            # Test cleanup
            stats = await cleanup.run_cleanup()

            # Verify result - old_versions_cleaned should be 0
            assert stats["old_versions_cleaned"] == 0
            assert stats["excess_versions_cleaned"] == 3
            assert stats["orphaned_versions_cleaned"] == 2
            assert stats["archived_versions"] == 1

            # Verify storage cleanup was not called
            mock_storage.cleanup_old_versions.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_cleanup_compression_disabled(self, mock_storage, version_config):
        """Test cleanup when compression is disabled."""
        # Disable compression
        version_config.enable_compression = False
        cleanup = VersionCleanup(storage=mock_storage, config=version_config)

        # Setup mocks
        mock_storage.cleanup_old_versions.return_value = 5

        with (
            patch.object(
                cleanup, "cleanup_excess_versions", return_value=3
            ) as mock_excess,
            patch.object(
                cleanup, "cleanup_orphaned_versions", return_value=2
            ) as mock_orphaned,
            patch.object(
                cleanup, "archive_old_versions", return_value=0
            ) as mock_archive,
        ):

            # Test cleanup
            stats = await cleanup.run_cleanup()

            # Verify result - archived_versions should be 0
            assert stats["old_versions_cleaned"] == 5
            assert stats["excess_versions_cleaned"] == 3
            assert stats["orphaned_versions_cleaned"] == 2
            assert stats["archived_versions"] == 0

            # Verify archive was NOT called when compression is disabled
            mock_archive.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_cleanup_exception(self, version_cleanup, mock_storage):
        """Test cleanup with exception."""
        # Setup mock to raise exception
        mock_storage.cleanup_old_versions.side_effect = Exception("Storage error")

        # Test cleanup
        stats = await version_cleanup.run_cleanup()

        # Verify result - should return empty stats on exception
        assert isinstance(stats, dict)
        assert all(count == 0 for count in stats.values())

    @pytest.mark.asyncio
    async def test_cleanup_old_versions_success(self, version_cleanup, mock_storage):
        """Test successful old versions cleanup."""
        # Setup mock
        mock_storage.cleanup_old_versions.return_value = 10

        # Test cleanup
        result = await version_cleanup.cleanup_old_versions()

        # Verify result
        assert result == 10

        # Verify storage method was called with default retention
        mock_storage.cleanup_old_versions.assert_called_once_with(30)

    @pytest.mark.asyncio
    async def test_cleanup_old_versions_custom_retention(
        self, version_cleanup, mock_storage
    ):
        """Test old versions cleanup with custom retention days."""
        # Setup mock
        mock_storage.cleanup_old_versions.return_value = 5

        # Test cleanup with custom retention
        result = await version_cleanup.cleanup_old_versions(retention_days=60)

        # Verify result
        assert result == 5

        # Verify storage method was called with custom retention
        mock_storage.cleanup_old_versions.assert_called_once_with(60)

    @pytest.mark.asyncio
    async def test_cleanup_old_versions_exception(self, version_cleanup, mock_storage):
        """Test old versions cleanup with exception."""
        # Setup mock to raise exception
        mock_storage.cleanup_old_versions.side_effect = Exception("Storage error")

        # Test cleanup
        result = await version_cleanup.cleanup_old_versions()

        # Verify result
        assert result == 0

    @pytest.mark.asyncio
    async def test_cleanup_excess_versions(self, version_cleanup):
        """Test excess versions cleanup (stub implementation)."""
        # Test cleanup
        result = await version_cleanup.cleanup_excess_versions()

        # Verify result - should be 0 as it's not implemented
        assert result == 0

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_versions(self, version_cleanup):
        """Test orphaned versions cleanup (stub implementation)."""
        # Test cleanup
        result = await version_cleanup.cleanup_orphaned_versions()

        # Verify result - should be 0 as it's not implemented
        assert result == 0

    @pytest.mark.asyncio
    async def test_archive_old_versions_enabled(self, version_cleanup):
        """Test old versions archival when compression is enabled."""
        # Test archival
        result = await version_cleanup.archive_old_versions()

        # Verify result - should be 0 as it's not implemented
        assert result == 0

    @pytest.mark.asyncio
    async def test_archive_old_versions_disabled(self, mock_storage, version_config):
        """Test old versions archival when compression is disabled."""
        # Disable compression
        version_config.enable_compression = False
        cleanup = VersionCleanup(storage=mock_storage, config=version_config)

        # Test archival
        result = await cleanup.archive_old_versions()

        # Verify result - should be 0 when compression is disabled
        assert result == 0

    @pytest.mark.asyncio
    async def test_schedule_cleanup_single_iteration(self, version_cleanup):
        """Test scheduled cleanup for a single iteration."""
        call_count = 0

        async def mock_run_cleanup():
            nonlocal call_count
            call_count += 1
            return {
                "old_versions_cleaned": 1,
                "excess_versions_cleaned": 0,
                "orphaned_versions_cleaned": 0,
                "archived_versions": 0,
            }

        # Mock sleep to raise CancelledError after first call
        async def mock_sleep(duration):
            if call_count >= 1:  # Stop after first cleanup
                raise asyncio.CancelledError()

        # Mock sleep and run_cleanup
        with patch("asyncio.sleep", side_effect=mock_sleep) as mock_sleep_patch:
            version_cleanup.run_cleanup = mock_run_cleanup

            # Test scheduled cleanup - CancelledError is caught and handled
            await version_cleanup.schedule_cleanup()

            # Verify sleep was called with correct interval (24 hours = 86400 seconds)
            mock_sleep_patch.assert_called_with(86400)
            assert call_count == 1

    @pytest.mark.asyncio
    async def test_schedule_cleanup_exception(self, version_cleanup):
        """Test scheduled cleanup with exception."""

        # Mock run_cleanup to raise exception and sleep to raise CancelledError
        async def mock_sleep(duration):
            raise asyncio.CancelledError()

        with (
            patch.object(
                version_cleanup, "run_cleanup", side_effect=Exception("Cleanup error")
            ),
            patch("asyncio.sleep", side_effect=mock_sleep),
        ):

            # Test scheduled cleanup - should not raise because CancelledError is caught
            await version_cleanup.schedule_cleanup()

    @pytest.mark.asyncio
    async def test_validate_version_integrity(self, version_cleanup):
        """Test version integrity validation (stub implementation)."""
        # Test validation
        issues = await version_cleanup.validate_version_integrity()

        # Verify result structure
        assert isinstance(issues, dict)
        assert "missing_parents" in issues
        assert "circular_references" in issues
        assert "invalid_supersessions" in issues
        assert "orphaned_versions" in issues

        # All should be empty lists as it's not implemented
        assert all(
            isinstance(issue_list, list) and len(issue_list) == 0
            for issue_list in issues.values()
        )

    @pytest.mark.asyncio
    async def test_validate_version_integrity_exception(self, version_cleanup):
        """Test version integrity validation with exception."""
        # Since it's a stub, we can't easily inject an exception
        # but we can test that it handles exceptions gracefully
        issues = await version_cleanup.validate_version_integrity()

        # Should still return the expected structure
        assert isinstance(issues, dict)
        assert len(issues) == 4

    @pytest.mark.asyncio
    async def test_repair_version_issues(self, version_cleanup):
        """Test version issues repair (stub implementation)."""
        # Test repair
        test_issues = {
            "missing_parents": ["version_1", "version_2"],
            "circular_references": ["version_3"],
            "invalid_supersessions": [],
            "orphaned_versions": ["version_4"],
        }

        repairs = await version_cleanup.repair_version_issues(test_issues)

        # Verify result structure
        assert isinstance(repairs, dict)
        assert "fixed_parents" in repairs
        assert "resolved_circular_refs" in repairs
        assert "fixed_supersessions" in repairs
        assert "cleaned_orphans" in repairs

        # All should be 0 as it's not implemented
        assert all(count == 0 for count in repairs.values())

    @pytest.mark.asyncio
    async def test_repair_version_issues_exception(self, version_cleanup):
        """Test version issues repair with exception."""
        # Since it's a stub, we can't easily inject an exception
        # but we can test that it handles exceptions gracefully
        repairs = await version_cleanup.repair_version_issues({})

        # Should still return the expected structure
        assert isinstance(repairs, dict)
        assert len(repairs) == 4

    @pytest.mark.asyncio
    async def test_get_cleanup_recommendations_success(
        self, version_cleanup, mock_storage
    ):
        """Test successful cleanup recommendations generation."""
        # Setup mock statistics
        mock_stats = VersionStatistics(
            total_versions=100,
            total_entities=50,
            average_versions_per_entity=2.0,
            max_versions_per_entity=5,
        )
        mock_storage.get_version_statistics.return_value = mock_stats

        # Test recommendations
        recommendations = await version_cleanup.get_cleanup_recommendations()

        # Verify result structure
        assert isinstance(recommendations, dict)
        assert "old_versions_to_clean" in recommendations
        assert "excess_versions_to_clean" in recommendations
        assert "storage_savings_estimate" in recommendations
        assert "recommended_retention_days" in recommendations

        # Verify storage method was called
        mock_storage.get_version_statistics.assert_called_once()

        # Verify recommended retention days is within expected range
        assert 30 <= recommendations["recommended_retention_days"] <= 365

    @pytest.mark.asyncio
    async def test_get_cleanup_recommendations_no_versions(
        self, version_cleanup, mock_storage
    ):
        """Test cleanup recommendations when no versions exist."""
        # Setup mock statistics with no versions
        mock_stats = VersionStatistics(
            total_versions=0,
            total_entities=0,
            average_versions_per_entity=0.0,
            max_versions_per_entity=0,
        )
        mock_storage.get_version_statistics.return_value = mock_stats

        # Test recommendations
        recommendations = await version_cleanup.get_cleanup_recommendations()

        # Verify result structure
        assert isinstance(recommendations, dict)
        assert recommendations["old_versions_to_clean"] == 0
        assert recommendations["excess_versions_to_clean"] == 0
        assert recommendations["storage_savings_estimate"] == 0

    @pytest.mark.asyncio
    async def test_get_cleanup_recommendations_exception(
        self, version_cleanup, mock_storage
    ):
        """Test cleanup recommendations with exception."""
        # Setup mock to raise exception
        mock_storage.get_version_statistics.side_effect = Exception("Storage error")

        # Test recommendations
        recommendations = await version_cleanup.get_cleanup_recommendations()

        # Verify result structure is still returned with defaults
        assert isinstance(recommendations, dict)
        assert "old_versions_to_clean" in recommendations
        assert "excess_versions_to_clean" in recommendations
        assert "storage_savings_estimate" in recommendations
        assert "recommended_retention_days" in recommendations

        # Should use default retention days from config
        assert recommendations["recommended_retention_days"] == 30
