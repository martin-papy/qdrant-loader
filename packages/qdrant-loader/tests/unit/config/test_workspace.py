"""Tests for the workspace configuration module."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from qdrant_loader.config.workspace import (
    WorkspaceConfig,
    create_workspace_structure,
    get_workspace_env_override,
    setup_workspace,
    validate_workspace,
    validate_workspace_flags,
)


class TestWorkspaceConfig:
    """Test cases for WorkspaceConfig dataclass."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory with required files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)

            # Create config.yaml
            config_file = workspace_path / "config.yaml"
            config_file.write_text("projects: {}")

            # Create basic directory structure
            (workspace_path / "logs").mkdir()
            (workspace_path / "metrics").mkdir()
            (workspace_path / "data").mkdir()

            yield workspace_path

    @pytest.fixture
    def valid_workspace_config_data(self, temp_workspace):
        """Create valid workspace config data."""
        return {
            "workspace_path": temp_workspace,
            "config_path": temp_workspace / "config.yaml",
            "env_path": None,
            "logs_path": temp_workspace / "logs" / "qdrant-loader.log",
            "metrics_path": temp_workspace / "metrics",
            "database_path": temp_workspace / "data" / "qdrant-loader.db",
        }

    def test_workspace_config_initialization(self, valid_workspace_config_data):
        """Test WorkspaceConfig initialization with valid data."""
        with patch("qdrant_loader.config.workspace._get_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            config = WorkspaceConfig(**valid_workspace_config_data)

            assert config.workspace_path.is_absolute()
            assert config.config_path == valid_workspace_config_data["config_path"]
            assert config.env_path is None
            mock_logger.debug.assert_called()

    def test_workspace_config_nonexistent_directory(self):
        """Test WorkspaceConfig with non-existent workspace directory."""
        nonexistent_path = Path("/nonexistent/workspace")

        with pytest.raises(ValueError, match="Workspace directory does not exist"):
            WorkspaceConfig(
                workspace_path=nonexistent_path,
                config_path=nonexistent_path / "config.yaml",
                env_path=None,
                logs_path=nonexistent_path / "logs" / "qdrant-loader.log",
                metrics_path=nonexistent_path / "metrics",
                database_path=nonexistent_path / "data" / "qdrant-loader.db",
            )

    def test_workspace_config_path_is_file(self, temp_workspace):
        """Test WorkspaceConfig with workspace path pointing to a file."""
        file_path = temp_workspace / "somefile.txt"
        file_path.write_text("content")

        with pytest.raises(ValueError, match="Workspace path is not a directory"):
            WorkspaceConfig(
                workspace_path=file_path,
                config_path=temp_workspace / "config.yaml",
                env_path=None,
                logs_path=temp_workspace / "logs" / "qdrant-loader.log",
                metrics_path=temp_workspace / "metrics",
                database_path=temp_workspace / "data" / "qdrant-loader.db",
            )

    def test_workspace_config_missing_config_file(self, temp_workspace):
        """Test WorkspaceConfig with missing config.yaml."""
        # Remove the config file
        (temp_workspace / "config.yaml").unlink()

        with pytest.raises(ValueError, match="config.yaml not found in workspace"):
            WorkspaceConfig(
                workspace_path=temp_workspace,
                config_path=temp_workspace / "config.yaml",
                env_path=None,
                logs_path=temp_workspace / "logs" / "qdrant-loader.log",
                metrics_path=temp_workspace / "metrics",
                database_path=temp_workspace / "data" / "qdrant-loader.db",
            )

    def test_workspace_config_readonly_workspace(self, temp_workspace):
        """Test WorkspaceConfig with read-only workspace."""
        # Mock os.access to return False for write permissions
        with patch("os.access", return_value=False):
            with pytest.raises(ValueError, match="Cannot write to workspace directory"):
                WorkspaceConfig(
                    workspace_path=temp_workspace,
                    config_path=temp_workspace / "config.yaml",
                    env_path=None,
                    logs_path=temp_workspace / "logs" / "qdrant-loader.log",
                    metrics_path=temp_workspace / "metrics",
                    database_path=temp_workspace / "data" / "qdrant-loader.db",
                )

    def test_workspace_config_with_env_path(self, temp_workspace):
        """Test WorkspaceConfig with env_path set."""
        env_file = temp_workspace / ".env"
        env_file.write_text("TEST_VAR=value")

        config = WorkspaceConfig(
            workspace_path=temp_workspace,
            config_path=temp_workspace / "config.yaml",
            env_path=env_file,
            logs_path=temp_workspace / "logs" / "qdrant-loader.log",
            metrics_path=temp_workspace / "metrics",
            database_path=temp_workspace / "data" / "qdrant-loader.db",
        )

        assert config.env_path == env_file


class TestSetupWorkspace:
    """Test cases for setup_workspace function."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory with required files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)

            # Create config.yaml
            config_file = workspace_path / "config.yaml"
            config_file.write_text("projects: {}")

            yield workspace_path

    def test_setup_workspace_success(self, temp_workspace):
        """Test successful workspace setup."""
        with patch("qdrant_loader.config.workspace._get_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            config = setup_workspace(temp_workspace)

            assert isinstance(config, WorkspaceConfig)
            assert config.workspace_path == temp_workspace.resolve()
            assert config.config_path == temp_workspace.resolve() / "config.yaml"
            assert (
                config.logs_path
                == temp_workspace.resolve() / "logs" / "qdrant-loader.log"
            )
            assert config.metrics_path == temp_workspace.resolve() / "metrics"
            assert (
                config.database_path
                == temp_workspace.resolve() / "data" / "qdrant-loader.db"
            )

            # Verify logging
            mock_logger.debug.assert_called()

    def test_setup_workspace_with_env_file(self, temp_workspace):
        """Test workspace setup with existing .env file."""
        env_file = temp_workspace / ".env"
        env_file.write_text("TEST_VAR=value")

        config = setup_workspace(temp_workspace)

        assert config.env_path == env_file.resolve()

    def test_setup_workspace_without_env_file(self, temp_workspace):
        """Test workspace setup without .env file."""
        # Ensure no .env file exists
        env_file = temp_workspace / ".env"
        if env_file.exists():
            env_file.unlink()

        config = setup_workspace(temp_workspace)

        assert config.env_path is None

    def test_setup_workspace_relative_path(self, temp_workspace):
        """Test workspace setup with relative path."""
        # Get relative path
        current_dir = Path.cwd()
        try:
            relative_path = temp_workspace.relative_to(current_dir)
            config = setup_workspace(relative_path)

            # Should be resolved to absolute path
            assert config.workspace_path.is_absolute()
            assert config.workspace_path == temp_workspace.resolve()
        except ValueError:
            # If temp_workspace is not relative to current directory, test with a known relative path
            pytest.skip("Cannot create relative path for this temp directory")

    def test_setup_workspace_invalid_directory(self):
        """Test workspace setup with invalid directory."""
        nonexistent_path = Path("/nonexistent/workspace")

        with pytest.raises(ValueError):
            setup_workspace(nonexistent_path)


class TestValidateWorkspace:
    """Test cases for validate_workspace function."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory with required files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)

            # Create config.yaml
            config_file = workspace_path / "config.yaml"
            config_file.write_text("projects: {}")

            yield workspace_path

    def test_validate_workspace_valid(self, temp_workspace):
        """Test workspace validation with valid workspace."""
        result = validate_workspace(temp_workspace)
        assert result is True

    def test_validate_workspace_invalid(self):
        """Test workspace validation with invalid workspace."""
        nonexistent_path = Path("/nonexistent/workspace")

        with patch("qdrant_loader.config.workspace._get_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            result = validate_workspace(nonexistent_path)

            assert result is False
            mock_logger.debug.assert_called()
            # Check that error was logged
            args, kwargs = mock_logger.debug.call_args
            assert "Workspace validation failed" in args[0]

    def test_validate_workspace_missing_config(self, temp_workspace):
        """Test workspace validation with missing config file."""
        # Remove config file
        (temp_workspace / "config.yaml").unlink()

        result = validate_workspace(temp_workspace)
        assert result is False


class TestCreateWorkspaceStructure:
    """Test cases for create_workspace_structure function."""

    def test_create_workspace_structure_new_directory(self):
        """Test creating workspace structure in new directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir) / "new_workspace"

            with patch("qdrant_loader.config.workspace._get_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
                create_workspace_structure(workspace_path)

                # Verify directories were created
                assert workspace_path.exists()
                assert workspace_path.is_dir()
                assert (workspace_path / "logs").exists()
                assert (workspace_path / "metrics").exists()
                assert (workspace_path / "data").exists()

                # Verify logging
                mock_logger.debug.assert_called()

    def test_create_workspace_structure_existing_directory(self):
        """Test creating workspace structure in existing directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)

            # Pre-create some directories
            (workspace_path / "logs").mkdir()

            create_workspace_structure(workspace_path)

            # Verify all directories exist
            assert (workspace_path / "logs").exists()
            assert (workspace_path / "metrics").exists()
            assert (workspace_path / "data").exists()

    def test_create_workspace_structure_with_parents(self):
        """Test creating workspace structure with parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir) / "parent" / "child" / "workspace"

            create_workspace_structure(workspace_path)

            # Verify nested structure was created
            assert workspace_path.exists()
            assert (workspace_path / "logs").exists()
            assert (workspace_path / "metrics").exists()
            assert (workspace_path / "data").exists()


class TestGetWorkspaceEnvOverride:
    """Test cases for get_workspace_env_override function."""

    def test_get_workspace_env_override(self):
        """Test getting workspace environment overrides."""
        workspace_path = Path("/test/workspace")
        database_path = workspace_path / "data" / "qdrant-loader.db"

        # Mock the __post_init__ validation to avoid directory checks
        with patch.object(WorkspaceConfig, "__post_init__", return_value=None):
            config = WorkspaceConfig(
                workspace_path=workspace_path,
                config_path=workspace_path / "config.yaml",
                env_path=None,
                logs_path=workspace_path / "logs" / "qdrant-loader.log",
                metrics_path=workspace_path / "metrics",
                database_path=database_path,
            )

        with patch("qdrant_loader.config.workspace._get_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            overrides = get_workspace_env_override(config)

            expected = {
                "STATE_DB_PATH": str(database_path),
            }

            assert overrides == expected
            mock_logger.debug.assert_called()

    def test_get_workspace_env_override_with_real_paths(self):
        """Test getting workspace environment overrides with real paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)
            database_path = workspace_path / "data" / "qdrant-loader.db"

            # Create config.yaml file
            config_file = workspace_path / "config.yaml"
            config_file.write_text("projects: {}")

            config = WorkspaceConfig(
                workspace_path=workspace_path,
                config_path=workspace_path / "config.yaml",
                env_path=None,
                logs_path=workspace_path / "logs" / "qdrant-loader.log",
                metrics_path=workspace_path / "metrics",
                database_path=database_path,
            )

            overrides = get_workspace_env_override(config)

            assert "STATE_DB_PATH" in overrides
            assert overrides["STATE_DB_PATH"] == str(database_path)


