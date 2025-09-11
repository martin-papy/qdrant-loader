"""Tests for CLI module."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.exceptions import ClickException
from click.testing import CliRunner
from qdrant_loader.cli.cli import (
    _check_for_updates,
    _check_settings,
    _create_database_directory,
    _get_version,
    _load_config,
    _run_init,
    _setup_logging,
    cli,
)
from qdrant_loader.config.state import DatabaseDirectoryError


class TestGetVersion:
    """Test version retrieval functionality."""

    @patch("importlib.metadata.version")
    def test_get_version_success(self, mock_version):
        """Test successful version retrieval."""
        mock_version.return_value = "1.2.3"

        version = _get_version()
        assert version == "1.2.3"
        mock_version.assert_called_once_with("qdrant-loader")

    @patch("importlib.metadata.version")
    def test_get_version_fallback(self, mock_version):
        """Test version fallback when package not found."""
        from importlib.metadata import PackageNotFoundError

        mock_version.side_effect = PackageNotFoundError("qdrant-loader")

        version = _get_version()
        assert version == "unknown"
        mock_version.assert_called_once_with("qdrant-loader")

    @patch("importlib.metadata.version")
    def test_get_version_exception_handling(self, mock_version):
        """Test version retrieval with generic exception."""
        mock_version.side_effect = Exception("Some error")

        version = _get_version()
        assert version == "unknown"
        mock_version.assert_called_once_with("qdrant-loader")

    def test_get_version_import_error(self):
        """Test version retrieval when importlib.metadata is not available."""
        # Mock the import to fail by making the import statement raise ImportError
        with patch(
            "builtins.__import__",
            side_effect=ImportError("No module named 'importlib.metadata'"),
        ):
            version = _get_version()
            assert version == "unknown"


class TestCheckForUpdates:
    """Test version update checking functionality."""

    @patch("qdrant_loader.utils.version_check.check_version_async")
    @patch("qdrant_loader.cli.cli._get_version")
    def test_check_for_updates_enabled(self, mock_get_version, mock_check_async):
        """Test version check when enabled."""
        mock_get_version.return_value = "1.0.0"

        _check_for_updates()

        mock_get_version.assert_called_once()
        mock_check_async.assert_called_once_with("1.0.0", silent=False)

    def test_check_for_updates_exception(self):
        """Test version check with exception (should not raise)."""
        with patch(
            "qdrant_loader.utils.version_check.check_version_async",
            side_effect=Exception("Import error"),
        ):
            # Should not raise exception
            _check_for_updates()


class TestSetupLogging:
    """Test logging setup functionality."""

    @patch("qdrant_loader.utils.logging.LoggingConfig")
    def test_setup_logging_success(self, mock_logging_config):
        """Test successful logging setup."""
        mock_logger = Mock()
        mock_logging_config.get_logger.return_value = mock_logger

        _setup_logging("DEBUG")

        mock_logging_config.setup.assert_called_once_with(
            level="DEBUG", format="console", file="qdrant-loader.log"
        )
        mock_logging_config.get_logger.assert_called()

    @patch("qdrant_loader.utils.logging.LoggingConfig")
    def test_setup_logging_exception(self, mock_logging_config):
        """Test logging setup with exception."""
        mock_logging_config.setup.side_effect = Exception("Logging setup failed")

        with pytest.raises(ClickException, match="Failed to setup logging"):
            _setup_logging("INFO")


class TestCreateDatabaseDirectory:
    """Test database directory creation functionality."""

    def test_create_database_directory_success(self):
        """Test successful directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "test_db"

            with patch("click.confirm", return_value=True):
                result = _create_database_directory(test_path)

            assert result is True
            assert test_path.exists()

    def test_create_database_directory_declined(self):
        """Test directory creation when user declines."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "test_db"

            with patch("click.confirm", return_value=False):
                result = _create_database_directory(test_path)

            assert result is False
            assert not test_path.exists()

    def test_create_database_directory_exception(self):
        """Test directory creation with exception."""
        test_path = Path("/invalid/path/that/cannot/be/created")

        with patch("click.confirm", return_value=True):
            with pytest.raises(ClickException, match="Failed to create directory"):
                _create_database_directory(test_path)


class TestLoadConfig:
    """Test configuration loading functionality."""

    def test_load_config_with_existing_file(self):
        """Test loading config with existing file."""
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

    def test_load_config_file_not_found(self):
        """Test loading config with non-existent file."""
        config_path = Path("/non/existent/config.yaml")

        with pytest.raises(ClickException, match="Config file not found"):
            _load_config(config_path)

    def test_load_config_default_file_exists(self):
        """Test loading config with default file existing."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("qdrant_loader.config.initialize_config") as mock_init:
                _load_config()
                mock_init.assert_called_once_with(
                    Path("config.yaml"), None, skip_validation=False
                )

    def test_load_config_no_file_found(self):
        """Test loading config when no file is found."""
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(ClickException, match="No config file found"):
                _load_config()

    def test_load_config_database_directory_error(self):
        """Test loading config with database directory error."""
        config_path = Path("config.yaml")

        # Mock the first call to raise the error, second call to succeed
        mock_init = Mock()
        mock_init.side_effect = [
            DatabaseDirectoryError(Path("/test/path")),
            None,  # Second call succeeds
        ]

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("qdrant_loader.config.initialize_config", mock_init),
            patch("click.confirm", return_value=True),
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("os.path.expanduser", return_value="/test/path"),
        ):
            # This should not raise an exception since we're creating the directory
            _load_config(config_path)
            mock_mkdir.assert_called_once()
            # Should be called twice - first fails, second succeeds
            assert mock_init.call_count == 2

    def test_load_config_database_directory_error_declined(self):
        """Test loading config with database directory error when user declines."""
        config_path = Path("config.yaml")

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "qdrant_loader.config.initialize_config",
                side_effect=DatabaseDirectoryError(Path("/test/path")),
            ),
            patch("click.confirm", return_value=False),
        ):
            with pytest.raises(
                ClickException, match="Database directory creation declined"
            ):
                _load_config(config_path)


