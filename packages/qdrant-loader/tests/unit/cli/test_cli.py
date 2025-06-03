"""Tests for CLI module."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, mock_open, patch

import pytest
from click.exceptions import ClickException
from click.testing import CliRunner
from qdrant_loader.cli.cli import (
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
            test_path = Path(temp_dir) / "new_db_dir"

            with patch("click.confirm", return_value=True):
                # The function uses click.echo directly, not through a mock
                result = _create_database_directory(test_path)

                assert result is True
                assert test_path.exists()
                assert test_path.stat().st_mode & 0o777 == 0o755

    def test_create_database_directory_declined(self):
        """Test directory creation declined by user."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "new_db_dir"

            with patch("click.confirm", return_value=False):
                result = _create_database_directory(test_path)

                assert result is False
                assert not test_path.exists()

    def test_create_database_directory_exception(self):
        """Test directory creation with exception."""
        # Use a path that will cause permission error
        test_path = Path("/root/forbidden_dir")

        with patch("click.confirm", return_value=True):
            with pytest.raises(ClickException, match="Failed to create directory"):
                _create_database_directory(test_path)


class TestLoadConfig:
    """Test configuration loading functionality."""

    def test_load_config_with_explicit_path(self):
        """Test loading config with explicit path."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            config_path = Path(temp_file.name)

            try:
                with patch("qdrant_loader.config.initialize_config") as mock_init:
                    _load_config(config_path=config_path)
                    mock_init.assert_called_once_with(
                        config_path, None, skip_validation=False
                    )
            finally:
                config_path.unlink()

    def test_load_config_explicit_path_not_found(self):
        """Test loading config with non-existent explicit path."""
        config_path = Path("/non/existent/config.yaml")

        with pytest.raises(ClickException, match="Config file not found"):
            _load_config(config_path=config_path)

    def test_load_config_default_path(self):
        """Test loading config from default path."""
        # Create a real temporary config file
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            config_path = Path(temp_file.name)

        try:
            # Mock Path("config.yaml") to return our temp file path
            with patch("qdrant_loader.cli.cli.Path") as mock_path_class:

                def path_side_effect(path_str):
                    if path_str == "config.yaml":
                        return config_path
                    return Mock()

                mock_path_class.side_effect = path_side_effect

                with patch("qdrant_loader.config.initialize_config") as mock_init:
                    _load_config()
                    mock_init.assert_called_once()
        finally:
            config_path.unlink()

    def test_load_config_no_file_found(self):
        """Test loading config when no file is found."""
        with patch("qdrant_loader.cli.cli.Path") as mock_path_class:
            mock_config_path = Mock()
            mock_config_path.exists.return_value = False
            mock_path_class.return_value = mock_config_path

            with pytest.raises(ClickException, match="No config file found"):
                _load_config()

    def test_load_config_database_directory_error_create(self):
        """Test handling DatabaseDirectoryError with directory creation."""
        # Create a real temporary config file
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            config_path = Path(temp_file.name)

        try:
            with patch("qdrant_loader.config.initialize_config") as mock_init:
                # First call raises DatabaseDirectoryError, second succeeds
                mock_init.side_effect = [
                    DatabaseDirectoryError(path=Path("/tmp/test_db")),
                    None,
                ]

                with patch(
                    "qdrant_loader.cli.cli._create_database_directory",
                    return_value=True,
                ):
                    _load_config(config_path=config_path)
                    assert mock_init.call_count == 2
        finally:
            config_path.unlink()

    def test_load_config_database_directory_error_declined(self):
        """Test handling DatabaseDirectoryError with declined creation."""
        # Create a real temporary config file
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            config_path = Path(temp_file.name)

        try:
            with patch("qdrant_loader.config.initialize_config") as mock_init:
                mock_init.side_effect = DatabaseDirectoryError(
                    path=Path("/tmp/test_db")
                )

                with patch(
                    "qdrant_loader.cli.cli._create_database_directory",
                    return_value=False,
                ):
                    with pytest.raises(
                        ClickException, match="Database directory creation declined"
                    ):
                        _load_config(config_path=config_path)
        finally:
            config_path.unlink()

    def test_load_config_skip_validation(self):
        """Test loading config with skip_validation=True."""
        with patch("qdrant_loader.config.initialize_config") as mock_init:
            mock_init.side_effect = DatabaseDirectoryError(path=Path("/tmp/test_db"))

            # Mock the Path.exists() method to simulate config.yaml exists
            with patch("pathlib.Path.exists", return_value=True):
                # Should not raise exception when skip_validation=True
                _load_config(skip_validation=True)

    def test_load_config_generic_exception(self):
        """Test loading config with generic exception."""
        with patch("qdrant_loader.config.initialize_config") as mock_init:
            mock_init.side_effect = Exception("Generic error")

            # Mock the Path.exists() method to simulate config.yaml exists
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(
                    ClickException, match="Failed to load configuration"
                ):
                    _load_config()


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
        """Test settings check when settings are None."""
        mock_get_settings.return_value = None

        with pytest.raises(ClickException, match="Settings not available"):
            _check_settings()


class TestCliCommands:
    """Test CLI command functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_cli_main_command(self):
        """Test main CLI command."""
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "QDrant Loader CLI" in result.output

    def test_cli_version(self):
        """Test CLI version option."""
        # Don't mock _get_version, just check that the actual version is displayed
        result = self.runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "qDrant Loader v." in result.output

    def test_cli_log_level(self):
        """Test CLI log level option."""
        # The log level is processed during CLI initialization, not in a separate call
        # So we just verify the command runs without error
        result = self.runner.invoke(cli, ["--log-level", "DEBUG", "--help"])
        assert result.exit_code == 0

    @patch("qdrant_loader.cli.cli._setup_logging")
    @patch("qdrant_loader.cli.cli._load_config_with_workspace")
    @patch("qdrant_loader.cli.cli._check_settings")
    def test_config_command(
        self, mock_check_settings, mock_load_config_with_workspace, mock_setup_logging
    ):
        """Test config command."""
        mock_settings = Mock()
        # Mock the model_dump method to return a serializable dict
        mock_settings.model_dump.return_value = {"test": "config", "version": "1.0"}
        mock_check_settings.return_value = mock_settings

        result = self.runner.invoke(cli, ["config"])
        assert result.exit_code == 0
        assert "Current Configuration:" in result.output
        assert '"test": "config"' in result.output

        # _setup_logging is called twice: once by CLI framework, once by config command
        assert mock_setup_logging.call_count == 2
        mock_load_config_with_workspace.assert_called_once_with(
            None, None, None, skip_validation=True
        )
        mock_check_settings.assert_called_once()

    @patch("qdrant_loader.cli.cli._setup_logging")
    @patch("qdrant_loader.cli.cli._load_config_with_workspace")
    def test_config_command_exception(
        self, mock_load_config_with_workspace, mock_setup_logging
    ):
        """Test config command with exception."""
        mock_load_config_with_workspace.side_effect = ClickException("Config error")

        result = self.runner.invoke(cli, ["config"])
        assert result.exit_code == 1
        assert "Config error" in result.output


