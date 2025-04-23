import os
import sys
import tempfile
from unittest.mock import MagicMock, mock_open, patch

import pytest
import tomli
import tomli_w

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# Import the functions we want to test
from release import (
    check_current_branch,
    check_git_status,
    check_github_workflows,
    check_main_up_to_date,
    check_unpushed_commits,
    create_github_release,
    get_current_version,
    get_github_token,
    run_command,
    update_version,
)


@pytest.fixture
def temp_pyproject():
    """Create a temporary pyproject.toml file for testing."""
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".toml", delete=False) as f:
        pyproject = {"project": {"name": "test-project", "version": "0.1.0"}}
        tomli_w.dump(pyproject, f)
        return f.name


def test_get_current_version(temp_pyproject):
    """Test getting the current version from pyproject.toml."""
    # Read the content of the temp file
    with open(temp_pyproject, "rb") as f:
        content = f.read()

    # Mock the open function to return our content
    m = mock_open(read_data=content)
    with patch("release.open", m), patch("release.logging.getLogger") as mock_logger:
        mock_log = MagicMock()
        mock_logger.return_value = mock_log
        version = get_current_version()
        assert version == "0.1.0"
        mock_log.debug.assert_any_call("Reading current version from pyproject.toml")
        mock_log.debug.assert_any_call("Current version: 0.1.0")


def test_update_version():
    """Test updating the version in pyproject.toml."""
    new_version = "0.2.0"
    initial_pyproject = {"project": {"name": "test-project", "version": "0.1.0"}}

    # Create a mock file handler class
    class MockFileHandler:
        def __init__(self, initial_content):
            self.content = initial_content
            self.read_mode = None
            self.accumulated_content = ""

        def __call__(self, filename, mode):
            self.read_mode = mode
            return self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            if self.read_mode == "rb":
                result = tomli_w.dumps(self.content).encode("utf-8")
            else:
                result = tomli_w.dumps(self.content)
            return result

        def write(self, content):
            if isinstance(content, bytes):
                content_str = content.decode("utf-8")
            else:
                content_str = content
            self.accumulated_content += content_str
            self.content = tomli.loads(self.accumulated_content)

    # Create the mock handler
    mock_handler = MockFileHandler(initial_pyproject)

    with patch("release.open", mock_handler), patch("release.logging.getLogger") as mock_logger:
        mock_log = MagicMock()
        mock_logger.return_value = mock_log

        # Test normal update
        update_version(new_version)
        assert mock_handler.content["project"]["version"] == new_version
        mock_log.info.assert_called_with(f"Updating version in pyproject.toml to {new_version}")
        mock_log.debug.assert_called_with("Version updated successfully")

        # Test dry run
        update_version(new_version, dry_run=True)
        mock_log.info.assert_called_with(
            f"[DRY RUN] Would update version in pyproject.toml to {new_version}"
        )


def test_run_command():
    """Test running shell commands."""
    with patch("subprocess.run") as mock_run, patch("release.logging.getLogger") as mock_logger:
        mock_log = MagicMock()
        mock_logger.return_value = mock_log

        # Test normal command
        mock_run.return_value.stdout = "test output"
        mock_run.return_value.stderr = ""
        mock_run.return_value.returncode = 0
        stdout, stderr = run_command("echo test")
        assert stdout == "test output"
        assert stderr == ""
        mock_log.debug.assert_called_with("Executing command: echo test")

        # Test command with error
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "error message"
        stdout, stderr = run_command("echo test")
        mock_log.error.assert_any_call("Command failed with return code 1")
        mock_log.error.assert_any_call("stderr: error message")

        # Test dry run for non-git command
        stdout, stderr = run_command("echo test", dry_run=True)
        assert stdout == ""
        assert stderr == ""
        mock_log.info.assert_called_with("[DRY RUN] Would execute: echo test")

        # Test dry run for git command (should still execute)
        mock_run.return_value.stdout = "main"
        mock_run.return_value.stderr = ""
        mock_run.return_value.returncode = 0
        stdout, stderr = run_command("git branch --show-current", dry_run=True)
        assert stdout == "main"
        mock_log.debug.assert_called_with("Executing command: git branch --show-current")


