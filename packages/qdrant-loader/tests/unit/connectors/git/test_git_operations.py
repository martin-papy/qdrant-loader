"""
Unit tests for GitOperations.
"""

import os
import shutil
import tempfile
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from git.exc import GitCommandError
from qdrant_loader.connectors.git.operations import GitOperations


@pytest.fixture
def git_operations():
    """Create a GitOperations instance."""
    return GitOperations()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_repo():
    """Create a mock Git repository."""
    repo = MagicMock()
    repo.working_dir = "/fake/repo/path"
    return repo


class TestGitOperationsInitialization:
    """Test GitOperations initialization."""

    def test_initialization(self, git_operations):
        """Test that GitOperations initializes correctly."""
        assert git_operations.repo is None
        assert git_operations.logger is not None


class TestCloneOperations:
    """Test Git clone operations."""

    def test_clone_local_repository_success(self, git_operations, temp_dir):
        """Test successful cloning of a local repository."""
        # Create a fake local git repository
        source_repo = os.path.join(temp_dir, "source")
        target_repo = os.path.join(temp_dir, "target")
        os.makedirs(source_repo)
        os.makedirs(os.path.join(source_repo, ".git"))

        with patch("shutil.copytree") as mock_copytree:
            with patch("git.Repo") as mock_git_repo:
                mock_repo_instance = MagicMock()
                mock_git_repo.return_value = mock_repo_instance

                git_operations.clone(
                    url=source_repo, to_path=target_repo, branch="main", depth=1
                )

                mock_copytree.assert_called_once_with(
                    source_repo, target_repo, dirs_exist_ok=True
                )
                mock_git_repo.assert_called_once_with(target_repo)
                assert git_operations.repo == mock_repo_instance

    def test_clone_local_repository_invalid_git_repo(self, git_operations, temp_dir):
        """Test cloning of an invalid local repository."""
        # Create a directory without .git
        source_repo = os.path.join(temp_dir, "source")
        target_repo = os.path.join(temp_dir, "target")
        os.makedirs(source_repo)

        with pytest.raises(ValueError, match="not a valid Git repository"):
            git_operations.clone(
                url=source_repo, to_path=target_repo, branch="main", depth=1
            )

    def test_clone_remote_repository_success(self, git_operations, temp_dir):
        """Test successful cloning of a remote repository."""
        url = "https://github.com/example/repo.git"
        target_repo = os.path.join(temp_dir, "target")

        with patch("git.Repo.clone_from") as mock_clone_from:
            with patch("os.path.exists") as mock_exists:
                with patch("os.listdir") as mock_listdir:
                    mock_repo_instance = MagicMock()
                    mock_clone_from.return_value = mock_repo_instance
                    # Make sure os.path.exists returns False for the URL so it's treated as remote
                    mock_exists.side_effect = (
                        lambda path: path.endswith(".git") and "target" in path
                    )
                    mock_listdir.return_value = []

                    git_operations.clone(
                        url=url, to_path=target_repo, branch="main", depth=1
                    )

                    mock_clone_from.assert_called_once()
                    assert git_operations.repo == mock_repo_instance

    def test_clone_with_auth_token(self, git_operations, temp_dir):
        """Test cloning with authentication token."""
        url = "https://github.com/example/repo.git"
        target_repo = os.path.join(temp_dir, "target")
        auth_token = "ghp_test_token"

        with patch("git.Repo.clone_from") as mock_clone_from:
            with patch("os.path.exists") as mock_exists:
                with patch("os.listdir") as mock_listdir:
                    mock_repo_instance = MagicMock()
                    mock_clone_from.return_value = mock_repo_instance
                    # Make sure os.path.exists returns False for the URL so it's treated as remote
                    mock_exists.side_effect = (
                        lambda path: path.endswith(".git") and "target" in path
                    )
                    mock_listdir.return_value = []

                    git_operations.clone(
                        url=url,
                        to_path=target_repo,
                        branch="main",
                        depth=1,
                        auth_token=auth_token,
                    )

                    # Verify the URL was modified to include the token
                    call_args = mock_clone_from.call_args
                    assert f"https://{auth_token}@github.com" in call_args[0][0]

    def test_clone_with_retry_on_failure(self, git_operations, temp_dir):
        """Test cloning with retry on failure."""
        url = "https://github.com/example/repo.git"
        target_repo = os.path.join(temp_dir, "target")

        with patch("git.Repo.clone_from") as mock_clone_from:
            with patch("os.path.exists") as mock_exists:
                with patch("os.listdir") as mock_listdir:
                    with patch("time.sleep") as mock_sleep:
                        # Make sure os.path.exists returns False for the URL so it's treated as remote
                        mock_exists.side_effect = (
                            lambda path: path.endswith(".git") and "target" in path
                        )
                        mock_listdir.return_value = []

                        # First call fails, second succeeds
                        mock_repo_instance = MagicMock()
                        mock_clone_from.side_effect = [
                            GitCommandError("clone", "Clone failed"),
                            mock_repo_instance,
                        ]

                        git_operations.clone(
                            url=url,
                            to_path=target_repo,
                            branch="main",
                            depth=1,
                            max_retries=2,
                            retry_delay=1,
                        )

                        assert mock_clone_from.call_count == 2
                        mock_sleep.assert_called_once_with(1)
                        assert git_operations.repo == mock_repo_instance

    def test_clone_all_retries_fail(self, git_operations, temp_dir):
        """Test cloning when all retries fail."""
        url = "https://github.com/example/repo.git"
        target_repo = os.path.join(temp_dir, "target")

        with patch("git.Repo.clone_from") as mock_clone_from:
            with patch("os.path.exists") as mock_exists:
                with patch("os.listdir") as mock_listdir:
                    with patch("time.sleep") as mock_sleep:
                        # Make sure os.path.exists returns False for the URL so it's treated as remote
                        mock_exists.side_effect = (
                            lambda path: path.endswith(".git") and "target" in path
                        )
                        mock_listdir.return_value = []
                        mock_clone_from.side_effect = GitCommandError(
                            "clone", "Clone failed"
                        )

                        with pytest.raises(GitCommandError):
                            git_operations.clone(
                                url=url,
                                to_path=target_repo,
                                branch="main",
                                depth=1,
                                max_retries=2,
                                retry_delay=1,
                            )

                        assert mock_clone_from.call_count == 2
                        mock_sleep.assert_called_once_with(1)

    def test_clone_target_directory_cleanup(self, git_operations, temp_dir):
        """Test that non-empty target directory is cleaned up."""
        url = "https://github.com/example/repo.git"
        target_repo = os.path.join(temp_dir, "target")

        with patch("git.Repo.clone_from") as mock_clone_from:
            with patch("os.path.exists") as mock_exists:
                with patch("os.listdir") as mock_listdir:
                    with patch("shutil.rmtree") as mock_rmtree:
                        with patch("os.makedirs") as mock_makedirs:
                            mock_repo_instance = MagicMock()
                            mock_clone_from.return_value = mock_repo_instance
                            mock_exists.side_effect = lambda path: (
                                (path == target_repo)
                                or (path.endswith(".git") and "target" in path)
                            )
                            mock_listdir.return_value = ["existing_file.txt"]

                            git_operations.clone(
                                url=url, to_path=target_repo, branch="main", depth=1
                            )

                            mock_rmtree.assert_called_once_with(target_repo)
                            mock_makedirs.assert_called_once_with(target_repo)

    def test_clone_git_terminal_prompt_handling(self, git_operations, temp_dir):
        """Test that GIT_TERMINAL_PROMPT is properly handled during clone."""
        url = "https://github.com/example/repo.git"
        target_repo = os.path.join(temp_dir, "target")

        # Set an initial value for GIT_TERMINAL_PROMPT
        original_value = "1"
        os.environ["GIT_TERMINAL_PROMPT"] = original_value

        try:
            with patch("git.Repo.clone_from") as mock_clone_from:
                with patch("os.path.exists") as mock_exists:
                    with patch("os.listdir") as mock_listdir:
                        mock_repo_instance = MagicMock()
                        mock_clone_from.return_value = mock_repo_instance
                        # Make sure os.path.exists returns False for the URL so it's treated as remote
                        mock_exists.side_effect = (
                            lambda path: path.endswith(".git") and "target" in path
                        )
                        mock_listdir.return_value = []

                        git_operations.clone(
                            url=url, to_path=target_repo, branch="main", depth=1
                        )

                        # Verify the environment variable was restored
                        assert os.environ.get("GIT_TERMINAL_PROMPT") == original_value
        finally:
            # Clean up
            if "GIT_TERMINAL_PROMPT" in os.environ:
                del os.environ["GIT_TERMINAL_PROMPT"]

    def test_clone_git_terminal_prompt_not_set_initially(
        self, git_operations, temp_dir
    ):
        """Test GIT_TERMINAL_PROMPT handling when not set initially."""
        url = "https://github.com/example/repo.git"
        target_repo = os.path.join(temp_dir, "target")

        # Ensure GIT_TERMINAL_PROMPT is not set
        if "GIT_TERMINAL_PROMPT" in os.environ:
            del os.environ["GIT_TERMINAL_PROMPT"]

        with patch("git.Repo.clone_from") as mock_clone_from:
            with patch("os.path.exists") as mock_exists:
                with patch("os.listdir") as mock_listdir:
                    mock_repo_instance = MagicMock()
                    mock_clone_from.return_value = mock_repo_instance
                    # Make sure os.path.exists returns False for the URL so it's treated as remote
                    mock_exists.side_effect = (
                        lambda path: path.endswith(".git") and "target" in path
                    )
                    mock_listdir.return_value = []

                    git_operations.clone(
                        url=url, to_path=target_repo, branch="main", depth=1
                    )

                    # Verify the environment variable is not set after clone
                    assert "GIT_TERMINAL_PROMPT" not in os.environ


