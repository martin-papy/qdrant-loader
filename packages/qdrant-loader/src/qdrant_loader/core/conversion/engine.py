"""The engine seam: the abstraction the rest of the codebase depends on.

A :class:`ConversionEngine` is anything that turns a source into a
:class:`~.outcome.ConversionOutcome`. :func:`build_engine` constructs the docling
engine behind this Protocol (the markitdown path is handled directly by
:class:`~.service.ConversionService`, which routes to ``FileConverter`` rather than
through an engine adapter). Keeping callers on the Protocol (not on docling) is what
makes the swap reversible.

Once docling is the only engine, this Protocol can be collapsed — a
one-implementation interface is just ceremony.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from docling.datamodel.base_models import DocumentStream

    from .config import ConversionConfig
    from .outcome import ConversionOutcome


# Anything docling's DocumentConverter.convert accepts. PEP 695 alias: the body is
# evaluated lazily, so the docling type need not exist at runtime.
type ConversionSource = Path | str | DocumentStream


@runtime_checkable
class ConversionEngine(Protocol):
    """Source -> ConversionOutcome. The codebase depends on this, not on docling."""

    def convert(self, source: ConversionSource) -> ConversionOutcome: ...


class EngineKind(StrEnum):
    MARKITDOWN = "markitdown"
    DOCLING = "docling"


def build_engine(kind: EngineKind, config: ConversionConfig) -> ConversionEngine:
    """Composition root: construct the docling conversion engine.

    Only ``EngineKind.DOCLING`` is built through an engine adapter; the markitdown
    path is routed directly to ``FileConverter`` by ``ConversionService`` and never
    reaches here. docling is imported lazily so the markitdown path never requires it
    (and the import also breaks the engine <-> docling_engine cycle).
    """
    if kind is EngineKind.DOCLING:
        from .docling_engine import DoclingConverter

        return DoclingConverter(config)
    raise ValueError(f"build_engine only constructs the docling engine, got: {kind!r}")
