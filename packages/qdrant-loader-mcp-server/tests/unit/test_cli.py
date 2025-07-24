"""Tests for CLI module."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
from click.testing import CliRunner
from qdrant_loader_mcp_server.cli import (
    _get_version,
    _setup_logging,
    cli,
    handle_stdio,
    read_stdin,
    shutdown,
)


class TestVersionDetection:
    """Test version detection functionality."""

    @patch("qdrant_loader_mcp_server.cli.Path")
    @patch("builtins.open", new_callable=mock_open)
    @patch("qdrant_loader_mcp_server.cli.tomli.load")
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

        version = _get_version()
        assert version == "1.2.3"

    @patch("qdrant_loader_mcp_server.cli.Path")
    @patch("builtins.open", new_callable=mock_open)
    @patch("qdrant_loader_mcp_server.cli.tomli.load")
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

        version = _get_version()
        assert version == "2.0.0"

    @patch("qdrant_loader_mcp_server.cli.Path")
    def test_get_version_not_found(self, mock_path):
        """Test version detection when pyproject.toml is not found."""
        # Mock all paths not existing
        mock_pyproject_path = MagicMock()
        mock_pyproject_path.exists.return_value = False
        mock_path.return_value.parent.__truediv__.return_value = mock_pyproject_path
        mock_path.cwd.return_value.__truediv__.return_value = mock_pyproject_path

        version = _get_version()
        assert version == "Unknown"

    @patch("qdrant_loader_mcp_server.cli.Path")
    @patch("builtins.open", side_effect=Exception("File error"))
    def test_get_version_exception_handling(self, mock_file, mock_path):
        """Test version detection with file reading exception."""
        mock_pyproject_path = MagicMock()
        mock_pyproject_path.exists.return_value = True
        mock_path.return_value.parent.__truediv__.return_value = mock_pyproject_path

        version = _get_version()
        assert version == "Unknown"


class TestLoggingSetup:
    """Test logging setup functionality."""

    @patch("qdrant_loader_mcp_server.cli.LoggingConfig")
    @patch.dict(os.environ, {}, clear=True)
    def test_setup_logging_console_enabled(self, mock_logging_config):
        """Test logging setup with console logging enabled."""
        _setup_logging("DEBUG")

        mock_logging_config.setup.assert_called_once_with(
            level="DEBUG", format="console"
        )

    @patch("qdrant_loader_mcp_server.cli.LoggingConfig")
    @patch.dict(os.environ, {"MCP_DISABLE_CONSOLE_LOGGING": "true"})
    def test_setup_logging_console_disabled(self, mock_logging_config):
        """Test logging setup with console logging disabled."""
        _setup_logging("INFO")

        mock_logging_config.setup.assert_called_once_with(level="INFO", format="json")

    @patch("qdrant_loader_mcp_server.cli.LoggingConfig")
    @patch.dict(os.environ, {"MCP_DISABLE_CONSOLE_LOGGING": "TRUE"})
    def test_setup_logging_console_disabled_case_insensitive(self, mock_logging_config):
        """Test logging setup with case insensitive console logging disable."""
        _setup_logging("WARNING")

        mock_logging_config.setup.assert_called_once_with(
            level="WARNING", format="json"
        )

    @patch("qdrant_loader_mcp_server.cli.LoggingConfig")
    @patch("builtins.print")
    def test_setup_logging_exception_handling(self, mock_print, mock_logging_config):
        """Test logging setup exception handling."""
        mock_logging_config.setup.side_effect = Exception("Logging error")

        _setup_logging("ERROR")

        mock_print.assert_called_once_with(
            "Failed to setup logging: Logging error", file=sys.stderr
        )


class TestAsyncFunctions:
    """Test async utility functions."""

    @pytest.mark.asyncio
    async def test_read_stdin(self):
        """Test stdin reading functionality."""
        with (
            patch("asyncio.get_running_loop") as mock_get_loop,
            patch("asyncio.StreamReader") as mock_reader,
            patch("asyncio.StreamReaderProtocol") as mock_protocol,
        ):

            mock_loop = AsyncMock()
            mock_get_loop.return_value = mock_loop
            mock_reader_instance = MagicMock()
            mock_reader.return_value = mock_reader_instance
            mock_protocol_instance = MagicMock()
            mock_protocol.return_value = mock_protocol_instance

            result = await read_stdin()

            assert result == mock_reader_instance
            mock_loop.connect_read_pipe.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test graceful shutdown functionality."""
        with (
            patch("qdrant_loader_mcp_server.cli.LoggingConfig") as mock_logging_config,
            patch("asyncio.all_tasks") as mock_all_tasks,
            patch("asyncio.current_task") as mock_current_task,
            patch("asyncio.gather", new_callable=AsyncMock) as mock_gather,
        ):

            mock_logger = MagicMock()
            mock_logging_config.get_logger.return_value = mock_logger

            # Mock tasks
            mock_current = MagicMock()
            mock_task1 = MagicMock()
            mock_task2 = MagicMock()
            mock_current_task.return_value = mock_current
            mock_all_tasks.return_value = [mock_current, mock_task1, mock_task2]

            # Mock loop
            mock_loop = MagicMock()

            await shutdown(mock_loop)

            # Verify tasks were cancelled
            mock_task1.cancel.assert_called_once()
            mock_task2.cancel.assert_called_once()
            mock_current.cancel.assert_not_called()  # Current task should not be cancelled

            # Verify gather was called
            mock_gather.assert_called_once_with(
                mock_task1, mock_task2, return_exceptions=True
            )

            # Verify loop was stopped
            mock_loop.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_with_exception(self):
        """Test shutdown with exception during task gathering."""

        # Create an async function that raises an exception
        async def mock_gather_error(*args, **kwargs):
            raise Exception("Gather error")

        with (
            patch("qdrant_loader_mcp_server.cli.LoggingConfig") as mock_logging_config,
            patch("asyncio.all_tasks") as mock_all_tasks,
            patch("asyncio.current_task") as mock_current_task,
            patch("asyncio.gather", side_effect=mock_gather_error) as mock_gather,
        ):

            mock_logger = MagicMock()
            mock_logging_config.get_logger.return_value = mock_logger

            # Mock tasks
            mock_current = MagicMock()
            mock_task1 = MagicMock()
            mock_current_task.return_value = mock_current
            mock_all_tasks.return_value = [mock_current, mock_task1]

            # Mock loop
            mock_loop = MagicMock()

            await shutdown(mock_loop)

            # Verify error was logged
            mock_logger.error.assert_called_once_with(
                "Error during shutdown", exc_info=True
            )

            # Verify loop was still stopped
            mock_loop.stop.assert_called_once()


