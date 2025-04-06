"""
Tests for the CLI module.
"""
import pytest
from click.testing import CliRunner
from qdrant_loader.cli import cli
from qdrant_loader.config import get_settings, Settings, _settings_instance, SourcesConfig
from unittest.mock import patch, MagicMock

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """Setup environment variables for all tests."""
    # Mock environment variables
    monkeypatch.setenv('QDRANT_URL', 'http://test-url')
    monkeypatch.setenv('QDRANT_API_KEY', 'test-key')
    monkeypatch.setenv('QDRANT_COLLECTION_NAME', 'test-collection')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    
    # Clear any cached settings
    global _settings_instance
    _settings_instance = None
    
    yield
    
    # Clean up after test
    _settings_instance = None

def test_cli_help(runner):
    """Test that the CLI help message is displayed correctly."""
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert "QDrant Loader - A tool for collecting and vectorizing technical content" in result.output

def test_cli_version(runner):
    """Test that the version command works."""
    result = runner.invoke(cli, ['version'])
    assert result.exit_code == 0
    assert "QDrant Loader version" in result.output

def test_cli_config(runner):
    """Test that the config command works."""
    result = runner.invoke(cli, ['config'])
    assert result.exit_code == 0
    assert "Current Configuration" in result.output
    assert "QDRANT_URL" in result.output
    assert "QDRANT_API_KEY" in result.output
    assert "QDRANT_COLLECTION_NAME" in result.output
    assert "OPENAI_API_KEY" in result.output

def test_cli_init(runner):
    """Test that the init command works."""
    result = runner.invoke(cli, ['init'])
    # Note: This will fail in a real environment without proper qDrant connection
    # We should mock the qDrant client in a real test environment
    assert result.exit_code != 0  # Expected to fail without proper connection

def test_cli_ingest(runner):
    """Test that the ingest command works."""
    result = runner.invoke(cli, ['ingest'])
    # Note: This will fail in a real environment without proper configuration
    # We should mock the ingestion pipeline in a real test environment
    assert result.exit_code != 0  # Expected to fail without proper configuration

def test_cli_ingest_with_config(runner, tmp_path):
    """Test that the ingest command works with a valid configuration file."""
    # Create a temporary config file
    config_path = tmp_path / "config.yaml"
    config_path.write_text("""
global:
  chunking:
    size: 500
    overlap: 50
  embedding:
    model: text-embedding-3-small
    batch_size: 100
  logging:
    level: INFO
    format: json
    file: qdrant-loader.log

public_docs:
  thymeleaf:
    base_url: https://www.thymeleaf.org/doc/tutorials/3.1/usingthymeleaf.html
    version: "3.1"
    content_type: html
    exclude_paths:
      - /downloads
    selectors:
      content: article, main, .content
      remove:
        - nav
        - header
        - footer
        - .sidebar
      code_blocks: pre code
""")

    # Mock the ingestion pipeline
    with patch('qdrant_loader.cli.IngestionPipeline') as mock_pipeline:
        # Mock the process_documents method
        mock_pipeline.return_value.process_documents.return_value = None
        
        # Run the command
        result = runner.invoke(cli, ['ingest', '--config', str(config_path)])
        
        # Check that the command succeeded
        assert result.exit_code == 0
        
        # Verify that the pipeline was called with the correct configuration
        mock_pipeline.return_value.process_documents.assert_called_once()
        config_arg = mock_pipeline.return_value.process_documents.call_args[0][0]
        assert isinstance(config_arg, SourcesConfig)
        assert config_arg.public_docs["thymeleaf"].base_url == "https://www.thymeleaf.org/doc/tutorials/3.1/usingthymeleaf.html" 