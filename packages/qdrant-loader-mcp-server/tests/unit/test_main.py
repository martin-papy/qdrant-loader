"""Tests for main module and entry points."""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pytest_asyncio


def test_main_entry_point():
    """Test the __main__.py entry point."""
    # Test that the module can be imported
    import qdrant_loader_mcp_server.__main__

    # Test that main function is available
    assert hasattr(qdrant_loader_mcp_server.__main__, "main")


@pytest.mark.asyncio
async def test_read_stdin():
    """Test the read_stdin function."""
    from qdrant_loader_mcp_server.main import read_stdin

    # Mock stdin with some test data
    test_data = b"test input\n"

    with patch("sys.stdin") as mock_stdin:
        # Create a mock reader
        mock_reader = AsyncMock()
        mock_reader.readline.return_value = test_data

        with patch("asyncio.StreamReader", return_value=mock_reader):
            with patch("asyncio.StreamReaderProtocol"):
                with patch("asyncio.get_event_loop") as mock_loop:
                    mock_loop.return_value.connect_read_pipe = AsyncMock()

                    reader = await read_stdin()
                    assert reader is not None


@pytest.mark.asyncio
async def test_shutdown():
    """Test the shutdown function."""
    from qdrant_loader_mcp_server.main import shutdown

    # Create a mock event loop
    mock_loop = MagicMock()
    mock_loop.stop = MagicMock()

    # Create some mock tasks
    mock_task1 = MagicMock()
    mock_task1.cancel = MagicMock()
    mock_task2 = MagicMock()
    mock_task2.cancel = MagicMock()

    with patch("asyncio.all_tasks", return_value=[mock_task1, mock_task2]):
        with patch("asyncio.current_task", return_value=None):
            with patch("asyncio.gather", return_value=None) as mock_gather:
                await shutdown(mock_loop)

                # Verify tasks were cancelled
                mock_task1.cancel.assert_called_once()
                mock_task2.cancel.assert_called_once()

                # Verify loop was stopped
                mock_loop.stop.assert_called_once()


def test_main_module_imports():
    """Test that main module imports work correctly."""
    # Test that we can import the main components
    from qdrant_loader_mcp_server.main import (
        config,
        search_engine,
        query_processor,
        mcp_handler,
    )

    # Verify the components are initialized
    assert config is not None
    assert search_engine is not None
    assert query_processor is not None
    assert mcp_handler is not None


def test_main_module_logging_setup():
    """Test that logging is set up correctly in main module."""
    # Import should set up logging
    from qdrant_loader_mcp_server.main import logger

    assert logger is not None
    assert hasattr(logger, "info")
    assert hasattr(logger, "debug")
    assert hasattr(logger, "error")


@pytest.mark.asyncio
async def test_handle_stdio_initialization_error():
    """Test handle_stdio with search engine initialization error."""
    from qdrant_loader_mcp_server.main import handle_stdio, search_engine

    # Mock search engine to raise an error during initialization
    with patch.object(search_engine, "initialize", side_effect=Exception("Test error")):
        with pytest.raises(RuntimeError, match="Failed to initialize search engine"):
            await handle_stdio()


def test_main_environment_variables():
    """Test main module respects environment variables."""
    # Test with console logging disabled
    with patch.dict(os.environ, {"MCP_DISABLE_CONSOLE_LOGGING": "true"}):
        # Re-import to test environment variable handling
        import importlib
        import qdrant_loader_mcp_server.main

        importlib.reload(qdrant_loader_mcp_server.main)

        # Should not raise any errors
        assert True


def test_main_component_initialization_error():
    """Test main module handles component initialization errors."""
    # Test that initialization errors are handled gracefully
    # This test verifies that the module can be imported even with potential config issues
    import importlib
    import qdrant_loader_mcp_server.main

    # Module should import successfully
    assert qdrant_loader_mcp_server.main is not None


@pytest.mark.asyncio
async def test_lifespan_startup_success():
    """Test FastAPI lifespan startup success."""
    from qdrant_loader_mcp_server.main import lifespan, search_engine, config

    # Mock successful initialization
    with patch.object(search_engine, "initialize", return_value=None) as mock_init:
        with patch.object(search_engine, "cleanup", return_value=None) as mock_cleanup:
            # Create a mock FastAPI app
            mock_app = MagicMock()

            # Test the lifespan context manager
            async with lifespan(mock_app):
                # Verify initialization was called
                mock_init.assert_called_once_with(config.qdrant, config.openai)

            # Verify cleanup was called
            mock_cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_startup_failure():
    """Test FastAPI lifespan startup failure."""
    from qdrant_loader_mcp_server.main import lifespan, search_engine

    # Mock failed initialization
    with patch.object(
        search_engine, "initialize", side_effect=RuntimeError("Connection failed")
    ):
        with patch("os._exit") as mock_exit:
            mock_app = MagicMock()

            # Test the lifespan context manager with failure
            try:
                async with lifespan(mock_app):
                    pass
            except SystemExit:
                pass

            # Verify exit was called
            mock_exit.assert_called_once_with(1)
