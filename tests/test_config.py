import os
import pytest
from pathlib import Path
from dotenv import load_dotenv
from qdrant_loader.config import Settings
from pydantic import ValidationError

# Load test environment variables
load_dotenv(Path(__file__).parent / ".env.test")

@pytest.fixture
def test_settings():
    return Settings(
        QDRANT_URL=os.getenv("QDRANT_URL"),
        QDRANT_API_KEY=os.getenv("QDRANT_API_KEY"),
        QDRANT_COLLECTION_NAME=os.getenv("QDRANT_COLLECTION_NAME"),
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
        OPENAI_MODEL=os.getenv("OPENAI_MODEL"),
        LOG_LEVEL=os.getenv("LOG_LEVEL"),
        CHUNK_SIZE=int(os.getenv("CHUNK_SIZE")),
        CHUNK_OVERLAP=int(os.getenv("CHUNK_OVERLAP"))
    )

def test_settings_validation(test_settings):
    """Test that all required settings are present and have correct types."""
    # Test required string fields
    assert isinstance(test_settings.QDRANT_URL, str)
    assert isinstance(test_settings.QDRANT_API_KEY, str)
    assert isinstance(test_settings.QDRANT_COLLECTION_NAME, str)
    assert isinstance(test_settings.OPENAI_API_KEY, str)
    assert isinstance(test_settings.OPENAI_MODEL, str)
    assert isinstance(test_settings.LOG_LEVEL, str)
    
    # Test numeric fields
    assert isinstance(test_settings.CHUNK_SIZE, int)
    assert isinstance(test_settings.CHUNK_OVERLAP, int)
    
    # Test that string fields are not empty
    assert test_settings.QDRANT_URL
    assert test_settings.QDRANT_API_KEY
    assert test_settings.QDRANT_COLLECTION_NAME
    assert test_settings.OPENAI_API_KEY
    assert test_settings.OPENAI_MODEL
    assert test_settings.LOG_LEVEL
    
    # Test that numeric fields are positive
    assert test_settings.CHUNK_SIZE > 0
    assert test_settings.CHUNK_OVERLAP > 0

def test_invalid_log_level():
    """Test that invalid log level raises ValueError."""
    with pytest.raises(ValueError):
        Settings(
            QDRANT_URL=os.getenv("QDRANT_URL"),
            QDRANT_API_KEY=os.getenv("QDRANT_API_KEY"),
            QDRANT_COLLECTION_NAME=os.getenv("QDRANT_COLLECTION_NAME"),
            OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
            LOG_LEVEL="INVALID"
        )

def test_invalid_chunk_size():
    """Test that invalid chunk size raises ValueError."""
    with pytest.raises(ValueError):
        Settings(
            QDRANT_URL=os.getenv("QDRANT_URL"),
            QDRANT_API_KEY=os.getenv("QDRANT_API_KEY"),
            QDRANT_COLLECTION_NAME=os.getenv("QDRANT_COLLECTION_NAME"),
            OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
            CHUNK_SIZE=-1
        )

def test_invalid_chunk_overlap():
    """Test that invalid chunk overlap raises ValueError."""
    with pytest.raises(ValueError):
        Settings(
            QDRANT_URL=os.getenv("QDRANT_URL"),
            QDRANT_API_KEY=os.getenv("QDRANT_API_KEY"),
            QDRANT_COLLECTION_NAME=os.getenv("QDRANT_COLLECTION_NAME"),
            OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
            CHUNK_OVERLAP=-1
        )

def test_missing_required_fields():
    """Test that missing required fields raises ValidationError."""
    with pytest.raises(ValidationError, match="Field is required and cannot be empty"):
        Settings(
            QDRANT_URL="",
            QDRANT_API_KEY="",
            QDRANT_COLLECTION_NAME="",
            OPENAI_API_KEY=""
        ) 