"""
Tests for Git authentication functionality.
"""

import logging

import pytest
import pytest_asyncio
from git.exc import GitCommandError
from pydantic import ValidationError

from qdrant_loader.config import GitRepoConfig
from qdrant_loader.connectors.git import GitConnector

# Configure logging for tests
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


@pytest_asyncio.fixture
async def session_documents(cached_documents):
    # Get the documents from the cached fixture
    docs = cached_documents
    assert len(docs) > 0
    assert all(doc.metadata for doc in docs)


@pytest.mark.integration
def test_missing_token_environment_variable(test_repo_url):
    """Test that the connector raises an error when REPO_TOKEN is missing."""
    with pytest.raises(
        ValueError,
        match="GitHub token is required for authentication. Set to None if you don't need authentication.",
    ):
        try:
            GitRepoConfig(
                url=test_repo_url,
                branch="main",
                depth=1,
                file_types=["*.md"],
                include_paths=["docs/"],
                exclude_paths=[],
                max_file_size=1024 * 1024,
                temp_dir="/tmp/test",
            )  # type: ignore
        except ValidationError as e:
            # Convert Pydantic validation error to our custom error
            raise ValueError(
                "GitHub token is required for authentication. Set to None if you don't need authentication."
            ) from e


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_token_authentication(test_repo_url):
    """Test that the connector raises an error when an invalid token is provided."""
    config = GitRepoConfig(
        url=test_repo_url,
        branch="main",
        depth=1,
        file_types=["*.md"],
        include_paths=["docs/"],
        exclude_paths=[],
        max_file_size=1024 * 1024,
        token="invalid_token",
        temp_dir="/tmp/test",
    )
    with pytest.raises(
        (GitCommandError, RuntimeError), match=r"(Authentication failed|Could not resolve host)"
    ):
        with GitConnector(config) as connector:
            await connector.get_documents()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_repository_url(valid_github_token):
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
        token=valid_github_token,
        temp_dir="/tmp/test",
    )

    with pytest.raises((GitCommandError, RuntimeError)):
        with GitConnector(config) as connector:
            await connector.get_documents()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_branch(test_repo_url, valid_github_token):
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
        token=valid_github_token,
        temp_dir="/tmp/test",
    )

    with pytest.raises((GitCommandError, RuntimeError)):
        with GitConnector(config) as connector:
            await connector.get_documents()
