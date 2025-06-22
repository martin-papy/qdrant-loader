"""Tests for CLI configuration commands."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner
from qdrant_loader.cli.config_commands import (
    check_config,
    config_command,
    config_group,
    export_config,
    init_config,
    show_config,
    validate_config,
)


@pytest.fixture
def cli_runner():
    """Provide CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def temp_config_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_settings():
    """Create mock settings object."""
    mock_settings = Mock()
    mock_settings.model_dump.return_value = {"test": "config"}
    mock_settings.global_config = Mock()
    mock_settings.global_config.qdrant = Mock()
    mock_settings.projects_config = Mock()
    mock_settings.projects_config.projects = {"test": Mock()}
    return mock_settings


class TestShowConfig:
    """Test show config command."""

    @patch("qdrant_loader.cli.config_commands.check_settings")
    @patch("qdrant_loader.cli.config_commands.load_config_with_workspace")
    @patch("qdrant_loader.cli.config_commands.setup_logging")
    @patch("qdrant_loader.cli.config_commands.validate_workspace_flags")
    def test_show_config_basic(
        self,
        mock_validate,
        mock_setup_logging,
        mock_load_config,
        mock_check_settings,
        cli_runner,
        mock_settings,
    ):
        """Test basic show config command."""
        mock_check_settings.return_value = mock_settings

        result = cli_runner.invoke(show_config)

        assert result.exit_code == 0
        assert "Current Configuration:" in result.output
        mock_validate.assert_called_once()
        mock_setup_logging.assert_called_once()
        mock_load_config.assert_called_once()

    @patch("qdrant_loader.cli.config_commands.check_settings")
    @patch("qdrant_loader.cli.config_commands.load_config_with_workspace")
    @patch("qdrant_loader.cli.config_commands.setup_logging")
    @patch("qdrant_loader.cli.config_commands.setup_workspace")
    @patch("qdrant_loader.cli.config_commands.validate_workspace_flags")
    def test_show_config_with_workspace(
        self,
        mock_validate,
        mock_setup_workspace,
        mock_setup_logging,
        mock_load_config,
        mock_check_settings,
        cli_runner,
        mock_settings,
        temp_config_dir,
    ):
        """Test show config with workspace option."""
        mock_check_settings.return_value = mock_settings
        # Mock workspace config with proper structure
        mock_workspace_config = Mock()
        mock_workspace_config.workspace_path = temp_config_dir
        mock_workspace_config.config_path = temp_config_dir / "config.yaml"
        mock_setup_workspace.return_value = mock_workspace_config

        result = cli_runner.invoke(show_config, ["--workspace", str(temp_config_dir)])

        assert result.exit_code == 0
        mock_setup_workspace.assert_called_once_with(temp_config_dir)

    @patch("qdrant_loader.cli.config_commands.check_settings")
    @patch("qdrant_loader.cli.config_commands.load_config_with_workspace")
    @patch("qdrant_loader.cli.config_commands.setup_logging")
    @patch("qdrant_loader.cli.config_commands.validate_workspace_flags")
    def test_show_config_with_domains(
        self,
        mock_validate,
        mock_setup_logging,
        mock_load_config,
        mock_check_settings,
        cli_runner,
        mock_settings,
    ):
        """Test show config with domains filter."""
        mock_check_settings.return_value = mock_settings

        result = cli_runner.invoke(show_config, ["--domains", "test_domain"])

        assert result.exit_code == 0
        mock_load_config.assert_called_once()
        call_args = mock_load_config.call_args[1]
        assert call_args["domains"] == "test_domain"

    @patch("qdrant_loader.cli.config_commands.validate_workspace_flags")
    def test_show_config_error_handling(self, mock_validate, cli_runner):
        """Test show config error handling."""
        mock_validate.side_effect = Exception("Test error")

        result = cli_runner.invoke(show_config)

        assert result.exit_code == 1
        assert "Failed to display configuration" in result.output


