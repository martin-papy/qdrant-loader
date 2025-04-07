import os
import pytest
from pathlib import Path
from dotenv import load_dotenv
from qdrant_loader.config import (
    Settings,
    SourcesConfig,
    GlobalConfig,
    PublicDocsSourceConfig,
    SelectorsConfig,
    GitRepoConfig,
    ConfluenceConfig,
    JiraConfig,
    ChunkingConfig
)
from pydantic import ValidationError

# Load test environment variables
load_dotenv(Path(__file__).parent / ".env.test")

@pytest.fixture
def test_settings():
    return Settings(
        QDRANT_URL="http://localhost:6333",
        QDRANT_API_KEY="test-key",
        QDRANT_COLLECTION_NAME="test-collection",
        OPENAI_API_KEY="test-key",
        LOG_LEVEL="INFO"
    )

def test_settings_validation(test_settings):
    """Test that all required settings are present and have correct types."""
    # Test required string fields
    assert isinstance(test_settings.QDRANT_URL, str)
    assert isinstance(test_settings.QDRANT_API_KEY, str)
    assert isinstance(test_settings.QDRANT_COLLECTION_NAME, str)
    assert isinstance(test_settings.OPENAI_API_KEY, str)
    assert isinstance(test_settings.LOG_LEVEL, str)
    
    # Test that string fields are not empty
    assert test_settings.QDRANT_URL
    assert test_settings.QDRANT_API_KEY
    assert test_settings.QDRANT_COLLECTION_NAME
    assert test_settings.OPENAI_API_KEY
    assert test_settings.LOG_LEVEL

def test_sources_config_validation():
    """Test that SourcesConfig can be created with valid data."""
    config = SourcesConfig(
        global_config=GlobalConfig(),
        public_docs={
            "test_docs": PublicDocsSourceConfig(
                base_url="https://docs.example.com",
                version="1.0",
                content_type="html",
                selectors=SelectorsConfig()
            )
        },
        git_repos={
            "test_repo": GitRepoConfig(
                url="https://github.com/example/repo.git",
                branch="main"
            )
        },
        confluence={
            "test_space": ConfluenceConfig(
                url="https://example.atlassian.net/wiki",
                space_key="SPACE",
                content_types=["page"]
            )
        },
        jira={
            "test_project": JiraConfig(
                project_key="PROJ",
                issue_types=["Documentation"]
            )
        }
    )
    
    assert isinstance(config.global_config, GlobalConfig)
    assert isinstance(config.public_docs["test_docs"], PublicDocsSourceConfig)
    assert isinstance(config.git_repos["test_repo"], GitRepoConfig)
    assert isinstance(config.confluence["test_space"], ConfluenceConfig)
    assert isinstance(config.jira["test_project"], JiraConfig)

def test_global_config_defaults():
    """Test that GlobalConfig has correct default values."""
    config = GlobalConfig()
    
    assert config.chunking["size"] == 500
    assert config.chunking["overlap"] == 50
    assert config.embedding.model == "text-embedding-3-small"
    assert config.embedding.batch_size == 100
    assert config.logging["level"] == "INFO"
    assert config.logging["format"] == "json"
    assert config.logging["file"] == "qdrant-loader.log"

def test_invalid_log_level():
    """Test that invalid log level raises ValueError."""
    with pytest.raises(ValueError):
        Settings(
            QDRANT_URL="http://localhost:6333",
            QDRANT_API_KEY="test-key",
            QDRANT_COLLECTION_NAME="test-collection",
            OPENAI_API_KEY="test-key",
            LOG_LEVEL="INVALID"
        )

def test_invalid_log_format():
    """Test that invalid log format raises ValueError."""
    with pytest.raises(ValueError):
        GlobalConfig(logging={"level": "INFO", "format": "invalid"})

def test_invalid_chunk_size():
    """Test that invalid chunk size raises ValueError."""
    with pytest.raises(ValueError, match="Input should be greater than 0"):
        ChunkingConfig(chunk_size=0)

def test_invalid_chunk_overlap():
    """Test that invalid chunk overlap raises ValueError."""
    with pytest.raises(ValueError, match="Input should be greater than or equal to 0"):
        ChunkingConfig(chunk_overlap=-1)

    with pytest.raises(ValueError, match="Chunk overlap must be less than chunk size"):
        ChunkingConfig(chunk_size=100, chunk_overlap=100)

def test_missing_required_fields():
    """Test that missing required fields raises ValidationError."""
    with pytest.raises(ValidationError):
        Settings(
            QDRANT_URL="",
            QDRANT_API_KEY="",
            QDRANT_COLLECTION_NAME="",
            OPENAI_API_KEY=""
        ) 