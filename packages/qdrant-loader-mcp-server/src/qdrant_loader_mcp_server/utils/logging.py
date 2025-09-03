"""Centralized logging configuration for the MCP Server application."""

import logging
import os
import re
import sys
from pathlib import Path

import structlog


class QdrantVersionFilter(logging.Filter):
    """Filter to suppress Qdrant version check warnings."""

    def filter(self, record):
        return "Failed to obtain server version" not in str(record.msg)


class ApplicationFilter(logging.Filter):
    """Filter to only show logs from our application."""

    def filter(self, record):
        # Show logs from our application and related modules
        return (
            record.name.startswith("mcp_server")
            or record.name.startswith("src.")
            or record.name == "uvicorn"
            or record.name == "fastapi"
            or record.name == "__main__"  # Allow logs from main module
            or record.name == "asyncio"  # Allow logs from asyncio
            or record.name == "main"  # Allow logs when started as a script
            or record.name == "qdrant_loader_mcp_server"  # Allow logs from the package
        )


class CleanFormatter(logging.Formatter):
    """Formatter that removes ANSI color codes."""

    def format(self, record):
        # Get the formatted message
        message = super().format(record)
        # Remove ANSI color codes
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_escape.sub("", message)


try:
    # Re-export core LoggingConfig to standardize behavior across packages
    from qdrant_loader_core.logging import LoggingConfig  # type: ignore
except Exception:
    # Fallback shim using previous behavior if core is unavailable
    class LoggingConfig:
        @classmethod
        def setup(
            cls,
            level: str = "INFO",
            format: str = "console",
            file: str | None = None,
            suppress_qdrant_warnings: bool = True,
        ) -> None:
            # Maintain minimal behavior
            disable_console_logging = (
                os.getenv("MCP_DISABLE_CONSOLE_LOGGING", "").lower() == "true"
            )
            numeric_level = getattr(logging, level.upper(), logging.INFO)
            handlers = []
            if not disable_console_logging:
                stderr_handler = logging.StreamHandler(sys.stderr)
                stderr_handler.setFormatter(logging.Formatter("%(message)s"))
                handlers.append(stderr_handler)
            if file:
                file_handler = logging.FileHandler(file)
                file_handler.setFormatter(CleanFormatter("%(message)s"))
                handlers.append(file_handler)
            logging.basicConfig(level=numeric_level, handlers=handlers, force=True)

        @classmethod
        def get_logger(cls, name: str | None = None):  # type: ignore
            return structlog.get_logger(name)
