"""Tests for traditional configuration mode (using --config flag)."""

import os
import tempfile
from pathlib import Path

import pytest
from qdrant_loader.config import get_settings, initialize_config


class TestTraditionalConfiguration:
    """Tests for traditional configuration mode."""

    @pytest.fixture
    def traditional_config_content(self):
        """Traditional configuration content with $HOME expansion."""
        return """
global:
  qdrant:
    url: "http://localhost:6333"
    api_key: null
    collection_name: "traditional_test"

  chunking:
    chunk_size: 1500
    chunk_overlap: 200
  
  embedding:
    model: "text-embedding-3-small"
    api_key: "${OPENAI_API_KEY}"
    batch_size: 100

  state_management:
    database_path: ":memory:"
    table_prefix: "qdrant_loader_"
    connection_pool:
      size: 5
      timeout: 30

  file_conversion:
    max_file_size: 52428800
    conversion_timeout: 300
    markitdown:
      enable_llm_descriptions: false

projects:
  default:
    display_name: "Traditional Test Project"
    description: "Default project for traditional configuration testing"
sources: {}
"""

    @pytest.fixture
    def temp_config_file(self, traditional_config_content):
        """Create a temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(traditional_config_content)
            temp_path = Path(f.name)

        yield temp_path

        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_traditional_config_initialization(self, temp_config_file):
        """Test traditional configuration initialization."""
        # Set required environment variables
        os.environ["OPENAI_API_KEY"] = "traditional_test_key"

        try:
            # Initialize configuration in traditional mode
            initialize_config(temp_config_file, skip_validation=True)
            settings = get_settings()

            # Test basic configuration access
            assert settings.qdrant_url == "http://localhost:6333"
            assert settings.qdrant_collection_name == "traditional_test"

            # Test that database path is set to memory
            assert settings.state_db_path == ":memory:"

            # Test embedding configuration
            assert settings.global_config.embedding.api_key == "traditional_test_key"
            assert settings.global_config.embedding.model == "text-embedding-3-small"
            assert settings.global_config.embedding.batch_size == 100

            # Test chunking configuration
            assert settings.global_config.chunking.chunk_size == 1500
            assert settings.global_config.chunking.chunk_overlap == 200

        finally:
            # Clean up environment variables
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def test_traditional_config_home_expansion(self, temp_config_file):
        """Test traditional configuration with environment variable expansion."""
        # Set required environment variables
        os.environ["OPENAI_API_KEY"] = "home_expansion_test_key"

        try:
            # Initialize configuration
            initialize_config(temp_config_file, skip_validation=True)
            settings = get_settings()

            # Test that configuration is loaded correctly
            assert settings.qdrant_collection_name == "traditional_test"
            assert settings.state_db_path == ":memory:"
            assert settings.global_config.embedding.api_key == "home_expansion_test_key"

        finally:
            # Clean up environment variables
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
