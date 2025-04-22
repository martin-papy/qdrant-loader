"""Unit tests for the embedding service."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import tiktoken
from openai.types.create_embedding_response import CreateEmbeddingResponse
from qdrant_loader.config import Settings
from qdrant_loader.core.document import Document
from qdrant_loader.core.embedding.embedding_service import EmbeddingService
import openai


@pytest.fixture
def mock_openai():
    """Mock OpenAI client."""
    with patch("qdrant_loader.core.embedding.embedding_service.OpenAI") as mock:
        yield mock


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    # Create mock for global config
    global_config = MagicMock()

    # Create mock for embedding config
    embedding_config = MagicMock()
    embedding_config.endpoint = "https://api.openai.com/v1"
    embedding_config.model = "text-embedding-3-small"
    embedding_config.tokenizer = "cl100k_base"
    embedding_config.batch_size = 10
    embedding_config.vector_size = 1536

    # Attach embedding config to global config
    global_config.embedding = embedding_config

    # Create main settings mock
    settings = MagicMock(spec=Settings)
    settings.OPENAI_API_KEY = "test-key"
    settings.global_config = global_config

    return settings


@pytest.fixture
def mock_local_settings():
    """Create mock settings for local service testing."""
    # Create mock for global config
    global_config = MagicMock()

    # Create mock for embedding config
    embedding_config = MagicMock()
    embedding_config.endpoint = "http://localhost:8000"
    embedding_config.model = "local-model"
    embedding_config.tokenizer = "none"
    embedding_config.batch_size = 10
    embedding_config.vector_size = 768

    # Attach embedding config to global config
    global_config.embedding = embedding_config

    # Create main settings mock
    settings = MagicMock(spec=Settings)
    settings.global_config = global_config

    return settings


@pytest.fixture
def mock_openai_response():
    """Create mock OpenAI API response."""
    response = MagicMock(spec=CreateEmbeddingResponse)
    response.data = [MagicMock(embedding=[0.1] * 1536)]
    return response


@pytest.fixture
def mock_local_response():
    """Create mock local service response."""
    return {"data": [{"embedding": [0.2] * 768}]}


def test_init_openai(mock_openai, mock_settings):
    """Test initialization with OpenAI configuration."""
    # Create mock client
    mock_client = MagicMock()
    mock_openai.return_value = mock_client

    # Create the service
    service = EmbeddingService(mock_settings)

    # Verify OpenAI client initialization
    assert service.use_openai is True
    assert service.client is not None
    mock_openai.assert_called_once_with(api_key="test-key", base_url="https://api.openai.com/v1")


def test_init_local():
    """Test initialization with local service configuration."""
    # Create proper mock settings structure
    global_config = MagicMock()
    embedding_config = MagicMock()
    embedding_config.endpoint = "http://localhost:8000"
    embedding_config.tokenizer = "none"
    global_config.embedding = embedding_config

    settings = MagicMock(spec=Settings)
    settings.global_config = global_config

    service = EmbeddingService(settings)

    assert service.use_openai is False
    assert service.client is None
    assert service.encoding is None


def test_init_tokenizer():
    """Test tokenizer initialization."""
    with patch("tiktoken.get_encoding") as mock_get_encoding:
        # Create proper mock settings structure
        global_config = MagicMock()
        embedding_config = MagicMock()
        embedding_config.tokenizer = "cl100k_base"
        global_config.embedding = embedding_config

        settings = MagicMock(spec=Settings)
        settings.global_config = global_config

        EmbeddingService(settings)

        mock_get_encoding.assert_called_once_with("cl100k_base")


def test_init_tokenizer_fallback():
    """Test tokenizer initialization fallback on error."""
    with patch("tiktoken.get_encoding", side_effect=Exception("Test error")):
        # Create proper mock settings structure
        global_config = MagicMock()
        embedding_config = MagicMock()
        embedding_config.tokenizer = "invalid_tokenizer"
        global_config.embedding = embedding_config

        settings = MagicMock(spec=Settings)
        settings.global_config = global_config

        service = EmbeddingService(settings)

        assert service.encoding is None


@pytest.mark.asyncio
async def test_get_embedding_openai(mock_openai, mock_settings, mock_openai_response):
    """Test getting single embedding from OpenAI."""
    # Setup mock client
    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = mock_openai_response
    mock_openai.return_value = mock_client

    # Create service and get embedding
    service = EmbeddingService(mock_settings)
    embedding = await service.get_embedding("test text")

    # Verify results
    assert len(embedding) == 1536
    mock_client.embeddings.create.assert_called_once_with(
        model="text-embedding-3-small", input=["test text"]
    )


@pytest.mark.asyncio
async def test_get_embedding_local(mock_local_settings, mock_local_response):
    """Test getting single embedding from local service."""
    with patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = mock_local_response
        mock_post.return_value.raise_for_status = MagicMock()

        service = EmbeddingService(mock_local_settings)
        embedding = await service.get_embedding("test text")

        assert len(embedding) == 768
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_get_embeddings_batch(mock_openai, mock_settings):
    """Test batch embedding generation."""
    # Setup mock client with multiple responses
    mock_client = MagicMock()
    mock_response = MagicMock(spec=CreateEmbeddingResponse)
    mock_response.data = [
        MagicMock(embedding=[0.1] * 1536),
        MagicMock(embedding=[0.2] * 1536),
    ]
    mock_client.embeddings.create.return_value = mock_response
    mock_openai.return_value = mock_client

    service = EmbeddingService(mock_settings)
    documents = [
        Document(
            title="Test 1",
            content="Test content 1",
            source_type="test",
            source="test_source",
            url="http://test.com/1",
            metadata={},
        ),
        Document(
            title="Test 2",
            content="Test content 2",
            source_type="test",
            source="test_source",
            url="http://test.com/2",
            metadata={},
        ),
    ]
    embeddings = await service.get_embeddings(documents)

    # Verify results
    assert len(embeddings) == 2
    assert all(len(emb) == 1536 for emb in embeddings)
    mock_client.embeddings.create.assert_called_once_with(
        model="text-embedding-3-small",
        input=["Test content 1", "Test content 2"],
    )


@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting between requests."""
    # Create proper mock settings structure
    global_config = MagicMock()
    embedding_config = MagicMock()
    embedding_config.endpoint = "http://localhost:8000"
    global_config.embedding = embedding_config

    settings = MagicMock(spec=Settings)
    settings.global_config = global_config

    service = EmbeddingService(settings)

    start_time = asyncio.get_event_loop().time()
    await service._apply_rate_limit()
    await service._apply_rate_limit()
    end_time = asyncio.get_event_loop().time()

    assert end_time - start_time >= 0.5  # Minimum interval is 500ms


