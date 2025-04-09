"""
Tests for the CLI module.
"""
import pytest
from click.testing import CliRunner
from qdrant_loader.cli import cli
from qdrant_loader.config import get_settings, Settings, _global_settings, SourcesConfig, initialize_config
from unittest.mock import patch, MagicMock
import yaml
from pathlib import Path

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture(autouse=True)
def setup_env(monkeypatch, tmp_path):
    """Setup environment variables for all tests."""
    # Mock environment variables
    monkeypatch.setenv('QDRANT_URL', 'http://test-url')
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
    monkeypatch.setenv('AUTH_TEST_REPO_TOKEN', 'test-token')
    monkeypatch.setenv('OPENAI_ORGANIZATION', 'test-org')
    
    # Clear any cached settings
    global _global_settings
    _global_settings = None
    
    # Create a mock config file
    config_path = tmp_path / "test_config.yaml"
    config_data = {
        "global": {
            "chunking": {"size": 500, "overlap": 50},
            "embedding": {"model": "text-embedding-3-small", "batch_size": 100},
            "logging": {"level": "INFO", "format": "json", "file": "qdrant-loader.log"}
        },
        "sources": {
            "confluence": {
                "space1": {
                    "url": "https://test.atlassian.net/wiki",
                    "space_key": "SPACE1",
                    "content_types": ["page", "blogpost"],
                    "token": "test-token",
                    "email": "test@example.com"
                }
            },
            "git_repos": {
                "repo1": {
                    "url": "https://github.com/test/repo1",
                    "branch": "main",
                    "include_paths": ["docs/**/*"],
                    "exclude_paths": ["docs/drafts/**/*"]
                }
            },
            "public_docs": {
                "docs1": {
                    "base_url": "https://docs.example.com",
                    "version": "1.0",
                    "content_type": "html",
                    "exclude_paths": ["/downloads"],
                    "selectors": {
                        "content": "article",
                        "remove": ["nav", "header", "footer"]
                    }
                }
            }
        }
    }
    config_path.write_text(yaml.dump(config_data))
    
    # Initialize settings with the mock config
    initialize_config(config_path)
    
    yield
    
    # Clean up after test
    _global_settings = None

@pytest.fixture
def mock_config_file(tmp_path):
    """Create a mock configuration file with all source types."""
    config_path = tmp_path / "config.yaml"
    config_data = {
        "global": {
            "chunking": {"size": 500, "overlap": 50},
            "embedding": {"model": "text-embedding-3-small", "batch_size": 100},
            "logging": {"level": "INFO", "format": "json", "file": "qdrant-loader.log"}
        },
        "sources": {
            "confluence": {
                "space1": {
                    "url": "https://test.atlassian.net/wiki",
                    "space_key": "SPACE1",
                    "content_types": ["page", "blogpost"],
                    "token": "test-token",
                    "email": "test@example.com"
                }
            },
            "git_repos": {
                "repo1": {
                    "url": "https://github.com/test/repo1",
                    "branch": "main",
                    "include_paths": ["docs/**/*"],
                    "exclude_paths": ["docs/drafts/**/*"]
                }
            },
            "public_docs": {
                "docs1": {
                    "base_url": "https://docs.example.com",
                    "version": "1.0",
                    "content_type": "html",
                    "exclude_paths": ["/downloads"],
                    "selectors": {
                        "content": "article",
                        "remove": ["nav", "header", "footer"]
                    }
                }
            },
            "jira": {
                "project1": {
                    "base_url": "https://test.atlassian.net/jira",
                    "project_key": "PROJ1",
                    "issue_types": ["Documentation", "Technical Spec"],
                    "include_statuses": ["Done", "Approved"],
                    "token": "test-token",
                    "email": "test@example.com"
                }
            }
        }
    }
    config_path.write_text(yaml.dump(config_data))
    return config_path

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

