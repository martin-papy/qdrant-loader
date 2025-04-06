import pytest
from unittest.mock import Mock, patch, MagicMock
from qdrant_loader.embedding_service import EmbeddingService
from qdrant_loader.config import GlobalConfig

@pytest.fixture
def mock_global_config():
    return GlobalConfig(
        chunking={"size": 500, "overlap": 50},
        embedding={"model": "text-embedding-3-small", "batch_size": 100},
        logging={"level": "INFO", "format": "json", "file": "qdrant-loader.log"}
    )

@pytest.fixture
def mock_openai_client():
    mock_client = MagicMock()
    mock_client.embeddings.create = MagicMock()
    return mock_client

@pytest.fixture
def embedding_service(test_settings, mock_global_config):
    with patch('openai.OpenAI') as mock_openai_class, \
         patch('tiktoken.encoding_for_model') as mock_tiktoken, \
         patch('qdrant_loader.embedding_service.get_global_config', return_value=mock_global_config):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_tiktoken.return_value = MagicMock()
        service = EmbeddingService(settings=test_settings)
        service.client = mock_client
        return service

def test_init_no_settings():
    """Test initialization with no settings provided."""
    with pytest.raises(TypeError, match="missing 1 required positional argument: 'settings'"):
        EmbeddingService()

def test_init_openai_error():
    """Test initialization with OpenAI client error."""
    with patch('qdrant_loader.embedding_service.OpenAI', side_effect=Exception("API Error")), \
         patch('tiktoken.encoding_for_model', return_value=MagicMock()), \
         patch('qdrant_loader.embedding_service.get_global_config', return_value=MagicMock()):
        with pytest.raises(Exception, match="API Error"):
            EmbeddingService(settings=Mock(OPENAI_API_KEY="test"))

def test_get_embedding_error(embedding_service):
    """Test error handling in get_embedding."""
    embedding_service.client.embeddings.create.side_effect = Exception("API Error")
    
    with pytest.raises(Exception, match="API Error"):
        embedding_service.get_embedding("test text")
    
    embedding_service.client.embeddings.create.assert_called_once_with(
        model=embedding_service.model,
        input="test text"
    )

def test_get_embeddings_error(embedding_service):
    """Test error handling in get_embeddings."""
    embedding_service.client.embeddings.create.side_effect = Exception("API Error")
    
    with pytest.raises(Exception, match="API Error"):
        embedding_service.get_embeddings(["text1", "text2"])
    
    embedding_service.client.embeddings.create.assert_called_once_with(
        model=embedding_service.model,
        input=["text1", "text2"]
    )

def test_get_embedding(embedding_service):
    # Mock the OpenAI response
    mock_embedding = [0.1, 0.2, 0.3]
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=mock_embedding)]
    embedding_service.client.embeddings.create.return_value = mock_response
    
    result = embedding_service.get_embedding("test text")
    
    assert result == mock_embedding
    embedding_service.client.embeddings.create.assert_called_once_with(
        model=embedding_service.model,
        input="test text"
    )

def test_get_embeddings(embedding_service):
    # Mock the OpenAI response
    mock_embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=emb) for emb in mock_embeddings]
    embedding_service.client.embeddings.create.return_value = mock_response
    
    texts = ["text1", "text2"]
    result = embedding_service.get_embeddings(texts)
    
    assert result == mock_embeddings
    embedding_service.client.embeddings.create.assert_called_once_with(
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