def test_count_tokens_with_tokenizer(mock_settings):
    """Test token counting with tiktoken."""
    with patch("tiktoken.get_encoding") as mock_get_encoding:
        mock_encoding = MagicMock()
        mock_encoding.encode.return_value = [1, 2, 3]  # 3 tokens
        mock_get_encoding.return_value = mock_encoding

        service = EmbeddingService(mock_settings)
        count = service.count_tokens("test text")

        assert count == 3
        mock_encoding.encode.assert_called_once_with("test text")


def test_count_tokens_fallback(mock_local_settings):
    """Test token counting fallback to character count."""
    service = EmbeddingService(mock_local_settings)
    count = service.count_tokens("test")

    assert count == 4  # Length of "test"


def test_count_tokens_batch(mock_settings):
    """Test batch token counting."""
    with patch("tiktoken.get_encoding") as mock_get_encoding:
        mock_encoding = MagicMock()
        mock_encoding.encode.side_effect = lambda x: [1] * len(x)
        mock_get_encoding.return_value = mock_encoding

        service = EmbeddingService(mock_settings)
        counts = service.count_tokens_batch(["test", "longer text"])

        assert counts == [4, 11]


def test_get_embedding_dimension(mock_settings):
    """Test getting embedding dimension."""
    service = EmbeddingService(mock_settings)
    dimension = service.get_embedding_dimension()

    assert dimension == 1536


@pytest.mark.asyncio
async def test_error_handling_openai(mock_openai, mock_settings):
    """Test error handling for OpenAI API errors."""
    # Setup mock client with custom error
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = '{"error": {"message": "Incorrect API key provided"}}'
    mock_client.embeddings.create.side_effect = openai.AuthenticationError(
        message="Incorrect API key provided",
        response=mock_response,
        body={"error": {"message": "Incorrect API key provided"}},
    )
    mock_openai.return_value = mock_client

    service = EmbeddingService(mock_settings)
    with pytest.raises(openai.AuthenticationError, match="Incorrect API key provided"):
        await service.get_embedding("test text")


@pytest.mark.asyncio
async def test_error_handling_local(mock_local_settings):
    """Test error handling for local service errors."""
    with patch("requests.post") as mock_post:
        mock_post.side_effect = Exception("Connection Error")

        service = EmbeddingService(mock_local_settings)
        with pytest.raises(Exception, match="Connection Error"):
            await service.get_embedding("test text")