def test_cli_ingest_with_source_type(runner, mock_config_file):
    """Test that the ingest command works with source type filtering."""
    with patch('qdrant_loader.cli.IngestionPipeline') as mock_pipeline, \
         patch('qdrant_loader.cli.asyncio.run') as mock_run:
        # Mock the process_documents method
        mock_pipeline.return_value.process_documents.return_value = None
        mock_run.return_value = None
        
        # Test with confluence source type
        result = runner.invoke(cli, ['ingest', '--config', str(mock_config_file), '--source-type', 'confluence'])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        args = mock_pipeline.return_value.process_documents.call_args[1]
        assert args['source_type'] == 'confluence'
        assert args['source_name'] is None

def test_cli_ingest_with_source_type_and_name(runner, mock_config_file):
    """Test that the ingest command works with both source type and name."""
    with patch('qdrant_loader.cli.IngestionPipeline') as mock_pipeline, \
         patch('qdrant_loader.cli.asyncio.run') as mock_run:
        # Mock the process_documents method
        mock_pipeline.return_value.process_documents.return_value = None
        mock_run.return_value = None
        
        # Test with specific confluence space
        result = runner.invoke(cli, ['ingest', '--config', str(mock_config_file), 
                                   '--source-type', 'confluence', '--source', 'space1'])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        args = mock_pipeline.return_value.process_documents.call_args[1]
        assert args['source_type'] == 'confluence'
        assert args['source_name'] == 'space1'

def test_cli_ingest_with_invalid_source_type(runner, mock_config_file):
    """Test that the ingest command fails with invalid source type."""
    result = runner.invoke(cli, ['ingest', '--config', str(mock_config_file), '--source-type', 'invalid'])
    assert result.exit_code != 0
    assert "Invalid value for '--source-type'" in result.output

def test_cli_ingest_with_source_but_no_type(runner, mock_config_file):
    """Test that the ingest command fails when source is provided without source type."""
    result = runner.invoke(cli, ['ingest', '--config', str(mock_config_file), '--source', 'space1'])
    assert result.exit_code != 0
    assert "--source-type must be specified when using --source" in result.output

def test_cli_ingest_with_nonexistent_source(runner, mock_config_file):
    """Test that the ingest command handles nonexistent source names gracefully."""
    with patch('qdrant_loader.cli.IngestionPipeline') as mock_pipeline, \
         patch('qdrant_loader.cli.asyncio.run') as mock_run:
        # Mock the process_documents method
        mock_pipeline.return_value.process_documents.return_value = None
        mock_run.return_value = None
        
        # Test with nonexistent source
        result = runner.invoke(cli, ['ingest', '--config', str(mock_config_file),
                                   '--source-type', 'confluence', '--source', 'nonexistent'])
        assert result.exit_code == 0
        mock_run.assert_called_once()

def test_cli_ingest_with_all_source_types(runner, mock_config_file):
    """Test that the ingest command works with all source types."""
    with patch('qdrant_loader.cli.IngestionPipeline') as mock_pipeline, \
         patch('qdrant_loader.cli.asyncio.run') as mock_run:
        # Mock the process_documents method
        mock_pipeline.return_value.process_documents.return_value = None
        mock_run.return_value = None
        
        # Test with all source types
        result = runner.invoke(cli, ['ingest', '--config', str(mock_config_file)])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        args = mock_pipeline.return_value.process_documents.call_args[1]
        assert args['source_type'] is None
        assert args['source_name'] is None

def test_cli_ingest_with_verbose(runner, mock_config_file):
    """Test that the ingest command works with verbose output."""
    with patch('qdrant_loader.cli.IngestionPipeline') as mock_pipeline, \
         patch('qdrant_loader.cli.asyncio.run') as mock_run, \
         patch('qdrant_loader.cli.logger') as mock_logger:
        # Mock the process_documents method
        mock_pipeline.return_value.process_documents.return_value = None
        mock_run.return_value = None
        
        # Test with verbose flag (must be before the command)
        result = runner.invoke(cli, ['--verbose', 'ingest', '--config', str(mock_config_file)])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        
        # Verify that the logger was called with the verbose message
        mock_logger.info.assert_any_call("Verbose mode enabled")