def test_check_git_status_clean():
    """Test git status check with clean working directory."""
    with (
        patch("release.run_command") as mock_run,
        patch("release.logging.getLogger") as mock_logger,
    ):
        mock_log = MagicMock()
        mock_logger.return_value = mock_log
        mock_run.return_value = ("", "")

        # Test normal mode
        check_git_status()
        mock_log.debug.assert_any_call("Checking git status")
        mock_log.debug.assert_any_call("Git status check passed")

        # Test dry run mode (should still execute the check)
        check_git_status(dry_run=True)
        mock_run.assert_called_with("git status --porcelain", True)


def test_check_git_status_dirty():
    """Test git status check with dirty working directory."""
    with (
        patch("release.run_command") as mock_run,
        patch("release.logging.getLogger") as mock_logger,
    ):
        mock_log = MagicMock()
        mock_logger.return_value = mock_log
        mock_run.return_value = ("modified file", "")

        with pytest.raises(SystemExit):
            check_git_status()
        mock_log.error.assert_called_with(
            "There are uncommitted changes. Please commit or stash them first."
        )


def test_check_current_branch_main():
    """Test branch check when on main branch."""
    with (
        patch("release.run_command") as mock_run,
        patch("release.logging.getLogger") as mock_logger,
    ):
        mock_log = MagicMock()
        mock_logger.return_value = mock_log
        mock_run.return_value = ("main", "")

        # Test normal mode
        check_current_branch()
        mock_log.debug.assert_any_call("Checking current branch")
        mock_log.debug.assert_any_call("Current branch check passed")

        # Test dry run mode (should still execute the check)
        check_current_branch(dry_run=True)
        mock_run.assert_called_with("git branch --show-current", True)


def test_check_current_branch_other():
    """Test branch check when not on main branch."""
    with (
        patch("release.run_command") as mock_run,
        patch("release.logging.getLogger") as mock_logger,
    ):
        mock_log = MagicMock()
        mock_logger.return_value = mock_log
        mock_run.return_value = ("feature", "")

        with pytest.raises(SystemExit):
            check_current_branch()
        mock_log.error.assert_called_with("Not on main branch. Please switch to main branch first.")


def test_check_unpushed_commits_with_commits():
    """Test unpushed commits check when there are commits."""
    with (
        patch("release.run_command") as mock_run,
        patch("release.logging.getLogger") as mock_logger,
    ):
        mock_log = MagicMock()
        mock_logger.return_value = mock_log
        mock_run.return_value = ("commit1\ncommit2", "")

        with pytest.raises(SystemExit):
            check_unpushed_commits()
        mock_log.error.assert_called_with(
            "There are unpushed commits. Please push all changes before creating a release."
        )


def test_check_unpushed_commits_without_commits():
    """Test unpushed commits check when there are no commits."""
    with (
        patch("release.run_command") as mock_run,
        patch("release.logging.getLogger") as mock_logger,
    ):
        mock_log = MagicMock()
        mock_logger.return_value = mock_log
        mock_run.return_value = ("", "")

        check_unpushed_commits()
        mock_log.debug.assert_any_call("Checking for unpushed commits")
        mock_log.debug.assert_any_call("No unpushed commits found")


def test_get_github_token():
    """Test getting GitHub token from environment."""
    with (
        patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}),
        patch("release.logging.getLogger") as mock_logger,
    ):
        mock_log = MagicMock()
        mock_logger.return_value = mock_log

        token = get_github_token()
        assert token == "test-token"
        mock_log.debug.assert_called_with("Getting GitHub token from environment")


def test_get_github_token_missing():
    """Test getting GitHub token when it's missing."""
    with patch.dict(os.environ, {}, clear=True), patch("release.logging.getLogger") as mock_logger:
        mock_log = MagicMock()
        mock_logger.return_value = mock_log

        with pytest.raises(SystemExit):
            get_github_token()
        mock_log.error.assert_called_with("GITHUB_TOKEN not found in .env file.")


