import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import tempfile
from pathlib import Path
from git import GitCommandError
from qdrant_loader.connectors.git import GitConnector, GitOperations
from qdrant_loader.config import GitRepoConfig, GitAuthConfig
from qdrant_loader.core.document import Document
from datetime import datetime
from typing import List

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
    return MockGitOperations()

def test_should_process_file(mock_config, mock_git_ops):
    """Test file filtering based on configuration."""
    with GitConnector(mock_config, mock_git_ops) as connector:
        # Create test files
        test_files = {
            "test.md": "Test content",
            "test.txt": "Test content",
            "test.py": "Test content",
            "test.jpg": "Test content"
        }

        for filename, content in test_files.items():
            file_path = Path(connector.temp_dir) / filename
            file_path.write_text(content)
            mock_git_ops.files[str(file_path)] = content

        # Test file type filtering
        assert connector._should_process_file(str(Path(connector.temp_dir) / "test.md"))
        assert connector._should_process_file(str(Path(connector.temp_dir) / "test.txt"))
        assert not connector._should_process_file(str(Path(connector.temp_dir) / "test.py"))
        assert not connector._should_process_file(str(Path(connector.temp_dir) / "test.jpg"))

def test_process_file(mock_config, mock_git_ops):
    """Test file processing."""
    with GitConnector(mock_config, mock_git_ops) as connector:
        # Create a temporary directory and test file
        test_file = Path(connector.temp_dir) / "test.md"
        test_file.write_text("Test content")
        mock_git_ops.files[str(test_file)] = "Test content"

        # Process the file
        doc = connector._process_file(str(test_file))
        assert doc.content == "Test content"
        assert doc.metadata["file_name"] == "test.md"
        assert doc.metadata["repository_url"] == "https://github.com/example/repo.git"

def test_get_documents(mock_config, mock_git_ops):
    """Test document retrieval."""
    with GitConnector(mock_config, mock_git_ops) as connector:
        # Create test files
        test_files = {
            "test1.md": "Content 1",
            "test2.txt": "Content 2",
            "test3.py": "Content 3"
        }

        for filename, content in test_files.items():
            file_path = Path(connector.temp_dir) / filename
            file_path.write_text(content)
            mock_git_ops.files[str(file_path)] = content

        # Test with default config
        docs = connector.get_documents()
        assert len(docs) == 2  # Only .md and .txt files
        assert any(doc.metadata["file_name"] == "test1.md" for doc in docs)
        assert any(doc.metadata["file_name"] == "test2.txt" for doc in docs)

def test_cleanup(mock_config, mock_git_ops):
    """Test cleanup functionality."""
    connector = GitConnector(mock_config, mock_git_ops)
    with connector:
        temp_dir = connector.temp_dir
        assert os.path.exists(temp_dir)
    assert not os.path.exists(temp_dir)
    assert connector.temp_dir is None
