"""Enhanced comprehensive tests for CLI commands to achieve 80%+ coverage."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.exceptions import ClickException
from click.testing import CliRunner
from qdrant_loader.cli.cli import (
    _create_database_directory,
    _get_logger,
    _load_config,
    _setup_logging,
    _setup_workspace,
    cli,
)
from qdrant_loader.config.state import DatabaseDirectoryError


class TestCreateDatabaseDirectory:
    """Test database directory creation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_create_database_directory_success_user_confirms(self):
        """Test successful directory creation when user confirms."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "new_db_dir"

            with patch("click.confirm", return_value=True):
                with patch("qdrant_loader.cli.cli._get_logger") as mock_logger:
                    mock_logger.return_value = Mock()

                    result = _create_database_directory(test_path)

                    assert result is True
                    assert test_path.exists()
                    mock_logger.return_value.info.assert_called()

    def test_create_database_directory_user_declines(self):
        """Test directory creation when user declines."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "new_db_dir"

            with patch("click.confirm", return_value=False):
                with patch("qdrant_loader.cli.cli._get_logger") as mock_logger:
                    mock_logger.return_value = Mock()

                    result = _create_database_directory(test_path)

                    assert result is False
                    assert not test_path.exists()

    def test_create_database_directory_handles_relative_path(self):
        """Test directory creation with relative path gets resolved."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp dir and use relative path
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                test_path = Path("relative_db_dir")

                with patch("click.confirm", return_value=True):
                    with patch("qdrant_loader.cli.cli._get_logger") as mock_logger:
                        mock_logger.return_value = Mock()

                        result = _create_database_directory(test_path)

                        assert result is True
                        assert test_path.resolve().exists()
            finally:
                os.chdir(str(original_cwd))

    def test_create_database_directory_nested_path(self):
        """Test directory creation with nested path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "level1" / "level2" / "db_dir"

            with patch("click.confirm", return_value=True):
                with patch("qdrant_loader.cli.cli._get_logger") as mock_logger:
                    mock_logger.return_value = Mock()

                    result = _create_database_directory(test_path)

                    assert result is True
                    assert test_path.exists()

    def test_create_database_directory_exception_handling(self):
        """Test directory creation exception handling."""
        test_path = Path("/invalid/path/that/cannot/be/created")

        with patch("click.confirm", return_value=True):
            with patch("qdrant_loader.cli.cli._get_logger") as mock_logger:
                mock_logger.return_value = Mock()

                with patch(
                    "qdrant_loader.cli.cli._create_db_dir_helper"
                ) as mock_helper:
                    # Force helper to raise exception
                    mock_helper.side_effect = OSError("Permission denied")

                    with pytest.raises(ClickException) as exc_info:
                        _create_database_directory(test_path)

                    assert "Failed to create directory" in str(exc_info.value)

    def test_create_database_directory_existing_directory(self):
        """Test directory creation when directory already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "existing_dir"
            test_path.mkdir()  # Create directory first

            with patch("click.confirm", return_value=True):
                with patch("qdrant_loader.cli.cli._get_logger") as mock_logger:
                    mock_logger.return_value = Mock()

                    result = _create_database_directory(test_path)

                    assert result is True
                    assert test_path.exists()


class TestLoadConfig:
    """Test configuration loading functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_load_config_with_explicit_path_success(self):
        """Test loading config with explicit path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("test: config")
            config_path = Path(f.name)

        try:
            with patch("qdrant_loader.config.initialize_config") as mock_init:
                _load_config(config_path)

                mock_init.assert_called_once_with(
                    config_path, None, skip_validation=False
                )
        finally:
            config_path.unlink()

    def test_load_config_with_explicit_path_not_found(self):
        """Test loading config with non-existent explicit path."""
        config_path = Path("/non/existent/config.yaml")

        with patch("qdrant_loader.cli.cli._get_logger") as mock_logger:
            mock_logger.return_value = Mock()

            with pytest.raises(ClickException) as exc_info:
                _load_config(config_path)

            assert "Config file not found" in str(exc_info.value)

    def test_load_config_default_path_exists(self):
        """Test loading config from default path when it exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                import os

                os.chdir(temp_dir)

                # Create default config.yaml
                default_config = Path("config.yaml")
                default_config.write_text("test: config")

                with patch("qdrant_loader.config.initialize_config") as mock_init:
                    _load_config()

                    mock_init.assert_called_once_with(
                        default_config, None, skip_validation=False
                    )
            finally:
                os.chdir(str(original_cwd))

    def test_load_config_no_config_found(self):
        """Test loading config when no config file is found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                import os

                os.chdir(temp_dir)

                with pytest.raises(ClickException) as exc_info:
                    _load_config()

                assert "No config file found" in str(exc_info.value)
            finally:
                os.chdir(str(original_cwd))

    def test_load_config_with_env_path(self):
        """Test loading config with environment file path."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as config_f:
            config_f.write("test: config")
            config_path = Path(config_f.name)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".env", delete=False
        ) as env_f:
            env_f.write("TEST=value")
            env_path = Path(env_f.name)

        try:
            with patch("qdrant_loader.config.initialize_config") as mock_init:
                _load_config(config_path, env_path)

                mock_init.assert_called_once_with(
                    config_path, env_path, skip_validation=False
                )
        finally:
            config_path.unlink()
            env_path.unlink()

    def test_load_config_skip_validation(self):
        """Test loading config with skip_validation=True."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("test: config")
            config_path = Path(f.name)

        try:
            with patch("qdrant_loader.config.initialize_config") as mock_init:
                _load_config(config_path, skip_validation=True)

                mock_init.assert_called_once_with(
                    config_path, None, skip_validation=True
                )
        finally:
            config_path.unlink()

    def test_load_config_database_directory_error_user_confirms(self):
        """Test loading config with DatabaseDirectoryError when user confirms creation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("test: config")
            config_path = Path(f.name)

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "nonexistent_db"

            try:
                with patch("qdrant_loader.config.initialize_config") as mock_init:
                    # First call raises DatabaseDirectoryError, second succeeds
                    # Create exception properly
                    error = DatabaseDirectoryError(
                        f"Database directory does not exist: {db_path}"
                    )
                    error.path = db_path  # Set path attribute
                    mock_init.side_effect = [error, None]

                    with patch(
                        "qdrant_loader.cli.cli._create_database_directory",
                        return_value=True,
                    ) as mock_create:
                        _load_config(config_path)

                        mock_create.assert_called_once()
                        assert mock_init.call_count == 2
            finally:
                config_path.unlink()

    def test_load_config_database_directory_error_user_declines(self):
        """Test loading config with DatabaseDirectoryError when user declines creation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("test: config")
            config_path = Path(f.name)

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "nonexistent_db"

            try:
                with patch("qdrant_loader.config.initialize_config") as mock_init:
                    error = DatabaseDirectoryError(
                        f"Database directory does not exist: {db_path}"
                    )
                    error.path = db_path
                    mock_init.side_effect = error

                    with patch(
                        "qdrant_loader.cli.cli._create_database_directory",
                        return_value=False,
                    ):
                        with pytest.raises(ClickException) as exc_info:
                            _load_config(config_path)

                        assert "Database directory creation declined" in str(
                            exc_info.value
                        )
            finally:
                config_path.unlink()

    def test_load_config_database_directory_error_skip_validation(self):
        """Test loading config with DatabaseDirectoryError when skip_validation=True."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("test: config")
            config_path = Path(f.name)

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "nonexistent_db"

            try:
                with patch("qdrant_loader.config.initialize_config") as mock_init:
                    error = DatabaseDirectoryError(
                        f"Database directory does not exist: {db_path}"
                    )
                    error.path = db_path
                    mock_init.side_effect = error

                    # Should not raise exception when skip_validation=True
                    _load_config(config_path, skip_validation=True)
            finally:
                config_path.unlink()

    def test_load_config_click_exception_passthrough(self):
        """Test that ClickExceptions are passed through unchanged."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("test: config")
            config_path = Path(f.name)

        try:
            with patch("qdrant_loader.config.initialize_config") as mock_init:
                mock_init.side_effect = ClickException("Test click exception")

                with pytest.raises(ClickException) as exc_info:
                    _load_config(config_path)

                assert "Test click exception" in str(exc_info.value)
        finally:
            config_path.unlink()

    def test_load_config_generic_exception_handling(self):
        """Test loading config with generic exception."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("test: config")
            config_path = Path(f.name)

        try:
            with patch("qdrant_loader.config.initialize_config") as mock_init:
                mock_init.side_effect = ValueError("Test generic error")

                with patch("qdrant_loader.cli.cli._get_logger") as mock_logger:
                    mock_logger.return_value = Mock()

                    with pytest.raises(ClickException) as exc_info:
                        _load_config(config_path)

                    assert "Failed to load configuration" in str(exc_info.value)
                    mock_logger.return_value.error.assert_called()
        finally:
            config_path.unlink()


