"""Tests for Settings class qdrant configuration integration."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml
from qdrant_loader.config import Settings


class TestSettingsQdrantIntegration:
    """Test cases for Settings class qdrant configuration integration."""

    def test_settings_requires_qdrant_config(self):
        """Test that Settings requires qdrant configuration in global config."""
        # Create a minimal config without qdrant
        config_data = {
            "global": {
                "chunking": {"chunk_size": 500},
                "embedding": {"model": "test-model"},
            },
            "projects": {
                "default": {
                    "display_name": "Test Project",
                    "description": "Test project for qdrant config testing",
                    "sources": {},
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        # Create minimal env file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("OPENAI_API_KEY=test-key\n")
            f.write("STATE_DB_PATH=/tmp/test.db\n")
            env_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Qdrant configuration is required"):
                Settings.from_yaml(config_path, env_path)
        finally:
            os.unlink(config_path)
            os.unlink(env_path)

    def test_settings_with_valid_qdrant_config(self):
        """Test that Settings works with valid qdrant configuration."""
        config_data = {
            "global": {
                "qdrant": {
                    "url": "http://localhost:6333",
                    "api_key": None,
                    "collection_name": "test_collection",
                },
                "chunking": {"chunk_size": 500},
                "embedding": {"model": "test-model"},
            },
            "projects": {
                "default": {
                    "display_name": "Valid Qdrant Test Project",
                    "description": "Test project for valid qdrant config testing",
                    "sources": {},
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        # Create minimal env file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("OPENAI_API_KEY=test-key\n")
            f.write("STATE_DB_PATH=/tmp/test.db\n")
            env_path = Path(f.name)

        try:
            settings = Settings.from_yaml(config_path, env_path)

            # Verify qdrant configuration is loaded
            assert settings.global_config.qdrant is not None
            assert settings.global_config.qdrant.url == "http://localhost:6333"
            assert settings.global_config.qdrant.api_key is None
            assert settings.global_config.qdrant.collection_name == "test_collection"

        finally:
            os.unlink(config_path)
            os.unlink(env_path)

    def test_qdrant_convenience_properties(self):
        """Test the convenience properties for accessing qdrant configuration."""
        config_data = {
            "global": {
                "qdrant": {
                    "url": "https://cloud.qdrant.io",
                    "api_key": "test-api-key",
                    "collection_name": "production_collection",
                },
                "chunking": {"chunk_size": 500},
                "embedding": {"model": "test-model"},
            },
            "projects": {
                "default": {
                    "display_name": "Convenience Properties Test Project",
                    "description": "Test project for qdrant convenience properties testing",
                    "sources": {},
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        # Create minimal env file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("OPENAI_API_KEY=test-key\n")
            f.write("STATE_DB_PATH=/tmp/test.db\n")
            env_path = Path(f.name)

        try:
            settings = Settings.from_yaml(config_path, env_path)

            # Test convenience properties
            assert settings.qdrant_url == "https://cloud.qdrant.io"
            assert settings.qdrant_api_key == "test-api-key"
            assert settings.qdrant_collection_name == "production_collection"

        finally:
            os.unlink(config_path)
            os.unlink(env_path)

    def test_yaml_loading_with_environment_substitution(self):
        """Test that qdrant configuration supports environment variable substitution."""
        # Set environment variables
        os.environ["TEST_QDRANT_URL"] = "http://test.qdrant.io"
        os.environ["TEST_COLLECTION_NAME"] = "env_collection"

        config_data = {
            "global": {
                "qdrant": {
                    "url": "${TEST_QDRANT_URL}",
                    "api_key": None,
                    "collection_name": "${TEST_COLLECTION_NAME}",
                },
                "chunking": {"chunk_size": 500},
                "embedding": {"model": "test-model"},
            },
            "projects": {
                "default": {
                    "display_name": "Environment Substitution Test Project",
                    "description": "Test project for environment variable substitution testing",
                    "sources": {},
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        # Create minimal env file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("OPENAI_API_KEY=test-key\n")
            f.write("STATE_DB_PATH=/tmp/test.db\n")
            env_path = Path(f.name)

        try:
            settings = Settings.from_yaml(config_path, env_path)

            # Verify environment variables were substituted
            assert settings.qdrant_url == "http://test.qdrant.io"
            assert settings.qdrant_collection_name == "env_collection"

        finally:
            os.unlink(config_path)
            os.unlink(env_path)
            # Clean up environment variables
            del os.environ["TEST_QDRANT_URL"]
            del os.environ["TEST_COLLECTION_NAME"]
