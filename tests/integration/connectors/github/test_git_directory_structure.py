"""
Tests for Git directory structure handling.
"""
import os
import pytest
from pathlib import Path
from qdrant_loader.config import GitRepoConfig, GitAuthConfig
from qdrant_loader.connectors.git import GitConnector

@pytest.fixture(scope="function")
def git_config_with_directories(test_settings):
    """Create a GitRepoConfig instance with directory settings."""
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
def git_connector(git_config_with_directories):
    """Create a GitConnector instance."""
    return GitConnector(git_config_with_directories)

@pytest.mark.integration
def test_nested_directory_handling(git_connector):
    """Test handling of nested directories."""
    with git_connector:
        # Get all documents
        docs = list(git_connector.get_documents())
        
        # Verify we have documents from nested directories
        assert any(doc.metadata["file_directory"].startswith("src/") for doc in docs)
        assert any(doc.metadata["file_directory"].startswith("docs/") for doc in docs)

@pytest.mark.integration
def test_root_directory_handling(git_connector):
    """Test handling of root directory files."""
    with git_connector:
        # Get all documents
        docs = list(git_connector.get_documents())
        
        # Verify we have documents from root directory
        assert any(doc.metadata["file_directory"] == "" for doc in docs)

@pytest.mark.integration
def test_directory_exclusion(git_connector):
    """Test directory exclusion functionality."""
    with git_connector:
        # Get all documents
        docs = list(git_connector.get_documents())
        
        # Verify no documents from excluded directories
        assert not any(doc.metadata["file_directory"].startswith("tests/") for doc in docs)

@pytest.mark.integration
def test_directory_inclusion(git_connector):
    """Test directory inclusion functionality."""
    with git_connector:
        # Get all documents
        docs = list(git_connector.get_documents())
        
        # Verify we have documents from included directories
        assert any(doc.metadata["file_directory"].startswith("src/") for doc in docs)
        assert any(doc.metadata["file_directory"].startswith("docs/") for doc in docs)

@pytest.mark.integration
def test_directory_pattern_matching(git_connector):
    """Test directory pattern matching."""
    with git_connector:
        # Get all documents
        docs = list(git_connector.get_documents())
        
        # Verify pattern matching works
        assert any(doc.metadata["file_directory"].startswith("src/") for doc in docs)
        assert any(doc.metadata["file_directory"].startswith("docs/") for doc in docs)
        assert not any(doc.metadata["file_directory"].startswith("tests/") for doc in docs) 