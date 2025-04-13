"""
Tests for Git file access functionality.
"""
import pytest

@pytest.mark.integration
def test_file_type_filtering(session_git_connector, is_github_actions):
    """Test file type filtering."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with session_git_connector:
        docs = session_git_connector.get_documents()
        md_files = [doc for doc in docs if doc.metadata['file_name'].endswith('.md')]
        assert len(md_files) > 0, "Should find markdown files"

@pytest.mark.integration
def test_file_size_limit(session_git_connector, is_github_actions):
    """Test file size limit enforcement."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with session_git_connector:
        docs = session_git_connector.get_documents()
        for doc in docs:
            assert len(doc.content) <= session_git_connector.config.max_file_size, "File size should be within limit"

@pytest.mark.integration
def test_file_metadata_extraction(session_git_connector, is_github_actions):
    """Test file metadata extraction."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with session_git_connector:
        docs = session_git_connector.get_documents()
        for doc in docs:
            assert 'file_name' in doc.metadata
            assert 'last_commit_date' in doc.metadata
            assert 'last_commit_author' in doc.metadata

@pytest.mark.integration
def test_file_content_extraction(session_git_connector, is_github_actions):
    """Test file content extraction."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with session_git_connector:
        docs = session_git_connector.get_documents()
        for doc in docs:
            assert doc.content, "File content should not be empty" 