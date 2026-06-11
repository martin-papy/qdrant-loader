from __future__ import annotations

import pytest
from qdrant_loader.core.document import Document
from qdrant_loader_core.graph.extractor.publicdocs import PublicDocsEntityExtractor


@pytest.mark.asyncio
async def test_public_webpage():
    extractor = PublicDocsEntityExtractor()

    metadata = {
        "url": "https://example.com/page",
        "tags": ["ai", "ml"],
        "links": ["https://example.com/other"],
        "attachments": [
            {"id": "att1", "filename": "doc.pdf", "mime_type": "application/pdf"}
        ],
    }

    doc = Document(
        title="Example Page",
        content_type="page",
        content="Example webpage content",
        source_type="publicdocs",
        source="https://example.com/page",
        url="https://example.com/page",
        metadata=metadata,
    )

    result = await extractor.extract(doc)

    assert any(n.label == "Document" for n in result.nodes)
    assert any(n.label == "Label" for n in result.nodes)
    assert any(n.label == "Container" for n in result.nodes), "Container node missing"
    assert any(n.label == "Attachment" for n in result.nodes), "Attachment node missing"
    assert any(e.edge_type == "HAS_LABEL" for e in result.edges)
    assert any(e.edge_type == "LINKS_TO" for e in result.edges), "LINKS_TO edge missing"
    assert any(
        e.edge_type == "HAS_ATTACHMENT" for e in result.edges
    ), "HAS_ATTACHMENT edge missing"
