"""Main application entry point for RAG MCP Server."""

import asyncio
import json
import logging  # Keep this for asyncio logger
import os
import signal
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Config
from .mcp import MCPHandler
from .search.engine import SearchEngine
from .search.processor import QueryProcessor
from .utils import LoggingConfig

# Suppress asyncio debug messages
logging.getLogger("asyncio").setLevel(logging.WARNING)

# Initialize logging first with DEBUG level and ensure it works when started as a script
try:
    # Check if console logging is disabled
    disable_console_logging = (
        os.getenv("MCP_DISABLE_CONSOLE_LOGGING", "").lower() == "true"
    )

    # Try to initialize logging with the module path
    LoggingConfig.setup(level="DEBUG", format="console")
    logger = LoggingConfig.get_logger("src.main")
except Exception:
    # If that fails, try with just the module name
    LoggingConfig.setup(level="DEBUG", format="console")
    logger = LoggingConfig.get_logger("main")

if not disable_console_logging:
    logger.info("=" * 50)
    logger.info("MCP Qdrant Loader Starting")
    logger.info("=" * 50)

# Initialize components
try:
    if not disable_console_logging:
        logger.debug("Initializing configuration...")
    config = Config()
    if not disable_console_logging:
        logger.debug("Configuration initialized successfully")

    if not disable_console_logging:
        logger.debug("Initializing search engine...")
    search_engine = SearchEngine()
    if not disable_console_logging:
        logger.debug("Search engine initialized successfully")

    if not disable_console_logging:
        logger.debug("Initializing query processor...")
    query_processor = QueryProcessor(config.openai)
    if not disable_console_logging:
        logger.debug("Query processor initialized successfully")

    if not disable_console_logging:
        logger.debug("Initializing MCP handler...")
    mcp_handler = MCPHandler(search_engine, query_processor)
    if not disable_console_logging:
        logger.debug("MCP handler initialized successfully")
except Exception:
    if not disable_console_logging:
        logger.error("Failed to initialize components", exc_info=True)
    raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # Startup
    logger.info("Starting MCP Qdrant Loader")
    try:
        await search_engine.initialize(config.qdrant, config.openai)
    except RuntimeError:
        logger.error("Failed to initialize search engine", exc_info=True)
        logger.error(
            "Server cannot start without Qdrant connection. "
            "Please ensure Qdrant is running and try again."
        )
        # Exit immediately without traceback
        os._exit(1)

    yield

    # Shutdown
    logger.info("Shutting down MCP Qdrant Loader")
    await search_engine.cleanup()


app = FastAPI(title="MCP Qdrant Loader", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def read_stdin():
    """Read from stdin non-blockingly."""
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    return reader


async def shutdown(loop: asyncio.AbstractEventLoop):
    """Handle graceful shutdown."""
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


async def handle_stdio():
    """Handle stdio communication with Cursor."""
    try:
        # Check if console logging is disabled
        disable_console_logging = (
            os.getenv("MCP_DISABLE_CONSOLE_LOGGING", "").lower() == "true"
        )

        if not disable_console_logging:
            logger.info("Setting up stdio handler...")

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

    except Exception:
        if not disable_console_logging:
            logger.error("Error in stdio handler", exc_info=True)
        raise


def main():
    """Main entry point."""
    try:
        # Create and set the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Set up signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(loop)))

        # Start the stdio handler
        loop.run_until_complete(handle_stdio())
    except Exception:
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
            logger.error("Error during final cleanup", exc_info=True)
        finally:
            loop.close()
            logger.info("Server shutdown complete")


if __name__ == "__main__":
    main()
