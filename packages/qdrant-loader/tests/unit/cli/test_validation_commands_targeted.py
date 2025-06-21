"""Targeted tests for validation_commands.py to improve coverage.

Focuses on uncovered error paths, edge cases, and main command flows.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from qdrant_loader.cli.validation_commands import (
    _run_validation,
    _run_repairs,
    _get_validation_status,
    _configure_scheduled_validation,
    repair_inconsistencies,
    schedule_validation,
    validate_graph,
    validation_status,
)


@pytest.fixture
def runner():
    """Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_settings():
    """Mock settings object."""
    settings = Mock()
    settings.qdrant = Mock()
    settings.neo4j = Mock()
    settings.logging = Mock()
    settings.workspace = Mock()
    return settings


@pytest.fixture
def mock_validation_report():
    """Mock validation report."""
    report = Mock()
    report.to_dict.return_value = {
        "validation_id": "test-123",
        "total_issues": 5,
        "critical_issues": 1,
        "error_issues": 2,
        "warning_issues": 2,
        "info_issues": 0,
        "system_health_score": 75.5,
        "auto_repairable_issues": 3,
    }
    report.total_issues = 5
    report.critical_issues = 1
    report.error_issues = 2
    report.warning_issues = 2
    report.info_issues = 0
    report.system_health_score = 75.5
    report.auto_repairable_issues = 3
    return report


