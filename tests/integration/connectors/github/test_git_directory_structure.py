"""
Tests for Git connector directory structure handling.
"""
import os
import pytest
from pathlib import Path
from qdrant_loader.config import GitRepoConfig
from qdrant_loader.connectors.git import GitConnector

@pytest.fixture(scope="function")
def git_config_with_directories(test_settings):
    """Create a GitRepoConfig instance with specific directory settings."""
    # Get the first Git repo config from the test settings
    repo_key = next(iter(test_settings.sources_config.git_repos.keys()))
    base_config = test_settings.sources_config.git_repos[repo_key]
    
    return GitRepoConfig(
        url=base_config.url,
        branch=base_config.branch,
        file_types=base_config.file_types,
        include_paths=["/","src/", "docs/"],
        exclude_paths=["tests/"],
        max_file_size=base_config.max_file_size,
        auth=base_config.auth
    )

@pytest.fixture(scope="function")
def git_connector_with_directories(git_config_with_directories):
    """Create a GitConnector instance with specific directory settings."""
    connector = GitConnector(git_config_with_directories)
    yield connector
    # Cleanup temporary directory
    if connector.temp_dir and os.path.exists(connector.temp_dir):
        import shutil
        shutil.rmtree(connector.temp_dir)

@pytest.mark.integration
def test_nested_directory_handling(git_connector_with_directories):
    """Test handling of nested directories."""
    with git_connector_with_directories:
        # Test various nested directory structures
        test_dirs = [
            "src/nested/deep/path/",
            "docs/technical/specs/",
            "src/utils/helpers/"
        ]
        
        for dir_path in test_dirs:
            full_path = os.path.join(git_connector_with_directories.temp_dir, dir_path)
            os.makedirs(full_path, exist_ok=True)
            
            # Create a test file in each directory
            test_file = os.path.join(full_path, "test.md")
            with open(test_file, 'w') as f:
                f.write("test content")
            
            # Verify the file is processed
            assert git_connector_with_directories._should_process_file(test_file), \
                f"File in nested directory {dir_path} should be processed"

@pytest.mark.integration
def test_root_directory_handling(git_connector_with_directories):
    """Test handling of root directory files."""
    with git_connector_with_directories:
        # Test root directory files
        test_files = [
            "README.md",
            "src/root.md",
            "docs/index.md"
        ]
        
        for file_path in test_files:
            full_path = os.path.join(git_connector_with_directories.temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write("test content")
            
            # Verify the file is processed
            assert git_connector_with_directories._should_process_file(full_path), \
                f"Root directory file {file_path} should be processed"

@pytest.mark.integration
def test_directory_exclusion(git_connector_with_directories):
    """Test exclusion of specified directories."""
    with git_connector_with_directories:
        # Test excluded directories
        test_dirs = [
            "tests/",
            "tests/nested/",
            "tests/deep/path/"
        ]
        
        for dir_path in test_dirs:
            full_path = os.path.join(git_connector_with_directories.temp_dir, dir_path)
            os.makedirs(full_path, exist_ok=True)
            
            # Create a test file in each directory
            test_file = os.path.join(full_path, "test.md")
            with open(test_file, 'w') as f:
                f.write("test content")
            
            # Verify the file is not processed
            assert not git_connector_with_directories._should_process_file(test_file), \
                f"File in excluded directory {dir_path} should not be processed"

@pytest.mark.integration
def test_directory_inclusion(git_connector_with_directories):
    """Test inclusion of specified directories."""
    with git_connector_with_directories:
        # Test included directories
        test_dirs = [
            "src/",
            "docs/",
            "src/nested/",
            "docs/technical/"
        ]
        
        for dir_path in test_dirs:
            full_path = os.path.join(git_connector_with_directories.temp_dir, dir_path)
            os.makedirs(full_path, exist_ok=True)
            
            # Create a test file in each directory
            test_file = os.path.join(full_path, "test.md")
            with open(test_file, 'w') as f:
                f.write("test content")
            
            # Verify the file is processed
            assert git_connector_with_directories._should_process_file(test_file), \
                f"File in included directory {dir_path} should be processed"

@pytest.mark.integration
def test_directory_pattern_matching(git_connector_with_directories):
    """Test pattern matching for directory paths."""
    with git_connector_with_directories:
        # Test various directory patterns
        test_cases = [
            ("src/", True),
            ("docs/", True),
            ("tests/", False),
            ("src/nested/", True),
            ("docs/technical/", True),
            ("tests/nested/", False),
            ("other/", False),
            ("src/other/", True),  # Should be included as it's under src/
            ("docs/other/", True),  # Should be included as it's under docs/
        ]
        
        for dir_path, should_process in test_cases:
            full_path = os.path.join(git_connector_with_directories.temp_dir, dir_path)
            os.makedirs(full_path, exist_ok=True)
            
            # Create a test file in each directory
            test_file = os.path.join(full_path, "test.md")
            with open(test_file, 'w') as f:
                f.write("test content")
            
            # Verify the file is processed or not based on the pattern
            assert git_connector_with_directories._should_process_file(test_file) == should_process, \
                f"Directory {dir_path} should {'' if should_process else 'not'} be processed" 