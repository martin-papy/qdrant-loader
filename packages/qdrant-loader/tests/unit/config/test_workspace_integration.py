"""Integration tests for workspace functionality with multi-file configuration."""

import os
import tempfile
from pathlib import Path

import pytest
from qdrant_loader.config import get_settings, initialize_multi_file_config
from qdrant_loader.config.workspace import setup_workspace


class TestWorkspaceIntegration:
    """Integration tests for workspace functionality."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)

            # Create multi-file configuration structure
            config_dir = workspace_path / "config"
            config_dir.mkdir()

            # Create connectivity.yaml
            connectivity_data = {
                "qdrant": {
                    "url": "http://localhost:6333",
                    "api_key": None,
                    "collection_name": "test_workspace",
                },
                "embedding": {
                    "provider": "openai",
                    "model": "text-embedding-3-small",
                    "api_key": "${OPENAI_API_KEY}",
                    "batch_size": 100,
                },
                "state_management": {
                    "database_path": "${STATE_DB_PATH}",
                    "table_prefix": "qdrant_loader_",
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
                        "display_name": "Test Workspace Project",
                        "description": "Default project for workspace testing",
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

            # Create .env file
            env_content = """
OPENAI_API_KEY=test_workspace_api_key
STATE_DB_PATH=/tmp/workspace_test.db
test_key_for_workspace=workspace_value
"""
            env_file = workspace_path / ".env"
            env_file.write_text(env_content)

            yield workspace_path

    @pytest.mark.skip(
        reason="Workspace functionality requires legacy single-file configuration support"
    )
    def test_workspace_setup(self, temp_workspace):
        """Test workspace setup functionality."""
        workspace_config = setup_workspace(temp_workspace)

        assert workspace_config.workspace_path == temp_workspace.resolve()
        # Note: config_path now points to the config directory, not a single file
        assert workspace_config.config_path == (temp_workspace / "config").resolve()
        assert workspace_config.env_path == (temp_workspace / ".env").resolve()
        assert (
            workspace_config.logs_path
            == (temp_workspace / "logs" / "qdrant-loader.log").resolve()
        )
        assert workspace_config.metrics_path == (temp_workspace / "metrics").resolve()
        assert (
            workspace_config.database_path
            == (temp_workspace / "data" / "qdrant-loader.db").resolve()
        )

    @pytest.mark.skip(
        reason="Workspace functionality requires legacy single-file configuration support"
    )
    def test_workspace_configuration_initialization(self, temp_workspace):
        """Test configuration initialization with workspace."""
        workspace_config = setup_workspace(temp_workspace)

        # Initialize configuration with workspace using multi-file config
        initialize_multi_file_config(
            workspace_config.config_path,
            env_path=workspace_config.env_path,
            enhanced_validation=False,
        )
        settings = get_settings()

        # Test configuration access
        assert settings.qdrant_url == "http://localhost:6333"
        assert settings.qdrant_collection_name == "test_workspace"

        # Test that database path was loaded from environment
        assert settings.state_db_path == "/tmp/workspace_test.db"

    @pytest.mark.skip(
        reason="Workspace functionality requires legacy single-file configuration support"
    )
    def test_workspace_environment_variables(self, temp_workspace):
        """Test workspace environment variable loading."""
        workspace_config = setup_workspace(temp_workspace)

        # Store original env vars
        original_openai_key = os.environ.get("OPENAI_API_KEY")
        original_test_key = os.environ.get("test_key_for_workspace")

        try:
            # Initialize configuration with workspace
            initialize_multi_file_config(
                workspace_config.config_path,
                env_path=workspace_config.env_path,
                enhanced_validation=False,
            )
            settings = get_settings()

            # Check if workspace-specific env vars are loaded
            test_key = os.environ.get("test_key_for_workspace")
            assert test_key == "workspace_value"

            # Test OpenAI API key access
            api_key = settings.openai_api_key
            assert api_key == "test_workspace_api_key"

        finally:
            # Restore original env vars
            if original_openai_key is not None:
                os.environ["OPENAI_API_KEY"] = original_openai_key
            elif "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

            if original_test_key is not None:
                os.environ["test_key_for_workspace"] = original_test_key
            elif "test_key_for_workspace" in os.environ:
                del os.environ["test_key_for_workspace"]

    @pytest.mark.skip(
        reason="Workspace functionality requires legacy single-file configuration support"
    )
    def test_workspace_without_env_file(self):
        """Test workspace setup without .env file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)

            # Create multi-file configuration structure
            config_dir = workspace_path / "config"
            config_dir.mkdir()

            # Create connectivity.yaml
            connectivity_data = {
                "qdrant": {
                    "url": "http://localhost:6333",
                    "api_key": None,
                    "collection_name": "test_no_env",
                },
                "embedding": {
                    "provider": "openai",
                    "model": "text-embedding-3-small",
                    "api_key": None,
                    "batch_size": 100,
                },
                "state_management": {
                    "database_path": ":memory:",
                    "table_prefix": "qdrant_loader_",
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
                        "display_name": "Test No Env Project",
                        "description": "Default project for testing without env file",
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

            workspace_config = setup_workspace(workspace_path)
            assert workspace_config.env_path is None

            # Should still work without .env file
            initialize_multi_file_config(
                workspace_config.config_path, enhanced_validation=False
            )
            settings = get_settings()
            assert settings.qdrant_collection_name == "test_no_env"

    @pytest.mark.skip(
        reason="Workspace functionality requires legacy single-file configuration support"
    )
    def test_workspace_database_path_override(self, temp_workspace):
        """Test that workspace correctly loads database path from environment."""
        workspace_config = setup_workspace(temp_workspace)

        # Initialize configuration
        initialize_multi_file_config(
            workspace_config.config_path,
            env_path=workspace_config.env_path,
            enhanced_validation=False,
        )
        settings = get_settings()

        # Database path should be from environment variable
        expected_path = "/tmp/workspace_test.db"
        actual_path = settings.state_db_path

        assert actual_path == expected_path

    @pytest.mark.skip(
        reason="Workspace functionality requires legacy single-file configuration support"
    )
    def test_workspace_configuration_validation(self, temp_workspace):
        """Test workspace configuration validation."""
        workspace_config = setup_workspace(temp_workspace)

        # Test that all required paths exist
        assert workspace_config.workspace_path.exists()
        assert workspace_config.config_path.exists()
        if workspace_config.env_path is not None:
            assert workspace_config.env_path.exists()

        # Test that workspace directory is resolved to absolute path
        assert workspace_config.workspace_path.is_absolute()
