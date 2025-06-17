"""Unit tests for workspace configuration."""


import pytest
from qdrant_loader.config.workspace import (
    WorkspaceConfig,
    setup_workspace,
    validate_workspace_flags,
)


class TestWorkspaceConfig:
    """Test WorkspaceConfig dataclass."""

    def test_workspace_config_validation_success(self, tmp_path):
        """Test successful workspace config validation."""
        # Create test files
        config_file = tmp_path / "config.yaml"
        config_file.write_text("test: config")
        env_file = tmp_path / "env"

        workspace_config = WorkspaceConfig(
            workspace_path=tmp_path,
            config_path=config_file,
            env_path=env_file,
            logs_path=tmp_path / "logs.log",
            metrics_path=tmp_path / "metrics",
            database_path=tmp_path / "db.sqlite",
        )

        assert workspace_config.workspace_path == tmp_path.resolve()
        assert workspace_config.config_path == config_file

    def test_workspace_config_validation_no_directory(self, tmp_path):
        """Test workspace config validation with non-existent directory."""
        non_existent = tmp_path / "non_existent"
        config_file = non_existent / "config.yaml"

        with pytest.raises(ValueError, match="Workspace directory does not exist"):
            WorkspaceConfig(
                workspace_path=non_existent,
                config_path=config_file,
                env_path=None,
                logs_path=non_existent / "logs.log",
                metrics_path=non_existent / "metrics",
                database_path=non_existent / "db.sqlite",
            )

    def test_workspace_config_validation_no_config(self, tmp_path):
        """Test workspace config validation with missing config.yaml."""
        config_file = tmp_path / "config.yaml"
        # Don't create the config file

        with pytest.raises(ValueError, match="config.yaml not found in workspace"):
            WorkspaceConfig(
                workspace_path=tmp_path,
                config_path=config_file,
                env_path=None,
                logs_path=tmp_path / "logs.log",
                metrics_path=tmp_path / "metrics",
                database_path=tmp_path / "db.sqlite",
            )


class TestSetupWorkspace:
    """Test setup_workspace function."""

    def test_setup_workspace_success(self, tmp_path):
        """Test successful workspace setup."""
        # Create config.yaml
        config_file = tmp_path / "config.yaml"
        config_file.write_text("test: config")

        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("TEST=value")

        workspace_config = setup_workspace(tmp_path)

        assert workspace_config.workspace_path == tmp_path.resolve()
        assert workspace_config.config_path == config_file
        assert workspace_config.env_path == env_file
        assert workspace_config.logs_path == tmp_path / "logs" / "qdrant-loader.log"
        assert workspace_config.metrics_path == tmp_path / "metrics"
        assert workspace_config.database_path == tmp_path / "data" / "qdrant-loader.db"

    def test_setup_workspace_no_env_file(self, tmp_path):
        """Test workspace setup without .env file."""
        # Create config.yaml only
        config_file = tmp_path / "config.yaml"
        config_file.write_text("test: config")

        workspace_config = setup_workspace(tmp_path)

        assert workspace_config.env_path is None


class TestValidateWorkspaceFlags:
    """Test validate_workspace_flags function."""

    def test_validate_workspace_flags_workspace_only(self, tmp_path):
        """Test validation with workspace flag only."""
        # Should not raise any exception
        validate_workspace_flags(tmp_path, None, None)

    def test_validate_workspace_flags_workspace_with_config(self, tmp_path):
        """Test validation with conflicting workspace and config flags."""
        config_path = tmp_path / "config.yaml"

        with pytest.raises(
            ValueError, match="Cannot use --workspace with --config flag"
        ):
            validate_workspace_flags(tmp_path, config_path, None)

    def test_validate_workspace_flags_workspace_with_env(self, tmp_path):
        """Test validation with conflicting workspace and env flags."""
        env_path = tmp_path / ".env"

        with pytest.raises(ValueError, match="Cannot use --workspace with --env flag"):
            validate_workspace_flags(tmp_path, None, env_path)