class TestFileOperations:
    """Test file operations."""

    def test_get_file_content_success(self, git_operations, mock_repo):
        """Test successful file content retrieval."""
        git_operations.repo = mock_repo
        file_path = "/fake/repo/path/test.txt"
        expected_content = "Test file content"

        mock_repo.git.show.return_value = expected_content

        content = git_operations.get_file_content(file_path)

        assert content == expected_content
        mock_repo.git.show.assert_called_once_with("HEAD:test.txt")

    def test_get_file_content_no_repo(self, git_operations):
        """Test file content retrieval when repository is not initialized."""
        with pytest.raises(ValueError, match="Repository not initialized"):
            git_operations.get_file_content("/some/file.txt")

    def test_get_file_content_file_not_in_repo(self, git_operations, mock_repo):
        """Test file content retrieval when file exists on disk but not in repo."""
        git_operations.repo = mock_repo
        file_path = "/fake/repo/path/test.txt"

        mock_repo.git.show.side_effect = GitCommandError(
            "show", "exists on disk, but not in"
        )

        with pytest.raises(
            FileNotFoundError, match="exists on disk but not in the repository"
        ):
            git_operations.get_file_content(file_path)

    def test_get_file_content_file_does_not_exist(self, git_operations, mock_repo):
        """Test file content retrieval when file does not exist."""
        git_operations.repo = mock_repo
        file_path = "/fake/repo/path/test.txt"

        mock_repo.git.show.side_effect = GitCommandError("show", "does not exist")

        with pytest.raises(FileNotFoundError, match="does not exist in the repository"):
            git_operations.get_file_content(file_path)

    def test_get_file_content_other_git_error(self, git_operations, mock_repo):
        """Test file content retrieval with other git errors."""
        git_operations.repo = mock_repo
        file_path = "/fake/repo/path/test.txt"

        mock_repo.git.show.side_effect = GitCommandError("show", "Some other error")

        with pytest.raises(GitCommandError):
            git_operations.get_file_content(file_path)


