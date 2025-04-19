"""
Tests for the Git integration.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest
from git import Repo
from pydantic import HttpUrl

from qdrant_loader.config import (
    GitRepoConfig,
    get_settings,
    initialize_config,
)
from qdrant_loader.connectors.git import GitConnector
from qdrant_loader.core.document import Document


@pytest.fixture(scope="session")
def test_settings():
    """Load test settings from environment variables and config file."""
    # Load sources config from YAML
    config_path = Path(__file__).parent.parent.parent.parent / "config.test.yaml"
    # Initialize global settings
    initialize_config(config_path)
    # Return the initialized settings
    return get_settings()


@pytest.fixture(scope="function")
def git_config(test_settings):
    """Create a GitRepoConfig instance with test settings."""
    # Get the first Git repo config from the test settings
    repo_key = next(iter(test_settings.sources_config.git.keys()))
    return test_settings.sources_config.git[repo_key]


@pytest.fixture(scope="function")
def git_connector(git_config):
    """Create a GitConnector instance for testing."""
    connector = GitConnector(git_config)
    yield connector
    # Cleanup temporary directory
    if connector.temp_dir and os.path.exists(connector.temp_dir):
        import shutil

        shutil.rmtree(connector.temp_dir)


@pytest.mark.integration
def test_git_connector_init(git_config):
    """Test GitConnector initialization with real settings."""
    connector = GitConnector(git_config)
    assert connector.config == git_config
    assert connector.temp_dir is None
    assert connector.logger is not None
    assert connector.metadata_extractor is not None


@pytest.mark.integration
def test_git_connector_context_manager(git_config):
    """Test GitConnector context manager with real repository."""
    with GitConnector(git_config) as connector:
        assert connector.temp_dir is not None
        assert os.path.exists(connector.temp_dir)
        assert os.path.exists(os.path.join(connector.temp_dir, ".git"))


@pytest.mark.integration
def test_git_connector_cleanup(git_config):
    """Test GitConnector cleanup with real repository."""
    temp_dir = None
    with GitConnector(git_config) as connector:
        temp_dir = connector.temp_dir
        assert temp_dir is not None
        assert os.path.exists(temp_dir)

    # Verify cleanup
    assert not os.path.exists(temp_dir)


@pytest.mark.integration
def test_should_process_file(git_connector):
    """Test GitConnector _should_process_file method with real files."""
    with git_connector:
        # Create test files in the temporary directory
        test_files = [
            (".git/config", False),  # Should be excluded
            ("src/main/test.md", True),  # Should be included
            ("src/test/test.md", False),  # Should be excluded
            ("docs/README.md", True),  # Should be included
            ("large_file.md", False),  # Should be excluded if too large
        ]

        for file_path, should_process in test_files:
            full_path = os.path.join(git_connector.temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write("test content")

            # Set file size for large_file.md
            if file_path == "large_file.md":
                with open(full_path, "w") as f:
                    f.write("x" * (git_connector.config.max_file_size + 1))

            assert git_connector._should_process_file(full_path) == should_process


@pytest.mark.integration
def test_process_file(git_connector):
    """Test GitConnector _process_file method with real files."""
    with git_connector:
        # Create a test file
        file_path = os.path.join(git_connector.temp_dir, "src", "main", "test.md")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        content = "# Test Document\n\n## Section 1\nTest content\n\n## Section 2\nMore test content"
        with open(file_path, "w") as f:
            f.write(content)

        # Initialize git repo and commit the file
        repo = Repo(git_connector.temp_dir)
        repo.index.add([os.path.relpath(file_path, git_connector.temp_dir)])
        repo.index.commit("Add test file")

        # Process the file
        doc = git_connector._process_file(file_path)
        assert isinstance(doc, Document)
        assert doc.content == content
        assert "repository_url" in doc.metadata
        assert doc.source == str(doc.metadata["repository_url"])
        assert doc.source_type == "git"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling(git_config, state_manager):
    """Test error handling with invalid repository URL."""
    invalid_config = GitRepoConfig(
        source_type="git",
        source="test",
        base_url=HttpUrl("https://github.com/invalid/repo.git"),
        branch=git_config.branch,
        depth=git_config.depth,
        file_types=git_config.file_types,
        include_paths=git_config.include_paths,
        exclude_paths=git_config.exclude_paths,
        max_file_size=git_config.max_file_size,
        token="None",
        temp_dir="/tmp/test",
    )

    with pytest.raises(RuntimeError):
        with GitConnector(invalid_config) as connector:
            await connector.get_documents()


@pytest.mark.integration
async def test_git_connector_get_documents(git_config):
    """Test document retrieval with state management."""
    with GitConnector(git_config) as connector:
        # Mock last ingestion time
        last_ingestion = Mock()
        last_ingestion.last_updated = datetime.now(timezone.utc)

        # Get documents
        documents = await connector.get_documents()
        # Verify documents were processed
        assert isinstance(documents, list)
        for doc in documents:
            assert doc.source_type == "git"
            assert doc.source == str(git_config.base_url)
            assert "path" in doc.metadata
            assert "last_modified" in doc.metadata
            assert "content_hash" in doc.metadata


@pytest.mark.integration
async def test_invalid_config(git_config, mock_state_manager):
    """Test GitConnector with invalid configuration."""
    invalid_config = GitRepoConfig(
        source_type="git",
        source="test",
        base_url=HttpUrl("https://invalid-url.com"),
        branch="main",
        depth=1,
        file_types=["*.md", "*.txt"],
        include_paths=["docs/**/*"],
        exclude_paths=["tests/**/*"],
        max_file_size=1024 * 1024,  # 1MB
        token="test-token",
        temp_dir="/tmp/test",
    )

    with pytest.raises(Exception):
        with GitConnector(invalid_config) as connector:
            await connector.get_documents()