def test_cli_ingest_with_log_level(runner, mock_config_file):
    """Test that the ingest command works with different log levels."""
    with patch('qdrant_loader.cli.IngestionPipeline') as mock_pipeline, \
         patch('qdrant_loader.cli.asyncio.run') as mock_run:
        # Mock the process_documents method
        mock_pipeline.return_value.process_documents.return_value = None
        mock_run.return_value = None
        
        # Test with different log levels (must be before the command)
        for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            result = runner.invoke(cli, ['--log-level', level, 'ingest', '--config', str(mock_config_file)])
            assert result.exit_code == 0
            mock_run.assert_called_once()
            mock_run.reset_mock()

def test_cli_init_with_force(runner):
    """Test that the init command works with force flag."""
    with patch('qdrant_loader.cli.init_collection') as mock_init, \
         patch('qdrant_loader.cli.get_settings', return_value=Settings()):
        result = runner.invoke(cli, ['init', '--force'])
        assert result.exit_code == 0
        mock_init.assert_called_once()
        assert "Force reinitialization requested" in result.output

def test_cli_init_without_settings(runner):
    """Test that the init command fails when settings are not available."""
    with patch('qdrant_loader.cli.get_settings', return_value=None):
        result = runner.invoke(cli, ['init'])
        assert result.exit_code != 0
        assert "Settings not available. Please check your environment variables." in str(result.output)

def test_cli_init_with_error(runner):
    """Test that the init command handles errors gracefully."""
    with patch('qdrant_loader.cli.init_collection', side_effect=Exception("Test error")):
        result = runner.invoke(cli, ['init'])
        assert result.exit_code != 0
        assert "Failed to initialize collection: Test error" in str(result.output)

def test_cli_ingest_without_settings(runner, mock_config_file):
    """Test that the ingest command fails when settings are not available."""
    with patch('qdrant_loader.cli.get_settings', return_value=None):
        result = runner.invoke(cli, ['ingest', '--config', str(mock_config_file)])
        assert result.exit_code != 0
        assert "Settings not available. Please check your environment variables." in str(result.output)

def test_cli_ingest_with_nonexistent_config(runner):
    """Test that the ingest command fails with nonexistent config file."""
    result = runner.invoke(cli, ['ingest', '--config', 'nonexistent.yaml'])
    assert result.exit_code != 0
    assert "Invalid value for '--config'" in result.output
    assert "Path 'nonexistent.yaml' does not exist" in result.output

def test_cli_ingest_with_invalid_config(runner, tmp_path):
    """Test that the ingest command fails with invalid config file."""
    config_path = tmp_path / "invalid_config.yaml"
    config_path.write_text("invalid: yaml: content")

    result = runner.invoke(cli, ['ingest', '--config', str(config_path)])
    assert result.exit_code != 0
    assert "Failed to load configuration:" in str(result.output)

def test_cli_ingest_pipeline_error(runner, mock_config_file):
    """Test that the ingest command handles pipeline errors correctly."""
    with patch('qdrant_loader.cli.IngestionPipeline') as mock_pipeline, \
         patch('qdrant_loader.cli.asyncio.run') as mock_run:
        # Mock the process_documents method to raise an exception
        mock_pipeline.return_value.process_documents.side_effect = Exception("Test error")
        mock_run.side_effect = Exception("Test error")
        
        # Test error handling
        result = runner.invoke(cli, ['ingest', '--config', str(mock_config_file)])
        assert result.exit_code == 1
        assert "Failed to run ingestion pipeline" in result.output

def test_cli_config_without_settings(runner):
    """Test that the config command fails when settings are not available."""
    with patch('qdrant_loader.cli.get_settings', return_value=None):
        result = runner.invoke(cli, ['config'])
        assert result.exit_code != 0
        assert "Settings not available. Please check your environment variables." in str(result.output)

def test_cli_config_with_error(runner):
    """Test that the config command handles errors gracefully."""
    with patch('qdrant_loader.cli.get_settings', side_effect=Exception("Config error")):
        result = runner.invoke(cli, ['config'])
        assert result.exit_code != 0
        assert "Failed to show configuration: Config error" in str(result.output)

def test_cli_version_with_error(runner):
    """Test that the version command handles errors gracefully."""
    with patch('importlib.metadata.version', side_effect=Exception("Version error")):
        result = runner.invoke(cli, ['version'])
        assert result.exit_code != 0
        assert "Failed to get version information: Version error" in str(result.output)

