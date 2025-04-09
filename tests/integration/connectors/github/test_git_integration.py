"""
Tests for the Git integration.
"""
import os
import tempfile
from datetime import datetime, UTC
from pathlib import Path
from typing import List
import pytest
from git import Repo
from git.exc import GitCommandError
from dotenv import load_dotenv
import yaml
from qdrant_loader.config import GitRepoConfig, Settings, GitAuthConfig, SourcesConfig, initialize_config, get_settings
from qdrant_loader.connectors.git import GitConnector, GitOperations, GitPythonAdapter
from qdrant_loader.core.document import Document

# Load test environment variables
load_dotenv(Path(__file__).parent.parent.parent / ".env.test")

@pytest.fixture(scope="session")
def test_settings():
    """Load test settings from environment variables and config file."""
    # Load sources config from YAML
    config_path = Path(__file__).parent.parent.parent.parent / "config.test.yaml"
    # Initialize global settings
    initialize_config(config_path)
    # Return the initialized settings
    return get_settings()

@pytest.fixture(scope="function")
def git_config(test_settings):
    """Create a GitRepoConfig instance with test settings."""
    # Get the first Git repo config from the test settings
    repo_key = next(iter(test_settings.sources_config.git_repos.keys()))
    return test_settings.sources_config.git_repos[repo_key]

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
def test_git_connector_init(git_config):
    """Test GitConnector initialization with real settings."""
    connector = GitConnector(git_config)
    assert connector.config == git_config
    assert connector.temp_dir is None
    assert connector.logger is not None
    assert connector.metadata_extractor is not None

@pytest.mark.integration
def test_git_connector_context_manager(git_config):
    """Test GitConnector context manager with real repository."""
    with GitConnector(git_config) as connector:
        assert connector.temp_dir is not None
        assert os.path.exists(connector.temp_dir)
        assert os.path.exists(os.path.join(connector.temp_dir, '.git'))

@pytest.mark.integration
def test_git_connector_cleanup(git_config):
    """Test GitConnector cleanup with real repository."""
    temp_dir = None
    with GitConnector(git_config) as connector:
        temp_dir = connector.temp_dir
        assert os.path.exists(temp_dir)
    assert not os.path.exists(temp_dir)

@pytest.mark.integration
def test_should_process_file(git_connector):
    """Test GitConnector _should_process_file method with real files."""
    with git_connector:
        # Create test files in the temporary directory
        test_files = [
            (".git/config", False),  # Should be excluded
            ("src/main/test.md", True),  # Should be included
            ("src/test/test.md", False),  # Should be excluded
            ("docs/README.md", True),  # Should be included
            ("large_file.md", False)  # Should be excluded if too large
        ]

        for file_path, should_process in test_files:
            full_path = os.path.join(git_connector.temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write("test content")
            
            # Set file size for large_file.md
            if file_path == "large_file.md":
                with open(full_path, 'w') as f:
                    f.write("x" * (git_connector.config.max_file_size + 1))
            
            assert git_connector._should_process_file(full_path) == should_process

@pytest.mark.integration
def test_process_file(git_connector):
    """Test GitConnector _process_file method with real files."""
    with git_connector:
        # Create a test file
        file_path = os.path.join(git_connector.temp_dir, "src", "main", "test.md")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        content = "# Test Document\n\n## Section 1\nTest content\n\n## Section 2\nMore test content"
        with open(file_path, 'w') as f:
            f.write(content)
        
        # Initialize git repo and commit the file
        repo = Repo(git_connector.temp_dir)
        repo.index.add([os.path.relpath(file_path, git_connector.temp_dir)])
        repo.index.commit("Add test file")
        
        # Process the file
        doc = git_connector._process_file(file_path)
        assert isinstance(doc, Document)
        assert doc.content == content
        assert "repository_url" in doc.metadata
        assert doc.source == doc.metadata["repository_url"]
        assert doc.source_type == "git"

@pytest.mark.integration
def test_get_documents(git_connector):
    """Test GitConnector get_documents method with real repository."""
    with git_connector:
        # Get documents
        docs = git_connector.get_documents()
        
        # Verify results
        assert len(docs) >= 1  # At least the README.md should be processed
        readme_doc = next((doc for doc in docs if doc.metadata["file_name"] == "README.md"), None)
        assert readme_doc is not None, "README.md was not found in the processed documents"
        
        # Verify document structure
        assert isinstance(readme_doc, Document)
        assert readme_doc.content  # Should have content
        assert "repository_url" in readme_doc.metadata
        assert readme_doc.source == readme_doc.metadata["repository_url"]
        assert readme_doc.source_type == "git"
        assert "created_at" in readme_doc.metadata

@pytest.mark.integration
def test_error_handling(git_config):
    """Test error handling with invalid repository URL."""
    invalid_config = GitRepoConfig(
        url="https://github.com/invalid/repo.git",
        branch=git_config.branch,
        depth=git_config.depth,
        file_types=git_config.file_types,
        include_paths=git_config.include_paths,
        exclude_paths=git_config.exclude_paths,
        max_file_size=git_config.max_file_size
    )
    
    with pytest.raises(RuntimeError):
        with GitConnector(invalid_config) as connector:
            connector.get_documents()