class TestSetupWorkspace:
    """Test workspace setup functionality."""

    def test_setup_workspace_success(self):
        """Test successful workspace setup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)

            with patch(
                "qdrant_loader.config.workspace.create_workspace_structure"
            ) as mock_create:
                with patch(
                    "qdrant_loader.config.workspace.setup_workspace"
                ) as mock_setup:
                    mock_workspace_config = Mock()
                    mock_workspace_config.workspace_path = workspace_path
                    mock_workspace_config.env_path = workspace_path / ".env"
                    mock_workspace_config.config_path = workspace_path / "config.yaml"
                    mock_setup.return_value = mock_workspace_config

                    result = _setup_workspace(workspace_path)

                    mock_create.assert_called_once_with(workspace_path)
                    mock_setup.assert_called_once_with(workspace_path)
                    assert result is mock_workspace_config

    def test_setup_workspace_no_env_file(self):
        """Test workspace setup when no env file is found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)

            with patch("qdrant_loader.config.workspace.create_workspace_structure"):
                with patch(
                    "qdrant_loader.config.workspace.setup_workspace"
                ) as mock_setup:
                    mock_workspace_config = Mock()
                    mock_workspace_config.workspace_path = workspace_path
                    mock_workspace_config.env_path = None  # No env file
                    mock_workspace_config.config_path = workspace_path / "config.yaml"
                    mock_setup.return_value = mock_workspace_config

                    result = _setup_workspace(workspace_path)

                    assert result is mock_workspace_config

    def test_setup_workspace_no_config_file(self):
        """Test workspace setup when no config file is found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)

            with patch("qdrant_loader.config.workspace.create_workspace_structure"):
                with patch(
                    "qdrant_loader.config.workspace.setup_workspace"
                ) as mock_setup:
                    mock_workspace_config = Mock()
                    mock_workspace_config.workspace_path = workspace_path
                    mock_workspace_config.env_path = workspace_path / ".env"
                    mock_workspace_config.config_path = None  # No config file
                    mock_setup.return_value = mock_workspace_config

                    result = _setup_workspace(workspace_path)

                    assert result is mock_workspace_config

    def test_setup_workspace_exception_handling(self):
        """Test workspace setup exception handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)

            with patch(
                "qdrant_loader.config.workspace.create_workspace_structure"
            ) as mock_create:
                mock_create.side_effect = Exception("Workspace setup failed")

                with pytest.raises(ClickException) as exc_info:
                    _setup_workspace(workspace_path)

                assert "Failed to setup workspace" in str(exc_info.value)


