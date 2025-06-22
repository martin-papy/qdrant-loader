"""Tests for multi-file configuration mode."""

import os
import tempfile
from pathlib import Path

import pytest
from qdrant_loader.config import get_settings, initialize_multi_file_config


class TestMultiFileConfiguration:
    """Tests for multi-file configuration mode."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory with multi-file structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "config"
            config_dir.mkdir()

            # Create connectivity.yaml
            connectivity_data = {
                "qdrant": {
                    "url": "http://localhost:6333",
                    "api_key": None,
                    "collection_name": "traditional_test",
                },
                "embedding": {
                    "provider": "openai",
                    "model": "text-embedding-3-small",
                    "api_key": "${OPENAI_API_KEY}",
                    "batch_size": 100,
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
                        "enable_llm_descriptions": False,
                    },
                },
            }

            # Create fine-tuning.yaml
            fine_tuning_data = {
                "chunking": {
                    "chunk_size": 1500,
                    "chunk_overlap": 200,
                },
            }

            # Create projects.yaml
            projects_data = {
                "projects": {
                    "default": {
                        "project_id": "default",
                        "display_name": "Traditional Test Project",
                        "description": "Default project for traditional configuration testing",
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

    def test_multi_file_config_initialization(self, temp_config_dir):
        """Test multi-file configuration initialization."""
        # Set required environment variables
        os.environ["OPENAI_API_KEY"] = "traditional_test_key"

        try:
            # Initialize configuration in multi-file mode
            initialize_multi_file_config(temp_config_dir, enhanced_validation=False)
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
            assert settings.global_config.chunking.chunk_size == 1000  # Default value
            assert settings.global_config.chunking.chunk_overlap == 200

        finally:
            # Clean up environment variables
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def test_multi_file_config_environment_expansion(self, temp_config_dir):
        """Test multi-file configuration with environment variable expansion."""
        # Set required environment variables
        os.environ["OPENAI_API_KEY"] = "home_expansion_test_key"

        try:
            # Initialize configuration
            initialize_multi_file_config(temp_config_dir, enhanced_validation=False)
            settings = get_settings()

            # Test that configuration is loaded correctly
            assert settings.qdrant_collection_name == "traditional_test"
            assert settings.state_db_path == ":memory:"
            assert settings.global_config.embedding.api_key == "home_expansion_test_key"

        finally:
            # Clean up environment variables
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
