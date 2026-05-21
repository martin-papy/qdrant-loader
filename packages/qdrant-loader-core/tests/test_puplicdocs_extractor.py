from qdrant_loader_core.graph.extractor.publicdocs import PublicDocsEntityExtractor


def test_public_webpage():
    extractor = PublicDocsEntityExtractor()

    raw = {
        "url": "https://example.com/page",
        "title": "Example Page",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
        "tags": ["ai", "ml"],
    }

    result = extractor.extract(raw)

    assert any(n.label == "Document" for n in result.nodes)
    assert any(n.label == "Label" for n in result.nodes)
    assert any(e.edge_type == "HAS_LABEL" for e in result.edges)
