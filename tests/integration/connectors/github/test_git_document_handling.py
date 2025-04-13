"""
Tests for Git document handling functionality.
"""
import pytest

@pytest.mark.integration
def test_document_metadata(session_git_connector):
    """Test that documents have correct metadata."""
    with session_git_connector as connector:
        docs = connector.get_documents()
        assert len(docs) > 0
        
        for doc in docs:
            assert doc.metadata is not None
            assert "file_name" in doc.metadata
            assert "repository_url" in doc.metadata
            assert "last_commit_date" in doc.metadata
            assert "last_commit_author" in doc.metadata
            assert doc.metadata["repository_url"].startswith("https://github.com/")
            assert doc.metadata["file_name"].endswith((".md", ".java")) 