def test_create_github_release():
    """Test creating a GitHub release."""
    with (
        patch("release.run_command") as mock_run,
        patch("requests.post") as mock_post,
        patch("release.get_github_token") as mock_token,
        patch("release.logging.getLogger") as mock_logger,
    ):

        mock_log = MagicMock()
        mock_logger.return_value = mock_log

        # Setup mocks
        mock_run.side_effect = [
            ("commit1\ncommit2", ""),  # For git log
            ("git@github.com:owner/repo.git", ""),  # For git remote
        ]
        mock_token.return_value = "test-token"
        mock_post.return_value.status_code = 201

        # Test the function
        create_github_release("0.1.0", "test-token")

        # Verify the API call
        mock_post.assert_called_once()
        mock_log.info.assert_called_with("GitHub release created successfully")

        # Test dry run
        create_github_release("0.1.0", "test-token", dry_run=True)
        mock_log.info.assert_called_with("[DRY RUN] Would create GitHub release for version 0.1.0")


def test_check_main_up_to_date_up_to_date():
    """Test main branch check when up to date with remote."""
    with (
        patch("release.run_command") as mock_run,
        patch("release.logging.getLogger") as mock_logger,
    ):
        mock_log = MagicMock()
        mock_logger.return_value = mock_log

        # Setup mock for normal run
        mock_run.side_effect = [("", ""), ("0", "")]  # For git fetch  # For git rev-list

        check_main_up_to_date()
        mock_log.debug.assert_any_call("Checking if main branch is up to date")
        mock_log.debug.assert_any_call("Main branch is up to date")

        # Setup mock for dry run
        mock_run.side_effect = [
            ("", ""),  # For git fetch
            ("0", ""),  # For git rev-list
            ("", ""),  # For git fetch (dry run)
            ("0", ""),  # For git rev-list (dry run)
        ]

        # Test dry run (should still execute the checks)
        check_main_up_to_date(dry_run=True)
        assert mock_run.call_count == 4  # Two calls for each check


def test_check_github_workflows_success():
    """Test GitHub workflows check when all workflows are passing."""
    test_cases = [
        ("git@github.com:owner/repo.git", "owner/repo"),
        ("ssh://git@github.com/owner/repo.git", "owner/repo"),
        ("https://github.com/owner/repo.git", "owner/repo"),
    ]

    for remote_url, expected_repo in test_cases:
        with (
            patch("release.run_command") as mock_run,
            patch("release.get_github_token") as mock_token,
            patch("requests.get") as mock_get,
            patch("release.logging.getLogger") as mock_logger,
        ):

            mock_log = MagicMock()
            mock_logger.return_value = mock_log

            # Setup mocks
            mock_run.side_effect = [
                (remote_url, ""),  # For git remote
                ("abc123", ""),  # For git rev-parse HEAD
            ]
            mock_token.return_value = "test-token"

            # Mock successful API responses
            # First call: check running workflows
            mock_response_running = MagicMock()
            mock_response_running.status_code = 200
            mock_response_running.json.return_value = {"workflow_runs": []}

            # Second call: check completed workflows
            mock_response_completed = MagicMock()
            mock_response_completed.status_code = 200
            mock_response_completed.json.return_value = {
                "workflow_runs": [
                    {
                        "name": "Test and Coverage",
                        "conclusion": "success",
                        "html_url": "http://example.com",
                        "head_sha": "abc123",
                    },
                    {
                        "name": "Lint",
                        "conclusion": "success",
                        "html_url": "http://example.com",
                        "head_sha": "abc123",
                    },
                ]
            }

            # Setup side effect to return different responses for different calls
            mock_get.side_effect = [mock_response_running, mock_response_completed]

            check_github_workflows()
            mock_log.info.assert_any_call("GitHub workflows check completed successfully")

            # Verify the correct repository URL was used in both API calls
            assert mock_get.call_count == 2
            for call_args in mock_get.call_args_list:
                assert expected_repo in call_args[0][0]

            # Reset mocks for next iteration
            mock_get.reset_mock()


