import pytest
from unittest.mock import Mock, patch, MagicMock
from qdrant_loader.embedding_service import EmbeddingService

@pytest.fixture
def mock_openai_client():
    mock_client = MagicMock()
    mock_client.embeddings.create = MagicMock()
    with patch('openai.OpenAI', return_value=mock_client) as mock:
        yield mock_client

@pytest.fixture
def embedding_service(mock_openai_client, test_settings):
    service = EmbeddingService(settings=test_settings)
    service.client = mock_openai_client
    return service

def test_get_embedding(embedding_service, mock_openai_client):
    # Mock the OpenAI response
    mock_embedding = [0.1, 0.2, 0.3]
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=mock_embedding)]
    mock_openai_client.embeddings.create.return_value = mock_response
    
    result = embedding_service.get_embedding("test text")
    
    assert result == mock_embedding
    mock_openai_client.embeddings.create.assert_called_once_with(
        model=embedding_service.model,
        input="test text"
    )

def test_get_embeddings(embedding_service, mock_openai_client):
    # Mock the OpenAI response
    mock_embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=emb) for emb in mock_embeddings]
    mock_openai_client.embeddings.create.return_value = mock_response
    
    texts = ["text1", "text2"]
    result = embedding_service.get_embeddings(texts)
    
    assert result == mock_embeddings
    mock_openai_client.embeddings.create.assert_called_once_with(
        model=embedding_service.model,
        input=texts
    )

def test_count_tokens(embedding_service):
    # Mock the tiktoken encoding
    mock_encoding = Mock()
    mock_encoding.encode.return_value = [1, 2, 3]
    embedding_service.encoding = mock_encoding
    
    result = embedding_service.count_tokens("test text")
    
    assert result == 3
    mock_encoding.encode.assert_called_once_with("test text")

def test_count_tokens_batch(embedding_service):
    # Mock the tiktoken encoding
    mock_encoding = Mock()
    mock_encoding.encode.side_effect = [[1, 2], [3, 4, 5]]
    embedding_service.encoding = mock_encoding
    
    texts = ["text1", "text2"]
    result = embedding_service.count_tokens_batch(texts)
    
    assert result == [2, 3]
    assert mock_encoding.encode.call_count == 2

def test_get_embedding_dimension(embedding_service):
    assert embedding_service.get_embedding_dimension() == 1536 