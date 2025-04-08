import os
import pytest
from pathlib import Path
from dotenv import load_dotenv
import yaml

# Load test environment variables
load_dotenv(Path(__file__).parent.parent / ".env.test")

@pytest.fixture(scope="session")
def test_settings():
    """Load test settings from environment variables."""
    return {
        "QDRANT_URL": os.getenv("QDRANT_URL"),
        "QDRANT_API_KEY": os.getenv("QDRANT_API_KEY"),
        "QDRANT_COLLECTION_NAME": os.getenv("QDRANT_COLLECTION_NAME"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO")
    }

@pytest.fixture(scope="session")
def test_config():
    """Load test configuration from config.test.yaml."""
    config_path = Path(__file__).parent / "config.test.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)

@pytest.fixture(scope="function")
def test_collection_name(test_settings):
    """Generate a unique collection name for each test."""
    import uuid
    return f"{test_settings['QDRANT_COLLECTION_NAME']}-{uuid.uuid4().hex[:8]}"

@pytest.fixture(scope="function")
def cleanup_collections(test_settings):
    """Cleanup fixture to remove test collections after tests."""
    from qdrant_client import QdrantClient
    
    client = QdrantClient(
        url=test_settings["QDRANT_URL"],
        api_key=test_settings["QDRANT_API_KEY"]
    )
    
    yield
    
    # Cleanup all test collections
    collections = client.get_collections().collections
    for collection in collections:
        if collection.name.startswith(test_settings["QDRANT_COLLECTION_NAME"]):
            client.delete_collection(collection.name) 