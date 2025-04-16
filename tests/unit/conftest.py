import pytest
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.fixture(autouse=True)
def mock_qdrant_client():
    """Mock the Qdrant client at the module level."""
    with patch("qdrant_loader.core.qdrant_manager.QdrantClient") as mock_client:
        # Setup mock client
        mock_instance = MagicMock()
        mock_instance.get_collections.return_value = MagicMock(collections=[])
        mock_client.return_value = mock_instance
        yield mock_client


@pytest.fixture
def mock_qdrant_manager(mock_qdrant_client):
    """Create a mock Qdrant manager with minimal required components."""
    mock_manager = MagicMock()
    mock_manager.client = mock_qdrant_client.return_value

    # Set up collections response
    collections_mock = MagicMock()
    collections_mock.collections = []  # No existing collections
    mock_manager.client.get_collections.return_value = collections_mock

    # Set up create_collection to actually call get_collections
    def mock_create_collection():
        mock_manager.client.get_collections()

    mock_manager.create_collection.side_effect = mock_create_collection

    return mock_manager


@pytest.fixture
def mock_settings():
    """Create a mock settings object with required configuration."""
    mock_settings = MagicMock()
    mock_settings.QDRANT_COLLECTION_NAME = "qdrant-loader-test"
    mock_settings.QDRANT_URL = "https://test-url"
    mock_settings.QDRANT_API_KEY = "test-key"
    return mock_settings


@pytest.fixture
def mock_collection():
    """Create a mock collection object."""
    mock_collection = MagicMock()
    mock_collection.name = "qdrant-loader-test"
    return mock_collection


@pytest.fixture
def mock_collections_response(mock_collection):
    """Create a mock collections response with a collection."""
    mock_response = MagicMock()
    mock_response.collections = [mock_collection]
    return mock_response


@pytest.fixture
def mock_pipeline():
    """Create a mock ingestion pipeline."""
    mock = MagicMock()
    mock.process_documents = MagicMock(return_value=None)
    return mock


@pytest.fixture
def mock_init_collection():
    """Mock the init_collection function."""
    mock = AsyncMock()
    mock.return_value = True
    return mock
