"""
Tests for Git document handling functionality.
"""

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_document_metadata(session_git_connector):
    """Test that documents have correct metadata."""
    with session_git_connector:
        docs = await session_git_connector.get_documents()
        assert len(docs) > 0

        for doc in docs:
            assert doc.metadata is not None
            assert "file_name" in doc.metadata
            assert "repository_url" in doc.metadata
            assert "last_commit_date" in doc.metadata
            assert "last_commit_author" in doc.metadata
            assert str(doc.metadata["repository_url"]).startswith("https://github.com/")
            assert doc.metadata["file_name"].endswith((".md", ".java"))
