"""Tests for the Git file processor implementation."""

import os
import tempfile
from pathlib import Path
from typing import List, Optional

import pytest
from pydantic import HttpUrl

from qdrant_loader.connectors.git.config import GitRepoConfig
from qdrant_loader.connectors.git.file_processor import FileProcessor
from qdrant_loader.config.types import SourceType


class TestFileProcessor:
    """Test suite for the FileProcessor class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def create_test_file(self, temp_dir):
        """Helper fixture to create test files."""

        def _create_file(
            relative_path: str, content: str = "test content", size: Optional[int] = None
        ):
            file_path = os.path.join(temp_dir, relative_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            if size is not None:
                # Create a file of exact size
                with open(file_path, "wb") as f:
                    f.write(b"0" * size)
            else:
                with open(file_path, "w") as f:
                    f.write(content)

            return file_path

        return _create_file

    @pytest.fixture
    def base_config(self):
        """Create a base configuration for testing."""
        return GitRepoConfig(
            base_url=HttpUrl("https://github.com/test/repo.git"),
            branch="main",
            file_types=["*.md", "*.txt"],
            token="test_token",
            source="test_source",
            source_type=SourceType.GIT,
            temp_dir=None,
            include_paths=[],
            exclude_paths=[],
            max_file_size=1024 * 1024,  # 1MB
        )

    def test_file_type_filtering(self, temp_dir, create_test_file, base_config):
        """Test filtering files based on file types."""
        # Create test files
        md_file = create_test_file("test.md")
        txt_file = create_test_file("test.txt")
        py_file = create_test_file("test.py")
        hidden_file = create_test_file(".hidden.md")

        processor = FileProcessor(base_config, temp_dir)

        # Test file type matching
        assert processor.should_process_file(md_file) is True
        assert processor.should_process_file(txt_file) is True
        assert processor.should_process_file(py_file) is False
        assert processor.should_process_file(hidden_file) is False

    def test_include_paths(self, temp_dir, create_test_file, base_config):
        """Test include paths filtering."""
        # Create test files in different directories
        root_file = create_test_file("root.md")
        docs_file = create_test_file("docs/test.md")
        nested_file = create_test_file("docs/api/test.md")

        # Test root directory only
        config = base_config.model_copy(update={"include_paths": ["/"]})
        processor = FileProcessor(config, temp_dir)
        assert processor.should_process_file(root_file) is True
        assert processor.should_process_file(docs_file) is False
        assert processor.should_process_file(nested_file) is False

        # Test specific directory (includes subdirectories)
        config = base_config.model_copy(update={"include_paths": ["docs/"]})
        processor = FileProcessor(config, temp_dir)
        assert processor.should_process_file(root_file) is False
        assert processor.should_process_file(docs_file) is True
        assert processor.should_process_file(nested_file) is True  # Subdirectories are included

        # Test recursive directory (explicit)
        config = base_config.model_copy(update={"include_paths": ["docs/**/*"]})
        processor = FileProcessor(config, temp_dir)
        assert processor.should_process_file(root_file) is False
        assert processor.should_process_file(docs_file) is True
        assert processor.should_process_file(nested_file) is True

    def test_exclude_paths(self, temp_dir, create_test_file, base_config):
        """Test exclude paths filtering."""
        # Create test files
        root_file = create_test_file("test.md")
        test_file = create_test_file("tests/test.md")
        vendor_file = create_test_file("vendor/lib.md")

        # Test excluding specific directories
        config = base_config.model_copy(update={"exclude_paths": ["tests/", "vendor/"]})
        processor = FileProcessor(config, temp_dir)
        assert processor.should_process_file(root_file) is True
        assert processor.should_process_file(test_file) is False
        assert processor.should_process_file(vendor_file) is False

        # Test excluding with wildcards
        config = base_config.model_copy(update={"exclude_paths": ["**/test.md"]})
        processor = FileProcessor(config, temp_dir)
        assert processor.should_process_file(test_file) is False
        assert processor.should_process_file(vendor_file) is True

    def test_file_size_limit(self, temp_dir, create_test_file, base_config):
        """Test file size filtering."""
        # Create files of different sizes
        small_file = create_test_file("small.md", size=100)  # 100 bytes
        large_file = create_test_file("large.md", size=2 * 1024 * 1024)  # 2MB

        config = base_config.model_copy(update={"max_file_size": 1024 * 1024})  # 1MB limit
        processor = FileProcessor(config, temp_dir)

        assert processor.should_process_file(small_file) is True
        assert processor.should_process_file(large_file) is False

    def test_error_handling(self, temp_dir, base_config):
        """Test error handling for invalid files."""
        processor = FileProcessor(base_config, temp_dir)

        # Test non-existent file
        assert processor.should_process_file("/nonexistent/file.md") is False

        # Test unreadable file (if possible to create one)
        test_file = os.path.join(temp_dir, "unreadable.md")
        with open(test_file, "w") as f:
            f.write("test")
        os.chmod(test_file, 0o000)  # Remove all permissions

        assert processor.should_process_file(test_file) is False

        # Cleanup
        os.chmod(test_file, 0o666)  # Restore permissions for cleanup
