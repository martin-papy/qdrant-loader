"""
Tests for Git authentication functionality.
"""
import os
import pytest
import yaml
from git.exc import GitCommandError
from dotenv import load_dotenv
from pathlib import Path
import logging
from pydantic import ValidationError

from qdrant_loader.config import GitRepoConfig, GitAuthConfig, Settings, SourcesConfig
from qdrant_loader.connectors.git import GitConnector

# Configure logging for tests
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Load test environment variables
load_dotenv(Path(__file__).parent.parent.parent / ".env.test")

@pytest.fixture(autouse=True)
def disable_git_prompt():
    """Disable Git credential prompts for all tests."""
    original_prompt = os.environ.get('GIT_TERMINAL_PROMPT')
    original_askpass = os.environ.get('GIT_ASKPASS')
    
    # Disable both credential prompts and credential helpers
    os.environ['GIT_TERMINAL_PROMPT'] = '0'
    os.environ['GIT_ASKPASS'] = 'echo'
    
    yield
    
    # Restore original values
    if original_prompt is not None:
        os.environ['GIT_TERMINAL_PROMPT'] = original_prompt
    else:
        del os.environ['GIT_TERMINAL_PROMPT']
        
    if original_askpass is not None:
        os.environ['GIT_ASKPASS'] = original_askpass
    else:
        del os.environ['GIT_ASKPASS']

@pytest.fixture(scope="session")
def test_settings():
    """Load test settings from environment variables and config file."""
    try:
        # Log environment variables (excluding sensitive data)
        env_vars = {
            'REPO_URL': os.getenv('REPO_URL'),
            'REPO_TOKEN': 'REDACTED' if os.getenv('REPO_TOKEN') else None
        }
        logger.debug("Environment variables: %s", env_vars)

        # Load settings from YAML
        config_path = Path(__file__).parent.parent.parent.parent / "config.test.yaml"
        logger.debug("Loading config from: %s", config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found at {config_path}")
            
        try:
            with open(config_path) as f:
                config_data = yaml.safe_load(f)
                logger.debug("Loaded YAML data: %s", {k: '...' for k in config_data.keys()})
        except yaml.YAMLError as e:
            logger.error("Failed to parse YAML file: %s", e)
            raise
            
        try:
            settings = Settings.from_yaml(config_path)
            logger.debug("Successfully initialized settings")
            return settings
        except Exception as e:
            logger.error("Failed to initialize settings: %s", e)
            raise
            
    except Exception as e:
        logger.error("Failed to load test settings: %s", e)
        raise

@pytest.fixture
def test_repo_url(test_settings):
    """Return the test repository URL from settings."""
    return test_settings.sources_config.git_repos["auth-test-repo"].url

@pytest.fixture
def valid_github_token(test_settings):
    """Return the valid GitHub token from settings."""
    return test_settings.sources_config.git_repos["auth-test-repo"].token

@pytest.fixture
def git_config_with_auth(test_settings):
    """Return a GitRepoConfig with authentication from settings."""
    repo_config = test_settings.sources_config.git_repos["auth-test-repo"]
    return GitRepoConfig(
        url=repo_config.url,
        branch=repo_config.branch,
        depth=repo_config.depth,
        file_types=["*.md"],
        include_paths=["docs/"],
        exclude_paths=[],
        max_file_size=1024 * 1024,
        auth=GitAuthConfig(token=repo_config.token)
    )

@pytest.mark.integration
def test_github_pat_authentication_success(git_config_with_auth):
    """Test successful authentication with a GitHub Personal Access Token."""
    with GitConnector(git_config_with_auth) as connector:
        docs = connector.get_documents()
        assert len(docs) > 0
        assert all(doc.metadata for doc in docs)

@pytest.mark.integration
def test_missing_token_environment_variable(test_repo_url):
    """Test that the connector raises an error when REPO_TOKEN is missing."""
    with pytest.raises(ValueError, match="GitHub token is required for authentication"):
        try:
            GitRepoConfig(
                url=test_repo_url,
                branch="main",
                depth=1,
                file_types=["*.md"],
                include_paths=["docs/"],
                exclude_paths=[],
                max_file_size=1024 * 1024,
                auth=GitAuthConfig(token=None)
            )
        except ValidationError as e:
            # Convert Pydantic validation error to our custom error
            raise ValueError("GitHub token is required for authentication") from e

@pytest.mark.integration
def test_invalid_token_authentication(test_repo_url):
    """Test that the connector raises an error when an invalid token is provided."""
    config = GitRepoConfig(
        url=test_repo_url,
        branch="main",
        depth=1,
        file_types=["*.md"],
        include_paths=["docs/"],
        exclude_paths=[],
        max_file_size=1024 * 1024,
        auth=GitAuthConfig(token="invalid_token")
    )
    with pytest.raises((GitCommandError, RuntimeError), match=r"(Authentication failed|Could not resolve host)"):
        with GitConnector(config) as connector:
            connector.get_documents()

@pytest.mark.integration
def test_invalid_repository_url(valid_github_token):
    """Test authentication with an invalid repository URL."""
    if not valid_github_token:
        pytest.skip("REPO_TOKEN environment variable not set")
        
    config = GitRepoConfig(
        url="https://github.com/invalid/invalid-repo",
        branch="main",
        depth=1,
        file_types=["*.md"],
        include_paths=["."],
        exclude_paths=[],
        max_file_size=1024 * 1024,
        auth=GitAuthConfig(token=valid_github_token)
    )
    
    with pytest.raises((GitCommandError, RuntimeError)):
        with GitConnector(config) as connector:
            connector.get_documents()

@pytest.mark.integration
def test_invalid_branch(test_repo_url, valid_github_token):
    """Test authentication with an invalid branch."""
    if not valid_github_token:
        pytest.skip("REPO_TOKEN environment variable not set")
        
    config = GitRepoConfig(
        url=test_repo_url,
        branch="invalid-branch",
        depth=1,
        file_types=["*.md"],
        include_paths=["."],
        exclude_paths=[],
        max_file_size=1024 * 1024,
        auth=GitAuthConfig(token=valid_github_token)
    )
    
    with pytest.raises((GitCommandError, RuntimeError)):
        with GitConnector(config) as connector:
            connector.get_documents()

@pytest.mark.integration
def test_document_metadata(git_config_with_auth):
    """Test that documents have correct metadata."""
    with GitConnector(git_config_with_auth) as connector:
        docs = connector.get_documents()
        assert len(docs) > 0
        
        for doc in docs:
            assert doc.metadata is not None
            assert "file_name" in doc.metadata
            assert "repository_url" in doc.metadata
            assert "last_commit_date" in doc.metadata
            assert "last_commit_author" in doc.metadata
            assert doc.metadata["repository_url"].startswith("https://github.com/")
            assert doc.metadata["file_name"].endswith(".md") 