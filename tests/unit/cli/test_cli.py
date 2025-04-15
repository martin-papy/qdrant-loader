"""
Tests for the CLI module.
"""
import asyncio
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from qdrant_loader.cli.cli import cli
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

@pytest.fixture
def runner(monkeypatch):
    """Create a CLI runner with the test environment."""
    # Set the current working directory to the project root
    monkeypatch.chdir(Path(__file__).parent.parent.parent.parent)
    
    # Create the runner
    runner = AsyncCliRunner()
    return runner

@pytest.fixture
def mock_pipeline(mocker):
    """Mock the IngestionPipeline class."""
    mock = mocker.MagicMock()
    mock.process_documents = AsyncMock(return_value=None)
    mocker.patch("qdrant_loader.cli.cli.IngestionPipeline", return_value=mock)
    return mock

@pytest.fixture
def mock_init_collection(mocker):
    """Mock the init_collection function."""
    mock = AsyncMock()
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
async def test_cli_init(runner, mock_init_collection):
    """Test the init command."""
    result = await runner.async_invoke(cli, ["init", "--config", "tests/config.test.yaml"])
    assert result.exit_code == 0
    mock_init_collection.assert_called_once()

@pytest.mark.asyncio
async def test_cli_init_with_force(runner, mock_init_collection):
    """Test the init command with force flag."""
    result = await runner.async_invoke(cli, ["init", "--force", "--config", "tests/config.test.yaml"])
    assert result.exit_code == 0
    mock_init_collection.assert_called_once()

@pytest.mark.asyncio
async def test_cli_init_with_config_path(runner, mock_init_collection):
    """Test the init command with config path."""
    # Setup mock init_collection
    mock_init_collection.return_value = None
    
    result = await runner.async_invoke(cli, ['init', '--config', "tests/config.test.yaml"])
    assert result.exit_code == 0, f"CLI failed with output: {result.output}"
    mock_init_collection.assert_called_once()

@pytest.mark.asyncio
async def test_cli_init_with_invalid_config(runner):
    """Test the init command with invalid config."""
    result = await runner.async_invoke(cli, ['init', '--config', 'nonexistent.yaml'])
    assert result.exit_code == 2
    assert "Invalid value for '--config': Path 'nonexistent.yaml' does not exist" in result.output

@pytest.mark.asyncio
async def test_cli_ingest_with_source_type(runner, mock_pipeline, mock_qdrant_manager):
    """Test the ingest command with source type."""
    # Setup mock pipeline
    mock_pipeline.process_documents = AsyncMock(return_value=None)
    
    # Setup mock QdrantManager
    mock_collections_response = MagicMock()
    mock_collection = MagicMock()
    mock_collection.name = "qdrant-loader-test"  # Match the expected collection name
    mock_collections_response.collections = [mock_collection]
    mock_qdrant_manager.client.get_collections.return_value = mock_collections_response
    
    # Patch both the QdrantManager class and the pipeline at the module level
    with patch("qdrant_loader.cli.cli.QdrantManager", return_value=mock_qdrant_manager), \
         patch("qdrant_loader.cli.cli.IngestionPipeline", return_value=mock_pipeline), \
         patch("qdrant_loader.config.get_settings") as mock_get_settings:
        # Mock the settings to return the expected collection name
        mock_settings = MagicMock()
        mock_settings.QDRANT_COLLECTION_NAME = "qdrant-loader-test"
        mock_get_settings.return_value = mock_settings
        
        result = await runner.async_invoke(cli, ['ingest', '--source-type', 'confluence', '--config', "tests/config.test.yaml"])
        assert result.exit_code == 0, f"CLI failed with output: {result.output}"
        mock_pipeline.process_documents.assert_awaited_once()
        mock_qdrant_manager.client.get_collections.assert_called_once()

