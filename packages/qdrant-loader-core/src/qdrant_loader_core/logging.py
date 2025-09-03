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
        re.compile(r"(?i)(api_key|authorization|token|access_token|secret|password)\s*[:=]\s*([^\s]+)"),
        re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]+"),
    ]

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
            if isinstance(record.msg, str):
                record.msg = self._redact_text(record.msg)
            # Args may contain secrets; best-effort mask strings
            if isinstance(record.args, tuple):
                record.args = tuple(
                    self._redact_text(a) if isinstance(a, str) else a for a in record.args
                )
        except Exception:
            pass
        return True


def _redact_processor(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
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
                return {k: (mask(v) if k in sensitive_keys and isinstance(v, str) else deep_redact(v)) for k, v in obj.items()}
            if isinstance(obj, list):
                return [deep_redact(i) for i in obj]
            return obj
        except Exception:
            return obj

    return deep_redact(event_dict)


class LoggingConfig:
    """Core logging setup with structlog + stdlib redaction and filters."""

    _initialized = False

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
            disable_console = os.getenv("MCP_DISABLE_CONSOLE_LOGGING", "").lower() == "true"

        try:
            numeric_level = getattr(logging, level.upper())
        except AttributeError:
            raise ValueError(f"Invalid log level: {level}") from None

        # Reset previous config
        logging.getLogger().handlers = []
        structlog.reset_defaults()

        handlers: list[logging.Handler] = []

        if not disable_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter("%(message)s"))
            console_handler.addFilter(ApplicationFilter())
            console_handler.addFilter(RedactionFilter())
            handlers.append(console_handler)

        if file:
            file_handler = logging.FileHandler(file)
            file_handler.setFormatter(logging.Formatter("%(message)s"))
            file_handler.addFilter(ApplicationFilter())
            file_handler.addFilter(RedactionFilter())
            handlers.append(file_handler)

        logging.basicConfig(level=numeric_level, handlers=handlers, format="%(message)s")

        # Optional suppressions
        if suppress_qdrant_warnings:
            logging.getLogger("qdrant_client").addFilter(QdrantVersionFilter())

        # Quiet noisy libs a bit
        for name in ("httpx", "httpcore", "urllib3", "gensim"):
            logging.getLogger(name).setLevel(logging.WARNING)

        # structlog processors
        if clean_output and format == "console":
            processors = [
                structlog.stdlib.filter_by_level,
                structlog.processors.TimeStamper(fmt="%H:%M:%S"),
                _redact_processor,
                structlog.dev.ConsoleRenderer(colors=True),
            ]
        else:
            processors = [
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.UnicodeDecoder(),
                _redact_processor,
            ]
            if format == "json":
                processors.append(structlog.processors.JSONRenderer())
            else:
                processors.append(structlog.dev.ConsoleRenderer(colors=True))

        structlog.configure(
            processors=processors,
            wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=False,
        )

        cls._initialized = True

    @classmethod
    def get_logger(cls, name: str | None = None) -> structlog.BoundLogger:
        if not cls._initialized:
            cls.setup()
        return structlog.get_logger(name)


