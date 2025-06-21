"""Targeted tests for ingest_commands.py to improve coverage.

Focuses on uncovered error paths, edge cases, and command flows.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from qdrant_loader.cli.ingest_commands import (
    check_status,
    init,
    init_command,
    ingest_command,
    run_ingest,
    run_init,
)


@pytest.fixture
def runner():
    """Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_settings():
    """Mock settings object."""
    settings = Mock()
    settings.qdrant_collection_name = "test_collection"
    settings.global_config.state_management.database_path = "/tmp/test.db"
    settings.projects = {"test_project": Mock()}
    return settings


class TestRunInitFunction:
    """Test the run_init async function."""

    @pytest.mark.asyncio
    async def test_run_init_success(self, mock_settings):
        """Test successful initialization."""
        with patch("qdrant_loader.cli.ingest_commands.init_collection") as mock_init, \
             patch("qdrant_loader.cli.ingest_commands.get_logger") as mock_logger:
            
            mock_init.return_value = True
            logger = Mock()
            mock_logger.return_value = logger

            await run_init(mock_settings, force=False)

            mock_init.assert_called_once_with(mock_settings, False)
            logger.info.assert_called_once_with(
                "Collection initialized successfully",
                collection="test_collection"
            )

    @pytest.mark.asyncio
    async def test_run_init_success_with_force(self, mock_settings):
        """Test successful initialization with force flag."""
        with patch("qdrant_loader.cli.ingest_commands.init_collection") as mock_init, \
             patch("qdrant_loader.cli.ingest_commands.get_logger") as mock_logger:
            
            mock_init.return_value = True
            logger = Mock()
            mock_logger.return_value = logger

            await run_init(mock_settings, force=True)

            mock_init.assert_called_once_with(mock_settings, True)
            logger.info.assert_called_once_with(
                "Collection recreated successfully",
                collection="test_collection"
            )

    @pytest.mark.asyncio
    async def test_run_init_failure(self, mock_settings):
        """Test initialization failure."""
        with patch("qdrant_loader.cli.ingest_commands.init_collection") as mock_init, \
             patch("qdrant_loader.cli.ingest_commands.get_logger"):
            
            mock_init.return_value = False

            with pytest.raises(Exception) as exc_info:
                await run_init(mock_settings, force=False)
            
            assert "Failed to initialize collection" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_run_init_exception(self, mock_settings):
        """Test initialization with exception."""
        with patch("qdrant_loader.cli.ingest_commands.init_collection") as mock_init, \
             patch("qdrant_loader.cli.ingest_commands.get_logger") as mock_logger:
            
            mock_init.side_effect = Exception("Init error")
            logger = Mock()
            mock_logger.return_value = logger

            with pytest.raises(Exception) as exc_info:
                await run_init(mock_settings, force=False)
            
            assert "Failed to initialize collection: Init error" in str(exc_info.value)
            logger.error.assert_called_once()


