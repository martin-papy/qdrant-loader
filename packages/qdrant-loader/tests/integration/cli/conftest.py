"""CLI Integration Test Configuration.

This module provides fixtures and utilities for testing CLI commands
in isolated environments with temporary workspaces.
"""

import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from qdrant_loader.cli import create_cli


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
    """Provide a temporary workspace directory for CLI tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir) / "test_workspace"
        workspace_path.mkdir(parents=True, exist_ok=True)
        yield workspace_path


@pytest.fixture
def sample_config_yaml() -> str:
    """Provide a sample configuration YAML for testing."""
    return """
qdrant:
  host: "localhost"
  port: 6333
  collection_name: "test_collection"
  vector_size: 384
  distance: "Cosine"

neo4j:
  uri: "bolt://localhost:7687"
  username: "neo4j" 
  password: "test_password"
  database: "test_db"

embedding:
  api_key: "test-key"
  model: "text-embedding-ada-002"
"""


@pytest.fixture
def sample_env_file() -> str:
    """Provide a sample .env file content for testing."""
    return """
# Test environment variables
QDRANT_API_KEY=test-qdrant-key
NEO4J_PASSWORD=test-password
OPENAI_API_KEY=test-openai-key
ANTHROPIC_API_KEY=test-anthropic-key
"""


@pytest.fixture
def workspace_with_config(temp_workspace: Path, sample_config_yaml: str, sample_env_file: str) -> Path:
    """Set up a workspace with configuration files."""
    # Create workspace structure
    config_dir = temp_workspace / "config"
    data_dir = temp_workspace / "data"
    logs_dir = temp_workspace / "logs"
    
    config_dir.mkdir()
    data_dir.mkdir()
    logs_dir.mkdir()
    
    # Create config files
    config_file = config_dir / "config.yaml"
    config_file.write_text(sample_config_yaml)
    
    env_file = temp_workspace / ".env"
    env_file.write_text(sample_env_file)
    
    return temp_workspace


@pytest.fixture
def sample_document_file(temp_workspace: Path) -> Path:
    """Create a sample document file for ingestion testing."""
    docs_dir = temp_workspace / "documents"
    docs_dir.mkdir(exist_ok=True)
    
    doc_file = docs_dir / "sample.txt"
    doc_file.write_text("""
This is a sample document for testing CLI ingestion functionality.
It contains multiple lines of text that should be processed by the loader.
The document has sufficient content to test text chunking and embedding.
""")
    
    return doc_file


@pytest.fixture
def cli_app():
    """Provide the CLI application for testing."""
    return create_cli()


@pytest.fixture
def mock_external_services():
    """Mock external services to prevent actual network calls during CLI tests."""
    with patch('qdrant_loader.core.managers.qdrant_manager.QdrantManager') as mock_qdrant, \
         patch('qdrant_loader.core.managers.neo4j_manager.Neo4jManager') as mock_neo4j, \
         patch('qdrant_loader.utils.version_check.check_version_async') as mock_version_check:
        
        # Configure Qdrant manager mock
        mock_qdrant_instance = mock_qdrant.return_value
        mock_qdrant_instance.health_check.return_value = True
        mock_qdrant_instance.create_collection.return_value = True
        mock_qdrant_instance.upsert_points.return_value = True
        
        # Configure Neo4j manager mock
        mock_neo4j_instance = mock_neo4j.return_value
        mock_neo4j_instance.health_check.return_value = True
        mock_neo4j_instance.test_connection.return_value = True
        
        # Configure version check mock
        mock_version_check.return_value = None
        
        yield {
            'qdrant': mock_qdrant,
            'neo4j': mock_neo4j,
            'version_check': mock_version_check
        }


@pytest.fixture
def isolated_environment():
    """Provide an isolated environment for CLI tests."""
    # Store original environment
    original_env = dict(os.environ)
    
    try:
        # Clear potentially conflicting environment variables
        env_vars_to_clear = [
            'QDRANT_HOST', 'QDRANT_PORT', 'QDRANT_API_KEY',
            'NEO4J_URI', 'NEO4J_USERNAME', 'NEO4J_PASSWORD',
            'OPENAI_API_KEY', 'ANTHROPIC_API_KEY'
        ]
        
        for var in env_vars_to_clear:
            os.environ.pop(var, None)
            
        yield
        
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env) 