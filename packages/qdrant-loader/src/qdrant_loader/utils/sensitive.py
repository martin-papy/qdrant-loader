"""Utilities for redacting sensitive values from logs and error messages."""

from __future__ import annotations

import re

_SENSITIVE_FIELD_RE = re.compile(
    r"(?i)(?P<quote>['\"]?)(?P<key>[a-z0-9_\-]*(?:token|api[_-]?key|password|secret|access[_-]?key|private[_-]?key|authorization)[a-z0-9_\-]*)(?P=quote)\s*(?P<sep>[:=])\s*(?P<value>'[^']*'|\"[^\"]*\"|[^,\s}\]]+)"
)
_INPUT_VALUE_PREFIX_RE = re.compile(r"input_value\s*=\s*", re.IGNORECASE)
_BEARER_RE = re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)([^\s,]+)")
_AUTHORIZATION_RE = re.compile(
    r"(?i)(authorization\s*[:=]\s*)(?:(?:bearer|basic|token)\s+)?[^\s,]+"
)
_OPENAI_KEY_RE = re.compile(r"\bsk-[a-zA-Z0-9\-_]{12,}\b")


def _consume_input_value(text: str, start: int) -> int:
    """Consume the value that follows input_value=, handling nested structures."""
    if start >= len(text):
        return start

    ch = text[start]

    # Quoted scalar
    if ch in "'\"":
        quote = ch
        i = start + 1
        escaped = False
        while i < len(text):
            cur = text[i]
            if escaped:
                escaped = False
            elif cur == "\\":
                escaped = True
            elif cur == quote:
                return i + 1
            i += 1
        return i

    # Nested dict/list structures
    if ch in "[{":
        stack = ["]" if ch == "[" else "}"]
        i = start + 1
        in_quote = ""
        escaped = False

        while i < len(text) and stack:
            cur = text[i]

            if in_quote:
                if escaped:
                    escaped = False
                elif cur == "\\":
                    escaped = True
                elif cur == in_quote:
                    in_quote = ""
            else:
                if cur in "'\"":
                    in_quote = cur
                elif cur in "[{":
                    stack.append("]" if cur == "[" else "}")
                elif cur in "]}" and stack and cur == stack[-1]:
                    stack.pop()
            i += 1

        return i

    # Unquoted scalar value: consume until delimiter
    i = start
    while i < len(text) and text[i] not in ",\n":
        i += 1
    return i


def _mask_input_value_segments(text: str, mask: str) -> str:
    """Mask all input_value=... occurrences, including deeply nested values."""
    if "input_value" not in text.lower():
        return text

    out_parts: list[str] = []
    cursor = 0

    for match in _INPUT_VALUE_PREFIX_RE.finditer(text):
        value_start = match.end()
        value_end = _consume_input_value(text, value_start)

        out_parts.append(text[cursor : match.start()])
        out_parts.append(f"{match.group(0)}{mask}")
        cursor = value_end

    out_parts.append(text[cursor:])
    return "".join(out_parts)


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

    redacted = _mask_input_value_segments(text, mask)
    redacted = _AUTHORIZATION_RE.sub(rf"\1{mask}", redacted)
    redacted = _SENSITIVE_FIELD_RE.sub(_replace_field, redacted)
    redacted = _BEARER_RE.sub(rf"\1{mask}", redacted)
    redacted = _OPENAI_KEY_RE.sub(mask, redacted)
    return redacted


def sanitize_exception_message(error: Exception | str, mask: str = "**") -> str:
    """Convert an exception or message string to a safe, redacted message."""
    redacted = redact_sensitive_data(str(error), mask=mask)

    if redacted and redacted.strip():
        return redacted

    if isinstance(error, Exception):
        return error.__class__.__name__

    return "<redacted>"
