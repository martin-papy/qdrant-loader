"""Tests for LLM descriptions configuration functionality."""

import os
import tempfile
from pathlib import Path

import pytest
from qdrant_loader.config import get_settings, initialize_config


class TestLLMDescriptionsConfiguration:
    """Tests for LLM descriptions configuration."""

    @pytest.fixture
    def llm_enabled_config_content(self):
        """Configuration content with LLM descriptions enabled."""
        return """
global:
  qdrant:
    url: "http://localhost:6333"
    api_key: null
    collection_name: "test_llm"

  chunking:
    chunk_size: 1000
    chunk_overlap: 200
  
  embedding:
    model: "text-embedding-3-small"
    api_key: "${OPENAI_API_KEY}"
    batch_size: 100
    endpoint: "https://api.openai.com/v1"
    tokenizer: "cl100k_base"
    vector_size: 1536
    max_tokens_per_request: 8000
    max_tokens_per_chunk: 8000

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
      enable_llm_descriptions: true
      llm_model: "gpt-4o"
      llm_endpoint: "https://api.openai.com/v1"
      llm_api_key: "${OPENAI_API_KEY}"

projects:
  default:
    display_name: "LLM Test Project"
    description: "Default project for LLM descriptions testing"
    sources: {}
"""

    @pytest.fixture
    def llm_disabled_config_content(self):
        """Configuration content with LLM descriptions disabled."""
        return """
global:
  qdrant:
    url: "http://localhost:6333"
    api_key: null
    collection_name: "test_no_llm"

  chunking:
    chunk_size: 1000
    chunk_overlap: 200
  
  embedding:
    model: "text-embedding-3-small"
    api_key: "${OPENAI_API_KEY}"
    batch_size: 100

  state_management:
    database_path: ":memory:"

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
    display_name: "LLM Disabled Test Project"
    description: "Default project for LLM descriptions disabled testing"
    sources: {}
"""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing."""

        def _create_config(content):
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as f:
                f.write(content)
                temp_path = Path(f.name)
            return temp_path

        created_files = []

        def create_and_track(content):
            temp_path = _create_config(content)
            created_files.append(temp_path)
            return temp_path

        yield create_and_track

        # Cleanup all created files
        for temp_path in created_files:
            if temp_path.exists():
                temp_path.unlink()

    def test_llm_descriptions_enabled_configuration(
        self, temp_config_file, llm_enabled_config_content
    ):
        """Test that LLM descriptions configuration works when enabled."""
        config_path = temp_config_file(llm_enabled_config_content)

        # Set environment variables
        os.environ["OPENAI_API_KEY"] = "test_api_key_for_llm"

        try:
            # Initialize configuration
            initialize_config(config_path, skip_validation=True)
            settings = get_settings()

            # Test LLM descriptions configuration
            markitdown_config = settings.global_config.file_conversion.markitdown

            assert markitdown_config.enable_llm_descriptions is True
            assert markitdown_config.llm_model == "gpt-4o"
            assert markitdown_config.llm_endpoint == "https://api.openai.com/v1"
            assert markitdown_config.llm_api_key == "test_api_key_for_llm"

        finally:
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def test_llm_descriptions_disabled_configuration(
        self, temp_config_file, llm_disabled_config_content
    ):
        """Test that LLM descriptions configuration works when disabled."""
        config_path = temp_config_file(llm_disabled_config_content)

        # Set environment variables
        os.environ["OPENAI_API_KEY"] = "test_api_key_disabled"

        try:
            # Initialize configuration
            initialize_config(config_path, skip_validation=True)
            settings = get_settings()

            # Test LLM descriptions configuration
            markitdown_config = settings.global_config.file_conversion.markitdown

            assert markitdown_config.enable_llm_descriptions is False
            assert markitdown_config.llm_model == "gpt-4o"
            assert markitdown_config.llm_endpoint == "https://api.openai.com/v1"
            assert markitdown_config.llm_api_key == "test_api_key_disabled"

        finally:
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def test_llm_descriptions_required_fields_when_enabled(
        self, temp_config_file, llm_enabled_config_content
    ):
        """Test that when LLM descriptions are enabled, all required fields are present."""
        config_path = temp_config_file(llm_enabled_config_content)

        # Set environment variables
        os.environ["OPENAI_API_KEY"] = "test_required_fields_key"

        try:
            # Initialize configuration
            initialize_config(config_path, skip_validation=True)
            settings = get_settings()

            markitdown_config = settings.global_config.file_conversion.markitdown

            # Verify that when LLM descriptions are enabled, we have all required fields
            if markitdown_config.enable_llm_descriptions:
                assert markitdown_config.llm_api_key is not None
                assert markitdown_config.llm_api_key != ""
                assert markitdown_config.llm_model is not None
                assert markitdown_config.llm_model != ""
                assert markitdown_config.llm_endpoint is not None
                assert markitdown_config.llm_endpoint != ""

        finally:
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def test_llm_descriptions_api_key_substitution(
        self, temp_config_file, llm_enabled_config_content
    ):
        """Test that API key environment variable substitution works correctly."""
        config_path = temp_config_file(llm_enabled_config_content)

        # Test with different API key values
        test_api_keys = [
            "sk-test123456789",
            "custom_llm_key_xyz",
            "another-api-key-format",
        ]

        for test_key in test_api_keys:
            os.environ["OPENAI_API_KEY"] = test_key

            try:
                # Initialize configuration
                initialize_config(config_path, skip_validation=True)
                settings = get_settings()

                # Verify API key substitution
                markitdown_config = settings.global_config.file_conversion.markitdown
                assert markitdown_config.llm_api_key == test_key

            finally:
                if "OPENAI_API_KEY" in os.environ:
                    del os.environ["OPENAI_API_KEY"]

    def test_llm_descriptions_missing_api_key(
        self, temp_config_file, llm_enabled_config_content
    ):
        """Test behavior when API key is missing."""
        # Modify config to use a different env var that definitely doesn't exist
        modified_config = llm_enabled_config_content.replace(
            "${OPENAI_API_KEY}", "${NONEXISTENT_API_KEY}"
        )
        config_path = temp_config_file(modified_config)

        # Ensure the nonexistent key is not in environment
        if "NONEXISTENT_API_KEY" in os.environ:
            del os.environ["NONEXISTENT_API_KEY"]

        # Should still initialize with skip_validation=True
        initialize_config(config_path, skip_validation=True)
        settings = get_settings()

        markitdown_config = settings.global_config.file_conversion.markitdown

        # Should have placeholder value when env var is missing
        api_key = markitdown_config.llm_api_key
        assert api_key is not None and (
            "${NONEXISTENT_API_KEY}" in api_key or api_key == "${NONEXISTENT_API_KEY}"
        )

    def test_llm_descriptions_full_configuration_validation(
        self, temp_config_file, llm_enabled_config_content
    ):
        """Test complete configuration validation for LLM descriptions."""
        config_path = temp_config_file(llm_enabled_config_content)

        os.environ["OPENAI_API_KEY"] = "comprehensive_test_key"

        try:
            initialize_config(config_path, skip_validation=True)
            settings = get_settings()

            # Test all configuration sections
            assert settings.qdrant_collection_name == "test_llm"
            assert settings.global_config.chunking.chunk_size == 1000
            assert settings.global_config.embedding.model == "text-embedding-3-small"
            assert settings.global_config.embedding.api_key == "comprehensive_test_key"

            # Test file conversion configuration
            file_conv = settings.global_config.file_conversion
            assert file_conv.max_file_size == 52428800
            assert file_conv.conversion_timeout == 300

            # Test MarkItDown configuration
            markitdown = file_conv.markitdown
            assert markitdown.enable_llm_descriptions is True
            assert markitdown.llm_model == "gpt-4o"
            assert markitdown.llm_endpoint == "https://api.openai.com/v1"
            assert markitdown.llm_api_key == "comprehensive_test_key"

        finally:
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
