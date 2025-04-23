"""Shared test fixtures and configuration.

This module contains pytest fixtures that are shared across all test modules.
"""

import shutil
from pathlib import Path
import os
import sys

import pytest
from dotenv import load_dotenv
from qdrant_loader.config import get_settings, initialize_config


def pytest_configure(config):
    """Configure pytest before test collection."""
    # Add the tests directory to the Python path
    # This ensures imports within tests use absolute paths
    # rather than trying to resolve relative to the module name
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)

    # Suppress XMLParsedAsHTMLWarning from BeautifulSoup
    config.addinivalue_line("filterwarnings", "ignore::bs4.XMLParsedAsHTMLWarning")


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment before running tests."""
    # Create necessary directories
    data_dir = Path("./data")
    data_dir.mkdir(parents=True, exist_ok=True)

    # Load test configuration
    config_path = Path("tests/config.test.yaml")
    env_path = Path("tests/.env.test")

    # Load environment variables first
    load_dotenv(env_path, override=True)

    # Initialize config using the same function as CLI
    initialize_config(config_path)

    yield

    # Clean up after all tests
    if data_dir.exists():
        shutil.rmtree(data_dir)


@pytest.fixture(scope="session")
def test_settings():
    """Get test settings."""
    settings = get_settings()
    return settings


@pytest.fixture(scope="session")
def test_global_config():
    """Get test configuration."""
    config = get_settings().global_config
    return config


@pytest.fixture(scope="session")
def qdrant_client(test_global_config):
    """Create and return a Qdrant client for testing."""
    from qdrant_client import QdrantClient

    client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
    yield client
    # Cleanup: Delete test collection after tests
    collection_name = os.getenv("QDRANT_COLLECTION_NAME")
    if collection_name:
        client.delete_collection(collection_name)


@pytest.fixture(scope="function")
def clean_collection(qdrant_client):
    """Ensure the test collection is empty before each test."""
    collection_name = os.getenv("QDRANT_COLLECTION_NAME")
    if collection_name:
        qdrant_client.delete_collection(collection_name)
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config={"size": 1536, "distance": "Cosine"},  # OpenAI embedding size
        )


@pytest.fixture(scope="session")
def mock_requests():
    """Mock requests for external HTTP calls in unit tests."""
    import requests_mock

    with requests_mock.Mocker() as m:
        yield m


@pytest.fixture(scope="session")
def test_data_dir():
    """Return the path to the test data directory."""
    return os.path.join(os.path.dirname(__file__), "fixtures")
