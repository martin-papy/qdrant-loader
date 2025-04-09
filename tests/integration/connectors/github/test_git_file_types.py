"""
Tests for Git file type handling.
"""
import os
import pytest
from pathlib import Path
from qdrant_loader.config import GitRepoConfig
from qdrant_loader.connectors.git import GitConnector

@pytest.fixture(scope="function")
def git_config_with_file_types(test_settings):
    """Create a GitRepoConfig instance with specific file types."""
    # Get the first Git repo config from the test settings
    repo_key = next(iter(test_settings.sources_config.git_repos.keys()))
    base_config = test_settings.sources_config.git_repos[repo_key]
    
    return GitRepoConfig(
        url=base_config.url,
        branch=base_config.branch,
        file_types=["*.md", "*.txt"],
        include_paths=["/", "src/", "docs/"],
        exclude_paths=["tests/"],
        max_file_size=1024 * 1024,
        auth=base_config.auth
    )

@pytest.fixture(scope="function")
def git_connector_with_file_types(git_config_with_file_types):
    """Create a GitConnector instance for testing file types."""
    return GitConnector(git_config_with_file_types)

@pytest.mark.integration
def test_md_file_handling(git_connector_with_file_types, is_github_actions):
    """Test handling of markdown files."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with git_connector_with_file_types:
        docs = git_connector_with_file_types.get_documents()
        md_files = [doc for doc in docs if doc.metadata['file_name'].endswith('.md')]
        assert len(md_files) > 0, "Should find markdown files"

@pytest.mark.integration
def test_txt_file_handling(git_connector_with_file_types, is_github_actions):
    """Test handling of text files."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with git_connector_with_file_types:
        docs = git_connector_with_file_types.get_documents()
        txt_files = [doc for doc in docs if doc.metadata['file_name'].endswith('.txt')]
        assert len(txt_files) > 0, "Should find text files"

@pytest.mark.integration
def test_file_type_exclusion(git_connector_with_file_types, is_github_actions):
    """Test exclusion of non-specified file types."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with git_connector_with_file_types:
        docs = git_connector_with_file_types.get_documents()
        other_files = [doc for doc in docs if not doc.metadata['file_name'].endswith(('.md', '.txt'))]
        assert len(other_files) == 0, "Should not process non-specified file types"

@pytest.mark.integration
def test_file_type_validation(git_connector_with_file_types, is_github_actions):
    """Test validation of file types."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with git_connector_with_file_types:
        docs = git_connector_with_file_types.get_documents()
        for doc in docs:
            assert doc.metadata['file_name'].endswith(('.md', '.txt')), "Only .md and .txt files should be processed" 