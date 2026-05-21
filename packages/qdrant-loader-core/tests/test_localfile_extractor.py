from qdrant_loader_core.graph.extractor.localfile import LocalFileEntityExtractor


def test_localfile_basic():
    extractor = LocalFileEntityExtractor()

    raw = {
        "path": "/home/user/file.txt",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
    }

    result = extractor.extract(raw)

    assert any(n.label == "Document" for n in result.nodes)
    assert any(n.label == "Container" for n in result.nodes)
    assert any(e.edge_type == "BELONGS_TO" for e in result.edges)
