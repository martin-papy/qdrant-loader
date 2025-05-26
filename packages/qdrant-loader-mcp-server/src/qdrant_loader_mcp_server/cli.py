"""CLI module for QDrant Loader MCP Server."""

import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path

import click
import tomli
from click.decorators import option
from click.types import Choice
from click.types import Path as ClickPath

from .config import Config
from .mcp import MCPHandler
from .search.engine import SearchEngine
from .search.processor import QueryProcessor
from .utils import LoggingConfig

# Suppress asyncio debug messages
logging.getLogger("asyncio").setLevel(logging.WARNING)


def _get_version() -> str:
    """Get version from pyproject.toml."""
    try:
        # Try to find pyproject.toml in the package directory or parent directories
        current_dir = Path(__file__).parent
        for _ in range(5):  # Look up to 5 levels up
            pyproject_path = current_dir / "pyproject.toml"
            if pyproject_path.exists():
                with open(pyproject_path, "rb") as f:
                    pyproject = tomli.load(f)
                    return pyproject["project"]["version"]
            current_dir = current_dir.parent

        # If not found, try the workspace root
        workspace_root = Path.cwd()
        for package_dir in ["packages/qdrant-loader-mcp-server", "."]:
            pyproject_path = workspace_root / package_dir / "pyproject.toml"
            if pyproject_path.exists():
                with open(pyproject_path, "rb") as f:
                    pyproject = tomli.load(f)
                    return pyproject["project"]["version"]
    except Exception:
        pass
    return "Unknown"


def _setup_logging(log_level: str) -> None:
    """Set up logging configuration."""
    try:
        # Check if console logging is disabled
        disable_console_logging = (
            os.getenv("MCP_DISABLE_CONSOLE_LOGGING", "").lower() == "true"
        )

        if not disable_console_logging:
            LoggingConfig.setup(level=log_level.upper(), format="console")
        else:
            LoggingConfig.setup(level=log_level.upper(), format="json")
    except Exception as e:
        print(f"Failed to setup logging: {e}", file=sys.stderr)


async def read_stdin():
    """Read from stdin asynchronously."""
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    return reader


async def shutdown(loop: asyncio.AbstractEventLoop):
    """Handle graceful shutdown."""
    logger = LoggingConfig.get_logger(__name__)
    logger.info("Shutting down...")

    # Get all tasks except the current one
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    # Cancel all tasks
    for task in tasks:
        task.cancel()

    # Wait for all tasks to complete
    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception:
        logger.error("Error during shutdown", exc_info=True)

    # Stop the event loop
    loop.stop()


