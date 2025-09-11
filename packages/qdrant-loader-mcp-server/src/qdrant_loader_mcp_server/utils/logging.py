"""Centralized logging configuration for the MCP Server application."""

import logging
import os
import re
import sys

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
    # Use core logging config if available
    from qdrant_loader_core.logging import (
        LoggingConfig as CoreLoggingConfig,  # type: ignore
    )
except Exception:  # pragma: no cover - core may not be available
    CoreLoggingConfig = None  # type: ignore


class LoggingConfig:
    """Wrapper that standardizes env handling and tracks current config.

    Delegates to core LoggingConfig when available, while maintaining
    _initialized and _current_config for MCP server tests and utilities.
    """

    _initialized = False
    _current_config: tuple[str, str, str | None, bool] | None = None

    @classmethod
    def setup(
        cls,
        level: str = "INFO",
        format: str = "console",
        file: str | None = None,
        suppress_qdrant_warnings: bool = True,
    ) -> None:
        # Resolve from environment when present for level; for file only when using all defaults
        env_level = os.getenv("MCP_LOG_LEVEL")
        resolved_level = (env_level or level).upper()
        env_file = os.getenv("MCP_LOG_FILE")
        all_defaults = (
            level == "INFO"
            and format == "console"
            and file is None
            and suppress_qdrant_warnings is True
        )
        resolved_file = (
            file if file is not None else (env_file if all_defaults else None)
        )
        disable_console_logging = (
            os.getenv("MCP_DISABLE_CONSOLE_LOGGING", "").lower() == "true"
        )

        # Validate level
        if not hasattr(logging, resolved_level):
            raise ValueError(f"Invalid log level: {resolved_level}")

        numeric_level = getattr(logging, resolved_level)

        if CoreLoggingConfig is not None:
            # Delegate to core implementation
            CoreLoggingConfig.setup(
                level=resolved_level,
                format=format,
                file=resolved_file,
                suppress_qdrant_warnings=suppress_qdrant_warnings,
                disable_console=disable_console_logging,
            )
        else:
            # Minimal fallback behavior
            handlers: list[logging.Handler] = []
            if not disable_console_logging:
                stderr_handler = logging.StreamHandler(sys.stderr)
                stderr_handler.setFormatter(logging.Formatter("%(message)s"))
                handlers.append(stderr_handler)
            if resolved_file:
                file_handler = logging.FileHandler(resolved_file)
                file_handler.setFormatter(CleanFormatter("%(message)s"))
                handlers.append(file_handler)
            logging.basicConfig(level=numeric_level, handlers=handlers, force=True)
            if suppress_qdrant_warnings:
                logging.getLogger("qdrant_client").addFilter(QdrantVersionFilter())

        cls._initialized = True
        cls._current_config = (
            resolved_level,
            format,
            resolved_file,
            suppress_qdrant_warnings,
        )

    @classmethod
    def get_logger(cls, name: str | None = None):  # type: ignore
        if not cls._initialized:
            cls.setup()
        return structlog.get_logger(name)

    @classmethod
    def reconfigure(cls, *, file: str | None = None) -> None:
        """Lightweight file reconfiguration for MCP server wrapper.

        If core logging is present and supports reconfigure, delegate to it.
        Otherwise, force-replace root handlers with a new file handler (and keep stderr
        if console is enabled via env).
        """
        disable_console_logging = (
            os.getenv("MCP_DISABLE_CONSOLE_LOGGING", "").lower() == "true"
        )

        if CoreLoggingConfig is not None and hasattr(CoreLoggingConfig, "reconfigure"):
            CoreLoggingConfig.reconfigure(file=file)  # type: ignore
        else:
            handlers: list[logging.Handler] = []
            if not disable_console_logging:
                stderr_handler = logging.StreamHandler(sys.stderr)
                stderr_handler.setFormatter(logging.Formatter("%(message)s"))
                handlers.append(stderr_handler)
            if file:
                file_handler = logging.FileHandler(file)
                file_handler.setFormatter(CleanFormatter("%(message)s"))
                handlers.append(file_handler)
            logging.basicConfig(level=getattr(logging, (cls._current_config or ("INFO",))[0]), handlers=handlers, force=True)  # type: ignore

        if cls._current_config is not None:
            level, fmt, _, suppress = cls._current_config
            cls._current_config = (level, fmt, file, suppress)
