"""Centralized logging configuration for the application."""

import logging
import re

import structlog


class QdrantVersionFilter(logging.Filter):
    """Filter to suppress Qdrant version check warnings."""

    def filter(self, record):
        return "version check" not in record.getMessage().lower()


class ApplicationFilter(logging.Filter):
    """Filter to only show logs from our application."""

    def filter(self, record):
        # Only show logs from our application
        return not record.name.startswith(("httpx", "httpcore", "urllib3"))


class SQLiteFilter(logging.Filter):
    """Filter to suppress verbose SQLite operation logs."""

    def filter(self, record):
        # Suppress verbose SQLite debug logs
        message = record.getMessage()
        sqlite_patterns = [
            "executing functools.partial(<built-in method",
            "operation functools.partial(<built-in method",
            "executing <function connect.",
            "operation <function connect.",
            "returning exception",
        ]
        return not any(pattern in message for pattern in sqlite_patterns)


class VerbosityFilter(logging.Filter):
    """Filter to reduce verbosity of debug messages."""

    def filter(self, record):
        # Only filter DEBUG level messages
        if record.levelno != logging.DEBUG:
            return True

        # Suppress overly verbose debug messages
        message = record.getMessage()
        verbose_patterns = [
            "HTTP Request:",
            "Response status:",
            "Request headers:",
            "Response headers:",
            # PDF parsing debug messages
            "seek:",
            "nexttoken:",
            "do_keyword:",
            "nextobject:",
            "add_results:",
            "register:",
            "getobj:",
            "get_unichr:",
            "exec:",
            # Character encoding detection
            "confidence =",
            "prober hit error",
            "not active",
            # File processing verbosity
            "checking if file should be processed",
            "current configuration",
            "checking file extension",
            "file type detection",
            "file supported via",
            "starting metadata extraction",
            "completed metadata extraction",
            "document metadata:",
            # HTTP client debug
            "connect_tcp.started",
            "connect_tcp.complete",
            "send_request_headers",
            "send_request_body",
            "receive_response_headers",
            "receive_response_body",
            "response_closed",
        ]
        return not any(pattern in message for pattern in verbose_patterns)


class WindowsSafeConsoleHandler(logging.StreamHandler):
    """Custom console handler that handles Windows encoding issues."""

    # ANSI escape sequence pattern
    ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    def emit(self, record):
        """Emit a record, handling Windows console encoding issues."""
        try:
            # Check if stream is still open before writing
            if hasattr(self.stream, "closed") and self.stream.closed:
                return  # Skip logging if stream is closed

            # Get the formatted message
            msg = self.format(record)

            # For Windows, handle Unicode characters proactively
            import sys

            if sys.platform == "win32":
                # Replace problematic Unicode characters with safe alternatives
                safe_msg = (
                    msg.replace("🚀", "[ROCKET]")
                    .replace("📄", "[DOCUMENT]")
                    .replace("✅", "[CHECK]")
                    .replace("❌", "[CROSS]")
                    .replace("⚠️", "[WARNING]")
                    .replace("🔍", "[SEARCH]")
                    .replace("💾", "[SAVE]")
                    .replace("🔧", "[TOOL]")
                    .replace("📊", "[CHART]")
                    .replace("🎯", "[TARGET]")
                    .replace("⚙️", "[GEAR]")
                    .replace("⏱️", "[TIMER]")
                    .replace("⏭️", "[NEXT]")
                    .replace("🏗️", "[CONSTRUCTION]")
                    .replace("1️⃣", "[1]")
                    .replace("2️⃣", "[2]")
                    .replace("3️⃣", "[3]")
                    .replace("4️⃣", "[4]")
                )
                try:
                    self.stream.write(safe_msg + self.terminator)
                except UnicodeEncodeError:
                    # Final fallback: encode with ASCII and replace all unsupported chars
                    ascii_msg = safe_msg.encode("ascii", errors="replace").decode(
                        "ascii"
                    )
                    self.stream.write(ascii_msg + self.terminator)
            else:
                # For non-Windows, use standard handling
                self.stream.write(msg + self.terminator)

            self.flush()
        except (ValueError, OSError):
            # Stream is closed or unavailable, skip silently
            pass
        except Exception:
            self.handleError(record)


