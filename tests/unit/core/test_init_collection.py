from unittest.mock import patch

import pytest

from qdrant_loader.core.init_collection import init_collection


@pytest.mark.asyncio
async def test_init_collection(test_settings, mock_qdrant_manager):
    """Test collection initialization."""
    with patch(
        "qdrant_loader.core.init_collection.QdrantManager", return_value=mock_qdrant_manager
    ):
        await init_collection(test_settings)

        # Verify the manager's create_collection was called
        mock_qdrant_manager.create_collection.assert_called_once()

        # Verify the client's get_collections was called
        mock_qdrant_manager.client.get_collections.assert_called_once()


@pytest.mark.asyncio
async def test_init_collection_missing_settings():
    """Test initialization failure due to missing settings."""
    with (
        patch("qdrant_loader.core.init_collection.get_settings", return_value=None),
        patch("qdrant_loader.core.init_collection.logger") as mock_logger,
    ):

        with pytest.raises(
            ValueError, match="Settings not available. Please check your environment variables."
        ):
            await init_collection()

        # Verify error was logged
        mock_logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_init_collection_manager_error(test_settings, mock_qdrant_manager):
    """Test initialization failure due to QdrantManager error."""
    mock_qdrant_manager.create_collection.side_effect = Exception("Test error")

    with (
        patch("qdrant_loader.core.init_collection.get_settings", return_value=test_settings),
        patch("qdrant_loader.core.init_collection.QdrantManager", return_value=mock_qdrant_manager),
        patch("qdrant_loader.core.init_collection.logger") as mock_logger,
    ):

        with pytest.raises(Exception, match="Test error"):
            await init_collection()

        # Verify error was logged
        mock_logger.error.assert_called_once()
