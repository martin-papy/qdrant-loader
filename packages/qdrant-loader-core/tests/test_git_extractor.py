from qdrant_loader_core.graph.extractor.git import GitEntityExtractor


def test_git_commit():
    extractor = GitEntityExtractor()

    raw = {
        "sha": "abc123",
        "html_url": "http://git/commit/abc123",
        "commit": {
            "message": "Initial commit",
            "author": {
                "name": "Alice",
                "email": "alice@company.com",
                "date": "2024-01-01T00:00:00Z",
            },
        },
        "repository": {"full_name": "org/repo", "name": "repo"},
    }

    result = extractor.extract(raw)

    assert any(n.label == "Document" for n in result.nodes)
    assert any(n.label == "Person" for n in result.nodes)
    assert any(e.edge_type == "AUTHORED_BY" for e in result.edges)