async def handle_stdio(config: Config, log_level: str):
    """Handle stdio communication with Cursor."""
    logger = LoggingConfig.get_logger(__name__)

    try:
        # Check if console logging is disabled
        disable_console_logging = (
            os.getenv("MCP_DISABLE_CONSOLE_LOGGING", "").lower() == "true"
        )

        if not disable_console_logging:
            logger.info("Setting up stdio handler...")

        # Initialize components
        search_engine = SearchEngine()
        query_processor = QueryProcessor(config.openai)
        mcp_handler = MCPHandler(search_engine, query_processor)

        # Initialize search engine
        try:
            await search_engine.initialize(config.qdrant, config.openai)
            if not disable_console_logging:
                logger.info("Search engine initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize search engine", exc_info=True)
            raise RuntimeError("Failed to initialize search engine") from e

        reader = await read_stdin()
        if not disable_console_logging:
            logger.info("Server ready to handle requests")

        while True:
            try:
                # Read a line from stdin
                if not disable_console_logging:
                    logger.debug("Waiting for input...")
                try:
                    line = await reader.readline()
                    if not line:
                        if not disable_console_logging:
                            logger.warning("No input received, breaking")
                        break
                except asyncio.CancelledError:
                    if not disable_console_logging:
                        logger.info("Read operation cancelled during shutdown")
                    break

                # Log the raw input
                raw_input = line.decode().strip()
                if not disable_console_logging:
                    logger.debug("Received raw input", raw_input=raw_input)

                # Parse the request
                try:
                    request = json.loads(raw_input)
                    if not disable_console_logging:
                        logger.debug("Parsed request", request=request)
                except json.JSONDecodeError as e:
                    if not disable_console_logging:
                        logger.error("Invalid JSON received", error=str(e))
                    # Send error response for invalid JSON
                    response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error",
                            "data": f"Invalid JSON received: {str(e)}",
                        },
                    }
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
                    continue

                # Validate request format
                if not isinstance(request, dict):
                    if not disable_console_logging:
                        logger.error("Request must be a JSON object")
                    response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32600,
                            "message": "Invalid Request",
                            "data": "Request must be a JSON object",
                        },
                    }
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
                    continue

                if "jsonrpc" not in request or request["jsonrpc"] != "2.0":
                    if not disable_console_logging:
                        logger.error("Invalid JSON-RPC version")
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "error": {
                            "code": -32600,
                            "message": "Invalid Request",
                            "data": "Invalid JSON-RPC version",
                        },
                    }
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
                    continue

                # Process the request
                try:
                    response = await mcp_handler.handle_request(request)
                    if not disable_console_logging:
                        logger.debug("Sending response", response=response)
                    # Only write to stdout if response is not empty (not a notification)
                    if response:
                        sys.stdout.write(json.dumps(response) + "\n")
                        sys.stdout.flush()
                except Exception as e:
                    if not disable_console_logging:
                        logger.error("Error processing request", exc_info=True)
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "error": {
                            "code": -32603,
                            "message": "Internal error",
                            "data": str(e),
                        },
                    }
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()

            except asyncio.CancelledError:
                if not disable_console_logging:
                    logger.info("Request handling cancelled during shutdown")
                break
            except Exception:
                if not disable_console_logging:
                    logger.error("Error handling request", exc_info=True)
                continue

        # Cleanup
        await search_engine.cleanup()

    except Exception:
        if not disable_console_logging:
            logger.error("Error in stdio handler", exc_info=True)
        raise


@click.command(name="mcp-qdrant-loader")
@option(
    "--log-level",
    type=Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False
    ),
    default="INFO",
    help="Set the logging level.",
)
@option(
    "--config",
    type=ClickPath(exists=True, path_type=Path),
    help="Path to configuration file (currently not implemented).",
)
@click.version_option(
    version=_get_version(),
    message="QDrant Loader MCP Server v%(version)s",
)
def cli(log_level: str = "INFO", config: Path | None = None) -> None:
    """QDrant Loader MCP Server.

    A Model Context Protocol (MCP) server that provides RAG capabilities
    to Cursor and other LLM applications using Qdrant vector database.

    The server communicates via JSON-RPC over stdio and provides semantic
    search capabilities for documents stored in Qdrant.

    Environment Variables:
        QDRANT_URL: URL of your QDrant instance (required)
        QDRANT_API_KEY: API key for QDrant authentication
        QDRANT_COLLECTION_NAME: Name of the collection to use (default: "documents")
        OPENAI_API_KEY: OpenAI API key for embeddings (required)
        MCP_DISABLE_CONSOLE_LOGGING: Set to "true" to disable console logging

    Examples:
        # Start the MCP server
        mcp-qdrant-loader

        # Start with debug logging
        mcp-qdrant-loader --log-level DEBUG

        # Show help
        mcp-qdrant-loader --help

        # Show version
        mcp-qdrant-loader --version
    """
    try:
        # Setup logging
        _setup_logging(log_level)

        # Initialize configuration
        config_obj = Config()

        # Create and set the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Set up signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(loop)))

        # Start the stdio handler
        loop.run_until_complete(handle_stdio(config_obj, log_level))
    except Exception:
        logger = LoggingConfig.get_logger(__name__)
        logger.error("Error in main", exc_info=True)
        sys.exit(1)
    finally:
        try:
            # Cancel all remaining tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()

            # Run the loop until all tasks are done
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            logger = LoggingConfig.get_logger(__name__)
            logger.error("Error during final cleanup", exc_info=True)
        finally:
            loop.close()
            logger = LoggingConfig.get_logger(__name__)
            logger.info("Server shutdown complete")


if __name__ == "__main__":
    cli()
