"""Tests for the Git metadata extractor implementation."""

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import git
import pytest
from pydantic import HttpUrl

from qdrant_loader.connectors.git.config import GitRepoConfig
from qdrant_loader.connectors.git.metadata_extractor import GitMetadataExtractor
from qdrant_loader.config.types import SourceType


class TestGitMetadataExtractor:
    """Test suite for the GitMetadataExtractor class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def base_config(self, temp_dir):
        """Create a base configuration for testing."""
        return GitRepoConfig(
            base_url=HttpUrl("https://github.com/test/repo.git"),
            branch="main",
            file_types=["*.md", "*.txt"],
            token="test_token",
            source="test_source",
            source_type=SourceType.GIT,
            temp_dir=temp_dir,
        )

    @pytest.fixture
    def mock_repo(self):
        """Create a mock Git repository."""
        repo = MagicMock(spec=git.Repo)

        # Mock config reader
        config_reader = MagicMock()
        config_reader.has_section.side_effect = lambda section: section in ["github", "core"]
        config_reader.get_value.side_effect = lambda section, key, default: {
            ("github", "description"): "Test repository",
            ("github", "language"): "Python",
            ("core", "description"): "Core description",
        }.get((section, key), default)
        repo.config_reader.return_value = config_reader

        # Mock commit
        commit = MagicMock()
        commit.committed_datetime = datetime(2024, 1, 1, tzinfo=timezone.utc)
        commit.author.name = "Test Author"
        commit.message = "Test commit message\n"

        # Mock head
        repo.head.commit = commit
        repo.iter_commits.return_value = [commit]
        repo.working_dir = "/tmp/test_repo"
        repo.bare = False

        return repo

    def test_extract_file_metadata(self, base_config):
        """Test extraction of file metadata."""
        extractor = GitMetadataExtractor(base_config)

        # Test markdown file with various features
        content = """# Test Document
        
This is a test document with some features:

```python
def test():
    pass
```

![Test Image](test.png)

[Test Link](https://example.com)
"""

        metadata = extractor._extract_file_metadata("/tmp/test.md", content)

        assert metadata["file_type"] == ".md"
        assert metadata["file_name"] == "test.md"
        assert metadata["file_directory"].replace("//", "/") == "/tmp"  # Normalize path
        assert metadata["file_encoding"] == "utf-8"
        assert metadata["line_count"] == 12
        assert metadata["word_count"] > 0
        assert metadata["file_size"] > 0
        assert metadata["has_code_blocks"] is True
        assert metadata["has_images"] is True
        assert metadata["has_links"] is True

    def test_extract_repo_metadata(self, base_config, mock_repo):
        """Test extraction of repository metadata."""
        with patch("git.Repo", return_value=mock_repo):
            extractor = GitMetadataExtractor(base_config)
            metadata = extractor._extract_repo_metadata("/tmp/test.md")

            assert metadata["repository_name"] == "repo"
            assert metadata["repository_owner"] == "test"
            assert metadata["repository_url"] == "https://github.com/test/repo.git"
            assert metadata["repository_description"] == "Test repository"
            assert metadata["repository_language"] == "Python"

    def test_extract_git_metadata(self, base_config, mock_repo):
        """Test extraction of Git metadata."""
        with patch("git.Repo", return_value=mock_repo):
            extractor = GitMetadataExtractor(base_config)
            metadata = extractor._extract_git_metadata("/tmp/test.md")

            assert metadata["last_commit_date"] == "2024-01-01T00:00:00+00:00"
            assert metadata["last_commit_author"] == "Test Author"
            assert metadata["last_commit_message"] == "Test commit message"

    def test_extract_all_metadata(self, base_config, mock_repo):
        """Test extraction of all metadata."""
        content = """# Test Document

This is a test document.

```python
print("Hello")
```
"""
        with patch("git.Repo", return_value=mock_repo):
            extractor = GitMetadataExtractor(base_config)
            metadata = extractor.extract_all_metadata("/tmp/test.md", content)

            # Verify file metadata
            assert metadata["file_type"] == ".md"
            assert metadata["file_name"] == "test.md"
            assert metadata["has_code_blocks"] is True

            # Verify repo metadata
            assert metadata["repository_name"] == "repo"
            assert metadata["repository_description"] == "Test repository"

            # Verify git metadata
            assert metadata["last_commit_author"] == "Test Author"
            assert metadata["last_commit_message"] == "Test commit message"

    def test_error_handling(self, base_config):
        """Test error handling in metadata extraction."""
        extractor = GitMetadataExtractor(base_config)

        # Test with invalid repository
        with patch("git.Repo", side_effect=git.InvalidGitRepositoryError):
            metadata = extractor._extract_git_metadata("/tmp/test.md")
            assert metadata == {}

        # Test with non-existent file
        metadata = extractor._extract_file_metadata("/nonexistent/test.md", "")
        assert metadata["file_type"] == ".md"
        assert metadata["file_name"] == "test.md"
        assert metadata["file_directory"].replace("//", "/") == "/nonexistent"

    def test_detect_encoding(self, base_config):
        """Test encoding detection."""
        extractor = GitMetadataExtractor(base_config)

        # Test UTF-8 content
        assert extractor._detect_encoding("Hello, world! 🌍") == "utf-8"

        # Test UTF-8 content without special characters
        # Note: Python strings are always UTF-8, so we can't really test ASCII encoding
        assert extractor._detect_encoding("Hello") == "utf-8"

    def test_markdown_features(self, base_config):
        """Test detection of Markdown features."""
        extractor = GitMetadataExtractor(base_config)

        content = """# Heading 1
## Heading 2

```python
def test():
    pass
```

![Image](test.png)

[Link](https://example.com)
"""

        assert extractor._has_code_blocks(content) is True
        assert extractor._has_images(content) is True
        assert extractor._has_links(content) is True
        assert extractor._get_heading_levels(content) == [1, 2]
