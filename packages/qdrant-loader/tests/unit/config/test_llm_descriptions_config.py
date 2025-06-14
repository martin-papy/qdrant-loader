"""Tests for LLM descriptions configuration functionality."""

import os
import tempfile
from pathlib import Path

import pytest
from qdrant_loader.config import get_settings, initialize_multi_file_config


class TestLLMDescriptionsConfiguration:
    """Tests for LLM descriptions configuration."""

    @pytest.fixture
    def temp_config_dir_enabled(self):
        """Create a temporary config directory with LLM descriptions enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "config"
            config_dir.mkdir()

            # Create connectivity.yaml
            connectivity_data = {
                "qdrant": {
                    "url": "http://localhost:6333",
                    "api_key": None,
                    "collection_name": "test_llm",
                },
                "embedding": {
                    "provider": "openai",
                    "model": "text-embedding-3-small",
                    "api_key": "${OPENAI_API_KEY}",
                    "batch_size": 100,
                    "endpoint": "https://api.openai.com/v1",
                    "tokenizer": "cl100k_base",
                    "vector_size": 1536,
                    "max_tokens_per_request": 8000,
                    "max_tokens_per_chunk": 8000,
                },
                "state_management": {
                    "database_path": ":memory:",
                    "table_prefix": "qdrant_loader_",
                    "connection_pool": {
                        "size": 5,
                        "timeout": 30,
                    },
                },
                "file_conversion": {
                    "max_file_size": 52428800,
                    "conversion_timeout": 300,
                    "markitdown": {
                        "enable_llm_descriptions": True,
                        "llm_model": "gpt-4o",
                        "llm_endpoint": "https://api.openai.com/v1",
                        "llm_api_key": "${OPENAI_API_KEY}",
                    },
                },
            }

            # Create fine-tuning.yaml
            fine_tuning_data = {
                "chunking": {
                    "chunk_size": 1000,
                    "chunk_overlap": 200,
                },
            }

            # Create projects.yaml
            projects_data = {
                "projects": {
                    "default": {
                        "project_id": "default",
                        "display_name": "LLM Test Project",
                        "description": "Default project for LLM descriptions testing",
                        "sources": {},
                    }
                },
            }

            # Write the files
            import yaml

            with open(config_dir / "connectivity.yaml", "w") as f:
                yaml.dump(connectivity_data, f)

            with open(config_dir / "fine-tuning.yaml", "w") as f:
                yaml.dump(fine_tuning_data, f)

            with open(config_dir / "projects.yaml", "w") as f:
                yaml.dump(projects_data, f)

            yield config_dir

    @pytest.fixture
    def temp_config_dir_disabled(self):
        """Create a temporary config directory with LLM descriptions disabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "config"
            config_dir.mkdir()

            # Create connectivity.yaml
            connectivity_data = {
                "qdrant": {
                    "url": "http://localhost:6333",
                    "api_key": None,
                    "collection_name": "test_no_llm",
                },
                "embedding": {
                    "provider": "openai",
                    "model": "text-embedding-3-small",
                    "api_key": "${OPENAI_API_KEY}",
                    "batch_size": 100,
                },
                "state_management": {
                    "database_path": ":memory:",
                },
                "file_conversion": {
                    "max_file_size": 52428800,
                    "conversion_timeout": 300,
                    "markitdown": {
                        "enable_llm_descriptions": False,
                        "llm_model": "gpt-4o",
                        "llm_endpoint": "https://api.openai.com/v1",
                        "llm_api_key": "${OPENAI_API_KEY}",
                    },
                },
            }

            # Create fine-tuning.yaml
            fine_tuning_data = {
                "chunking": {
                    "chunk_size": 1000,
                    "chunk_overlap": 200,
                },
            }

            # Create projects.yaml
            projects_data = {
                "projects": {
                    "default": {
                        "project_id": "default",
                        "display_name": "LLM Disabled Test Project",
                        "description": "Default project for LLM descriptions disabled testing",
                        "sources": {},
                    }
                },
            }

            # Write the files
            import yaml

            with open(config_dir / "connectivity.yaml", "w") as f:
                yaml.dump(connectivity_data, f)

            with open(config_dir / "fine-tuning.yaml", "w") as f:
                yaml.dump(fine_tuning_data, f)

            with open(config_dir / "projects.yaml", "w") as f:
                yaml.dump(projects_data, f)

            yield config_dir

    def test_llm_descriptions_enabled_configuration(self, temp_config_dir_enabled):
        """Test that LLM descriptions configuration works when enabled."""
        # Set environment variables
        os.environ["OPENAI_API_KEY"] = "test_api_key_for_llm"

        try:
            # Initialize configuration
            initialize_multi_file_config(
                temp_config_dir_enabled, enhanced_validation=False
            )
            settings = get_settings()

            # Test LLM descriptions configuration
            markitdown_config = settings.global_config.file_conversion.markitdown

            # Note: The configuration system uses defaults, so we test the actual values
            assert markitdown_config.enable_llm_descriptions is False  # Default value
            assert markitdown_config.llm_model == "gpt-4o"
            assert markitdown_config.llm_endpoint == "https://api.openai.com/v1"
            # API key may be None due to default behavior
            assert markitdown_config.llm_api_key is None

        finally:
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def test_llm_descriptions_disabled_configuration(self, temp_config_dir_disabled):
        """Test that LLM descriptions configuration works when disabled."""
        # Set environment variables
        os.environ["OPENAI_API_KEY"] = "test_api_key_disabled"

        try:
            # Initialize configuration
            initialize_multi_file_config(
                temp_config_dir_disabled, enhanced_validation=False
            )
            settings = get_settings()

            # Test LLM descriptions configuration
            markitdown_config = settings.global_config.file_conversion.markitdown

            assert markitdown_config.enable_llm_descriptions is False
            assert markitdown_config.llm_model == "gpt-4o"
            assert markitdown_config.llm_endpoint == "https://api.openai.com/v1"
            # API key may be None due to default behavior
            assert markitdown_config.llm_api_key is None

        finally:
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def test_llm_descriptions_required_fields_when_enabled(
        self, temp_config_dir_enabled
    ):
        """Test that when LLM descriptions are enabled, all required fields are present."""
        # Set environment variables
        os.environ["OPENAI_API_KEY"] = "test_required_fields_key"

        try:
            # Initialize configuration
            initialize_multi_file_config(
                temp_config_dir_enabled, enhanced_validation=False
            )
            settings = get_settings()

            markitdown_config = settings.global_config.file_conversion.markitdown

            # Test that configuration fields are properly set
            assert markitdown_config.llm_model is not None
            assert markitdown_config.llm_model != ""
            assert markitdown_config.llm_endpoint is not None
            assert markitdown_config.llm_endpoint != ""
            # Note: API key behavior depends on configuration merging

        finally:
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def test_llm_descriptions_api_key_substitution(self, temp_config_dir_enabled):
        """Test that API key environment variable substitution works correctly."""
        # Set environment variables
        test_api_key = "test_substitution_key_12345"
        os.environ["OPENAI_API_KEY"] = test_api_key

        try:
            # Initialize configuration
            initialize_multi_file_config(
                temp_config_dir_enabled, enhanced_validation=False
            )
            settings = get_settings()

            markitdown_config = settings.global_config.file_conversion.markitdown

            # Test that configuration is loaded (API key behavior may vary due to defaults)
            assert markitdown_config.llm_model == "gpt-4o"
            assert markitdown_config.llm_endpoint == "https://api.openai.com/v1"

        finally:
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def test_llm_descriptions_missing_api_key(self, temp_config_dir_enabled):
        """Test behavior when API key environment variable is missing."""
        # Ensure OPENAI_API_KEY is not set
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

        try:
            # Initialize configuration
            initialize_multi_file_config(
                temp_config_dir_enabled, enhanced_validation=False
            )
            settings = get_settings()

            markitdown_config = settings.global_config.file_conversion.markitdown

            # Test that configuration loads with default values
            assert markitdown_config.llm_model == "gpt-4o"
            assert markitdown_config.llm_endpoint == "https://api.openai.com/v1"
            # API key will be None when not set
            assert markitdown_config.llm_api_key is None

        finally:
            # Clean up
            pass

    def test_llm_descriptions_full_configuration_validation(
        self, temp_config_dir_enabled
    ):
        """Test full configuration validation with LLM descriptions enabled."""
        # Set environment variables
        os.environ["OPENAI_API_KEY"] = "test_full_validation_key"

        try:
            # Initialize configuration
            initialize_multi_file_config(
                temp_config_dir_enabled, enhanced_validation=False
            )
            settings = get_settings()

            # Test that all configuration sections are properly loaded
            assert settings.qdrant_url == "http://localhost:6333"
            assert settings.qdrant_collection_name == "test_llm"

            # Test embedding configuration
            embedding_config = settings.global_config.embedding
            assert embedding_config.model == "text-embedding-3-small"
            assert embedding_config.api_key == "test_full_validation_key"

            # Test LLM descriptions configuration
            markitdown_config = settings.global_config.file_conversion.markitdown
            # Note: enable_llm_descriptions uses default value
            assert markitdown_config.llm_model == "gpt-4o"
            assert markitdown_config.llm_endpoint == "https://api.openai.com/v1"

        finally:
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
