"""Test configuration validation."""

import tempfile
from pathlib import Path

import pytest
from dotenv import load_dotenv
from pydantic import ValidationError

from qdrant_loader.config import (
    ChunkingConfig,
    GlobalConfig,
    Settings,
    SourcesConfig,
    StateManagementConfig,
)
from qdrant_loader.config.global_ import LoggingConfig

# Load test environment variables
load_dotenv(Path(__file__).parent / ".env.test")


@pytest.fixture
def temp_db_dir():
    """Create a temporary directory for database files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def test_settings(temp_db_dir):
    """Create test settings with required fields."""
    db_path = str(Path(temp_db_dir) / "test.db")
    return Settings(
        QDRANT_URL="http://localhost:6333",
        QDRANT_API_KEY="test-key",
        QDRANT_COLLECTION_NAME="test-collection",
        OPENAI_API_KEY="test-key",
        STATE_DB_PATH=db_path,
        REPO_TOKEN=None,
        REPO_URL=None,
        CONFLUENCE_URL=None,
        CONFLUENCE_SPACE_KEY=None,
        CONFLUENCE_TOKEN=None,
        CONFLUENCE_EMAIL=None,
        JIRA_URL=None,
        JIRA_PROJECT_KEY=None,
        JIRA_TOKEN=None,
        JIRA_EMAIL=None,
        global_config=GlobalConfig(state_management=StateManagementConfig(database_path=db_path)),
    )


@pytest.fixture
def test_global_config(temp_db_dir):
    """Create test global config with required fields."""
    db_path = str(Path(temp_db_dir) / "test.db")
    return GlobalConfig(state_management=StateManagementConfig(database_path=db_path))


def test_settings_validation(test_settings):
    """Test that settings validation works correctly."""
    assert test_settings.QDRANT_URL == "http://localhost:6333"
    assert test_settings.QDRANT_API_KEY == "test-key"
    assert test_settings.QDRANT_COLLECTION_NAME == "test-collection"
    assert test_settings.OPENAI_API_KEY == "test-key"
    assert test_settings.global_config.logging.level == "INFO"
    assert test_settings.STATE_DB_PATH.endswith("test.db")


def test_sources_config_validation():
    """Test that sources config validation works correctly."""
    config = SourcesConfig()
    assert isinstance(config, SourcesConfig)


def test_global_config_defaults(test_global_config):
    """Test that GlobalConfig has correct default values."""
    assert test_global_config.chunking.chunk_size == 1000
    assert test_global_config.chunking.chunk_overlap == 200
    assert test_global_config.embedding.model == "text-embedding-3-small"
    assert test_global_config.embedding.batch_size == 100
    assert test_global_config.logging.level == "INFO"
    assert test_global_config.logging.format == "json"
    assert test_global_config.logging.file == "qdrant-loader.log"
    assert test_global_config.state_management.table_prefix == "qdrant_loader_"
    assert test_global_config.state_management.connection_pool == {"size": 5, "timeout": 30}


def test_invalid_log_level(test_global_config):
    """Test that invalid log level raises ValueError."""
    with pytest.raises(
        ValidationError,
        match="Invalid logging level. Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL",
    ):
        GlobalConfig(
            state_management=test_global_config.state_management,
            logging=LoggingConfig(level="INVALID"),
        )


def test_invalid_log_format(test_global_config):
    """Test that invalid log format raises ValueError."""
    with pytest.raises(ValidationError, match="Invalid log format. Must be one of: json, text"):
        GlobalConfig(
            state_management=test_global_config.state_management,
            logging=LoggingConfig(format="INVALID"),
        )


def test_invalid_chunk_size(test_global_config):
    """Test that invalid chunk size raises ValueError."""
    with pytest.raises(ValidationError, match="Input should be greater than 0"):
        GlobalConfig(
            state_management=test_global_config.state_management,
            chunking=ChunkingConfig(chunk_size=0),
        )


def test_invalid_chunk_overlap(test_global_config):
    """Test that invalid chunk overlap raises ValueError."""
    with pytest.raises(ValidationError, match="Input should be greater than or equal to 0"):
        GlobalConfig(
            state_management=test_global_config.state_management,
            chunking=ChunkingConfig(chunk_overlap=-1),
        )


def test_missing_required_fields():
    """Test that missing required fields raises ValidationError."""
    with pytest.raises(ValidationError):
        Settings(
            QDRANT_URL="",  # Required field
            QDRANT_API_KEY=None,  # Optional field
            QDRANT_COLLECTION_NAME="",  # Required field
            OPENAI_API_KEY="",  # Required field
            STATE_DB_PATH="",  # Required field
            REPO_TOKEN=None,  # Optional field
            REPO_URL=None,  # Optional field
            CONFLUENCE_URL=None,  # Optional field
            CONFLUENCE_SPACE_KEY=None,  # Optional field
            CONFLUENCE_TOKEN=None,  # Optional field
            CONFLUENCE_EMAIL=None,  # Optional field
            JIRA_URL=None,  # Optional field
            JIRA_PROJECT_KEY=None,  # Optional field
            JIRA_TOKEN=None,  # Optional field
            JIRA_EMAIL=None,  # Optional field
        )
