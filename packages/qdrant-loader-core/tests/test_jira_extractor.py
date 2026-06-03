from qdrant_loader.core.document import Document
from qdrant_loader_core.graph.extractor.jira import JiraEntityExtractor


def test_jira_basic():
    extractor = JiraEntityExtractor()

    metadata = {
        "project_key": "ABC",
        "status": "Open",
        "priority": "High",
        "issue_type": "Bug",
        "reporter": {
            "email_address": "reporter@company.com",
            "display_name": "Reporter",
        },
        "assignee": {
            "email_address": "john@company.com",
            "display_name": "John",
        },
        "labels": ["backend"],
        "description": "Related confluence page: http://confluence.example.com/display/ABC/Page",
    }

    doc = Document(
        title="Fix login bug",
        content_type="issue",
        content="Jira issue content",
        source_type="jira",
        source="ABC-1",
        url="http://jira/ABC-1",
        metadata=metadata,
    )

    result = extractor.extract(doc)

    assert any(n.label == "Document" for n in result.nodes)
    assert any(n.label == "Container" for n in result.nodes)
    assert any(n.label == "Person" for n in result.nodes)
    assert any(n.edge_type == "BELONGS_TO" for n in result.edges)
    assert any(e.edge_type == "AUTHORED_BY" for e in result.edges)
    assert any(e.edge_type == "LINKS_TO" for e in result.edges)
