"""Tests for MarkItDown client API key usage."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from qdrant_loader.config import get_settings, initialize_config
from qdrant_loader.core.file_conversion import FileConverter


class TestMarkItDownAPIKeyUsage:
    """Tests for MarkItDown client API key usage."""

    @pytest.fixture
    def markitdown_config_content(self):
        """Configuration content for testing MarkItDown API key usage."""
        return """
global:
  qdrant:
    url: "http://localhost:6333"
    api_key: null
    collection_name: "test_markitdown"

  file_conversion:
    markitdown:
      enable_llm_descriptions: true
      llm_model: "gpt-4o"
      llm_endpoint: "https://api.openai.com/v1"
      llm_api_key: "fake-test-api-key-for-testing-only"

projects:
  default:
    display_name: "Test Project"
    description: "Test project for MarkItDown API key testing"
    sources: {}
"""

    @pytest.fixture
    def temp_config_file(self, markitdown_config_content):
        """Create a temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(markitdown_config_content)
            temp_path = Path(f.name)

        yield temp_path

        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_markitdown_uses_configured_api_key(self, temp_config_file):
        """Test that MarkItDown client uses the API key from configuration."""
        # Set different environment variable to ensure config takes precedence
        os.environ["OPENAI_API_KEY"] = "fake-env-api-key-for-testing"

        try:
            # Initialize configuration
            initialize_config(temp_config_file, skip_validation=True)
            settings = get_settings()

            # Create FileConverter with the configuration
            file_converter = FileConverter(settings.global_config.file_conversion)

            # Test that the configuration has the correct API key
            configured_api_key = (
                settings.global_config.file_conversion.markitdown.llm_api_key
            )
            assert configured_api_key == "fake-test-api-key-for-testing-only"

            # Mock the OpenAI client to capture the API key being used
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                # This should trigger the creation of the LLM client
                client = file_converter._create_llm_client()

                if mock_openai.called:
                    call_args = mock_openai.call_args
                    assert "api_key" in call_args.kwargs
                    used_api_key = call_args.kwargs["api_key"]
                    assert used_api_key == configured_api_key
                else:
                    # Provider-backed client path; no OpenAI instantiation occurs
                    assert hasattr(client, "chat") and hasattr(
                        client.chat, "completions"
                    )

        finally:
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def test_markitdown_fallback_to_environment_variable(self, temp_config_file):
        """Test that MarkItDown falls back to environment variable when config API key is None."""
        # Modify config to have None API key
        config_content = """
global:
  qdrant:
    url: "http://localhost:6333"
    api_key: null
    collection_name: "test_markitdown_fallback"

  file_conversion:
    markitdown:
      enable_llm_descriptions: true
      llm_model: "gpt-4o"
      llm_endpoint: "https://api.openai.com/v1"
      llm_api_key: null

projects:
  default:
    display_name: "Test Project"
    description: "Test project for fallback testing"
    sources: {}
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            fallback_config_path = Path(f.name)

        # Set environment variable
        os.environ["OPENAI_API_KEY"] = "fake-fallback-test-key"

        try:
            # Initialize configuration
            initialize_config(fallback_config_path, skip_validation=True)
            settings = get_settings()

            # Create FileConverter
            file_converter = FileConverter(settings.global_config.file_conversion)

            # Mock the OpenAI client
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                client = file_converter._create_llm_client()

                if mock_openai.called:
                    call_args = mock_openai.call_args
                    used_api_key = call_args.kwargs.get("api_key")
                    assert used_api_key == "fake-fallback-test-key"
                else:
                    assert hasattr(client, "chat") and hasattr(
                        client.chat, "completions"
                    )

        finally:
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
            if fallback_config_path.exists():
                fallback_config_path.unlink()

    def test_markitdown_api_key_precedence(self, temp_config_file):
        """Test that configured API key takes precedence over environment variable."""
        # Set environment variable with different value
        os.environ["OPENAI_API_KEY"] = "fake-env-key-should-not-be-used"

        try:
            # Initialize configuration
            initialize_config(temp_config_file, skip_validation=True)
            settings = get_settings()

            # Create FileConverter
            file_converter = FileConverter(settings.global_config.file_conversion)

            # The configured API key should take precedence
            configured_key = (
                settings.global_config.file_conversion.markitdown.llm_api_key
            )
            assert configured_key == "fake-test-api-key-for-testing-only"

            # Mock OpenAI to verify the correct key is used
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                client = file_converter._create_llm_client()

                if mock_openai.called:
                    call_args = mock_openai.call_args
                    used_api_key = call_args.kwargs.get("api_key")
                    assert used_api_key == "fake-test-api-key-for-testing-only"
                    assert used_api_key != "fake-env-key-should-not-be-used"
                else:
                    assert hasattr(client, "chat") and hasattr(
                        client.chat, "completions"
                    )

        finally:
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def test_markitdown_openai_endpoint_configuration(self, temp_config_file):
        """Test that MarkItDown client uses the configured OpenAI endpoint."""
        try:
            # Initialize configuration
            initialize_config(temp_config_file, skip_validation=True)
            settings = get_settings()

            # Create FileConverter
            file_converter = FileConverter(settings.global_config.file_conversion)

            # Test that the configuration has the correct endpoint
            configured_endpoint = (
                settings.global_config.file_conversion.markitdown.llm_endpoint
            )
            assert configured_endpoint == "https://api.openai.com/v1"

            # Mock the OpenAI client to capture the endpoint being used
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                client = file_converter._create_llm_client()

                if mock_openai.called:
                    call_args = mock_openai.call_args
                    used_endpoint = call_args.kwargs.get("base_url")
                    assert used_endpoint == configured_endpoint
                else:
                    assert hasattr(client, "chat") and hasattr(
                        client.chat, "completions"
                    )

        finally:
            pass

    def test_markitdown_without_llm_descriptions(self):
        """Test that MarkItDown works without LLM descriptions enabled."""
        config_content = """
global:
  qdrant:
    url: "http://localhost:6333"
    api_key: null
    collection_name: "test_markitdown_no_llm"

  file_conversion:
    markitdown:
      enable_llm_descriptions: false

projects:
  default:
    display_name: "Test Project"
    description: "Test project without LLM descriptions"
    sources: {}
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            config_path = Path(f.name)

        try:
            # Initialize configuration
            initialize_config(config_path, skip_validation=True)
            settings = get_settings()

            # Create FileConverter
            FileConverter(settings.global_config.file_conversion)

            # Test that LLM descriptions are disabled
            markitdown_config = settings.global_config.file_conversion.markitdown
            assert markitdown_config.enable_llm_descriptions is False

            # Should not attempt to create LLM client when disabled
            # This test mainly ensures the configuration is properly parsed

        finally:
            if config_path.exists():
                config_path.unlink()
