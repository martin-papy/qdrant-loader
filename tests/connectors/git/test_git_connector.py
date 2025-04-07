import os
import tempfile
from datetime import datetime, UTC
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, mock_open, patch

import pytest
from git import Repo
from git.exc import GitCommandError

from qdrant_loader.config import GitRepoConfig, GitAuthConfig
from qdrant_loader.connectors.git import GitConnector, GitOperations, GitPythonAdapter
from qdrant_loader.core.document import Document

class MockGitOperations:
    """Mock Git operations for testing."""

    def __init__(self):
        """Initialize mock Git operations."""
        self.files = {}
        self.repo = None
        self.repo_dir = None

    def _init_repo(self, path: str) -> None:
        """Initialize a Git repository."""
        # Create .git directory
        git_dir = os.path.join(path, '.git')
        os.makedirs(git_dir, exist_ok=True)

        # Create basic Git config file
        config_path = os.path.join(git_dir, 'config')
        with open(config_path, 'w') as f:
            f.write('[core]\n\trepositoryformatversion = 0\n\tfilemode = true\n\tbare = false\n')
            f.write('[remote "origin"]\n\turl = https://github.com/example/repo.git\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n')

        # Create description file
        description_path = os.path.join(git_dir, 'description')
        with open(description_path, 'w') as f:
            f.write("Mock repository description\n")

        # Create objects directory and refs
        os.makedirs(os.path.join(git_dir, 'objects'), exist_ok=True)
        os.makedirs(os.path.join(git_dir, 'refs', 'heads'), exist_ok=True)

        # Initialize a real Git repository
        import git
        repo = git.Repo.init(path)
        
        # Create an initial commit
        repo.index.add([])
        initial_commit = repo.index.commit("Initial commit")

        # Update HEAD to point to the initial commit
        with open(os.path.join(git_dir, 'refs', 'heads', 'main'), 'w') as f:
            f.write(initial_commit.hexsha + '\n')

        with open(os.path.join(git_dir, 'HEAD'), 'w') as f:
            f.write('ref: refs/heads/main\n')

        # Create mock repo object
        mock_repo = MagicMock()
        mock_repo.working_dir = path
        mock_repo.git_dir = git_dir

        # Mock remotes
        mock_remote = MagicMock()
        mock_remote.url = "https://github.com/example/repo.git"
        mock_remote.name = "origin"

        # Create a list-like object for remotes
        class MockRemote:
            def __init__(self, url):
                self.url = url
                self.name = "origin"

        class MockRemotes:
            def __init__(self, remote):
                self.origin = remote
                self._remotes = [remote]

            def __iter__(self):
                return iter(self._remotes)

            def __getattr__(self, name):
                if name == "origin":
                    return self.origin
                raise AttributeError(f"'MockRemotes' object has no attribute '{name}'")

        mock_repo.remotes = MockRemotes(MockRemote("https://github.com/example/repo.git"))

        # Mock description
        mock_repo.description = "Mock repository"

        # Create mock commit
        mock_commit = MagicMock()
        mock_commit.hexsha = initial_commit.hexsha
        mock_commit.committed_date = datetime.now().timestamp()
        mock_commit.author = MagicMock()
        mock_commit.author.name = "Test Author"
        mock_commit.message = "Initial commit"
        mock_repo.iter_commits.return_value = [mock_commit]

        # Mock head commit
        mock_repo.head.commit = mock_commit

        self.repo = mock_repo

    def clone(self, url: str, to_path: str, branch: str, depth: int) -> None:
        """Mock repository cloning."""
        self.repo_dir = to_path
        self._init_repo(to_path)

    def get_file_content(self, file_path: str) -> str:
        """Mock file content retrieval."""
        return self.files.get(file_path, "")

    def get_last_commit_date(self, file_path: str) -> datetime:
        """Mock last commit date retrieval."""
        if not self.repo:
            raise RuntimeError("Repository not initialized")
        return datetime.now()

    def list_files(self) -> List[str]:
        """Mock file listing."""
        if not self.repo:
            raise RuntimeError("Repository not initialized")
        return list(self.files.keys())

@pytest.fixture
def mock_config():
    return GitRepoConfig(
        url="https://github.com/example/repo.git",
        branch="main",
        include_paths=["**/*"],
        exclude_paths=[],
        file_types=["*.md", "*.txt"],
        max_file_size=1024 * 1024,
        depth=1,
        auth=GitAuthConfig(type="none", token_env=None)
    )

