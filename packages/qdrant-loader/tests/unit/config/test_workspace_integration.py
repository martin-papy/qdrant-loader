"""Integration tests for workspace functionality with simplified configuration."""

import os
import tempfile
from pathlib import Path

import pytest
from qdrant_loader.config import get_settings, initialize_config_with_workspace
from qdrant_loader.config.workspace import setup_workspace


class TestWorkspaceIntegration:
    """Integration tests for workspace functionality."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)

            # Create config.yaml
            config_content = """
global:
  qdrant:
    url: "http://localhost:6333"
    api_key: null
    collection_name: "test_workspace"

  chunking:
    chunk_size: 1000
    chunk_overlap: 200
  
  embedding:
    model: "text-embedding-3-small"
    api_key: "${OPENAI_API_KEY}"
    batch_size: 100

  state_management:
    database_path: "${STATE_DB_PATH}"
    table_prefix: "qdrant_loader_"

projects:
  default:
    display_name: "Test Workspace Project"
    description: "Default project for workspace testing"
    sources: {}
"""
            config_file = workspace_path / "config.yaml"
            config_file.write_text(config_content)

            # Create .env file
            env_content = """
OPENAI_API_KEY=test_workspace_api_key
STATE_DB_PATH=/tmp/workspace_test.db
test_key_for_workspace=workspace_value
"""
            env_file = workspace_path / ".env"
            env_file.write_text(env_content)

            yield workspace_path

    def test_workspace_setup(self, temp_workspace):
        """Test workspace setup functionality."""
        workspace_config = setup_workspace(temp_workspace)

        assert workspace_config.workspace_path == temp_workspace.resolve()
        assert (
            workspace_config.config_path == (temp_workspace / "config.yaml").resolve()
        )
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

    def test_workspace_configuration_initialization(self, temp_workspace):
        """Test configuration initialization with workspace."""
        workspace_config = setup_workspace(temp_workspace)

        # Initialize configuration with workspace
        initialize_config_with_workspace(workspace_config, skip_validation=True)
        settings = get_settings()

        # Test configuration access
        assert settings.qdrant_url == "http://localhost:6333"
        assert settings.qdrant_collection_name == "test_workspace"

        # Test that database path was overridden for workspace
        expected_db_path = str(workspace_config.database_path)
        actual_db_path = settings.state_db_path
        assert actual_db_path == expected_db_path

    def test_workspace_environment_variables(self, temp_workspace):
        """Test workspace environment variable loading."""
        workspace_config = setup_workspace(temp_workspace)

        # Store original env vars
        original_openai_key = os.environ.get("OPENAI_API_KEY")
        original_test_key = os.environ.get("test_key_for_workspace")

        try:
            # Initialize configuration with workspace
            initialize_config_with_workspace(workspace_config, skip_validation=True)
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

    def test_workspace_without_env_file(self):
        """Test workspace setup without .env file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)

            # Create config.yaml only
            config_content = """
global:
  qdrant:
    url: "http://localhost:6333"
    api_key: null
    collection_name: "test_no_env"

  state_management:
    database_path: ":memory:"

projects:
  default:
    display_name: "Test No Env Project"
    description: "Default project for testing without env file"
    sources: {}
"""
            config_file = workspace_path / "config.yaml"
            config_file.write_text(config_content)

            workspace_config = setup_workspace(workspace_path)
            assert workspace_config.env_path is None

            # Should still work without .env file
            initialize_config_with_workspace(workspace_config, skip_validation=True)
            settings = get_settings()
            assert settings.qdrant_collection_name == "test_no_env"

    def test_workspace_database_path_override(self, temp_workspace):
        """Test that workspace correctly overrides database path."""
        workspace_config = setup_workspace(temp_workspace)

        # Initialize configuration
        initialize_config_with_workspace(workspace_config, skip_validation=True)
        settings = get_settings()

        # Database path should be workspace-local, not from config
        expected_path = str(workspace_config.database_path)
        actual_path = settings.state_db_path

        assert actual_path == expected_path
        assert actual_path.endswith("qdrant-loader.db")
        assert str(temp_workspace) in actual_path

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
