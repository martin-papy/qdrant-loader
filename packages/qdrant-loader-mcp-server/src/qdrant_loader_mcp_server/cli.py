"""CLI module for QDrant Loader MCP Server."""

import asyncio
import json
import logging
import os
import signal
import sys
import time
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
from .transport import HTTPTransportHandler
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


async def read_stdin():
    """Read from stdin asynchronously."""
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    return reader


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


async def start_http_server(
    config: Config, log_level: str, host: str, port: int, shutdown_event: asyncio.Event
):
    """Start MCP server with HTTP transport."""
    logger = LoggingConfig.get_logger(__name__)
    search_engine = None

    try:
        logger.info(f"Starting HTTP server on {host}:{port}")

        # Initialize components
        search_engine = SearchEngine()
        query_processor = QueryProcessor(config.openai)
        mcp_handler = MCPHandler(search_engine, query_processor)

        # Initialize search engine
        try:
            await search_engine.initialize(config.qdrant, config.openai, config.search)
            logger.info("Search engine initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize search engine", exc_info=True)
            raise RuntimeError("Failed to initialize search engine") from e

        # Create HTTP transport handler
        http_handler = HTTPTransportHandler(mcp_handler, host=host, port=port)

        # Start the FastAPI server using uvicorn
        import uvicorn

        uvicorn_config = uvicorn.Config(
            app=http_handler.app,
            host=host,
            port=port,
            log_level=log_level.lower(),
            access_log=log_level.upper() == "DEBUG",
        )

        server = uvicorn.Server(uvicorn_config)
        logger.info(f"HTTP MCP server ready at http://{host}:{port}/mcp")

        # Create a task to monitor shutdown event
        async def shutdown_monitor():
            try:
                await shutdown_event.wait()
                logger.info("Shutdown signal received, stopping HTTP server...")

                # Signal uvicorn to stop gracefully
                server.should_exit = True

                # Graceful drain logic: wait for in-flight requests to finish before forcing exit
                # Configurable timeouts via environment variables
                drain_timeout = float(
                    os.getenv("MCP_HTTP_DRAIN_TIMEOUT_SECONDS", "10.0")
                )
                max_shutdown_timeout = float(
                    os.getenv("MCP_HTTP_SHUTDOWN_TIMEOUT_SECONDS", "30.0")
                )

                start_ts = time.monotonic()

                # 1) Prioritize draining non-streaming requests quickly
                drained_non_stream = False
                try:
                    while time.monotonic() - start_ts < drain_timeout:
                        if not http_handler.has_inflight_non_streaming():
                            drained_non_stream = True
                            logger.info(
                                "Non-streaming requests drained; continuing shutdown"
                            )
                            break
                        await asyncio.sleep(0.1)
                except asyncio.CancelledError:
                    logger.debug("Shutdown monitor cancelled during drain phase")
                    return
                except Exception:
                    # On any error during drain check, fall through to timeout-based force
                    pass

                if not drained_non_stream:
                    logger.warning(
                        f"Non-streaming requests still in flight after {drain_timeout}s; proceeding with shutdown"
                    )

                # 2) Allow additional time (up to max_shutdown_timeout total) for all requests to complete
                total_deadline = start_ts + max_shutdown_timeout
                try:
                    while time.monotonic() < total_deadline:
                        counts = http_handler.get_inflight_request_counts()
                        if counts.get("total", 0) == 0:
                            logger.info(
                                "All in-flight requests drained; completing shutdown without force"
                            )
                            break
                        await asyncio.sleep(0.2)
                except asyncio.CancelledError:
                    logger.debug("Shutdown monitor cancelled during final drain phase")
                    return
                except Exception:
                    pass

                # 3) If still not finished after the max timeout, force the server to exit
                if hasattr(server, "force_exit"):
                    if time.monotonic() >= total_deadline:
                        logger.warning(
                            f"Forcing server exit after {max_shutdown_timeout}s shutdown timeout"
                        )
                        server.force_exit = True
                    else:
                        logger.debug(
                            "Server drained gracefully; force_exit not required"
                        )
            except asyncio.CancelledError:
                logger.debug("Shutdown monitor task cancelled")
                return

        # Start shutdown monitor task
        monitor_task = asyncio.create_task(shutdown_monitor())

        try:
            # Run the server until shutdown
            await server.serve()
        except asyncio.CancelledError:
            logger.info("Server shutdown initiated")
        except Exception as e:
            if not shutdown_event.is_set():
                logger.error(f"Server error: {e}", exc_info=True)
            else:
                logger.info(f"Server stopped during shutdown: {e}")
        finally:
            # Clean up the monitor task gracefully
            if monitor_task and not monitor_task.done():
                logger.debug("Cleaning up shutdown monitor task")
                monitor_task.cancel()
                try:
                    await asyncio.wait_for(monitor_task, timeout=2.0)
                except asyncio.CancelledError:
                    logger.debug("Shutdown monitor task cancelled successfully")
                except TimeoutError:
                    logger.warning("Shutdown monitor task cleanup timed out")
                except Exception as e:
                    logger.debug(f"Shutdown monitor cleanup completed with: {e}")

    except Exception as e:
        if not shutdown_event.is_set():
            logger.error(f"Error in HTTP server: {e}", exc_info=True)
        raise
    finally:
        # Clean up search engine
        if search_engine:
            try:
                await search_engine.cleanup()
                logger.info("Search engine cleanup completed")
            except Exception as e:
                logger.error(f"Error during search engine cleanup: {e}", exc_info=True)


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
            await search_engine.initialize(config.qdrant, config.openai, config.search)
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
    loop = None
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

        # Create and set the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Create shutdown event for coordinating graceful shutdown
        shutdown_event = asyncio.Event()
        shutdown_task = None

        # Set up signal handlers with shutdown event
        def signal_handler():
            # Schedule shutdown on the explicit loop for clarity and correctness
            nonlocal shutdown_task
            if shutdown_task is None:
                shutdown_task = loop.create_task(shutdown(loop, shutdown_event))

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)

        # Start the appropriate transport handler
        if transport.lower() == "stdio":
            loop.run_until_complete(handle_stdio(config_obj, log_level))
        elif transport.lower() == "http":
            loop.run_until_complete(
                start_http_server(config_obj, log_level, host, port, shutdown_event)
            )
        else:
            raise ValueError(f"Unsupported transport: {transport}")
    except Exception:
        logger = LoggingConfig.get_logger(__name__)
        logger.error("Error in main", exc_info=True)
        sys.exit(1)
    finally:
        if loop:
            try:
                # First, wait for the shutdown task if it exists
                if (
                    "shutdown_task" in locals()
                    and shutdown_task is not None
                    and not shutdown_task.done()
                ):
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

                # Then cancel any remaining tasks (except completed shutdown task)
                def _cancel_all_pending_tasks():
                    """Cancel tasks safely without circular dependencies."""
                    all_tasks = list(asyncio.all_tasks(loop))
                    if not all_tasks:
                        return

                    # Cancel all tasks except the completed shutdown task
                    cancelled_tasks = []
                    for task in all_tasks:
                        if not task.done() and task is not shutdown_task:
                            task.cancel()
                            cancelled_tasks.append(task)

                    # Don't await gather to avoid recursion - just let them finish on their own
                    # The loop will handle the cleanup when it closes
                    if cancelled_tasks:
                        logger = LoggingConfig.get_logger(__name__)
                        logger.info(
                            f"Cancelled {len(cancelled_tasks)} remaining tasks for cleanup"
                        )

                _cancel_all_pending_tasks()
            except Exception:
                logger = LoggingConfig.get_logger(__name__)
                logger.error("Error during final cleanup", exc_info=True)
            finally:
                loop.close()
                logger = LoggingConfig.get_logger(__name__)
                logger.info("Server shutdown complete")


if __name__ == "__main__":
    cli()