@pytest.fixture
def mock_git_ops():
    """Create a mock GitOperations instance."""
    git_ops = MagicMock()
    git_ops.clone.return_value = None
    git_ops.get_file_content.return_value = "test content"
    git_ops.get_last_commit_date.return_value = datetime.now()
    git_ops.list_files.return_value = ["file1.txt", "file2.txt"]
    return git_ops

@pytest.fixture
def git_config():
    """Create a GitRepoConfig instance."""
    return GitRepoConfig(
        url="https://github.com/test/repo.git",
        branch="main",
        depth=1,
        file_types=["*.txt", "*.md"],
        include_paths=["docs/*", "src/*"],
        exclude_paths=[".git/*", "tests/*"],
        max_file_size=1024 * 1024  # 1MB
    )

def test_git_operations_init():
    """Test GitOperations initialization."""
    ops = GitOperations()
    assert ops.repo is None
    assert ops.logger is not None

def test_git_operations_clone():
    """Test GitOperations clone method."""
    ops = GitOperations()
    url = "https://github.com/test/repo.git"
    to_path = tempfile.mkdtemp()
    branch = "main"
    depth = 1

    with patch('git.Repo.clone_from') as mock_clone:
        ops.clone(url, to_path, branch, depth)
        mock_clone.assert_called_once_with(
            url,
            to_path,
            multi_options=['--branch', branch, '--depth', str(depth)]
        )

def test_git_operations_clone_error():
    """Test GitOperations clone method with error."""
    ops = GitOperations()
    url = "https://github.com/test/repo.git"
    to_path = tempfile.mkdtemp()
    branch = "main"
    depth = 1

    with patch('git.Repo.clone_from', side_effect=GitCommandError("clone", "error")):
        with pytest.raises(GitCommandError):
            ops.clone(url, to_path, branch, depth)

def test_git_operations_get_file_content():
    """Test GitOperations get_file_content method."""
    ops = GitOperations()
    file_path = "test.txt"
    content = "test content"

    m = mock_open(read_data=content)
    with patch('builtins.open', m):
        result = ops.get_file_content(file_path)
        assert result == content

def test_git_operations_get_file_content_error():
    """Test GitOperations get_file_content method with error."""
    ops = GitOperations()
    file_path = "test.txt"

    with patch('builtins.open', side_effect=IOError("error")):
        with pytest.raises(IOError):
            ops.get_file_content(file_path)

def test_git_operations_get_last_commit_date():
    """Test GitOperations get_last_commit_date method."""
    ops = GitOperations()
    file_path = "test.txt"
    commit_date = datetime.now()
    
    mock_repo = MagicMock()
    mock_commit = MagicMock()
    mock_commit.committed_date = int(commit_date.timestamp())
    mock_repo.iter_commits.return_value = [mock_commit]
    mock_repo.working_dir = "/tmp/repo"
    ops.repo = mock_repo

    result = ops.get_last_commit_date(file_path)
    assert isinstance(result, datetime)
    # Compare only up to seconds precision
    assert int(result.timestamp()) == int(commit_date.timestamp())

def test_git_operations_get_last_commit_date_no_commits():
    """Test GitOperations get_last_commit_date method with no commits."""
    ops = GitOperations()
    file_path = "test.txt"
    
    mock_repo = MagicMock()
    mock_repo.iter_commits.return_value = []
    mock_repo.working_dir = "/tmp/repo"
    ops.repo = mock_repo

    result = ops.get_last_commit_date(file_path)
    assert isinstance(result, datetime)

def test_git_operations_list_files():
    """Test GitOperations list_files method."""
    ops = GitOperations()
    mock_repo = MagicMock()
    mock_repo.working_dir = "/tmp/repo"
    ops.repo = mock_repo

    files = ["file1.txt", "file2.txt"]
    with patch('os.walk', return_value=[("/tmp/repo", [], files)]):
        result = ops.list_files()
        assert len(result) == 2
        assert all(f.endswith(file) for f, file in zip(result, files))

def test_git_connector_init(git_config, mock_git_ops):
    """Test GitConnector initialization."""
    connector = GitConnector(git_config, mock_git_ops)
    assert connector.config == git_config
    assert connector.git_ops == mock_git_ops
    assert connector.temp_dir is None
    assert connector.logger is not None
    assert connector.metadata_extractor is not None

def test_git_connector_context_manager(git_config, mock_git_ops):
    """Test GitConnector context manager."""
    with patch('tempfile.mkdtemp', return_value="/tmp/test"):
        with GitConnector(git_config, mock_git_ops) as connector:
            assert connector.temp_dir == "/tmp/test"
            mock_git_ops.clone.assert_called_once_with(
                git_config.url,
                "/tmp/test",
                git_config.branch,
                git_config.depth
            )

