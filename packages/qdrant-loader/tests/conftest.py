"""Shared test fixtures and configuration for qdrant-loader package.

This module contains pytest fixtures that are shared across qdrant-loader package tests.
"""

import logging
import os
import shutil
import sys
from pathlib import Path

import pytest
import pytest_asyncio
import structlog
from dotenv import load_dotenv
from qdrant_client.http import models

# Add the src directory to Python path for imports
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from qdrant_loader.config import get_settings, initialize_multi_file_config


@pytest.fixture(scope="session", autouse=True)
def configure_logging_for_tests():
    """Configure logging to work properly with pytest's caplog fixture."""
    # Reset structlog configuration to work with standard logging
    structlog.reset_defaults()

    # Configure structlog to use standard library logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to work with pytest caplog
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True,  # Override any existing configuration
    )

    # Ensure all our loggers use the standard logging
    for logger_name in [
        "qdrant_loader",
        "qdrant_loader.core",
        "qdrant_loader.core.validation_repair",
    ]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)

    yield

    # Reset after tests
    structlog.reset_defaults()


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment before running tests."""
    # Create necessary directories
    data_dir = Path("./data")
    data_dir.mkdir(parents=True, exist_ok=True)

    # Get the tests directory path relative to this conftest.py file
    tests_dir = Path(__file__).parent

    # Check if we have multi-file configuration
    config_dir = tests_dir / "config"
    if config_dir.exists() and (config_dir / "connectivity.yaml").exists():
        # Use multi-file configuration
        env_path = tests_dir / ".env.test"
        load_dotenv(env_path, override=True)
        initialize_multi_file_config(
            config_dir,
            env_path=env_path,
            enhanced_validation=False,  # Disable enhanced validation for tests
        )
    else:
        # Fallback: create minimal configuration for tests
        config_dir.mkdir(exist_ok=True)

        # Create minimal connectivity.yaml
        connectivity_config = {
            "qdrant": {
                "url": "${QDRANT_URL:-http://localhost:6333}",
                "collection_name": "${QDRANT_COLLECTION_NAME:-test_collection}",
                "api_key": "${QDRANT_API_KEY:-}",
            },
            "embedding": {
                "api_key": "${OPENAI_API_KEY:-test-key}",
                "model": "text-embedding-ada-002",
            },
        }

        # Create minimal projects.yaml
        projects_config = {"projects": {}}

        # Create minimal fine-tuning.yaml
        fine_tuning_config = {"text_chunking": {"chunk_size": 1000}}

        import yaml

        with open(config_dir / "connectivity.yaml", "w") as f:
            yaml.dump(connectivity_config, f)

        with open(config_dir / "projects.yaml", "w") as f:
            yaml.dump(projects_config, f)

        with open(config_dir / "fine-tuning.yaml", "w") as f:
            yaml.dump(fine_tuning_config, f)

        # Load environment variables and initialize
        env_path = tests_dir / ".env.test"
        load_dotenv(env_path, override=True)
        initialize_multi_file_config(
            config_dir,
            env_path=env_path,
            enhanced_validation=False,  # Disable enhanced validation for tests
        )

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

    client = QdrantClient(
        url=test_global_config.qdrant.url, api_key=test_global_config.qdrant.api_key
    )
    yield client
    # Cleanup: Delete test collection after tests
    collection_name = test_global_config.qdrant.collection_name
    if collection_name:
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass


@pytest_asyncio.fixture(scope="function")
async def neo4j_driver(test_global_config):
    """Create and return a Neo4j driver for testing."""
    from neo4j import AsyncGraphDatabase

    uri = test_global_config.neo4j.uri
    user = test_global_config.neo4j.user
    password = test_global_config.neo4j.password
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    yield driver
    await driver.close()


@pytest.fixture(scope="function")
def clean_collection(qdrant_client, test_global_config):
    """Ensure the test collection is empty before each test."""
    collection_name = test_global_config.qdrant.collection_name
    vector_size = test_global_config.embedding.vector_size or 1536

    if collection_name:
        try:
            qdrant_client.delete_collection(collection_name=collection_name)
        except Exception:
            # Ignore errors if collection doesn't exist
            pass

        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size, distance=models.Distance.COSINE
            ),
        )


@pytest_asyncio.fixture(scope="function")
async def clean_neo4j(neo4j_driver):
    """Ensure the Neo4j database is empty before each test."""
    async with neo4j_driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")


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
