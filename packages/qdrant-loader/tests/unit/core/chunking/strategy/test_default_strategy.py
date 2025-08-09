"""Tests for the DefaultChunkingStrategy."""

from unittest.mock import Mock, patch

import pytest
from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.strategy.default_strategy import (
    DefaultChunkingStrategy,
)
from qdrant_loader.core.document import Document

# Use the config value instead of hardcoded constant
MAX_CHUNKS_TO_PROCESS = 500  # This matches the mock settings


class TestDefaultChunkingStrategy:
    """Test cases for the DefaultChunkingStrategy."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.global_config = Mock()
        settings.global_config.chunking = Mock()
        settings.global_config.chunking.chunk_size = 100
        settings.global_config.chunking.chunk_overlap = 20
        settings.global_config.chunking.max_chunks_per_document = 500

        # Add strategy-specific configuration
        settings.global_config.chunking.strategies = Mock()
        settings.global_config.chunking.strategies.default = Mock()
        settings.global_config.chunking.strategies.default.min_chunk_size = 50
        settings.global_config.chunking.strategies.default.enable_semantic_analysis = (
            True
        )
        settings.global_config.chunking.strategies.default.enable_entity_extraction = (
            True
        )

        settings.global_config.embedding = Mock()
        settings.global_config.embedding.tokenizer = "cl100k_base"
        return settings

    @pytest.fixture
    def mock_settings_no_tokenizer(self):
        """Create mock settings without tokenizer."""
        settings = Mock(spec=Settings)
        settings.global_config = Mock()
        settings.global_config.chunking = Mock()
        settings.global_config.chunking.chunk_size = 50
        settings.global_config.chunking.chunk_overlap = 10
        settings.global_config.chunking.max_chunks_per_document = 500

        # Add strategy-specific configuration
        settings.global_config.chunking.strategies = Mock()
        settings.global_config.chunking.strategies.default = Mock()
        settings.global_config.chunking.strategies.default.min_chunk_size = 25
        settings.global_config.chunking.strategies.default.enable_semantic_analysis = (
            True
        )
        settings.global_config.chunking.strategies.default.enable_entity_extraction = (
            True
        )

        settings.global_config.embedding = Mock()
        settings.global_config.embedding.tokenizer = "none"
        return settings

    @pytest.fixture
    def sample_document(self):
        """Create a sample document for testing."""
        return Document(
            content="This is a test document with some content that should be chunked properly.",
            url="http://example.com/test.txt",
            content_type="txt",
            source_type="test",
            source="test_source",
            title="Test Document",
            metadata={"file_name": "test.txt", "source": "test"},
        )

    @pytest.fixture
    def long_document(self):
        """Create a long document for testing chunking limits."""
        content = "This is a sentence. " * 1000  # Create long content
        return Document(
            content=content,
            url="http://example.com/long.txt",
            content_type="txt",
            source_type="test",
            source="test_source",
            title="Long Document",
            metadata={"file_name": "long.txt", "source": "test"},
        )

    @pytest.fixture
    def empty_document(self):
        """Create an empty document for testing."""
        return Document(
            content="",
            url="http://example.com/empty.txt",
            content_type="txt",
            source_type="test",
            source="test_source",
            title="Empty Document",
            metadata={"file_name": "empty.txt", "source": "test"},
        )

    def test_initialization_with_tokenizer(self, mock_settings):
        """Test initialization with tokenizer."""
        with patch(
            "qdrant_loader.core.chunking.strategy.base_strategy.tiktoken"
        ) as mock_tiktoken:
            mock_encoding = Mock()
            mock_tiktoken.get_encoding.return_value = mock_encoding

            with patch(
                "qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"
            ):
                strategy = DefaultChunkingStrategy(mock_settings)

                assert strategy.settings == mock_settings
                assert strategy.chunk_size == 100
                assert strategy.chunk_overlap == 20
                assert strategy.encoding == mock_encoding
                mock_tiktoken.get_encoding.assert_called_once_with("cl100k_base")

    def test_initialization_without_tokenizer(self, mock_settings_no_tokenizer):
        """Test initialization without tokenizer."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = DefaultChunkingStrategy(mock_settings_no_tokenizer)

            assert strategy.settings == mock_settings_no_tokenizer
            assert strategy.chunk_size == 50
            assert strategy.chunk_overlap == 10
            assert strategy.encoding is None

    def test_initialization_tokenizer_error(self, mock_settings):
        """Test initialization when tokenizer fails to load."""
        with patch(
            "qdrant_loader.core.chunking.strategy.base_strategy.tiktoken"
        ) as mock_tiktoken:
            mock_tiktoken.get_encoding.side_effect = Exception("Tokenizer error")

            with patch(
                "qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"
            ):
                strategy = DefaultChunkingStrategy(mock_settings)

                assert strategy.encoding is None

    def test_chunk_document_success(self, mock_settings, sample_document):
        """Test successful document chunking."""
        with patch(
            "qdrant_loader.core.chunking.strategy.base_strategy.tiktoken"
        ) as mock_tiktoken:
            mock_encoding = Mock()
            mock_encoding.encode.return_value = list(range(50))  # 50 tokens
            mock_encoding.decode.return_value = "chunk content"
            mock_tiktoken.get_encoding.return_value = mock_encoding

            with patch(
                "qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"
            ):
                strategy = DefaultChunkingStrategy(mock_settings)

                # Mock the modular chunk processor instead of _create_chunk_document
                with patch.object(
                    strategy.chunk_processor, "create_chunk_document"
                ) as mock_create_chunk:
                    mock_chunk_doc = Mock(spec=Document)
                    mock_chunk_doc.id = "test_id"
                    mock_chunk_doc.metadata = {"parent_document_id": sample_document.id}
                    mock_chunk_doc.content = "chunk content"
                    mock_create_chunk.return_value = mock_chunk_doc

                    result = strategy.chunk_document(sample_document)

                    assert len(result) >= 1
                    assert mock_create_chunk.called

    def test_chunk_document_empty_content(self, mock_settings, empty_document):
        """Test chunking document with empty content."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = DefaultChunkingStrategy(mock_settings)

            result = strategy.chunk_document(empty_document)

            # Empty content returns single empty chunk based on section splitter behavior
            assert len(result) == 1
            assert result[0].content == ""

    def test_chunk_document_large_document(self, mock_settings, long_document):
        """Test chunking large document with chunk limit."""
        with patch(
            "qdrant_loader.core.chunking.strategy.base_strategy.tiktoken"
        ) as mock_tiktoken:
            mock_encoding = Mock()
            # Create many tokens to trigger chunking
            mock_encoding.encode.return_value = list(range(10000))
            mock_encoding.decode.return_value = "chunk content"
            mock_tiktoken.get_encoding.return_value = mock_encoding

            with patch(
                "qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"
            ):
                strategy = DefaultChunkingStrategy(mock_settings)

                # Force the section splitter to return more chunks than the limit
                with patch.object(
                    strategy.section_splitter, "split_sections"
                ) as mock_split:
                    # Return more chunks than the limit
                    mock_chunks_metadata = [
                        {"content": "chunk", "metadata": {"section_type": "paragraph"}}
                        for _ in range(MAX_CHUNKS_TO_PROCESS + 10)
                    ]
                    mock_split.return_value = mock_chunks_metadata

                    with patch(
                        "qdrant_loader.core.chunking.strategy.default_strategy.logger"
                    ) as mock_logger:
                        result = strategy.chunk_document(long_document)

                        # Should be limited to MAX_CHUNKS_TO_PROCESS
                        assert len(result) == MAX_CHUNKS_TO_PROCESS
                        mock_logger.warning.assert_called()

    def test_chunk_document_with_custom_chunk_size(
        self, mock_settings, sample_document
    ):
        """Test chunking with custom chunk size and overlap."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = DefaultChunkingStrategy(mock_settings)
            # Manually set the chunk size and overlap after initialization
            strategy.chunk_size = 200
            strategy.chunk_overlap = 50

            assert strategy.chunk_size == 200
            assert strategy.chunk_overlap == 50

    def test_chunk_document_generates_unique_ids(self, mock_settings, sample_document):
        """Test that chunk documents get unique IDs."""
        with patch(
            "qdrant_loader.core.chunking.strategy.base_strategy.tiktoken"
        ) as mock_tiktoken:
            mock_encoding = Mock()
            mock_encoding.encode.return_value = list(
                range(200)
            )  # Enough for multiple chunks
            mock_encoding.decode.side_effect = lambda tokens: f"chunk_{len(tokens)}"
            mock_tiktoken.get_encoding.return_value = mock_encoding

            with patch(
                "qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"
            ):
                strategy = DefaultChunkingStrategy(mock_settings)

                # Create a longer document that will definitely be split
                long_content = (
                    "This is a very long document with lots of content that should be split into multiple chunks when using character-based chunking. "
                    * 5
                )
                sample_document.content = long_content
                assert (
                    len(long_content) > 500
                )  # Ensure it's much longer than chunk_size

                result = strategy.chunk_document(sample_document)

                # Verify unique IDs were generated - IDs are generated by the chunk processor now
                assert len(result) > 1
                ids = [chunk.id for chunk in result]
                assert len(ids) == len(set(ids))  # All IDs should be unique

    def test_chunk_document_preserves_metadata(self, mock_settings, sample_document):
        """Test that chunking preserves and enhances metadata."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = DefaultChunkingStrategy(mock_settings)

            result = strategy.chunk_document(sample_document)

            # Verify metadata preservation and enhancement
            for chunk_doc in result:
                assert "parent_document_id" in chunk_doc.metadata
                assert chunk_doc.metadata["parent_document_id"] == sample_document.id

    def test_chunk_document_logging(self, mock_settings, sample_document):
        """Test that chunking includes proper logging."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = DefaultChunkingStrategy(mock_settings)

            with patch(
                "qdrant_loader.core.chunking.strategy.default_strategy.logger"
            ) as mock_logger:
                strategy.chunk_document(sample_document)

                # Verify logging calls - check for the new logging messages
                assert mock_logger.debug.call_count >= 2  # Start and end logging

                # Check that logging includes relevant information
                # Find the chunk processing debug call (not shutdown or other calls)
                chunk_processing_calls = [
                    call
                    for call in mock_logger.debug.call_args_list
                    if len(call[0]) > 0 and "Analyzing document structure" in call[0][0]
                ]
                assert (
                    len(chunk_processing_calls) >= 1
                ), f"Expected chunking debug call not found. Calls: {[call[0][0] for call in mock_logger.debug.call_args_list]}"