class TestGetLogger:
    """Test logger initialization."""

    def test_get_logger_lazy_initialization(self):
        """Test that logger is lazily initialized."""
        # Reset global logger
        import qdrant_loader.cli.cli as cli_module

        cli_module.logger = None

        with patch(
            "qdrant_loader.utils.logging.LoggingConfig.get_logger"
        ) as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            logger1 = _get_logger()
            logger2 = _get_logger()

            # Should only initialize once
            mock_get_logger.assert_called_once()
            assert logger1 is mock_logger
            assert logger2 is mock_logger

    def test_get_logger_already_initialized(self):
        """Test getting logger when already initialized."""
        # Set global logger
        import qdrant_loader.cli.cli as cli_module

        mock_existing_logger = Mock()
        cli_module.logger = mock_existing_logger

        with patch(
            "qdrant_loader.utils.logging.LoggingConfig.get_logger"
        ) as mock_get_logger:
            logger = _get_logger()

            # Should not call get_logger since already initialized
            mock_get_logger.assert_not_called()
            assert logger is mock_existing_logger


class TestSetupLoggingEnhanced:
    """Enhanced tests for logging setup functionality."""

    def test_setup_logging_with_workspace_config(self):
        """Test logging setup with workspace configuration."""
        mock_workspace_config = Mock()
        mock_workspace_config.logs_path = Path("/workspace/logs/app.log")

        with patch("qdrant_loader.utils.logging.LoggingConfig") as mock_logging_config:
            mock_logger = Mock()
            mock_logging_config.get_logger.return_value = mock_logger

            _setup_logging("DEBUG", mock_workspace_config)

            mock_logging_config.setup.assert_called_once_with(
                level="DEBUG",
                format="console",
                file=str(mock_workspace_config.logs_path),
            )

    def test_setup_logging_without_workspace_config(self):
        """Test logging setup without workspace configuration."""
        with patch("qdrant_loader.utils.logging.LoggingConfig") as mock_logging_config:
            mock_logger = Mock()
            mock_logging_config.get_logger.return_value = mock_logger

            _setup_logging("INFO")

            mock_logging_config.setup.assert_called_once_with(
                level="INFO",
                format="console",
                file="qdrant-loader.log",
            )

    def test_setup_logging_exception_handling(self):
        """Test logging setup exception handling."""
        with patch("qdrant_loader.utils.logging.LoggingConfig.setup") as mock_setup:
            mock_setup.side_effect = Exception("Logging setup failed")

            with pytest.raises(ClickException) as exc_info:
                _setup_logging("INFO")

            assert "Failed to setup logging" in str(exc_info.value)

    def test_setup_logging_updates_global_logger(self):
        """Test that setup_logging updates the global logger."""
        with patch("qdrant_loader.utils.logging.LoggingConfig") as mock_logging_config:
            mock_logger = Mock()
            mock_logging_config.get_logger.return_value = mock_logger

            _setup_logging("INFO")

            # Check that global logger is updated
            import qdrant_loader.cli.cli as cli_module

            assert cli_module.logger is mock_logger


class TestCLICommands:
    """Test CLI command functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_cli_main_command_with_log_level(self):
        """Test main CLI command with log level option."""
        with patch("qdrant_loader.cli.cli._setup_logging"):
            with patch("qdrant_loader.cli.cli._check_for_updates"):
                result = self.runner.invoke(cli, ["--log-level", "DEBUG", "--help"])

                # CLI help should work
                assert result.exit_code == 0
                # Setup logging should be called for the group command
                # but help might exit before other functions are called

    def test_cli_main_command_default_log_level(self):
        """Test main CLI command with default log level."""
        with patch("qdrant_loader.cli.cli._setup_logging"):
            with patch("qdrant_loader.cli.cli._check_for_updates"):
                result = self.runner.invoke(cli, ["--help"])

                # CLI help should work
                assert result.exit_code == 0

    def test_cli_version_option(self):
        """Test CLI version option."""
        # Version is set at import time, so we need to test the actual behavior
        result = self.runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "qDrant Loader v." in result.output

    def test_cli_help_option(self):
        """Test CLI help option."""
        result = self.runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "QDrant Loader CLI" in result.output
