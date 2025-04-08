"""
Tests for Git repository cleanup functionality.
"""
import os
import pytest
import yaml
import tempfile
from pathlib import Path
from dotenv import load_dotenv
import time
from tests.utils import is_github_actions

from qdrant_loader.config import GitRepoConfig, GitAuthConfig
from qdrant_loader.connectors.git import GitConnector

# Load test environment variables
load_dotenv(Path(__file__).parent.parent.parent / ".env.test")

# Skip all tests in this file if running in GitHub Actions
pytestmark = pytest.mark.skipif(
    is_github_actions(),
    reason="Git repository tests are skipped in GitHub Actions"
)

@pytest.fixture
def test_repo_url():
    """Return a test repository URL from config.test.yaml."""
    config_path = Path(__file__).parent.parent.parent.parent / "config.test.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Get the auth-test-repo URL from the correct path in config
    auth_test_repo_url = config['sources']['git_repos']['auth-test-repo']['url']
    
    # Verify the URL is valid
    if not auth_test_repo_url.startswith(("http://", "https://")):
        pytest.fail("Invalid repository URL in config.test.yaml")
    
    return auth_test_repo_url

@pytest.fixture
def test_repo_config(test_repo_url):
    """Create a test GitRepoConfig."""
    return GitRepoConfig(
        url=str(Path("./tests/fixtures/test-repo").absolute()),  # Use local test repo
        branch="main",
        depth=1,
        file_types=["*.md"],
        include_paths=["src"],
        exclude_paths=["tests"],
        max_file_size=1024 * 1024,  # 1MB
        auth=None  # No authentication needed for local repo
    )

def test_cleanup_on_success(test_repo_config):
    """Test that temporary directory is cleaned up after successful execution."""
    temp_dir = None
    with GitConnector(test_repo_config) as connector:
        temp_dir = connector.temp_dir
        assert os.path.exists(temp_dir), "Temporary directory should exist during execution"
        
    # After exiting context manager, directory should be cleaned up
    assert not os.path.exists(temp_dir), "Temporary directory should be cleaned up after execution"

def test_cleanup_on_error(test_repo_config):
    """Test that temporary directory is cleaned up when an error occurs."""
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

def test_cleanup_on_init_failure(test_repo_config):
    """Test that temporary directory is cleaned up if initialization fails."""
    # Create an invalid config that will cause initialization to fail
    invalid_config = GitRepoConfig(
        url="https://invalid.host/user/repo.git",  # Valid format but invalid host
        branch="main",
        depth=1,
        file_types=["*.md"],
        include_paths=["src"],
        exclude_paths=["tests"],
        max_file_size=1024 * 1024,
        auth=GitAuthConfig(
            token="invalid_token"  # Invalid token to ensure authentication fails
        )
    )
    
    temp_dir = None
    try:
        with GitConnector(invalid_config) as connector:
            temp_dir = connector.temp_dir
            pytest.fail("Should have raised an error")
    except:
        # Wait a short time for cleanup to complete
        time.sleep(1)
        
        # Verify the specific temporary directory was cleaned up
        if temp_dir:
            assert not os.path.exists(temp_dir), f"Temporary directory {temp_dir} was not cleaned up"
            git_dir = Path(temp_dir) / '.git'
            assert not git_dir.exists(), f"Git repository at {temp_dir} was not cleaned up"

def test_multiple_connector_cleanup(test_repo_config):
    """Test that multiple GitConnector instances clean up properly."""
    temp_dirs = []
    
    # Create multiple connectors
    for _ in range(3):
        with GitConnector(test_repo_config) as connector:
            temp_dir = connector.temp_dir
            assert os.path.exists(temp_dir), "Temporary directory should exist during execution"
            temp_dirs.append(temp_dir)
            
    # All directories should be cleaned up
    for temp_dir in temp_dirs:
        assert not os.path.exists(temp_dir), f"Temporary directory {temp_dir} should be cleaned up" 