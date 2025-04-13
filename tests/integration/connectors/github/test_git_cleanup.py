"""
Tests for Git repository cleanup functionality.
"""
import os

import pytest

from qdrant_loader.connectors.git import GitConnector


@pytest.mark.integration
def test_cleanup_on_success(git_config_with_auth, is_github_actions):
    """Test that temporary directory is cleaned up after successful execution."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    temp_dir = None
    with GitConnector(git_config_with_auth) as connector:
        temp_dir = connector.temp_dir
        assert os.path.exists(temp_dir), "Temporary directory should exist during execution"
        # Don't assert on document count as it might be empty
        connector.get_documents()

    # After successful execution, directory should be cleaned up
    assert not os.path.exists(temp_dir), "Temporary directory should be cleaned up after success"

@pytest.mark.integration
def test_cleanup_on_error(git_config_with_auth, is_github_actions):
    """Test that temporary directory is cleaned up when an error occurs."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    temp_dir = None
    try:
        with GitConnector(git_config_with_auth) as connector:
            temp_dir = connector.temp_dir
            assert os.path.exists(temp_dir), "Temporary directory should exist during execution"
            raise RuntimeError("Simulated error")
    except RuntimeError:
        pass

    # After error, directory should still be cleaned up
    assert not os.path.exists(temp_dir), "Temporary directory should be cleaned up after error"

@pytest.mark.integration
def test_cleanup_on_init_failure(git_config_with_auth):
    """Test cleanup when initialization fails."""
    # This test should still run as it tests error handling
    with pytest.raises((RuntimeError, ValueError)):
        with GitConnector(git_config_with_auth) as connector:
            raise RuntimeError("Simulated initialization error")

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
            # Don't assert on document count as it might be empty
            connector.get_documents()

    # After all connectors are closed, all temp directories should be cleaned up
    for temp_dir in temp_dirs:
        assert not os.path.exists(temp_dir), "All temporary directories should be cleaned up" 