"""Centralized logging configuration for the application."""

import logging

import structlog


class QdrantVersionFilter(logging.Filter):
    """Filter to suppress Qdrant version check warnings."""

    def filter(self, record):
        return "Failed to obtain server version" not in str(record.msg)


class ApplicationFilter(logging.Filter):
    """Filter to only show logs from our application."""

    def filter(self, record):
        # Only show logs from our application
        return record.name.startswith("qdrant_loader")


class VerbosityFilter(logging.Filter):
    """Filter to reduce verbosity by suppressing certain debug messages."""

    def filter(self, record):
        # Suppress overly verbose debug messages
        message = str(record.msg)

        # Skip these verbose debug messages
        verbose_debug_patterns = [
            "Making JIRA API request",
            "JIRA API request completed successfully",
            "Getting batch embeddings from",
            "Getting embedding from",
            "Completed batch processing",
            "Processing embedding batch",
            "Embedding request failed",
            "Single embedding request failed",
            "Fetching JIRA issues page",
            "Processing JIRA issues page",
            "Processed JIRA issues",
            "Starting document chunking",
            "Selected chunking strategy",
            "Document chunking completed",
            "Jira document created",
            "Processing documents from source",
            "Document processed successfully",
            "Chunk created",
            "Embedding generated",
            "Document stored in Qdrant",
        ]

        # Skip these verbose info messages too
        verbose_info_patterns = [
            "Configured Confluence",
            "Configured Jira",
            "File conversion enabled",
            "Attachment downloader initialized",
            "Successfully connected to qDrant",
            "Creating pipeline components",
            "Pipeline components created successfully",
            "Initializing metrics directory",
            "AsyncIngestionPipeline initialized",
            "Starting document processing with new pipeline",
            "Starting document processing orchestration",
            "Processing Confluence sources:",
            "Processing Jira sources:",
            "Processing Confluence source:",
            "Processing Jira source:",
            "Retrieved",
            "Completed processing",
            "Starting JIRA issue retrieval",
            "Found",
            "Fetching Confluence",
            "Processed",
            "documents from",
            "total results in",
            "pages from space",
        ]

        # If it's a debug message and matches verbose patterns, suppress it
        if record.levelno == logging.DEBUG:
            for pattern in verbose_debug_patterns:
                if pattern in message:
                    return False

        # If it's an info message and matches verbose patterns, suppress it
        if record.levelno == logging.INFO:
            for pattern in verbose_info_patterns:
                if pattern in message:
                    return False

        return True


class CleanFormatter(logging.Formatter):
    """Clean formatter that removes excessive metadata."""

    def format(self, record):
        # For INFO level, just show the message
        if record.levelno == logging.INFO:
            return record.getMessage()

        # For WARNING/ERROR, add level indicator
        level_indicators = {
            logging.WARNING: "⚠️ ",
            logging.ERROR: "❌ ",
            logging.CRITICAL: "🚨 ",
            logging.DEBUG: "🔍 ",
        }

        indicator = level_indicators.get(record.levelno, "")
        return f"{indicator}{record.getMessage()}"


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
            console_handler.setFormatter(CleanFormatter())
        else:
            console_handler.setFormatter(logging.Formatter("%(message)s"))

        console_handler.addFilter(ApplicationFilter())  # Only show our application logs

        if clean_output:
            console_handler.addFilter(VerbosityFilter())  # Reduce verbosity

        handlers.append(console_handler)

        # Add file handler if file is configured
        if file:
            file_handler = logging.FileHandler(file)
            file_handler.setFormatter(logging.Formatter("%(message)s"))
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
                structlog.dev.ConsoleRenderer(
                    colors=True,
                ),
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
