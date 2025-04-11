import pytest
from unittest.mock import patch, MagicMock
from qdrant_loader.core.init_collection import init_collection
from qdrant_loader.config import Settings
from qdrant_loader.core.qdrant_manager import QdrantManager

@pytest.fixture
def mock_settings():
    return Settings(
        QDRANT_URL="http://localhost:6333",  # More realistic test URL
        QDRANT_API_KEY="test-key",
        QDRANT_COLLECTION_NAME="test-collection",
        OPENAI_API_KEY="test-openai-key",
        LOG_LEVEL="INFO",
        global_config={
            "chunking": {
                "size": 500,
                "overlap": 50
            },
            "embedding": {
                "model": "text-embedding-3-small",
                "batch_size": 100
            }
        }
    )

@pytest.fixture
def mock_qdrant_manager():
    manager = MagicMock(spec=QdrantManager)
    # Create a mock client with the required methods
    mock_client = MagicMock()
    mock_client.get_collections.return_value = MagicMock(collections=[])
    # Set the client attribute on the manager
    manager.client = mock_client
    manager.create_collection.return_value = None
    return manager

@pytest.mark.asyncio
async def test_init_collection_success(mock_settings, mock_qdrant_manager):
    """Test successful collection initialization."""
    with patch('qdrant_loader.core.init_collection.get_settings', return_value=mock_settings), \
         patch('qdrant_loader.core.init_collection.QdrantManager', return_value=mock_qdrant_manager), \
         patch('qdrant_loader.core.init_collection.logger') as mock_logger:
        
        await init_collection()
        
        # Verify QdrantManager was called
        mock_qdrant_manager.create_collection.assert_called_once()
        # Verify success log was called
        mock_logger.info.assert_called_once_with("Successfully initialized qDrant collection")

@pytest.mark.asyncio
async def test_init_collection_missing_settings():
    """Test initialization failure due to missing settings."""
    with patch('qdrant_loader.core.init_collection.get_settings', return_value=None), \
         patch('qdrant_loader.core.init_collection.logger') as mock_logger:
        
        with pytest.raises(ValueError, match="Settings not available. Please check your environment variables."):
            await init_collection()
        
        # Verify error was logged
        mock_logger.error.assert_called_once()

@pytest.mark.asyncio
async def test_init_collection_manager_error(mock_settings, mock_qdrant_manager):
    """Test initialization failure due to QdrantManager error."""
    mock_qdrant_manager.create_collection.side_effect = Exception("Test error")
    
    with patch('qdrant_loader.core.init_collection.get_settings', return_value=mock_settings), \
         patch('qdrant_loader.core.init_collection.QdrantManager', return_value=mock_qdrant_manager), \
         patch('qdrant_loader.core.init_collection.logger') as mock_logger:
        
        with pytest.raises(Exception, match="Test error"):
            await init_collection()
        
        # Verify error was logged
        mock_logger.error.assert_called_once() 