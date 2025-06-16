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
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Create connectivity.yaml without qdrant
            connectivity_data = {
                "chunking": {"chunk_size": 500},
                "embedding": {
                    "provider": "openai",
                    "model": "test-model",
                    "api_key": "${OPENAI_API_KEY}",
                },
                "state_management": {"database_path": "${STATE_DB_PATH}"},
            }
            connectivity_file = config_dir / "connectivity.yaml"
            connectivity_file.write_text(yaml.dump(connectivity_data))

            # Create projects.yaml
            projects_data = {
                "projects": {
                    "default": {
                        "project_id": "default",
                        "display_name": "Test Project",
                        "description": "Test project for qdrant config testing",
                        "sources": {},
                    }
                }
            }
            projects_file = config_dir / "projects.yaml"
            projects_file.write_text(yaml.dump(projects_data))

            # Create .env file
            env_file = config_dir / ".env"
            env_file.write_text("OPENAI_API_KEY=test-key\nSTATE_DB_PATH=/tmp/test.db\n")

            with pytest.raises(Exception, match="Field required"):
                Settings.from_multi_file(
                    config_dir, env_path=env_file, enhanced_validation=False
                )

    def test_settings_with_valid_qdrant_config(self):
        """Test that Settings works with valid qdrant configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Create connectivity.yaml with qdrant
            connectivity_data = {
                "qdrant": {
                    "url": "http://localhost:6333",
                    "api_key": None,
                    "collection_name": "test_collection",
                },
                "chunking": {"chunk_size": 500},
                "embedding": {
                    "provider": "openai",
                    "model": "test-model",
                    "api_key": "${OPENAI_API_KEY}",
                },
                "state_management": {"database_path": "${STATE_DB_PATH}"},
            }
            connectivity_file = config_dir / "connectivity.yaml"
            connectivity_file.write_text(yaml.dump(connectivity_data))

            # Create projects.yaml
            projects_data = {
                "projects": {
                    "default": {
                        "project_id": "default",
                        "display_name": "Valid Qdrant Test Project",
                        "description": "Test project for valid qdrant config testing",
                        "sources": {},
                    }
                }
            }
            projects_file = config_dir / "projects.yaml"
            projects_file.write_text(yaml.dump(projects_data))

            # Create .env file
            env_file = config_dir / ".env"
            env_file.write_text("OPENAI_API_KEY=test-key\nSTATE_DB_PATH=/tmp/test.db\n")

            settings = Settings.from_multi_file(
                config_dir, env_path=env_file, enhanced_validation=False
            )

            # Verify qdrant configuration is loaded
            assert settings.global_config.qdrant is not None
            assert settings.global_config.qdrant.url == "http://localhost:6333"
            assert settings.global_config.qdrant.api_key is None
            assert settings.global_config.qdrant.collection_name == "test_collection"

    def test_qdrant_convenience_properties(self):
        """Test the convenience properties for accessing qdrant configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Create connectivity.yaml with qdrant
            connectivity_data = {
                "qdrant": {
                    "url": "https://cloud.qdrant.io",
                    "api_key": "test-api-key",
                    "collection_name": "production_collection",
                },
                "chunking": {"chunk_size": 500},
                "embedding": {
                    "provider": "openai",
                    "model": "test-model",
                    "api_key": "${OPENAI_API_KEY}",
                },
                "state_management": {"database_path": "${STATE_DB_PATH}"},
            }
            connectivity_file = config_dir / "connectivity.yaml"
            connectivity_file.write_text(yaml.dump(connectivity_data))

            # Create projects.yaml
            projects_data = {
                "projects": {
                    "default": {
                        "project_id": "default",
                        "display_name": "Convenience Properties Test Project",
                        "description": "Test project for qdrant convenience properties testing",
                        "sources": {},
                    }
                }
            }
            projects_file = config_dir / "projects.yaml"
            projects_file.write_text(yaml.dump(projects_data))

            # Create .env file
            env_file = config_dir / ".env"
            env_file.write_text("OPENAI_API_KEY=test-key\nSTATE_DB_PATH=/tmp/test.db\n")

            settings = Settings.from_multi_file(
                config_dir, env_path=env_file, enhanced_validation=False
            )

            # Test convenience properties
            assert settings.qdrant_url == "https://cloud.qdrant.io"
            assert settings.qdrant_api_key == "test-api-key"
            assert settings.qdrant_collection_name == "production_collection"

    def test_yaml_loading_with_environment_substitution(self):
        """Test that qdrant configuration supports environment variable substitution."""
        # Set environment variables
        os.environ["TEST_QDRANT_URL"] = "http://test.qdrant.io"
        os.environ["TEST_COLLECTION_NAME"] = "env_collection"

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                config_dir = Path(temp_dir)

                # Create connectivity.yaml with environment variables
                connectivity_data = {
                    "qdrant": {
                        "url": "${TEST_QDRANT_URL}",
                        "api_key": None,
                        "collection_name": "${TEST_COLLECTION_NAME}",
                    },
                    "chunking": {"chunk_size": 500},
                    "embedding": {
                        "provider": "openai",
                        "model": "test-model",
                        "api_key": "${OPENAI_API_KEY}",
                    },
                    "state_management": {"database_path": "${STATE_DB_PATH}"},
                }
                connectivity_file = config_dir / "connectivity.yaml"
                connectivity_file.write_text(yaml.dump(connectivity_data))

                # Create projects.yaml
                projects_data = {
                    "projects": {
                        "default": {
                            "project_id": "default",
                            "display_name": "Environment Substitution Test Project",
                            "description": "Test project for environment variable substitution testing",
                            "sources": {},
                        }
                    }
                }
                projects_file = config_dir / "projects.yaml"
                projects_file.write_text(yaml.dump(projects_data))

                # Create .env file
                env_file = config_dir / ".env"
                env_file.write_text(
                    "OPENAI_API_KEY=test-key\nSTATE_DB_PATH=/tmp/test.db\n"
                )

                settings = Settings.from_multi_file(
                    config_dir, env_path=env_file, enhanced_validation=False
                )

                # Verify environment variables were substituted
                assert settings.qdrant_url == "http://test.qdrant.io"
                assert settings.qdrant_collection_name == "env_collection"

        finally:
            # Clean up environment variables
            del os.environ["TEST_QDRANT_URL"]
            del os.environ["TEST_COLLECTION_NAME"]
