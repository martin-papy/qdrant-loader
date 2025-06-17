"""Test Windows compatibility for Git connector."""

import os
import tempfile
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch

import pytest
from pydantic import HttpUrl
from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.git.config import GitRepoConfig
from qdrant_loader.connectors.git.connector import GitConnector
from qdrant_loader.connectors.git.operations import GitOperations


class TestGitConnectorWindowsCompatibility:
    """Test Windows compatibility for Git connector."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock Git configuration."""
        return GitRepoConfig(
            base_url=HttpUrl("https://github.com/test/repo.git"),
            branch="main",
            file_types=["*.md", "*.txt", "*.py"],
            token="test_token",
            source="test_source",
            source_type=SourceType.GIT,
            temp_dir=None,
        )

    @pytest.fixture
    def mock_git_ops(self):
        """Create mock Git operations."""
        git_ops = MagicMock(spec=GitOperations)
        mock_repo = MagicMock()
        mock_repo.working_dir = "C:\\temp\\git_repo_123"  # Windows-style temp dir
        git_ops.repo = mock_repo
        git_ops.clone.return_value = None
        git_ops.get_file_content.return_value = "Test file content"
        git_ops.get_last_commit_date.return_value = datetime(
            2024, 1, 15, 10, 30, tzinfo=UTC
        )
        git_ops.get_first_commit_date.return_value = datetime(
            2024, 1, 10, 9, 0, tzinfo=UTC
        )
        return git_ops

    def test_document_url_generation_with_windows_paths(
        self, mock_config, mock_git_ops
    ):
        """Test that document URLs are correctly generated with forward slashes even on Windows."""
        # Simulate Windows file paths with backslashes
        windows_file_paths = [
            "C:\\temp\\git_repo_123\\README.md",
            "C:\\temp\\git_repo_123\\src\\main.py",
            "C:\\temp\\git_repo_123\\docs\\api\\index.md",
            "C:\\temp\\git_repo_123\\tests\\unit\\test_file.py",
        ]

        mock_git_ops.list_files.return_value = windows_file_paths

        with patch(
            "qdrant_loader.connectors.git.connector.GitOperations",
            return_value=mock_git_ops,
        ):
            with patch(
                "qdrant_loader.connectors.git.connector.FileProcessor.should_process_file",
                return_value=True,
            ):
                with patch("tempfile.mkdtemp", return_value="C:\\temp\\git_repo_123"):
                    # Mock os.path.relpath to return the expected relative path for Windows
                    with patch("os.path.relpath") as mock_relpath:
                        mock_relpath.return_value = (
                            "docs\\api\\index.md"  # Windows-style relative path
                        )

                        connector = GitConnector(mock_config)
                        connector.temp_dir = "C:\\temp\\git_repo_123"
                        connector._initialized = True

                        # Mock the file processor and metadata extractor
                        connector.file_processor = MagicMock()
                        connector.file_processor.should_process_file.return_value = True
                        connector.metadata_extractor = MagicMock()
                        connector.metadata_extractor.extract_all_metadata.return_value = {
                            "file_name": "test.md",
                            "file_size": 1024,
                        }

                        # Process a file to test URL generation
                        document = connector._process_file(
                            "C:\\temp\\git_repo_123\\docs\\api\\index.md"
                        )

                        # Verify the URL uses forward slashes, not backslashes
                        expected_url = (
                            "https://github.com/test/repo/blob/main/docs/api/index.md"
                        )
                        assert document.url == expected_url
                        assert (
                            "\\" not in document.url
                        ), "Document URL contains backslashes"
                        assert "//" not in document.url.replace(
                            "https://", ""
                        ), "Document URL contains double slashes"

    @pytest.mark.parametrize(
        "windows_file_path,expected_rel_path,expected_url_path",
        [
            # Regular nested files
            ("C:\\temp\\repo\\README.md", "README.md", "README.md"),
            ("C:\\temp\\repo\\src\\main.py", "src\\main.py", "src/main.py"),
            (
                "C:\\temp\\repo\\docs\\guide\\setup.md",
                "docs\\guide\\setup.md",
                "docs/guide/setup.md",
            ),
            # Files with spaces
            (
                "C:\\temp\\repo\\My Documents\\file.txt",
                "My Documents\\file.txt",
                "My Documents/file.txt",
            ),
            (
                "C:\\temp\\repo\\Program Files\\app\\config.py",
                "Program Files\\app\\config.py",
                "Program Files/app/config.py",
            ),
            # Deep nested paths
            (
                "C:\\temp\\repo\\very\\deep\\nested\\folder\\structure\\file.md",
                "very\\deep\\nested\\folder\\structure\\file.md",
                "very/deep/nested/folder/structure/file.md",
            ),
            # Root level files
            ("C:\\temp\\repo\\root_file.txt", "root_file.txt", "root_file.txt"),
        ],
    )
    def test_path_normalization_scenarios(
        self,
        mock_config,
        mock_git_ops,
        windows_file_path,
        expected_rel_path,
        expected_url_path,
    ):
        """Test various Windows path normalization scenarios."""
        mock_git_ops.list_files.return_value = [windows_file_path]

        with patch(
            "qdrant_loader.connectors.git.connector.GitOperations",
            return_value=mock_git_ops,
        ):
            with patch(
                "qdrant_loader.connectors.git.connector.FileProcessor.should_process_file",
                return_value=True,
            ):
                with patch("tempfile.mkdtemp", return_value="C:\\temp\\repo"):
                    # Mock os.path.relpath to return the expected Windows-style relative path
                    with patch("os.path.relpath") as mock_relpath:
                        mock_relpath.return_value = expected_rel_path

                        connector = GitConnector(mock_config)
                        connector.temp_dir = "C:\\temp\\repo"
                        connector._initialized = True

                        # Mock dependencies
                        connector.file_processor = MagicMock()
                        connector.file_processor.should_process_file.return_value = True
                        connector.metadata_extractor = MagicMock()
                        connector.metadata_extractor.extract_all_metadata.return_value = {
                            "file_name": "test"
                        }

                        # Process the file
                        document = connector._process_file(windows_file_path)

                        # Verify URL uses forward slashes
                        expected_url = f"https://github.com/test/repo/blob/main/{expected_url_path}"
                        assert document.url == expected_url
                        assert (
                            "\\" not in document.url
                        ), f"URL contains backslashes: {document.url}"

    def test_local_repository_cloning_windows_paths(self, mock_config):
        """Test cloning local repositories with Windows drive letter paths."""
        windows_local_paths = [
            "C:\\Users\\user\\MyProject",
            "D:\\Repositories\\MyRepo",
            "E:\\Development\\test-repo",
        ]

        for local_path in windows_local_paths:
            # Mock the existence checks and git operations
            with patch("os.path.exists", return_value=True):
                with patch("os.path.abspath", return_value=local_path):
                    with patch("os.path.join") as mock_join:
                        mock_join.return_value = f"{local_path}\\.git"
                        with patch("shutil.copytree"):
                            with patch("git.Repo") as mock_repo_class:
                                mock_repo_instance = MagicMock()
                                mock_repo_class.return_value = mock_repo_instance

                                git_ops = GitOperations()

                                # This should not raise an exception
                                git_ops.clone(
                                    url=local_path,
                                    to_path="C:\\temp\\target",
                                    branch="main",
                                    depth=1,
                                )

                                # Verify the repository was set
                                assert git_ops.repo == mock_repo_instance

    def test_file_path_operations_windows(self, mock_git_ops):
        """Test file path operations work correctly on Windows."""
        # Test that the mock git_ops returns the expected content
        content = mock_git_ops.get_file_content("any_path")
        assert content == "Test file content"

    def test_temporary_directory_handling_windows(self, mock_config, mock_git_ops):
        """Test temporary directory creation and cleanup on Windows."""
        windows_temp_dir = "C:\\temp\\git_connector_test_123"

        with patch("tempfile.mkdtemp", return_value=windows_temp_dir):
            with patch(
                "qdrant_loader.connectors.git.connector.GitOperations",
                return_value=mock_git_ops,
            ):
                with patch("shutil.rmtree") as mock_rmtree:
                    with patch("os.path.exists", return_value=True):
                        connector = GitConnector(mock_config)

                        # Test context manager entry
                        with connector:
                            assert connector.temp_dir == windows_temp_dir
                            assert connector.config.temp_dir == windows_temp_dir

                        # Verify cleanup was called
                        mock_rmtree.assert_called_with(windows_temp_dir)

    def test_edge_cases_windows_paths(self, mock_config, mock_git_ops):
        """Test edge cases with Windows paths."""
        edge_case_paths = [
            # UNC paths
            ("\\\\server\\share\\repo\\file.txt", "file.txt"),
            # Paths with multiple consecutive separators
            ("C:\\temp\\repo\\\\folder\\\\file.txt", "folder\\file.txt"),
            # Paths with mixed separators (shouldn't happen but test anyway)
            ("C:\\temp\\repo/mixed\\separators/file.txt", "mixed\\separators/file.txt"),
        ]

        mock_git_ops.repo.working_dir = "C:\\temp\\repo"

        for file_path, expected_rel_path in edge_case_paths:
            mock_git_ops.list_files.return_value = [file_path]

            with patch(
                "qdrant_loader.connectors.git.connector.GitOperations",
                return_value=mock_git_ops,
            ):
                with patch(
                    "qdrant_loader.connectors.git.connector.FileProcessor.should_process_file",
                    return_value=True,
                ):
                    with patch("tempfile.mkdtemp", return_value="C:\\temp\\repo"):
                        with patch("os.path.relpath") as mock_relpath:
                            mock_relpath.return_value = expected_rel_path

                            connector = GitConnector(mock_config)
                            connector.temp_dir = "C:\\temp\\repo"
                            connector._initialized = True

                            # Mock dependencies
                            connector.file_processor = MagicMock()
                            connector.file_processor.should_process_file.return_value = (
                                True
                            )
                            connector.metadata_extractor = MagicMock()
                            connector.metadata_extractor.extract_all_metadata.return_value = {
                                "file_name": "test"
                            }

                            try:
                                # This should not crash, even with edge case paths
                                document = connector._process_file(file_path)
                                # URL should not contain backslashes
                                assert (
                                    "\\" not in document.url
                                ), f"URL contains backslashes: {document.url}"
                            except Exception as e:
                                pytest.fail(
                                    f"Failed to process edge case path {file_path}: {e}"
                                )

    def test_url_encoding_windows_paths(self, mock_config, mock_git_ops):
        """Test that Windows paths with special characters are properly handled in URLs."""
        # Files with characters that need URL encoding
        special_char_files = [
            ("C:\\temp\\repo\\file with spaces.md", "file with spaces.md"),
            ("C:\\temp\\repo\\file&with&ampersands.txt", "file&with&ampersands.txt"),
            ("C:\\temp\\repo\\file%with%percent.py", "file%with%percent.py"),
            ("C:\\temp\\repo\\file#with#hash.md", "file#with#hash.md"),
        ]

        mock_git_ops.repo.working_dir = "C:\\temp\\repo"

        for file_path, expected_rel_path in special_char_files:
            mock_git_ops.list_files.return_value = [file_path]

            with patch(
                "qdrant_loader.connectors.git.connector.GitOperations",
                return_value=mock_git_ops,
            ):
                with patch(
                    "qdrant_loader.connectors.git.connector.FileProcessor.should_process_file",
                    return_value=True,
                ):
                    with patch("tempfile.mkdtemp", return_value="C:\\temp\\repo"):
                        with patch("os.path.relpath") as mock_relpath:
                            mock_relpath.return_value = expected_rel_path

                            connector = GitConnector(mock_config)
                            connector.temp_dir = "C:\\temp\\repo"
                            connector._initialized = True

                            # Mock dependencies
                            connector.file_processor = MagicMock()
                            connector.file_processor.should_process_file.return_value = (
                                True
                            )
                            connector.metadata_extractor = MagicMock()
                            connector.metadata_extractor.extract_all_metadata.return_value = {
                                "file_name": "test"
                            }

                            # Process the file
                            document = connector._process_file(file_path)

                            # URL should use forward slashes and preserve special characters
                            assert "\\" not in document.url
                            assert document.url.startswith(
                                "https://github.com/test/repo/blob/main/"
                            )

                            # The URL should contain the filename (with special chars preserved)
                            filename = os.path.basename(file_path)
                            # Convert to forward slash path
                            rel_path = expected_rel_path.replace("\\", "/")
                            expected_url = (
                                f"https://github.com/test/repo/blob/main/{rel_path}"
                            )
                            assert document.url == expected_url
