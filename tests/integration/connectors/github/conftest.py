import asyncio
import logging
import os

import pytest

from qdrant_loader.connectors.git import GitConnector

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def is_github_actions():
    """Check if running in GitHub Actions environment."""
    return os.getenv("GITHUB_ACTIONS") == "true"


@pytest.fixture(autouse=True)
def setup_disable_git_prompt():
    """Disable Git credential prompts for all tests."""
    original_prompt = os.environ.get("GIT_TERMINAL_PROMPT")
    original_askpass = os.environ.get("GIT_ASKPASS")

    # Disable both credential prompts and credential helpers
    os.environ["GIT_TERMINAL_PROMPT"] = "0"
    os.environ["GIT_ASKPASS"] = "echo"

    yield

    # Restore original values
    if original_prompt is not None:
        os.environ["GIT_TERMINAL_PROMPT"] = original_prompt
    else:
        del os.environ["GIT_TERMINAL_PROMPT"]

    if original_askpass is not None:
        os.environ["GIT_ASKPASS"] = original_askpass
    else:
        del os.environ["GIT_ASKPASS"]


@pytest.fixture
def test_repo_url(test_settings):
    """Return the test repository URL from settings."""
    return test_settings.sources_config.git_repos["auth-test-repo"].base_url


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


@pytest.fixture(scope="session")
async def session_documents(session_git_connector):
    """Cache and provide documents for all tests in the session."""
    logger.debug("Fetching documents for the test session")
    with session_git_connector as connector:
        docs = await connector.get_documents()
        return docs


_documents_cache = None


@pytest.fixture(scope="session")
def cached_documents(session_git_connector):
    """Cache the documents for reuse across tests."""
    global _documents_cache
    if _documents_cache is None:
        with session_git_connector as connector:
            _documents_cache = asyncio.run(connector.get_documents())
    return _documents_cache


@pytest.fixture(scope="function")
def fresh_git_connector(git_config_with_auth):
    """Create a GitConnector instance."""
    logger.debug("Creating a fresh GitConnector instance")
    return GitConnector(git_config_with_auth)


@pytest.fixture(scope="function")
async def fresh_documents(fresh_git_connector):
    """Provide fresh documents for each test function."""
    logger.debug("Fetching fresh documents for the test function")
    with fresh_git_connector as connector:
        docs = await connector.get_documents()
        return docs