class CleanFileHandler(logging.FileHandler):
    """Custom file handler that strips ANSI color codes from log messages."""

    # ANSI escape sequence pattern
    ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    def emit(self, record):
        """Emit a record, stripping ANSI codes from the message."""
        try:
            # Check if stream is still open before writing
            if hasattr(self.stream, "closed") and self.stream.closed:
                return  # Skip logging if stream is closed

            # Get the formatted message
            msg = self.format(record)
            # Strip ANSI escape sequences
            clean_msg = self.ANSI_ESCAPE.sub("", msg)

            # Handle Windows console encoding issues more robustly
            stream = self.stream
            try:
                stream.write(clean_msg + self.terminator)
            except UnicodeEncodeError:
                # Fallback for Windows console encoding issues
                # Replace problematic Unicode characters with safe alternatives
                import sys

                if sys.platform == "win32":
                    # Replace common emoji/Unicode characters with ASCII equivalents
                    safe_msg = (
                        clean_msg.replace("🚀", "[ROCKET]")
                        .replace("📄", "[DOCUMENT]")
                        .replace("✅", "[CHECK]")
                        .replace("❌", "[CROSS]")
                        .replace("⚠️", "[WARNING]")
                        .replace("🔍", "[SEARCH]")
                        .replace("💾", "[SAVE]")
                        .replace("🔧", "[TOOL]")
                        .replace("📊", "[CHART]")
                        .replace("🎯", "[TARGET]")
                        .replace("⚙️", "[GEAR]")
                        .replace("⏱️", "[TIMER]")
                        .replace("⏭️", "[NEXT]")
                        .replace("🏗️", "[CONSTRUCTION]")
                        .replace("1️⃣", "[1]")
                        .replace("2️⃣", "[2]")
                        .replace("3️⃣", "[3]")
                        .replace("4️⃣", "[4]")
                    )
                    try:
                        stream.write(safe_msg + self.terminator)
                    except UnicodeEncodeError:
                        # Final fallback: encode with ASCII and replace all unsupported chars
                        ascii_msg = safe_msg.encode("ascii", errors="replace").decode(
                            "ascii"
                        )
                        stream.write(ascii_msg + self.terminator)
                else:
                    # For non-Windows, try UTF-8 encoding with replacement
                    safe_msg = clean_msg.encode("utf-8", errors="replace").decode(
                        "utf-8", errors="replace"
                    )
                    stream.write(safe_msg + self.terminator)
            self.flush()
        except (ValueError, OSError):
            # Stream is closed or unavailable, skip silently
            pass
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

                # Check if the rest_of_message already contains a level tag
                # This can happen when CustomConsoleRenderer already formatted it
                level_in_message_pattern = (
                    r"^\[(?:DEBUG|INFO|WARNING|ERROR|CRITICAL)\]\s"
                )
                if re.match(level_in_message_pattern, rest_of_message):
                    # Level already present, don't add another one
                    return f"{timestamp} {rest_of_message}"
                else:
                    # Add level tag
                    return f"{timestamp} [{record.levelname}] {rest_of_message}"
            else:
                # No timestamp found
                # Check if message already has a level tag at the beginning
                level_in_message_pattern = (
                    r"^\[(?:DEBUG|INFO|WARNING|ERROR|CRITICAL)\]\s"
                )
                if re.match(level_in_message_pattern, message):
                    # Level already present, don't add another one
                    return message
                else:
                    # Add level tag
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

        # Check if the message already contains a level tag to avoid duplication
        level_in_message_pattern = r"^\[(?:DEBUG|INFO|WARNING|ERROR|CRITICAL)\]\s"
        has_level_tag = re.match(level_in_message_pattern, clean_message)

        # Format based on log level
        if record.levelno == logging.INFO:
            # For INFO level, use a clean format: timestamp | message
            return f"{timestamp} | {clean_message}"
        else:
            # For other levels, include the level only if not already present
            if has_level_tag:
                return f"{timestamp} | {clean_message}"
            else:
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

        # Add console handler with Windows encoding support

        # Use Windows-safe console handler for all platforms
        console_handler = WindowsSafeConsoleHandler()

        if clean_output and format == "console":
            # Use clean formatter for console output
            console_handler.setFormatter(CleanFormatter(use_custom_renderer=True))
        else:
            console_handler.setFormatter(logging.Formatter("%(message)s"))

        console_handler.addFilter(ApplicationFilter())  # Only show our application logs
        console_handler.addFilter(SQLiteFilter())  # Suppress verbose SQLite logs

        if clean_output:
            console_handler.addFilter(VerbosityFilter())  # Reduce verbosity

        handlers.append(console_handler)

        # Add file handler if file is configured
        if file:
            file_handler = CleanFileHandler(file)
            file_handler.setFormatter(FileFormatter())
            file_handler.addFilter(
                SQLiteFilter()
            )  # Suppress verbose SQLite logs in files too
            # Don't apply verbosity filter to file logs - keep everything for debugging
            handlers.append(file_handler)

        # Configure standard logging
        logging.basicConfig(
            level=numeric_level,
            format="%(message)s",
            handlers=handlers,
        )

        # Apply SQLite filter to all existing loggers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            handler.addFilter(SQLiteFilter())

        # Add filter to suppress Qdrant version check warnings
        if suppress_qdrant_warnings:
            qdrant_logger = logging.getLogger("qdrant_client")
            qdrant_logger.addFilter(QdrantVersionFilter())

            # Suppress verbose SQLAlchemy and SQLite logs
        sqlalchemy_loggers = [
            "sqlalchemy.engine",
            "sqlalchemy.dialects",
            "sqlalchemy.pool",
            "aiosqlite",
            "sqlite3",
        ]

        for logger_name in sqlalchemy_loggers:
            logger = logging.getLogger(logger_name)
            logger.addFilter(SQLiteFilter())
            logger.setLevel(logging.WARNING)  # Only show warnings and errors

        # Suppress verbose third-party library debug logs
        noisy_loggers = [
            "chardet",  # Character encoding detection
            "chardet.charsetprober",
            "chardet.latin1prober",
            "chardet.mbcharsetprober",
            "chardet.sbcharsetprober",
            "chardet.utf8prober",
            "pdfminer",  # PDF parsing
            "pdfminer.pdfparser",
            "pdfminer.pdfdocument",
            "pdfminer.pdfinterp",
            "pdfminer.converter",
            "pdfplumber",  # PDF processing
            "markitdown",  # File conversion
            "httpcore",  # HTTP client debug logs
            "httpx",  # HTTP client debug logs
            "gensim",  # Topic modeling library
            "gensim.models",  # LDA model training logs
            "gensim.models.ldamodel",  # Specific LDA training logs
            "gensim.corpora",  # Dictionary and corpus logs
        ]

        for logger_name in noisy_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.WARNING)  # Only show warnings and errors

        # Configure structlog processors based on format and clean_output
        # Redaction processor to mask sensitive fields in event_dict
        def _redact_sensitive(logger, method_name, event_dict):  # type: ignore[no-redef]
            sensitive_keys = {
                "api_key",
                "llm_api_key",
                "authorization",
                "Authorization",
                "token",
                "access_token",
                "secret",
                "password",
            }

            def _mask(value: str) -> str:
                try:
                    if not isinstance(value, str) or not value:
                        return "***REDACTED***"
                    # Preserve small hint while masking majority
                    if len(value) <= 8:
                        return "***REDACTED***"
                    return value[:2] + "***REDACTED***" + value[-2:]
                except Exception:
                    return "***REDACTED***"

            def _deep_redact(obj):
                try:
                    if isinstance(obj, dict):
                        red = {}
                        for k, v in obj.items():
                            if k in sensitive_keys:
                                red[k] = (
                                    _mask(v) if isinstance(v, str) else "***REDACTED***"
                                )
                            else:
                                red[k] = _deep_redact(v)
                        return red
                    if isinstance(obj, list):
                        return [_deep_redact(i) for i in obj]
                    return obj
                except Exception:
                    return obj

            return _deep_redact(event_dict)

        if clean_output and format == "console":
            # Minimal processors for clean output
            processors = [
                structlog.stdlib.filter_by_level,
                structlog.processors.TimeStamper(fmt="%H:%M:%S"),
                _redact_sensitive,
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
                _redact_sensitive,
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


# Standardize on core logging configuration
try:
    from qdrant_loader_core.logging import (
        LoggingConfig as _CoreLoggingConfig,  # type: ignore
    )

    LoggingConfig = _CoreLoggingConfig  # type: ignore[assignment]
except Exception:
    # Fallback to local implementation if core is unavailable
    pass
