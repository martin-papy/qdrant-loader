from __future__ import annotations

from .types import TokenCounter

try:  # Optional dependency
    import tiktoken  # type: ignore
except Exception:  # pragma: no cover - absence is acceptable
    tiktoken = None  # type: ignore


class CharCountTokenCounter(TokenCounter):
    def count(self, text: str) -> int:
        return len(text)


class TiktokenTokenCounter(TokenCounter):
    """Token counter backed by tiktoken; falls back gracefully when unavailable.

    If the requested encoding cannot be loaded or encode fails, falls back to
    a simple character count to avoid runtime errors.
    """

    def __init__(self, encoding_name: str):
        self._encoding_name = encoding_name
        self._encoding = None
        if tiktoken is not None:
            try:
                self._encoding = tiktoken.get_encoding(encoding_name)
            except Exception:
                self._encoding = None

    def count(self, text: str) -> int:
        if self._encoding is not None:
            try:
                return len(self._encoding.encode(text))
            except Exception:
                pass
        return len(text)
