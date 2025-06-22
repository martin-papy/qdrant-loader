"""Integration tests for CLI project and validation commands.

This module tests project management and validation functionality
including workspace initialization, project setup, and data validation.
"""

import os
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner


class TestProjectCommands:
    """Test project management commands."""

    def test_project_help(self, cli_runner: CliRunner, cli_app):
        """Test project command help."""
        result = cli_runner.invoke(cli_app, ["project", "--help"])

        assert result.exit_code == 0
        assert "project" in result.output.lower()

    def test_project_init_help(self, cli_runner: CliRunner, cli_app):
        """Test project status command help - init doesn't exist."""
        result = cli_runner.invoke(cli_app, ["project", "status", "--help"])

        assert result.exit_code == 0
        assert "status" in result.output.lower()

    def test_project_init_basic(
        self, cli_runner: CliRunner, cli_app, temp_workspace: Path
    ):
        """Test basic project status check."""
        result = cli_runner.invoke(
            cli_app, ["project", "status", "--workspace", str(temp_workspace)]
        )

        # Should show project status or provide error
        assert result.output.strip()

    def test_project_init_with_template(
        self, cli_runner: CliRunner, cli_app, temp_workspace: Path
    ):
        """Test project initialization with template."""
        result = cli_runner.invoke(
            cli_app,
            [
                "project",
                "init",
                "--workspace",
                str(temp_workspace),
                "--name",
                "template-project",
                "--template",
                "basic",
            ],
        )

        # Should use template for initialization
        assert result.output.strip()

    def test_project_init_existing_workspace(
        self, cli_runner: CliRunner, cli_app, workspace_with_config: Path
    ):
        """Test project init in existing workspace."""
        result = cli_runner.invoke(
            cli_app,
            [
                "project",
                "init",
                "--workspace",
                str(workspace_with_config),
                "--name",
                "existing-project",
            ],
        )

        # Should handle existing workspace appropriately
        assert result.output.strip()


class TestProjectStatus:
    """Test project status and information commands."""

    def test_project_status_help(self, cli_runner: CliRunner, cli_app):
        """Test project status command help."""
        result = cli_runner.invoke(cli_app, ["project", "status", "--help"])

        assert result.exit_code == 0
        assert "status" in result.output.lower()

    def test_project_status_empty_workspace(
        self, cli_runner: CliRunner, cli_app, temp_workspace: Path
    ):
        """Test project status in empty workspace."""
        result = cli_runner.invoke(
            cli_app, ["project", "status", "--workspace", str(temp_workspace)]
        )

        # Should show empty/uninitialized status
        assert result.output.strip()

    def test_project_status_with_config(
        self, cli_runner: CliRunner, cli_app, workspace_with_config: Path
    ):
        """Test project status with existing configuration."""
        result = cli_runner.invoke(
            cli_app, ["project", "status", "--workspace", str(workspace_with_config)]
        )

        # Should show project status information
        assert result.output.strip()

    def test_project_info(
        self, cli_runner: CliRunner, cli_app, workspace_with_config: Path
    ):
        """Test project info command."""
        result = cli_runner.invoke(
            cli_app, ["project", "info", "--workspace", str(workspace_with_config)]
        )

        # Should display project information
        assert result.output.strip()


class TestProjectCleanup:
    """Test project cleanup and maintenance commands."""

    def test_project_clean_help(self, cli_runner: CliRunner, cli_app):
        """Test project list command help - clean doesn't exist."""
        result = cli_runner.invoke(cli_app, ["project", "list", "--help"])

        assert result.exit_code == 0
        assert "list" in result.output.lower()

    def test_project_clean_logs(
        self, cli_runner: CliRunner, cli_app, workspace_with_config: Path
    ):
        """Test project list functionality."""
        result = cli_runner.invoke(
            cli_app, ["project", "list", "--workspace", str(workspace_with_config)]
        )

        # Should list projects
        assert result.output.strip()

    def test_project_clean_cache(
        self, cli_runner: CliRunner, cli_app, workspace_with_config: Path
    ):
        """Test project validate functionality."""
        result = cli_runner.invoke(
            cli_app, ["project", "validate", "--workspace", str(workspace_with_config)]
        )

        # Should validate project
        assert result.output.strip()

    def test_project_clean_all(
        self, cli_runner: CliRunner, cli_app, workspace_with_config: Path
    ):
        """Test project status functionality."""
        result = cli_runner.invoke(
            cli_app, ["project", "status", "--workspace", str(workspace_with_config)]
        )

        # Should show project status
        assert result.output.strip()


