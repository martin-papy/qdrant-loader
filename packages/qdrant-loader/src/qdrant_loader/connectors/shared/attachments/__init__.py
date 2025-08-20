"""Shared attachment helpers for connectors."""

from .reader import AttachmentReader
from .metadata import normalize_attachment_metadata

__all__ = [
    "AttachmentReader",
    "normalize_attachment_metadata",
]


