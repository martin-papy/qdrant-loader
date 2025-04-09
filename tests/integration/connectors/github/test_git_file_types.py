"""
Tests for Git connector file type filtering.
"""
import os
import pytest
from pathlib import Path
from qdrant_loader.config import GitRepoConfig
from qdrant_loader.connectors.git import GitConnector

@pytest.fixture(scope="function")
def git_config_with_file_types(test_settings):
    """Create a GitRepoConfig instance with specific file type settings."""
    # Get the first Git repo config from the test settings
    repo_key = next(iter(test_settings.sources_config.git_repos.keys()))
    base_config = test_settings.sources_config.git_repos[repo_key]
    
    return GitRepoConfig(
        url=base_config.url,
        branch=base_config.branch,
        file_types=["*.md", "*.txt"],
        include_paths=base_config.include_paths,
        exclude_paths=base_config.exclude_paths,
        max_file_size=base_config.max_file_size,
        auth=base_config.auth
    )

@pytest.fixture(scope="function")
def git_connector_with_file_types(git_config_with_file_types):
    """Create a GitConnector instance with specific file type settings."""
    connector = GitConnector(git_config_with_file_types)
    yield connector
    # Cleanup temporary directory
    if connector.temp_dir and os.path.exists(connector.temp_dir):
        import shutil
        shutil.rmtree(connector.temp_dir)

@pytest.mark.integration
def test_md_file_handling(git_connector_with_file_types):
    """Test handling of Markdown files."""
    with git_connector_with_file_types:
        # Test various MD files
        test_files = [
            "README.md",
            "src/test.md",
            "docs/README.md",
            "src/nested/deep/path/test.md"
        ]
        
        for file_path in test_files:
            full_path = os.path.join(git_connector_with_file_types.temp_dir, file_path)
            # Create the file and its parent directories
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write("test content")
            
            assert git_connector_with_file_types._should_process_file(full_path), \
                f"MD file {file_path} should be processed"

@pytest.mark.integration
def test_txt_file_handling(git_connector_with_file_types):
    """Test handling of text files."""
    with git_connector_with_file_types:
        # Create and test TXT files
        test_files = [
            "src/test.txt",
            "docs/notes.txt",
            "src/nested/deep/path/readme.txt"
        ]
        
        for file_path in test_files:
            full_path = os.path.join(git_connector_with_file_types.temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write("test content")
            
            assert git_connector_with_file_types._should_process_file(full_path), \
                f"TXT file {file_path} should be processed"

@pytest.mark.integration
def test_file_type_exclusion(git_connector_with_file_types):
    """Test exclusion of unsupported file types."""
    with git_connector_with_file_types:
        # Test various unsupported file types
        test_files = [
            "src/test.py",
            "docs/config.json",
            "src/nested/deep/path/data.csv"
        ]
        
        for file_path in test_files:
            full_path = os.path.join(git_connector_with_file_types.temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write("test content")
            
            assert not git_connector_with_file_types._should_process_file(full_path), \
                f"Unsupported file {file_path} should not be processed"

@pytest.mark.integration
def test_file_type_validation(git_connector_with_file_types):
    """Test validation of file type patterns."""
    with git_connector_with_file_types:
        # Test various file patterns
        test_cases = [
            ("test.md", True),
            ("test.txt", True),
            ("test.MD", True),  # Case insensitive
            ("test.TXT", True),  # Case insensitive
            ("test.md.bak", False),  # Not exact match
            ("test.txt~", False),  # Not exact match
            (".md", False),  # Invalid pattern
            ("md", False),  # Invalid pattern
        ]
        
        for filename, should_process in test_cases:
            full_path = os.path.join(git_connector_with_file_types.temp_dir, filename)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write("test content")
            
            assert git_connector_with_file_types._should_process_file(full_path) == should_process, \
                f"File {filename} should {'' if should_process else 'not'} be processed" 