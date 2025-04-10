import os
import tempfile
from unittest.mock import patch, MagicMock, mock_open
import pytest
import tomli
import tomli_w
from pathlib import Path

# Import the functions we want to test
from release import (
    get_current_version,
    update_version,
    run_command,
    check_git_status,
    check_current_branch,
    check_unpushed_commits,
    get_github_token,
    create_github_release,
)

@pytest.fixture
def temp_pyproject():
    """Create a temporary pyproject.toml file for testing."""
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.toml', delete=False) as f:
        pyproject = {
            "project": {
                "name": "test-project",
                "version": "0.1.0"
            }
        }
        tomli_w.dump(pyproject, f)
        return f.name

def test_get_current_version(temp_pyproject):
    """Test getting the current version from pyproject.toml."""
    # Read the content of the temp file
    with open(temp_pyproject, 'rb') as f:
        content = f.read()
    
    # Mock the open function to return our content
    m = mock_open(read_data=content)
    with patch('release.open', m):
        version = get_current_version()
        assert version == "0.1.0"

def test_update_version():
    """Test updating the version in pyproject.toml."""
    new_version = "0.2.0"
    initial_pyproject = {
        "project": {
            "name": "test-project",
            "version": "0.1.0"
        }
    }
    
    # Create a mock file handler class
    class MockFileHandler:
        def __init__(self, initial_content):
            self.content = initial_content
            self.read_mode = None
            self.accumulated_content = ""
            print(f"Initial content: {self.content}")
        
        def __call__(self, filename, mode):
            print(f"Opening file {filename} in mode {mode}")
            self.read_mode = mode
            return self
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
        
        def read(self):
            print(f"Reading content in mode {self.read_mode}")
            if self.read_mode == "rb":
                result = tomli_w.dumps(self.content).encode('utf-8')
            else:
                result = tomli_w.dumps(self.content)
            print(f"Read result: {result}")
            return result
        
        def write(self, content):
            print(f"Writing content: {content}")
            if isinstance(content, bytes):
                content_str = content.decode('utf-8')
            else:
                content_str = content
            
            # Accumulate the content
            self.accumulated_content += content_str
            
            try:
                # Try to parse the accumulated content as TOML
                self.content = tomli.loads(self.accumulated_content)
                print(f"Updated content: {self.content}")
            except tomli.TOMLDecodeError:
                # If parsing fails, it means we don't have a complete TOML document yet
                print(f"Partial TOML content accumulated: {self.accumulated_content}")
    
    # Create the mock handler
    mock_handler = MockFileHandler(initial_pyproject)
    
    with patch('release.open', mock_handler):
        update_version(new_version)
        
        # Verify the content was updated correctly
        print(f"Final content: {mock_handler.content}")
        assert mock_handler.content["project"]["version"] == new_version
        assert mock_handler.content["project"]["name"] == "test-project"  # Verify other fields are preserved

def test_run_command():
    """Test running shell commands."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.stdout = "test output"
        mock_run.return_value.stderr = ""
        stdout, stderr = run_command("echo test")
        assert stdout == "test output"
        assert stderr == ""

def test_check_git_status_clean():
    """Test git status check with clean working directory."""
    with patch('release.run_command') as mock_run:
        mock_run.return_value = ("", "")
        # Should not raise any exception
        check_git_status()

def test_check_git_status_dirty():
    """Test git status check with dirty working directory."""
    with patch('release.run_command') as mock_run:
        mock_run.return_value = ("modified file", "")
        with pytest.raises(SystemExit):
            check_git_status()

def test_check_current_branch_main():
    """Test branch check when on main branch."""
    with patch('release.run_command') as mock_run:
        mock_run.return_value = ("main", "")
        # Should not raise any exception
        check_current_branch()

def test_check_current_branch_other():
    """Test branch check when not on main branch."""
    with patch('release.run_command') as mock_run:
        mock_run.return_value = ("feature", "")
        with pytest.raises(SystemExit):
            check_current_branch()

def test_check_unpushed_commits_with_commits():
    """Test unpushed commits check when there are commits."""
    with patch('release.run_command') as mock_run:
        mock_run.return_value = ("commit1\ncommit2", "")
        # Should not raise any exception
        check_unpushed_commits()

def test_check_unpushed_commits_without_commits():
    """Test unpushed commits check when there are no commits."""
    with patch('release.run_command') as mock_run:
        mock_run.return_value = ("", "")
        with pytest.raises(SystemExit):
            check_unpushed_commits()

def test_get_github_token():
    """Test getting GitHub token from environment."""
    with patch.dict(os.environ, {'GITHUB_TOKEN': 'test-token'}):
        token = get_github_token()
        assert token == 'test-token'

def test_get_github_token_missing():
    """Test getting GitHub token when it's missing."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(SystemExit):
            get_github_token()

def test_create_github_release():
    """Test creating a GitHub release."""
    with patch('release.run_command') as mock_run, \
         patch('requests.post') as mock_post, \
         patch('release.get_github_token') as mock_token:
        
        # Setup mocks
        mock_run.side_effect = [
            ("commit1\ncommit2", ""),  # For git log
            ("git@github.com:owner/repo.git", "")  # For git remote
        ]
        mock_token.return_value = "test-token"
        mock_post.return_value.status_code = 201
        
        # Test the function
        create_github_release("0.1.0", "test-token")
        
        # Verify the API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        assert call_args['json']['tag_name'] == 'v0.1.0'
        assert call_args['json']['name'] == 'Release v0.1.0'
        assert call_args['json']['body'] == "## Changes\n\n```\ncommit1\ncommit2\n```"

def test_create_github_release_failure():
    """Test GitHub release creation failure."""
    with patch('release.run_command') as mock_run, \
         patch('requests.post') as mock_post, \
         patch('release.get_github_token') as mock_token:
        
        # Setup mocks
        mock_run.side_effect = [
            ("commit1\ncommit2", ""),  # For git log
            ("git@github.com:owner/repo.git", "")  # For git remote
        ]
        mock_token.return_value = "test-token"
        mock_post.return_value.status_code = 400
        mock_post.return_value.text = "Error message"
        
        # Test the function
        with pytest.raises(SystemExit):
            create_github_release("0.1.0", "test-token")

def test_dry_run_mode():
    """Test dry run mode for various functions."""
    # Test update_version
    with patch('release.open') as mock_open:
        update_version("0.2.0", dry_run=True)
        mock_open.assert_not_called()
    
    # Test run_command
    with patch('subprocess.run') as mock_run:
        run_command("echo test", dry_run=True)
        mock_run.assert_not_called()
    
    # Test check_git_status
    with patch('release.run_command') as mock_run:
        check_git_status(dry_run=True)
        mock_run.assert_not_called()
    
    # Test create_github_release
    with patch('requests.post') as mock_post:
        create_github_release("0.1.0", "test-token", dry_run=True)
        mock_post.assert_not_called() 