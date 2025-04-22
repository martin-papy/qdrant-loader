"""
Tests for the Git connector implementation.
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from git import Repo
from pydantic import HttpUrl

from qdrant_loader.connectors.git.connector import GitConnector
from qdrant_loader.connectors.git.config import GitRepoConfig
from qdrant_loader.connectors.git.operations import GitOperations
from qdrant_loader.core.document import Document
from qdrant_loader.config.types import SourceType


class TestGitConnector:
    """Test suite for the GitConnector class."""

    @pytest.fixture
    def mock_config(self):
        """Fixture providing a mock Git repository configuration."""
        return GitRepoConfig(
            base_url=HttpUrl("https://github.com/test/repo.git"),
            branch="main",
            file_types=["*.md", "*.txt"],
            token="test_token",
            source="test_source",
            source_type=SourceType.GIT,
            temp_dir=None,
        )

    @pytest.fixture
    def mock_repo(self):
        """Fixture creating a mock Git repository."""
        repo = MagicMock(spec=Repo)
        repo.git.status.return_value = "On branch main"
        return repo

    @pytest.fixture
    def mock_git_ops(self, mock_repo):
        """Fixture creating mock Git operations."""
        git_ops = MagicMock(spec=GitOperations)
        git_ops.repo = mock_repo
        git_ops.clone.return_value = None
        git_ops.list_files.return_value = ["/tmp/test.md", "/tmp/test.txt"]
        git_ops.get_file_content.return_value = "Test content"
        git_ops.get_last_commit_date.return_value = datetime.now()
        git_ops.get_first_commit_date.return_value = datetime.now()
        return git_ops

    @pytest.mark.asyncio
    async def test_repository_cloning(self, mock_config, mock_git_ops):
        """Test repository cloning functionality."""
        with patch(
            "qdrant_loader.connectors.git.connector.GitOperations", return_value=mock_git_ops
        ):
            # Create a GitConnector instance
            connector = GitConnector(mock_config)

            # Use the connector as a context manager
            async with connector:
                # Verify the repository was cloned
                assert connector.temp_dir is not None
                assert os.path.exists(connector.temp_dir)
                assert connector.git_ops.repo is not None

                # Verify repository is valid
                assert connector.git_ops.repo.git.status() is not None

    @pytest.mark.asyncio
    async def test_content_extraction(self, mock_config, mock_git_ops):
        """Test content extraction from repository files."""
        with (
            patch(
                "qdrant_loader.connectors.git.connector.GitOperations", return_value=mock_git_ops
            ),
            patch(
                "qdrant_loader.connectors.git.connector.FileProcessor.should_process_file",
                return_value=True,
            ),
        ):
            connector = GitConnector(mock_config)

            async with connector:
                # Get documents from the repository
                documents = await connector.get_documents()

                # Verify documents were extracted
                assert len(documents) > 0
                assert all(isinstance(doc, Document) for doc in documents)

                # Verify document content and metadata
                for doc in documents:
                    assert doc.content == "Test content"
                    assert doc.metadata is not None
                    assert doc.source_type == SourceType.GIT
                    assert doc.source == mock_config.source
                    assert doc.metadata.get("file_name") in ["test.md", "test.txt"]

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_config):
        """Test error handling in the Git connector."""
        # Test invalid repository URL
        invalid_config = GitRepoConfig(
            base_url=HttpUrl("https://invalid-url.com/nonexistent.git"),
            branch="main",
            file_types=[".md"],
            token="test_token",
            source="test_source",
            source_type=SourceType.GIT,
            temp_dir=None,
        )

        connector = GitConnector(invalid_config)

        # Test cloning failure
        with pytest.raises(RuntimeError):
            async with connector:
                pass

    @pytest.mark.asyncio
    async def test_file_processing(self, mock_config, mock_git_ops):
        """Test file processing and filtering."""
        with (
            patch(
                "qdrant_loader.connectors.git.connector.GitOperations", return_value=mock_git_ops
            ),
            patch(
                "qdrant_loader.connectors.git.connector.FileProcessor.should_process_file",
                return_value=True,
            ),
        ):
            connector = GitConnector(mock_config)

            async with connector:
                # Get documents from the repository
                documents = await connector.get_documents()

                # Verify only configured file types are processed
                processed_files = {doc.metadata.get("file_name", "") for doc in documents}
                assert "test.md" in processed_files
                assert "test.txt" in processed_files
                assert "test.py" not in processed_files
                assert "test.json" not in processed_files
