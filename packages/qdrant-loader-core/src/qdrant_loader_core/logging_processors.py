"""Logging processors and formatters for structlog."""

from __future__ import annotations

import logging
import re
from typing import Any


class CleanFormatter(logging.Formatter):
    """Formatter that removes ANSI color codes for clean file output."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        try:
            ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
            return ansi_escape.sub("", message)
        except Exception:
            return message


def redact_processor(
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
