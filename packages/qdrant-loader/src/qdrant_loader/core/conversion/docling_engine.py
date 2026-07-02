"""The docling conversion engine — the one module that touches docling directly.

:class:`DoclingConverter` is a thin facade over a single docling
``DocumentConverter``. It owns construction *once* via ``cached_property`` (a
class-enforced lazy-once, not a lazy-null singleton) and composes the pure
:class:`~.options.DoclingOptionsBuilder` and :class:`~.formats.FormatPolicy` rather
than inlining their logic.

It structurally satisfies :class:`~.engine.ConversionEngine` — no base class, no
registration.
"""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from .config import ConversionConfig
from .formats import FormatPolicy
from .options import DoclingOptionsBuilder
from .outcome import ConversionOutcome

if TYPE_CHECKING:
    from docling.document_converter import DocumentConverter

    from .engine import ConversionSource


class DoclingConverter:
    """Source -> ConversionOutcome via docling."""

    def __init__(self, config: ConversionConfig) -> None:
        self._config = config
        self._options_builder = DoclingOptionsBuilder(config)
        self._format_policy = FormatPolicy(config)

    @cached_property
    def _converter(self) -> DocumentConverter:
        """Construct the docling ``DocumentConverter`` once, then reuse it.

        docling caches pipelines across calls, so one converter handles every
        document. ``compile_torch_models`` lives on a process-global settings
        singleton, so it is set here (the one intentional global mutation), not
        in the pure option builder.
        """
        from docling.datamodel.settings import settings
        from docling.document_converter import DocumentConverter

        settings.inference.compile_torch_models = self._config.compile_models
        return DocumentConverter(
            allowed_formats=self._format_policy.allowed_formats(),
            format_options=self._options_builder.build_format_options(),
        )

    def convert(self, source: ConversionSource) -> ConversionOutcome:
        """Convert a single source into a typed outcome.

        Status, not exceptions, drives control flow: ``raises_on_error=False``
        makes docling return a result carrying its status, which the outcome
        mapper translates into our typed value.
        """
        result = self._converter.convert(
            source,
            raises_on_error=False,
            max_file_size=self._config.max_file_size,
        )
        return ConversionOutcome.from_docling_result(result)
