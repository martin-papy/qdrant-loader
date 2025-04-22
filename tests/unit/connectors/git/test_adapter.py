"""Tests for the GitPythonAdapter implementation."""

import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import git
import pytest
from pydantic import HttpUrl

from qdrant_loader.connectors.git.adapter import GitPythonAdapter
from qdrant_loader.connectors.git.config import GitRepoConfig
from qdrant_loader.config.types import SourceType


class TestGitPythonAdapter:
    """Test suite for the GitPythonAdapter class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def mock_repo(self):
        """Create a mock Git repository."""
        repo = MagicMock(spec=git.Repo)
        repo.working_dir = "/tmp/test_repo"
        repo.bare = False
        return repo

    @pytest.fixture
    def adapter(self, mock_repo):
        """Create a GitPythonAdapter instance with a mock repository."""
        return GitPythonAdapter(repo=mock_repo)

    def test_initialization(self):
        """Test adapter initialization."""
        # Test initialization without repo
        adapter = GitPythonAdapter()
        assert adapter.repo is None

        # Test initialization with repo
        mock_repo = MagicMock(spec=git.Repo)
        adapter = GitPythonAdapter(repo=mock_repo)
        assert adapter.repo == mock_repo

    def test_clone_success(self, adapter, temp_dir):
        """Test successful repository cloning."""
        url = "https://github.com/test/repo.git"
        branch = "main"
        depth = 1

        with patch("git.Repo.clone_from") as mock_clone:
            adapter.clone(url, temp_dir, branch, depth)
            mock_clone.assert_called_once()
            assert adapter.repo is not None

    def test_clone_retry(self, adapter, temp_dir):
        """Test repository cloning with retries."""
        url = "https://github.com/test/repo.git"
        branch = "main"
        depth = 1

        mock_repo = MagicMock()
        with patch(
            "git.Repo.clone_from", side_effect=[Exception("Failed"), Exception("Failed"), mock_repo]
        ):
            adapter.clone(url, temp_dir, branch, depth)
            assert adapter.repo == mock_repo

    def test_clone_failure(self, adapter, temp_dir):
        """Test repository cloning failure after max retries."""
        url = "https://github.com/test/repo.git"
        branch = "main"
        depth = 1

        with patch(
            "git.Repo.clone_from",
            side_effect=Exception("Failed to clone repository after 3 attempts"),
        ):
            with pytest.raises(Exception) as exc_info:
                adapter.clone(url, temp_dir, branch, depth)
            assert "Failed to clone repository after 3 attempts" in str(exc_info.value)

    def test_get_file_content(self, adapter, mock_repo):
        """Test getting file content."""
        file_path = "test.md"
        expected_content = "Test content"

        mock_repo.git.show.return_value = expected_content
        content = adapter.get_file_content(file_path)
        assert content == expected_content
        mock_repo.git.show.assert_called_once_with(f"HEAD:{file_path}")

    def test_get_file_content_no_repo(self):
        """Test getting file content when repository is not initialized."""
        adapter = GitPythonAdapter()
        with pytest.raises(ValueError, match="Repository not initialized"):
            adapter.get_file_content("test.md")

    def test_get_last_commit_date(self, adapter, mock_repo):
        """Test getting last commit date."""
        file_path = "test.md"
        commit_date = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Mock the repository and commit
        mock_commit = MagicMock()
        mock_commit.committed_datetime = commit_date
        mock_repo.iter_commits.return_value = [mock_commit]

        with patch("git.Repo") as mock_repo_class:
            mock_repo_class.return_value = mock_repo
            result = adapter.get_last_commit_date(file_path)
            assert result == commit_date

    def test_get_last_commit_date_no_commits(self, adapter, mock_repo):
        """Test getting last commit date when no commits exist."""
        file_path = "test.md"

        with patch("git.Repo") as mock_repo_class:
            mock_repo_class.return_value = mock_repo
            mock_repo.iter_commits.return_value = []
            result = adapter.get_last_commit_date(file_path)
            assert result is None

    def test_list_files(self, adapter, mock_repo):
        """Test listing files in repository."""
        expected_files = ["file1.md", "file2.txt"]
        mock_repo.git.ls_tree.return_value = "\n".join(expected_files)

        files = adapter.list_files()
        assert files == expected_files
        mock_repo.git.ls_tree.assert_called_once_with("-r", "--name-only", "HEAD", ".")

    def test_list_files_no_repo(self):
        """Test listing files when repository is not initialized."""
        adapter = GitPythonAdapter()
        with pytest.raises(ValueError, match="Repository not initialized"):
            adapter.list_files()

    def test_list_files_empty(self, adapter, mock_repo):
        """Test listing files when repository is empty."""
        mock_repo.git.ls_tree.return_value = ""
        files = adapter.list_files()
        assert files == []

    def test_list_files_specific_path(self, adapter, mock_repo):
        """Test listing files from a specific path."""
        path = "docs"
        expected_files = ["docs/file1.md", "docs/file2.txt"]
        mock_repo.git.ls_tree.return_value = "\n".join(expected_files)

        files = adapter.list_files(path)
        assert files == expected_files
        mock_repo.git.ls_tree.assert_called_once_with("-r", "--name-only", "HEAD", path)