class TestCommitDateOperations:
    """Test commit date operations."""

    def test_get_last_commit_date_success(self, git_operations, mock_repo):
        """Test successful last commit date retrieval."""
        git_operations.repo = mock_repo
        file_path = "/fake/repo/path/test.txt"

        # Mock commit object
        mock_commit = MagicMock()
        mock_commit.committed_datetime = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        mock_repo.iter_commits.return_value = [mock_commit]

        result = git_operations.get_last_commit_date(file_path)

        assert result == datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        mock_repo.iter_commits.assert_called_once_with(paths="test.txt", max_count=1)

    def test_get_last_commit_date_no_commits(self, git_operations, mock_repo):
        """Test last commit date retrieval when no commits found."""
        git_operations.repo = mock_repo
        file_path = "/fake/repo/path/test.txt"

        mock_repo.iter_commits.return_value = []

        result = git_operations.get_last_commit_date(file_path)

        assert result is None

    def test_get_last_commit_date_no_repo(self, git_operations):
        """Test last commit date retrieval when repository is not initialized."""
        # The method catches the ValueError and returns None instead of raising
        result = git_operations.get_last_commit_date("/some/file.txt")
        assert result is None

    def test_get_last_commit_date_git_error(self, git_operations, mock_repo):
        """Test last commit date retrieval with git error."""
        git_operations.repo = mock_repo
        file_path = "/fake/repo/path/test.txt"

        mock_repo.iter_commits.side_effect = GitCommandError("log", "Git error")

        result = git_operations.get_last_commit_date(file_path)

        assert result is None

    def test_get_first_commit_date_success(self, git_operations, mock_repo):
        """Test successful first commit date retrieval."""
        git_operations.repo = mock_repo
        file_path = "/fake/repo/path/test.txt"

        # Mock commit objects - iter_commits with reverse=True and max_count=1 returns the first commit
        mock_commit1 = MagicMock()
        mock_commit1.committed_datetime = datetime(2024, 1, 10, 10, 30, 0, tzinfo=UTC)

        mock_repo.iter_commits.return_value = [mock_commit1]

        result = git_operations.get_first_commit_date(file_path)

        assert result == datetime(2024, 1, 10, 10, 30, 0, tzinfo=UTC)
        mock_repo.iter_commits.assert_called_once_with(
            paths="test.txt", reverse=True, max_count=1
        )

    def test_get_first_commit_date_no_commits(self, git_operations, mock_repo):
        """Test first commit date retrieval when no commits found."""
        git_operations.repo = mock_repo
        file_path = "/fake/repo/path/test.txt"

        mock_repo.iter_commits.return_value = []

        result = git_operations.get_first_commit_date(file_path)

        assert result is None

    def test_get_first_commit_date_no_repo(self, git_operations):
        """Test first commit date retrieval when repository is not initialized."""
        # The method catches the ValueError and returns None instead of raising
        result = git_operations.get_first_commit_date("/some/file.txt")
        assert result is None


