"""CLI module for QDrant Loader MCP Server."""

import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path

import click
from click.decorators import option
from click.types import Choice
from click.types import Path as ClickPath
from dotenv import load_dotenv

from .config import Config
from .config_loader import load_config, redact_effective_config
from .mcp import MCPHandler
from .search.engine import SearchEngine
from .search.processor import QueryProcessor
from .utils import LoggingConfig, get_version

# Suppress asyncio debug messages to reduce noise in logs.
logging.getLogger("asyncio").setLevel(logging.WARNING)


def _setup_logging(log_level: str, transport: str | None = None) -> None:
    """Set up logging configuration."""
    try:
        # Force-disable console logging in stdio mode to avoid polluting stdout
        if transport and transport.lower() == "stdio":
            os.environ["MCP_DISABLE_CONSOLE_LOGGING"] = "true"

        # Check if console logging is disabled via environment variable (after any override)
        disable_console_logging = (
            os.getenv("MCP_DISABLE_CONSOLE_LOGGING", "").lower() == "true"
        )

        # Reset any pre-existing handlers to prevent duplicate logs when setup() is
        # invoked implicitly during module imports before CLI config is applied.
        root_logger = logging.getLogger()
        for h in list(root_logger.handlers):
            try:
                root_logger.removeHandler(h)
            except Exception:
                pass

        # Use reconfigure if available to avoid stacking handlers on repeated setup
        level = log_level.upper()
        if getattr(LoggingConfig, "reconfigure", None):  # type: ignore[attr-defined]
            if getattr(LoggingConfig, "_initialized", False):  # type: ignore[attr-defined]
                # Only switch file target (none in stdio; may be env provided)
                LoggingConfig.reconfigure(file=os.getenv("MCP_LOG_FILE"))  # type: ignore[attr-defined]
            else:
                LoggingConfig.setup(
                    level=level,
                    format=("json" if disable_console_logging else "console"),
                )
        else:
            # Force replace handlers on older versions
            logging.getLogger().handlers = []
            LoggingConfig.setup(
                level=level, format=("json" if disable_console_logging else "console")
            )
    except Exception as e:
        print(f"Failed to setup logging: {e}", file=sys.stderr)


async def read_stdin_lines():
    """Cross-platform async generator that yields lines from stdin."""
    loop = asyncio.get_event_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:  # EOF
            break
        yield line