class TestInitCommand:
    """Test init command functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("qdrant_loader.cli.cli._setup_logging")
    @patch("qdrant_loader.cli.cli._load_config_with_workspace")
    @patch("qdrant_loader.cli.cli._check_settings")
    @patch("qdrant_loader.cli.cli._run_init")
    @patch("qdrant_loader.cli.cli._create_database_directory")
    def test_init_command_success(
        self,
        mock_create_dir,
        mock_run_init,
        mock_check_settings,
        mock_load_config_with_workspace,
        mock_setup_logging,
    ):
        """Test successful init command."""
        mock_settings = Mock()
        mock_settings.global_config.state_management.database_path = "/tmp/test.db"
        mock_check_settings.return_value = mock_settings
        mock_create_dir.return_value = True

        result = self.runner.invoke(cli, ["init"])
        assert result.exit_code == 0

        # _setup_logging is called twice: once by CLI framework, once by init command
        assert mock_setup_logging.call_count == 2
        mock_load_config_with_workspace.assert_called_once()
        mock_check_settings.assert_called_once()

    @patch("qdrant_loader.cli.cli._setup_logging")
    @patch("qdrant_loader.cli.cli._load_config_with_workspace")
    @patch("qdrant_loader.cli.cli._check_settings")
    @patch("qdrant_loader.cli.cli._run_init")
    def test_init_command_memory_database(
        self,
        mock_run_init,
        mock_check_settings,
        mock_load_config_with_workspace,
        mock_setup_logging,
    ):
        """Test init command with memory database."""
        mock_settings = Mock()
        mock_settings.global_config.state_management.database_path = ":memory:"
        mock_check_settings.return_value = mock_settings

        result = self.runner.invoke(cli, ["init"])
        assert result.exit_code == 0

        # _setup_logging is called twice: once by CLI framework, once by init command
        assert mock_setup_logging.call_count == 2
        mock_load_config_with_workspace.assert_called_once()
        mock_check_settings.assert_called_once()

    @patch("qdrant_loader.cli.cli._setup_logging")
    @patch("qdrant_loader.cli.cli._load_config_with_workspace")
    @patch("qdrant_loader.cli.cli._check_settings")
    @patch("qdrant_loader.cli.cli._run_init")
    @patch("qdrant_loader.cli.cli._create_database_directory")
    def test_init_command_force_delete(
        self,
        mock_create_dir,
        mock_run_init,
        mock_check_settings,
        mock_load_config_with_workspace,
        mock_setup_logging,
    ):
        """Test init command with force delete."""
        mock_settings = Mock()
        mock_settings.global_config.state_management.database_path = "/tmp/test.db"
        mock_check_settings.return_value = mock_settings
        mock_create_dir.return_value = True

        with patch("os.path.exists", return_value=True):
            with patch("os.remove") as mock_remove:
                result = self.runner.invoke(cli, ["init", "--force"])
                assert result.exit_code == 0
                mock_remove.assert_called_once_with("/tmp/test.db")

    @patch("qdrant_loader.cli.cli._setup_logging")
    @patch("qdrant_loader.cli.cli._load_config_with_workspace")
    def test_init_command_exception(
        self, mock_load_config_with_workspace, mock_setup_logging
    ):
        """Test init command with exception."""
        mock_load_config_with_workspace.side_effect = ClickException("Init error")

        result = self.runner.invoke(cli, ["init"])
        assert result.exit_code == 1
        assert "Init error" in result.output


class TestIngestCommand:
    """Test ingest command functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("qdrant_loader.cli.cli._setup_logging")
    @patch("qdrant_loader.cli.cli._load_config_with_workspace")
    @patch("qdrant_loader.cli.cli._check_settings")
    @patch("qdrant_loader.core.qdrant_manager.QdrantManager")
    @patch("qdrant_loader.core.async_ingestion_pipeline.AsyncIngestionPipeline")
    def test_ingest_command_success(
        self,
        mock_pipeline_class,
        mock_qdrant_manager,
        mock_check_settings,
        mock_load_config_with_workspace,
        mock_setup_logging,
    ):
        """Test successful ingest command."""
        mock_settings = Mock()
        mock_check_settings.return_value = mock_settings

        mock_pipeline = AsyncMock()
        mock_pipeline_class.return_value = mock_pipeline

        result = self.runner.invoke(cli, ["ingest"])
        assert result.exit_code == 0

        # _setup_logging is called twice: once by CLI framework, once by ingest command
        assert mock_setup_logging.call_count == 2
        mock_load_config_with_workspace.assert_called_once()
        mock_check_settings.assert_called_once()

    @patch("qdrant_loader.cli.cli._setup_logging")
    @patch("qdrant_loader.cli.cli._load_config_with_workspace")
    @patch("qdrant_loader.cli.cli._check_settings")
    @patch("qdrant_loader.core.qdrant_manager.QdrantManager")
    @patch("qdrant_loader.core.async_ingestion_pipeline.AsyncIngestionPipeline")
    def test_ingest_command_with_source_filters(
        self,
        mock_pipeline_class,
        mock_qdrant_manager,
        mock_check_settings,
        mock_load_config_with_workspace,
        mock_setup_logging,
    ):
        """Test ingest command with source filters."""
        mock_settings = Mock()
        mock_check_settings.return_value = mock_settings

        mock_pipeline = AsyncMock()
        mock_pipeline_class.return_value = mock_pipeline

        result = self.runner.invoke(
            cli, ["ingest", "--source-type", "git", "--source", "test-repo"]
        )
        assert result.exit_code == 0

        # _setup_logging is called twice: once by CLI framework, once by ingest command
        assert mock_setup_logging.call_count == 2
        mock_load_config_with_workspace.assert_called_once()
        mock_check_settings.assert_called_once()

    @patch("qdrant_loader.cli.cli._setup_logging")
    @patch("qdrant_loader.cli.cli._load_config_with_workspace")
    @patch("qdrant_loader.cli.cli._check_settings")
    @patch("qdrant_loader.core.qdrant_manager.QdrantManager")
    @patch("qdrant_loader.core.async_ingestion_pipeline.AsyncIngestionPipeline")
    def test_ingest_command_with_profiling(
        self,
        mock_pipeline_class,
        mock_qdrant_manager,
        mock_check_settings,
        mock_load_config_with_workspace,
        mock_setup_logging,
    ):
        """Test ingest command with profiling."""
        mock_settings = Mock()
        mock_check_settings.return_value = mock_settings

        mock_pipeline = AsyncMock()
        mock_pipeline_class.return_value = mock_pipeline

        with patch("cProfile.Profile") as mock_profile:
            mock_profiler = Mock()
            mock_profile.return_value = mock_profiler

            result = self.runner.invoke(cli, ["ingest", "--profile"])
            assert result.exit_code == 0

            mock_profiler.enable.assert_called_once()
            mock_profiler.disable.assert_called_once()
            mock_profiler.dump_stats.assert_called_once_with("profile.out")

    @patch("qdrant_loader.cli.cli._setup_logging")
    @patch("qdrant_loader.cli.cli._load_config_with_workspace")
    def test_ingest_command_exception(
        self, mock_load_config_with_workspace, mock_setup_logging
    ):
        """Test ingest command with exception."""
        mock_load_config_with_workspace.side_effect = ClickException("Ingest error")

        result = self.runner.invoke(cli, ["ingest"])
        assert result.exit_code == 1
        assert "Ingest error" in result.output