def test_check_github_workflows_commit_mismatch():
    """Test GitHub workflows check when workflow runs are on different commits."""
    with (
        patch("release.run_command") as mock_run,
        patch("release.get_github_token") as mock_token,
        patch("requests.get") as mock_get,
        patch("release.logging.getLogger") as mock_logger,
    ):

        mock_log = MagicMock()
        mock_logger.return_value = mock_log

        # Setup mocks
        mock_run.side_effect = [
            ("git@github.com:owner/repo.git", ""),  # For git remote
            ("abc123", ""),  # For git rev-parse HEAD
        ]
        mock_token.return_value = "test-token"

        # Mock successful API responses
        # First call: check running workflows
        mock_response_running = MagicMock()
        mock_response_running.status_code = 200
        mock_response_running.json.return_value = {"workflow_runs": []}

        # Second call: check completed workflows
        mock_response_completed = MagicMock()
        mock_response_completed.status_code = 200
        mock_response_completed.json.return_value = {
            "workflow_runs": [
                {
                    "name": "Test and Coverage",
                    "conclusion": "success",
                    "html_url": "http://example.com",
                    "head_sha": "def456",
                },
                {
                    "name": "Lint",
                    "conclusion": "success",
                    "html_url": "http://example.com",
                    "head_sha": "def456",
                },
            ]
        }

        # Setup side effect to return different responses for different calls
        mock_get.side_effect = [mock_response_running, mock_response_completed]

        with pytest.raises(SystemExit):
            check_github_workflows()

        # Verify error messages
        mock_log.error.assert_any_call(
            "Workflow 'Test and Coverage' was run on a different commit. Please ensure all workflows are run on the current commit."
        )
        mock_log.error.assert_any_call("Current commit: abc123")
        mock_log.error.assert_any_call("Workflow commit: def456")
        mock_log.error.assert_any_call("Workflow run: http://example.com")


def test_check_github_workflows_failure():
    """Test GitHub workflows check when a workflow is failing."""
    test_cases = [
        ("git@github.com:owner/repo.git", "owner/repo"),
        ("ssh://git@github.com/owner/repo.git", "owner/repo"),
        ("https://github.com/owner/repo.git", "owner/repo"),
    ]

    for remote_url, expected_repo in test_cases:
        with (
            patch("release.run_command") as mock_run,
            patch("release.get_github_token") as mock_token,
            patch("requests.get") as mock_get,
            patch("release.logging.getLogger") as mock_logger,
        ):

            mock_log = MagicMock()
            mock_logger.return_value = mock_log

            # Setup mocks
            mock_run.side_effect = [
                (remote_url, ""),  # For git remote
                ("abc123", ""),  # For git rev-parse HEAD
            ]
            mock_token.return_value = "test-token"

            # Mock successful API responses
            # First call: check running workflows
            mock_response_running = MagicMock()
            mock_response_running.status_code = 200
            mock_response_running.json.return_value = {"workflow_runs": []}

            # Second call: check completed workflows
            mock_response_completed = MagicMock()
            mock_response_completed.status_code = 200
            mock_response_completed.json.return_value = {
                "workflow_runs": [
                    {
                        "name": "Test and Coverage",
                        "conclusion": "failure",
                        "html_url": "http://example.com",
                        "head_sha": "abc123",
                    },
                    {
                        "name": "Lint",
                        "conclusion": "success",
                        "html_url": "http://example.com",
                        "head_sha": "abc123",
                    },
                ]
            }

            # Setup side effect to return different responses for different calls
            mock_get.side_effect = [mock_response_running, mock_response_completed]

            with pytest.raises(SystemExit):
                check_github_workflows()
            mock_log.error.assert_any_call(
                "Workflow 'Test and Coverage' is not passing. Latest run status: failure"
            )
            mock_log.error.assert_any_call("Please check the workflow run at: http://example.com")

            # Verify the correct repository URL was used in both API calls
            assert mock_get.call_count == 2
            for call_args in mock_get.call_args_list:
                assert expected_repo in call_args[0][0]

            # Reset mocks for next iteration
            mock_get.reset_mock()