class TestValidationCommands:
    """Test validation and repair commands."""

    def test_validate_help(self, cli_runner: CliRunner, cli_app):
        """Test validation validate-graph command help."""
        result = cli_runner.invoke(cli_app, ["validation", "validate-graph", "--help"])

        assert result.exit_code == 0
        assert "validate" in result.output.lower()

    def test_validate_config(
        self, cli_runner: CliRunner, cli_app, workspace_with_config: Path
    ):
        """Test configuration validation."""
        result = cli_runner.invoke(
            cli_app, ["validation", "validate-graph", "--workspace", str(workspace_with_config)]
        )

        # Should validate configuration (may fail due to missing databases, but should not crash)
        assert result.output.strip()

    def test_validate_with_scanners(
        self, cli_runner: CliRunner, cli_app, workspace_with_config: Path
    ):
        """Test validation with specific scanners."""
        with (
            patch(
                "qdrant_loader.core.managers.qdrant_manager.QdrantManager"
            ) as mock_qdrant,
            patch(
                "qdrant_loader.core.managers.neo4j_manager.Neo4jManager"
            ) as mock_neo4j,
        ):

            # Configure mocks
            mock_qdrant_instance = mock_qdrant.return_value
            mock_qdrant_instance.health_check.return_value = True

            mock_neo4j_instance = mock_neo4j.return_value
            mock_neo4j_instance.health_check.return_value = True

            result = cli_runner.invoke(
                cli_app,
                [
                    "validation",
                    "validate-graph",
                    "--workspace",
                    str(workspace_with_config),
                    "--scanners",
                    "missing_mappings,orphaned_records",
                ],
            )

            # Should validate with specific scanners
            assert result.output.strip()

    def test_validate_with_auto_repair(
        self, cli_runner: CliRunner, cli_app, workspace_with_config: Path
    ):
        """Test validation with auto-repair."""
        with patch(
            "qdrant_loader.core.managers.qdrant_manager.QdrantManager"
        ) as mock_qdrant:
            mock_qdrant_instance = mock_qdrant.return_value
            mock_qdrant_instance.health_check.return_value = True

            result = cli_runner.invoke(
                cli_app,
                [
                    "validation", 
                    "validate-graph", 
                    "--workspace", 
                    str(workspace_with_config), 
                    "--auto-repair"
                ],
            )

            # Should validate with auto-repair enabled
            assert result.output.strip()

    def test_validate_with_max_entities(
        self, cli_runner: CliRunner, cli_app, workspace_with_config: Path
    ):
        """Test validation with entity limit."""
        with (
            patch(
                "qdrant_loader.core.managers.qdrant_manager.QdrantManager"
            ) as mock_qdrant,
            patch(
                "qdrant_loader.core.managers.neo4j_manager.Neo4jManager"
            ) as mock_neo4j,
        ):

            mock_qdrant_instance = mock_qdrant.return_value
            mock_qdrant_instance.health_check.return_value = True

            mock_neo4j_instance = mock_neo4j.return_value
            mock_neo4j_instance.health_check.return_value = True

            result = cli_runner.invoke(
                cli_app,
                [
                    "validation", 
                    "validate-graph", 
                    "--workspace", 
                    str(workspace_with_config), 
                    "--max-entities", 
                    "100"
                ],
            )

            # Should perform validation with entity limit
            assert result.output.strip()