@pytest.mark.asyncio
async def test_cli_ingest_with_source_type_and_name(runner, mock_pipeline, mock_qdrant_manager):
    """Test the ingest command with source type and name."""
    # Setup mock pipeline
    mock_pipeline.process_documents = AsyncMock(return_value=None)
    
    # Setup mock QdrantManager
    mock_collections_response = MagicMock()
    mock_collection = MagicMock()
    mock_collection.name = "qdrant-loader-test"  # Match the expected collection name
    mock_collections_response.collections = [mock_collection]
    mock_qdrant_manager.client.get_collections.return_value = mock_collections_response
    
    # Patch both the QdrantManager class and the pipeline at the module level
    with patch("qdrant_loader.cli.cli.QdrantManager", return_value=mock_qdrant_manager), \
         patch("qdrant_loader.cli.cli.IngestionPipeline", return_value=mock_pipeline), \
         patch("qdrant_loader.config.get_settings") as mock_get_settings:
        # Mock the settings to return the expected collection name
        mock_settings = MagicMock()
        mock_settings.QDRANT_COLLECTION_NAME = "qdrant-loader-test"
        mock_get_settings.return_value = mock_settings
        
        result = await runner.async_invoke(cli, ['ingest', '--source-type', 'confluence', '--source', 'space1', '--config', "tests/config.test.yaml"])
        assert result.exit_code == 0, f"CLI failed with output: {result.output}"
        mock_pipeline.process_documents.assert_awaited_once()
        mock_qdrant_manager.client.get_collections.assert_called_once()

@pytest.mark.asyncio
async def test_cli_ingest_without_settings(runner):
    """Test the ingest command without settings."""
    with patch('qdrant_loader.cli.cli.get_settings', return_value=None):
        result = await runner.async_invoke(cli, ['ingest', '--config', "tests/config.test.yaml"])
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
async def test_cli_ingest_with_source_without_type(runner):
    """Test the ingest command with source but no source type."""
    result = await runner.async_invoke(cli, ['ingest', '--source', 'space1', '--config', "tests/config.test.yaml"])
    assert result.exit_code == 1
    assert "Source name provided without source type" in result.output

@pytest.mark.asyncio
async def test_cli_ingest_with_processing_error(runner, mock_pipeline, mock_qdrant_manager, mock_collections_response):
    """Test the ingest command with processing error."""
    # Setup mock QdrantManager
    mock_qdrant_manager.client.get_collections.return_value = mock_collections_response
    
    # Setup mock pipeline with error
    mock_pipeline.process_documents = AsyncMock(side_effect=Exception("Processing failed"))

    result = await runner.async_invoke(cli, ['ingest', '--config', "tests/config.test.yaml"])
    assert result.exit_code == 1, f"CLI failed with output: {result.output}"
    assert "Failed to process documents: Processing failed" in result.output
    mock_pipeline.process_documents.assert_awaited_once()
    mock_qdrant_manager.client.get_collections.assert_called_once()

@pytest.mark.asyncio
async def test_cli_ingest_with_nonexistent_source(runner, mock_pipeline, mock_qdrant_manager, mock_collections_response):
    """Test the ingest command with nonexistent source."""
    # Setup mock QdrantManager
    mock_qdrant_manager.client.get_collections.return_value = mock_collections_response
    
    # Setup mock pipeline with error
    mock_pipeline.process_documents = AsyncMock(side_effect=ValueError("Source not found"))
   

    result = await runner.async_invoke(cli, ['ingest', '--source-type', 'confluence', '--source', 'nonexistent', '--config', "tests/config.test.yaml"])
    assert result.exit_code == 1, f"CLI failed with output: {result.output}"
    assert "Failed to process documents: Source not found" in result.output
    mock_pipeline.process_documents.assert_awaited_once()
    mock_qdrant_manager.client.get_collections.assert_called_once()

@pytest.mark.asyncio
async def test_cli_ingest_with_all_source_types(runner, mock_pipeline, mock_qdrant_manager, mock_collections_response):
    """Test the ingest command with all source types."""
    # Setup mock QdrantManager
    mock_qdrant_manager.client.get_collections.return_value = mock_collections_response
    
    result = await runner.async_invoke(cli, ['ingest', '--config', "tests/config.test.yaml"])
    assert result.exit_code == 0, f"CLI failed with output: {result.output}"
    mock_pipeline.process_documents.assert_awaited_once()
    mock_qdrant_manager.client.get_collections.assert_called_once()

