"""Errors the chunking layer raises — loud by design.

The legacy markdown chunker degrades *silently*: a shape mismatch falls through to
a fallback splitter or returns one giant chunk with no signal (doc 03 §2.5, R10).
This layer rejects that — when an invariant the contract depends on breaks, it
raises. These are the cases the chunker refuses to paper over.
"""

from __future__ import annotations


class ChunkingError(Exception):
    """Base class for chunking errors raised by this package."""


class EmptyDocumentError(ChunkingError):
    """The source produced no chunkable content — never emit a fake empty chunk."""


class TokenizerUnavailableError(ChunkingError):
    """The configured tokenizer kind cannot be constructed for chunk sizing."""

    def __init__(self, kind: str, reason: str) -> None:
        super().__init__(f"cannot build {kind!r} tokenizer: {reason}")
        self.kind = kind
        self.reason = reason
