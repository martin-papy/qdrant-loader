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


class LoggingConfig:
    """Centralized logging configuration."""

    _initialized = False
    _current_config = None

    @classmethod
    def setup(
        cls,
        level: str = "INFO",
        format: str = "console",
        file: str | None = None,
        suppress_qdrant_warnings: bool = True,
    ) -> None:
        """Setup logging configuration.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format: Log format (json or text)
            file: Path to log file (optional)
            suppress_qdrant_warnings: Whether to suppress Qdrant version check warnings
        """
        # Check if console logging is disabled first
        disable_console_logging = (
            os.getenv("MCP_DISABLE_CONSOLE_LOGGING", "").lower() == "true"
        )

        try:
            # Get log level from environment variable or use default
            level = os.getenv("MCP_LOG_LEVEL", level)
            # Convert string level to logging level
            numeric_level = getattr(logging, level.upper())
        except AttributeError:
            raise ValueError(f"Invalid log level: {level}") from None

        # Reset logging configuration
        logging.getLogger().handlers = []
        structlog.reset_defaults()

        # Create a list of handlers
        handlers = []

        # Add console handler for stderr only if console logging is not disabled
        if not disable_console_logging:
            stderr_handler = logging.StreamHandler(sys.stderr)
            stderr_handler.setFormatter(logging.Formatter("%(message)s"))
            stderr_handler.addFilter(
                ApplicationFilter()
            )  # Only show our application logs
            handlers.append(stderr_handler)

        # Add file handler if file is configured
        if file:
            file_handler = logging.FileHandler(file)
            file_handler.setFormatter(CleanFormatter("%(message)s"))
            handlers.append(file_handler)

        # Add clean log file handler at configured path
        log_file = os.getenv("MCP_LOG_FILE")
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            clean_log_handler = logging.FileHandler(log_path)
            clean_log_handler.setFormatter(CleanFormatter("%(message)s"))
            clean_log_handler.addFilter(ApplicationFilter())
            handlers.append(clean_log_handler)

        # Configure standard logging
        logging.basicConfig(
            level=numeric_level,
            format="%(message)s",
            handlers=handlers,
            force=True,  # Force reconfiguration
        )

        # Add filter to suppress Qdrant version check warnings
        if suppress_qdrant_warnings:
            qdrant_logger = logging.getLogger("qdrant_client")
            qdrant_logger.addFilter(QdrantVersionFilter())

        # Configure structlog processors based on format
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.CallsiteParameterAdder(
                [
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
        ]

        if format == "json":
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer(colors=True))

        # Configure structlog
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=False,  # Disable caching to ensure new configuration is used
        )

        cls._initialized = True
        cls._current_config = (level, format, file, suppress_qdrant_warnings)

    @classmethod
    def get_logger(cls, name: str | None = None) -> structlog.BoundLogger:
        """Get a logger instance.

        Args:
            name: Logger name. If None, will use the calling module's name.

        Returns:
            structlog.BoundLogger: Logger instance
        """
        if not cls._initialized:
            # Initialize with default settings if not already initialized
            cls.setup()
        return structlog.get_logger(name)
