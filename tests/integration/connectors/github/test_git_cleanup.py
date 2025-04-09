"""
Tests for Git repository cleanup functionality.
"""
import os
import pytest
import yaml
import tempfile
from pathlib import Path
import time
from qdrant_loader.config import GitRepoConfig, GitAuthConfig
from qdrant_loader.connectors.git import GitConnector

@pytest.fixture
def test_repo_url(test_settings):
    """Return a test repository URL from config.test.yaml."""
    # Get the auth-test-repo URL from the correct path in config
    auth_test_repo_url = test_settings.sources_config.git_repos['auth-test-repo'].url
    
    # Verify the URL is valid
    if not auth_test_repo_url.startswith(("http://", "https://")):
        pytest.fail("Invalid repository URL in config.test.yaml")
    
    return auth_test_repo_url

@pytest.fixture
def test_repo_config(test_repo_url):
    """Create a test GitRepoConfig."""
    return GitRepoConfig(
        url=test_repo_url,
        branch="main",
        depth=1,
        file_types=["*.md"],
        include_paths=["src"],
        exclude_paths=["tests"],
        max_file_size=1024 * 1024,  # 1MB
        auth=None  # No authentication needed for local repo
    )

@pytest.mark.integration
def test_cleanup_on_success(test_repo_config, is_github_actions):
    """Test that temporary directory is cleaned up after successful execution."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    temp_dir = None
    with GitConnector(test_repo_config) as connector:
        temp_dir = connector.temp_dir
        assert os.path.exists(temp_dir), "Temporary directory should exist during execution"
        # Don't assert on document count as it might be empty
        connector.get_documents()

    # After successful execution, directory should be cleaned up
    assert not os.path.exists(temp_dir), "Temporary directory should be cleaned up after success"

@pytest.mark.integration
def test_cleanup_on_error(test_repo_config, is_github_actions):
    """Test that temporary directory is cleaned up when an error occurs."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    temp_dir = None
    try:
        with GitConnector(test_repo_config) as connector:
            temp_dir = connector.temp_dir
            assert os.path.exists(temp_dir), "Temporary directory should exist during execution"
            raise RuntimeError("Simulated error")
    except RuntimeError:
        pass

    # After error, directory should still be cleaned up
    assert not os.path.exists(temp_dir), "Temporary directory should be cleaned up after error"

@pytest.mark.integration
def test_cleanup_on_init_failure(test_repo_config):
    """Test cleanup when initialization fails."""
    # This test should still run as it tests error handling
    with pytest.raises((RuntimeError, ValueError)):
        with GitConnector(test_repo_config) as connector:
            raise RuntimeError("Simulated initialization error")

@pytest.mark.integration
def test_multiple_connector_cleanup(test_repo_config, is_github_actions):
    """Test that multiple GitConnector instances clean up properly."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    temp_dirs = []

    # Create multiple connectors
    for _ in range(3):
        with GitConnector(test_repo_config) as connector:
            temp_dirs.append(connector.temp_dir)
            assert os.path.exists(connector.temp_dir), "Temporary directory should exist during execution"
            # Don't assert on document count as it might be empty
            connector.get_documents()

    # After all connectors are closed, all temp directories should be cleaned up
    for temp_dir in temp_dirs:
        assert not os.path.exists(temp_dir), "All temporary directories should be cleaned up" 