"""Utilities for redacting sensitive values from logs and error messages."""

from __future__ import annotations

import re

_SENSITIVE_FIELD_RE = re.compile(
    r"(?i)(?P<quote>['\"]?)(?P<key>[a-z0-9_\-]*(?:token|api[_-]?key|password|secret|access[_-]?key|private[_-]?key)[a-z0-9_\-]*)(?P=quote)\s*(?P<sep>[:=])\s*(?P<value>'[^']*'|\"[^\"]*\"|[^,\s}\]]+)"
)
_INPUT_VALUE_RE = re.compile(r"input_value\s*=\s*([^,\n]+)", re.IGNORECASE)
_BEARER_RE = re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)([^\s,]+)")
_OPENAI_KEY_RE = re.compile(r"\bsk-[a-zA-Z0-9\-_]{12,}\b")


def redact_sensitive_data(text: str, mask: str = "**") -> str:
    """Redact common secret patterns in free-form text.

    Args:
        text: Input text that may contain secrets.
        mask: Replacement value for sensitive data.

    Returns:
        Redacted text safe for logs and terminal output.
    """
    if not text:
        return text

    def _replace_field(match: re.Match[str]) -> str:
        quote = match.group("quote") or ""
        key = match.group("key")
        sep = match.group("sep")
        return f"{quote}{key}{quote}{sep}{mask}"

    redacted = _SENSITIVE_FIELD_RE.sub(_replace_field, text)
    redacted = _INPUT_VALUE_RE.sub(f"input_value={mask}", redacted)
    redacted = _BEARER_RE.sub(rf"\1{mask}", redacted)
    redacted = _OPENAI_KEY_RE.sub(mask, redacted)
    return redacted


def sanitize_exception_message(error: Exception, mask: str = "**") -> str:
    """Convert an exception to a safe, redacted message string."""
    return redact_sensitive_data(str(error), mask=mask)
