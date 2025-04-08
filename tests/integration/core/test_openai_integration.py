"""
Tests for the OpenAI integration.
"""
import pytest
from pathlib import Path
from dotenv import load_dotenv
from qdrant_loader.config import Settings
from qdrant_loader.embedding_service import EmbeddingService
import os
import time

# Load test environment variables
load_dotenv(Path(__file__).parent.parent.parent / ".env.test")

@pytest.fixture(scope="session")
def test_settings():
    """Load test settings from environment variables."""
    return Settings(
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
        QDRANT_URL=os.getenv("QDRANT_URL"),
        QDRANT_API_KEY=os.getenv("QDRANT_API_KEY"),
        QDRANT_COLLECTION_NAME=os.getenv("QDRANT_COLLECTION_NAME"),
        LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO")
    )

@pytest.fixture(scope="function")
def embedding_service(test_settings):
    """Create an EmbeddingService instance for testing."""
    service = EmbeddingService(test_settings)
    yield service
    # Add a small delay to respect rate limits
    time.sleep(1)

@pytest.mark.integration
def test_embedding_service_init(test_settings):
    """Test initialization with real settings."""
    service = EmbeddingService(test_settings)
    assert service.settings == test_settings
    assert service.model == "text-embedding-3-small"

@pytest.mark.integration
def test_get_embedding(embedding_service):
    """Test getting a single embedding with real API."""
    text = "This is a test text for embedding generation."
    embedding = embedding_service.get_embedding(text)
    
    assert isinstance(embedding, list)
    assert len(embedding) == 1536  # text-embedding-3-small dimension
    assert all(isinstance(x, float) for x in embedding)

@pytest.mark.integration
def test_get_embeddings(embedding_service):
    """Test getting multiple embeddings with real API."""
    texts = [
        "First test text for embedding generation.",
        "Second test text for embedding generation."
    ]
    embeddings = embedding_service.get_embeddings(texts)
    
    assert isinstance(embeddings, list)
    assert len(embeddings) == 2
    assert all(len(embedding) == 1536 for embedding in embeddings)
    assert all(isinstance(x, float) for embedding in embeddings for x in embedding)

@pytest.mark.integration
def test_count_tokens(embedding_service):
    """Test token counting with real API."""
    text = "This is a test text for token counting."
    token_count = embedding_service.count_tokens(text)
    
    assert isinstance(token_count, int)
    assert token_count > 0

@pytest.mark.integration
def test_count_tokens_batch(embedding_service):
    """Test batch token counting with real API."""
    texts = [
        "First test text for token counting.",
        "Second test text for token counting.",
        "Third test text for token counting."
    ]
    token_counts = embedding_service.count_tokens_batch(texts)
    
    assert isinstance(token_counts, list)
    assert len(token_counts) == 3
    assert all(isinstance(count, int) for count in token_counts)
    assert all(count > 0 for count in token_counts)

@pytest.mark.integration
def test_get_embedding_dimension(embedding_service):
    """Test getting embedding dimension."""
    dimension = embedding_service.get_embedding_dimension()
    assert dimension == 1536  # text-embedding-3-small dimension

@pytest.mark.integration
def test_error_handling(test_settings):
    """Test error handling with invalid API key."""
    invalid_settings = Settings(
        OPENAI_API_KEY="invalid-key",
        QDRANT_URL=test_settings.QDRANT_URL,
        QDRANT_API_KEY=test_settings.QDRANT_API_KEY,
        QDRANT_COLLECTION_NAME=test_settings.QDRANT_COLLECTION_NAME,
        LOG_LEVEL=test_settings.LOG_LEVEL
    )
    
    service = EmbeddingService(invalid_settings)
    with pytest.raises(Exception):
        service.get_embedding("test text")

@pytest.mark.integration
def test_rate_limiting(embedding_service):
    """Test rate limiting handling."""
    texts = ["Test text"] * 10  # Create 10 identical texts
    start_time = time.time()
    
    # Get embeddings for all texts
    embeddings = embedding_service.get_embeddings(texts)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Verify we got all embeddings
    assert len(embeddings) == 10
    # Verify the operation took at least 0.5 seconds (due to rate limiting)
    assert duration >= 0.5 