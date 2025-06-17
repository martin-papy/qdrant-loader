"""Tests for template configuration with simplified approach."""

import os
import tempfile
from pathlib import Path

import pytest
from qdrant_loader.config import get_settings, initialize_config


class TestTemplateConfiguration:
    """Tests for template configuration loading."""

    @pytest.fixture
    def template_config_content(self):
        """Template configuration content for testing."""
        return """
global:
  qdrant:
    url: "http://localhost:6333"
    api_key: null
    collection_name: "test_template"

  chunking:
    chunk_size: 1500
    chunk_overlap: 200
  
  embedding:
    endpoint: "http://localhost:8080/v1"
    model: "BAAI/bge-small-en-v1.5"
    api_key: "${OPENAI_API_KEY}"
    batch_size: 100
    vector_size: 384
    tokenizer: "none"
    max_tokens_per_request: 8000
    max_tokens_per_chunk: 8000

  state_management:
    database_path: "${STATE_DB_PATH}"
    table_prefix: "qdrant_loader_"
    connection_pool:
      size: 5
      timeout: 30

  file_conversion:
    max_file_size: 52428800
    conversion_timeout: 300
    markitdown:
      enable_llm_descriptions: false
      llm_model: "gpt-4o"
      llm_endpoint: "https://api.openai.com/v1"
      llm_api_key: "${OPENAI_API_KEY}"

projects:
  default:
    display_name: "Template Test Project"
    description: "Default project for template configuration testing"
    sources: {}
"""

    @pytest.fixture
    def temp_config_file(self, template_config_content):
        """Create a temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(template_config_content)
            temp_path = Path(f.name)

        yield temp_path

        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_template_config_initialization(self, temp_config_file):
        """Test template configuration initialization."""
        # Set required environment variables
        os.environ["STATE_DB_PATH"] = "/tmp/test_template.db"
        os.environ["OPENAI_API_KEY"] = "test_api_key_12345"

        try:
            # Initialize configuration with template
            initialize_config(temp_config_file, skip_validation=True)
            settings = get_settings()

            # Test basic configuration access
            assert settings.qdrant_url == "http://localhost:6333"
            assert settings.qdrant_collection_name == "test_template"
            assert settings.state_db_path == "/tmp/test_template.db"

        finally:
            # Cleanup environment variables
            if "STATE_DB_PATH" in os.environ:
                del os.environ["STATE_DB_PATH"]
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def test_template_embedding_configuration(self, temp_config_file):
        """Test template embedding configuration."""
        os.environ["OPENAI_API_KEY"] = "test_embedding_key"

        try:
            initialize_config(temp_config_file, skip_validation=True)
            settings = get_settings()

            # Test embedding configuration
            assert settings.global_config.embedding.model == "BAAI/bge-small-en-v1.5"
            assert (
                settings.global_config.embedding.endpoint == "http://localhost:8080/v1"
            )
            assert settings.global_config.embedding.vector_size == 384
            assert settings.global_config.embedding.tokenizer == "none"
            assert settings.global_config.embedding.api_key == "test_embedding_key"

        finally:
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def test_template_chunking_configuration(self, temp_config_file):
        """Test template chunking configuration."""
        os.environ["OPENAI_API_KEY"] = "test_key"

        try:
            initialize_config(temp_config_file, skip_validation=True)
            settings = get_settings()

            # Test chunking configuration
            assert settings.global_config.chunking.chunk_size == 1500
            assert settings.global_config.chunking.chunk_overlap == 200

        finally:
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def test_template_file_conversion_configuration(self, temp_config_file):
        """Test template file conversion configuration."""
        os.environ["OPENAI_API_KEY"] = "test_conversion_key"

        try:
            initialize_config(temp_config_file, skip_validation=True)
            settings = get_settings()

            # Test file conversion configuration
            assert settings.global_config.file_conversion.max_file_size == 52428800
            assert settings.global_config.file_conversion.conversion_timeout == 300
            assert (
                settings.global_config.file_conversion.markitdown.enable_llm_descriptions
                is False
            )
            assert (
                settings.global_config.file_conversion.markitdown.llm_model == "gpt-4o"
            )
            assert (
                settings.global_config.file_conversion.markitdown.llm_endpoint
                == "https://api.openai.com/v1"
            )
            assert (
                settings.global_config.file_conversion.markitdown.llm_api_key
                == "test_conversion_key"
            )

        finally:
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def test_template_variable_substitution(self, temp_config_file):
        """Test that template variables are properly substituted."""
        # Set environment variables with specific values
        os.environ["STATE_DB_PATH"] = ":memory:"  # Use in-memory database for tests
        os.environ["OPENAI_API_KEY"] = "custom_api_key_xyz"

        try:
            initialize_config(temp_config_file, skip_validation=True)
            settings = get_settings()

            # Verify variable substitution worked
            assert settings.state_db_path == ":memory:"
            assert settings.global_config.embedding.api_key == "custom_api_key_xyz"
            assert (
                settings.global_config.file_conversion.markitdown.llm_api_key
                == "custom_api_key_xyz"
            )

        finally:
            if "STATE_DB_PATH" in os.environ:
                del os.environ["STATE_DB_PATH"]
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def test_template_with_missing_env_vars(self, temp_config_file):
        """Test template behavior with missing environment variables."""
        # Clear any existing environment variables
        env_vars_to_clear = ["STATE_DB_PATH", "OPENAI_API_KEY"]
        original_values = {}

        for var in env_vars_to_clear:
            original_values[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]

        try:
            # Should still initialize with skip_validation=True
            initialize_config(temp_config_file, skip_validation=True)
            settings = get_settings()

            # Should have placeholder values
            assert (
                "${STATE_DB_PATH}" in settings.state_db_path
                or settings.state_db_path == "${STATE_DB_PATH}"
            )

        finally:
            # Restore original environment variables
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value

    def test_template_state_management_configuration(self, temp_config_file):
        """Test template state management configuration."""
        os.environ["STATE_DB_PATH"] = ":memory:"
        os.environ["OPENAI_API_KEY"] = "test_key"

        try:
            initialize_config(temp_config_file, skip_validation=True)
            settings = get_settings()

            # Test state management configuration
            assert settings.global_config.state_management.database_path == ":memory:"
            assert (
                settings.global_config.state_management.table_prefix == "qdrant_loader_"
            )
            # Test connection pool configuration (it's a dict)
            connection_pool = settings.global_config.state_management.connection_pool
            assert connection_pool["size"] == 5
            assert connection_pool["timeout"] == 30

        finally:
            if "STATE_DB_PATH" in os.environ:
                del os.environ["STATE_DB_PATH"]
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