class TestValidateWorkspaceFlags:
    """Test cases for validate_workspace_flags function."""

    def test_validate_workspace_flags_no_conflicts(self):
        """Test workspace flag validation with no conflicts."""
        with patch("qdrant_loader.config.workspace._get_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            # Test with only workspace
            validate_workspace_flags(
                workspace=Path("/workspace"), config=None, env=None
            )
            mock_logger.debug.assert_called()

    def test_validate_workspace_flags_no_workspace(self):
        """Test workspace flag validation with no workspace flag."""
        # Should not raise any errors
        validate_workspace_flags(
            workspace=None, config=Path("/config.yaml"), env=Path("/.env")
        )

    def test_validate_workspace_flags_workspace_with_config(self):
        """Test workspace flag validation with conflicting config flag."""
        with pytest.raises(
            ValueError, match="Cannot use --workspace with --config flag"
        ):
            validate_workspace_flags(
                workspace=Path("/workspace"), config=Path("/config.yaml"), env=None
            )

    def test_validate_workspace_flags_workspace_with_env(self):
        """Test workspace flag validation with conflicting env flag."""
        with pytest.raises(ValueError, match="Cannot use --workspace with --env flag"):
            validate_workspace_flags(
                workspace=Path("/workspace"), config=None, env=Path("/.env")
            )

    def test_validate_workspace_flags_workspace_with_both(self):
        """Test workspace flag validation with both conflicting flags."""
        # Should raise error for config flag first
        with pytest.raises(
            ValueError, match="Cannot use --workspace with --config flag"
        ):
            validate_workspace_flags(
                workspace=Path("/workspace"),
                config=Path("/config.yaml"),
                env=Path("/.env"),
            )

    def test_validate_workspace_flags_all_none(self):
        """Test workspace flag validation with all flags None."""
        # Should not raise any errors
        validate_workspace_flags(workspace=None, config=None, env=None)
