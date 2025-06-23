"""Final targeted tests for CLI core module to reach 80% coverage."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from qdrant_loader.cli.core import (
    create_database_directory,
    setup_workspace,
    validate_workspace_flags,
)


class TestCreateDatabaseDirectory:
    """Test database directory creation functionality."""

    def test_create_database_directory_success(self):
        """Test successful database directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "new_db_dir"

            with patch("click.confirm", return_value=True):
                result = create_database_directory(test_path)

            assert result is True
            assert test_path.exists()

    def test_create_database_directory_declined(self):
        """Test database directory creation when user declines."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "new_db_dir"

            with patch("click.confirm", return_value=False):
                result = create_database_directory(test_path)

            assert result is False
            assert not test_path.exists()


class TestSetupWorkspace:
    """Test workspace setup functionality."""

    def test_setup_workspace_existing_directory(self):
        """Test setup workspace with existing directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)

            # Create necessary config file
            config_file = workspace_path / "config.yaml"
            config_file.write_text("projects: {}")

            result = setup_workspace(workspace_path)

            assert result is not None
            assert result.workspace_path == workspace_path.resolve()

    def test_setup_workspace_new_directory(self):
        """Test setup workspace with new directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir) / "new_workspace"
            workspace_path.mkdir()

            # Create necessary config file
            config_file = workspace_path / "config.yaml"
            config_file.write_text("projects: {}")

            result = setup_workspace(workspace_path)

            assert result is not None
            assert result.workspace_path == workspace_path.resolve()
            assert workspace_path.exists()

    def test_setup_workspace_creation_declined(self):
        """Test setup workspace when directory creation is declined."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir) / "new_workspace"

            with patch("click.confirm", return_value=False):
                from click.exceptions import ClickException

                with pytest.raises(ClickException):
                    setup_workspace(workspace_path)


class TestValidateWorkspaceFlags:
    """Test workspace flag validation."""

    def test_validate_workspace_flags_workspace_with_config(self):
        """Test validation fails when workspace used with config."""
        workspace = Path("/test/workspace")
        config = Path("/test/config.yaml")

        from click.exceptions import ClickException

        with pytest.raises(
            ClickException, match="Cannot use --workspace with --config"
        ):
            validate_workspace_flags(workspace, config, None)

    def test_validate_workspace_flags_workspace_with_env(self):
        """Test validation fails when workspace used with env."""
        workspace = Path("/test/workspace")
        env = Path("/test/.env")

        from click.exceptions import ClickException

        with pytest.raises(ClickException, match="Cannot use --workspace with --env"):
            validate_workspace_flags(workspace, None, env)

    def test_validate_workspace_flags_all_valid_combinations(self):
        """Test all valid flag combinations."""
        # Should not raise exceptions
        validate_workspace_flags(None, None, None)
        validate_workspace_flags(Path("/test"), None, None)
        validate_workspace_flags(None, Path("/test/config"), None)
        validate_workspace_flags(None, None, Path("/test/.env"))
        validate_workspace_flags(None, Path("/test/config"), Path("/test/.env"))


class TestWorkspaceConfig:
    """Test workspace configuration functionality."""

    def test_workspace_config_creation(self):
        """Test WorkspaceConfig creation and properties."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)

            # Create necessary files for workspace
            config_file = workspace_root / "config.yaml"
            config_file.write_text("projects: {}")

            # Test the workspace configuration setup
            from qdrant_loader.config.workspace import WorkspaceConfig

            config = WorkspaceConfig(
                workspace_path=workspace_root,
                config_path=config_file,
                config_dir=None,
                env_path=None,
                logs_path=workspace_root / "logs" / "qdrant-loader.log",
                metrics_path=workspace_root / "metrics",
                database_path=workspace_root / "data" / "qdrant-loader.db",
                is_multi_file=False,
            )

            assert config.workspace_path == workspace_root.resolve()
            assert config.config_path == config_file
            assert config.env_path is None


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_create_database_directory_permission_error(self):
        """Test database directory creation with permission error."""
        # Create a path that would cause permission error
        test_path = Path("/root/no_permission_dir")

        from click.exceptions import ClickException

        with (
            patch("click.confirm", return_value=True),
            patch(
                "pathlib.Path.mkdir", side_effect=PermissionError("Permission denied")
            ),
        ):

            with pytest.raises(
                ClickException, match="Failed to create directory: Permission denied"
            ):
                create_database_directory(test_path)

    def test_setup_workspace_mkdir_error(self):
        """Test workspace setup with mkdir error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir) / "new_workspace"

            with (
                patch("click.confirm", return_value=True),
                patch("pathlib.Path.mkdir", side_effect=OSError("Disk full")),
            ):

                from click.exceptions import ClickException

                with pytest.raises(ClickException):
                    setup_workspace(workspace_path)
