import os
import pytest
from pathlib import Path
from dotenv import load_dotenv
from qdrant_loader.config import Settings

# Load test environment variables
load_dotenv(Path(__file__).parent / ".env.test")

@pytest.fixture
def test_settings():
    """Fixture that provides test settings for all tests."""
    return Settings(
        QDRANT_URL=os.getenv("QDRANT_URL"),
        QDRANT_API_KEY=os.getenv("QDRANT_API_KEY"),
        QDRANT_COLLECTION_NAME=os.getenv("QDRANT_COLLECTION_NAME"),
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
        LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO")
    ) 