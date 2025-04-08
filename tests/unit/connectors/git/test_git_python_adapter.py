import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from git import Repo
from git.exc import GitCommandError

from qdrant_loader.connectors.git import GitPythonAdapter
from qdrant_loader.utils.logger import get_logger

@pytest.fixture
def mock_repo():
    """Create a mock Git repository."""
    repo = MagicMock()
    repo.git.show.return_value = "test content"
    repo.git.log.return_value = "2024-03-20 12:00:00 +0000"
    repo.git.ls_tree.return_value = "file1.txt\nfile2.txt"
    return repo

def test_git_python_adapter_init(mock_repo):
    """Test GitPythonAdapter initialization."""
    adapter = GitPythonAdapter(mock_repo)
    assert adapter.repo == mock_repo
    assert adapter.logger is not None

def test_git_python_adapter_init_no_repo():
    """Test GitPythonAdapter initialization without repo."""
    adapter = GitPythonAdapter()
    assert adapter.repo is None
    assert adapter.logger is not None

def test_git_python_adapter_clone(mock_repo):
    """Test GitPythonAdapter clone method."""
    adapter = GitPythonAdapter()
    url = "https://github.com/test/repo.git"
    to_path = tempfile.mkdtemp()
    branch = "main"
    depth = 1

    with patch('git.Repo.clone_from', return_value=mock_repo):
        adapter.clone(url, to_path, branch, depth)
        assert adapter.repo == mock_repo

def test_git_python_adapter_clone_full_history(mock_repo):
    """Test GitPythonAdapter clone method with full history."""
    adapter = GitPythonAdapter()
    url = "https://github.com/test/repo.git"
    to_path = tempfile.mkdtemp()
    branch = "main"
    depth = 0

    with patch('git.Repo.clone_from', return_value=mock_repo):
        adapter.clone(url, to_path, branch, depth)
        assert adapter.repo == mock_repo

def test_git_python_adapter_clone_error(mock_repo):
    """Test GitPythonAdapter clone method with error."""
    adapter = GitPythonAdapter()
    url = "https://github.com/test/repo.git"
    to_path = tempfile.mkdtemp()
    branch = "main"
    depth = 1

    error = GitCommandError("clone", "error")
    with patch('git.Repo.clone_from', side_effect=error):
        with pytest.raises(GitCommandError) as exc_info:
            adapter.clone(url, to_path, branch, depth)
        assert str(exc_info.value) == str(error)

def test_git_python_adapter_get_file_content(mock_repo):
    """Test GitPythonAdapter get_file_content method."""
    adapter = GitPythonAdapter(mock_repo)
    file_path = "test.md"
    
    content = adapter.get_file_content(file_path)
    assert content == "test content"
    mock_repo.git.show.assert_called_once_with(f"HEAD:{file_path}")

def test_git_python_adapter_get_file_content_no_repo():
    """Test GitPythonAdapter get_file_content method without repo."""
    adapter = GitPythonAdapter()
    with pytest.raises(ValueError) as exc_info:
        adapter.get_file_content("test.md")
    assert "Repository not initialized" in str(exc_info.value)

def test_git_python_adapter_get_file_content_error(mock_repo):
    """Test GitPythonAdapter get_file_content method with error."""
    adapter = GitPythonAdapter(mock_repo)
    error = GitCommandError("show", "error")
    mock_repo.git.show.side_effect = error
    
    with pytest.raises(GitCommandError) as exc_info:
        adapter.get_file_content("test.md")
    assert str(exc_info.value) == str(error)

def test_git_python_adapter_get_last_commit_date(mock_repo):
    """Test GitPythonAdapter get_last_commit_date method."""
    adapter = GitPythonAdapter(mock_repo)
    file_path = "test.md"
    
    # Mock the Repo class and iter_commits
    with patch('git.Repo') as mock_git_repo:
        mock_commit = MagicMock()
        mock_commit.committed_datetime = datetime(2024, 3, 20, 12, 0, 0)
        mock_git_repo.return_value.iter_commits.return_value = [mock_commit]
        
        date = adapter.get_last_commit_date(file_path)
        assert isinstance(date, datetime)
        assert date.isoformat() == "2024-03-20T12:00:00"

def test_git_python_adapter_get_last_commit_date_no_repo():
    """Test GitPythonAdapter get_last_commit_date method without repo."""
    adapter = GitPythonAdapter()
    result = adapter.get_last_commit_date("test.md")
    assert result is None

def test_git_python_adapter_get_last_commit_date_error(mock_repo):
    """Test GitPythonAdapter get_last_commit_date method with error."""
    adapter = GitPythonAdapter(mock_repo)
    
    # Mock the Repo class to raise an exception
    with patch('git.Repo', side_effect=Exception("Test error")):
        result = adapter.get_last_commit_date("test.md")
        assert result is None

def test_git_python_adapter_list_files(mock_repo):
    """Test GitPythonAdapter list_files method."""
    adapter = GitPythonAdapter(mock_repo)
    path = "."
    
    files = adapter.list_files(path)
    assert len(files) == 2
    assert "file1.txt" in files
    assert "file2.txt" in files
    mock_repo.git.ls_tree.assert_called_once_with("-r", "--name-only", "HEAD", path)

def test_git_python_adapter_list_files_no_repo():
    """Test GitPythonAdapter list_files method without repo."""
    adapter = GitPythonAdapter()
    with pytest.raises(ValueError) as exc_info:
        adapter.list_files()
    assert "Repository not initialized" in str(exc_info.value)

def test_git_python_adapter_list_files_error(mock_repo):
    """Test GitPythonAdapter list_files method with error."""
    adapter = GitPythonAdapter(mock_repo)
    error = GitCommandError("ls-tree", "error")
    mock_repo.git.ls_tree.side_effect = error
    
    with pytest.raises(GitCommandError) as exc_info:
        adapter.list_files()
    assert str(exc_info.value) == str(error)

def test_git_python_adapter_list_files_empty(mock_repo):
    """Test GitPythonAdapter list_files method with empty result."""
    adapter = GitPythonAdapter(mock_repo)
    mock_repo.git.ls_tree.return_value = ""
    
    files = adapter.list_files()
    assert len(files) == 0

def test_git_python_adapter_error_handling(mock_repo):
    """Test GitPythonAdapter error handling."""
    adapter = GitPythonAdapter(mock_repo)
    mock_repo.git.show.side_effect = Exception("Test error")
    
    with pytest.raises(Exception) as exc_info:
        adapter.get_file_content("test.md")
    assert str(exc_info.value) == "Test error" 