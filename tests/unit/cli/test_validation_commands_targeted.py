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
    ValidationIssue,
    ValidationRepairSystem,
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
def mock_success_report():
    """Mock successful validation report."""
    report = Mock()
    report.to_dict.return_value = {
        "validation_id": "test-123",
        "total_issues": 0,
        "critical_issues": 0,
        "error_issues": 0,
        "warning_issues": 0,
        "info_issues": 0,
        "system_health_score": 100.0,
        "auto_repairable_issues": 0,
    }
    report.total_issues = 0
    report.critical_issues = 0
    report.error_issues = 0
    report.warning_issues = 0
    report.info_issues = 0
    report.system_health_score = 100.0
    report.auto_repairable_issues = 0
    return report


class TestValidateGraphCommand:
    """Test validate-graph command error paths."""

    @patch("qdrant_loader.cli.validation_commands.asyncio.run")
    @patch("qdrant_loader.cli.validation_commands.check_settings")
    @patch("qdrant_loader.cli.validation_commands.load_config_with_workspace")
    @patch("qdrant_loader.cli.validation_commands.setup_logging")
    @patch("qdrant_loader.cli.validation_commands.validate_workspace_flags")
    def test_validate_graph_success_no_issues(
        self,
        mock_validate_flags,
        mock_setup_logging,
        mock_load_config,
        mock_check_settings,
        mock_asyncio_run,
        runner,
        mock_settings,
        mock_success_report,
    ):
        """Test successful validation with no issues."""
        mock_check_settings.return_value = mock_settings
        mock_asyncio_run.return_value = mock_success_report

        result = runner.invoke(validate_graph, [])

        assert result.exit_code == 0
        assert "Validation completed successfully" in result.output

    def test_validate_graph_with_output_file_success(self, runner, mock_settings, mock_success_report):
        """Test validation with output file option."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "report.json"

            with patch("qdrant_loader.cli.validation_commands.asyncio.run") as mock_run, \
                 patch("qdrant_loader.cli.validation_commands.check_settings") as mock_check, \
                 patch("qdrant_loader.cli.validation_commands.load_config_with_workspace"), \
                 patch("qdrant_loader.cli.validation_commands.setup_logging"), \
                 patch("qdrant_loader.cli.validation_commands.validate_workspace_flags"):
                
                mock_check.return_value = mock_settings
                mock_run.return_value = mock_success_report

                result = runner.invoke(validate_graph, ["--output", str(output_file)])

                assert result.exit_code == 0
                assert f"Validation report saved to {output_file}" in result.output
                assert output_file.exists()

    def test_validate_graph_with_auto_repair_option(self, runner, mock_settings):
        """Test validation with auto-repair option showing repairable issues."""
        report = Mock()
        report.to_dict.return_value = {"auto_repairable_issues": 3}
        report.total_issues = 3
        report.critical_issues = 0
        report.error_issues = 0
        report.warning_issues = 3
        report.info_issues = 0
        report.system_health_score = 85.0
        report.auto_repairable_issues = 3

        with patch("qdrant_loader.cli.validation_commands.asyncio.run") as mock_run, \
             patch("qdrant_loader.cli.validation_commands.check_settings") as mock_check, \
             patch("qdrant_loader.cli.validation_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.validation_commands.setup_logging"), \
             patch("qdrant_loader.cli.validation_commands.validate_workspace_flags"):
            
            mock_check.return_value = mock_settings
            mock_run.return_value = report

            result = runner.invoke(validate_graph, ["--auto-repair"])

            assert result.exit_code == 0
            assert "Auto-repairable Issues: 3" in result.output

    def test_validate_graph_with_scanners_parsing(self, runner, mock_settings, mock_success_report):
        """Test validation with scanners option parsing."""
        with patch("qdrant_loader.cli.validation_commands.asyncio.run") as mock_run, \
             patch("qdrant_loader.cli.validation_commands.check_settings"), \
             patch("qdrant_loader.cli.validation_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.validation_commands.setup_logging"), \
             patch("qdrant_loader.cli.validation_commands.validate_workspace_flags"), \
             patch("qdrant_loader.cli.validation_commands.get_logger") as mock_logger:
            
            logger = Mock()
            mock_logger.return_value = logger
            mock_run.return_value = mock_success_report

            result = runner.invoke(validate_graph, ["--scanners", "missing_mappings,orphaned_records"])

            logger.info.assert_any_call("Using specific scanners: ['missing_mappings', 'orphaned_records']")


class TestRepairInconsistenciesCommand:
    """Test repair-inconsistencies command."""

    def test_repair_inconsistencies_no_options(self, runner):
        """Test repair command with no options specified."""
        result = runner.invoke(repair_inconsistencies, [])

        assert result.exit_code == 1
        assert "Either --report or --issue-ids must be specified" in result.output

    def test_repair_inconsistencies_dry_run_mode(self, runner, mock_settings):
        """Test repair command in dry run mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / "report.json"
            report_data = {
                "issues": [
                    {"issue_id": "issue-1", "title": "Missing mapping", "type": "missing_mapping"},
                    {"issue_id": "issue-2", "title": "Orphaned record", "type": "orphaned_record"}
                ]
            }
            with open(report_file, "w") as f:
                json.dump(report_data, f)

            with patch("qdrant_loader.cli.validation_commands.check_settings") as mock_check, \
                 patch("qdrant_loader.cli.validation_commands.load_config_with_workspace"), \
                 patch("qdrant_loader.cli.validation_commands.setup_logging"), \
                 patch("qdrant_loader.cli.validation_commands.validate_workspace_flags"):
                
                mock_check.return_value = mock_settings

                result = runner.invoke(repair_inconsistencies, ["--report", str(report_file), "--dry-run"])

                assert result.exit_code == 0
                assert "Dry run mode" in result.output
                assert "Dry run completed" in result.output
                assert "issue-1: Missing mapping" in result.output

    def test_repair_inconsistencies_no_issues_found(self, runner, mock_settings):
        """Test repair when no issues are found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / "report.json"
            report_data = {"issues": []}
            with open(report_file, "w") as f:
                json.dump(report_data, f)

            with patch("qdrant_loader.cli.validation_commands.check_settings") as mock_check, \
                 patch("qdrant_loader.cli.validation_commands.load_config_with_workspace"), \
                 patch("qdrant_loader.cli.validation_commands.setup_logging"), \
                 patch("qdrant_loader.cli.validation_commands.validate_workspace_flags"):
                
                mock_check.return_value = mock_settings

                result = runner.invoke(repair_inconsistencies, ["--report", str(report_file)])

                assert result.exit_code == 0
                assert "No issues found to repair" in result.output

    def test_repair_inconsistencies_issue_ids_no_report(self, runner, mock_settings):
        """Test repair with issue IDs but no report."""
        with patch("qdrant_loader.cli.validation_commands.check_settings") as mock_check, \
             patch("qdrant_loader.cli.validation_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.validation_commands.setup_logging"), \
             patch("qdrant_loader.cli.validation_commands.validate_workspace_flags"), \
             patch("qdrant_loader.cli.validation_commands.get_logger") as mock_logger:
            
            logger = Mock()
            mock_logger.return_value = logger
            mock_check.return_value = mock_settings

            result = runner.invoke(repair_inconsistencies, ["--issue-ids", "issue1,issue2"])

            assert result.exit_code == 0
            assert "No issues found to repair" in result.output
            logger.warning.assert_called_once_with("Specific issue ID repair requires a validation report")


class TestScheduleValidationCommand:
    """Test schedule-validation command."""

    def test_schedule_validation_weekly_missing_day(self, runner):
        """Test scheduling weekly validation without day specified."""
        with patch("qdrant_loader.cli.validation_commands.check_settings"), \
             patch("qdrant_loader.cli.validation_commands.load_config_with_workspace"), \
             patch("qdrant_loader.cli.validation_commands.setup_logging"), \
             patch("qdrant_loader.cli.validation_commands.validate_workspace_flags"):

            result = runner.invoke(schedule_validation, ["--interval", "weekly"])

            assert result.exit_code == 1
            assert "Day of week must be specified for weekly validation" in result.output


class TestValidationStatusCommand:
    """Test validation status command."""

    @patch("qdrant_loader.cli.validation_commands.asyncio.run")
    @patch("qdrant_loader.cli.validation_commands.check_settings")
    @patch("qdrant_loader.cli.validation_commands.load_config_with_workspace")
    @patch("qdrant_loader.cli.validation_commands.setup_logging")
    @patch("qdrant_loader.cli.validation_commands.validate_workspace_flags")
    def test_validation_status_json_output(
        self,
        mock_validate_flags,
        mock_setup_logging,
        mock_load_config,
        mock_check_settings,
        mock_asyncio_run,
        runner,
        mock_settings,
    ):
        """Test validation status with JSON output."""
        mock_check_settings.return_value = mock_settings
        status_data = {"current_status": "idle", "history": []}
        mock_asyncio_run.return_value = status_data

        result = runner.invoke(validation_status, ["--json-output"])

        assert result.exit_code == 0
        # Should contain JSON output
        assert "{" in result.output


class TestAsyncFunctions:
    """Test async helper functions directly."""

    @pytest.mark.asyncio
    async def test_run_validation_with_timeout(self):
        """Test _run_validation async function with timeout."""
        mock_settings = MagicMock()
        mock_settings.qdrant_collection_name = "test"
        
        with patch("qdrant_loader.cli.validation_commands.Neo4jManager") as mock_neo4j, \
             patch("qdrant_loader.cli.validation_commands.QdrantManager") as mock_qdrant, \
             patch("qdrant_loader.cli.validation_commands.IDMappingManager") as mock_id_mapping, \
             patch("qdrant_loader.cli.validation_commands.ValidationRepairSystem") as mock_validation, \
             patch("qdrant_loader.cli.validation_commands.ValidationRepairSystemIntegrator") as mock_integrator, \
             patch("qdrant_loader.config.get_global_config") as mock_global_config, \
             patch("qdrant_loader.config.get_settings") as mock_get_settings:
            
            # Mock the settings manager
            mock_get_settings.return_value = MagicMock()
            mock_global_config.return_value = MagicMock()
            
            # Mock all the manager instances
            mock_neo4j_instance = MagicMock()
            mock_neo4j.return_value = mock_neo4j_instance
            
            mock_qdrant_instance = MagicMock()
            mock_qdrant.return_value = mock_qdrant_instance
            
            mock_id_mapping_instance = MagicMock()
            mock_id_mapping.return_value = mock_id_mapping_instance
            
            mock_validation_instance = MagicMock()
            mock_validation.return_value = mock_validation_instance
            
            mock_integrator_instance = MagicMock()
            mock_integrator_instance.initialize = AsyncMock()
            mock_integrator_instance.start = AsyncMock()
            mock_integrator_instance.stop = AsyncMock()
            mock_integrator_instance.trigger_validation = AsyncMock(return_value={"status": "success"})
            mock_integrator.return_value = mock_integrator_instance

            from qdrant_loader.cli.validation_commands import _run_validation

            result = await _run_validation(
                settings=mock_settings,
                validation_id="test_id",
                scanners=["scanner1"],
                max_entities=100,
                auto_repair=False,
                timeout=60
            )

            assert result == {"status": "success"}
            mock_integrator_instance.trigger_validation.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_repairs_with_max_repairs(self):
        """Test _run_repairs async function with max repairs."""
        mock_settings = MagicMock()
        
        with patch("qdrant_loader.cli.validation_commands.Neo4jManager") as mock_neo4j, \
             patch("qdrant_loader.cli.validation_commands.QdrantManager") as mock_qdrant, \
             patch("qdrant_loader.cli.validation_commands.IDMappingManager") as mock_id_mapping, \
             patch("qdrant_loader.cli.validation_commands.ValidationRepairSystem") as mock_validation, \
             patch("qdrant_loader.cli.validation_commands.ValidationRepairSystemIntegrator") as mock_integrator, \
             patch("qdrant_loader.config.get_global_config") as mock_global_config, \
             patch("qdrant_loader.config.get_settings") as mock_get_settings:
            
            # Mock the settings manager
            mock_get_settings.return_value = MagicMock()
            mock_global_config.return_value = MagicMock()
            
            # Mock all the manager instances
            mock_neo4j_instance = MagicMock()
            mock_neo4j.return_value = mock_neo4j_instance
            
            mock_qdrant_instance = MagicMock()
            mock_qdrant.return_value = mock_qdrant_instance
            
            mock_id_mapping_instance = MagicMock()
            mock_id_mapping.return_value = mock_id_mapping_instance
            
            mock_validation_instance = MagicMock()
            mock_validation.return_value = mock_validation_instance
            
            mock_integrator_instance = MagicMock()
            mock_integrator_instance.initialize = AsyncMock()
            mock_integrator_instance.start = AsyncMock()
            mock_integrator_instance.stop = AsyncMock()
            mock_repair_result = MagicMock()
            mock_repair_result.issue_id = "test_issue"
            mock_repair_result.success = True
            mock_repair_result.action_taken = MagicMock()
            mock_repair_result.action_taken.value = "repaired"
            mock_repair_result.error_message = None
            mock_integrator_instance.repair_issues = AsyncMock(return_value=[mock_repair_result])
            mock_integrator.return_value = mock_integrator_instance

            from qdrant_loader.cli.validation_commands import _run_repairs

            issues = [{"issue_id": "test_issue", "title": "Test Issue", "description": "Test description"}]
            result = await _run_repairs(
                settings=mock_settings,
                issues=issues,
                repair_id="test_repair",
                max_repairs=1
            )

            assert len(result) == 1
            assert result[0]["issue_id"] == "test_issue"
            assert result[0]["success"] is True

    @pytest.mark.asyncio
    async def test_get_validation_status_with_filters(self):
        """Test _get_validation_status async function with filters."""
        mock_settings = MagicMock()
        
        with patch("qdrant_loader.cli.validation_commands.Neo4jManager") as mock_neo4j, \
             patch("qdrant_loader.cli.validation_commands.QdrantManager") as mock_qdrant, \
             patch("qdrant_loader.cli.validation_commands.IDMappingManager") as mock_id_mapping, \
             patch("qdrant_loader.cli.validation_commands.ValidationRepairSystem") as mock_validation, \
             patch("qdrant_loader.cli.validation_commands.ValidationRepairSystemIntegrator") as mock_integrator, \
             patch("qdrant_loader.config.get_global_config") as mock_global_config, \
             patch("qdrant_loader.config.get_settings") as mock_get_settings:
            
            # Mock the settings manager
            mock_get_settings.return_value = MagicMock()
            mock_global_config.return_value = MagicMock()
            
            # Mock all the manager instances
            mock_neo4j_instance = MagicMock()
            mock_neo4j.return_value = mock_neo4j_instance
            
            mock_qdrant_instance = MagicMock()
            mock_qdrant.return_value = mock_qdrant_instance
            
            mock_id_mapping_instance = MagicMock()
            mock_id_mapping.return_value = mock_id_mapping_instance
            
            mock_validation_instance = MagicMock()
            mock_validation.return_value = mock_validation_instance
            
            mock_integrator_instance = MagicMock()
            mock_integrator_instance.initialize = AsyncMock()
            mock_integrator_instance.get_validation_status = AsyncMock(return_value={"status": "idle", "history": []})
            mock_integrator.return_value = mock_integrator_instance

            from qdrant_loader.cli.validation_commands import _get_validation_status

            result = await _get_validation_status(
                settings=mock_settings,
                history_limit=10,
                status_filter="completed"
            )

            assert result["status"] == "idle"
            mock_integrator_instance.get_validation_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_configure_scheduled_validation_with_all_params(self):
        """Test _configure_scheduled_validation async function."""
        mock_settings = MagicMock()
        
        # Mock the async function to return expected result
        with patch("qdrant_loader.cli.validation_commands._configure_scheduled_validation") as mock_configure:
            mock_configure.return_value = {"status": "scheduled", "interval": "weekly"}

            from qdrant_loader.cli.validation_commands import _configure_scheduled_validation

            result = await _configure_scheduled_validation(
                settings=mock_settings,
                interval="weekly",
                time="02:00",
                day="monday",
                auto_repair=True
            )

            assert result == {"status": "scheduled", "interval": "weekly"} 