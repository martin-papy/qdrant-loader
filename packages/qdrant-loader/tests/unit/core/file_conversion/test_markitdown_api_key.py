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
      llm_api_key: "test_configured_api_key_12345"

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
        os.environ["OPENAI_API_KEY"] = "env_var_api_key_67890"

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
            assert configured_api_key == "test_configured_api_key_12345"

            # Mock the OpenAI client to capture the API key being used
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                # This should trigger the creation of the LLM client
                try:
                    llm_client = file_converter._create_llm_client()

                    # Verify that OpenAI was called with our configured API key
                    mock_openai.assert_called_once()
                    call_args = mock_openai.call_args

                    # Check that the API key passed to OpenAI matches our configuration
                    assert "api_key" in call_args.kwargs
                    used_api_key = call_args.kwargs["api_key"]
                    assert used_api_key == configured_api_key

                except ImportError:
                    # This is expected in test environment without OpenAI library
                    pytest.skip("OpenAI library not available for testing")

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
        os.environ["OPENAI_API_KEY"] = "env_fallback_key_xyz"

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

                try:
                    llm_client = file_converter._create_llm_client()

                    call_args = mock_openai.call_args
                    if "api_key" in call_args.kwargs:
                        used_api_key = call_args.kwargs["api_key"]
                        # Should use environment variable as fallback
                        assert used_api_key == "env_fallback_key_xyz"

                except ImportError:
                    pytest.skip("OpenAI library not available for testing")

        finally:
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
            if fallback_config_path.exists():
                fallback_config_path.unlink()

    def test_markitdown_api_key_precedence(self, temp_config_file):
        """Test that configured API key takes precedence over environment variable."""
        # Set environment variable with different value
        os.environ["OPENAI_API_KEY"] = "environment_key_should_not_be_used"

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
            assert configured_key == "test_configured_api_key_12345"

            # Mock OpenAI to verify the correct key is used
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                try:
                    file_converter._create_llm_client()

                    call_args = mock_openai.call_args
                    used_api_key = call_args.kwargs.get("api_key")

                    # Should use configured key, not environment variable
                    assert used_api_key == "test_configured_api_key_12345"
                    assert used_api_key != "environment_key_should_not_be_used"

                except ImportError:
                    pytest.skip("OpenAI library not available for testing")

        finally:
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def test_markitdown_openai_endpoint_configuration(self, temp_config_file):
        """Test that MarkItDown uses the correct OpenAI endpoint configuration."""
        os.environ["OPENAI_API_KEY"] = "test_endpoint_key"

        try:
            initialize_config(temp_config_file, skip_validation=True)
            settings = get_settings()

            file_converter = FileConverter(settings.global_config.file_conversion)

            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                try:
                    file_converter._create_llm_client()

                    call_args = mock_openai.call_args

                    # Check that the correct endpoint is used
                    assert "base_url" in call_args.kwargs
                    assert call_args.kwargs["base_url"] == "https://api.openai.com/v1"

                    # Check that API key is passed
                    assert "api_key" in call_args.kwargs
                    assert (
                        call_args.kwargs["api_key"] == "test_configured_api_key_12345"
                    )

                except ImportError:
                    pytest.skip("OpenAI library not available for testing")

        finally:
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def test_markitdown_without_llm_descriptions(self):
        """Test that MarkItDown works correctly when LLM descriptions are disabled."""
        config_content = """
global:
  qdrant:
    url: "http://localhost:6333"
    api_key: null
    collection_name: "test_no_llm"

  file_conversion:
    markitdown:
      enable_llm_descriptions: false
      llm_model: "gpt-4o"
      llm_endpoint: "https://api.openai.com/v1"
      llm_api_key: "should_not_be_used"

projects:
  default:
    display_name: "Test Project"
    description: "Test project for no LLM testing"
    sources: {}
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            no_llm_config_path = Path(f.name)

        try:
            initialize_config(no_llm_config_path, skip_validation=True)
            settings = get_settings()

            file_converter = FileConverter(settings.global_config.file_conversion)

            # When LLM descriptions are disabled, _create_llm_client should not be called
            # during normal MarkItDown initialization
            markitdown_config = settings.global_config.file_conversion.markitdown
            assert markitdown_config.enable_llm_descriptions is False

            # The MarkItDown instance should be created without LLM client
            with patch("markitdown.MarkItDown") as mock_markitdown:
                mock_instance = MagicMock()
                mock_markitdown.return_value = mock_instance

                try:
                    markitdown_instance = file_converter._get_markitdown()

                    # Should be called without llm_client parameter
                    mock_markitdown.assert_called_once_with()

                except ImportError:
                    pytest.skip("MarkItDown library not available for testing")

        finally:
            if no_llm_config_path.exists():
                no_llm_config_path.unlink()
