"""Targeted tests for ingest_commands.py to improve coverage.

Focuses on uncovered error paths, edge cases, and command flows.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, mock_open, patch

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
    settings = MagicMock()
    settings.qdrant_collection_name = "test_collection"
    settings.global_config.state_management.database_path = "/tmp/test.db"
    settings.projects = {"test_project": MagicMock()}
    return settings


class TestRunInitFunction:
    """Test the run_init async function."""

    @pytest.mark.asyncio
    async def test_run_init_success(self):
        """Test successful run_init execution."""
        mock_settings = MagicMock()
        mock_settings.qdrant_collection_name = "test_collection"

        with patch("qdrant_loader.cli.ingest_commands.init_collection") as mock_init, \
             patch("qdrant_loader.cli.ingest_commands.get_logger") as mock_logger:
            
            mock_init.return_value = True
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance

            await run_init(mock_settings, force=False)

            mock_init.assert_called_once_with(mock_settings, False)
            mock_logger_instance.info.assert_called()

    @pytest.mark.asyncio
    async def test_run_init_success_with_force(self):
        """Test successful run_init with force flag."""
        mock_settings = MagicMock()
        mock_settings.qdrant_collection_name = "test_collection"

        with patch("qdrant_loader.cli.ingest_commands.init_collection") as mock_init, \
             patch("qdrant_loader.cli.ingest_commands.get_logger") as mock_logger:
            
            mock_init.return_value = True
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance

            await run_init(mock_settings, force=True)

            mock_init.assert_called_once_with(mock_settings, True)
            mock_logger_instance.info.assert_called()

    @pytest.mark.asyncio
    async def test_run_init_failure(self):
        """Test run_init when init_collection returns False."""
        mock_settings = MagicMock()

        with patch("qdrant_loader.core.init_collection.init_collection") as mock_init, \
             patch("qdrant_loader.cli.ingest_commands.get_logger"):
            
            mock_init.return_value = False

            from qdrant_loader.cli.ingest_commands import run_init
            from click.exceptions import ClickException

            with pytest.raises(ClickException):
                await run_init(mock_settings, force=False)

    @pytest.mark.asyncio
    async def test_run_init_exception(self):
        """Test run_init when init_collection raises exception."""
        mock_settings = MagicMock()

        with patch("qdrant_loader.core.init_collection.init_collection") as mock_init, \
             patch("qdrant_loader.cli.ingest_commands.get_logger") as mock_logger:
            
            mock_init.side_effect = Exception("Test error")
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance

            from qdrant_loader.cli.ingest_commands import run_init
            from click.exceptions import ClickException

            with pytest.raises(ClickException):
                await run_init(mock_settings, force=False)


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
             patch("qdrant_loader.cli.core.create_database_directory") as mock_create_dir, \
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
             patch("qdrant_loader.cli.core.create_database_directory") as mock_create_dir:
            
            mock_check.return_value = mock_settings
            mock_create_dir.return_value = False

            result = runner.invoke(init, ["--force"])

            assert result.exit_code == 1
            assert "Database directory creation declined" in result.output

    def test_init_with_existing_database_force_removal(self, runner, mock_settings):
        """Test init command with force flag removes existing database."""
        with patch("qdrant_loader.cli.ingest_commands.validate_workspace_flags"), \
             patch("qdrant_loader.cli.ingest_commands.setup_logging"), \
             patch("qdrant_loader.cli.ingest_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.ingest_commands.check_settings") as mock_check, \
             patch("qdrant_loader.cli.ingest_commands.run_init") as mock_run_init, \
             patch("os.path.exists") as mock_exists, \
             patch("os.remove") as mock_remove, \
             patch("qdrant_loader.cli.ingest_commands.get_logger") as mock_logger:
            
            mock_check.return_value = mock_settings
            mock_run_init.return_value = None
            mock_exists.return_value = True
            logger = MagicMock()
            mock_logger.return_value = logger

            result = runner.invoke(init, ["--force"])

            assert result.exit_code == 0
            mock_remove.assert_called_once_with("/tmp/test.db")
            logger.info.assert_any_call("Resetting state database", database_path="/tmp/test.db")

    def test_init_force_no_existing_database(self, runner, mock_settings):
        """Test init command with force flag when no existing database."""
        with patch("qdrant_loader.cli.ingest_commands.validate_workspace_flags"), \
             patch("qdrant_loader.cli.ingest_commands.setup_logging"), \
             patch("qdrant_loader.cli.ingest_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.ingest_commands.check_settings") as mock_check, \
             patch("qdrant_loader.cli.ingest_commands.run_init") as mock_run_init, \
             patch("os.path.exists") as mock_exists, \
             patch("qdrant_loader.cli.ingest_commands.get_logger") as mock_logger:
            
            mock_check.return_value = mock_settings
            mock_run_init.return_value = None
            mock_exists.return_value = False
            logger = MagicMock()
            mock_logger.return_value = logger

            result = runner.invoke(init, ["--force"])

            assert result.exit_code == 0
            logger.info.assert_any_call(
                "State database reset skipped (no existing database)",
                database_path="/tmp/test.db"
            )


class TestRunIngestCommand:
    """Test the run_ingest command."""

    def test_run_ingest_basic(self, runner, mock_settings):
        """Test basic run ingest command."""
        with patch("qdrant_loader.cli.ingest_commands.validate_workspace_flags"), \
             patch("qdrant_loader.cli.ingest_commands.setup_logging"), \
             patch("qdrant_loader.cli.ingest_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.ingest_commands.check_settings") as mock_check, \
             patch("qdrant_loader.core.managers.qdrant_manager.QdrantManager") as mock_qdrant_manager, \
             patch("qdrant_loader.core.async_ingestion_pipeline.AsyncIngestionPipeline") as mock_pipeline:
            
            mock_check.return_value = mock_settings
            mock_qdrant_instance = Mock()
            mock_qdrant_manager.return_value = mock_qdrant_instance
            
            mock_pipeline_instance = AsyncMock()
            mock_pipeline_instance.process_documents = AsyncMock()
            mock_pipeline_instance.cleanup = AsyncMock()
            mock_pipeline.return_value = mock_pipeline_instance

            result = runner.invoke(run_ingest, [])

            assert result.exit_code == 0

    def test_run_ingest_with_project_filter(self, runner, mock_settings):
        """Test run ingest with project filter."""
        with patch("qdrant_loader.cli.ingest_commands.validate_workspace_flags"), \
             patch("qdrant_loader.cli.ingest_commands.setup_logging"), \
             patch("qdrant_loader.cli.ingest_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.ingest_commands.check_settings") as mock_check, \
             patch("qdrant_loader.core.managers.qdrant_manager.QdrantManager") as mock_qdrant_manager, \
             patch("qdrant_loader.core.async_ingestion_pipeline.AsyncIngestionPipeline") as mock_pipeline:
            
            mock_check.return_value = mock_settings
            mock_qdrant_instance = Mock()
            mock_qdrant_manager.return_value = mock_qdrant_instance
            
            mock_pipeline_instance = AsyncMock()
            mock_pipeline_instance.process_documents = AsyncMock()
            mock_pipeline_instance.cleanup = AsyncMock()
            mock_pipeline.return_value = mock_pipeline_instance

            result = runner.invoke(run_ingest, ["--project", "test_project"])

            assert result.exit_code == 0

    def test_run_ingest_with_profiling(self, runner, mock_settings):
        """Test run ingest with profiling enabled."""
        with patch("qdrant_loader.cli.ingest_commands.validate_workspace_flags"), \
             patch("qdrant_loader.cli.ingest_commands.setup_logging"), \
             patch("qdrant_loader.cli.ingest_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.ingest_commands.check_settings") as mock_check, \
             patch("qdrant_loader.core.managers.qdrant_manager.QdrantManager") as mock_qdrant_manager, \
             patch("qdrant_loader.core.async_ingestion_pipeline.AsyncIngestionPipeline") as mock_pipeline, \
             patch("cProfile.Profile") as mock_profiler:
            
            mock_check.return_value = mock_settings
            mock_qdrant_instance = Mock()
            mock_qdrant_manager.return_value = mock_qdrant_instance
            
            mock_pipeline_instance = AsyncMock()
            mock_pipeline_instance.process_documents = AsyncMock()
            mock_pipeline_instance.cleanup = AsyncMock()
            mock_pipeline.return_value = mock_pipeline_instance
            
            mock_prof_instance = MagicMock()
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
             patch("qdrant_loader.core.managers.qdrant_manager.QdrantManager") as mock_qdrant_manager:
            
            # Configure mock settings
            mock_settings.projects_config = Mock()
            mock_settings.projects_config.projects = {}
            mock_check.return_value = mock_settings
            
            mock_qdrant_instance = Mock()
            mock_client = Mock()
            mock_qdrant_instance._ensure_client_connected.return_value = mock_client
            mock_qdrant_manager.return_value = mock_qdrant_instance
            
            # Mock collections response
            mock_collections = Mock()
            mock_collections.collections = []
            mock_client.get_collections.return_value = mock_collections

            result = runner.invoke(check_status, [])

            assert result.exit_code == 0

    def test_check_status_with_project(self, runner, mock_settings):
        """Test status check for specific project."""
        with patch("qdrant_loader.cli.ingest_commands.validate_workspace_flags"), \
             patch("qdrant_loader.cli.ingest_commands.setup_logging"), \
             patch("qdrant_loader.cli.ingest_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.ingest_commands.check_settings") as mock_check, \
             patch("qdrant_loader.core.managers.qdrant_manager.QdrantManager") as mock_qdrant_manager:
            
            # Configure mock settings with project
            mock_settings.projects_config = Mock()
            mock_settings.projects_config.projects = {
                "test_project": Mock(
                    display_name="Test Project",
                    description="Test description",
                    sources={}
                )
            }
            mock_check.return_value = mock_settings
            
            mock_qdrant_instance = Mock()
            mock_client = Mock()
            mock_qdrant_instance._ensure_client_connected.return_value = mock_client
            mock_qdrant_manager.return_value = mock_qdrant_instance
            
            # Mock collections response
            mock_collections = Mock()
            mock_collections.collections = []
            mock_client.get_collections.return_value = mock_collections

            result = runner.invoke(check_status, ["--project", "test_project"])

            assert result.exit_code == 0


class TestStandaloneCommands:
    """Test standalone command functions."""

    def test_ingest_command_basic(self, runner, mock_settings):
        """Test standalone ingest command."""
        with patch("qdrant_loader.cli.ingest_commands.run_ingest", new_callable=AsyncMock) as mock_run_ingest:
            # Mock the run_ingest function that ingest_command calls
            mock_run_ingest.return_value = None

            result = runner.invoke(ingest_command, [])

            assert result.exit_code == 0
            mock_run_ingest.assert_called_once()

    def test_init_command_basic(self, runner, mock_settings):
        """Test standalone init command."""
        with patch("qdrant_loader.cli.ingest_commands.init", new_callable=AsyncMock):
            # Mock the init function that init_command calls
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