@pytest.mark.asyncio
async def test_cli_ingest_with_verbose(runner, mock_pipeline, mock_qdrant_manager, mock_collections_response):
    """Test the ingest command with verbose flag."""
    # Setup mock QdrantManager
    mock_qdrant_manager.client.get_collections.return_value = mock_collections_response  

    result = await runner.async_invoke(cli, ['ingest', '--verbose', '--config', "tests/config.test.yaml"])
    assert result.exit_code == 0, f"CLI failed with output: {result.output}"
    mock_pipeline.process_documents.assert_awaited_once()
    mock_qdrant_manager.client.get_collections.assert_called_once()

@pytest.mark.asyncio
async def test_cli_ingest_with_log_level(runner, mock_pipeline, mock_qdrant_manager, mock_collections_response):
    """Test that the ingest command works with different log levels."""
    # Setup mock QdrantManager
    mock_qdrant_manager.client.get_collections.return_value = mock_collections_response
    
    result = await runner.async_invoke(cli, ['ingest', '--log-level', 'DEBUG', '--config', "tests/config.test.yaml"])
    assert result.exit_code == 0, f"CLI failed with output: {result.output}"
    mock_pipeline.process_documents.assert_awaited_once()
    mock_qdrant_manager.client.get_collections.assert_called_once()

@pytest.mark.asyncio
async def test_cli_init_without_settings(runner):
    """Test that the init command fails when settings are not available."""
    with patch('qdrant_loader.cli.cli.get_settings', return_value=None):
        result = await runner.async_invoke(cli, ['init', '--config', "tests/config.test.yaml"])
        assert result.exit_code == 1
        if is_github_actions():
            assert "No config file found" in result.output
        else:
            assert "Settings not available" in result.output

@pytest.mark.asyncio
async def test_cli_init_with_error(runner, mock_init_collection):
    """Test the init command with error."""
    mock_init_collection.side_effect = Exception("Failed to initialize")
    result = await runner.async_invoke(cli, ['init', '--config', "tests/config.test.yaml"])
    assert result.exit_code == 1
    assert "Failed to initialize collection" in result.output

@pytest.mark.asyncio
async def test_cli_ingest_pipeline_error(runner, mock_pipeline, mock_qdrant_manager):
    """Test that the ingest command handles pipeline errors."""
    # Setup mock QdrantManager
    mock_collections_response = MagicMock()
    mock_collection = MagicMock()
    mock_collection.name = "qdrant-loader-test"
    mock_collections_response.collections = [mock_collection]
    mock_qdrant_manager.client.get_collections.return_value = mock_collections_response
    
    # Setup mock pipeline with error
    mock_pipeline.process_documents = AsyncMock(side_effect=Exception("Pipeline error"))
    
    result = await runner.async_invoke(cli, ['ingest', '--config', "tests/config.test.yaml"])
    assert result.exit_code == 1
    assert "Failed to process documents: Pipeline error" in result.output

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

def test_cli_log_level_validation(runner):
    """Test that the log level validation works."""
    result = runner.invoke(cli, ['ingest', '--log-level', 'INVALID'])
    assert result.exit_code == 2
    assert "Invalid value for '--log-level'" in result.output

@pytest.mark.asyncio
async def test_cli_ingest_with_jira_source_type(runner, mock_pipeline, mock_qdrant_manager, mock_collections_response):
    """Test that the ingest command works with JIRA source type."""
    # Setup mock QdrantManager
    mock_qdrant_manager.client.get_collections.return_value = mock_collections_response
    
    result = await runner.async_invoke(cli, ['ingest', '--source-type', 'jira', '--config', "tests/config.test.yaml"])
    assert result.exit_code == 0, f"CLI failed with output: {result.output}"
    mock_pipeline.process_documents.assert_awaited_once()
    mock_qdrant_manager.client.get_collections.assert_called_once()

@pytest.mark.asyncio
async def test_cli_ingest_with_jira_source_type_and_name(runner, mock_pipeline, mock_qdrant_manager, mock_collections_response):
    """Test that the ingest command works with JIRA source type and name."""
    # Setup mock QdrantManager
    mock_qdrant_manager.client.get_collections.return_value = mock_collections_response
    
    result = await runner.async_invoke(cli, ['ingest', '--source-type', 'jira', '--source', 'project1', '--config', "tests/config.test.yaml"])
    assert result.exit_code == 0, f"CLI failed with output: {result.output}"
    mock_pipeline.process_documents.assert_awaited_once()
    mock_qdrant_manager.client.get_collections.assert_called_once()

