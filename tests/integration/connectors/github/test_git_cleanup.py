"""
Tests for Git repository cleanup functionality.
"""
import os

import pytest

from qdrant_loader.connectors.git import GitConnector


@pytest.mark.integration
def test_cleanup_behavior(fresh_git_connector, is_github_actions):
    """Test cleanup behavior in different scenarios."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    
    # Test successful cleanup
    temp_dir = None
    with fresh_git_connector as connector:
        temp_dir = connector.temp_dir
        assert os.path.exists(temp_dir), "Temporary directory should exist during execution"
        connector.get_documents()
    assert not os.path.exists(temp_dir), "Temporary directory should be cleaned up after success"
    
    # Test cleanup on error
    try:
        with fresh_git_connector as connector:
            temp_dir = connector.temp_dir
            assert os.path.exists(temp_dir), "Temporary directory should exist during execution"
            raise RuntimeError("Simulated error")
    except RuntimeError:
        pass
    assert not os.path.exists(temp_dir), "Temporary directory should be cleaned up after error"

@pytest.mark.integration
def test_multiple_connector_cleanup(git_config_with_auth, is_github_actions):
    """Test that multiple GitConnector instances clean up properly."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    temp_dirs = []

    # Create multiple connectors
    for _ in range(3):
        with GitConnector(git_config_with_auth) as connector:
            temp_dirs.append(connector.temp_dir)
            assert os.path.exists(connector.temp_dir), "Temporary directory should exist during execution"
            connector.get_documents()

    # After all connectors are closed, all temp directories should be cleaned up
    for temp_dir in temp_dirs:
        assert not os.path.exists(temp_dir), "All temporary directories should be cleaned up" 