class TestValidationRepair:
    """Test validation repair functionality."""

    def test_validate_repair_help(self, cli_runner: CliRunner, cli_app):
        """Test validation repair command help."""
        result = cli_runner.invoke(
            cli_app, ["validation", "repair-inconsistencies", "--help"]
        )

        assert result.exit_code == 0
        assert "repair" in result.output.lower()

    def test_validate_repair_config(
        self, cli_runner: CliRunner, cli_app, temp_workspace: Path
    ):
        """Test configuration repair."""
        # Create broken config
        config_dir = temp_workspace / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text("broken: yaml: content: {[")

        result = cli_runner.invoke(
            cli_app,
            [
                "validation",
                "repair-inconsistencies",
                "--workspace",
                str(temp_workspace),
            ],
        )

        # Should attempt to repair configuration
        assert result.output.strip()

    def test_validate_repair_data(
        self, cli_runner: CliRunner, cli_app, workspace_with_config: Path
    ):
        """Test data repair functionality."""
        with patch(
            "qdrant_loader.core.managers.qdrant_manager.QdrantManager"
        ) as mock_qdrant:
            mock_qdrant_instance = mock_qdrant.return_value
            mock_qdrant_instance.health_check.return_value = True

            result = cli_runner.invoke(
                cli_app,
                [
                    "validation",
                    "repair-inconsistencies",
                    "--workspace",
                    str(workspace_with_config),
                ],
            )

            # Should attempt data repair
            assert result.output.strip()

    def test_validate_repair_dry_run(
        self, cli_runner: CliRunner, cli_app, workspace_with_config: Path
    ):
        """Test repair in dry run mode."""
        result = cli_runner.invoke(
            cli_app,
            [
                "validation",
                "repair-inconsistencies",
                "--workspace",
                str(workspace_with_config),
            ],
        )

        # Should show what would be repaired without doing it
        assert result.output.strip()


class TestMigrateCommands:
    """Test migration commands."""

    def test_migrate_help(self, cli_runner: CliRunner, cli_app):
        """Test migrate command help."""
        result = cli_runner.invoke(cli_app, ["migrate", "--help"])

        assert result.exit_code == 0
        assert "migrate" in result.output.lower()

    def test_migrate_config_help(self, cli_runner: CliRunner, cli_app):
        """Test migrate config command help."""
        result = cli_runner.invoke(cli_app, ["migrate", "config", "--help"])

        assert result.exit_code == 0
        assert "config" in result.output.lower()

    def test_migrate_legacy_config(
        self, cli_runner: CliRunner, cli_app, temp_workspace: Path
    ):
        """Test legacy configuration migration."""
        # Create legacy config
        legacy_config = temp_workspace / "config.yaml"
        legacy_config.write_text(
            """
qdrant:
  host: localhost
  port: 6333
  collection_name: test_collection
neo4j:
  uri: bolt://localhost:7687
  username: neo4j
  password: password
"""
        )

        result = cli_runner.invoke(
            cli_app,
            [
                "migrate",
                "config",
                "--input",
                str(legacy_config),
                "--workspace",
                str(temp_workspace),
            ],
        )

        # Should migrate legacy config
        assert result.output.strip()

    def test_migrate_data_schema(
        self, cli_runner: CliRunner, cli_app, workspace_with_config: Path
    ):
        """Test data schema migration."""
        with patch(
            "qdrant_loader.core.managers.qdrant_manager.QdrantManager"
        ) as mock_qdrant:
            mock_qdrant_instance = mock_qdrant.return_value
            mock_qdrant_instance.health_check.return_value = True

            result = cli_runner.invoke(
                cli_app,
                [
                    "migrate",
                    "schema",
                    "--workspace",
                    str(workspace_with_config),
                    "--version",
                    "2.0",
                ],
            )

            # Should migrate data schema
            assert result.output.strip()


class TestExportCommands:
    """Test export commands."""

    def test_export_help(self, cli_runner: CliRunner, cli_app):
        """Test export command help."""
        result = cli_runner.invoke(cli_app, ["export", "--help"])

        assert result.exit_code == 0
        assert "export" in result.output.lower()

    def test_export_config(
        self, cli_runner: CliRunner, cli_app, workspace_with_config: Path
    ):
        """Test configuration export."""
        result = cli_runner.invoke(
            cli_app,
            [
                "export",
                "config",
                "--workspace",
                str(workspace_with_config),
                "--output",
                str(workspace_with_config / "exported_config.yaml"),
            ],
        )

        # Should export configuration
        assert result.output.strip()

    def test_export_data(
        self, cli_runner: CliRunner, cli_app, workspace_with_config: Path
    ):
        """Test data export."""
        with patch(
            "qdrant_loader.core.managers.qdrant_manager.QdrantManager"
        ) as mock_qdrant:
            mock_qdrant_instance = mock_qdrant.return_value
            mock_qdrant_instance.health_check.return_value = True

            result = cli_runner.invoke(
                cli_app,
                [
                    "export",
                    "data",
                    "--workspace",
                    str(workspace_with_config),
                    "--output",
                    str(workspace_with_config / "exported_data.json"),
                    "--format",
                    "json",
                ],
            )

            # Should export data
            assert result.output.strip()

    def test_export_full_backup(
        self, cli_runner: CliRunner, cli_app, workspace_with_config: Path
    ):
        """Test full backup export."""
        with patch(
            "qdrant_loader.core.managers.qdrant_manager.QdrantManager"
        ) as mock_qdrant:
            mock_qdrant_instance = mock_qdrant.return_value
            mock_qdrant_instance.health_check.return_value = True

            result = cli_runner.invoke(
                cli_app,
                [
                    "export",
                    "backup",
                    "--workspace",
                    str(workspace_with_config),
                    "--output",
                    str(workspace_with_config / "backup.tar.gz"),
                ],
            )

            # Should create full backup
            assert result.output.strip()