class TestListFiles:
    """Test file listing operations."""

    def test_list_files_success(self, git_operations, mock_repo):
        """Test successful file listing."""
        git_operations.repo = mock_repo

        # Mock git ls-tree output (not ls-files)
        mock_repo.git.ls_tree.return_value = "file1.txt\nfile2.py\ndir/file3.md"
        mock_repo.working_dir = "/fake/repo/path"

        result = git_operations.list_files()

        # Use os.path.join for expected paths to match OS-specific separators
        expected = [
            os.path.join("/fake/repo/path", "file1.txt"),
            os.path.join("/fake/repo/path", "file2.py"),
            os.path.join("/fake/repo/path", "dir/file3.md"),
        ]
        assert result == expected
        mock_repo.git.ls_tree.assert_called_once_with("-r", "--name-only", "HEAD")

    def test_list_files_empty_repo(self, git_operations, mock_repo):
        """Test file listing in empty repository."""
        git_operations.repo = mock_repo

        mock_repo.git.ls_tree.return_value = ""

        result = git_operations.list_files()

        assert result == []

    def test_list_files_no_repo(self, git_operations):
        """Test file listing when repository is not initialized."""
        with pytest.raises(ValueError, match="Repository not initialized"):
            git_operations.list_files()

    def test_list_files_git_error(self, git_operations, mock_repo):
        """Test file listing with git error."""
        git_operations.repo = mock_repo

        mock_repo.git.ls_tree.side_effect = GitCommandError("ls-tree", "Git error")

        with pytest.raises(GitCommandError):
            git_operations.list_files()


