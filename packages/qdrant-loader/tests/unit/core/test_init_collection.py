"""Tests for the init_collection module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from qdrant_loader.core.init_collection import init_collection


class TestInitCollection:
    """Test the init_collection function."""

    @pytest.mark.asyncio
    async def test_init_collection_with_settings(self):
        """Test init_collection with provided settings."""
        mock_settings = Mock()
        mock_settings.qdrant_collection_name = "test_collection"

        with (
            patch(
                "qdrant_loader.core.init_collection.QdrantManager"
            ) as mock_manager_class,
            patch("qdrant_loader.core.init_collection.logger") as mock_logger,
        ):
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager

            result = await init_collection(settings=mock_settings, force=False)

            # Verify manager was created with settings
            mock_manager_class.assert_called_once_with(settings=mock_settings)

            # Verify create_collection was called
            mock_manager.create_collection.assert_called_once()

            # Verify delete_collection was NOT called (force=False)
            mock_manager.delete_collection.assert_not_called()

            # Verify logging
            mock_logger.debug.assert_called()

            # Verify return value
            assert result is True

    @pytest.mark.asyncio
    async def test_init_collection_with_force(self):
        """Test init_collection with force=True."""
        mock_settings = Mock()
        mock_settings.qdrant_collection_name = "test_collection"

        with (
            patch(
                "qdrant_loader.core.init_collection.QdrantManager"
            ) as mock_manager_class,
            patch("qdrant_loader.core.init_collection.logger") as mock_logger,
        ):
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager

            result = await init_collection(settings=mock_settings, force=True)

            # Verify manager was created with settings
            mock_manager_class.assert_called_once_with(settings=mock_settings)

            # Verify delete_collection was called first (force=True)
            mock_manager.delete_collection.assert_called_once()

            # Verify create_collection was called
            mock_manager.create_collection.assert_called_once()

            # Verify logging for recreation
            mock_logger.debug.assert_called()

            # Verify return value
            assert result is True

    @pytest.mark.asyncio
    async def test_init_collection_force_delete_error_ignored(self):
        """Test that delete errors are ignored when force=True."""
        mock_settings = Mock()
        mock_settings.qdrant_collection_name = "test_collection"

        with (
            patch(
                "qdrant_loader.core.init_collection.QdrantManager"
            ) as mock_manager_class,
            patch("qdrant_loader.core.init_collection.logger") as mock_logger,
        ):
            mock_manager = Mock()
            mock_manager.delete_collection.side_effect = Exception(
                "Collection doesn't exist"
            )
            mock_manager_class.return_value = mock_manager

            result = await init_collection(settings=mock_settings, force=True)

            # Verify delete_collection was called and failed
            mock_manager.delete_collection.assert_called_once()

            # Verify create_collection was still called despite delete error
            mock_manager.create_collection.assert_called_once()

            # Verify return value
            assert result is True

    @pytest.mark.asyncio
    async def test_init_collection_without_settings(self):
        """Test init_collection without provided settings."""
        with (
            patch(
                "qdrant_loader.core.init_collection.get_settings"
            ) as mock_get_settings,
            patch(
                "qdrant_loader.core.init_collection.QdrantManager"
            ) as mock_manager_class,
            patch("qdrant_loader.core.init_collection.logger") as mock_logger,
        ):
            mock_settings = Mock()
            mock_settings.qdrant_collection_name = "test_collection"
            mock_get_settings.return_value = mock_settings

            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager

            result = await init_collection()

            # Verify get_settings was called
            mock_get_settings.assert_called_once()

            # Verify manager was created with retrieved settings
            mock_manager_class.assert_called_once_with(settings=mock_settings)

            # Verify create_collection was called
            mock_manager.create_collection.assert_called_once()

            # Verify return value
            assert result is True

    @pytest.mark.asyncio
    async def test_init_collection_no_settings_available(self):
        """Test init_collection when no settings are available."""
        with (
            patch(
                "qdrant_loader.core.init_collection.get_settings"
            ) as mock_get_settings,
            patch("qdrant_loader.core.init_collection.logger") as mock_logger,
        ):
            mock_get_settings.return_value = None

            with pytest.raises(ValueError, match="Settings not available"):
                await init_collection()

            # Verify get_settings was called
            mock_get_settings.assert_called_once()

            # Verify error was logged
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_collection_manager_creation_error(self):
        """Test init_collection when QdrantManager creation fails."""
        mock_settings = Mock()

        with (
            patch(
                "qdrant_loader.core.init_collection.QdrantManager"
            ) as mock_manager_class,
            patch("qdrant_loader.core.init_collection.logger") as mock_logger,
        ):
            mock_manager_class.side_effect = Exception("Failed to create manager")

            with pytest.raises(Exception, match="Failed to create manager"):
                await init_collection(settings=mock_settings)

            # Verify error was logged
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_collection_create_collection_error(self):
        """Test init_collection when create_collection fails."""
        mock_settings = Mock()
        mock_settings.qdrant_collection_name = "test_collection"

        with (
            patch(
                "qdrant_loader.core.init_collection.QdrantManager"
            ) as mock_manager_class,
            patch("qdrant_loader.core.init_collection.logger") as mock_logger,
        ):
            mock_manager = Mock()
            mock_manager.create_collection.side_effect = Exception(
                "Failed to create collection"
            )
            mock_manager_class.return_value = mock_manager

            with pytest.raises(Exception, match="Failed to create collection"):
                await init_collection(settings=mock_settings)

            # Verify error was logged
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_collection_logging_calls(self):
        """Test that proper logging calls are made."""
        mock_settings = Mock()
        mock_settings.qdrant_collection_name = "test_collection"

        with (
            patch(
                "qdrant_loader.core.init_collection.QdrantManager"
            ) as mock_manager_class,
            patch("qdrant_loader.core.init_collection.logger") as mock_logger,
        ):
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager

            await init_collection(settings=mock_settings, force=False)

            # Check that debug logging was called for initialization
            debug_calls = mock_logger.debug.call_args_list
            assert len(debug_calls) >= 2  # At least initialization and completion

            # Check specific log messages
            log_messages = [call[0][0] for call in debug_calls]
            assert "Initializing collection" in log_messages
            assert "Collection initialization completed" in log_messages

    @pytest.mark.asyncio
    async def test_init_collection_force_logging(self):
        """Test logging when force=True."""
        mock_settings = Mock()
        mock_settings.qdrant_collection_name = "test_collection"

        with (
            patch(
                "qdrant_loader.core.init_collection.QdrantManager"
            ) as mock_manager_class,
            patch("qdrant_loader.core.init_collection.logger") as mock_logger,
        ):
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager

            await init_collection(settings=mock_settings, force=True)

            # Check that debug logging was called for recreation
            debug_calls = mock_logger.debug.call_args_list
            log_messages = [call[0][0] for call in debug_calls]
            assert "Recreating collection" in log_messages

    @pytest.mark.asyncio
    async def test_init_collection_settings_validation(self):
        """Test that settings are properly validated."""
        # Test with None settings and no global settings
        with (
            patch(
                "qdrant_loader.core.init_collection.get_settings"
            ) as mock_get_settings,
            patch("qdrant_loader.core.init_collection.logger") as mock_logger,
        ):
            mock_get_settings.return_value = None

            with pytest.raises(ValueError) as exc_info:
                await init_collection(settings=None)

            assert "Settings not available" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_collection_return_value(self):
        """Test that init_collection returns True on success."""
        mock_settings = Mock()
        mock_settings.qdrant_collection_name = "test_collection"

        with (
            patch(
                "qdrant_loader.core.init_collection.QdrantManager"
            ) as mock_manager_class,
        ):
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager

            result = await init_collection(settings=mock_settings)

            assert result is True
            assert isinstance(result, bool)
