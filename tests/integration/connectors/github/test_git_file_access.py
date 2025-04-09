"""
Tests for Git file access functionality.
"""
import os
import pytest
from pathlib import Path
from qdrant_loader.config import GitRepoConfig, GitAuthConfig
from qdrant_loader.connectors.git import GitConnector

@pytest.fixture(scope="function")
def git_config(test_settings):
    """Create a GitRepoConfig instance."""
    # Get the first Git repo config from the test settings
    repo_key = next(iter(test_settings.sources_config.git_repos.keys()))
    base_config = test_settings.sources_config.git_repos[repo_key]
    
    return GitRepoConfig(
        url=base_config.url,
        branch=base_config.branch,
        depth=base_config.depth,
        file_types=["*.md"],
        include_paths=["/", "src/", "docs/"],
        exclude_paths=["tests/"],
        max_file_size=1024 * 1024,
        auth=base_config.auth
    )

@pytest.fixture(scope="function")
def git_connector(git_config):
    """Create a GitConnector instance."""
    return GitConnector(git_config)

@pytest.mark.integration
def test_file_type_filtering(git_connector, is_github_actions):
    """Test file type filtering."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with git_connector:
        docs = git_connector.get_documents()
        md_files = [doc for doc in docs if doc.metadata['file_name'].endswith('.md')]
        assert len(md_files) > 0, "Should find markdown files"

@pytest.mark.integration
def test_file_size_limit(git_connector, is_github_actions):
    """Test file size limit enforcement."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with git_connector:
        docs = git_connector.get_documents()
        for doc in docs:
            assert len(doc.content) <= git_connector.config.max_file_size, "File size should be within limit"

@pytest.mark.integration
def test_file_metadata_extraction(git_connector, is_github_actions):
    """Test file metadata extraction."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with git_connector:
        docs = git_connector.get_documents()
        for doc in docs:
            assert 'file_name' in doc.metadata
            assert 'last_commit_date' in doc.metadata
            assert 'last_commit_author' in doc.metadata

@pytest.mark.integration
def test_file_content_extraction(git_connector, is_github_actions):
    """Test file content extraction."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with git_connector:
        docs = git_connector.get_documents()
        for doc in docs:
            assert doc.content, "File content should not be empty" 