class TestNestedFileHandling:
    """Test handling of nested files with mock path."""

    def test_get_file_content_nested_path_with_windows_separators(
        self, git_operations, mock_repo
    ):
        """Test file content retrieval with Windows separators cross-platform."""
        git_operations.repo = mock_repo
        expected_content = "import os"

        # CI can run on Linux/macOS where relpath semantics differ for Windows-like paths.
        # Mock relpath to isolate and verify path normalization behavior only.
        with patch("os.path.relpath", return_value=r"src\nested\file.py"):
            mock_repo.git.show.return_value = expected_content

            content = git_operations.get_file_content("/irrelevant/absolute/path.py")

            assert content == expected_content
            # Verify path was normalized to Unix separators
            mock_repo.git.show.assert_called_once_with("HEAD:src/nested/file.py")

    def test_get_file_content_deeply_nested_path(self, git_operations, mock_repo):
        """Test file content retrieval for deeply nested files."""
        git_operations.repo = mock_repo
        file_path = "/fake/repo/path/a/b/c/d/e/f/deep_file.txt"
        expected_content = "Deep content"

        mock_repo.working_dir = "/fake/repo/path"
        mock_repo.git.show.return_value = expected_content

        content = git_operations.get_file_content(file_path)

        assert content == expected_content
        mock_repo.git.show.assert_called_once_with("HEAD:a/b/c/d/e/f/deep_file.txt")

    def test_get_file_content_path_with_spaces(self, git_operations, mock_repo):
        """Test file content retrieval for paths with spaces."""
        git_operations.repo = mock_repo
        file_path = "/fake/repo/path/my module/sub dir/file with spaces.py"
        expected_content = "# Code in file with spaces"

        mock_repo.working_dir = "/fake/repo/path"
        mock_repo.git.show.return_value = expected_content

        content = git_operations.get_file_content(file_path)

        assert content == expected_content
        mock_repo.git.show.assert_called_once_with(
            "HEAD:my module/sub dir/file with spaces.py"
        )

    def test_get_file_content_path_with_special_chars(self, git_operations, mock_repo):
        """Test file content retrieval for paths with special characters."""
        git_operations.repo = mock_repo
        file_path = "/fake/repo/path/src-main/test_file-2024.py"
        expected_content = "# Test code"

        mock_repo.working_dir = "/fake/repo/path"
        mock_repo.git.show.return_value = expected_content

        content = git_operations.get_file_content(file_path)

        assert content == expected_content
        mock_repo.git.show.assert_called_once_with("HEAD:src-main/test_file-2024.py")

    def test_list_files_nested_structure(self, git_operations, mock_repo):
        """Test file listing with nested directory structure."""
        git_operations.repo = mock_repo

        nested_files = """src/main.py
src/utils/helpers.py
src/lib/core/engine.py
tests/unit/test_main.py
tests/integration/test_api.py
config.yaml
README.md"""

        mock_repo.git.ls_tree.return_value = nested_files
        mock_repo.working_dir = "/fake/repo"

        result = git_operations.list_files()

        # Verify the result contains the expected files
        assert len(result) == 7
        # Check that paths are joined correctly (os.path.join handles the separator)
        assert any("src/main.py" in p or "src\\main.py" in p for p in result)
        assert any("README.md" in p for p in result)
        assert any("config.yaml" in p for p in result)

    def test_get_last_commit_date_nested_file(self, git_operations, mock_repo):
        """Test last commit date retrieval for nested file."""
        git_operations.repo = mock_repo
        file_path = "/fake/repo/path/src/utils/helpers.py"

        mock_commit = MagicMock()
        mock_commit.committed_datetime = datetime(2024, 3, 20, 14, 30, 0, tzinfo=UTC)
        mock_repo.iter_commits.return_value = [mock_commit]
        mock_repo.working_dir = "/fake/repo/path"

        result = git_operations.get_last_commit_date(file_path)

        assert result == datetime(2024, 3, 20, 14, 30, 0, tzinfo=UTC)
        mock_repo.iter_commits.assert_called_once_with(
            paths="src/utils/helpers.py", max_count=1
        )

    def test_get_first_commit_date_nested_file(self, git_operations, mock_repo):
        """Test first commit date retrieval for nested file."""
        git_operations.repo = mock_repo
        file_path = "/fake/repo/path/src/lib/core/engine.py"

        mock_commit = MagicMock()
        mock_commit.committed_datetime = datetime(2024, 1, 5, 9, 0, 0, tzinfo=UTC)
        mock_repo.iter_commits.return_value = [mock_commit]
        mock_repo.working_dir = "/fake/repo/path"

        result = git_operations.get_first_commit_date(file_path)

        assert result == datetime(2024, 1, 5, 9, 0, 0, tzinfo=UTC)
        mock_repo.iter_commits.assert_called_once_with(
            paths="src/lib/core/engine.py", reverse=True, max_count=1
        )

    def test_to_git_path_normalization(self, git_operations):
        """Test path normalization to git format."""
        # Windows-style path
        win_path = "src\\main\\utils\\helpers.py"
        assert git_operations._to_git_path(win_path) == "src/main/utils/helpers.py"

        # Already unix-style
        unix_path = "src/main/utils/helpers.py"
        assert git_operations._to_git_path(unix_path) == "src/main/utils/helpers.py"

        # Mixed separators
        mixed_path = "src\\main/utils\\helpers.py"
        assert git_operations._to_git_path(mixed_path) == "src/main/utils/helpers.py"


