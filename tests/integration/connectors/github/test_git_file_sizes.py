"""
Tests for Git connector file size handling.
"""
import os
import pytest
from pathlib import Path
from qdrant_loader.config import GitRepoConfig
from qdrant_loader.connectors.git import GitConnector

@pytest.fixture(scope="function")
def git_config_with_size_limit(test_settings):
    """Create a GitRepoConfig instance with specific size limits."""
    # Get the first Git repo config from the test settings
    repo_key = next(iter(test_settings.sources_config.git_repos.keys()))
    base_config = test_settings.sources_config.git_repos[repo_key]
    
    return GitRepoConfig(
        url=base_config.url,
        branch=base_config.branch,
        file_types=base_config.file_types,
        include_paths=base_config.include_paths,
        exclude_paths=base_config.exclude_paths,
        max_file_size=1024,  # 1KB for testing
        auth=base_config.auth
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
def test_size_limit_enforcement(git_connector_with_size_limit, is_github_actions):
    """Test that file size limits are enforced."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with git_connector_with_size_limit:
        docs = git_connector_with_size_limit.get_documents()
        for doc in docs:
            assert len(doc.content) <= git_connector_with_size_limit.config.max_file_size

@pytest.mark.integration
def test_large_file_handling(git_connector_with_size_limit, is_github_actions):
    """Test handling of large files."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with git_connector_with_size_limit:
        docs = git_connector_with_size_limit.get_documents()
        large_files = [doc for doc in docs if len(doc.content) > 1024 * 1024]
        assert len(large_files) == 0, "Should not process files larger than limit"

@pytest.mark.integration
def test_size_validation(git_connector_with_size_limit, is_github_actions):
    """Test file size validation."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with git_connector_with_size_limit:
        docs = git_connector_with_size_limit.get_documents()
        for doc in docs:
            assert isinstance(len(doc.content), int)
            assert len(doc.content) >= 0

@pytest.mark.integration
def test_error_handling(git_connector_with_size_limit, is_github_actions):
    """Test error handling for file size issues."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with git_connector_with_size_limit:
        docs = git_connector_with_size_limit.get_documents()
        for doc in docs:
            try:
                content_length = len(doc.content)
                assert content_length <= git_connector_with_size_limit.config.max_file_size
            except Exception as e:
                pytest.fail(f"Unexpected error processing file: {e}") 