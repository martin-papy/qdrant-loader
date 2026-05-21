from qdrant_loader_core.graph.extractor.confluence import ConfluenceEntityExtractor


def test_confluence_page():
    extractor = ConfluenceEntityExtractor()

    raw = {
        "id": "123",
        "title": "Design Doc",
        "_links": {"webui": "http://conf/page"},
        "history": {
            "createdDate": "2024-01-01T00:00:00Z",
            "createdBy": {"accountId": "u1", "displayName": "Bob"},
        },
        "version": {"when": "2024-01-02T00:00:00Z"},
        "space": {"key": "ENG", "name": "Engineering"},
        "metadata": {"labels": {"results": [{"name": "design"}]}},
    }

    result = extractor.extract(raw)

    assert any(n.label == "Container" for n in result.nodes)
    assert any(e.edge_type == "BELONGS_TO" for e in result.edges)
