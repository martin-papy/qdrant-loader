"""Unified logging configuration for qdrant-loader ecosystem.

Provides:
- structlog setup (console/json/file) with redaction
- stdlib logging bridge with redaction filter
- optional suppression of noisy third-party logs
"""

from __future__ import annotations

import logging
import os

import structlog
from structlog.stdlib import LoggerFactory

from .logging_filters import ApplicationFilter, QdrantVersionFilter, RedactionFilter
from .logging_processors import CleanFormatter, redact_processor

try:
    # ExtraAdder is available in structlog >= 20
    from structlog.stdlib import ExtraAdder  # type: ignore
except Exception:  # pragma: no cover - fallback when absent
    ExtraAdder = None  # type: ignore


class LoggingConfig:
    """Core logging setup with structlog + stdlib redaction and filters."""

    _initialized = False
    _installed_handlers: list[logging.Handler] = []
    _file_handler: logging.FileHandler | None = None
    _current_config: (
        tuple[
            str,  # level
            str,  # format
            str | None,  # file
            bool,  # clean_output
            bool,  # suppress_qdrant_warnings
            bool,  # disable_console
        ]
        | None
    ) = None

    @classmethod
    def setup(
        cls,
        *,
        level: str = "INFO",
        format: str = "console",  # "console" | "json"
        file: str | None = None,
        clean_output: bool = True,
        suppress_qdrant_warnings: bool = True,
        disable_console: bool | None = None,
    ) -> None:
        # Env override for console toggling (e.g., MCP server)
        if disable_console is None:
            disable_console = (
                os.getenv("MCP_DISABLE_CONSOLE_LOGGING", "").lower() == "true"
            )

        try:
            numeric_level = getattr(logging, level.upper())
        except AttributeError:
            raise ValueError(f"Invalid log level: {level}") from None

        # Short-circuit when configuration is unchanged
        current_tuple = (
            level.upper(),
            format,
            file,
            bool(clean_output),
            bool(suppress_qdrant_warnings),
            bool(disable_console),
        )
        if cls._initialized and cls._current_config == current_tuple:
            return

        # Reset structlog defaults but preserve existing stdlib handlers (e.g., pytest caplog)
        structlog.reset_defaults()

        # Remove any handlers previously added by this class, and also clear
        # any pre-existing root handlers that may cause duplicated outputs.
        # We keep this conservative by only touching the root logger.
        root_logger = logging.getLogger()
        # First remove our previously installed handlers
        for h in list(cls._installed_handlers):
            try:
                root_logger.removeHandler(h)
                if isinstance(h, logging.FileHandler):
                    try:
                        h.close()
                    except Exception:
                        pass
            except Exception:
                pass
        cls._installed_handlers.clear()

        # Then remove any remaining handlers on the root logger (e.g., added by
        # earlier setup calls or third-parties) to avoid duplicate emissions.
        # This is safe for CLI usage; tests relying on caplog attach to non-root loggers.
        for h in list(root_logger.handlers):
            try:
                root_logger.removeHandler(h)
                if isinstance(h, logging.FileHandler):
                    try:
                        h.close()
                    except Exception:
                        pass
            except Exception:
                pass

        handlers: list[logging.Handler] = []

        # Choose timestamp format and final renderer for structlog messages
        if clean_output and format == "console":
            ts_fmt = "%H:%M:%S"
            final_renderer = structlog.dev.ConsoleRenderer(colors=True)
        else:
            ts_fmt = "iso"
            final_renderer = (
                structlog.processors.JSONRenderer()
                if format == "json"
                else structlog.dev.ConsoleRenderer(colors=True)
            )

        if not disable_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter("%(message)s"))
            console_handler.addFilter(ApplicationFilter())
            console_handler.addFilter(RedactionFilter())
            handlers.append(console_handler)

        if file:
            file_handler = logging.FileHandler(file)
            # Use CleanFormatter to strip ANSI sequences from structlog console renderer output
            file_handler.setFormatter(CleanFormatter("%(message)s"))
            file_handler.addFilter(ApplicationFilter())
            file_handler.addFilter(RedactionFilter())
            handlers.append(file_handler)

        # Attach our handlers without removing existing ones (so pytest caplog keeps working)
        root_logger.setLevel(numeric_level)
        for h in handlers:
            root_logger.addHandler(h)
        # Track handlers we installed to avoid duplicates on re-setup
        cls._installed_handlers.extend(handlers)
        # Track file handler for lightweight reconfiguration
        cls._file_handler = next(
            (h for h in handlers if isinstance(h, logging.FileHandler)), None
        )

        # Add global filters so captured logs (e.g., pytest caplog) are also redacted
        # Avoid duplicate filters if setup() is called multiple times
        has_redaction = any(isinstance(f, RedactionFilter) for f in root_logger.filters)
        if not has_redaction:
            root_logger.addFilter(RedactionFilter())
        has_app_filter = any(
            isinstance(f, ApplicationFilter) for f in root_logger.filters
        )
        if not has_app_filter:
            root_logger.addFilter(ApplicationFilter())

        # Optional suppressions
        if suppress_qdrant_warnings:
            logging.getLogger("qdrant_client").addFilter(QdrantVersionFilter())

        # Quiet noisy libs a bit
        for name in ("httpx", "httpcore", "urllib3", "gensim"):
            logging.getLogger(name).setLevel(logging.WARNING)

        # structlog processors – render to a final string directly
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt=ts_fmt),
                redact_processor,
                final_renderer,
            ],
            wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
            logger_factory=LoggerFactory(),
            cache_logger_on_first_use=False,
        )

        cls._initialized = True
        cls._current_config = current_tuple

    @classmethod
    def get_logger(cls, name: str | None = None) -> structlog.BoundLogger:
        if not cls._initialized:
            cls.setup()
        return structlog.get_logger(name)

    @classmethod
    def reconfigure(cls, *, file: str | None = None, level: str | None = None) -> None:
        """Lightweight reconfiguration for file destination and optionally log level.

        Replaces only the file handler while keeping console handlers and
        structlog processors intact. Optionally updates the log level.

        Args:
            file: Path to log file (optional)
            level: New log level (optional, e.g., "DEBUG", "INFO")
        """
        root_logger = logging.getLogger()

        # Update log level if provided
        if level is not None:
            try:
                numeric_level = getattr(logging, level.upper())
                root_logger.setLevel(numeric_level)

                # Update structlog wrapper to use new level
                if cls._current_config is not None:
                    (
                        _,
                        fmt,
                        _,
                        clean_output,
                        suppress_qdrant_warnings,
                        disable_console,
                    ) = cls._current_config

                    # Choose timestamp format and final renderer
                    if clean_output and fmt == "console":
                        ts_fmt = "%H:%M:%S"
                        final_renderer = structlog.dev.ConsoleRenderer(colors=True)
                    else:
                        ts_fmt = "iso"
                        final_renderer = (
                            structlog.processors.JSONRenderer()
                            if fmt == "json"
                            else structlog.dev.ConsoleRenderer(colors=True)
                        )

                    # Reconfigure structlog with new level
                    structlog.configure(
                        processors=[
                            structlog.stdlib.filter_by_level,
                            structlog.stdlib.add_logger_name,
                            structlog.stdlib.add_log_level,
                            structlog.processors.TimeStamper(fmt=ts_fmt),
                            redact_processor,
                            final_renderer,
                        ],
                        wrapper_class=structlog.make_filtering_bound_logger(
                            numeric_level
                        ),
                        logger_factory=LoggerFactory(),
                        cache_logger_on_first_use=False,
                    )
            except AttributeError:
                raise ValueError(f"Invalid log level: {level}") from None

        # Remove existing file handler if present
        if cls._file_handler is not None:
            try:
                root_logger.removeHandler(cls._file_handler)
                cls._file_handler.close()
            except Exception:
                pass
            cls._installed_handlers = [
                h for h in cls._installed_handlers if h is not cls._file_handler
            ]
            cls._file_handler = None

        # Add new file handler if requested
        if file:
            fh = logging.FileHandler(file)
            fh.setFormatter(CleanFormatter("%(message)s"))
            fh.addFilter(ApplicationFilter())
            fh.addFilter(RedactionFilter())
            root_logger.addHandler(fh)
            cls._installed_handlers.append(fh)
            cls._file_handler = fh

        # Update current config tuple if available
        if cls._current_config is not None:
            (
                old_level,
                fmt,
                _,
                clean_output,
                suppress_qdrant_warnings,
                disable_console,
            ) = cls._current_config
            new_level = level.upper() if level is not None else old_level
            cls._current_config = (
                new_level,
                fmt,
                file,
                clean_output,
                suppress_qdrant_warnings,
                disable_console,
            )
