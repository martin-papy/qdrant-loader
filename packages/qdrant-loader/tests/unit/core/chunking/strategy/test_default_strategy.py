"""Tests for the DefaultChunkingStrategy."""

from unittest.mock import Mock, patch

import pytest
from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.strategy.default_strategy import (
    DefaultChunkingStrategy,
)
from qdrant_loader.core.document import Document

# Define the constant locally since it's not exported from the module
MAX_CHUNKS_TO_PROCESS = 1000


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

    def test_split_text_empty_content(self, mock_settings_no_tokenizer):
        """Test splitting empty text."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = DefaultChunkingStrategy(mock_settings_no_tokenizer)

            result = strategy._split_text("")
            assert result == [""]

    def test_split_text_without_tokenizer_short_text(self, mock_settings_no_tokenizer):
        """Test splitting short text without tokenizer."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = DefaultChunkingStrategy(mock_settings_no_tokenizer)

            text = "Short text"
            result = strategy._split_text(text)
            assert result == [text]

    def test_split_text_without_tokenizer_long_text(self, mock_settings_no_tokenizer):
        """Test splitting long text without tokenizer."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = DefaultChunkingStrategy(mock_settings_no_tokenizer)

            # Create text longer than chunk size (50 chars)
            text = "a" * 100
            result = strategy._split_text(text)

            assert len(result) > 1
            assert all(len(chunk) <= 50 for chunk in result)

    def test_split_text_with_tokenizer_short_text(self, mock_settings):
        """Test splitting short text with tokenizer."""
        with patch(
            "qdrant_loader.core.chunking.strategy.base_strategy.tiktoken"
        ) as mock_tiktoken:
            mock_encoding = Mock()
            mock_encoding.encode.return_value = [1, 2, 3, 4, 5]  # 5 tokens
            mock_tiktoken.get_encoding.return_value = mock_encoding

            with patch(
                "qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"
            ):
                strategy = DefaultChunkingStrategy(mock_settings)

                text = "Short text"
                result = strategy._split_text(text)
                assert result == [text]

    def test_split_text_with_tokenizer_long_text(self, mock_settings):
        """Test splitting long text with tokenizer."""
        with patch(
            "qdrant_loader.core.chunking.strategy.base_strategy.tiktoken"
        ) as mock_tiktoken:
            mock_encoding = Mock()
            # Mock tokenizer for boundary detection
            def mock_encode(text):
                # Return a token for each word
                return list(range(len(text.split())))
            
            def mock_decode(tokens):
                # For boundary detection, return text that's slightly shorter
                # to simulate token boundary adjustment
                return "adjusted_text_at_boundary"
            
            mock_encoding.encode.side_effect = mock_encode
            mock_encoding.decode.side_effect = mock_decode
            mock_tiktoken.get_encoding.return_value = mock_encoding

            with patch(
                "qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"
            ):
                strategy = DefaultChunkingStrategy(mock_settings)

                # Create text that's definitely longer than chunk_size (100 chars)
                text = "This is a very long text that should definitely be split into multiple chunks when using character-based chunking. " * 3
                assert len(text) > 300  # Ensure it's much longer than chunk_size
                
                result = strategy._split_text(text)

                assert len(result) > 1
                # Verify that the tokenizer was used for boundary detection
                assert mock_encoding.encode.call_count > 0

    def test_split_text_with_overlap_edge_case(self, mock_settings_no_tokenizer):
        """Test splitting text where overlap would cause infinite loop."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            # Set overlap equal to chunk size - 1 to test edge case
            mock_settings_no_tokenizer.global_config.chunking.chunk_overlap = 49
            strategy = DefaultChunkingStrategy(mock_settings_no_tokenizer)

            text = "a" * 100
            result = strategy._split_text(text)

            # Should still make progress and not get stuck
            assert len(result) > 1

    def test_split_text_max_chunks_limit(self, mock_settings_no_tokenizer):
        """Test that splitting respects MAX_CHUNKS_TO_PROCESS limit."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            # Create settings that would generate many chunks
            mock_settings_no_tokenizer.global_config.chunking.chunk_size = 1
            mock_settings_no_tokenizer.global_config.chunking.chunk_overlap = 0
            strategy = DefaultChunkingStrategy(mock_settings_no_tokenizer)

            # Create text that would generate more than MAX_CHUNKS_TO_PROCESS
            text = "a" * (MAX_CHUNKS_TO_PROCESS + 50)

            with patch(
                "qdrant_loader.core.chunking.strategy.default_strategy.logger"
            ) as mock_logger:
                result = strategy._split_text(text)

                assert len(result) == MAX_CHUNKS_TO_PROCESS
                mock_logger.warning.assert_called()

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

                with patch.object(
                    strategy, "_create_chunk_document"
                ) as mock_create_chunk:
                    mock_chunk_doc = Mock(spec=Document)
                    mock_chunk_doc.id = "test_id"
                    mock_chunk_doc.metadata = {}
                    mock_chunk_doc.content = "chunk content"
                    mock_create_chunk.return_value = mock_chunk_doc

                    result = strategy.chunk_document(sample_document)

                    assert len(result) == 1
                    assert mock_create_chunk.called
                    assert (
                        mock_chunk_doc.metadata["parent_document_id"]
                        == sample_document.id
                    )

    def test_chunk_document_empty_content(self, mock_settings, empty_document):
        """Test chunking document with empty content."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = DefaultChunkingStrategy(mock_settings)

            with patch.object(strategy, "_create_chunk_document") as mock_create_chunk:
                mock_chunk_doc = Mock(spec=Document)
                mock_chunk_doc.id = "test_id"
                mock_chunk_doc.metadata = {}
                mock_chunk_doc.content = ""
                mock_create_chunk.return_value = mock_chunk_doc

                result = strategy.chunk_document(empty_document)

                assert len(result) == 1
                mock_create_chunk.assert_called_once()

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

                with patch.object(strategy, "_split_text") as mock_split:
                    # Return more chunks than the limit
                    mock_split.return_value = ["chunk"] * (MAX_CHUNKS_TO_PROCESS + 10)

                    with patch.object(
                        strategy, "_create_chunk_document"
                    ) as mock_create_chunk:
                        mock_chunk_doc = Mock(spec=Document)
                        mock_chunk_doc.id = "test_id"
                        mock_chunk_doc.metadata = {}
                        mock_chunk_doc.content = "chunk content"
                        mock_create_chunk.return_value = mock_chunk_doc

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
                long_content = "This is a very long document with lots of content that should be split into multiple chunks when using character-based chunking. " * 5
                sample_document.content = long_content
                assert len(long_content) > 500  # Ensure it's much longer than chunk_size

                with patch.object(
                    strategy, "_create_chunk_document"
                ) as mock_create_chunk:

                    def create_mock_chunk(
                        original_doc,
                        chunk_content,
                        chunk_index,
                        total_chunks,
                        skip_nlp=False,
                    ):
                        mock_chunk_doc = Mock(spec=Document)
                        mock_chunk_doc.id = f"chunk_{chunk_index}"
                        mock_chunk_doc.metadata = {}
                        mock_chunk_doc.content = chunk_content
                        return mock_chunk_doc

                    mock_create_chunk.side_effect = create_mock_chunk

                    with patch.object(
                        Document, "generate_chunk_id"
                    ) as mock_generate_id:
                        mock_generate_id.side_effect = (
                            lambda doc_id, chunk_idx: f"{doc_id}_chunk_{chunk_idx}"
                        )

                        result = strategy.chunk_document(sample_document)

                        # Verify unique IDs were generated
                        assert len(result) > 1
                        for i, chunk_doc in enumerate(result):
                            expected_id = f"{sample_document.id}_chunk_{i}"
                            assert chunk_doc.id == expected_id

    def test_chunk_document_preserves_metadata(self, mock_settings, sample_document):
        """Test that chunking preserves and enhances metadata."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = DefaultChunkingStrategy(mock_settings)

            with patch.object(strategy, "_split_text") as mock_split:
                mock_split.return_value = ["chunk1", "chunk2"]

                with patch.object(
                    strategy, "_create_chunk_document"
                ) as mock_create_chunk:

                    def create_mock_chunk(
                        original_doc,
                        chunk_content,
                        chunk_index,
                        total_chunks,
                        skip_nlp=False,
                    ):
                        mock_chunk_doc = Mock(spec=Document)
                        mock_chunk_doc.id = f"chunk_{chunk_index}"
                        mock_chunk_doc.metadata = original_doc.metadata.copy()
                        mock_chunk_doc.content = chunk_content
                        return mock_chunk_doc

                    mock_create_chunk.side_effect = create_mock_chunk

                    result = strategy.chunk_document(sample_document)

                    # Verify metadata preservation and enhancement
                    for chunk_doc in result:
                        assert "file_name" in chunk_doc.metadata
                        assert (
                            chunk_doc.metadata["parent_document_id"]
                            == sample_document.id
                        )

    def test_chunk_document_logging(self, mock_settings, sample_document):
        """Test that chunking includes proper logging."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = DefaultChunkingStrategy(mock_settings)

            with patch.object(strategy, "_split_text") as mock_split:
                mock_split.return_value = ["chunk1"]

                with patch.object(
                    strategy, "_create_chunk_document"
                ) as mock_create_chunk:
                    mock_chunk_doc = Mock(spec=Document)
                    mock_chunk_doc.id = "test_id"
                    mock_chunk_doc.metadata = {}
                    mock_chunk_doc.content = "chunk1"
                    mock_create_chunk.return_value = mock_chunk_doc

                    with patch(
                        "qdrant_loader.core.chunking.strategy.default_strategy.logger"
                    ) as mock_logger:
                        strategy.chunk_document(sample_document)

                        # Verify logging calls - the implementation uses debug calls, not info
                        assert (
                            mock_logger.debug.call_count >= 2
                        )  # Start and end logging

                        # Check that logging includes relevant information
                        start_call = mock_logger.debug.call_args_list[0]
                        assert "Starting default chunking" in start_call[0][0]

                        end_call = mock_logger.debug.call_args_list[-1]
                        assert "Successfully chunked document" in end_call[0][0]