class TestRunInit:
    """Test async init functionality."""

    @pytest.mark.asyncio
    @patch("qdrant_loader.core.init_collection.init_collection")
    async def test_run_init_success(self, mock_init_collection):
        """Test successful async init."""
        mock_settings = Mock()
        mock_init_collection.return_value = True

        await _run_init(mock_settings, force=False)

        mock_init_collection.assert_called_once_with(mock_settings, False)

    @pytest.mark.asyncio
    @patch("qdrant_loader.core.init_collection.init_collection")
    async def test_run_init_failure(self, mock_init_collection):
        """Test async init failure."""
        mock_settings = Mock()
        mock_init_collection.return_value = False

        with pytest.raises(ClickException, match="Failed to initialize collection"):
            await _run_init(mock_settings, force=False)

    @pytest.mark.asyncio
    @patch("qdrant_loader.core.init_collection.init_collection")
    async def test_run_init_exception(self, mock_init_collection):
        """Test async init with exception."""
        mock_settings = Mock()
        mock_init_collection.side_effect = Exception("Init failed")

        with pytest.raises(ClickException, match="Failed to initialize collection"):
            await _run_init(mock_settings, force=False)


class TestCancelAllTasks:
    """Test task cancellation functionality."""

    @pytest.mark.asyncio
    async def test_cancel_all_tasks(self):
        """Test cancelling all tasks."""
        # Mock asyncio.all_tasks and asyncio.gather to avoid creating real tasks
        with patch("asyncio.all_tasks") as mock_all_tasks:
            with patch("asyncio.gather") as mock_gather:
                # Create mock tasks
                task1 = Mock()
                task1.done.return_value = False
                task2 = Mock()
                task2.done.return_value = True  # Already done
                task3 = Mock()
                task3.done.return_value = False

                mock_all_tasks.return_value = [task1, task2, task3]

                # Make gather return an awaitable
                async def mock_gather_result():
                    return []

                mock_gather.return_value = mock_gather_result()

                # Import and test the function
                from qdrant_loader.cli.cli import _cancel_all_tasks

                # Execute
                await _cancel_all_tasks()

                # Verify only non-done tasks were cancelled
                task1.cancel.assert_called_once()
                task2.cancel.assert_not_called()  # Already done
                task3.cancel.assert_called_once()

                # Verify gather was called with non-done tasks
                mock_gather.assert_called_once_with(
                    task1, task3, return_exceptions=True
                )
