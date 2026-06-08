import pytest
from qdrant_loader.core.document import Document
from qdrant_loader_core.graph.extractor.git import GitEntityExtractor


@pytest.mark.asyncio
async def test_git_commit():
    extractor = GitEntityExtractor()

    metadata = {
        "repository_name": "repo",
        "repository_owner": "org",
        "repository_url": "http://git/org/repo",
        "last_commit_author": "alice@company.com",
        "file_name": "README.md",
    }

    doc = Document(
        title="Initial commit",
        content_type="commit",
        content="Initial commit content",
        source_type="git",
        source="abc123",
        url="http://git/commit/abc123",
        metadata=metadata,
    )

    result = await extractor.extract(doc)

    assert any(n.label == "Document" for n in result.nodes)
    assert any(n.label == "Person" for n in result.nodes)
    assert any(n.label == "Container" for n in result.nodes)
    assert any(e.edge_type == "AUTHORED_BY" for e in result.edges)
    assert any(e.edge_type == "BELONGS_TO" for e in result.edges)