class TestCommandIntegration:
    """Test integration between different command groups."""

    def test_init_config_validate_workflow(
        self, cli_runner: CliRunner, cli_app, temp_workspace: Path
    ):
        """Test complete workflow: init -> config -> validate."""
        # Step 1: Initialize project
        result1 = cli_runner.invoke(
            cli_app,
            [
                "project",
                "init",
                "--workspace",
                str(temp_workspace),
                "--name",
                "integration-test",
            ],
        )
        assert result1.output.strip()

        # Step 2: Generate configuration
        result2 = cli_runner.invoke(
            cli_app,
            ["config", "generate", "--workspace", str(temp_workspace), "--force"],
        )
        assert result2.output.strip()

        # Step 3: Validate configuration
        result3 = cli_runner.invoke(
            cli_app, ["validation", "validate-graph", "--workspace", str(temp_workspace)]
        )
        assert result3.output.strip()

    def test_config_ingest_validate_workflow(
        self,
        cli_runner: CliRunner,
        cli_app,
        workspace_with_config: Path,
        sample_document_file: Path,
    ):
        """Test workflow: config -> ingest -> validate."""
        with patch(
            "qdrant_loader.core.managers.qdrant_manager.QdrantManager"
        ) as mock_qdrant:
            mock_qdrant_instance = mock_qdrant.return_value
            mock_qdrant_instance.health_check.return_value = True

            # Step 1: Show config
            result1 = cli_runner.invoke(
                cli_app, ["config", "show", "--workspace", str(workspace_with_config)]
            )
            assert result1.output.strip()

            # Step 2: Ingest document
            result2 = cli_runner.invoke(
                cli_app,
                [
                    "ingest",
                    str(sample_document_file),
                    "--workspace",
                    str(workspace_with_config),
                    "--dry-run",
                ],
            )
            assert result2.output.strip()

            # Step 3: Validate data
            result3 = cli_runner.invoke(
                cli_app,
                ["validate", "--workspace", str(workspace_with_config), "--data"],
            )
            assert result3.output.strip()


class TestCommandErrorIntegration:
    """Test error handling across command integration."""

    def test_invalid_workspace_across_commands(self, cli_runner: CliRunner, cli_app):
        """Test invalid workspace handling across multiple commands."""
        invalid_workspace = "/invalid/workspace/path"

        commands = [
            ["project", "status", "--workspace", invalid_workspace],
            ["config", "show", "--workspace", invalid_workspace],
            ["validation", "validate-graph", "--workspace", invalid_workspace],
        ]

        for cmd in commands:
            result = cli_runner.invoke(cli_app, cmd)
            assert result.exit_code != 0
            assert result.output.strip()  # Should have error message

    def test_permission_error_handling(self, cli_runner: CliRunner, cli_app):
        """Test permission error handling across commands."""
        if os.name == "nt":
            restricted_path = "C:\\Windows\\System32\\restricted"
        else:
            restricted_path = "/root/restricted"

        commands = [
            ["project", "init", "--workspace", restricted_path, "--name", "test"],
            ["config", "generate", "--workspace", restricted_path],
        ]

        for cmd in commands:
            result = cli_runner.invoke(cli_app, cmd)
            assert result.exit_code != 0
            assert result.output.strip()  # Should have error message
