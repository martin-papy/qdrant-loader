"""Logging filters for redaction and noise suppression."""

from __future__ import annotations

import logging
import re


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
