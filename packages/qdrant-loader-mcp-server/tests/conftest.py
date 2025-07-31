"""Shared test fixtures and configuration for MCP server tests."""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from dotenv import load_dotenv

# Add the src directory to Python path for imports
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def pytest_configure(config):
    """Configure pytest before test collection."""
    # Set asyncio mode to strict
    config.option.asyncio_mode = "strict"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment before running tests."""
    # Load test environment variables
    test_env_path = Path(__file__).parent / ".env.test"
    if test_env_path.exists():
        load_dotenv(test_env_path, override=True)

    # Set default test environment variables
    os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
    os.environ.setdefault("QDRANT_COLLECTION_NAME", "test_collection")
    os.environ.setdefault("OPENAI_API_KEY", "test_key")
    os.environ.setdefault("MCP_DISABLE_CONSOLE_LOGGING", "true")


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client."""
    client = AsyncMock()

    # Mock search results
    search_result1 = MagicMock()
    search_result1.id = "1"
    search_result1.score = 0.8
    search_result1.payload = {
        "content": "Test content 1",
        "metadata": {"title": "Test Doc 1", "url": "http://test1.com"},
        "source_type": "git",
    }

    search_result2 = MagicMock()
    search_result2.id = "2"
    search_result2.score = 0.7
    search_result2.payload = {
        "content": "Test content 2",
        "metadata": {"title": "Test Doc 2", "url": "http://test2.com"},
        "source_type": "confluence",
    }

    client.search.return_value = [search_result1, search_result2]
    client.scroll.return_value = ([search_result1, search_result2], None)

    # Mock collection operations
    collections_response = MagicMock()
    collections_response.collections = []
    client.get_collections.return_value = collections_response
    client.create_collection.return_value = None
    client.close.return_value = None

    return client


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    client = AsyncMock()

    # Mock embeddings response
    embedding_response = MagicMock()
    embedding_data = MagicMock()
    embedding_data.embedding = [0.1, 0.2, 0.3] * 512  # 1536 dimensions
    embedding_response.data = [embedding_data]
    client.embeddings.create.return_value = embedding_response

    # Mock chat completion response
    chat_response = MagicMock()
    chat_choice = MagicMock()
    chat_message = MagicMock()
    chat_message.content = "general"
    chat_choice.message = chat_message
    chat_response.choices = [chat_choice]
    client.chat.completions.create.return_value = chat_response

    return client


@pytest.fixture
def mock_search_engine(mock_qdrant_client, mock_openai_client):
    """Create a mock search engine."""
    from qdrant_loader_mcp_server.search.engine import SearchEngine
    from qdrant_loader_mcp_server.search.components.search_result_models import HybridSearchResult, create_hybrid_search_result

    engine = MagicMock(spec=SearchEngine)

    # Mock search results
    search_results = [
        create_hybrid_search_result(
            score=0.8,
            text="Test content 1",
            source_type="git",
            source_title="Test Doc 1",
            source_url="http://test1.com",
        ),
        create_hybrid_search_result(
            score=0.7,
            text="Test content 2",
            source_type="confluence",
            source_title="Test Doc 2",
            source_url="http://test2.com",
        ),
    ]

    engine.search = AsyncMock(return_value=search_results)
    engine.initialize = AsyncMock()
    engine.cleanup = AsyncMock()

    return engine


@pytest.fixture
def mock_query_processor():
    """Create a mock query processor."""
    from qdrant_loader_mcp_server.search.processor import QueryProcessor

    processor = MagicMock(spec=QueryProcessor)
    processor.process_query = AsyncMock(
        return_value={
            "query": "test query",
            "intent": "general",
            "source_type": None,
            "processed": True,
        }
    )

    return processor


@pytest.fixture
def mcp_handler(mock_search_engine, mock_query_processor):
    """Create an MCP handler with mocked dependencies."""
    from qdrant_loader_mcp_server.mcp.handler import MCPHandler

    return MCPHandler(mock_search_engine, mock_query_processor)


@pytest.fixture
def config():
    """Create test configuration."""
    from qdrant_loader_mcp_server.config import Config

    return Config()


@pytest.fixture
def qdrant_config():
    """Create Qdrant configuration."""
    from qdrant_loader_mcp_server.config import QdrantConfig

    return QdrantConfig()


@pytest.fixture
def openai_config():
    """Create OpenAI configuration."""
    from qdrant_loader_mcp_server.config import OpenAIConfig

    return OpenAIConfig(api_key="test_key")
