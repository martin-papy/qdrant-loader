import pytest
from pathlib import Path
from dotenv import load_dotenv
from qdrant_loader.core.qdrant_manager import QdrantManager
from qdrant_loader.config import Settings, initialize_config
import os
import uuid
from urllib.parse import urlparse

def load_test_env():
    """Load environment variables ensuring test settings take precedence."""
    # First load any existing .env file
    load_dotenv()
    # Then load test environment to override any existing values
    load_dotenv(Path(__file__).parent.parent.parent / ".env.test", override=True)

# Load test environment variables
load_test_env()

@pytest.fixture(scope="session", autouse=True)
def initialize_test_config():
    """Initialize the global config for all tests."""
    yaml_path = Path(__file__).parent.parent.parent / "config.test.yaml"
    initialize_config(yaml_path)

@pytest.fixture
def test_settings():
    """Fixture that provides test settings for all tests."""
    settings = Settings(
        QDRANT_URL=os.getenv("QDRANT_URL"),
        QDRANT_API_KEY=os.getenv("QDRANT_API_KEY"),
        QDRANT_COLLECTION_NAME=f"{os.getenv('QDRANT_COLLECTION_NAME')}-{uuid.uuid4().hex[:8]}",
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
        LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO")
    )
    return settings

@pytest.fixture
def qdrant_manager(test_settings):
    """Create a QdrantManager instance for testing."""
    manager = QdrantManager(settings=test_settings)
    yield manager
    # Cleanup: delete test collection after each test
    try:
        manager.client.delete_collection(test_settings.QDRANT_COLLECTION_NAME)
    except Exception:
        pass  # Ignore cleanup errors

@pytest.mark.integration
def test_init_connection(test_settings):
    """Test initialization with real connection."""
    manager = QdrantManager(settings=test_settings)
    assert manager.client is not None
    assert manager.collection_name == test_settings.QDRANT_COLLECTION_NAME

@pytest.mark.integration
def test_collection_operations(qdrant_manager, test_settings):
    """Test collection operations with real Qdrant instance."""
    # Create the collection first
    qdrant_manager.client.create_collection(
        collection_name=test_settings.QDRANT_COLLECTION_NAME,
        vectors_config={"size": 3, "distance": "Cosine"}
    )

    # Test collection creation
    collections = qdrant_manager.client.get_collections().collections
    collection_names = [collection.name for collection in collections]
    assert test_settings.QDRANT_COLLECTION_NAME in collection_names

    # Test point operations
    points = [
        {
            "id": 1,
            "vector": [0.1, 0.2, 0.3],
            "payload": {"text": "test document 1"}
        },
        {
            "id": 2,
            "vector": [0.4, 0.5, 0.6],
            "payload": {"text": "test document 2"}
        }
    ]
    
    # Insert points
    qdrant_manager.client.upsert(
        collection_name=test_settings.QDRANT_COLLECTION_NAME,
        points=points
    )
    
    # Search for points
    search_result = qdrant_manager.client.query_points(
        collection_name=test_settings.QDRANT_COLLECTION_NAME,
        query=[0.1, 0.2, 0.3],
        limit=1
    )
    
    assert len(search_result.points) == 1
    assert search_result.points[0].id == 1
    assert search_result.points[0].payload["text"] == "test document 1"
    
    # Delete points
    qdrant_manager.client.delete(
        collection_name=test_settings.QDRANT_COLLECTION_NAME,
        points_selector=[1, 2]
    )
    
    # Verify deletion
    search_result = qdrant_manager.client.query_points(
        collection_name=test_settings.QDRANT_COLLECTION_NAME,
        query=[0.1, 0.2, 0.3],
        limit=1
    )
    assert len(search_result.points) == 0

@pytest.mark.integration
def test_error_handling(test_settings):
    """Test error handling with real Qdrant instance."""
    from qdrant_client.http.exceptions import UnexpectedResponse, ResponseHandlingException
    from requests.exceptions import ConnectionError

    # Debug output
    print(f"\nQdrant URL being used: {test_settings.QDRANT_URL}")

    # Skip test if using local instance (no authentication required)
    parsed_url = urlparse(test_settings.QDRANT_URL)
    if any(host in parsed_url.netloc for host in ['localhost', '127.0.0.1']):
        pytest.skip("Skipping error handling test for local instance (no authentication required)")

    # Test invalid API key
    invalid_settings = Settings(
        QDRANT_URL=test_settings.QDRANT_URL,
        QDRANT_API_KEY="invalid-key",
        QDRANT_COLLECTION_NAME=test_settings.QDRANT_COLLECTION_NAME,
        OPENAI_API_KEY=test_settings.OPENAI_API_KEY,
        LOG_LEVEL=test_settings.LOG_LEVEL
    )
    
    # Test that we can't perform operations with invalid credentials
    manager = QdrantManager(settings=invalid_settings)
    with pytest.raises(UnexpectedResponse):
        manager.create_collection()
    
    # Test invalid URL
    invalid_settings = Settings(
        QDRANT_URL="https://invalid-url:6333",
        QDRANT_API_KEY=test_settings.QDRANT_API_KEY,
        QDRANT_COLLECTION_NAME=test_settings.QDRANT_COLLECTION_NAME,
        OPENAI_API_KEY=test_settings.OPENAI_API_KEY,
        LOG_LEVEL=test_settings.LOG_LEVEL
    )
    
    with pytest.raises(ResponseHandlingException):
        manager = QdrantManager(settings=invalid_settings)
        # Try to perform an operation to trigger the connection error
        manager.client.get_collections() 