class TestStdioHandler:
    """Test stdio communication handler."""

    @pytest.mark.asyncio
    async def test_handle_stdio_initialization_error(self):
        """Test stdio handler with search engine initialization error."""

        # Create an async function that raises an exception
        async def mock_initialize_error():
            raise Exception("Init error")

        with (
            patch("qdrant_loader_mcp_server.cli.LoggingConfig") as mock_logging_config,
            patch(
                "qdrant_loader_mcp_server.cli.SearchEngine"
            ) as mock_search_engine_class,
            patch(
                "qdrant_loader_mcp_server.cli.QueryProcessor"
            ) as mock_query_processor_class,
            patch("qdrant_loader_mcp_server.cli.MCPHandler") as mock_mcp_handler_class,
            patch.dict(os.environ, {}, clear=True),
        ):

            mock_logger = MagicMock()
            mock_logging_config.get_logger.return_value = mock_logger

            # Mock search engine initialization failure
            mock_search_engine = MagicMock()
            mock_search_engine.initialize = AsyncMock(side_effect=mock_initialize_error)
            mock_search_engine_class.return_value = mock_search_engine

            mock_config = MagicMock()

            with pytest.raises(
                RuntimeError, match="Failed to initialize search engine"
            ):
                await handle_stdio(mock_config, "INFO")

    @pytest.mark.asyncio
    async def test_handle_stdio_json_parse_error(self):
        """Test stdio handler with JSON parse error."""
        with (
            patch("qdrant_loader_mcp_server.cli.LoggingConfig") as mock_logging_config,
            patch(
                "qdrant_loader_mcp_server.cli.SearchEngine"
            ) as mock_search_engine_class,
            patch(
                "qdrant_loader_mcp_server.cli.QueryProcessor"
            ) as mock_query_processor_class,
            patch("qdrant_loader_mcp_server.cli.MCPHandler") as mock_mcp_handler_class,
            patch("qdrant_loader_mcp_server.cli.read_stdin") as mock_read_stdin,
            patch("sys.stdout") as mock_stdout,
            patch.dict(os.environ, {}, clear=True),
        ):

            mock_logger = MagicMock()
            mock_logging_config.get_logger.return_value = mock_logger

            # Mock successful initialization
            mock_search_engine = MagicMock()
            mock_search_engine.initialize = AsyncMock()
            mock_search_engine.cleanup = AsyncMock()
            mock_search_engine_class.return_value = mock_search_engine

            # Mock reader with invalid JSON
            mock_reader = MagicMock()
            mock_reader.readline = AsyncMock(
                side_effect=[b"invalid json\n", b""]  # Invalid JSON  # EOF
            )
            mock_read_stdin.return_value = mock_reader

            mock_config = MagicMock()

            await handle_stdio(mock_config, "INFO")

            # Verify error response was written
            mock_stdout.write.assert_called()
            written_response = mock_stdout.write.call_args[0][0]
            response = json.loads(written_response)
            assert response["error"]["code"] == -32700
            assert "Parse error" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_handle_stdio_invalid_request_format(self):
        """Test stdio handler with invalid request format."""
        with (
            patch("qdrant_loader_mcp_server.cli.LoggingConfig") as mock_logging_config,
            patch(
                "qdrant_loader_mcp_server.cli.SearchEngine"
            ) as mock_search_engine_class,
            patch(
                "qdrant_loader_mcp_server.cli.QueryProcessor"
            ) as mock_query_processor_class,
            patch("qdrant_loader_mcp_server.cli.MCPHandler") as mock_mcp_handler_class,
            patch("qdrant_loader_mcp_server.cli.read_stdin") as mock_read_stdin,
            patch("sys.stdout") as mock_stdout,
            patch.dict(os.environ, {}, clear=True),
        ):

            mock_logger = MagicMock()
            mock_logging_config.get_logger.return_value = mock_logger

            # Mock successful initialization
            mock_search_engine = MagicMock()
            mock_search_engine.initialize = AsyncMock()
            mock_search_engine.cleanup = AsyncMock()
            mock_search_engine_class.return_value = mock_search_engine

            # Mock reader with non-object JSON
            mock_reader = MagicMock()
            mock_reader.readline = AsyncMock(
                side_effect=[
                    b'"not an object"\n',  # Valid JSON but not an object
                    b"",  # EOF
                ]
            )
            mock_read_stdin.return_value = mock_reader

            mock_config = MagicMock()

            await handle_stdio(mock_config, "INFO")

            # Verify error response was written
            mock_stdout.write.assert_called()
            written_response = mock_stdout.write.call_args[0][0]
            response = json.loads(written_response)
            assert response["error"]["code"] == -32600
            assert "Invalid Request" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_handle_stdio_invalid_jsonrpc_version(self):
        """Test stdio handler with invalid JSON-RPC version."""
        with (
            patch("qdrant_loader_mcp_server.cli.LoggingConfig") as mock_logging_config,
            patch(
                "qdrant_loader_mcp_server.cli.SearchEngine"
            ) as mock_search_engine_class,
            patch(
                "qdrant_loader_mcp_server.cli.QueryProcessor"
            ) as mock_query_processor_class,
            patch("qdrant_loader_mcp_server.cli.MCPHandler") as mock_mcp_handler_class,
            patch("qdrant_loader_mcp_server.cli.read_stdin") as mock_read_stdin,
            patch("sys.stdout") as mock_stdout,
            patch.dict(os.environ, {}, clear=True),
        ):

            mock_logger = MagicMock()
            mock_logging_config.get_logger.return_value = mock_logger

            # Mock successful initialization
            mock_search_engine = MagicMock()
            mock_search_engine.initialize = AsyncMock()
            mock_search_engine.cleanup = AsyncMock()
            mock_search_engine_class.return_value = mock_search_engine

            # Mock reader with invalid JSON-RPC version
            invalid_request = {"jsonrpc": "1.0", "method": "test", "id": 1}
            mock_reader = MagicMock()
            mock_reader.readline = AsyncMock(
                side_effect=[json.dumps(invalid_request).encode() + b"\n", b""]  # EOF
            )
            mock_read_stdin.return_value = mock_reader

            mock_config = MagicMock()

            await handle_stdio(mock_config, "INFO")

            # Verify error response was written
            mock_stdout.write.assert_called()
            written_response = mock_stdout.write.call_args[0][0]
            response = json.loads(written_response)
            assert response["error"]["code"] == -32600
            assert "Invalid JSON-RPC version" in response["error"]["data"]

    @pytest.mark.asyncio
    async def test_handle_stdio_successful_request(self):
        """Test stdio handler with successful request processing."""
        with (
            patch("qdrant_loader_mcp_server.cli.LoggingConfig") as mock_logging_config,
            patch(
                "qdrant_loader_mcp_server.cli.SearchEngine"
            ) as mock_search_engine_class,
            patch(
                "qdrant_loader_mcp_server.cli.QueryProcessor"
            ) as mock_query_processor_class,
            patch("qdrant_loader_mcp_server.cli.MCPHandler") as mock_mcp_handler_class,
            patch("qdrant_loader_mcp_server.cli.read_stdin") as mock_read_stdin,
            patch("sys.stdout") as mock_stdout,
            patch.dict(os.environ, {}, clear=True),
        ):

            mock_logger = MagicMock()
            mock_logging_config.get_logger.return_value = mock_logger

            # Mock successful initialization
            mock_search_engine = MagicMock()
            mock_search_engine.initialize = AsyncMock()
            mock_search_engine.cleanup = AsyncMock()
            mock_search_engine_class.return_value = mock_search_engine

            # Mock MCP handler
            mock_mcp_handler = MagicMock()
            mock_mcp_handler.handle_request = AsyncMock(
                return_value={"jsonrpc": "2.0", "id": 1, "result": "success"}
            )
            mock_mcp_handler_class.return_value = mock_mcp_handler

            # Mock reader with valid request
            valid_request = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
            mock_reader = MagicMock()
            mock_reader.readline = AsyncMock(
                side_effect=[json.dumps(valid_request).encode() + b"\n", b""]  # EOF
            )
            mock_read_stdin.return_value = mock_reader

            mock_config = MagicMock()

            await handle_stdio(mock_config, "INFO")

            # Verify request was handled
            mock_mcp_handler.handle_request.assert_called_once_with(valid_request)

            # Verify response was written
            mock_stdout.write.assert_called()
            written_response = mock_stdout.write.call_args[0][0]
            response = json.loads(written_response)
            assert response["result"] == "success"


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
    @patch("qdrant_loader_mcp_server.cli.Config")
    @patch("qdrant_loader_mcp_server.cli.handle_stdio")
    @patch("asyncio.new_event_loop")
    @patch("asyncio.set_event_loop")
    @patch("signal.SIGTERM", 15)
    @patch("signal.SIGINT", 2)
    def test_cli_successful_execution(
        self,
        mock_set_event_loop,
        mock_new_event_loop,
        mock_handle_stdio,
        mock_config_class,
        mock_setup_logging,
    ):
        """Test successful CLI execution."""
        # Mock event loop
        mock_loop = MagicMock()
        mock_new_event_loop.return_value = mock_loop
        mock_loop.run_until_complete.return_value = None

        # Mock config
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        # Mock handle_stdio as async function
        mock_handle_stdio.return_value = AsyncMock()

        runner = CliRunner()
        result = runner.invoke(cli, ["--log-level", "DEBUG"])

        # Verify setup was called
        mock_setup_logging.assert_called_once_with("DEBUG")
        mock_config_class.assert_called_once()
        mock_new_event_loop.assert_called_once()
        mock_set_event_loop.assert_called_once_with(mock_loop)

    @patch("qdrant_loader_mcp_server.cli._setup_logging")
    @patch("qdrant_loader_mcp_server.cli.Config")
    @patch("qdrant_loader_mcp_server.cli.handle_stdio")
    @patch("asyncio.new_event_loop")
    @patch("asyncio.set_event_loop")
    @patch("sys.exit")
    def test_cli_exception_handling(
        self,
        mock_exit,
        mock_set_event_loop,
        mock_new_event_loop,
        mock_handle_stdio,
        mock_config_class,
        mock_setup_logging,
    ):
        """Test CLI exception handling."""
        # Mock config to raise exception
        mock_config_class.side_effect = Exception("Config error")

        # Mock event loop - use a simple class to avoid async confusion
        class MockLoop:
            def close(self):
                pass
            def run_until_complete(self, coro):
                pass
        
        mock_loop = MockLoop()
        mock_new_event_loop.return_value = mock_loop

        runner = CliRunner()
        result = runner.invoke(cli, [])

        # Verify exit was called with error code
        mock_exit.assert_called_once_with(1)

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
        assert "does not exist" in result.output
