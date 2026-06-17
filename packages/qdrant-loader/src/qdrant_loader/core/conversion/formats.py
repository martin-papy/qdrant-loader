"""Conversion eligibility policy, derived from docling's own format tables.

:class:`FormatPolicy` is the single source of truth for "should we convert this?".
It filters docling's ``FormatToMimeType`` table by our enabled-formats list plus a
size cap, instead of duplicating a hand-maintained MIME dict (the A6 anti-pattern:
two sources of truth that drift). Like the option builder, it is a small pure class
holding the injected config and imports docling lazily.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .config import ConversionConfig

if TYPE_CHECKING:
    from docling.datamodel.base_models import InputFormat


class FormatPolicy:
    """Decides which inputs are eligible for conversion under the config."""

    def __init__(self, config: ConversionConfig) -> None:
        self._config = config

    def allowed_formats(self) -> list[InputFormat]:
        """The enabled formats, resolved to docling ``InputFormat`` members."""
        from docling.datamodel.base_models import InputFormat

        formats_by_name = {fmt.value: fmt for fmt in InputFormat}
        return [
            formats_by_name[name]
            for name in self._config.enabled_formats
            if name in formats_by_name
        ]

    def supported_mime_types(self) -> set[str]:
        """Accepted MIME types = docling's table filtered to the enabled formats."""
        from docling.datamodel.base_models import FormatToMimeType

        allowed = set(self.allowed_formats())
        return {
            mime_type
            for fmt, mime_types in FormatToMimeType.items()
            if fmt in allowed
            for mime_type in mime_types
        }

    def is_within_size_limit(self, size_bytes: int) -> bool:
        return size_bytes <= self._config.max_file_size
