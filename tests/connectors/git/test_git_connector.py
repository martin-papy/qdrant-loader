import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import tempfile
from pathlib import Path
from git import GitCommandError
from qdrant_loader.connectors.git import GitConnector, GitOperations
from qdrant_loader.config import GitRepoConfig, GitAuthConfig
from qdrant_loader.core.document import Document

class MockGitOperations(GitOperations):
    def __init__(self):
        self.repo = None
        self.cloned = False
        self.files = {}

    def clone(self, url: str, to_path: str, branch: str, depth: int) -> None:
        self.cloned = True
        self.repo = MagicMock()
        self.repo.working_dir = to_path

    def get_file_content(self, file_path: str) -> str:
        if not self.cloned:
            raise RuntimeError("Repository not initialized")
        return self.files.get(file_path, "")

    def get_last_commit_date(self) -> str:
        if not self.cloned:
            raise RuntimeError("Repository not initialized")
        return "2024-01-01 12:00:00 +0000"

    def list_files(self, path: str) -> list[str]:
        if not self.cloned:
            raise RuntimeError("Repository not initialized")
        return [f for f in self.files.keys() if f.startswith(path)]

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

def test_should_process_file(mock_config):
    connector = GitConnector(mock_config)
    
    # Test file size limit
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"x" * (mock_config.max_file_size + 1))
        f.flush()
        assert not connector._should_process_file(f.name)
    
    # Test file type
    with tempfile.NamedTemporaryFile(suffix=".md") as f:
        assert connector._should_process_file(f.name)
    with tempfile.NamedTemporaryFile(suffix=".py") as f:
        assert not connector._should_process_file(f.name)
    
    # Test include/exclude paths
    with tempfile.NamedTemporaryFile(suffix=".md") as f:
        mock_config.include_paths = ["docs/**"]
        assert not connector._should_process_file(f.name)
        
        mock_config.include_paths = ["**/*"]
        mock_config.exclude_paths = ["docs/**"]
        assert connector._should_process_file(f.name)

def test_clone_repository(mock_config, mock_git_ops):
    connector = GitConnector(mock_config, mock_git_ops)
    
    # Create a temporary directory for the test
    with tempfile.TemporaryDirectory() as temp_dir:
        connector.temp_dir = temp_dir
        connector._clone_repository()
        
        assert mock_git_ops.cloned
        assert connector.temp_dir == temp_dir
        assert os.path.exists(temp_dir)

def test_process_file(mock_config, mock_git_ops):
    connector = GitConnector(mock_config, mock_git_ops)
    
    # Create a temporary directory and test file
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test.md"
        test_file.write_text("Test content")
        mock_git_ops.files[str(test_file)] = "Test content"
        
        connector.temp_dir = temp_dir
        mock_git_ops.clone("", temp_dir, "", 1)  # Initialize the mock repo
        
        doc = connector._process_file(str(test_file))
        
        assert isinstance(doc, Document)
        assert doc.content == "Test content"
        assert doc.source == mock_config.url
        assert doc.source_type == "git"
        assert doc.project == "repo"
        assert "file_path" in doc.metadata
        assert "branch" in doc.metadata
        assert "file_size" in doc.metadata
        assert "last_commit_date" in doc.metadata

def test_get_documents(mock_config, mock_git_ops):
    connector = GitConnector(mock_config, mock_git_ops)

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test files
        test_files = {
            "test1.md": "Content 1",
            "test2.txt": "Content 2",
            "test3.py": "Content 3"
        }

        for filename, content in test_files.items():
            file_path = Path(temp_dir) / filename
            file_path.write_text(content)
            mock_git_ops.files[str(file_path)] = content

        connector.temp_dir = temp_dir
        mock_git_ops.clone("", temp_dir, "", 1)  # Initialize the mock repo

        # Test with default config
        print(f"Files in mock_git_ops: {mock_git_ops.files}")
        files = mock_git_ops.list_files(temp_dir)
        print(f"Files from list_files: {files}")
        docs = connector.get_documents()
        print(f"Documents: {docs}")
        print(f"Files that passed _should_process_file:")
        for file_path in files:
            print(f"  {file_path}: {connector._should_process_file(file_path)}")

        assert len(docs) == 2  # Only .md and .txt files
        assert all(doc.source_type == "git" for doc in docs)
        assert all(doc.source == mock_config.url for doc in docs)

        # Test with custom file types
        mock_config.file_types = ["*.py"]
        connector = GitConnector(mock_config, mock_git_ops)
        connector.temp_dir = temp_dir
        docs = connector.get_documents()

        assert len(docs) == 1
        assert docs[0].content == "Content 3"

def test_cleanup(mock_config, mock_git_ops):
    connector = GitConnector(mock_config, mock_git_ops)
    temp_dir = tempfile.mkdtemp()
    connector.temp_dir = temp_dir
    
    assert os.path.exists(connector.temp_dir)
    connector.cleanup()
    assert not os.path.exists(temp_dir)
    assert connector.temp_dir is None
    assert connector.repo is None