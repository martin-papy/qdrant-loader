"""Tests for configuration module."""

import os
from unittest.mock import patch

from qdrant_loader_mcp_server.config import Config, OpenAIConfig, QdrantConfig


def test_config_creation():
    """Test basic config creation."""
    config = Config()
    assert config is not None
    assert hasattr(config, "qdrant")
    assert hasattr(config, "openai")


def test_qdrant_config_defaults(monkeypatch):
    """Test Qdrant configuration defaults."""
    # Clear all Qdrant-related environment variables
    monkeypatch.delenv("QDRANT_URL", raising=False)
    monkeypatch.delenv("QDRANT_API_KEY", raising=False)
    monkeypatch.delenv("QDRANT_COLLECTION_NAME", raising=False)

    config = QdrantConfig()
    assert config.url == "http://localhost:6333"
    assert config.collection_name == "documents"
    assert config.api_key is None


def test_qdrant_config_from_env(monkeypatch):
    """Test Qdrant configuration from environment variables."""
    # Set test environment variables
    monkeypatch.setenv("QDRANT_URL", "http://test:6333")
    monkeypatch.setenv("QDRANT_API_KEY", "test_key")
    monkeypatch.setenv("QDRANT_COLLECTION_NAME", "test_collection")

    config = QdrantConfig()
    assert config.url == "http://test:6333"
    assert config.api_key == "test_key"
    assert config.collection_name == "test_collection"


def test_openai_config_defaults():
    """Test OpenAI configuration defaults."""
    config = OpenAIConfig(api_key="test_key")
    assert config.model == "text-embedding-3-small"
    assert config.api_key == "test_key"


def test_openai_config_from_env():
    """Test OpenAI configuration from environment variables."""
    with patch.dict(
        os.environ,
        {"OPENAI_API_KEY": "test_key", "OPENAI_MODEL": "text-embedding-ada-002"},
    ):
        config = OpenAIConfig(api_key="test_key")
        assert config.api_key == "test_key"
        assert (
            config.model == "text-embedding-3-small"
        )  # Model is not read from env in this config


def test_openai_config_with_api_key():
    """Test OpenAI configuration with explicit API key."""
    config = OpenAIConfig(api_key="explicit_key")
    assert config.api_key == "explicit_key"


def test_config_validation():
    """Test configuration validation."""
    # Test valid configuration
    qdrant_config = QdrantConfig(
        url="http://localhost:6333", collection_name="test", api_key="key"
    )
    assert qdrant_config.url == "http://localhost:6333"

    openai_config = OpenAIConfig(api_key="test_key")
    assert openai_config.api_key == "test_key"


def test_config_integration(monkeypatch):
    """Test full configuration integration."""
    # Set test environment variables
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("QDRANT_COLLECTION_NAME", "test_collection")
    monkeypatch.delenv("QDRANT_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")

    config = Config()
    assert config.qdrant.url == "http://localhost:6333"
    assert config.qdrant.collection_name == "test_collection"
    assert config.openai.api_key == "test_key"


def test_openai_config_api_key_optional():
    """OpenAIConfig() without api_key should not raise."""
    # api_key is Optional[str] with a default of None; instantiation must succeed
    config = OpenAIConfig()
    assert config is not None


def test_openai_config_api_key_none_by_default():
    """OpenAIConfig().api_key is None when not provided."""
    config = OpenAIConfig()
    assert config.api_key is None


def test_openai_config_with_api_key_explicit():
    """OpenAIConfig(api_key='test').api_key equals the supplied value."""
    config = OpenAIConfig(api_key="test")
    assert config.api_key == "test"


def test_config_without_openai_env_var(monkeypatch):
    """Config() should work when OPENAI_API_KEY env var is not set."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    config = Config()
    assert config is not None
    assert config.openai.api_key is None


def test_qdrant_config_defaults_aligned(monkeypatch):
    """QdrantConfig() defaults match the expected canonical values.

    Defaults must stay aligned with qdrant_loader.config.qdrant.QdrantConfig:
      url            -> http://localhost:6333
      collection_name -> documents
      api_key        -> None
    """
    monkeypatch.delenv("QDRANT_URL", raising=False)
    monkeypatch.delenv("QDRANT_API_KEY", raising=False)
    monkeypatch.delenv("QDRANT_COLLECTION_NAME", raising=False)

    config = QdrantConfig()
    assert config.url == "http://localhost:6333"
    assert config.collection_name == "documents"
    assert config.api_key is None
