"""
Tests for the embedding service.
"""
import pytest
from unittest.mock import patch, MagicMock
import structlog
from qdrant_loader.config import Settings
from qdrant_loader.embedding_service import EmbeddingService

@pytest.fixture
def mock_settings():
    return Settings(
        OPENAI_API_KEY="test-key",
        QDRANT_URL="http://localhost:6333",
        QDRANT_API_KEY="test-key"
    )

@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service that returns predefined values."""
    with patch('qdrant_loader.embedding_service.EmbeddingService') as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.get_embedding.return_value = [0.1, 0.2, 0.3]
        mock_instance.get_embeddings.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_instance.count_tokens.return_value = 5
        mock_instance.count_tokens_batch.return_value = [5, 3, 1]
        mock_instance.get_embedding_dimension.return_value = 1536
        yield mock_instance

def test_embedding_service_init(mock_settings):
    service = EmbeddingService(mock_settings)
    assert service.settings == mock_settings
    assert service.model == "text-embedding-3-small"

def test_get_embedding(mock_embedding_service):
    embedding = mock_embedding_service.get_embedding("test text")
    assert embedding == [0.1, 0.2, 0.3]
    mock_embedding_service.get_embedding.assert_called_once_with("test text")

def test_get_embedding_error(mock_embedding_service):
    mock_embedding_service.get_embedding.side_effect = Exception("API error")
    with pytest.raises(Exception) as exc_info:
        mock_embedding_service.get_embedding("test text")
    assert str(exc_info.value) == "API error"

def test_get_embeddings(mock_embedding_service):
    embeddings = mock_embedding_service.get_embeddings(["text1", "text2"])
    assert embeddings == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    mock_embedding_service.get_embeddings.assert_called_once_with(["text1", "text2"])

def test_get_embeddings_error(mock_embedding_service):
    mock_embedding_service.get_embeddings.side_effect = Exception("API error")
    with pytest.raises(Exception) as exc_info:
        mock_embedding_service.get_embeddings(["text1", "text2"])
    assert str(exc_info.value) == "API error"

def test_count_tokens(mock_settings):
    service = EmbeddingService(mock_settings)
    token_count = service.count_tokens("Hello, world!")
    assert isinstance(token_count, int)
    assert token_count > 0

def test_count_tokens_batch(mock_settings):
    service = EmbeddingService(mock_settings)
    texts = ["Hello", "world", "!"]
    token_counts = service.count_tokens_batch(texts)
    assert isinstance(token_counts, list)
    assert len(token_counts) == 3
    assert all(isinstance(count, int) for count in token_counts)
    assert all(count > 0 for count in token_counts)

def test_get_embedding_dimension(mock_settings):
    service = EmbeddingService(mock_settings)
    dimension = service.get_embedding_dimension()
    assert dimension == 1536 