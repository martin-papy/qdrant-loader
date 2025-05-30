"""Centralized logging configuration for the application."""

import logging
import structlog
import sys
import re
from typing import Any, Dict


class QdrantVersionFilter(logging.Filter):
    """Filter to suppress Qdrant version check warnings."""

    def filter(self, record):
        return "version check" not in record.getMessage().lower()


class ApplicationFilter(logging.Filter):
    """Filter to only show logs from our application."""

    def filter(self, record):
        # Only show logs from our application
        return not record.name.startswith(("httpx", "httpcore", "urllib3"))


class VerbosityFilter(logging.Filter):
    """Filter to reduce verbosity of debug messages."""

    def filter(self, record):
        # Suppress overly verbose debug messages
        message = record.getMessage()
        verbose_patterns = [
            "HTTP Request:",
            "Response status:",
            "Request headers:",
            "Response headers:",
        ]
        return not any(pattern in message for pattern in verbose_patterns)


class CleanFileHandler(logging.FileHandler):
    """Custom file handler that strips ANSI color codes from log messages."""

    # ANSI escape sequence pattern
    ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    def emit(self, record):
        """Emit a record, stripping ANSI codes from the message."""
        try:
            # Get the formatted message
            msg = self.format(record)
            # Strip ANSI escape sequences
            clean_msg = self.ANSI_ESCAPE.sub("", msg)
            # Write the clean message
            stream = self.stream
            stream.write(clean_msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


class CleanFormatter(logging.Formatter):
    """Custom formatter that shows only the message for INFO level logs."""

    def __init__(self, use_custom_renderer=False):
        super().__init__()
        self.use_custom_renderer = use_custom_renderer

    def format(self, record):
        message = record.getMessage()

        # If we're using the custom renderer, just return the message as-is
        # since the CustomConsoleRenderer already handled the formatting
        if self.use_custom_renderer:
            return message

        # For INFO level, just show the message
        if record.levelno == logging.INFO:
            return message
        else:
            # For other levels, we need to reorder timestamp and level
            # Check if message starts with a timestamp (HH:MM:SS format)
            # The message might contain ANSI color codes, so we need to account for that
            time_pattern = (
                r"^(?:\x1b\[[0-9;]*m)?(\d{2}:\d{2}:\d{2})(?:\x1b\[[0-9;]*m)?\s+(.*)"
            )
            match = re.match(time_pattern, message)

            if match:
                timestamp = match.group(1)
                rest_of_message = match.group(2)
                return f"{timestamp} [{record.levelname}] {rest_of_message}"
            else:
                # No timestamp found, just add level name
                return f"[{record.levelname}] {message}"


class FileRenderer:
    """Custom renderer for file output without timestamps (FileFormatter will add them)."""

    def __call__(self, logger, method_name, event_dict):
        # Extract the main message
        event = event_dict.pop("event", "")

        # Format additional key-value pairs
        if event_dict:
            extras = " ".join(f"{k}={v}" for k, v in event_dict.items())
            return f"{event} {extras}".strip()
        else:
            return event


class FileFormatter(logging.Formatter):
    """Custom formatter for file output that provides clean, readable logs without ANSI codes."""

    # ANSI escape sequence pattern
    ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    def format(self, record):
        # Get the timestamp
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")

        # Get the level name
        level = record.levelname

        # Get the message (this will be the already formatted structlog message)
        message = record.getMessage()

        # First, strip ANSI escape sequences
        clean_message = self.ANSI_ESCAPE.sub("", message)

        # Now check if the clean message starts with a timestamp and remove it
        # Pattern for structlog output: "HH:MM:SS message content"
        time_pattern = r"^\d{2}:\d{2}:\d{2}\s+"
        if re.match(time_pattern, clean_message):
            # Remove the structlog timestamp since we're adding our own
            clean_message = re.sub(time_pattern, "", clean_message)

        # Format based on log level
        if record.levelno == logging.INFO:
            # For INFO level, use a clean format: timestamp | message
            return f"{timestamp} | {clean_message}"
        else:
            # For other levels, include the level: timestamp | [LEVEL] message
            return f"{timestamp} | [{level}] {clean_message}"


class CustomConsoleRenderer:
    """Custom console renderer that formats timestamp and level correctly."""

    def __init__(self, colors=True):
        self.colors = colors
        self._console_renderer = structlog.dev.ConsoleRenderer(colors=colors)
        # ANSI color codes
        self.gray = "\033[90m" if colors else ""
        self.green = "\033[92m" if colors else ""  # Bright green for INFO
        self.yellow = "\033[93m" if colors else ""  # Bright yellow for WARNING
        self.red = "\033[91m" if colors else ""  # Bright red for ERROR
        self.magenta = "\033[95m" if colors else ""  # Bright magenta for CRITICAL
        self.cyan = "\033[96m" if colors else ""  # Bright cyan for DEBUG
        self.reset = "\033[0m" if colors else ""

    def _get_level_color(self, level):
        """Get the appropriate color for a log level."""
        level_colors = {
            "DEBUG": self.cyan,
            "INFO": self.green,  # Green for INFO
            "WARNING": self.yellow,
            "ERROR": self.red,
            "CRITICAL": self.magenta,
        }
        return level_colors.get(level, "")

    def __call__(self, logger, method_name, event_dict):
        # Extract timestamp if present
        timestamp = event_dict.pop("timestamp", None)

        # Get the level from method_name
        level = method_name.upper()

        # Use the default console renderer to format the rest
        formatted = self._console_renderer(logger, method_name, event_dict)

        # If we have a timestamp
        if timestamp and isinstance(timestamp, str) and len(timestamp) >= 8:
            time_part = timestamp[:8]  # Get HH:MM:SS part

            # Remove the timestamp from the formatted message if it's there
            if formatted.startswith(time_part):
                formatted = formatted[len(time_part) :].lstrip()

            # Add gray color to timestamp
            colored_timestamp = f"{self.gray}{time_part}{self.reset}"

            # Get colored level for all levels including INFO
            level_color = self._get_level_color(level)
            colored_level = (
                f"{level_color}[{level}]{self.reset}" if level_color else f"[{level}]"
            )

            # Show timestamp, colored level, and message for all levels
            return f"{colored_timestamp} {colored_level} {formatted}"

        # Fallback if no timestamp
        level_color = self._get_level_color(level)
        colored_level = (
            f"{level_color}[{level}]{self.reset}" if level_color else f"[{level}]"
        )
        return f"{colored_level} {formatted}"


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
        clean_output: bool = True,
    ) -> None:
        """Setup logging configuration.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format: Log format (json or console)
            file: Path to log file (optional)
            suppress_qdrant_warnings: Whether to suppress Qdrant version check warnings
            clean_output: Whether to use clean, less verbose output
        """
        try:
            # Convert string level to logging level
            numeric_level = getattr(logging, level.upper())
        except AttributeError:
            raise ValueError(f"Invalid log level: {level}") from None

        # Reset logging configuration
        logging.getLogger().handlers = []
        structlog.reset_defaults()

        # Create a list of handlers
        handlers = []

        # Add console handler
        console_handler = logging.StreamHandler()

        if clean_output and format == "console":
            # Use clean formatter for console output
            console_handler.setFormatter(CleanFormatter(use_custom_renderer=True))
        else:
            console_handler.setFormatter(logging.Formatter("%(message)s"))

        console_handler.addFilter(ApplicationFilter())  # Only show our application logs

        if clean_output:
            console_handler.addFilter(VerbosityFilter())  # Reduce verbosity

        handlers.append(console_handler)

        # Add file handler if file is configured
        if file:
            file_handler = CleanFileHandler(file)
            file_handler.setFormatter(FileFormatter())
            # Don't apply verbosity filter to file logs - keep everything for debugging
            handlers.append(file_handler)

        # Configure standard logging
        logging.basicConfig(
            level=numeric_level,
            format="%(message)s",
            handlers=handlers,
        )

        # Add filter to suppress Qdrant version check warnings
        if suppress_qdrant_warnings:
            qdrant_logger = logging.getLogger("qdrant_client")
            qdrant_logger.addFilter(QdrantVersionFilter())

        # Configure structlog processors based on format and clean_output
        if clean_output and format == "console":
            # Minimal processors for clean output
            processors = [
                structlog.stdlib.filter_by_level,
                structlog.processors.TimeStamper(fmt="%H:%M:%S"),
                CustomConsoleRenderer(colors=True),
            ]
        else:
            # Full processors for detailed output
            processors = [
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
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
        cls._current_config = (
            level,
            format,
            file,
            suppress_qdrant_warnings,
            clean_output,
        )

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
