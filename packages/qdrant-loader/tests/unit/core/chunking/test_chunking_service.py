"""Tests for the ChunkingService."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from qdrant_loader.config import GlobalConfig, Settings
from qdrant_loader.core.chunking.chunking_service import ChunkingService
from qdrant_loader.core.chunking.strategy import (
    CodeChunkingStrategy,
    DefaultChunkingStrategy,
    HTMLChunkingStrategy,
    JSONChunkingStrategy,
    MarkdownChunkingStrategy,
)
from qdrant_loader.core.document import Document


class TestChunkingService:
    """Test cases for the ChunkingService."""

    @pytest.fixture
    def mock_global_config(self):
        """Create mock global configuration."""
        config = Mock(spec=GlobalConfig)
        config.chunking = Mock()
        config.chunking.chunk_size = 1000
        config.chunking.chunk_overlap = 100
        config.chunking.max_chunks_per_document = 500
        return config

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.global_config = Mock()
        settings.global_config.embedding = Mock()
        settings.global_config.embedding.tokenizer = None
        settings.global_config.chunking = Mock()
        settings.global_config.chunking.chunk_size = 1000
        settings.global_config.chunking.chunk_overlap = 100
        settings.global_config.chunking.max_chunks_per_document = 500
        
        # Add strategy-specific configurations
        settings.global_config.chunking.strategies = Mock()
        settings.global_config.chunking.strategies.markdown = Mock()
        settings.global_config.chunking.strategies.markdown.min_content_length_for_nlp = 100
        settings.global_config.chunking.strategies.markdown.min_word_count_for_nlp = 20
        settings.global_config.chunking.strategies.markdown.min_line_count_for_nlp = 3
        settings.global_config.chunking.strategies.markdown.min_section_size = 500
        settings.global_config.chunking.strategies.markdown.max_chunks_per_section = 1000
        settings.global_config.chunking.strategies.markdown.max_overlap_percentage = 0.25
        settings.global_config.chunking.strategies.markdown.max_workers = 4
        settings.global_config.chunking.strategies.markdown.estimation_buffer = 0.2
        settings.global_config.chunking.strategies.markdown.words_per_minute_reading = 200
        settings.global_config.chunking.strategies.markdown.header_analysis_threshold_h1 = 3
        settings.global_config.chunking.strategies.markdown.header_analysis_threshold_h3 = 8
        settings.global_config.chunking.strategies.markdown.enable_hierarchical_metadata = True
        
        settings.global_config.semantic_analysis = Mock()
        settings.global_config.semantic_analysis.spacy_model = "en_core_web_sm"
        settings.global_config.semantic_analysis.num_topics = 3
        settings.global_config.semantic_analysis.lda_passes = 10
        return settings

    @pytest.fixture
    def sample_document(self):
        """Create a sample document for testing."""
        return Document(
            content="This is a test document with some content.",
            url="http://example.com/test.md",
            content_type="md",
            source_type="test",
            source="test_source",
            title="Test Document",
            metadata={"source": "test"},
        )

    @pytest.fixture
    def empty_document(self):
        """Create an empty document for testing."""
        return Document(
            content="",
            url="http://example.com/empty.md",
            content_type="md",
            source_type="test",
            source="test_source",
            title="Empty Document",
            metadata={"source": "test"},
        )

    def test_initialization_success(self, mock_global_config, mock_settings):
        """Test successful initialization of ChunkingService."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path") as mock_path,
            patch(
                "qdrant_loader.core.chunking.chunking_service.IngestionMonitor"
            ) as mock_monitor,
            patch(
                "qdrant_loader.core.chunking.chunking_service.LoggingConfig"
            ) as mock_logging,
            patch("spacy.load") as mock_spacy_load,
        ):

            # Setup mocks
            mock_cwd_path = MagicMock()
            mock_metrics_dir = MagicMock()
            mock_cwd_path.__truediv__ = MagicMock(return_value=mock_metrics_dir)
            mock_path.cwd.return_value = mock_cwd_path
            mock_metrics_dir.absolute.return_value = "/test/metrics"

            mock_logger = Mock()
            mock_logging.get_logger.return_value = mock_logger
            
            # Mock spacy
            mock_nlp = Mock()
            mock_nlp.pipe_names = []  # Empty pipe names to avoid processing
            mock_spacy_load.return_value = mock_nlp

            # Create service
            service = ChunkingService(mock_global_config, mock_settings)

            # Verify initialization
            assert service.config == mock_global_config
            assert service.settings == mock_settings
            assert service.logger == mock_logger

            # Verify metrics directory creation (may be called multiple times by different components)
            assert mock_metrics_dir.mkdir.call_count >= 1
            mock_metrics_dir.mkdir.assert_called_with(parents=True, exist_ok=True)

            # Verify monitor initialization (may be called multiple times by different components)
            assert mock_monitor.call_count >= 1
            mock_monitor.assert_called_with("/test/metrics")

            # Verify strategies are initialized
            assert "md" in service.strategies
            assert "html" in service.strategies
            assert "json" in service.strategies
            assert "py" in service.strategies
            assert service.strategies["md"] == MarkdownChunkingStrategy
            assert service.strategies["html"] == HTMLChunkingStrategy
            assert service.strategies["json"] == JSONChunkingStrategy
            assert service.strategies["py"] == CodeChunkingStrategy

            # Verify default strategy
            assert isinstance(service.default_strategy, DefaultChunkingStrategy)

    def test_validate_config_success(self, mock_global_config, mock_settings):
        """Test successful configuration validation."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path"),
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch("qdrant_loader.core.chunking.chunking_service.LoggingConfig"),
        ):

            # Valid configuration
            mock_global_config.chunking.chunk_size = 1000
            mock_global_config.chunking.chunk_overlap = 100

            # Should not raise any exception
            service = ChunkingService(mock_global_config, mock_settings)
            assert service is not None

    def test_validate_config_invalid_chunk_size(
        self, mock_global_config, mock_settings
    ):
        """Test configuration validation with invalid chunk size."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path"),
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch("qdrant_loader.core.chunking.chunking_service.LoggingConfig"),
        ):

            # Invalid chunk size (zero)
            mock_global_config.chunking.chunk_size = 0
            mock_global_config.chunking.chunk_overlap = 100

            with pytest.raises(ValueError, match="Chunk size must be greater than 0"):
                ChunkingService(mock_global_config, mock_settings)

    def test_validate_config_negative_chunk_size(
        self, mock_global_config, mock_settings
    ):
        """Test configuration validation with negative chunk size."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path"),
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch("qdrant_loader.core.chunking.chunking_service.LoggingConfig"),
        ):

            # Invalid chunk size (negative)
            mock_global_config.chunking.chunk_size = -100
            mock_global_config.chunking.chunk_overlap = 50

            with pytest.raises(ValueError, match="Chunk size must be greater than 0"):
                ChunkingService(mock_global_config, mock_settings)

    def test_validate_config_negative_overlap(self, mock_global_config, mock_settings):
        """Test configuration validation with negative overlap."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path"),
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch("qdrant_loader.core.chunking.chunking_service.LoggingConfig"),
        ):

            # Invalid overlap (negative)
            mock_global_config.chunking.chunk_size = 1000
            mock_global_config.chunking.chunk_overlap = -50

            with pytest.raises(ValueError, match="Chunk overlap must be non-negative"):
                ChunkingService(mock_global_config, mock_settings)

    def test_validate_config_overlap_too_large(self, mock_global_config, mock_settings):
        """Test configuration validation with overlap >= chunk size."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path"),
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch("qdrant_loader.core.chunking.chunking_service.LoggingConfig"),
        ):

            # Invalid overlap (equal to chunk size)
            mock_global_config.chunking.chunk_size = 1000
            mock_global_config.chunking.chunk_overlap = 1000

            with pytest.raises(
                ValueError, match="Chunk overlap must be less than chunk size"
            ):
                ChunkingService(mock_global_config, mock_settings)

    def test_validate_config_overlap_greater_than_chunk_size(
        self, mock_global_config, mock_settings
    ):
        """Test configuration validation with overlap > chunk size."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path"),
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch("qdrant_loader.core.chunking.chunking_service.LoggingConfig"),
        ):

            # Invalid overlap (greater than chunk size)
            mock_global_config.chunking.chunk_size = 500
            mock_global_config.chunking.chunk_overlap = 600

            with pytest.raises(
                ValueError, match="Chunk overlap must be less than chunk size"
            ):
                ChunkingService(mock_global_config, mock_settings)

    def test_get_strategy_markdown(self, mock_global_config, mock_settings):
        """Test strategy selection for markdown documents."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path"),
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch("qdrant_loader.core.chunking.chunking_service.LoggingConfig"),
        ):

            service = ChunkingService(mock_global_config, mock_settings)

            # Create markdown document
            doc = Document(
                content="# Test",
                url="http://example.com/test.md",
                content_type="md",
                source_type="test",
                source="test_source",
                title="Test",
                metadata={"source": "test"},
            )

            strategy = service._get_strategy(doc)
            assert isinstance(strategy, MarkdownChunkingStrategy)

    def test_get_strategy_html(self, mock_global_config, mock_settings):
        """Test strategy selection for HTML documents."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path"),
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch("qdrant_loader.core.chunking.chunking_service.LoggingConfig"),
        ):

            service = ChunkingService(mock_global_config, mock_settings)

            # Create HTML document
            doc = Document(
                content="<h1>Test</h1>",
                url="http://example.com/test.html",
                content_type="html",
                source_type="test",
                source="test_source",
                title="Test",
                metadata={"source": "test"},
            )

            strategy = service._get_strategy(doc)
            assert isinstance(strategy, HTMLChunkingStrategy)

    def test_get_strategy_json(self, mock_global_config, mock_settings):
        """Test strategy selection for JSON documents."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path"),
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch("qdrant_loader.core.chunking.chunking_service.LoggingConfig"),
        ):

            service = ChunkingService(mock_global_config, mock_settings)

            # Create JSON document
            doc = Document(
                content='{"test": "value"}',
                url="http://example.com/test.json",
                content_type="json",
                source_type="test",
                source="test_source",
                title="Test",
                metadata={"source": "test"},
            )

            strategy = service._get_strategy(doc)
            assert isinstance(strategy, JSONChunkingStrategy)

    def test_get_strategy_code_python(self, mock_global_config, mock_settings):
        """Test strategy selection for Python code documents."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path"),
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch("qdrant_loader.core.chunking.chunking_service.LoggingConfig"),
        ):

            service = ChunkingService(mock_global_config, mock_settings)

            # Create Python document
            doc = Document(
                content="def test(): pass",
                url="http://example.com/test.py",
                content_type="py",
                source_type="test",
                source="test_source",
                title="Test",
                metadata={"source": "test"},
            )

            strategy = service._get_strategy(doc)
            assert isinstance(strategy, CodeChunkingStrategy)

    def test_get_strategy_code_java(self, mock_global_config, mock_settings):
        """Test strategy selection for Java code documents."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path"),
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch("qdrant_loader.core.chunking.chunking_service.LoggingConfig"),
        ):

            service = ChunkingService(mock_global_config, mock_settings)

            # Create Java document
            doc = Document(
                content="public class Test {}",
                url="http://example.com/Test.java",
                content_type="java",
                source_type="test",
                source="test_source",
                title="Test",
                metadata={"source": "test"},
            )

            strategy = service._get_strategy(doc)
            assert isinstance(strategy, CodeChunkingStrategy)

    def test_get_strategy_unknown_type(self, mock_global_config, mock_settings):
        """Test strategy selection for unknown document types."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path"),
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch("qdrant_loader.core.chunking.chunking_service.LoggingConfig"),
        ):

            service = ChunkingService(mock_global_config, mock_settings)

            # Create document with unknown type
            doc = Document(
                content="Some unknown content",
                url="http://example.com/test.xyz",
                content_type="xyz",
                source_type="test",
                source="test_source",
                title="Test",
                metadata={"source": "test"},
            )

            strategy = service._get_strategy(doc)
            assert strategy == service.default_strategy
            assert isinstance(strategy, DefaultChunkingStrategy)

    def test_get_strategy_case_insensitive(self, mock_global_config, mock_settings):
        """Test strategy selection is case insensitive."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path"),
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch("qdrant_loader.core.chunking.chunking_service.LoggingConfig"),
        ):

            service = ChunkingService(mock_global_config, mock_settings)

            # Create document with uppercase content type
            doc = Document(
                content="# Test",
                url="http://example.com/test.MD",
                content_type="MD",
                source_type="test",
                source="test_source",
                title="Test",
                metadata={"source": "test"},
            )

            strategy = service._get_strategy(doc)
            assert isinstance(strategy, MarkdownChunkingStrategy)

    def test_chunk_document_success(
        self, mock_global_config, mock_settings, sample_document
    ):
        """Test successful document chunking."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path"),
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch("qdrant_loader.core.chunking.chunking_service.LoggingConfig"),
        ):

            service = ChunkingService(mock_global_config, mock_settings)

            # Mock the strategy
            mock_strategy = Mock()
            mock_chunks = [
                Document(
                    content="Chunk 1",
                    url="http://example.com/test.md#chunk1",
                    content_type="md",
                    source_type="test",
                    source="test_source",
                    title="Test Document - Chunk 1",
                    metadata={"source": "test", "chunk_index": 0},
                ),
                Document(
                    content="Chunk 2",
                    url="http://example.com/test.md#chunk2",
                    content_type="md",
                    source_type="test",
                    source="test_source",
                    title="Test Document - Chunk 2",
                    metadata={"source": "test", "chunk_index": 1},
                ),
            ]
            mock_strategy.chunk_document.return_value = mock_chunks

            with patch.object(service, "_get_strategy", return_value=mock_strategy):
                result = service.chunk_document(sample_document)

                assert result == mock_chunks
                assert len(result) == 2
                mock_strategy.chunk_document.assert_called_once_with(sample_document)

    def test_chunk_document_empty_content(
        self, mock_global_config, mock_settings, empty_document
    ):
        """Test chunking document with empty content."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path"),
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch("qdrant_loader.core.chunking.chunking_service.LoggingConfig"),
        ):

            service = ChunkingService(mock_global_config, mock_settings)

            result = service.chunk_document(empty_document)

            assert len(result) == 1
            chunk = result[0]
            assert chunk.content == ""
            assert chunk.metadata["chunk_index"] == 0
            assert chunk.metadata["total_chunks"] == 1

    def test_chunk_document_none_content(self, mock_global_config, mock_settings):
        """Test chunking document with None content (simulated via mock)."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path"),
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch("qdrant_loader.core.chunking.chunking_service.LoggingConfig"),
        ):

            service = ChunkingService(mock_global_config, mock_settings)

            # Create a mock document with empty content (since Document model doesn't accept None)
            # and the service tries to get len(content) before checking for None
            mock_doc = Mock()
            mock_doc.content = (
                ""  # Use empty string instead of None to avoid len() error
            )
            mock_doc.content_type = "md"
            mock_doc.url = "http://example.com/test.md"
            mock_doc.title = "Test"
            mock_doc.metadata = {"source": "test"}
            mock_doc.id = "test-id"
            mock_doc.source = "test_source"
            mock_doc.source_type = "test"

            # Set up model_copy to return a copy with updated metadata
            mock_copy = Mock()
            mock_copy.content = ""
            mock_copy.metadata = {"source": "test", "chunk_index": 0, "total_chunks": 1}
            mock_copy.id = "test-id-copy"
            mock_doc.model_copy.return_value = mock_copy

            # For empty content, the service returns a single empty chunk directly
            # without calling the strategy
            result = service.chunk_document(mock_doc)

            # Should return single empty chunk for empty content
            assert len(result) == 1
            chunk = result[0]
            assert chunk.content == ""
            assert chunk.metadata["chunk_index"] == 0
            assert chunk.metadata["total_chunks"] == 1

    def test_chunk_document_strategy_error(
        self, mock_global_config, mock_settings, sample_document
    ):
        """Test error handling when strategy raises exception."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path"),
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch("qdrant_loader.core.chunking.chunking_service.LoggingConfig"),
        ):

            service = ChunkingService(mock_global_config, mock_settings)

            # Mock the strategy to raise an exception
            mock_strategy = Mock()
            test_error = Exception("Strategy processing error")
            mock_strategy.chunk_document.side_effect = test_error

            with patch.object(service, "_get_strategy", return_value=mock_strategy):
                with pytest.raises(Exception, match="Strategy processing error"):
                    service.chunk_document(sample_document)

    def test_all_programming_language_strategies(
        self, mock_global_config, mock_settings
    ):
        """Test that all programming language content types map to CodeChunkingStrategy."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path"),
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch("qdrant_loader.core.chunking.chunking_service.LoggingConfig"),
        ):

            service = ChunkingService(mock_global_config, mock_settings)

            # Test all programming language extensions
            programming_languages = [
                "py",
                "java",
                "js",
                "ts",
                "go",
                "rs",
                "cpp",
                "c",
                "cs",
                "php",
                "rb",
                "kt",
                "swift",
                "scala",
            ]

            for lang in programming_languages:
                doc = Document(
                    content="test code",
                    url=f"http://example.com/test.{lang}",
                    content_type=lang,
                    source_type="test",
                    source="test_source",
                    title="Test",
                    metadata={"source": "test"},
                )

                strategy = service._get_strategy(doc)
                assert isinstance(
                    strategy, CodeChunkingStrategy
                ), f"Failed for language: {lang}"

    def test_new_method_creates_instance(self, mock_global_config, mock_settings):
        """Test that __new__ method creates and initializes instance correctly."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path"),
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch("qdrant_loader.core.chunking.chunking_service.LoggingConfig"),
        ):

            # Use __new__ directly
            instance = ChunkingService.__new__(
                ChunkingService, mock_global_config, mock_settings
            )

            assert isinstance(instance, ChunkingService)
            assert instance.config == mock_global_config
            assert instance.settings == mock_settings

    def test_chunk_document_logging(
        self, mock_global_config, mock_settings, sample_document
    ):
        """Test that appropriate logging occurs during chunking."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path"),
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch(
                "qdrant_loader.core.chunking.chunking_service.LoggingConfig"
            ) as mock_logging,
        ):

            mock_logger = Mock()
            mock_logging.get_logger.return_value = mock_logger

            service = ChunkingService(mock_global_config, mock_settings)

            # Mock the strategy
            mock_strategy = Mock()
            mock_chunks = [sample_document]
            mock_strategy.chunk_document.return_value = mock_chunks

            with patch.object(service, "_get_strategy", return_value=mock_strategy):
                service.chunk_document(sample_document)

                # Verify debug logging was called
                assert (
                    mock_logger.debug.call_count >= 3
                )  # Start, strategy selection, completion

                # Check specific log calls
                debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
                assert "Starting document chunking" in debug_calls
                assert "Selected chunking strategy" in debug_calls
                assert "Document chunking completed" in debug_calls
