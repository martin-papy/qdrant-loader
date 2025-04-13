import os
import pytest
import logging

from qdrant_loader.connectors.git import GitConnector

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def is_github_actions():
    """Check if running in GitHub Actions environment."""
    return os.getenv('GITHUB_ACTIONS') == 'true'

@pytest.fixture(autouse=True)
def setup_disable_git_prompt():
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

@pytest.fixture
def test_repo_url(test_settings):
    """Return the test repository URL from settings."""
    return test_settings.sources_config.git_repos["auth-test-repo"].url

@pytest.fixture
def valid_github_token(test_settings):
    """Return the valid GitHub token from settings."""
    return test_settings.sources_config.git_repos["auth-test-repo"].token

@pytest.fixture(scope="session")
def git_config_with_auth(test_settings):
    """Return a GitRepoConfig with authentication from settings."""
    return test_settings.sources_config.git_repos["auth-test-repo"]

@pytest.fixture(scope="session")
def session_git_connector(git_config_with_auth):
    """Create a GitConnector instance."""
    logger.debug("Creating the GitConnector instance in the test session")
    return GitConnector(git_config_with_auth)

@pytest.fixture(scope="function")
def fresh_git_connector(git_config_with_auth):
    """Create a GitConnector instance."""
    logger.debug("Creating a fresh GitConnector instance")
    return GitConnector(git_config_with_auth)

@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_dirs():
    """Clean up any remaining temporary directories after all tests."""
    yield  # This is where the tests run
    # Cleanup code here will run after all tests are complete
    import shutil
    import tempfile
    temp_dir = tempfile.gettempdir()
    for item in os.listdir(temp_dir):
        if item.startswith("qdrant-loader-"):
            shutil.rmtree(os.path.join(temp_dir, item), ignore_errors=True)