def test_git_connector_cleanup(git_config, mock_git_ops):
    """Test GitConnector cleanup."""
    temp_dir = tempfile.mkdtemp()
    with patch('tempfile.mkdtemp', return_value=temp_dir):
        with GitConnector(git_config, mock_git_ops):
            assert os.path.exists(temp_dir)
        assert not os.path.exists(temp_dir)

def test_should_process_file(git_config, mock_git_ops):
    """Test GitConnector _should_process_file method."""
    connector = GitConnector(git_config, mock_git_ops)
    connector.temp_dir = "/tmp/test"

    with patch('os.path.exists', return_value=True), \
         patch('os.path.getsize', return_value=1000):  # Small file size
        # Test .git file
        assert not connector._should_process_file("/tmp/test/.git/config")

        # Test file size
        with patch('os.path.getsize', return_value=git_config.max_file_size + 1):
            assert not connector._should_process_file("/tmp/test/large_file.txt")

        # Test file type
        assert not connector._should_process_file("/tmp/test/file.exe")
        
        # Test include paths
        assert connector._should_process_file("/tmp/test/src/file.txt")
        assert not connector._should_process_file("/tmp/test/other/file.txt")

        # Test exclude paths
        assert not connector._should_process_file("/tmp/test/tests/file.txt")

def test_process_file(git_config, mock_git_ops):
    """Test GitConnector _process_file method."""
    connector = GitConnector(git_config, mock_git_ops)
    connector.temp_dir = "/tmp/test"
    file_path = "/tmp/test/src/file.txt"

    content = "test content"
    metadata = {"repository_url": "https://github.com/test/repo.git"}
    
    m = mock_open(read_data=content)
    with patch('builtins.open', m):
        with patch.object(connector.metadata_extractor, 'extract_all_metadata', return_value=metadata):
            doc = connector._process_file(file_path)
            assert isinstance(doc, Document)
            assert doc.content == content
            # Check that metadata contains the expected key
            assert doc.metadata["repository_url"] == metadata["repository_url"]
            assert doc.source == metadata["repository_url"]
            assert doc.source_type == "git"

def test_get_documents(git_config, mock_git_ops):
    """Test GitConnector get_documents method."""
    connector = GitConnector(git_config, mock_git_ops)
    connector.temp_dir = "/tmp/test"

    # Define files with their full paths
    files = [
        ("src", [], ["file1.txt", "file2.txt"]),
        ("tests", [], ["test.txt"]),
        (".git", [], ["config"])
    ]

    content = "test content"
    metadata = {
        "file_type": ".txt",
        "file_name": "file1.txt",
        "file_directory": "src",
        "file_encoding": "utf-8",
        "line_count": 1,
        "word_count": 2,
        "has_code_blocks": False,
        "has_images": False,
        "has_links": False,
        "repository_url": "https://github.com/test/repo.git",
        "repository_name": "repo",
        "repository_owner": "test",
        "repository_description": "Test repository",
        "repository_language": "Text",
        "last_commit_date": "2024-04-07T14:35:47",
        "last_commit_author": "Test Author",
        "last_commit_message": "Test commit",
        "has_toc": False,
        "heading_levels": [],
        "sections_count": 0
    }

    mock_now = datetime(2025, 4, 7, 7, 37, 46, 312620, tzinfo=UTC)
    with patch('os.walk', return_value=files), \
         patch('os.path.join', side_effect=lambda *args: '/'.join(args)), \
         patch('os.path.exists', return_value=True), \
         patch('os.path.getsize', return_value=1000), \
         patch('os.path.relpath', side_effect=lambda path, base: path.replace(base + '/', '')), \
         patch('builtins.open', mock_open(read_data=content)), \
         patch.object(connector.metadata_extractor, 'extract_all_metadata', return_value=metadata), \
         patch('qdrant_loader.core.document.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now
        docs = connector.get_documents()
        assert len(docs) == 2  # Only 2 files should be processed (src/file1.txt and src/file2.txt)
        for doc in docs:
            assert doc.content == content
            expected_metadata = metadata.copy()
            expected_metadata.update({
                'source': metadata['repository_url'],
                'source_type': 'git',
                'created_at': '2025-04-07T07:37:46.312620+00:00'
            })
            assert doc.metadata == expected_metadata
            assert doc.source == metadata["repository_url"]
            assert doc.source_type == "git"
