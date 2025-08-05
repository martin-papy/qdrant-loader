"""Tests for main module and entry points."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_main_entry_point():
    """Test the __main__.py entry point."""
    # Test that the module can be imported
    import qdrant_loader_mcp_server.__main__

    # Test that main function is available
    assert hasattr(qdrant_loader_mcp_server.__main__, "main")


def test_main_function():
    """Test the main function delegates to CLI."""
    from qdrant_loader_mcp_server.main import main

    # Mock the CLI function
    with patch("qdrant_loader_mcp_server.main.cli") as mock_cli:
        main()
        mock_cli.assert_called_once()


def test_read_stdin_function_exists():
    """Test that read_stdin function exists and is callable."""
    from qdrant_loader_mcp_server.cli import read_stdin

    # Just verify the function exists and is callable
    assert callable(read_stdin)
    # Note: Full testing of read_stdin requires complex asyncio mocking
    # and is covered by integration tests


@pytest.mark.asyncio
async def test_shutdown():
    """Test the shutdown function."""
    from qdrant_loader_mcp_server.cli import shutdown

    # Create a mock event loop
    mock_loop = MagicMock()
    mock_loop.stop = MagicMock()

    # Create some mock tasks
    mock_task1 = MagicMock()
    mock_task1.cancel = MagicMock()
    mock_task1.done.return_value = False  # Task not done, should be cancelled
    mock_task2 = MagicMock()
    mock_task2.cancel = MagicMock()
    mock_task2.done.return_value = False  # Task not done, should be cancelled

    # Create an async function that returns None
    async def mock_gather(*args, **kwargs):
        return None

    with patch("asyncio.all_tasks", return_value=[mock_task1, mock_task2]):
        with patch("asyncio.current_task", return_value=None):
            with patch("asyncio.sleep"):  # Mock the sleep call
                # Mock asyncio.gather with a proper async function
                with patch("asyncio.gather", side_effect=mock_gather) as mock_gather_patch:
                    await shutdown(mock_loop)

                    # Verify tasks were cancelled
                    mock_task1.cancel.assert_called_once()
                    mock_task2.cancel.assert_called_once()

                    # Verify gather was called with the tasks
                    mock_gather_patch.assert_called_once_with(
                        mock_task1, mock_task2, return_exceptions=True
                    )

                    # Verify loop was stopped
                    mock_loop.stop.assert_called_once()


def test_cli_imports():
    """Test that CLI module imports work correctly."""
    # Test that we can import the CLI components
    from qdrant_loader_mcp_server.cli import _setup_logging, cli
    from qdrant_loader_mcp_server.utils import get_version

    # Verify the components are available
    assert cli is not None
    assert get_version is not None
    assert _setup_logging is not None


def test_version_function():
    """Test the version function."""
    from qdrant_loader_mcp_server.utils import get_version

    version = get_version()
    assert isinstance(version, str)
    assert len(version) > 0


def test_setup_logging():
    """Test the logging setup function."""
    from qdrant_loader_mcp_server.cli import _setup_logging

    # Test that it doesn't raise an error
    _setup_logging("INFO")
    _setup_logging("DEBUG")


@pytest.mark.asyncio
async def test_handle_stdio_initialization_error():
    """Test handle_stdio with search engine initialization error."""
    from qdrant_loader_mcp_server.cli import handle_stdio
    from qdrant_loader_mcp_server.config import Config

    config = Config()

    # Create an async function that raises an exception
    async def mock_initialize_error():
        raise Exception("Test error")

    # Mock SearchEngine to raise an error during initialization
    with patch("qdrant_loader_mcp_server.cli.SearchEngine") as mock_search_engine_class:
        mock_search_engine = MagicMock()
        mock_search_engine.initialize = AsyncMock(side_effect=mock_initialize_error)
        mock_search_engine_class.return_value = mock_search_engine

        with pytest.raises(RuntimeError, match="Failed to initialize search engine"):
            await handle_stdio(config, "INFO")


def test_cli_environment_variables():
    """Test CLI module respects environment variables."""
    # Test with console logging disabled
    with patch.dict(os.environ, {"MCP_DISABLE_CONSOLE_LOGGING": "true"}):
        from qdrant_loader_mcp_server.cli import _setup_logging

        # Should not raise any errors
        _setup_logging("INFO")


def test_cli_component_initialization():
    """Test CLI module handles component initialization."""
    # Test that the CLI module can be imported
    import qdrant_loader_mcp_server.cli

    # Module should import successfully
    assert qdrant_loader_mcp_server.cli is not None


@pytest.mark.asyncio
async def test_handle_stdio_success():
    """Test handle_stdio with successful initialization."""
    from qdrant_loader_mcp_server.cli import handle_stdio
    from qdrant_loader_mcp_server.config import Config

    config = Config()

    # Mock all the components
    with patch("qdrant_loader_mcp_server.cli.SearchEngine") as mock_search_engine_class:
        with patch(
            "qdrant_loader_mcp_server.cli.QueryProcessor"
        ) as mock_query_processor_class:
            with patch(
                "qdrant_loader_mcp_server.cli.MCPHandler"
            ) as mock_mcp_handler_class:
                with patch(
                    "qdrant_loader_mcp_server.cli.read_stdin"
                ) as mock_read_stdin:
                    # Setup mocks
                    mock_search_engine = MagicMock()
                    mock_search_engine.initialize = AsyncMock()
                    mock_search_engine.cleanup = AsyncMock()
                    mock_search_engine_class.return_value = mock_search_engine

                    mock_query_processor = MagicMock()
                    mock_query_processor_class.return_value = mock_query_processor

                    mock_mcp_handler = MagicMock()
                    mock_mcp_handler.handle_request = AsyncMock(
                        return_value={"result": "test"}
                    )
                    mock_mcp_handler_class.return_value = mock_mcp_handler

                    # Mock stdin reader that returns empty (EOF)
                    mock_reader = AsyncMock()
                    mock_reader.readline.return_value = b""  # EOF
                    mock_read_stdin.return_value = mock_reader

                    # Test should complete without error
                    await handle_stdio(config, "INFO")

                    # Verify initialization was called
                    mock_search_engine.initialize.assert_called_once()
                    mock_search_engine.cleanup.assert_called_once()


def test_cli_click_integration():
    """Test that Click CLI integration works."""
    from click.testing import CliRunner
    from qdrant_loader_mcp_server.cli import cli

    runner = CliRunner()

    # Test help option
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "QDrant Loader MCP Server" in result.output

    # Test version option
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "QDrant Loader MCP Server v" in result.output


def test_main_module_structure():
    """Test that main module has the expected structure."""
    from qdrant_loader_mcp_server import main

    # Test that main function exists
    assert hasattr(main, "main")
    assert callable(main.main)
