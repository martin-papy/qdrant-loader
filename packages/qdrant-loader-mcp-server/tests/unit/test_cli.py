"""Tests for CLI module."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
from click.testing import CliRunner
from qdrant_loader_mcp_server.cli import (
    _setup_logging,
    cli,
    handle_stdio,
    read_stdin,
    shutdown,
)
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
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):

            mock_logger = MagicMock()
            mock_logging_config.get_logger.return_value = mock_logger

            # Mock loop
            mock_loop = MagicMock()

            # Mock shutdown event
            mock_shutdown_event = MagicMock()

            await shutdown(mock_loop, mock_shutdown_event)

            # Verify shutdown event was set
            mock_shutdown_event.set.assert_called_once()

            # Sleep should be called once with 0 (yield control)
            assert mock_sleep.await_count == 1
            mock_sleep.assert_awaited_with(0)

            # Verify logging calls
            assert mock_logging_config.get_logger.call_count >= 1
            mock_logger.info.assert_any_call("Shutting down...")
            mock_logger.info.assert_any_call("Shutdown signal dispatched")

    @pytest.mark.asyncio
    async def test_shutdown_with_exception(self):
        """Test shutdown with exception during sleep (e.g., cancellation)."""
        from asyncio import CancelledError

        # Create an async function that raises CancelledError
        async def mock_sleep_error(*args, **kwargs):
            raise CancelledError("Sleep cancelled")

        with (
            patch("qdrant_loader_mcp_server.cli.LoggingConfig") as mock_logging_config,
            patch("asyncio.sleep", side_effect=mock_sleep_error),
        ):

            mock_logger = MagicMock()
            mock_logging_config.get_logger.return_value = mock_logger

            # Mock loop
            mock_loop = MagicMock()

            # Mock shutdown event
            mock_shutdown_event = MagicMock()

            # The shutdown function should handle CancelledError gracefully
            await shutdown(mock_loop, mock_shutdown_event)

            # Verify shutdown event was set
            mock_shutdown_event.set.assert_called_once()

            # Verify logging calls were made
            mock_logger.info.assert_any_call("Shutting down...")

            # No explicit loop.stop() should be called in cooperative shutdown
            assert not mock_loop.stop.called


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
            patch("qdrant_loader_mcp_server.cli.QueryProcessor"),
            patch("qdrant_loader_mcp_server.cli.MCPHandler"),
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
            patch("qdrant_loader_mcp_server.cli.QueryProcessor"),
            patch("qdrant_loader_mcp_server.cli.MCPHandler"),
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
            patch("qdrant_loader_mcp_server.cli.QueryProcessor"),
            patch("qdrant_loader_mcp_server.cli.MCPHandler"),
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
            patch("qdrant_loader_mcp_server.cli.QueryProcessor"),
            patch("qdrant_loader_mcp_server.cli.MCPHandler"),
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
            patch("qdrant_loader_mcp_server.cli.QueryProcessor"),
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
    @patch("qdrant_loader_mcp_server.cli.load_config")
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
        mock_load_config,
        mock_setup_logging,
    ):
        """Test successful CLI execution."""
        # Mock event loop
        mock_loop = MagicMock()
        mock_new_event_loop.return_value = mock_loop
        mock_loop.run_until_complete.return_value = None

        # Mock config loader
        mock_config = MagicMock()
        mock_effective = {"dummy": True}
        mock_used_file = None
        mock_load_config.return_value = (mock_config, mock_effective, mock_used_file)

        # Mock handle_stdio as async function
        mock_handle_stdio.return_value = AsyncMock()

        runner = CliRunner()
        runner.invoke(cli, ["--log-level", "DEBUG"])

        # Verify setup was called with transport parameter (default is stdio)
        mock_setup_logging.assert_called_once_with("DEBUG", "stdio")
        mock_load_config.assert_called_once()
        mock_new_event_loop.assert_called_once()
        mock_set_event_loop.assert_called_once_with(mock_loop)

    @patch("qdrant_loader_mcp_server.cli._setup_logging")
    @patch("qdrant_loader_mcp_server.cli.load_config")
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
        mock_load_config,
        mock_setup_logging,
    ):
        """Test CLI exception handling."""
        # Mock config loader to raise exception
        mock_load_config.side_effect = Exception("Config error")

        # Mock event loop - use a simple class to avoid async confusion
        class MockLoop:
            def close(self):
                pass

            def run_until_complete(self, coro):
                pass

            def add_signal_handler(self, sig, handler):
                pass

        mock_loop = MockLoop()
        mock_new_event_loop.return_value = mock_loop

        runner = CliRunner()
        runner.invoke(cli, [])

        # Verify exit was called with error code - the CLI may call exit multiple times
        # once for the actual error and once during cleanup/normal exit flow
        assert mock_exit.call_count >= 1
        # Check that at least one call was with error code 1
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
        assert "does not exist" in result.output