class TestValidateConfig:
    """Test validate config command."""

    @patch("qdrant_loader.cli.config_commands.check_settings")
    @patch("qdrant_loader.cli.config_commands.load_config_with_workspace")
    @patch("qdrant_loader.cli.config_commands.setup_logging")
    @patch("qdrant_loader.cli.config_commands.get_logger")
    @patch("qdrant_loader.cli.config_commands.validate_workspace_flags")
    def test_validate_config_basic(
        self,
        mock_validate,
        mock_get_logger,
        mock_setup_logging,
        mock_load_config,
        mock_check_settings,
        cli_runner,
        mock_settings,
    ):
        """Test basic config validation."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_check_settings.return_value = mock_settings

        result = cli_runner.invoke(validate_config)

        assert result.exit_code == 0
        assert "Configuration validation passed!" in result.output
        mock_load_config.assert_called_once()
        call_args = mock_load_config.call_args[1]
        assert call_args["skip_validation"] is False

    @patch("qdrant_loader.cli.config_commands.check_settings")
    @patch("qdrant_loader.cli.config_commands.load_config_with_workspace")
    @patch("qdrant_loader.cli.config_commands.setup_logging")
    @patch("qdrant_loader.cli.config_commands.get_logger")
    @patch("qdrant_loader.cli.config_commands.validate_workspace_flags")
    def test_validate_config_strict_mode(
        self,
        mock_validate,
        mock_get_logger,
        mock_setup_logging,
        mock_load_config,
        mock_check_settings,
        cli_runner,
        mock_settings,
    ):
        """Test config validation in strict mode."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_check_settings.return_value = mock_settings

        result = cli_runner.invoke(validate_config, ["--strict"])

        assert result.exit_code == 0
        assert "Running strict validation checks" in result.output

    @patch("qdrant_loader.cli.config_commands.check_settings")
    @patch("qdrant_loader.cli.config_commands.load_config_with_workspace")
    @patch("qdrant_loader.cli.config_commands.setup_logging")
    @patch("qdrant_loader.cli.config_commands.get_logger")
    @patch("qdrant_loader.cli.config_commands.validate_workspace_flags")
    def test_validate_config_strict_mode_errors(
        self,
        mock_validate,
        mock_get_logger,
        mock_setup_logging,
        mock_load_config,
        mock_check_settings,
        cli_runner,
    ):
        """Test config validation strict mode with validation errors."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Mock settings with missing required sections
        mock_settings = Mock()
        mock_settings.global_config = None
        mock_settings.projects_config = None
        mock_check_settings.return_value = mock_settings

        result = cli_runner.invoke(validate_config, ["--strict"])

        assert result.exit_code == 1
        assert "Missing global configuration section" in result.output
        assert "No projects defined in configuration" in result.output

    @patch("qdrant_loader.cli.config_commands.validate_workspace_flags")
    def test_validate_config_error_handling(self, mock_validate, cli_runner):
        """Test validate config error handling."""
        mock_validate.side_effect = Exception("Test error")

        result = cli_runner.invoke(validate_config)

        assert result.exit_code == 1
        assert "Configuration validation failed" in result.output


class TestInitConfig:
    """Test init config command."""

    @patch("qdrant_loader.cli.config_commands.setup_logging")
    @patch("qdrant_loader.cli.config_commands.setup_workspace")
    @patch("qdrant_loader.cli.config_commands.get_logger")
    def test_init_config_basic_template(
        self,
        mock_get_logger,
        mock_setup_workspace,
        mock_setup_logging,
        cli_runner,
        temp_config_dir,
    ):
        """Test init config with basic template."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        # Mock workspace config with proper structure
        mock_workspace_config = Mock()
        mock_workspace_config.workspace_path = temp_config_dir
        mock_workspace_config.config_path = temp_config_dir / "config.yaml"
        mock_setup_workspace.return_value = mock_workspace_config

        result = cli_runner.invoke(init_config, ["--workspace", str(temp_config_dir)])

        # This should fail because template creation is not implemented
        assert result.exit_code == 1
        assert "Configuration template creation not yet implemented" in result.output
        mock_setup_workspace.assert_called_once()

    @patch("qdrant_loader.cli.config_commands.setup_logging")
    @patch("qdrant_loader.cli.config_commands.setup_workspace")
    @patch("qdrant_loader.cli.config_commands.get_logger")
    def test_init_config_advanced_template(
        self,
        mock_get_logger,
        mock_setup_workspace,
        mock_setup_logging,
        cli_runner,
        temp_config_dir,
    ):
        """Test init config with advanced template."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        # Mock workspace config with proper structure
        mock_workspace_config = Mock()
        mock_workspace_config.workspace_path = temp_config_dir
        mock_workspace_config.config_path = temp_config_dir / "config.yaml"
        mock_setup_workspace.return_value = mock_workspace_config

        result = cli_runner.invoke(
            init_config,
            ["--workspace", str(temp_config_dir), "--template", "advanced"],
        )

        # This should fail because template creation is not implemented
        assert result.exit_code == 1
        assert "Configuration template creation not yet implemented" in result.output

    @patch("qdrant_loader.cli.config_commands.setup_logging")
    @patch("qdrant_loader.cli.config_commands.setup_workspace")
    @patch("qdrant_loader.cli.config_commands.get_logger")
    def test_init_config_with_force(
        self,
        mock_get_logger,
        mock_setup_workspace,
        mock_setup_logging,
        cli_runner,
        temp_config_dir,
    ):
        """Test init config with force flag."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        # Mock workspace config with proper structure
        mock_workspace_config = Mock()
        mock_workspace_config.workspace_path = temp_config_dir
        mock_workspace_config.config_path = temp_config_dir / "config.yaml"
        mock_setup_workspace.return_value = mock_workspace_config

        result = cli_runner.invoke(
            init_config,
            ["--workspace", str(temp_config_dir), "--force"],
        )

        # This should fail because template creation is not implemented
        assert result.exit_code == 1
        assert "Configuration template creation not yet implemented" in result.output

    def test_init_config_error_handling(self, cli_runner):
        """Test init config error handling."""
        with patch(
            "qdrant_loader.cli.config_commands.setup_logging",
            side_effect=Exception("Test error"),
        ):
            result = cli_runner.invoke(init_config)

            assert result.exit_code == 1
            assert "Failed to initialize configuration" in result.output


