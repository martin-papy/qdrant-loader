"""
Tests for the CLI module.
"""
import pytest
from click.testing import CliRunner
from qdrant_loader.cli.cli import cli
from qdrant_loader.config import Settings, _global_settings, initialize_config
from unittest.mock import patch, MagicMock, AsyncMock, ANY
import yaml
from pathlib import Path
import asyncio
from functools import wraps
import os
from tests.utils import is_github_actions

class AsyncCliRunner(CliRunner):
    """A CLI runner that supports async operations."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    async def async_invoke(self, cli, args=None, **kwargs):
        """Async version of invoke to handle async operations."""
        def sync_invoke():
            return self.invoke(cli, args, **kwargs)
            
        # Run the sync invoke in the event loop
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, sync_invoke)

@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """Setup environment variables for all tests."""
    # Mock environment variables
    monkeypatch.setenv('QDRANT_URL', 'https://test-url')
    monkeypatch.setenv('QDRANT_API_KEY', 'test-key')
    monkeypatch.setenv('QDRANT_COLLECTION_NAME', 'test-collection')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('CONFLUENCE_TOKEN', 'test-token')
    monkeypatch.setenv('CONFLUENCE_EMAIL', 'test@example.com')
    monkeypatch.setenv('JIRA_TOKEN', 'test-token')
    monkeypatch.setenv('JIRA_EMAIL', 'test@example.com')
    monkeypatch.setenv('GITHUB_TOKEN', 'test-token')
    monkeypatch.setenv('GITLAB_TOKEN', 'test-token')
    monkeypatch.setenv('BITBUCKET_TOKEN', 'test-token')
    monkeypatch.setenv('BITBUCKET_EMAIL', 'test@example.com')

    # Clear any cached settings
    global _global_settings
    _global_settings = None
    
    # Initialize settings with the test config file
    config_path = Path('tests/config.test.yaml')
    initialize_config(config_path)
    
    # Return the config path for use in tests
    return config_path

@pytest.fixture
def runner(monkeypatch, setup_env):
    """Create a CLI runner with the test environment."""
    # Set the current working directory to the project root
    monkeypatch.chdir(Path(__file__).parent.parent.parent.parent)
    
    # Create the runner
    runner = AsyncCliRunner()
    return runner

@pytest.fixture
def mock_pipeline(mocker):
    """Mock the IngestionPipeline."""
    mock = AsyncMock()
    mock.process_documents = AsyncMock()
    mock.process_documents.return_value = None
    mocker.patch("qdrant_loader.cli.cli.IngestionPipeline", return_value=mock)
    return mock

@pytest.fixture
def mock_init_collection(mocker):
    """Mock the init_collection function."""
    mock = AsyncMock()
    mock.return_value = None
    mocker.patch("qdrant_loader.cli.cli.init_collection", mock)
    return mock

@pytest.mark.asyncio
async def test_cli_help(runner):
    """Test that the CLI help message is displayed correctly."""
    result = await runner.async_invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert "QDrant Loader - A tool for collecting and vectorizing technical content" in result.output

@pytest.mark.asyncio
async def test_cli_version(runner):
    """Test that the version command works."""
    result = await runner.async_invoke(cli, ['version'])
    assert result.exit_code == 0
    assert "QDrant Loader version" in result.output

@pytest.mark.asyncio
async def test_cli_config(runner):
    """Test that the config command works."""
    result = await runner.async_invoke(cli, ['config'])
    assert result.exit_code == 0
    assert "Current Configuration" in result.output

@pytest.mark.asyncio
async def test_cli_init(runner, mock_init_collection, setup_env):
    """Test the init command."""
    result = await runner.async_invoke(cli, ["init", "--config", str(setup_env)])
    assert result.exit_code == 0
    mock_init_collection.assert_called_once()

@pytest.mark.asyncio
async def test_cli_init_with_force(runner, mock_init_collection, setup_env):
    """Test the init command with force flag."""
    result = await runner.async_invoke(cli, ["init", "--force", "--config", str(setup_env)])
    assert result.exit_code == 0
    mock_init_collection.assert_called_once()

@pytest.mark.asyncio
async def test_cli_init_with_config_path(runner, setup_env, mock_init_collection):
    """Test the init command with config path."""
    result = await runner.async_invoke(cli, ['init', '--config', str(setup_env)])
    assert result.exit_code == 0
    mock_init_collection.assert_called_once()

@pytest.mark.asyncio
async def test_cli_init_with_invalid_config(runner):
    """Test the init command with invalid config."""
    result = await runner.async_invoke(cli, ['init', '--config', 'nonexistent.yaml'])
    assert result.exit_code == 2
    assert "Invalid value for '--config': Path 'nonexistent.yaml' does not exist" in result.output

@pytest.mark.asyncio
async def test_cli_ingest_with_source_type(runner, setup_env, mock_pipeline):
    """Test the ingest command with source type."""
    result = await runner.async_invoke(cli, ['ingest', '--source-type', 'confluence', '--config', str(setup_env)])
    assert result.exit_code == 0
    mock_pipeline.process_documents.assert_called_once()

@pytest.mark.asyncio
async def test_cli_ingest_with_source_type_and_name(runner, setup_env, mock_pipeline):
    """Test the ingest command with source type and name."""
    result = await runner.async_invoke(cli, ['ingest', '--source-type', 'confluence', '--source', 'space1', '--config', str(setup_env)])
    assert result.exit_code == 0
    mock_pipeline.process_documents.assert_called_once()

@pytest.mark.asyncio
async def test_cli_ingest_without_settings(runner):
    """Test the ingest command without settings."""
    with patch('qdrant_loader.cli.cli.get_settings', return_value=None):
        result = await runner.async_invoke(cli, ['ingest'])
        assert result.exit_code == 1
        if is_github_actions():
            assert "No config file found" in result.output
        else:
            assert "Settings not available" in result.output

@pytest.mark.asyncio
async def test_cli_ingest_with_invalid_config(runner):
    """Test the ingest command with invalid config."""
    result = await runner.async_invoke(cli, ['ingest', '--config', 'nonexistent.yaml'])
    assert result.exit_code == 2
    assert "Invalid value for '--config': Path 'nonexistent.yaml' does not exist" in result.output

@pytest.mark.asyncio
async def test_cli_ingest_with_source_without_type(runner, setup_env):
    """Test the ingest command with source but no source type."""
    result = await runner.async_invoke(cli, ['ingest', '--source', 'space1', '--config', str(setup_env)])
    assert result.exit_code == 1
    assert "Source name provided without source type" in result.output

@pytest.mark.asyncio
async def test_cli_ingest_with_processing_error(runner, setup_env, mock_pipeline):
    """Test the ingest command with processing error."""
    mock_pipeline.process_documents.side_effect = Exception("Processing failed")
    result = await runner.async_invoke(cli, ['ingest', '--config', str(setup_env)])
    assert result.exit_code == 1
    assert "Failed to process documents" in result.output

@pytest.mark.asyncio
async def test_cli_ingest_with_nonexistent_source(runner, setup_env, mock_pipeline):
    """Test the ingest command with nonexistent source."""
    mock_pipeline.process_documents.side_effect = ValueError("Source not found")
    result = await runner.async_invoke(cli, ['ingest', '--source-type', 'confluence', '--source', 'nonexistent', '--config', str(setup_env)])
    assert result.exit_code == 1
    assert "Failed to process documents" in result.output

@pytest.mark.asyncio
async def test_cli_ingest_with_all_source_types(runner, setup_env, mock_pipeline):
    """Test the ingest command with all source types."""
    result = await runner.async_invoke(cli, ['ingest', '--config', str(setup_env)])
    assert result.exit_code == 0
    mock_pipeline.process_documents.assert_called_once()

@pytest.mark.asyncio
async def test_cli_ingest_with_verbose(runner, setup_env, mock_pipeline):
    """Test the ingest command with verbose flag."""
    result = await runner.async_invoke(cli, ['ingest', '--verbose', '--config', str(setup_env)])
    assert result.exit_code == 0
    mock_pipeline.process_documents.assert_called_once()

@pytest.mark.asyncio
async def test_cli_ingest_with_log_level(runner, setup_env, mock_pipeline):
    """Test that the ingest command works with different log levels."""
    result = await runner.async_invoke(cli, ['ingest', '--log-level', 'DEBUG', '--config', str(setup_env)])
    assert result.exit_code == 0
    mock_pipeline.process_documents.assert_called_once()

@pytest.mark.asyncio
async def test_cli_init_without_settings(runner):
    """Test that the init command fails when settings are not available."""
    with patch('qdrant_loader.cli.cli.get_settings', return_value=None):
        result = await runner.async_invoke(cli, ['init'])
        assert result.exit_code == 1
        if is_github_actions():
            assert "No config file found" in result.output
        else:
            assert "Settings not available" in result.output

@pytest.mark.asyncio
async def test_cli_init_with_error(runner, setup_env, mock_init_collection):
    """Test the init command with error."""
    mock_init_collection.side_effect = Exception("Failed to initialize")
    result = await runner.async_invoke(cli, ['init', '--config', str(setup_env)])
    assert result.exit_code == 1
    assert "Failed to initialize collection" in result.output

@pytest.mark.asyncio
async def test_cli_ingest_pipeline_error(runner, setup_env, mock_pipeline):
    """Test that the ingest command handles pipeline errors."""
    mock_pipeline.process_documents.side_effect = Exception("Pipeline error")
    result = await runner.async_invoke(cli, ['ingest', '--config', str(setup_env)])
    assert result.exit_code == 1
    assert "Failed to process documents" in result.output

@pytest.mark.asyncio
async def test_cli_config_without_settings(runner):
    """Test that the config command fails when settings are not available."""
    with patch('qdrant_loader.cli.cli.get_settings', return_value=None):
        result = await runner.async_invoke(cli, ['config'])
        assert result.exit_code == 1
        assert "Settings not available" in result.output

def test_cli_ingest_with_missing_config_file(runner):
    """Test that the ingest command uses default config path when not specified."""
    with patch('pathlib.Path.exists', return_value=False):
        result = runner.invoke(cli, ['ingest'])
        assert result.exit_code == 1
        assert "No config file found" in result.output
        assert "Please specify a config file or create config.yaml in the current directory" in result.output

def test_cli_log_level_validation(runner, setup_env, mock_pipeline):
    """Test that the log level validation works."""
    result = runner.invoke(cli, ['ingest', '--log-level', 'INVALID'])
    assert result.exit_code == 2
    assert "Invalid value for '--log-level'" in result.output

def test_cli_ingest_with_jira_source_type(runner, setup_env, mock_pipeline):
    """Test that the ingest command works with JIRA source type."""
    result = runner.invoke(cli, ['ingest', '--source-type', 'jira', '--config', str(setup_env)])
    assert result.exit_code == 0
    mock_pipeline.process_documents.assert_awaited_once_with(config=ANY, source_type='jira', source_name=None)

def test_cli_ingest_with_jira_source_type_and_name(runner, setup_env, mock_pipeline):
    """Test that the ingest command works with JIRA source type and name."""
    result = runner.invoke(cli, ['ingest', '--source-type', 'jira', '--source', 'project1', '--config', str(setup_env)])
    assert result.exit_code == 0
    mock_pipeline.process_documents.assert_awaited_once_with(
        config=ANY, source_type='jira', source_name='project1'
    )

def test_cli_ingest_with_explicit_config(runner, setup_env, mock_pipeline):
    """Test that the ingest command works with explicit config path."""
    result = runner.invoke(cli, ['ingest', '--config', str(setup_env)])
    assert result.exit_code == 0
    mock_pipeline.process_documents.assert_awaited_once()

def test_cli_init_with_explicit_config(runner, setup_env, mock_init_collection):
    """Test that the init command works with explicit config path."""
    result = runner.invoke(cli, ['init', '--config', str(setup_env)])
    assert result.exit_code == 0
    mock_init_collection.assert_awaited_once()

def test_cli_init_with_force_and_config(runner, setup_env, mock_init_collection):
    """Test that the init command works with force flag and config path."""
    result = runner.invoke(cli, ['init', '--force', '--config', str(setup_env)])
    assert result.exit_code == 0
    mock_init_collection.assert_awaited_once_with(ANY, True)

def test_cli_init_with_connection_error(runner, setup_env, mock_init_collection):
    """Test the init command with connection error."""
    mock_init_collection.side_effect = ConnectionError("Failed to connect")
    result = runner.invoke(cli, ['init', '--config', str(setup_env)])
    assert result.exit_code == 1
    assert "Failed to initialize collection" in result.output 