import pytest
from unittest.mock import patch, MagicMock
from qdrant_loader.init_collection import init_collection
from qdrant_loader.config import Settings
from qdrant_loader.qdrant_manager import QdrantManager

@pytest.fixture
def mock_settings():
    return Settings(
        QDRANT_URL="http://test-url",
        QDRANT_API_KEY="test-key",
        QDRANT_COLLECTION_NAME="test-collection",
        OPENAI_API_KEY="test-openai-key",
        LOG_LEVEL="INFO"
    )

@pytest.fixture
def mock_qdrant_manager():
    manager = MagicMock(spec=QdrantManager)
    manager.create_collection.return_value = None
    return manager

def test_init_collection_success(mock_settings, mock_qdrant_manager):
    """Test successful collection initialization."""
    with patch('qdrant_loader.init_collection.get_settings', return_value=mock_settings), \
         patch('qdrant_loader.init_collection.QdrantManager', return_value=mock_qdrant_manager), \
         patch('qdrant_loader.init_collection.logger') as mock_logger:
        
        init_collection()
        
        # Verify QdrantManager was called with correct settings
        mock_qdrant_manager.create_collection.assert_called_once_with(vector_size=1536)
        # Verify success log was called
        mock_logger.info.assert_called_once_with("Successfully initialized qDrant collection")

def test_init_collection_missing_settings():
    """Test initialization failure due to missing settings."""
    with patch('qdrant_loader.init_collection.get_settings', return_value=None), \
         patch('qdrant_loader.init_collection.logger') as mock_logger:
        
        with pytest.raises(ValueError, match="Settings not available"):
            init_collection()
        
        # Verify error was logged
        mock_logger.error.assert_called_once()

def test_init_collection_manager_error(mock_settings, mock_qdrant_manager):
    """Test initialization failure due to QdrantManager error."""
    mock_qdrant_manager.create_collection.side_effect = Exception("Test error")
    
    with patch('qdrant_loader.init_collection.get_settings', return_value=mock_settings), \
         patch('qdrant_loader.init_collection.QdrantManager', return_value=mock_qdrant_manager), \
         patch('qdrant_loader.init_collection.logger') as mock_logger:
        
        with pytest.raises(Exception, match="Test error"):
            init_collection()
        
        # Verify error was logged
        mock_logger.error.assert_called_once() 