def test_check_github_workflows_running():
    """Test GitHub workflows check when workflows are still running."""
    with (
        patch("release.run_command") as mock_run,
        patch("release.get_github_token") as mock_token,
        patch("requests.get") as mock_get,
        patch("release.logging.getLogger") as mock_logger,
    ):

        mock_log = MagicMock()
        mock_logger.return_value = mock_log

        # Setup mocks
        mock_run.side_effect = [
            ("git@github.com:owner/repo.git", ""),  # For git remote
            ("abc123", ""),  # For git rev-parse HEAD
        ]
        mock_token.return_value = "test-token"

        # Mock API response with running workflow
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "workflow_runs": [
                {
                    "name": "Test and Coverage",
                    "status": "in_progress",
                    "html_url": "http://example.com",
                }
            ]
        }
        mock_get.return_value = mock_response

        with pytest.raises(SystemExit):
            check_github_workflows()
        mock_log.error.assert_any_call(
            "There are workflows still running. Please wait for them to complete."
        )
        mock_log.error.assert_any_call("- Test and Coverage is running: http://example.com")


def test_check_github_workflows_api_error():
    """Test GitHub workflows check when API request fails."""
    with (
        patch("release.run_command") as mock_run,
        patch("release.get_github_token") as mock_token,
        patch("requests.get") as mock_get,
        patch("release.logging.getLogger") as mock_logger,
    ):

        mock_log = MagicMock()
        mock_logger.return_value = mock_log

        # Setup mocks
        mock_run.side_effect = [
            ("git@github.com:owner/repo.git", ""),  # For git remote
            ("abc123", ""),  # For git rev-parse HEAD
        ]
        mock_token.return_value = "test-token"

        # Mock API error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        with pytest.raises(SystemExit):
            check_github_workflows()
        mock_log.error.assert_called_with(
            "Error checking GitHub Actions status: Internal Server Error"
        )


def test_dry_run_mode():
    """Test dry run mode for various functions."""
    with patch("release.logging.getLogger") as mock_logger:
        mock_log = MagicMock()
        mock_logger.return_value = mock_log

        # Test update_version
        with patch("release.open") as mock_open:
            update_version("0.2.0", dry_run=True)
            mock_open.assert_not_called()
            mock_log.info.assert_called_with(
                "[DRY RUN] Would update version in pyproject.toml to 0.2.0"
            )

        # Test run_command for non-git command
        with patch("subprocess.run") as mock_run:
            run_command("echo test", dry_run=True)
            mock_run.assert_not_called()
            mock_log.info.assert_called_with("[DRY RUN] Would execute: echo test")

        # Test run_command for git command (should still execute)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "main"
            mock_run.return_value.stderr = ""
            mock_run.return_value.returncode = 0
            run_command("git branch --show-current", dry_run=True)
            mock_run.assert_called()
            mock_log.debug.assert_called_with("Executing command: git branch --show-current")

        # Test check_git_status (should still execute)
        with patch("release.run_command") as mock_run:
            mock_run.return_value = ("", "")
            check_git_status(dry_run=True)
            mock_run.assert_called_with("git status --porcelain", True)

        # Test check_main_up_to_date (should still execute)
        with patch("release.run_command") as mock_run:
            mock_run.side_effect = [("", ""), ("0", "")]
            check_main_up_to_date(dry_run=True)
            assert mock_run.call_count == 2

        # Test check_github_workflows (should still execute)
        with (
            patch("release.run_command") as mock_run,
            patch("release.get_github_token") as mock_token,
            patch("requests.get") as mock_get,
        ):
            mock_run.side_effect = [
                ("git@github.com:owner/repo.git", ""),  # For git remote
                ("abc123", ""),  # For git rev-parse HEAD
            ]
            mock_token.return_value = "test-token"

            # Mock responses for both API calls
            mock_response_running = MagicMock()
            mock_response_running.status_code = 200
            mock_response_running.json.return_value = {"workflow_runs": []}

            mock_response_completed = MagicMock()
            mock_response_completed.status_code = 200
            mock_response_completed.json.return_value = {
                "workflow_runs": [
                    {
                        "name": "Test",
                        "conclusion": "success",
                        "html_url": "http://example.com",
                        "head_sha": "abc123",
                    }
                ]
            }

            mock_get.side_effect = [mock_response_running, mock_response_completed]

            check_github_workflows(dry_run=True)
            assert mock_get.call_count == 2