async def shutdown(
    loop: asyncio.AbstractEventLoop, shutdown_event: asyncio.Event = None
):
    """Handle graceful shutdown."""
    logger = LoggingConfig.get_logger(__name__)
    logger.info("Shutting down...")

    # Only signal shutdown; let server/monitor handle draining and cleanup
    if shutdown_event:
        shutdown_event.set()

    # Yield control so that other tasks (e.g., shutdown monitor, server) can react
    try:
        await asyncio.sleep(0)
    except asyncio.CancelledError:
        # If shutdown task is cancelled, just exit quietly
        return

    logger.info("Shutdown signal dispatched")


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
        mcp_handler = MCPHandler(
            search_engine, query_processor, reranking_config=config.reranking
        )

        # Initialize search engine
        try:
            await search_engine.initialize(config.qdrant, config.openai, config.search)
            if not disable_console_logging:
                logger.info("Search engine initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize search engine", exc_info=True)
            raise RuntimeError("Failed to initialize search engine") from e

        if not disable_console_logging:
            logger.info("Server ready to handle requests")

        async for line in read_stdin_lines():
            try:
                raw_input = line.strip()
                if not raw_input:
                    continue

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
# Hidden option to print effective config (redacts secrets)
@option(
    "--print-config",
    is_flag=True,
    default=False,
    help="Print the effective configuration (secrets redacted) and exit.",
)
@option(
    "--config",
    type=ClickPath(exists=True, path_type=Path),
    help="Path to configuration file.",
)
@option(
    "--transport",
    type=Choice(["stdio", "http"], case_sensitive=False),
    default="stdio",
    help="Transport protocol to use (stdio for JSON-RPC over stdin/stdout, http for HTTP with SSE)",
)
@option(
    "--host",
    type=str,
    default="127.0.0.1",
    help="Host to bind HTTP server to (only used with --transport http)",
)
@option(
    "--port",
    type=int,
    default=8080,
    help="Port to bind HTTP server to (only used with --transport http)",
)
@option(
    "--workers",
    type=int,
    default=1,
    help="Number of uvicorn worker processes (only used with --transport http)",
)
@option(
    "--env",
    type=ClickPath(exists=True, path_type=Path),
    help="Path to .env file to load environment variables from",
)
@click.version_option(
    version=get_version(),
    message="QDrant Loader MCP Server v%(version)s",
)
def cli(
    log_level: str = "INFO",
    config: Path | None = None,
    transport: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 8080,
    workers: int = 1,
    env: Path | None = None,
    print_config: bool = False,
) -> None:
    """QDrant Loader MCP Server.

    A Model Context Protocol (MCP) server that provides RAG capabilities
    to Cursor and other LLM applications using Qdrant vector database.

    The server supports both stdio (JSON-RPC) and HTTP (with SSE) transports
    for maximum compatibility with different MCP clients.

    Environment Variables:
        QDRANT_URL: URL of your QDrant instance (required)
        QDRANT_API_KEY: API key for QDrant authentication
        QDRANT_COLLECTION_NAME: Name of the collection to use (default: "documents")
        OPENAI_API_KEY: OpenAI API key for embeddings (required)
        MCP_DISABLE_CONSOLE_LOGGING: Set to "true" to disable console logging

    Examples:
        # Start with stdio transport (default, for Cursor/Claude Desktop)
        mcp-qdrant-loader

        # Start with HTTP transport (for web clients)
        mcp-qdrant-loader --transport http --port 8080

        # Start with environment variables from .env file
        mcp-qdrant-loader --transport http --env /path/to/.env

        # Start with debug logging
        mcp-qdrant-loader --log-level DEBUG --transport http

        # Show help
        mcp-qdrant-loader --help

        # Show version
        mcp-qdrant-loader --version
    """
    try:
        # Load environment variables from .env file if specified
        if env:
            load_dotenv(env)

        # Setup logging (force-disable console logging in stdio transport)
        _setup_logging(log_level, transport)

        # Log env file load after logging is configured to avoid duplicate handler setup
        if env:
            LoggingConfig.get_logger(__name__).info(
                "Loaded environment variables", env=str(env)
            )

        # If a config file was provided, propagate it via MCP_CONFIG so that
        # any internal callers that resolve config without CLI context can find it.
        if config is not None:
            try:
                os.environ["MCP_CONFIG"] = str(config)
            except Exception:
                # Best-effort; continue without blocking startup
                pass

        # Initialize configuration (file/env precedence)
        config_obj, effective_cfg, used_file = load_config(config)

        if print_config:
            redacted = redact_effective_config(effective_cfg)
            click.echo(json.dumps(redacted, indent=2))
            return

        if transport.lower() == "http":
            # Delegate to server.py's app via uvicorn.run() — single app,
            # no duplicate FastAPI instance.  uvicorn handles signals natively.
            import uvicorn

            os.environ["MCP_LOG_LEVEL"] = log_level
            os.environ["MCP_HOST"] = host
            os.environ["MCP_PORT"] = str(port)

            logger = LoggingConfig.get_logger(__name__)
            logger.info(
                "Starting HTTP server",
                host=host,
                port=port,
                log_level=log_level,
            )

            uvicorn.run(
                "qdrant_loader_mcp_server.server:app",
                host=host,
                port=port,
                workers=workers,
                log_level=log_level.lower(),
                access_log=(log_level.upper() == "DEBUG"),
            )
        elif transport.lower() == "stdio":
            # stdio needs its own event loop and signal handling
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            shutdown_event = asyncio.Event()
            shutdown_task = None

            def signal_handler():
                nonlocal shutdown_task
                if shutdown_task is None:
                    shutdown_task = loop.create_task(shutdown(loop, shutdown_event))

            for sig in (signal.SIGTERM, signal.SIGINT):
                try:
                    loop.add_signal_handler(sig, signal_handler)
                except (NotImplementedError, AttributeError) as e:
                    try:
                        logger = LoggingConfig.get_logger(__name__)
                        logger.debug(
                            f"Signal handler not supported: {e}; continuing without it."
                        )
                    except Exception:
                        pass

            try:
                loop.run_until_complete(handle_stdio(config_obj, log_level))
            except Exception:
                logger = LoggingConfig.get_logger(__name__)
                logger.error("Error in main", exc_info=True)
                sys.exit(1)
            finally:
                try:
                    # Wait for the shutdown task if it exists
                    if shutdown_task is not None and not shutdown_task.done():
                        try:
                            logger = LoggingConfig.get_logger(__name__)
                            logger.debug("Waiting for shutdown task to complete...")
                            loop.run_until_complete(
                                asyncio.wait_for(shutdown_task, timeout=5.0)
                            )
                            logger.debug("Shutdown task completed successfully")
                        except TimeoutError:
                            logger = LoggingConfig.get_logger(__name__)
                            logger.warning("Shutdown task timed out, cancelling...")
                            shutdown_task.cancel()
                            try:
                                loop.run_until_complete(shutdown_task)
                            except asyncio.CancelledError:
                                logger.debug("Shutdown task cancelled successfully")
                        except Exception as e:
                            logger = LoggingConfig.get_logger(__name__)
                            logger.debug(f"Shutdown task completed with: {e}")

                    # Cancel any remaining tasks
                    all_tasks = list(asyncio.all_tasks(loop))
                    cancelled_tasks = []
                    for task in all_tasks:
                        if not task.done() and task is not shutdown_task:
                            task.cancel()
                            cancelled_tasks.append(task)

                    if cancelled_tasks:
                        logger = LoggingConfig.get_logger(__name__)
                        logger.info(
                            f"Cancelled {len(cancelled_tasks)} remaining tasks for cleanup"
                        )
                except Exception:
                    logger = LoggingConfig.get_logger(__name__)
                    logger.error("Error during final cleanup", exc_info=True)
                finally:
                    loop.close()
                    logger = LoggingConfig.get_logger(__name__)
                    logger.info("Server shutdown complete")
        else:
            raise ValueError(f"Unsupported transport: {transport}")
    except Exception:
        logger = LoggingConfig.get_logger(__name__)
        logger.error("Error in main", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