class TestCheckSettings:
    """Test settings checking functionality."""

    @patch("qdrant_loader.config.get_settings")
    def test_check_settings_success(self, mock_get_settings):
        """Test successful settings check."""
        mock_settings = Mock()
        mock_get_settings.return_value = mock_settings

        result = _check_settings()
        assert result == mock_settings

    @patch("qdrant_loader.config.get_settings")
    def test_check_settings_none(self, mock_get_settings):
        """Test settings check when settings is None."""
        mock_get_settings.return_value = None

        with pytest.raises(ClickException, match="Settings not available"):
            _check_settings()


class TestRunInit:
    """Test initialization functionality."""

    @pytest.mark.asyncio
    async def test_run_init_success(self):
        """Test successful initialization."""
        mock_settings = Mock()
        mock_settings.qdrant_collection_name = "test_collection"

        with patch("qdrant_loader.core.init_collection.init_collection") as mock_init:
            mock_init.return_value = True
            await _run_init(mock_settings, False)
            mock_init.assert_called_once_with(mock_settings, False)

    @pytest.mark.asyncio
    async def test_run_init_failure(self):
        """Test initialization failure."""
        mock_settings = Mock()

        with patch("qdrant_loader.core.init_collection.init_collection") as mock_init:
            mock_init.return_value = False
            with pytest.raises(ClickException, match="Failed to initialize collection"):
                await _run_init(mock_settings, False)

    @pytest.mark.asyncio
    async def test_run_init_exception(self):
        """Test initialization with exception."""
        mock_settings = Mock()

        with patch(
            "qdrant_loader.core.init_collection.init_collection",
            side_effect=Exception("Init error"),
        ):
            with pytest.raises(ClickException, match="Failed to initialize collection"):
                await _run_init(mock_settings, False)


class TestCLIIntegration:
    """Test CLI integration functionality."""

    def test_cli_calls_version_check(self):
        """Test that CLI calls version check on startup."""
        runner = CliRunner()

        with patch("qdrant_loader.cli.cli._check_for_updates") as mock_check_updates:
            # Run the CLI with config command to trigger the main CLI function
            # This will fail due to missing config, but the CLI function will be called
            runner.invoke(cli, ["config"])

            # Verify that version check was called
            mock_check_updates.assert_called_once()

    def test_cli_handles_version_check_exception(self):
        """Test that CLI handles version check exceptions gracefully."""
        runner = CliRunner()

        with patch(
            "qdrant_loader.cli.cli._check_for_updates",
            side_effect=Exception("Version check error"),
        ) as mock_check_updates:
            # Should not raise exception even if version check fails
            runner.invoke(cli, ["config"])

            # CLI should still work (even though config command will fail)
            # The important thing is that the version check exception doesn't break the CLI
            mock_check_updates.assert_called_once()
