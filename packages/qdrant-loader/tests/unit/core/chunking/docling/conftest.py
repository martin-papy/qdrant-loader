"""Shared fixtures for the Docling-native chunking tests.

Real files are converted once per session through *our* conversion engine, then
chunked with a raw docling ``HybridChunker``. The raw chunker is deliberate: the
``StructureProjector`` tests need genuine ``DocChunk`` inputs that do NOT depend on
our own (under-test) ``DoclingChunker.chunk``. All formats here are model-free
(docx/xlsx SimplePipeline), so the suite runs offline.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from qdrant_loader.core.conversion import (
    ConversionConfig,
    ConversionProfile,
    EngineKind,
    build_engine,
)

FIXTURE_DIR = Path(__file__).parents[4] / "fixtures" / "unit" / "chunking"


@pytest.fixture(scope="session")
def _engine():
    return build_engine(
        EngineKind.DOCLING, ConversionConfig.from_profile(ConversionProfile.FAST)
    )


@pytest.fixture(scope="session")
def _raw_chunker():
    """A raw docling HybridChunker for producing real DocChunks in projector tests."""
    import tiktoken
    from docling_core.transforms.chunker import HybridChunker
    from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer

    tokenizer = OpenAITokenizer(
        tokenizer=tiktoken.get_encoding("cl100k_base"), max_tokens=8000
    )
    return HybridChunker(tokenizer=tokenizer, merge_peers=True)


def _convert_or_fail(engine, path: Path):
    """Convert a fixture and fail loudly if the engine did not succeed, so a broken
    conversion surfaces here rather than as an opaque ``NoneType`` access downstream."""
    outcome = engine.convert(path)
    assert outcome.succeeded and outcome.document is not None, (
        f"fixture conversion failed for {path.name}: "
        f"status={outcome.status}, error={outcome.error}"
    )
    return outcome.document


@pytest.fixture(scope="session")
def converted_headers(_engine):
    """The nested-headings docx, as a ConvertedDocument (the chunker's input type)."""
    return _convert_or_fail(_engine, FIXTURE_DIR / "unit_test_headers.docx")


@pytest.fixture(scope="session")
def converted_xlsx(_engine):
    """The table-bearing xlsx, as a ConvertedDocument."""
    return _convert_or_fail(_engine, FIXTURE_DIR / "xlsx_05_table_with_title.xlsx")


@pytest.fixture(scope="session")
def header_doc_chunks(_raw_chunker, converted_headers):
    """Real docling DocChunks from the headings docx (have meta.headings paths)."""
    return list(_raw_chunker.chunk(converted_headers.document))


@pytest.fixture(scope="session")
def xlsx_doc_chunks(_raw_chunker, converted_xlsx):
    """Real docling DocChunks from the xlsx (have TABLE items with prov)."""
    return list(_raw_chunker.chunk(converted_xlsx.document))
