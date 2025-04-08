"""
Tests for Git connector file size handling.
"""
import os
import pytest
from pathlib import Path
from tests.utils import is_github_actions
from qdrant_loader.config import GitRepoConfig
from qdrant_loader.connectors.git import GitConnector

# Skip all tests in this file if running in GitHub Actions
pytestmark = pytest.mark.skipif(
    is_github_actions(),
    reason="Git repository tests are skipped in GitHub Actions"
)

@pytest.fixture(scope="function")
def git_config_with_size_limit():
    """Create a GitRepoConfig instance with specific size limits."""
    return GitRepoConfig(
        url=str(Path("./tests/fixtures/test-repo").absolute()),
        branch="main",
        file_types=["*.md"],
        include_paths=[],
        exclude_paths=[],
        max_file_size=1024  # 1KB for testing
    )

@pytest.fixture(scope="function")
def git_connector_with_size_limit(git_config_with_size_limit):
    """Create a GitConnector instance for testing file sizes."""
    connector = GitConnector(git_config_with_size_limit)
    yield connector
    # Cleanup temporary directory
    if connector.temp_dir and os.path.exists(connector.temp_dir):
        import shutil
        shutil.rmtree(connector.temp_dir)

@pytest.mark.integration
def test_size_limit_enforcement(git_connector_with_size_limit):
    """Test enforcement of file size limits."""
    with git_connector_with_size_limit:
        # Test cases with different file sizes
        test_cases = [
            ("small.md", 512, True),  # Half the limit
            ("at_limit.md", 1024, True),  # At the limit
            ("slightly_over.md", 1025, False),  # Just over the limit
            ("well_over.md", 2048, False),  # Double the limit
        ]
        
        for filename, size, should_process in test_cases:
            full_path = os.path.join(git_connector_with_size_limit.temp_dir, filename)
            
            # Create file with specified size
            with open(full_path, 'w') as f:
                f.write('x' * size)
            
            # Verify size handling
            assert git_connector_with_size_limit._should_process_file(full_path) == should_process, \
                f"File {filename} ({size} bytes) should{'' if should_process else ' not'} be processed"

@pytest.mark.integration
def test_large_file_handling(git_connector_with_size_limit):
    """Test handling of large files."""
    with git_connector_with_size_limit:
        # Create a large file
        large_file = os.path.join(git_connector_with_size_limit.temp_dir, "large.md")
        large_size = 10 * 1024  # 10KB
        
        with open(large_file, 'w') as f:
            f.write('x' * large_size)
        
        # Verify the file is not processed
        assert not git_connector_with_size_limit._should_process_file(large_file), \
            "Large file should not be processed"
        
        # Verify memory usage doesn't spike when checking large files
        import resource
        before_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        git_connector_with_size_limit._should_process_file(large_file)
        after_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        
        # Memory increase should be minimal (less than file size)
        assert (after_mem - before_mem) < large_size, \
            "Memory usage increased significantly when processing large file"

@pytest.mark.integration
def test_size_validation(git_connector_with_size_limit):
    """Test validation of various file sizes."""
    with git_connector_with_size_limit:
        # Test cases for edge cases
        test_cases = [
            ("empty.md", 0, True),  # Empty file
            ("tiny.md", 1, True),  # One byte
            ("small.md", 100, True),  # Small file
            ("edge_under.md", 1023, True),  # Just under limit
            ("edge_at.md", 1024, True),  # At limit
            ("edge_over.md", 1025, False),  # Just over limit
        ]
        
        for filename, size, should_process in test_cases:
            full_path = os.path.join(git_connector_with_size_limit.temp_dir, filename)
            
            # Create file with specified size
            with open(full_path, 'w') as f:
                f.write('x' * size)
            
            # Verify size handling
            assert git_connector_with_size_limit._should_process_file(full_path) == should_process, \
                f"File {filename} ({size} bytes) should{'' if should_process else ' not'} be processed"

@pytest.mark.integration
def test_error_handling(git_connector_with_size_limit):
    """Test error handling for file size operations."""
    with git_connector_with_size_limit:
        # Test non-existent file
        non_existent = os.path.join(git_connector_with_size_limit.temp_dir, "non_existent.md")
        assert not git_connector_with_size_limit._should_process_file(non_existent), \
            "Non-existent file should not be processed"
        
        # Test directory instead of file
        dir_path = os.path.join(git_connector_with_size_limit.temp_dir, "test_dir")
        os.makedirs(dir_path)
        assert not git_connector_with_size_limit._should_process_file(dir_path), \
            "Directory should not be processed"
        
        # Test unreadable file
        unreadable = os.path.join(git_connector_with_size_limit.temp_dir, "unreadable.md")
        with open(unreadable, 'w') as f:
            f.write("test content")
        os.chmod(unreadable, 0o000)  # Remove all permissions
        
        assert not git_connector_with_size_limit._should_process_file(unreadable), \
            "Unreadable file should not be processed"
        os.chmod(unreadable, 0o644)  # Restore permissions for cleanup 