"""Tests for the SourceProcessor class."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.core.document import Document
from qdrant_loader.core.file_conversion import FileConversionConfig
from qdrant_loader.core.pipeline.source_processor import SourceProcessor


class MockConnector(BaseConnector):
    """Mock connector for testing."""

    def __init__(self, source_config: SourceConfig):
        self.source_config = source_config
        self.file_conversion_config = None
        self._documents = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def get_documents(self) -> list[Document]:
        return self._documents

    def set_file_conversion_config(self, config: FileConversionConfig):
        self.file_conversion_config = config


class TestSourceProcessor:
    """Test cases for SourceProcessor."""

    @pytest.fixture
    def sample_documents(self):
        """Create sample documents for testing."""
        return [
            Document(
                content="Test document 1",
                url="http://example.com/doc1",
                content_type="md",
                source_type="test",
                source="test_source_1",
                title="Test Document 1",
                metadata={"source": "test"},
            ),
            Document(
                content="Test document 2",
                url="http://example.com/doc2",
                content_type="md",
                source_type="test",
                source="test_source_1",
                title="Test Document 2",
                metadata={"source": "test"},
            ),
        ]

    @pytest.fixture
    def mock_source_config(self):
        """Create a mock source config."""
        config = MagicMock(spec=SourceConfig)
        config.enable_file_conversion = True
        return config

    @pytest.fixture
    def file_conversion_config(self):
        """Create a file conversion config."""
        return FileConversionConfig()

    def test_initialization_default(self):
        """Test SourceProcessor initialization with defaults."""
        processor = SourceProcessor()

        assert processor.shutdown_event is not None
        assert isinstance(processor.shutdown_event, asyncio.Event)
        assert processor.file_conversion_config is None

    def test_initialization_with_shutdown_event(self):
        """Test SourceProcessor initialization with provided shutdown event."""
        shutdown_event = asyncio.Event()
        processor = SourceProcessor(shutdown_event=shutdown_event)

        assert processor.shutdown_event is shutdown_event
        assert processor.file_conversion_config is None

    def test_initialization_with_file_conversion_config(self, file_conversion_config):
        """Test SourceProcessor initialization with file conversion config."""
        processor = SourceProcessor(file_conversion_config=file_conversion_config)

        assert processor.shutdown_event is not None
        assert processor.file_conversion_config is file_conversion_config

    def test_initialization_with_all_parameters(self, file_conversion_config):
        """Test SourceProcessor initialization with all parameters."""
        shutdown_event = asyncio.Event()
        processor = SourceProcessor(
            shutdown_event=shutdown_event, file_conversion_config=file_conversion_config
        )

        assert processor.shutdown_event is shutdown_event
        assert processor.file_conversion_config is file_conversion_config

    @pytest.mark.asyncio
    async def test_process_source_type_success(
        self, mock_source_config, sample_documents
    ):
        """Test successful processing of source type."""
        processor = SourceProcessor()

        # Create mock connector class
        mock_connector_class = MagicMock()
        mock_connector_instance = AsyncMock()
        mock_connector_instance.get_documents.return_value = sample_documents
        mock_connector_class.return_value = mock_connector_instance

        source_configs = {"test_source": mock_source_config}

        with patch(
            "qdrant_loader.core.pipeline.source_processor.logger"
        ) as mock_logger:
            result = await processor.process_source_type(
                source_configs, mock_connector_class, "test_type"
            )

        # Verify results
        assert len(result) == 2
        assert result == sample_documents

        # Verify connector was created and called
        mock_connector_class.assert_called_once_with(mock_source_config)
        mock_connector_instance.get_documents.assert_called_once()

        # Verify logging
        mock_logger.debug.assert_called()
        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_process_source_type_multiple_sources(self, sample_documents):
        """Test processing multiple sources of the same type."""
        processor = SourceProcessor()

        # Create multiple source configs
        source_config_1 = MagicMock(spec=SourceConfig)
        source_config_2 = MagicMock(spec=SourceConfig)

        source_configs = {"source_1": source_config_1, "source_2": source_config_2}

        # Create mock connector class that returns different documents for each source
        mock_connector_class = MagicMock()
        mock_instances = []

        for _i, docs in enumerate([sample_documents[:1], sample_documents[1:]]):
            mock_instance = AsyncMock()
            mock_instance.get_documents.return_value = docs
            mock_instances.append(mock_instance)

        mock_connector_class.side_effect = mock_instances

        result = await processor.process_source_type(
            source_configs, mock_connector_class, "test_type"
        )

        # Verify all documents are collected
        assert len(result) == 2
        assert result[0] == sample_documents[0]
        assert result[1] == sample_documents[1]

    @pytest.mark.asyncio
    async def test_process_source_type_with_shutdown_event(self, mock_source_config):
        """Test processing with shutdown event set."""
        shutdown_event = asyncio.Event()
        shutdown_event.set()  # Set the shutdown event

        processor = SourceProcessor(shutdown_event=shutdown_event)

        mock_connector_class = MagicMock()
        source_configs = {"test_source": mock_source_config}

        with patch(
            "qdrant_loader.core.pipeline.source_processor.logger"
        ) as mock_logger:
            result = await processor.process_source_type(
                source_configs, mock_connector_class, "test_type"
            )

        # Should return empty list and not create connector
        assert result == []
        mock_connector_class.assert_not_called()

        # Verify shutdown logging
        mock_logger.info.assert_called()
        assert "Shutdown requested" in str(mock_logger.info.call_args)

    @pytest.mark.asyncio
    async def test_process_source_type_with_file_conversion_config(
        self, file_conversion_config
    ):
        """Test processing with file conversion config."""
        processor = SourceProcessor(file_conversion_config=file_conversion_config)

        # Create source config that supports file conversion
        source_config = MagicMock(spec=SourceConfig)
        source_config.enable_file_conversion = True

        # Create mock connector that supports file conversion
        mock_connector_instance = AsyncMock()
        mock_connector_instance.get_documents.return_value = []
        mock_connector_instance.set_file_conversion_config = MagicMock()

        mock_connector_class = MagicMock(return_value=mock_connector_instance)

        source_configs = {"test_source": source_config}

        with patch(
            "qdrant_loader.core.pipeline.source_processor.logger"
        ) as mock_logger:
            await processor.process_source_type(
                source_configs, mock_connector_class, "test_type"
            )

        # Verify file conversion config was set
        mock_connector_instance.set_file_conversion_config.assert_called_once_with(
            file_conversion_config
        )

        # Verify debug logging for file conversion
        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        assert any("Setting file conversion config" in msg for msg in debug_calls)

    @pytest.mark.asyncio
    async def test_process_source_type_file_conversion_disabled(
        self, file_conversion_config
    ):
        """Test processing with file conversion config but disabled in source."""
        processor = SourceProcessor(file_conversion_config=file_conversion_config)

        # Create source config with file conversion disabled
        source_config = MagicMock(spec=SourceConfig)
        source_config.enable_file_conversion = False

        mock_connector_instance = AsyncMock()
        mock_connector_instance.get_documents.return_value = []
        mock_connector_instance.set_file_conversion_config = MagicMock()

        mock_connector_class = MagicMock(return_value=mock_connector_instance)

        source_configs = {"test_source": source_config}

        await processor.process_source_type(
            source_configs, mock_connector_class, "test_type"
        )

        # Verify file conversion config was NOT set
        mock_connector_instance.set_file_conversion_config.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_source_type_connector_without_file_conversion(
        self, file_conversion_config
    ):
        """Test processing with connector that doesn't support file conversion."""
        processor = SourceProcessor(file_conversion_config=file_conversion_config)

        source_config = MagicMock(spec=SourceConfig)
        source_config.enable_file_conversion = True

        # Create mock connector without set_file_conversion_config method
        mock_connector_instance = AsyncMock()
        mock_connector_instance.get_documents.return_value = []
        # Don't add set_file_conversion_config method

        mock_connector_class = MagicMock(return_value=mock_connector_instance)

        source_configs = {"test_source": source_config}

        # Should not raise error and should complete successfully
        result = await processor.process_source_type(
            source_configs, mock_connector_class, "test_type"
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_process_source_type_exception_handling(self, mock_source_config):
        """Test exception handling during source processing."""
        processor = SourceProcessor()

        # Create mock connector that raises exception
        mock_connector_class = MagicMock()
        mock_connector_class.side_effect = Exception("Connector creation failed")

        source_configs = {"test_source": mock_source_config}

        with patch(
            "qdrant_loader.core.pipeline.source_processor.logger"
        ) as mock_logger:
            result = await processor.process_source_type(
                source_configs, mock_connector_class, "test_type"
            )

        # Should return empty list and continue processing
        assert result == []

        # Verify error logging
        mock_logger.error.assert_called()
        error_msg = str(mock_logger.error.call_args[0][0])
        assert "Failed to process" in error_msg
        assert "test_source" in error_msg

    @pytest.mark.asyncio
    async def test_process_source_type_partial_failure(self, sample_documents):
        """Test processing where one source fails but others succeed."""
        processor = SourceProcessor()

        source_config_1 = MagicMock(spec=SourceConfig)
        source_config_2 = MagicMock(spec=SourceConfig)

        source_configs = {"good_source": source_config_1, "bad_source": source_config_2}

        # Create mock connector class that fails for one source
        call_count = 0

        def mock_connector_side_effect(config):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # First call succeeds
                mock_instance = AsyncMock()
                mock_instance.get_documents.return_value = sample_documents
                return mock_instance
            else:  # Second call fails
                raise Exception("Connection failed")

        mock_connector_class = MagicMock(side_effect=mock_connector_side_effect)

        with patch(
            "qdrant_loader.core.pipeline.source_processor.logger"
        ) as mock_logger:
            result = await processor.process_source_type(
                source_configs, mock_connector_class, "test_type"
            )

        # Should get documents from successful source
        assert len(result) == 2
        assert result == sample_documents

        # Should have logged both success and error
        mock_logger.info.assert_called()
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_process_source_type_empty_sources(self):
        """Test processing with empty source configs."""
        processor = SourceProcessor()

        mock_connector_class = MagicMock()
        source_configs = {}

        result = await processor.process_source_type(
            source_configs, mock_connector_class, "test_type"
        )

        # Should return empty list
        assert result == []
        mock_connector_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_source_type_no_documents(self, mock_source_config):
        """Test processing when connector returns no documents."""
        processor = SourceProcessor()

        mock_connector_instance = AsyncMock()
        mock_connector_instance.get_documents.return_value = []
        mock_connector_class = MagicMock(return_value=mock_connector_instance)

        source_configs = {"test_source": mock_source_config}

        with patch(
            "qdrant_loader.core.pipeline.source_processor.logger"
        ) as mock_logger:
            result = await processor.process_source_type(
                source_configs, mock_connector_class, "test_type"
            )

        # Should return empty list
        assert result == []

        # Should not log the success message (since no documents)
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert not any("documents from" in msg for msg in info_calls)

    @pytest.mark.asyncio
    @patch("qdrant_loader.core.pipeline.source_processor.logger")
    async def test_process_source_type_logging_calls(
        self, mock_logger, mock_source_config, sample_documents
    ):
        """Test that appropriate logging calls are made."""
        processor = SourceProcessor()

        mock_connector_instance = AsyncMock()
        mock_connector_instance.get_documents.return_value = sample_documents
        mock_connector_class = MagicMock(return_value=mock_connector_instance)

        source_configs = {"test_source": mock_source_config}

        await processor.process_source_type(source_configs, mock_connector_class, "git")

        # Verify specific logging patterns
        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]

        # Check debug logging
        assert any("Processing git sources:" in msg for msg in debug_calls)
        assert any("Processing git source: test_source" in msg for msg in debug_calls)
        assert any(
            "Retrieved 2 documents from git source: test_source" in msg
            for msg in debug_calls
        )

        # Check info logging
        assert any("git: 2 documents from 1 sources" in msg for msg in info_calls)
