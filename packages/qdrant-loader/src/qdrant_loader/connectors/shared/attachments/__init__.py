"""Shared attachment helpers for connectors."""

from .metadata import normalize_attachment_metadata
from .reader import AttachmentReader

__all__ = [
    "AttachmentReader",
    "normalize_attachment_metadata",
]