class TestInitCommand:
    """Test the init command."""

    def test_init_basic_success(self, runner, mock_settings):
        """Test basic init command success."""
        with patch("qdrant_loader.cli.ingest_commands.validate_workspace_flags"), \
             patch("qdrant_loader.cli.ingest_commands.setup_logging"), \
             patch("qdrant_loader.cli.ingest_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.ingest_commands.check_settings") as mock_check, \
             patch("qdrant_loader.cli.ingest_commands.run_init") as mock_run_init:
            
            mock_check.return_value = mock_settings
            mock_run_init.return_value = None  # Async function completion

            result = runner.invoke(init, [])

            assert result.exit_code == 0

    def test_init_with_force_flag(self, runner, mock_settings):
        """Test init command with force flag."""
        with patch("qdrant_loader.cli.ingest_commands.validate_workspace_flags"), \
             patch("qdrant_loader.cli.ingest_commands.setup_logging"), \
             patch("qdrant_loader.cli.ingest_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.ingest_commands.check_settings") as mock_check, \
             patch("qdrant_loader.cli.ingest_commands.run_init") as mock_run_init:
            
            mock_check.return_value = mock_settings
            mock_run_init.return_value = None

            result = runner.invoke(init, ["--force"])

            assert result.exit_code == 0

    def test_init_database_directory_creation(self, runner, mock_settings):
        """Test init command with database directory creation."""
        mock_settings.global_config.state_management.database_path = "/tmp/nonexistent/test.db"
        
        with patch("qdrant_loader.cli.ingest_commands.validate_workspace_flags"), \
             patch("qdrant_loader.cli.ingest_commands.setup_logging"), \
             patch("qdrant_loader.cli.ingest_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.ingest_commands.check_settings") as mock_check, \
             patch("qdrant_loader.cli.ingest_commands.run_init") as mock_run_init, \
             patch("qdrant_loader.cli.ingest_commands.create_database_directory") as mock_create_dir, \
             patch("os.path.exists") as mock_exists:
            
            mock_check.return_value = mock_settings
            mock_run_init.return_value = None
            mock_create_dir.return_value = True
            mock_exists.return_value = False

            result = runner.invoke(init, ["--force"])

            assert result.exit_code == 0
            mock_create_dir.assert_called_once()

    def test_init_database_directory_creation_declined(self, runner, mock_settings):
        """Test init command when database directory creation is declined."""
        mock_settings.global_config.state_management.database_path = "/tmp/nonexistent/test.db"
        
        with patch("qdrant_loader.cli.ingest_commands.validate_workspace_flags"), \
             patch("qdrant_loader.cli.ingest_commands.setup_logging"), \
             patch("qdrant_loader.cli.ingest_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.ingest_commands.check_settings") as mock_check, \
             patch("qdrant_loader.cli.ingest_commands.create_database_directory") as mock_create_dir:
            
            mock_check.return_value = mock_settings
            mock_create_dir.return_value = False

            result = runner.invoke(init, ["--force"])

            assert result.exit_code == 1
            assert "Database directory creation declined" in result.output


class TestRunIngestCommand:
    """Test the run_ingest command."""

    def test_run_ingest_basic(self, runner, mock_settings):
        """Test basic run ingest command."""
        with patch("qdrant_loader.cli.ingest_commands.validate_workspace_flags"), \
             patch("qdrant_loader.cli.ingest_commands.setup_logging"), \
             patch("qdrant_loader.cli.ingest_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.ingest_commands.check_settings") as mock_check, \
             patch("qdrant_loader.cli.ingest_commands.IngestionManager") as mock_manager:
            
            mock_check.return_value = mock_settings
            mock_instance = Mock()
            mock_instance.run_ingestion = AsyncMock()
            mock_manager.return_value = mock_instance

            result = runner.invoke(run_ingest, [])

            assert result.exit_code == 0

    def test_run_ingest_with_project_filter(self, runner, mock_settings):
        """Test run ingest with project filter."""
        with patch("qdrant_loader.cli.ingest_commands.validate_workspace_flags"), \
             patch("qdrant_loader.cli.ingest_commands.setup_logging"), \
             patch("qdrant_loader.cli.ingest_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.ingest_commands.check_settings") as mock_check, \
             patch("qdrant_loader.cli.ingest_commands.IngestionManager") as mock_manager:
            
            mock_check.return_value = mock_settings
            mock_instance = Mock()
            mock_instance.run_ingestion = AsyncMock()
            mock_manager.return_value = mock_instance

            result = runner.invoke(run_ingest, ["--project", "test_project"])

            assert result.exit_code == 0

    def test_run_ingest_with_profiling(self, runner, mock_settings):
        """Test run ingest with profiling enabled."""
        with patch("qdrant_loader.cli.ingest_commands.validate_workspace_flags"), \
             patch("qdrant_loader.cli.ingest_commands.setup_logging"), \
             patch("qdrant_loader.cli.ingest_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.ingest_commands.check_settings") as mock_check, \
             patch("qdrant_loader.cli.ingest_commands.IngestionManager") as mock_manager, \
             patch("cProfile.Profile") as mock_profiler:
            
            mock_check.return_value = mock_settings
            mock_instance = Mock()
            mock_instance.run_ingestion = AsyncMock()
            mock_manager.return_value = mock_instance
            
            mock_prof_instance = Mock()
            mock_profiler.return_value = mock_prof_instance

            result = runner.invoke(run_ingest, ["--profile"])

            assert result.exit_code == 0
            mock_prof_instance.enable.assert_called_once()
            mock_prof_instance.disable.assert_called_once()
            mock_prof_instance.dump_stats.assert_called_once_with("profile.out")