class TestValidateGraphCommand:
    """Test validate-graph command."""

    @patch("qdrant_loader.cli.validation_commands.asyncio.run")
    @patch("qdrant_loader.cli.validation_commands.check_settings")
    @patch("qdrant_loader.cli.validation_commands.load_config_with_workspace")
    @patch("qdrant_loader.cli.validation_commands.setup_logging")
    @patch("qdrant_loader.cli.validation_commands.validate_workspace_flags")
    def test_validate_graph_basic_success(
        self,
        mock_validate_flags,
        mock_setup_logging,
        mock_load_config,
        mock_check_settings,
        mock_asyncio_run,
        runner,
        mock_settings,
        mock_validation_report,
    ):
        """Test successful validation with basic options."""
        mock_check_settings.return_value = mock_settings
        mock_asyncio_run.return_value = mock_validation_report

        result = runner.invoke(validate_graph, [])

        assert result.exit_code == 0
        assert "Validation completed successfully" in result.output
        assert "Total Issues: 5" in result.output
        assert "Health Score: 75.5/100" in result.output

    @patch("qdrant_loader.cli.validation_commands.asyncio.run")
    @patch("qdrant_loader.cli.validation_commands.check_settings")
    @patch("qdrant_loader.cli.validation_commands.load_config_with_workspace")
    @patch("qdrant_loader.cli.validation_commands.setup_logging")
    @patch("qdrant_loader.cli.validation_commands.validate_workspace_flags")
    def test_validate_graph_with_critical_issues(
        self,
        mock_validate_flags,
        mock_setup_logging,
        mock_load_config,
        mock_check_settings,
        mock_asyncio_run,
        runner,
        mock_settings,
    ):
        """Test validation with critical issues exits with error."""
        report = Mock()
        report.to_dict.return_value = {"critical_issues": 2, "error_issues": 0}
        report.critical_issues = 2
        report.error_issues = 0
        report.total_issues = 2
        report.warning_issues = 0
        report.info_issues = 0
        report.system_health_score = 25.0
        report.auto_repairable_issues = 0

        mock_check_settings.return_value = mock_settings
        mock_asyncio_run.return_value = report

        result = runner.invoke(validate_graph, [])

        assert result.exit_code == 1
        assert "Critical validation issues found" in result.output

    @patch("qdrant_loader.cli.validation_commands.asyncio.run")
    @patch("qdrant_loader.cli.validation_commands.check_settings")
    @patch("qdrant_loader.cli.validation_commands.load_config_with_workspace")
    @patch("qdrant_loader.cli.validation_commands.setup_logging")
    @patch("qdrant_loader.cli.validation_commands.validate_workspace_flags")
    def test_validate_graph_with_error_issues_exit_code(
        self,
        mock_validate_flags,
        mock_setup_logging,
        mock_load_config,
        mock_check_settings,
        mock_asyncio_run,
        runner,
        mock_settings,
    ):
        """Test validation with error issues exits with code 1."""
        report = Mock()
        report.to_dict.return_value = {"critical_issues": 0, "error_issues": 3}
        report.critical_issues = 0
        report.error_issues = 3
        report.total_issues = 3
        report.warning_issues = 0
        report.info_issues = 0
        report.system_health_score = 50.0
        report.auto_repairable_issues = 1

        mock_check_settings.return_value = mock_settings
        mock_asyncio_run.return_value = report

        # Mock sys.exit to catch the exit call
        with patch("sys.exit") as mock_exit:
            result = runner.invoke(validate_graph, [])
            mock_exit.assert_called_once_with(1)

        assert "Validation completed with errors" in result.output

    def test_validate_graph_with_output_file(self, runner, mock_settings, mock_validation_report):
        """Test validation with output file option."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "report.json"

            with patch("qdrant_loader.cli.validation_commands.asyncio.run") as mock_run, \
                 patch("qdrant_loader.cli.validation_commands.check_settings") as mock_check, \
                 patch("qdrant_loader.cli.validation_commands.load_config_with_workspace"), \
                 patch("qdrant_loader.cli.validation_commands.setup_logging"), \
                 patch("qdrant_loader.cli.validation_commands.validate_workspace_flags"):
                
                mock_check.return_value = mock_settings
                mock_run.return_value = mock_validation_report

                result = runner.invoke(validate_graph, ["--output", str(output_file)])

                assert result.exit_code == 0
                assert f"Validation report saved to {output_file}" in result.output
                assert output_file.exists()

                # Verify JSON content
                with open(output_file) as f:
                    saved_data = json.load(f)
                assert saved_data["validation_id"] == "test-123"

    def test_validate_graph_with_scanners_option(self, runner, mock_settings, mock_validation_report):
        """Test validation with specific scanners."""
        with patch("qdrant_loader.cli.validation_commands.asyncio.run") as mock_run, \
             patch("qdrant_loader.cli.validation_commands.check_settings") as mock_check, \
             patch("qdrant_loader.cli.validation_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.validation_commands.setup_logging"), \
             patch("qdrant_loader.cli.validation_commands.validate_workspace_flags"), \
             patch("qdrant_loader.cli.validation_commands.get_logger") as mock_logger:
            
            logger = Mock()
            mock_logger.return_value = logger
            mock_check.return_value = mock_settings
            mock_run.return_value = mock_validation_report

            result = runner.invoke(validate_graph, ["--scanners", "missing_mappings,orphaned_records"])

            assert result.exit_code == 0
            logger.info.assert_any_call("Using specific scanners: ['missing_mappings', 'orphaned_records']")

    def test_validate_graph_exception_handling(self, runner):
        """Test validation command exception handling."""
        with patch("qdrant_loader.cli.validation_commands.validate_workspace_flags") as mock_validate:
            mock_validate.side_effect = Exception("Test error")

            with patch("qdrant_loader.cli.validation_commands.get_logger") as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger

                result = runner.invoke(validate_graph, [])

                assert result.exit_code == 1
                assert "Test error" in result.output

    def test_validate_graph_exception_no_logger(self, runner):
        """Test validation command exception when logger setup fails."""
        with patch("qdrant_loader.cli.validation_commands.validate_workspace_flags") as mock_validate:
            mock_validate.side_effect = Exception("Test error")

            with patch("qdrant_loader.cli.validation_commands.get_logger") as mock_get_logger:
                mock_get_logger.side_effect = Exception("Logger error")

                result = runner.invoke(validate_graph, [])

                assert result.exit_code == 1
                assert "Test error" in result.output


class TestRepairInconsistenciesCommand:
    """Test repair-inconsistencies command."""

    @patch("qdrant_loader.cli.validation_commands.asyncio.run")
    @patch("qdrant_loader.cli.validation_commands.check_settings")
    @patch("qdrant_loader.cli.validation_commands.load_config_with_workspace")
    @patch("qdrant_loader.cli.validation_commands.setup_logging")
    @patch("qdrant_loader.cli.validation_commands.validate_workspace_flags")
    def test_repair_inconsistencies_no_issues_specified(
        self,
        mock_validate_flags,
        mock_setup_logging,
        mock_load_config,
        mock_check_settings,
        mock_asyncio_run,
        runner,
        mock_settings,
    ):
        """Test repair command when no issues are specified."""
        mock_check_settings.return_value = mock_settings

        result = runner.invoke(repair_inconsistencies, [])

        assert result.exit_code == 1
        assert "Either --report or --issue-ids must be provided" in result.output

    def test_repair_inconsistencies_with_issue_ids(self, runner, mock_settings):
        """Test repair command with specific issue IDs."""
        with patch("qdrant_loader.cli.validation_commands.asyncio.run") as mock_run, \
             patch("qdrant_loader.cli.validation_commands.check_settings") as mock_check, \
             patch("qdrant_loader.cli.validation_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.validation_commands.setup_logging"), \
             patch("qdrant_loader.cli.validation_commands.validate_workspace_flags"):
            
            mock_check.return_value = mock_settings
            mock_run.return_value = {"repaired": 2, "failed": 0}

            result = runner.invoke(repair_inconsistencies, ["--issue-ids", "issue1,issue2", "--force"])

            assert result.exit_code == 0
            assert "Repair operation completed" in result.output
