"""Tests for CLI module."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from click.testing import CliRunner
from qdrant_loader_mcp_server.cli import _setup_logging, cli
from qdrant_loader_mcp_server.utils import get_version


class TestVersionDetection:
    """Test version detection functionality."""

    @patch("qdrant_loader_mcp_server.utils.version.Path")
    @patch("builtins.open", new_callable=mock_open)
    @patch("qdrant_loader_mcp_server.utils.version.tomli.load")
    def test_get_version_from_package_dir(self, mock_tomli_load, mock_file, mock_path):
        """Test version detection from package directory."""
        # Mock the path structure
        mock_current_dir = MagicMock()
        mock_pyproject_path = MagicMock()
        mock_pyproject_path.exists.return_value = True
        mock_current_dir.__truediv__.return_value = mock_pyproject_path
        mock_path.return_value.parent = mock_current_dir

        # Mock tomli loading
        mock_tomli_load.return_value = {"project": {"version": "1.2.3"}}

        version = get_version()
        assert version == "1.2.3"

    @patch("qdrant_loader_mcp_server.utils.version.Path")
    @patch("builtins.open", new_callable=mock_open)
    @patch("qdrant_loader_mcp_server.utils.version.tomli.load")
    def test_get_version_from_workspace_root(
        self, mock_tomli_load, mock_file, mock_path
    ):
        """Test version detection from workspace root."""
        # Mock package directory not found, but workspace root found
        mock_current_dir = MagicMock()
        mock_pyproject_path = MagicMock()
        mock_pyproject_path.exists.side_effect = [
            False,
            False,
            False,
            False,
            False,
            True,
        ]
        mock_current_dir.__truediv__.return_value = mock_pyproject_path
        mock_path.return_value.parent = mock_current_dir

        # Mock workspace root
        mock_workspace_root = MagicMock()
        mock_workspace_pyproject = MagicMock()
        mock_workspace_pyproject.exists.return_value = True
        mock_workspace_root.__truediv__.return_value = mock_workspace_pyproject
        mock_path.cwd.return_value = mock_workspace_root

        # Mock tomli loading
        mock_tomli_load.return_value = {"project": {"version": "2.0.0"}}

        version = get_version()
        assert version == "2.0.0"

    @patch("qdrant_loader_mcp_server.utils.version.Path")
    def test_get_version_not_found(self, mock_path):
        """Test version detection when pyproject.toml is not found."""
        # Mock all paths not existing
        mock_pyproject_path = MagicMock()
        mock_pyproject_path.exists.return_value = False
        mock_path.return_value.parent.__truediv__.return_value = mock_pyproject_path
        mock_path.cwd.return_value.__truediv__.return_value = mock_pyproject_path

        version = get_version()
        assert version == "Unknown"

    @patch("qdrant_loader_mcp_server.utils.version.Path")
    @patch("builtins.open", side_effect=Exception("File error"))
    def test_get_version_exception_handling(self, mock_file, mock_path):
        """Test version detection with file reading exception."""
        mock_pyproject_path = MagicMock()
        mock_pyproject_path.exists.return_value = True
        mock_path.return_value.parent.__truediv__.return_value = mock_pyproject_path

        version = get_version()
        assert version == "Unknown"


class TestLoggingSetup:
    """Test logging setup functionality."""

    @patch("qdrant_loader_mcp_server.cli.LoggingConfig")
    @patch.dict(os.environ, {}, clear=True)
    def test_setup_logging_console_enabled(self, mock_logging_config):
        """Test logging setup with console logging enabled."""
        # Mock that LoggingConfig is not initialized and has no reconfigure method
        mock_logging_config._initialized = False
        mock_logging_config.reconfigure = None

        _setup_logging("DEBUG")

        mock_logging_config.setup.assert_called_once_with(
            level="DEBUG", format="console"
        )

    @patch("qdrant_loader_mcp_server.cli.LoggingConfig")
    @patch.dict(os.environ, {"MCP_DISABLE_CONSOLE_LOGGING": "true"})
    def test_setup_logging_console_disabled(self, mock_logging_config):
        """Test logging setup with console logging disabled."""
        # Mock that LoggingConfig is not initialized and has no reconfigure method
        mock_logging_config._initialized = False
        mock_logging_config.reconfigure = None

        _setup_logging("INFO")

        mock_logging_config.setup.assert_called_once_with(level="INFO", format="json")

    @patch("qdrant_loader_mcp_server.cli.LoggingConfig")
    @patch.dict(os.environ, {"MCP_DISABLE_CONSOLE_LOGGING": "TRUE"})
    def test_setup_logging_console_disabled_case_insensitive(self, mock_logging_config):
        """Test logging setup with case insensitive console logging disable."""
        # Mock that LoggingConfig is not initialized and has no reconfigure method
        mock_logging_config._initialized = False
        mock_logging_config.reconfigure = None

        _setup_logging("WARNING")

        mock_logging_config.setup.assert_called_once_with(
            level="WARNING", format="json"
        )

    @patch("qdrant_loader_mcp_server.cli.LoggingConfig")
    @patch("builtins.print")
    def test_setup_logging_exception_handling(self, mock_print, mock_logging_config):
        """Test logging setup exception handling."""
        # Mock that LoggingConfig is not initialized and has no reconfigure method
        mock_logging_config._initialized = False
        mock_logging_config.reconfigure = None
        mock_logging_config.setup.side_effect = Exception("Logging error")

        _setup_logging("ERROR")

        mock_print.assert_called_once_with(
            "Failed to setup logging: Logging error", file=sys.stderr
        )


class TestCLICommand:
    """Test CLI command functionality."""

    def test_cli_help(self):
        """Test CLI help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "QDrant Loader MCP Server" in result.output
        assert "--log-level" in result.output
        assert "--config" in result.output

    def test_cli_version(self):
        """Test CLI version output."""
        # Don't mock _get_version, use the actual version from pyproject.toml
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        # Just check that it contains the expected format, not the exact version
        assert "QDrant Loader MCP Server v" in result.output

    def test_cli_invalid_log_level(self):
        """Test CLI with invalid log level."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--log-level", "INVALID"])

        assert result.exit_code != 0
        assert "Invalid value for '--log-level'" in result.output

    @patch("qdrant_loader_mcp_server.cli._setup_logging")
    @patch("qdrant_loader_mcp_server.cli.load_config")
    @patch("qdrant_loader_mcp_server.fastmcp_app.mcp.run")
    def test_cli_stdio_uses_fastmcp(
        self, mock_run, mock_load_config, mock_setup_logging
    ):
        """stdio transport (default) hands off to the FastMCP stdio runner."""
        mock_load_config.return_value = (MagicMock(), {"dummy": True}, None)

        runner = CliRunner()
        result = runner.invoke(cli, ["--log-level", "DEBUG"])

        assert result.exit_code == 0
        mock_setup_logging.assert_called_once_with("DEBUG", "stdio")
        mock_run.assert_called_once()
        assert mock_run.call_args.kwargs.get("transport") == "stdio"

    @patch("qdrant_loader_mcp_server.cli._setup_logging")
    @patch("qdrant_loader_mcp_server.cli.load_config")
    @patch("uvicorn.run")
    def test_cli_http_uses_fastmcp_app(
        self, mock_uvicorn_run, mock_load_config, mock_setup_logging
    ):
        """http transport serves the module-level FastMCP ASGI app via uvicorn."""
        mock_load_config.return_value = (MagicMock(), {"dummy": True}, None)

        runner = CliRunner()
        result = runner.invoke(cli, ["--transport", "http", "--port", "9999"])

        assert result.exit_code == 0
        mock_uvicorn_run.assert_called_once()
        assert (
            mock_uvicorn_run.call_args.args[0]
            == "qdrant_loader_mcp_server.fastmcp_app:http_app"
        )

    @patch("qdrant_loader_mcp_server.cli._setup_logging")
    @patch("qdrant_loader_mcp_server.cli.load_config")
    @patch("sys.exit")
    def test_cli_exception_handling(
        self, mock_exit, mock_load_config, mock_setup_logging
    ):
        """Config resolution failure exits with code 1."""
        mock_load_config.side_effect = Exception("Config error")

        runner = CliRunner()
        runner.invoke(cli, [])

        assert mock_exit.call_count >= 1
        exit_calls = [call[0][0] for call in mock_exit.call_args_list if call[0]]
        assert 1 in exit_calls

    def test_cli_config_file_option(self):
        """Test CLI with config file option."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create a dummy config file
            config_file = Path("config.toml")
            config_file.write_text("[test]\nkey = 'value'")

            # Test that the option accepts the file
            result = runner.invoke(cli, ["--config", str(config_file), "--help"])
            assert result.exit_code == 0

    def test_cli_nonexistent_config_file(self):
        """Test CLI with nonexistent config file."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--config", "nonexistent.toml"])

        assert result.exit_code != 0
