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
def test_file_type_filtering(git_connector):
    """Test filtering by file type."""
    with git_connector:
        # Get all documents
        docs = list(git_connector.get_documents())
        
        # Verify all files are markdown
        assert all(doc.metadata["file_name"].endswith(".md") for doc in docs)

@pytest.mark.integration
def test_file_size_limit(git_connector):
    """Test file size limit enforcement."""
    with git_connector:
        # Get all documents
        docs = list(git_connector.get_documents())
        
        # Verify no files exceed the size limit
        assert all(doc.metadata["file_size"] <= 1024 * 1024 for doc in docs)

@pytest.mark.integration
def test_file_metadata_extraction(git_connector):
    """Test file metadata extraction."""
    with git_connector:
        # Get all documents
        docs = list(git_connector.get_documents())
        
        # Verify metadata is present
        for doc in docs:
            assert "file_name" in doc.metadata
            assert "file_directory" in doc.metadata
            assert "file_size" in doc.metadata
            assert "file_type" in doc.metadata
            assert "last_commit_date" in doc.metadata
            assert "last_commit_author" in doc.metadata
            assert "last_commit_message" in doc.metadata
            assert "repository_name" in doc.metadata
            assert "repository_url" in doc.metadata
            assert "branch" in doc.metadata

@pytest.mark.integration
def test_file_content_extraction(git_connector):
    """Test that file content is correctly extracted."""
    with git_connector as repo:
        documents = list(repo.get_documents())
        assert len(documents) > 0
        for doc in documents:
            assert doc.content is not None
            assert isinstance(doc.content, str)
            assert len(doc.content) > 0 