"""
Tests for Git file access operations.
"""
import os
import tempfile
import threading
import time
from pathlib import Path
import pytest
from git import Repo, GitCommandError
from tests.utils import is_github_actions

from qdrant_loader.config import GitRepoConfig
from qdrant_loader.connectors.git import GitConnector

# Skip all tests in this file if running in GitHub Actions
pytestmark = pytest.mark.skipif(
    is_github_actions(),
    reason="Git repository tests are skipped in GitHub Actions"
)

# Path to the test repository
TEST_REPO_PATH = Path(__file__).parent.parent.parent.parent / "fixtures" / "test-repo"

@pytest.fixture(scope="function")
def git_config():
    """Create a GitRepoConfig instance for testing."""
    return GitRepoConfig(
        url=str(TEST_REPO_PATH.absolute()),
        branch="main",
        depth=1,
        file_types=["*.md"],
        include_paths=["docs/", "src/"],
        exclude_paths=[".git/"],
        max_file_size=1024 * 1024  # 1MB
    )

@pytest.fixture(scope="function")
def git_connector(git_config):
    """Create a GitConnector instance for testing."""
    connector = GitConnector(git_config)
    yield connector
    # Cleanup temporary directory
    if connector.temp_dir and os.path.exists(connector.temp_dir):
        import shutil
        shutil.rmtree(connector.temp_dir)

@pytest.mark.integration
def test_file_read_permissions(git_connector):
    """Test file read permissions in the cloned repository."""
    with git_connector:
        # Create a test file with specific permissions
        test_file = os.path.join(git_connector.temp_dir, "test_permissions.md")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        # Test read access
        assert os.access(test_file, os.R_OK), "File should be readable"
        
        # Test file content reading
        with open(test_file, 'r') as f:
            content = f.read()
            assert content == "Test content", "File content should be readable"

@pytest.mark.integration
def test_file_locking_mechanism(git_connector):
    """Test file locking mechanism during concurrent access."""
    with git_connector:
        test_file = os.path.join(git_connector.temp_dir, "test_locking.md")
        
        def write_to_file(content):
            with open(test_file, 'w') as f:
                f.write(content)
                time.sleep(0.1)  # Simulate some processing time
        
        # Create multiple threads trying to write to the same file
        threads = []
        for i in range(3):
            thread = threading.Thread(target=write_to_file, args=(f"Content {i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify the final content
        with open(test_file, 'r') as f:
            content = f.read()
            assert content.startswith("Content "), "File should have been written by one of the threads"

@pytest.mark.integration
def test_concurrent_file_access(git_connector):
    """Test concurrent access to multiple files."""
    with git_connector:
        # Create multiple test files
        test_files = [
            os.path.join(git_connector.temp_dir, f"test_{i}.md")
            for i in range(3)
        ]
        
        def process_file(file_path, content):
            with open(file_path, 'w') as f:
                f.write(content)
                time.sleep(0.1)  # Simulate processing time
        
        # Create threads to process different files concurrently
        threads = []
        for i, file_path in enumerate(test_files):
            thread = threading.Thread(
                target=process_file,
                args=(file_path, f"Content for file {i}")
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all files were processed
        for i, file_path in enumerate(test_files):
            assert os.path.exists(file_path), f"File {file_path} should exist"
            with open(file_path, 'r') as f:
                content = f.read()
                assert content == f"Content for file {i}", f"File {file_path} should have correct content"

@pytest.mark.integration
def test_file_access_error_handling(git_connector):
    """Test error handling during file access operations."""
    with git_connector:
        # Test non-existent file
        non_existent_file = os.path.join(git_connector.temp_dir, "non_existent.md")
        with pytest.raises(FileNotFoundError):
            with open(non_existent_file, 'r') as f:
                f.read()
        
        # Test permission denied
        test_file = os.path.join(git_connector.temp_dir, "test_permissions.md")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        # Change file permissions to read-only
        os.chmod(test_file, 0o444)
        
        # Test write access
        with pytest.raises(PermissionError):
            with open(test_file, 'w') as f:
                f.write("New content")
        
        # Restore permissions
        os.chmod(test_file, 0o644) 