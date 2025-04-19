"""
Tests for the CLI module.
"""

import asyncio
import logging
import os
from logging import getLogger
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, patch
from functools import wraps

import pytest
from click.testing import CliRunner

from qdrant_loader.cli.cli import cli
from qdrant_loader.config import Settings
from qdrant_loader.core.ingestion_pipeline import IngestionPipeline
from qdrant_loader.core.qdrant_manager import QdrantManager, QdrantConnectionError

logger = getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Error message constants
COLLECTION_NOT_FOUND = "Collection not found"
SOURCE_WITHOUT_TYPE = "Source type not specified"
CONNECTION_REFUSED = "Connection refused"


def mock_async_command(f):
    """Mock async_command decorator that properly handles event loop management."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            should_close = True
        else:
            should_close = False

        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            if should_close:
                loop.close()

    return wrapper


@pytest.fixture(autouse=True)
def mock_async_decorator():
    """Automatically mock the async_command decorator for all tests."""
    with patch("qdrant_loader.cli.asyncio.async_command", side_effect=mock_async_command):
        yield


@pytest.fixture
def mock_event_loop():
    """Mock event loop management functions."""
    with (
        patch("asyncio.get_running_loop") as mock_get_loop,
        patch("asyncio.new_event_loop") as mock_new_loop,
        patch("asyncio.set_event_loop") as mock_set_loop,
    ):
        mock_loop = MagicMock()
        mock_loop.run_until_complete = AsyncMock()
        mock_loop.close = MagicMock()

        def get_running_loop_side_effect():
            try:
                return asyncio.get_running_loop()
            except RuntimeError:
                raise RuntimeError("No running event loop")

        mock_get_loop.side_effect = get_running_loop_side_effect
        mock_new_loop.return_value = mock_loop
        mock_set_loop.return_value = None

        yield mock_loop


@pytest.fixture
def mock_settings():
    """Mock settings object."""
    settings = MagicMock(spec=Settings)
    settings.config_file = "config.yaml"
    settings.collection_name = "test_collection"
    settings.source_type = "csv"
    settings.source_path = "data.csv"
    settings.host = "localhost"
    settings.port = 6333
    settings.grpc_port = 6334
    settings.prefer_grpc = False
    settings.verbose = False
    return settings


@pytest.fixture
def mock_qdrant_manager():
    """Mock QdrantManager object."""
    manager = MagicMock(spec=QdrantManager)
    manager.collection_exists = AsyncMock(return_value=True)
    manager.create_collection = AsyncMock()
    manager.delete_collection = AsyncMock()
    return manager


@pytest.fixture
def mock_pipeline():
    """Mock IngestionPipeline object."""
    pipeline = MagicMock(spec=IngestionPipeline)
    pipeline.run = AsyncMock()
    return pipeline


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


class TestBase:
    """Base class for CLI tests with common setup."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_event_loop, mock_settings, mock_qdrant_manager, mock_pipeline, runner):
        self.loop = mock_event_loop
        self.settings = mock_settings
        self.qdrant_manager = mock_qdrant_manager
        self.pipeline = mock_pipeline
        self.runner = runner

        # Setup patches
        self.patches = [
            patch("qdrant_loader.cli.cli.Settings", return_value=self.settings),
            patch("qdrant_loader.cli.cli.QdrantManager", return_value=self.qdrant_manager),
            patch("qdrant_loader.cli.cli.IngestionPipeline", return_value=self.pipeline),
        ]

        for p in self.patches:
            p.start()

    def teardown_method(self):
        for p in self.patches:
            p.stop()

    @pytest.fixture(autouse=True)
    def setup_event_loop(self, event_loop):
        """Ensure each test has access to the event loop."""
        asyncio.set_event_loop(event_loop)
        yield
        # Clean up after test
        asyncio.set_event_loop(None)

    @pytest.fixture
    def mock_collection(self, mocker):
        """Create a mock collection."""
        mock = mocker.MagicMock()
        mock.name = "qdrant-loader-test"
        return mock

    @pytest.fixture
    def mock_collections_response(self, mock_collection):
        """Create a mock collections response."""
        mock = MagicMock()
        mock.collections = [mock_collection]
        return mock

    @pytest.fixture
    def mock_init_collection(self, mocker):
        """Create a mock init_collection function."""
        mock = AsyncMock()
        mock.return_value = True
        return mock

    def setup_common_mocks(self, mock_qdrant_manager, mock_collections_response):
        """Setup common mock behaviors."""
        mock_qdrant_manager.client.get_collections.return_value = mock_collections_response


class TestCliCommands(TestBase):
    """Test CLI commands."""

    def test_cli_help(self):
        """Test help command."""
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "QDrant Loader CLI" in result.output

    def test_cli_version(self):
        """Test version command."""
        result = self.runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "qDrant Loader v." in result.output

    def test_cli_config(self, mock_settings):
        """Test that the config command works."""
        with (
            patch("qdrant_loader.cli.cli.get_settings", return_value=mock_settings),
            patch("qdrant_loader.cli.cli._load_config", return_value=None),
        ):
            result = self.runner.invoke(cli, ["config"])
            assert result.exit_code == 0
            assert "Current Configuration" in result.output

    def test_cli_config_without_settings(self):
        """Test that the config command fails when no configuration file is found."""
        with patch("pathlib.Path.exists", return_value=False):
            result = self.runner.invoke(cli, ["config"])
            assert result.exit_code == 1
            assert "No config file found" in result.output

    def test_cli_config_with_wrong_path_to_settings(self):
        """Test that the config command fails when no configuration file is found."""
        result = self.runner.invoke(cli, ["config", "--config", "non-existing-file.yaml"])
        assert result.exit_code == 2
        assert "Invalid value for '--config'" in result.output


