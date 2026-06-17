"""End-to-end: a real file flows connector -> docling conversion -> structure-aware
chunking when the conversion engine is configured to docling.

This exercises the production path (the LocalFile connector actually using
ConversionService), not the engine in isolation. It runs offline: docx uses docling's
model-free SimplePipeline and the chunk tokenizer is tiktoken cl100k_base.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pydantic import AnyUrl
from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.localfile import LocalFileConnector
from qdrant_loader.connectors.localfile.config import LocalFileConfig
from qdrant_loader.core.chunking.chunking_service import ChunkingService
from qdrant_loader.core.document import Document
from qdrant_loader.core.file_conversion.conversion_config import FileConversionConfig

FIXTURE = Path(__file__).parents[1] / "fixtures" / "unit" / "conversion" / "lorem_ipsum.docx"


async def _convert_via_localfile(source_dir: Path) -> Document:
    """Run the LocalFile connector over ``source_dir`` with the docling engine."""
    config = LocalFileConfig(
        base_url=AnyUrl(f"file://{source_dir}"),
        source="docling-e2e",
        source_type=SourceType.LOCALFILE,
        file_types=[],
        include_paths=["*"],
        exclude_paths=[],
        enable_file_conversion=True,
    )
    connector = LocalFileConnector(config)
    connector.set_file_conversion_config(FileConversionConfig(engine="docling"))
    async with connector:
        documents = await connector.get_documents()
    return next(doc for doc in documents if doc.title.endswith(".docx"))


@pytest.mark.asyncio
async def test_localfile_connector_converts_with_docling_engine(tmp_path):
    shutil.copy(FIXTURE, tmp_path / "lorem_ipsum.docx")

    doc = await _convert_via_localfile(tmp_path)

    assert doc.metadata["conversion_method"] == "docling"
    assert doc.metadata["conversion_failed"] is False
    assert doc.metadata["original_file_type"] == "docx"
    # The structured artifact must ride the Document to the chunker.
    assert doc.converted_document is not None
    assert doc.content.strip()  # markdown export, for display/state/back-compat


@pytest.mark.asyncio
async def test_docling_document_chunks_into_structured_chunks(tmp_path, test_settings):
    shutil.copy(FIXTURE, tmp_path / "lorem_ipsum.docx")
    doc = await _convert_via_localfile(tmp_path)

    chunks = ChunkingService(test_settings.global_config, test_settings).chunk_document(
        doc
    )

    assert chunks, "docling chunking produced no chunks"
    for index, chunk in enumerate(chunks):
        assert chunk.content.strip()
        assert chunk.metadata["chunking_strategy"] == "docling"
        assert chunk.metadata["chunk_index"] == index
        structure = chunk.metadata["structure"]
        assert isinstance(structure, dict)
        assert "heading_path" in structure  # engine-neutral provenance block
