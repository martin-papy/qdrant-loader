"""CLI module for QDrant Loader MCP Server."""

import json
import logging
import os
import sys
from pathlib import Path

import click
from click.decorators import option
from click.types import Choice
from click.types import Path as ClickPath
from dotenv import load_dotenv

from .config_loader import load_config, redact_effective_config
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
    help="Transport protocol to use (stdio for JSON-RPC over stdin/stdout, http for streamable HTTP)",
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

    The server is built on FastMCP and supports both stdio (JSON-RPC over
    stdin/stdout) and HTTP (streamable) transports.

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
        # the FastMCP lifespan (which resolves config independently) can find it.
        if config is not None:
            try:
                os.environ["MCP_CONFIG"] = str(config)
            except Exception:
                # Best-effort; continue without blocking startup
                pass

        # Resolve configuration early (fail fast; also powers --print-config).
        _, effective_cfg, _ = load_config(config)

        if print_config:
            redacted = redact_effective_config(effective_cfg)
            click.echo(json.dumps(redacted, indent=2))
            return

        if transport.lower() == "http":
            import uvicorn

            os.environ["MCP_LOG_LEVEL"] = log_level
            os.environ["MCP_HOST"] = host
            os.environ["MCP_PORT"] = str(port)

            logger = LoggingConfig.get_logger(__name__)
            logger.info(
                "Starting HTTP server (FastMCP)",
                host=host,
                port=port,
                log_level=log_level,
            )

            uvicorn.run(
                "qdrant_loader_mcp_server.fastmcp_app:http_app",
                host=host,
                port=port,
                workers=workers,
                log_level=log_level.lower(),
                access_log=(log_level.upper() == "DEBUG"),
            )
        elif transport.lower() == "stdio":
            logger = LoggingConfig.get_logger(__name__)
            logger.info("Starting stdio transport (FastMCP)")
            from .fastmcp_app import mcp

            mcp.run(transport="stdio", show_banner=False)
        else:
            raise ValueError(f"Unsupported transport: {transport}")
    except Exception:
        logger = LoggingConfig.get_logger(__name__)
        logger.error("Error in main", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