def test_cli_ingest_with_missing_config_file(runner):
    """Test that the ingest command uses default config path when not specified."""
    with patch('pathlib.Path.exists', return_value=False):
        result = runner.invoke(cli, ['ingest'])
        assert result.exit_code != 0
        assert "No config file specified and no config.yaml found in current directory" in str(result.output)

def test_cli_log_level_validation(runner, mock_config_file):
    """Test that invalid log levels are rejected."""
    result = runner.invoke(cli, ['--log-level', 'INVALID', 'ingest', '--config', str(mock_config_file)])
    assert result.exit_code != 0
    assert "Invalid value for '--log-level'" in result.output

def test_cli_ingest_with_jira_source_type(runner, mock_config_file):
    """Test that the ingest command works with JIRA source type."""
    with patch('qdrant_loader.cli.IngestionPipeline') as mock_pipeline, \
         patch('qdrant_loader.cli.asyncio.run') as mock_run:
        # Mock the process_documents method
        mock_pipeline.return_value.process_documents.return_value = None
        mock_run.return_value = None
        
        # Test with JIRA source type
        result = runner.invoke(cli, ['ingest', '--config', str(mock_config_file), '--source-type', 'jira'])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        args = mock_pipeline.return_value.process_documents.call_args[1]
        assert args['source_type'] == 'jira'
        assert args['source_name'] is None

def test_cli_ingest_with_jira_source_type_and_name(runner, mock_config_file):
    """Test that the ingest command works with JIRA source type and name."""
    with patch('qdrant_loader.cli.IngestionPipeline') as mock_pipeline, \
         patch('qdrant_loader.cli.asyncio.run') as mock_run:
        # Mock the process_documents method
        mock_pipeline.return_value.process_documents.return_value = None
        mock_run.return_value = None
        
        # Test with specific JIRA project
        result = runner.invoke(cli, ['ingest', '--config', str(mock_config_file), 
                                   '--source-type', 'jira', '--source', 'project1'])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        args = mock_pipeline.return_value.process_documents.call_args[1]
        assert args['source_type'] == 'jira'
        assert args['source_name'] == 'project1'

def test_cli_ingest_with_default_config(runner):
    """Test that the ingest command uses config.yaml from current directory when no config is specified."""
    with patch('pathlib.Path.exists', return_value=True), \
         patch('qdrant_loader.cli.IngestionPipeline') as mock_pipeline, \
         patch('qdrant_loader.cli.asyncio.run') as mock_run, \
         patch('qdrant_loader.config.initialize_config') as mock_init_config, \
         patch('qdrant_loader.cli.get_settings', return_value=MagicMock()):
        
        # Mock the process_documents method
        mock_pipeline.return_value.process_documents.return_value = None
        mock_run.return_value = None
        
        result = runner.invoke(cli, ['ingest'])
        assert result.exit_code == 0
        mock_init_config.assert_called_once_with(Path('config.yaml'))

def test_cli_ingest_without_config_and_no_default(runner):
    """Test that the ingest command fails when no config is specified and no config.yaml exists."""
    with patch('pathlib.Path.exists', return_value=False):
        result = runner.invoke(cli, ['ingest'])
        assert result.exit_code != 0
        assert "No config file specified and no config.yaml found in current directory" in str(result.output)

def test_cli_ingest_with_explicit_config(runner, mock_config_file):
    """Test that the ingest command uses the explicitly specified config file."""
    with patch('qdrant_loader.cli.IngestionPipeline') as mock_pipeline, \
         patch('qdrant_loader.cli.asyncio.run') as mock_run, \
         patch('qdrant_loader.config.initialize_config') as mock_init_config, \
         patch('qdrant_loader.cli.get_settings', return_value=MagicMock()):
        
        # Mock the process_documents method
        mock_pipeline.return_value.process_documents.return_value = None
        mock_run.return_value = None
        
        result = runner.invoke(cli, ['ingest', '--config', str(mock_config_file)])
        assert result.exit_code == 0
        mock_init_config.assert_called_once_with(Path(str(mock_config_file))) 