class TestCliInit(TestBase):
    """Test init command variations."""

    @pytest.mark.asyncio
    async def test_cli_init(self):
        """Test basic init command."""
        result = self.runner.invoke(cli, ["init"])
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_cli_init_with_force(self):
        """Test init command with force flag."""
        result = self.runner.invoke(cli, ["init", "--force"])
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_cli_init_with_error(self):
        """Test init command with error."""
        self.settings.side_effect = Exception("Test error")
        with patch("qdrant_loader.cli.cli.logger.error") as mock_logger:
            result = self.runner.invoke(cli, ["init"])
            assert result.exit_code == 0
            mock_logger.assert_called_once_with("init_failed", error="Test error")

    @pytest.mark.asyncio
    async def test_cli_init_with_connection_error(self):
        """Test init command with connection error."""
        self.qdrant_manager.connect.side_effect = Exception("Connection refused")
        with patch("qdrant_loader.cli.cli.logger.error") as mock_logger:
            result = self.runner.invoke(cli, ["init"])
            assert result.exit_code == 0
            mock_logger.assert_called_once_with("init_failed", error="Connection refused")


class TestCliIngest(TestBase):
    """Test ingest command variations."""

    @pytest.mark.asyncio
    async def test_cli_ingest_basic(self):
        """Test basic ingest command."""
        with patch("qdrant_loader.cli.cli.logger.info") as mock_logger:
            result = self.runner.invoke(cli, ["ingest"])
            assert result.exit_code == 0
            mock_logger.assert_called_with("Successfully processed 0 documents")

    @pytest.mark.asyncio
    async def test_cli_ingest_with_source_type(self):
        """Test ingest command with source type."""
        with patch("qdrant_loader.cli.cli.logger.info") as mock_logger:
            result = self.runner.invoke(cli, ["ingest", "--source-type", "confluence"])
            assert result.exit_code == 0
            mock_logger.assert_called_with("Successfully processed 0 documents")

    @pytest.mark.asyncio
    async def test_cli_ingest_with_source(self):
        """Test ingest command with source."""
        with patch("qdrant_loader.cli.cli.logger.info") as mock_logger:
            result = self.runner.invoke(
                cli, ["ingest", "--source-type", "confluence", "--source", "test"]
            )
            assert result.exit_code == 0
            mock_logger.assert_called_with("Successfully processed 0 documents")

    @pytest.mark.asyncio
    async def test_cli_ingest_with_error(self):
        """Test ingest command with error."""
        self.pipeline.process_documents.side_effect = Exception("Test error")
        with patch("qdrant_loader.cli.cli.logger.error") as mock_logger:
            result = self.runner.invoke(cli, ["ingest"])
            assert result.exit_code == 0
            mock_logger.assert_called_once_with("ingestion_failed", error="Test error")

    @pytest.mark.asyncio
    async def test_cli_ingest_with_connection_error(self):
        """Test ingest command with connection error."""
        self.qdrant_manager.connect.side_effect = Exception("Connection refused")
        with patch("qdrant_loader.cli.cli.logger.error") as mock_logger:
            result = self.runner.invoke(cli, ["ingest"])
            assert result.exit_code == 0
            mock_logger.assert_called_once_with(
                "qdrant_connection_failed", error="Connection refused"
            )

    @pytest.mark.asyncio
    async def test_cli_ingest_with_source_without_type(self):
        """Test ingest with source without type."""
        with patch("qdrant_loader.cli.cli.logger.error") as mock_logger:
            result = self.runner.invoke(cli, ["ingest", "--source-name", "test-source"])
            assert result.exit_code == 0
            mock_logger.assert_called_once_with("source_without_type")

    @pytest.mark.asyncio
    async def test_cli_ingest_with_collection_not_found(self):
        """Test ingest with collection not found."""
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])
        self.qdrant_manager._ensure_client_connected.return_value = mock_client
        with patch("qdrant_loader.cli.cli.logger.error") as mock_logger:
            result = self.runner.invoke(cli, ["ingest"])
            assert result.exit_code == 0
            mock_logger.assert_called_once_with("collection_not_found")

    def test_cli_ingest_with_missing_config_file(self):
        """Test ingest with missing config file."""
        result = self.runner.invoke(cli, ["ingest", "--config", "non-existing-file.yaml"])
        assert result.exit_code == 2
        assert "Invalid value for '--config'" in result.output

    def test_cli_log_level_validation(self):
        """Test log level validation."""
        result = self.runner.invoke(cli, ["--log-level", "INVALID"])
        assert result.exit_code == 2
        assert "Invalid value for '--log-level'" in result.output
