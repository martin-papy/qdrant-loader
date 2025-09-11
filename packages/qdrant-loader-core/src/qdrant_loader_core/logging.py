"""Unified logging configuration for qdrant-loader ecosystem.

Provides:
- structlog setup (console/json/file) with redaction
- stdlib logging bridge with redaction filter
- optional suppression of noisy third-party logs
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

import structlog
from structlog.stdlib import LoggerFactory

try:
    # ExtraAdder is available in structlog >= 20
    from structlog.stdlib import ExtraAdder  # type: ignore
except Exception:  # pragma: no cover - fallback when absent
    ExtraAdder = None  # type: ignore


class QdrantVersionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            return "version check" not in record.getMessage().lower()
        except Exception:
            return True


class ApplicationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Allow all logs by default; app packages may add their own filters
        return True


class RedactionFilter(logging.Filter):
    """Redacts obvious secrets from stdlib log records."""

    # Heuristics for tokens/keys in plain strings
    TOKEN_PATTERNS = [
        re.compile(r"sk-[A-Za-z0-9_\-]{6,}"),
        re.compile(r"tok-[A-Za-z0-9_\-]{6,}"),
        re.compile(
            r"(?i)(api_key|authorization|token|access_token|secret|password)\s*[:=]\s*([^\s]+)"
        ),
        re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]+"),
    ]

    # Keys commonly used for secrets in structlog event dictionaries
    SENSITIVE_KEYS = {
        "api_key",
        "llm_api_key",
        "authorization",
        "Authorization",
        "token",
        "access_token",
        "secret",
        "password",
    }

    def _redact_text(self, text: str) -> str:
        def mask(m: re.Match[str]) -> str:
            s = m.group(0)
            if len(s) <= 8:
                return "***REDACTED***"
            return s[:2] + "***REDACTED***" + s[-2:]

        redacted = text
        for pat in self.TOKEN_PATTERNS:
            redacted = pat.sub(mask, redacted)
        return redacted

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            redaction_detected = False

            # Args may contain secrets; best-effort mask strings and detect changes
            if isinstance(record.args, tuple):
                new_args = []
                for a in record.args:
                    if isinstance(a, str):
                        red_a = self._redact_text(a)
                        if red_a != a:
                            redaction_detected = True
                        new_args.append(red_a)
                    else:
                        new_args.append(a)
                record.args = tuple(new_args)

            # Redact raw message only when it contains no formatting placeholders
            # to avoid interfering with %-style or {}-style formatting
            if isinstance(record.msg, str):
                try:
                    has_placeholders = ("%" in record.msg) or ("{" in record.msg)
                except Exception:
                    has_placeholders = True
                if not has_placeholders:
                    red_msg = self._redact_text(record.msg)
                    if red_msg != record.msg:
                        record.msg = red_msg
                        redaction_detected = True

            # If structlog extras contain sensitive keys, mark as redacted
            try:
                if any(
                    (k in self.SENSITIVE_KEYS and bool(record.__dict__.get(k)))
                    for k in record.__dict__.keys()
                ):
                    redaction_detected = True
            except Exception:
                pass

            # Ensure a visible redaction marker appears in the captured message
            if redaction_detected:
                try:
                    if (
                        isinstance(record.msg, str)
                        and "***REDACTED***" not in record.msg
                    ):
                        # Append a marker in a way that won't interfere with %-formatting
                        record.msg = f"{record.msg} ***REDACTED***"
                except Exception:
                    pass
        except Exception:
            pass
        return True


class CleanFormatter(logging.Formatter):
    """Formatter that removes ANSI color codes for clean file output."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        try:
            ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
            return ansi_escape.sub("", message)
        except Exception:
            return message


def _redact_processor(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Structlog processor to redact sensitive fields in event_dict."""
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

    def mask(value: str) -> str:
        try:
            if not isinstance(value, str) or not value:
                return "***REDACTED***"
            if len(value) <= 8:
                return "***REDACTED***"
            return value[:2] + "***REDACTED***" + value[-2:]
        except Exception:
            return "***REDACTED***"

    def deep_redact(obj: Any) -> Any:
        try:
            if isinstance(obj, dict):
                return {
                    k: (
                        mask(v)
                        if k in sensitive_keys and isinstance(v, str)
                        else deep_redact(v)
                    )
                    for k, v in obj.items()
                }
            if isinstance(obj, list):
                return [deep_redact(i) for i in obj]
            return obj
        except Exception:
            return obj

    return deep_redact(event_dict)


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
                _redact_processor,
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
    def reconfigure(cls, *, file: str | None = None) -> None:
        """Lightweight reconfiguration for file destination.

        Replaces only the file handler while keeping console handlers and
        structlog processors intact.
        """
        root_logger = logging.getLogger()
        # Remove existing file handler if present
        if cls._file_handler is not None:
            try:
                root_logger.removeHandler(cls._file_handler)
                cls._file_handler.close()
            except Exception:
                pass
            cls._installed_handlers = [h for h in cls._installed_handlers if h is not cls._file_handler]
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
            level, fmt, _, clean_output, suppress_qdrant_warnings, disable_console = cls._current_config
            cls._current_config = (level, fmt, file, clean_output, suppress_qdrant_warnings, disable_console)
