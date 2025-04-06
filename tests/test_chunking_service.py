import pytest
from qdrant_loader.config import Config
from qdrant_loader.chunking_service import ChunkingService

@pytest.fixture
def mock_config():
    """Create a mock config for testing."""
    return Config(
        qdrant_url="http://localhost:6333",
        qdrant_api_key="test_key",
        collection_name="test_collection",
        chunk_size=1000,
        chunk_overlap=100,
        openai_api_key="test_key",
        sources=[],
    )

def test_invalid_chunk_size(mock_config):
    """Test that invalid chunk size raises ValueError."""
    mock_config.chunk_size = 0
    with pytest.raises(ValueError, match="Chunk size must be greater than 0"):
        ChunkingService(mock_config)

def test_invalid_chunk_overlap(mock_config):
    """Test that invalid chunk overlap raises ValueError."""
    mock_config.chunk_overlap = -1
    with pytest.raises(ValueError, match="Chunk overlap must be non-negative"):
        ChunkingService(mock_config)

    mock_config.chunk_overlap = 1001
    mock_config.chunk_size = 1000
    with pytest.raises(ValueError, match="Chunk overlap must be less than chunk size"):
        ChunkingService(mock_config) 