class TestExceptionPaths:
    """Test exception paths for full coverage."""

    def test_get_file_content_generic_exception_in_outer_try(
        self, git_operations, mock_repo
    ):
        """Test file content when non-git exception occurs in outer try block."""
        git_operations.repo = mock_repo
        file_path = "/fake/repo/path/test.txt"

        # Simulate an unexpected exception by patching os.path.relpath
        with patch("os.path.relpath") as mock_relpath:
            mock_relpath.side_effect = RuntimeError("Unexpected error in relpath")

            with pytest.raises(RuntimeError):
                git_operations.get_file_content(file_path)

    def test_get_last_commit_date_broken_pipe_error(self, git_operations, mock_repo):
        """Test last commit date with BrokenPipeError."""
        git_operations.repo = mock_repo
        file_path = "/fake/repo/path/test.txt"

        # Make iter_commits raise BrokenPipeError
        mock_repo.iter_commits.side_effect = BrokenPipeError("Git process terminated")

        result = git_operations.get_last_commit_date(file_path)

        assert result is None

    def test_get_last_commit_date_unexpected_exception(self, git_operations, mock_repo):
        """Test last commit date with unexpected exception."""
        git_operations.repo = mock_repo
        file_path = "/fake/repo/path/test.txt"

        # Make iter_commits raise an unexpected exception
        mock_repo.iter_commits.side_effect = RuntimeError("Unexpected error")

        result = git_operations.get_last_commit_date(file_path)

        assert result is None

    def test_get_first_commit_date_broken_pipe_error(self, git_operations, mock_repo):
        """Test first commit date with BrokenPipeError."""
        git_operations.repo = mock_repo
        file_path = "/fake/repo/path/test.txt"

        # Make iter_commits raise BrokenPipeError
        mock_repo.iter_commits.side_effect = BrokenPipeError("Git process terminated")

        result = git_operations.get_first_commit_date(file_path)

        assert result is None

    def test_get_first_commit_date_unexpected_exception(
        self, git_operations, mock_repo
    ):
        """Test first commit date with unexpected exception."""
        git_operations.repo = mock_repo
        file_path = "/fake/repo/path/test.txt"

        # Make iter_commits raise an unexpected exception
        mock_repo.iter_commits.side_effect = ValueError("Bad value")

        result = git_operations.get_first_commit_date(file_path)

        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