class TestCheckStatusCommand:
    """Test the check_status command."""

    def test_check_status_basic(self, runner, mock_settings):
        """Test basic status check."""
        with patch("qdrant_loader.cli.ingest_commands.validate_workspace_flags"), \
             patch("qdrant_loader.cli.ingest_commands.setup_logging"), \
             patch("qdrant_loader.cli.ingest_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.ingest_commands.check_settings") as mock_check, \
             patch("qdrant_loader.cli.ingest_commands.IngestStatusChecker") as mock_checker:
            
            mock_check.return_value = mock_settings
            mock_instance = Mock()
            mock_checker.return_value = mock_instance

            result = runner.invoke(check_status, [])

            assert result.exit_code == 0

    def test_check_status_with_project(self, runner, mock_settings):
        """Test status check for specific project."""
        with patch("qdrant_loader.cli.ingest_commands.validate_workspace_flags"), \
             patch("qdrant_loader.cli.ingest_commands.setup_logging"), \
             patch("qdrant_loader.cli.ingest_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.ingest_commands.check_settings") as mock_check, \
             patch("qdrant_loader.cli.ingest_commands.IngestStatusChecker") as mock_checker:
            
            mock_check.return_value = mock_settings
            mock_instance = Mock()
            mock_checker.return_value = mock_instance

            result = runner.invoke(check_status, ["--project", "test_project"])

            assert result.exit_code == 0


class TestStandaloneCommands:
    """Test standalone command functions."""

    def test_ingest_command_basic(self, runner, mock_settings):
        """Test standalone ingest command."""
        with patch("qdrant_loader.cli.ingest_commands.validate_workspace_flags"), \
             patch("qdrant_loader.cli.ingest_commands.setup_logging"), \
             patch("qdrant_loader.cli.ingest_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.ingest_commands.check_settings") as mock_check, \
             patch("qdrant_loader.cli.ingest_commands.IngestionManager") as mock_manager:
            
            mock_check.return_value = mock_settings
            mock_instance = Mock()
            mock_instance.run_ingestion = AsyncMock()
            mock_manager.return_value = mock_instance

            result = runner.invoke(ingest_command, [])

            assert result.exit_code == 0

    def test_init_command_basic(self, runner, mock_settings):
        """Test standalone init command."""
        with patch("qdrant_loader.cli.ingest_commands.validate_workspace_flags"), \
             patch("qdrant_loader.cli.ingest_commands.setup_logging"), \
             patch("qdrant_loader.cli.ingest_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.ingest_commands.check_settings") as mock_check, \
             patch("qdrant_loader.cli.ingest_commands.run_init") as mock_run_init:
            
            mock_check.return_value = mock_settings
            mock_run_init.return_value = None

            result = runner.invoke(init_command, [])

            assert result.exit_code == 0


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_init_click_exception_handling(self, runner):
        """Test init command Click exception handling."""
        with patch("qdrant_loader.cli.ingest_commands.validate_workspace_flags") as mock_validate:
            mock_validate.side_effect = Exception("Validation error")

            result = runner.invoke(init, [])

            assert result.exit_code == 1
            assert "Failed to initialize collection" in result.output

    def test_run_ingest_exception_handling(self, runner):
        """Test run ingest command exception handling."""
        with patch("qdrant_loader.cli.ingest_commands.validate_workspace_flags") as mock_validate:
            mock_validate.side_effect = Exception("Validation error")

            result = runner.invoke(run_ingest, [])

            assert result.exit_code == 1
            assert "Validation error" in result.output

    def test_check_status_exception_handling(self, runner):
        """Test check status command exception handling."""
        with patch("qdrant_loader.cli.ingest_commands.validate_workspace_flags") as mock_validate:
            mock_validate.side_effect = Exception("Validation error")

            result = runner.invoke(check_status, [])

            assert result.exit_code == 1
            assert "Validation error" in result.output
