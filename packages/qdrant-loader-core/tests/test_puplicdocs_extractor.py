from qdrant_loader.core.document import Document
from qdrant_loader_core.graph.extractor.publicdocs import PublicDocsEntityExtractor


def test_public_webpage():
    extractor = PublicDocsEntityExtractor()

    metadata = {
        "url": "https://example.com/page",
        "tags": ["ai", "ml"],
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

    result = extractor.extract(doc)

    assert any(n.label == "Document" for n in result.nodes)
    assert any(n.label == "Label" for n in result.nodes)
    assert any(e.edge_type == "HAS_LABEL" for e in result.edges)
