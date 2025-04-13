"""
Tests for Git file type handling.
"""
import pytest

@pytest.mark.integration
def test_md_file_handling(git_connector, is_github_actions):
    """Test handling of markdown files."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with git_connector:
        docs = git_connector.get_documents()
        md_files = [doc for doc in docs if doc.metadata['file_name'].endswith('.md')]
        assert len(md_files) > 0, "Should find markdown files"

@pytest.mark.integration
def test_java_file_handling(git_connector, is_github_actions):
    """Test handling of java files."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with git_connector:
        docs = git_connector.get_documents()
        txt_files = [doc for doc in docs if doc.metadata['file_name'].endswith('.java')]
        assert len(txt_files) > 0, "Should find Java files"

@pytest.mark.integration
def test_file_type_exclusion(git_connector, is_github_actions):
    """Test exclusion of non-specified file types."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with git_connector:
        docs = git_connector.get_documents()
        other_files = [doc for doc in docs if not doc.metadata['file_name'].endswith(('.md', '.java'))]
        assert len(other_files) == 0, "Should not process non-specified file types"

@pytest.mark.integration
def test_file_type_validation(git_connector, is_github_actions):
    """Test validation of file types."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with git_connector:
        docs = git_connector.get_documents()
        for doc in docs:
            assert doc.metadata['file_name'].endswith(('.md', '.java')), "Only .md and .java files should be processed" 