class TestExportConfig:
    """Test export config command."""

    @patch("qdrant_loader.cli.config_commands.setup_logging")
    @patch("qdrant_loader.cli.config_commands.setup_workspace")
    @patch("qdrant_loader.cli.config_commands.get_logger")
    @patch("qdrant_loader.config.hot_reload.HotReloadConfigLoader")
    def test_export_config_yaml_format(
        self,
        mock_loader_class,
        mock_get_logger,
        mock_setup_workspace,
        mock_setup_logging,
        cli_runner,
        temp_config_dir,
    ):
        """Test export config in YAML format."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        # Mock workspace config with proper structure
        mock_workspace_config = Mock()
        mock_workspace_config.workspace_path = temp_config_dir
        mock_workspace_config.config_path = temp_config_dir / "config.yaml"
        mock_setup_workspace.return_value = mock_workspace_config

        # Mock the config loader
        mock_loader = Mock()
        mock_loader.export_config_with_sources.return_value = "test: config"
        mock_loader_class.return_value = mock_loader

        # Create mock config files
        config_dir = temp_config_dir / "config"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "connectivity.yaml").write_text("qdrant:\n  url: test")
        (config_dir / "projects.yaml").write_text("projects:\n  test: {}")

        result = cli_runner.invoke(
            export_config,
            ["--workspace", str(temp_config_dir), "--config-dir", str(config_dir)],
        )

        assert result.exit_code == 0

    @patch("qdrant_loader.cli.config_commands.setup_logging")
    @patch("qdrant_loader.cli.config_commands.setup_workspace")
    @patch("qdrant_loader.cli.config_commands.get_logger")
    @patch("qdrant_loader.config.hot_reload.HotReloadConfigLoader")
    def test_export_config_json_format(
        self,
        mock_loader_class,
        mock_get_logger,
        mock_setup_workspace,
        mock_setup_logging,
        cli_runner,
        temp_config_dir,
    ):
        """Test export config in JSON format."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        # Mock workspace config with proper structure
        mock_workspace_config = Mock()
        mock_workspace_config.workspace_path = temp_config_dir
        mock_workspace_config.config_path = temp_config_dir / "config.yaml"
        mock_setup_workspace.return_value = mock_workspace_config

        # Mock the config loader
        mock_loader = Mock()
        mock_loader.export_config_with_sources.return_value = '{"test": "config"}'
        mock_loader_class.return_value = mock_loader

        # Create mock config files
        config_dir = temp_config_dir / "config"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "connectivity.yaml").write_text("qdrant:\n  url: test")

        result = cli_runner.invoke(
            export_config,
            [
                "--workspace",
                str(temp_config_dir),
                "--config-dir",
                str(config_dir),
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0

    @patch("qdrant_loader.cli.config_commands.setup_logging")
    @patch("qdrant_loader.cli.config_commands.setup_workspace")
    @patch("qdrant_loader.cli.config_commands.get_logger")
    @patch("qdrant_loader.config.hot_reload.HotReloadConfigLoader")
    def test_export_config_to_file(
        self,
        mock_loader_class,
        mock_get_logger,
        mock_setup_workspace,
        mock_setup_logging,
        cli_runner,
        temp_config_dir,
    ):
        """Test export config to output file."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        # Mock workspace config with proper structure
        mock_workspace_config = Mock()
        mock_workspace_config.workspace_path = temp_config_dir
        mock_workspace_config.config_path = temp_config_dir / "config.yaml"
        mock_setup_workspace.return_value = mock_workspace_config

        # Mock the config loader
        mock_loader = Mock()
        mock_loader.export_config_with_sources.return_value = "test: config"
        mock_loader_class.return_value = mock_loader

        # Create mock config files
        config_dir = temp_config_dir / "config"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "connectivity.yaml").write_text("qdrant:\n  url: test")

        output_file = temp_config_dir / "exported_config.yaml"

        result = cli_runner.invoke(
            export_config,
            [
                "--workspace",
                str(temp_config_dir),
                "--config-dir",
                str(config_dir),
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == 0

    def test_export_config_error_handling(self, cli_runner):
        """Test export config error handling."""
        with (
            patch("qdrant_loader.cli.config_commands.setup_logging"),
            patch("qdrant_loader.cli.config_commands.get_logger"),
            patch(
                "qdrant_loader.config.hot_reload.HotReloadConfigLoader",
                side_effect=Exception("Test error"),
            ),
        ):
            result = cli_runner.invoke(export_config)

            assert result.exit_code == 1
            assert "Failed to export configuration" in result.output


class TestCheckConfig:
    """Test check config command."""

    @patch("qdrant_loader.cli.config_commands.check_settings")
    @patch("qdrant_loader.cli.config_commands.load_config_with_workspace")
    @patch("qdrant_loader.cli.config_commands.setup_logging")
    @patch("qdrant_loader.cli.config_commands.get_logger")
    @patch("qdrant_loader.cli.config_commands.validate_workspace_flags")
    @patch("qdrant_loader.config.legacy_detection.detect_legacy_configuration")
    def test_check_config_basic(
        self,
        mock_detect_legacy,
        mock_validate,
        mock_get_logger,
        mock_setup_logging,
        mock_load_config,
        mock_check_settings,
        cli_runner,
        mock_settings,
        temp_config_dir,
    ):
        """Test basic config check."""
        mock_check_settings.return_value = mock_settings
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_detect_legacy.return_value = (False, None, None)

        # Create a mock config file
        config_file = temp_config_dir / "config.yaml"
        config_file.write_text("test: config")

        result = cli_runner.invoke(check_config, ["--config", str(config_file)])

        assert result.exit_code == 0
        assert "Configuration check completed successfully" in result.output

    @patch("qdrant_loader.cli.config_commands.validate_workspace_flags")
    def test_check_config_error_handling(self, mock_validate, cli_runner):
        """Test check config error handling."""
        mock_validate.side_effect = Exception("Test error")

        result = cli_runner.invoke(check_config)

        assert result.exit_code == 1
        assert "Failed to check configuration" in result.output


class TestConfigCommand:
    """Test main config command."""

    @patch("qdrant_loader.cli.config_commands.show_config")
    def test_config_command_basic(
        self,
        mock_show_config,
        cli_runner,
    ):
        """Test basic config command."""
        result = cli_runner.invoke(config_command)

        assert result.exit_code == 0
        mock_show_config.assert_called_once()

    def test_config_command_error_handling(self, cli_runner):
        """Test config command error handling."""
        with patch(
            "qdrant_loader.cli.config_commands.validate_workspace_flags",
            side_effect=Exception("Test error"),
        ):
            result = cli_runner.invoke(config_command)

            assert result.exit_code == 1


class TestConfigGroup:
    """Test config group command."""

    def test_config_group_help(self, cli_runner):
        """Test config group help command."""
        result = cli_runner.invoke(config_group, ["--help"])

        assert result.exit_code == 0
        assert "Configuration management commands" in result.output

    def test_config_group_subcommands(self, cli_runner):
        """Test config group has expected subcommands."""
        result = cli_runner.invoke(config_group, ["--help"])

        assert "show" in result.output
        assert "validate" in result.output
        assert "init" in result.output
        assert "export" in result.output
        assert "check" in result.output


class TestIntegrationScenarios:
    """Test integration scenarios for config commands."""

    @patch("qdrant_loader.cli.config_commands.check_settings")
    @patch("qdrant_loader.cli.config_commands.load_config_with_workspace")
    @patch("qdrant_loader.cli.config_commands.setup_logging")
    @patch("qdrant_loader.cli.config_commands.setup_workspace")
    @patch("qdrant_loader.cli.config_commands.validate_workspace_flags")
    def test_full_config_workflow(
        self,
        mock_validate,
        mock_setup_workspace,
        mock_setup_logging,
        mock_load_config,
        mock_check_settings,
        cli_runner,
        mock_settings,
        temp_config_dir,
    ):
        """Test full configuration workflow."""
        mock_check_settings.return_value = mock_settings
        # Mock workspace config with proper structure
        mock_workspace_config = Mock()
        mock_workspace_config.workspace_path = temp_config_dir
        mock_workspace_config.config_path = temp_config_dir / "config.yaml"
        mock_setup_workspace.return_value = mock_workspace_config

        # Initialize config (should fail because not implemented)
        result = cli_runner.invoke(init_config, ["--workspace", str(temp_config_dir)])
        assert result.exit_code == 1

        # Show config
        result = cli_runner.invoke(show_config, ["--workspace", str(temp_config_dir)])
        assert result.exit_code == 0

        # Validate config
        result = cli_runner.invoke(
            validate_config, ["--workspace", str(temp_config_dir)]
        )
        assert result.exit_code == 0

        # Check config - create a mock config file first
        config_file = temp_config_dir / "config.yaml"
        config_file.write_text("test: config")
        with patch(
            "qdrant_loader.config.legacy_detection.detect_legacy_configuration"
        ) as mock_detect:
            mock_detect.return_value = (False, None, None)
            result = cli_runner.invoke(check_config, ["--config", str(config_file)])
            assert result.exit_code == 0
