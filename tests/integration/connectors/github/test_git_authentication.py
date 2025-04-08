"""
Tests for Git authentication functionality.
"""
import os
import pytest
import yaml
from git.exc import GitCommandError
from dotenv import load_dotenv
from pathlib import Path

from qdrant_loader.config import GitRepoConfig, GitAuthConfig
from qdrant_loader.connectors.git import GitConnector

# Load test environment variables
load_dotenv(Path(__file__).parent.parent.parent / ".env.test")

@pytest.fixture
def test_repo_url():
    """Return a test repository URL from config.test.yaml."""
    config_path = Path(__file__).parent.parent.parent.parent / "config.test.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Get the auth-test-repo URL
    auth_test_repo_url = config['git_repos']['auth-test-repo']['url']
    
    # Verify the URL is valid
    if not auth_test_repo_url.startswith(("http://", "https://")):
        pytest.fail("Invalid repository URL in config.test.yaml")
    
    return auth_test_repo_url

@pytest.fixture
def valid_github_token():
    """Return a valid GitHub token from environment."""
    return os.getenv("AUTH_TEST_REPO_TOKEN")

@pytest.fixture
def git_config_with_auth(test_repo_url, valid_github_token):
    """Create a GitRepoConfig with GitHub authentication."""
    return GitRepoConfig(
        url=test_repo_url,
        branch="main",
        depth=1,
        file_types=["*.md"],
        include_paths=["src"],
        exclude_paths=["tests"],
        max_file_size=1024 * 1024,  # 1MB
        auth=GitAuthConfig(
            type="github",
            token_env="AUTH_TEST_REPO_TOKEN"
        )
    )

@pytest.mark.integration
def test_github_pat_authentication_success(git_config_with_auth, valid_github_token):
    """Test successful GitHub PAT authentication."""
    if not valid_github_token:
        pytest.skip("AUTH_TEST_REPO_TOKEN environment variable not set")
    
    with GitConnector(git_config_with_auth) as connector:
        # If we can get documents, authentication was successful
        docs = connector.get_documents()
        assert docs is not None 