from qdrant_loader_core.graph.extractor.jira import JiraEntityExtractor


def test_jira_basic():
    extractor = JiraEntityExtractor()

    raw = {
        "key": "ABC-1",
        "self": "http://jira/ABC-1",
        "fields": {
            "summary": "Fix login bug",
            "created": "2024-01-01T00:00:00Z",
            "updated": "2024-01-02T00:00:00Z",
            "status": {"name": "Open"},
            "priority": {"name": "High"},
            "issuetype": {"name": "Bug"},
            "project": {"key": "ABC", "name": "Project ABC"},
            "assignee": {"emailAddress": "john@company.com", "displayName": "John"},
            "labels": ["backend"],
        },
    }

    result = extractor.extract(raw)

    assert len(result.nodes) >= 3
    assert len(result.edges) >= 2

    # Check document exists
    doc_ids = [n.id for n in result.nodes]
    assert "jira:ABC-1" in doc_ids