@pytest.mark.asyncio
async def test_cli_ingest_with_explicit_config(runner, mock_pipeline, mock_qdrant_manager, mock_collections_response):
    """Test that the ingest command works with explicit config path."""
    # Setup mock QdrantManager
    mock_qdrant_manager.client.get_collections.return_value = mock_collections_response
    
    result = await runner.async_invoke(cli, ['ingest', '--config', "tests/config.test.yaml"])
    assert result.exit_code == 0, f"CLI failed with output: {result.output}"
    mock_pipeline.process_documents.assert_awaited_once()
    mock_qdrant_manager.client.get_collections.assert_called_once()

@pytest.mark.asyncio
async def test_cli_init_with_explicit_config(runner, mock_init_collection):
    """Test that the init command works with explicit config path."""
    result = await runner.async_invoke(cli, ['init', '--config', "tests/config.test.yaml"])
    assert result.exit_code == 0
    mock_init_collection.assert_awaited_once()

@pytest.mark.asyncio
async def test_cli_init_with_force_and_config(runner, mock_init_collection):
    """Test that the init command works with force flag and config path."""
    result = await runner.async_invoke(cli, ['init', '--force', '--config', "tests/config.test.yaml"])
    assert result.exit_code == 0
    mock_init_collection.assert_awaited_once_with(ANY, True)

@pytest.mark.asyncio
async def test_cli_init_with_connection_error(runner, mock_init_collection):
    """Test the init command with connection error."""
    mock_init_collection.side_effect = ConnectionError("Failed to connect")
    result = runner.invoke(cli, ['init', '--config', "tests/config.test.yaml"])
    assert result.exit_code == 1
    assert "Failed to initialize collection" in result.output

@pytest.mark.asyncio
async def test_cli_ingest_with_connection_error(runner, mock_qdrant_manager):
    """Test that the ingest command handles connection errors."""
    # Import the QdrantConnectionError class
    from qdrant_loader.core.qdrant_manager import QdrantConnectionError
    
    # Setup mock QdrantManager with connection error
    mock_qdrant_manager.client.get_collections = MagicMock(side_effect=QdrantConnectionError("Connection refused"))
    
    result = await runner.async_invoke(cli, ['ingest', '--config', "tests/config.test.yaml"])
    assert result.exit_code == 1, f"CLI failed with output: {result.output}"
    assert "Failed to connect to Qdrant: Connection refused" in result.output
    mock_qdrant_manager.client.get_collections.assert_called_once()

@pytest.mark.asyncio
async def test_cli_ingest_with_collection_not_found(runner, mock_qdrant_manager, mock_collections_response):
    """Test that the ingest command handles collection not found errors."""
    # Setup mock QdrantManager with empty collections
    mock_collections_response.collections = []  # Override to have no collections
    mock_qdrant_manager.client.get_collections.return_value = mock_collections_response
    
    # First patch the QdrantClient at the module level
    with patch('qdrant_loader.core.qdrant_manager.QdrantClient') as mock_client, \
         patch("qdrant_loader.cli.cli.QdrantManager", return_value=mock_qdrant_manager), \
         patch("qdrant_loader.cli.cli.IngestionPipeline") as mock_pipeline_cls, \
         patch("qdrant_loader.config.get_settings") as mock_get_settings:
        # Setup mock client
        mock_client_instance = MagicMock()
        mock_client_instance.get_collections.return_value = mock_collections_response
        mock_client.return_value = mock_client_instance
        
        # Mock the settings
        mock_settings = MagicMock()
        mock_settings.QDRANT_COLLECTION_NAME = "qdrant-loader-test"
        mock_get_settings.return_value = mock_settings
        
        # Setup mock pipeline
        mock_pipeline = MagicMock()
        mock_pipeline.process_documents = AsyncMock()
        mock_pipeline_cls.return_value = mock_pipeline
        
        result = await runner.async_invoke(cli, ['ingest', '--config', "tests/config.test.yaml"])
        assert result.exit_code == 1, f"CLI failed with output: {result.output}"
        assert "collection_not_found" in result.output
        assert "collection=qdrant-loader-test" in result.output 