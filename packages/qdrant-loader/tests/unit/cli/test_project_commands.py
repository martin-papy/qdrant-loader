"""Tests for project management CLI commands."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.exceptions import ClickException
from click.testing import CliRunner

from qdrant_loader.cli.project_commands import (
    _get_all_sources_from_config,
    _initialize_project_contexts_from_config,
    _setup_project_manager,
    project_cli,
)
from qdrant_loader.config.models import ProjectConfig, ProjectContext
from qdrant_loader.config.sources import SourcesConfig


class TestGetAllSourcesFromConfig:
    """Test the _get_all_sources_from_config helper function."""

    def test_get_all_sources_empty_config(self):
        """Test with empty sources config."""
        sources_config = SourcesConfig()
        result = _get_all_sources_from_config(sources_config)
        assert result == {}

    def test_get_all_sources_with_data(self):
        """Test with populated sources config."""
        # Create mock source configs that don't require validation
        mock_doc_config = Mock()
        mock_git_config = Mock()
        mock_confluence_config = Mock()
        mock_jira_config = Mock()
        mock_localfile_config = Mock()

        sources_config = SourcesConfig(
            publicdocs={"doc1": mock_doc_config},
            git={"repo1": mock_git_config},
            confluence={"space1": mock_confluence_config},
            jira={"project1": mock_jira_config},
            localfile={"files1": mock_localfile_config},
        )
        result = _get_all_sources_from_config(sources_config)
        assert len(result) == 5
        assert "doc1" in result
        assert "repo1" in result
        assert "space1" in result
        assert "project1" in result
        assert "files1" in result


class TestSetupProjectManager:
    """Test the _setup_project_manager function."""

    @pytest.mark.asyncio
    async def test_setup_project_manager_with_workspace(self):
        """Test setup with workspace parameter."""
        with (
            patch("qdrant_loader.cli.cli._setup_workspace") as mock_setup_workspace,
            patch(
                "qdrant_loader.cli.cli._load_config_with_workspace"
            ) as mock_load_config,
            patch("qdrant_loader.cli.cli._check_settings") as mock_check_settings,
            patch("qdrant_loader.cli.project_commands.ProjectManager") as mock_pm,
            patch(
                "qdrant_loader.cli.project_commands._initialize_project_contexts_from_config"
            ) as mock_init,
        ):
            # Mock workspace config
            mock_workspace_config = Mock()
            mock_setup_workspace.return_value = mock_workspace_config

            # Mock settings with proper structure
            mock_settings = Mock()
            mock_settings.global_config = Mock()
            mock_settings.global_config.qdrant = Mock()
            mock_settings.global_config.qdrant.collection_name = "test_collection"
            mock_settings.projects_config = Mock()
            mock_check_settings.return_value = mock_settings

            # Mock project manager
            mock_project_manager = Mock()
            mock_pm.return_value = mock_project_manager

            workspace_path = Path("/test/workspace")
            result = await _setup_project_manager(workspace_path, None, None)

            mock_setup_workspace.assert_called_once_with(workspace_path)
            mock_load_config.assert_called_once_with(mock_workspace_config, None, None)
            mock_check_settings.assert_called_once()
            mock_pm.assert_called_once()
            mock_init.assert_called_once_with(mock_project_manager)
            assert result == (mock_settings, mock_project_manager)

    @pytest.mark.asyncio
    async def test_setup_project_manager_with_config_and_env(self):
        """Test setup with config and env parameters."""
        with (
            patch("qdrant_loader.cli.cli._setup_workspace") as mock_setup_workspace,
            patch(
                "qdrant_loader.cli.cli._load_config_with_workspace"
            ) as mock_load_config,
            patch("qdrant_loader.cli.cli._check_settings") as mock_check_settings,
            patch("qdrant_loader.cli.project_commands.ProjectManager") as mock_pm,
            patch(
                "qdrant_loader.cli.project_commands._initialize_project_contexts_from_config"
            ) as mock_init,
        ):
            # Mock settings with proper structure
            mock_settings = Mock()
            mock_settings.global_config = Mock()
            mock_settings.global_config.qdrant = Mock()
            mock_settings.global_config.qdrant.collection_name = "test_collection"
            mock_settings.projects_config = Mock()
            mock_check_settings.return_value = mock_settings

            # Mock project manager
            mock_project_manager = Mock()
            mock_pm.return_value = mock_project_manager

            config_path = Path("/test/config.yaml")
            env_path = Path("/test/.env")
            result = await _setup_project_manager(None, config_path, env_path)

            mock_setup_workspace.assert_not_called()
            mock_load_config.assert_called_once_with(None, config_path, env_path)
            mock_check_settings.assert_called_once()
            mock_pm.assert_called_once()
            mock_init.assert_called_once_with(mock_project_manager)
            assert result == (mock_settings, mock_project_manager)

    @pytest.mark.asyncio
    async def test_setup_project_manager_no_qdrant_config(self):
        """Test setup when Qdrant configuration is missing."""
        with (
            patch("qdrant_loader.cli.cli._setup_workspace"),
            patch("qdrant_loader.cli.cli._load_config_with_workspace"),
            patch("qdrant_loader.cli.cli._check_settings") as mock_check_settings,
        ):
            # Mock settings without Qdrant config
            mock_settings = Mock()
            mock_settings.global_config = None
            mock_check_settings.return_value = mock_settings

            with pytest.raises(
                ClickException,
                match="Global configuration or Qdrant configuration is missing",
            ):
                await _setup_project_manager(None, None, None)


class TestInitializeProjectContextsFromConfig:
    """Test the _initialize_project_contexts_from_config function."""

    @pytest.mark.asyncio
    async def test_initialize_project_contexts_success(self):
        """Test successful initialization of project contexts."""
        with patch(
            "qdrant_loader.core.project_manager.ProjectContext"
        ) as mock_context_class:
            # Mock project manager with projects config
            mock_project_manager = Mock()
            mock_project_manager.projects_config = Mock()
            mock_project_manager.projects_config.projects = {"test-project": Mock()}
            mock_project_manager.global_collection_name = "global_collection"
            mock_project_manager._project_contexts = {}

            # Mock project config
            mock_project_config = Mock()
            mock_project_config.get_effective_collection_name.return_value = (
                "test_collection"
            )
            mock_project_manager.projects_config.projects["test-project"] = (
                mock_project_config
            )

            # Mock context creation
            mock_context = Mock()
            mock_context_class.return_value = mock_context

            await _initialize_project_contexts_from_config(mock_project_manager)

            # Verify context was created and added
            mock_context_class.assert_called_once()
            assert "test-project" in mock_project_manager._project_contexts


class TestProjectListCommand:
    """Test the project list command."""

    def test_project_list_table_format(self):
        """Test project list with table format."""
        runner = CliRunner()

        with (
            patch(
                "qdrant_loader.cli.project_commands._setup_project_manager"
            ) as mock_setup,
            patch("qdrant_loader.cli.project_commands.console") as mock_console,
            patch(
                "qdrant_loader.cli.project_commands.validate_workspace_flags"
            ) as mock_validate,
        ):
            # Mock project contexts
            mock_context = Mock()
            mock_context.project_id = "test-project"
            mock_context.display_name = "Test Project"
            mock_context.description = "A test project"
            mock_context.collection_name = "test_collection"
            mock_context.config = Mock()
            mock_context.config.sources = SourcesConfig()

            mock_project_manager = Mock()
            mock_project_manager.get_all_project_contexts.return_value = {
                "test-project": mock_context
            }
            mock_setup.return_value = (Mock(), mock_project_manager)

            result = runner.invoke(project_cli, ["list", "--format", "table"])

            assert result.exit_code == 0
            mock_console.print.assert_called()

    def test_project_list_json_format(self):
        """Test project list with JSON format."""
        runner = CliRunner()

        with (
            patch(
                "qdrant_loader.cli.project_commands._setup_project_manager"
            ) as mock_setup,
            patch(
                "qdrant_loader.cli.project_commands.validate_workspace_flags"
            ) as mock_validate,
        ):
            # Mock project contexts
            mock_context = Mock()
            mock_context.project_id = "test-project"
            mock_context.display_name = "Test Project"
            mock_context.description = "A test project"
            mock_context.collection_name = "test_collection"
            mock_context.config = Mock()
            mock_context.config.sources = SourcesConfig()

            mock_project_manager = Mock()
            mock_project_manager.get_all_project_contexts.return_value = {
                "test-project": mock_context
            }
            mock_setup.return_value = (Mock(), mock_project_manager)

            result = runner.invoke(project_cli, ["list", "--format", "json"])

            assert result.exit_code == 0
            # Parse the JSON output
            output_data = json.loads(result.output)
            assert len(output_data) == 1
            assert output_data[0]["project_id"] == "test-project"
            assert output_data[0]["display_name"] == "Test Project"
            assert output_data[0]["source_count"] == 0

    def test_project_list_no_projects(self):
        """Test project list when no projects are configured."""
        runner = CliRunner()

        with (
            patch(
                "qdrant_loader.cli.project_commands._setup_project_manager"
            ) as mock_setup,
            patch("qdrant_loader.cli.project_commands.console") as mock_console,
            patch(
                "qdrant_loader.cli.project_commands.validate_workspace_flags"
            ) as mock_validate,
        ):
            mock_project_manager = Mock()
            mock_project_manager.get_all_project_contexts.return_value = {}
            mock_setup.return_value = (Mock(), mock_project_manager)

            result = runner.invoke(project_cli, ["list"])

            assert result.exit_code == 0
            mock_console.print.assert_called_with(
                "[yellow]No projects configured.[/yellow]"
            )

    def test_project_list_error_handling(self):
        """Test project list error handling."""
        runner = CliRunner()

        with (
            patch(
                "qdrant_loader.cli.project_commands._setup_project_manager"
            ) as mock_setup,
            patch(
                "qdrant_loader.cli.project_commands.validate_workspace_flags"
            ) as mock_validate,
        ):
            mock_setup.side_effect = Exception("Setup failed")

            result = runner.invoke(project_cli, ["list"])

            assert result.exit_code != 0
            assert "Failed to list projects" in result.output


class TestProjectStatusCommand:
    """Test the project status command."""

    def test_project_status_all_projects(self):
        """Test project status for all projects."""
        runner = CliRunner()

        with (
            patch(
                "qdrant_loader.cli.project_commands._setup_project_manager"
            ) as mock_setup,
            patch("qdrant_loader.cli.project_commands.console") as mock_console,
            patch(
                "qdrant_loader.cli.project_commands.validate_workspace_flags"
            ) as mock_validate,
        ):
            # Mock project contexts
            mock_context = Mock()
            mock_context.project_id = "test-project"
            mock_context.display_name = "Test Project"
            mock_context.collection_name = "test_collection"
            mock_context.config = Mock()
            mock_context.config.sources = SourcesConfig()

            mock_project_manager = Mock()
            mock_project_manager.get_all_project_contexts.return_value = {
                "test-project": mock_context
            }
            mock_setup.return_value = (Mock(), mock_project_manager)

            result = runner.invoke(project_cli, ["status"])

            assert result.exit_code == 0

    def test_project_status_specific_project(self):
        """Test project status for a specific project."""
        runner = CliRunner()

        with (
            patch(
                "qdrant_loader.cli.project_commands._setup_project_manager"
            ) as mock_setup,
            patch("qdrant_loader.cli.project_commands.console") as mock_console,
            patch(
                "qdrant_loader.cli.project_commands.validate_workspace_flags"
            ) as mock_validate,
        ):
            # Mock project contexts
            mock_context = Mock()
            mock_context.project_id = "test-project"
            mock_context.display_name = "Test Project"
            mock_context.collection_name = "test_collection"
            mock_context.config = Mock()
            mock_context.config.sources = SourcesConfig()

            mock_project_manager = Mock()
            mock_project_manager.get_project_context.return_value = mock_context
            mock_setup.return_value = (Mock(), mock_project_manager)

            result = runner.invoke(
                project_cli, ["status", "--project-id", "test-project"]
            )

            assert result.exit_code == 0
            mock_project_manager.get_project_context.assert_called_with("test-project")

    def test_project_status_project_not_found(self):
        """Test project status when project is not found."""
        runner = CliRunner()

        with (
            patch(
                "qdrant_loader.cli.project_commands._setup_project_manager"
            ) as mock_setup,
            patch(
                "qdrant_loader.cli.project_commands.validate_workspace_flags"
            ) as mock_validate,
        ):
            mock_project_manager = Mock()
            mock_project_manager.get_project_context.return_value = None
            mock_setup.return_value = (Mock(), mock_project_manager)

            result = runner.invoke(
                project_cli, ["status", "--project-id", "nonexistent"]
            )

            assert result.exit_code != 0
            assert "Project 'nonexistent' not found" in result.output

    def test_project_status_json_format(self):
        """Test project status with JSON format."""
        runner = CliRunner()

        with (
            patch(
                "qdrant_loader.cli.project_commands._setup_project_manager"
            ) as mock_setup,
            patch(
                "qdrant_loader.cli.project_commands.validate_workspace_flags"
            ) as mock_validate,
        ):
            # Mock project contexts
            mock_context = Mock()
            mock_context.project_id = "test-project"
            mock_context.display_name = "Test Project"
            mock_context.collection_name = "test_collection"
            mock_context.config = Mock()
            mock_context.config.sources = SourcesConfig()

            mock_project_manager = Mock()
            mock_project_manager.get_all_project_contexts.return_value = {
                "test-project": mock_context
            }
            mock_setup.return_value = (Mock(), mock_project_manager)

            result = runner.invoke(project_cli, ["status", "--format", "json"])

            assert result.exit_code == 0
            # Parse the JSON output
            output_data = json.loads(result.output)
            assert len(output_data) == 1
            assert output_data[0]["project_id"] == "test-project"


class TestProjectValidateCommand:
    """Test the project validate command."""

    def test_project_validate_all_projects(self):
        """Test project validation for all projects."""
        runner = CliRunner()

        with (
            patch(
                "qdrant_loader.cli.project_commands._setup_project_manager"
            ) as mock_setup,
            patch("qdrant_loader.cli.project_commands.console") as mock_console,
            patch(
                "qdrant_loader.cli.project_commands.validate_workspace_flags"
            ) as mock_validate,
        ):
            # Mock project contexts with valid config
            mock_context = Mock()
            mock_context.project_id = "test-project"
            mock_context.display_name = "Test Project"
            mock_context.collection_name = "test_collection"
            mock_context.config = Mock()
            mock_context.config.sources = SourcesConfig()

            mock_project_manager = Mock()
            mock_project_manager.get_all_project_contexts.return_value = {
                "test-project": mock_context
            }
            mock_setup.return_value = (Mock(), mock_project_manager)

            result = runner.invoke(project_cli, ["validate"])

            assert result.exit_code == 0

    def test_project_validate_specific_project(self):
        """Test project validation for a specific project."""
        runner = CliRunner()

        with (
            patch(
                "qdrant_loader.cli.project_commands._setup_project_manager"
            ) as mock_setup,
            patch("qdrant_loader.cli.project_commands.console") as mock_console,
            patch(
                "qdrant_loader.cli.project_commands.validate_workspace_flags"
            ) as mock_validate,
        ):
            # Mock project contexts with valid config
            mock_context = Mock()
            mock_context.project_id = "test-project"
            mock_context.config = Mock()
            mock_context.config.sources = SourcesConfig()

            mock_project_manager = Mock()
            mock_project_manager.get_project_context.return_value = mock_context
            mock_setup.return_value = (Mock(), mock_project_manager)

            result = runner.invoke(
                project_cli, ["validate", "--project-id", "test-project"]
            )

            assert result.exit_code == 0

    def test_project_validate_validation_failure(self):
        """Test project validation when validation fails."""
        runner = CliRunner()

        with (
            patch(
                "qdrant_loader.cli.project_commands._setup_project_manager"
            ) as mock_setup,
            patch("qdrant_loader.cli.project_commands.console") as mock_console,
            patch(
                "qdrant_loader.cli.project_commands.validate_workspace_flags"
            ) as mock_validate,
        ):
            # Mock project contexts with invalid config (no config)
            mock_context = Mock()
            mock_context.project_id = "test-project"
            mock_context.config = None  # Invalid - no config

            mock_project_manager = Mock()
            mock_project_manager.get_all_project_contexts.return_value = {
                "test-project": mock_context
            }
            mock_setup.return_value = (Mock(), mock_project_manager)

            result = runner.invoke(project_cli, ["validate"])

            assert result.exit_code != 0
            assert "Project validation failed" in result.output

    def test_project_validate_error_handling(self):
        """Test project validation error handling."""
        runner = CliRunner()

        with (
            patch(
                "qdrant_loader.cli.project_commands._setup_project_manager"
            ) as mock_setup,
            patch(
                "qdrant_loader.cli.project_commands.validate_workspace_flags"
            ) as mock_validate,
        ):
            mock_setup.side_effect = Exception("Setup failed")

            result = runner.invoke(project_cli, ["validate"])

            assert result.exit_code != 0
            assert "Failed to validate projects" in result.output


class TestWorkspaceFlags:
    """Test workspace flag validation."""

    def test_workspace_flag_validation_exists(self):
        """Test that workspace flag validation function exists."""
        from qdrant_loader.config.workspace import validate_workspace_flags

        # Just verify the function exists and is callable
        assert callable(validate_workspace_flags)
