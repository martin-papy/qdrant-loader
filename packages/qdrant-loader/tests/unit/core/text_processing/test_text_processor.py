"""Unit tests for text processor."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from qdrant_loader.config import Settings
from qdrant_loader.core.text_processing.text_processor import (
    MAX_ENTITIES_TO_EXTRACT,
    MAX_POS_TAGS_TO_EXTRACT,
    MAX_TEXT_LENGTH_FOR_SPACY,
    TextProcessor,
)


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = Mock(spec=Settings)

    # Mock global_config
    global_config = Mock()

    # Mock chunking config
    chunking_config = Mock()
    chunking_config.chunk_size = 1000
    chunking_config.chunk_overlap = 100

    # Mock semantic analysis config
    semantic_analysis_config = Mock()
    semantic_analysis_config.spacy_model = "en_core_web_md"

    global_config.chunking = chunking_config
    global_config.semantic_analysis = semantic_analysis_config
    settings.global_config = global_config

    return settings


class TestTextProcessor:
    """Test cases for TextProcessor class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock spaCy model and components
        self.mock_nlp = MagicMock()
        self.mock_doc = MagicMock()
        self.mock_nlp.return_value = self.mock_doc
        self.mock_nlp.pipe_names = ["tokenizer", "tagger", "parser", "ner"]
        self.mock_nlp.select_pipes = MagicMock()

        # Mock text splitter
        self.mock_text_splitter = MagicMock()
        self.mock_text_splitter.split_text = MagicMock(
            return_value=["chunk1", "chunk2"]
        )

    @patch("qdrant_loader.core.text_processing.text_processor.spacy.load")
    @patch(
        "qdrant_loader.core.text_processing.text_processor.RecursiveCharacterTextSplitter"
    )
    @patch("qdrant_loader.core.text_processing.text_processor.nltk")
    def test_init_successful_spacy_load(
        self, mock_nltk, mock_text_splitter_class, mock_spacy_load, mock_settings
    ):
        """Test successful initialization with spaCy model loading."""
        # Setup mocks
        mock_nltk.data.find.return_value = True  # NLTK data already exists
        mock_spacy_load.return_value = self.mock_nlp
        mock_text_splitter_class.return_value = self.mock_text_splitter

        # Initialize processor
        processor = TextProcessor(mock_settings)

        # Verify spaCy model loading
        mock_spacy_load.assert_called_once_with("en_core_web_md")
        assert processor.nlp == self.mock_nlp

        # Verify pipeline optimization
        self.mock_nlp.select_pipes.assert_called_once()

        # Verify text splitter initialization
        mock_text_splitter_class.assert_called_once()
        assert processor.text_splitter == self.mock_text_splitter

    @patch("qdrant_loader.core.text_processing.text_processor.spacy.load")
    @patch("qdrant_loader.core.text_processing.text_processor.download")
    @patch(
        "qdrant_loader.core.text_processing.text_processor.RecursiveCharacterTextSplitter"
    )
    @patch("qdrant_loader.core.text_processing.text_processor.nltk")
    def test_init_spacy_model_download(
        self,
        mock_nltk,
        mock_text_splitter_class,
        mock_download,
        mock_spacy_load,
        mock_settings,
    ):
        """Test initialization with spaCy model download."""
        # Setup mocks
        mock_nltk.data.find.return_value = True
        mock_spacy_load.side_effect = [
            OSError("Model not found"),
            self.mock_nlp,
        ]
        mock_text_splitter_class.return_value = self.mock_text_splitter

        # Initialize processor
        processor = TextProcessor(mock_settings)

        # Verify model download was triggered
        mock_download.assert_called_once_with("en_core_web_md")
        assert mock_spacy_load.call_count == 2
        assert processor.nlp == self.mock_nlp

    @patch("qdrant_loader.core.text_processing.text_processor.spacy.load")
    @patch(
        "qdrant_loader.core.text_processing.text_processor.RecursiveCharacterTextSplitter"
    )
    @patch("qdrant_loader.core.text_processing.text_processor.nltk")
    def test_init_nltk_data_download(
        self, mock_nltk, mock_text_splitter_class, mock_spacy_load, mock_settings
    ):
        """Test initialization with NLTK data download."""
        # Setup mocks
        mock_nltk.data.find.side_effect = [
            LookupError("Not found"),
            LookupError("Not found"),
        ]
        mock_nltk.download = MagicMock()
        mock_spacy_load.return_value = self.mock_nlp
        mock_text_splitter_class.return_value = self.mock_text_splitter

        # Initialize processor
        TextProcessor(mock_settings)

        # Verify NLTK downloads
        assert mock_nltk.download.call_count == 2
        mock_nltk.download.assert_any_call("punkt")
        mock_nltk.download.assert_any_call("stopwords")

    @patch("qdrant_loader.core.text_processing.text_processor.spacy.load")
    @patch(
        "qdrant_loader.core.text_processing.text_processor.RecursiveCharacterTextSplitter"
    )
    @patch("qdrant_loader.core.text_processing.text_processor.nltk")
    def test_process_text_success(
        self, mock_nltk, mock_text_splitter_class, mock_spacy_load, mock_settings
    ):
        """Test successful text processing."""
        # Setup mocks
        mock_nltk.data.find.return_value = True

        # Mock spaCy document processing
        mock_token1 = MagicMock()
        mock_token1.text = "Hello"
        mock_token1.pos_ = "INTJ"
        mock_token2 = MagicMock()
        mock_token2.text = "world"
        mock_token2.pos_ = "NOUN"

        mock_entity = MagicMock()
        mock_entity.text = "John"
        mock_entity.label_ = "PERSON"

        # Set up the mock document to return tokens when iterated
        def mock_iter(self):
            return iter([mock_token1, mock_token2])

        self.mock_doc.__iter__ = mock_iter
        self.mock_doc.ents = [mock_entity]

        # Set up the nlp mock to return the mock document when called
        self.mock_nlp.return_value = self.mock_doc
        self.mock_nlp.pipe_names = ["tokenizer", "tagger", "ner"]  # No parser
        mock_spacy_load.return_value = self.mock_nlp
        mock_text_splitter_class.return_value = self.mock_text_splitter

        # Initialize processor
        processor = TextProcessor(mock_settings)

        # Test text processing
        result = processor.process_text("Hello world")

        # Verify results
        assert result["tokens"] == ["Hello", "world"]
        assert result["entities"] == [("John", "PERSON")]
        assert result["pos_tags"] == [("Hello", "INTJ"), ("world", "NOUN")]
        assert result["chunks"] == ["chunk1", "chunk2"]

    @patch("qdrant_loader.core.text_processing.text_processor.spacy.load")
    @patch(
        "qdrant_loader.core.text_processing.text_processor.RecursiveCharacterTextSplitter"
    )
    @patch("qdrant_loader.core.text_processing.text_processor.nltk")
    def test_process_text_long_text_truncation(
        self, mock_nltk, mock_text_splitter_class, mock_spacy_load, mock_settings
    ):
        """Test text processing with long text truncation."""
        # Setup mocks
        mock_nltk.data.find.return_value = True
        mock_spacy_load.return_value = self.mock_nlp
        mock_text_splitter_class.return_value = self.mock_text_splitter

        # Mock empty document
        self.mock_doc.__iter__ = MagicMock(return_value=iter([]))
        self.mock_doc.ents = []

        # Initialize processor
        processor = TextProcessor(mock_settings)

        # Test with very long text
        long_text = "a" * (MAX_TEXT_LENGTH_FOR_SPACY + 1000)
        processor.process_text(long_text)

        # Verify text was truncated
        self.mock_nlp.assert_called_with("a" * MAX_TEXT_LENGTH_FOR_SPACY)

    @patch("qdrant_loader.core.text_processing.text_processor.spacy.load")
    @patch(
        "qdrant_loader.core.text_processing.text_processor.RecursiveCharacterTextSplitter"
    )
    @patch("qdrant_loader.core.text_processing.text_processor.nltk")
    def test_process_text_exception_handling(
        self, mock_nltk, mock_text_splitter_class, mock_spacy_load, mock_settings
    ):
        """Test text processing exception handling."""
        # Setup mocks
        mock_nltk.data.find.return_value = True
        mock_spacy_load.return_value = self.mock_nlp
        mock_text_splitter_class.return_value = self.mock_text_splitter

        # Mock spaCy to raise exception
        self.mock_nlp.side_effect = Exception("Processing failed")

        # Initialize processor
        processor = TextProcessor(mock_settings)

        # Test exception handling
        result = processor.process_text("test text")

        # Verify fallback results
        assert result["tokens"] == []
        assert result["entities"] == []
        assert result["pos_tags"] == []
        assert result["chunks"] == ["test text"]

    @patch("qdrant_loader.core.text_processing.text_processor.spacy.load")
    @patch(
        "qdrant_loader.core.text_processing.text_processor.RecursiveCharacterTextSplitter"
    )
    @patch("qdrant_loader.core.text_processing.text_processor.nltk")
    def test_get_entities_success(
        self, mock_nltk, mock_text_splitter_class, mock_spacy_load, mock_settings
    ):
        """Test successful entity extraction."""
        # Setup mocks
        mock_nltk.data.find.return_value = True
        mock_spacy_load.return_value = self.mock_nlp
        mock_text_splitter_class.return_value = self.mock_text_splitter

        # Mock entities
        mock_entity1 = MagicMock()
        mock_entity1.text = "John"
        mock_entity1.label_ = "PERSON"
        mock_entity2 = MagicMock()
        mock_entity2.text = "New York"
        mock_entity2.label_ = "GPE"

        self.mock_doc.ents = [mock_entity1, mock_entity2]

        # Initialize processor
        processor = TextProcessor(mock_settings)

        # Test entity extraction
        result = processor.get_entities("John lives in New York")

        # Verify results
        assert result == [("John", "PERSON"), ("New York", "GPE")]

    @patch("qdrant_loader.core.text_processing.text_processor.spacy.load")
    @patch(
        "qdrant_loader.core.text_processing.text_processor.RecursiveCharacterTextSplitter"
    )
    @patch("qdrant_loader.core.text_processing.text_processor.nltk")
    def test_get_entities_limit(
        self, mock_nltk, mock_text_splitter_class, mock_spacy_load, mock_settings
    ):
        """Test entity extraction with limit."""
        # Setup mocks
        mock_nltk.data.find.return_value = True
        mock_spacy_load.return_value = self.mock_nlp
        mock_text_splitter_class.return_value = self.mock_text_splitter

        # Mock many entities (more than limit)
        mock_entities = []
        for i in range(MAX_ENTITIES_TO_EXTRACT + 10):
            mock_entity = MagicMock()
            mock_entity.text = f"Entity{i}"
            mock_entity.label_ = "PERSON"
            mock_entities.append(mock_entity)

        self.mock_doc.ents = mock_entities

        # Initialize processor
        processor = TextProcessor(mock_settings)

        # Test entity extraction
        result = processor.get_entities("Many entities text")

        # Verify limit is respected
        assert len(result) == MAX_ENTITIES_TO_EXTRACT

    @patch("qdrant_loader.core.text_processing.text_processor.spacy.load")
    @patch(
        "qdrant_loader.core.text_processing.text_processor.RecursiveCharacterTextSplitter"
    )
    @patch("qdrant_loader.core.text_processing.text_processor.nltk")
    def test_get_entities_exception_handling(
        self, mock_nltk, mock_text_splitter_class, mock_spacy_load, mock_settings
    ):
        """Test entity extraction exception handling."""
        # Setup mocks
        mock_nltk.data.find.return_value = True
        mock_spacy_load.return_value = self.mock_nlp
        mock_text_splitter_class.return_value = self.mock_text_splitter

        # Mock spaCy to raise exception
        self.mock_nlp.side_effect = Exception("Entity extraction failed")

        # Initialize processor
        processor = TextProcessor(mock_settings)

        # Test exception handling
        result = processor.get_entities("test text")

        # Verify empty result
        assert result == []

    @patch("qdrant_loader.core.text_processing.text_processor.spacy.load")
    @patch(
        "qdrant_loader.core.text_processing.text_processor.RecursiveCharacterTextSplitter"
    )
    @patch("qdrant_loader.core.text_processing.text_processor.nltk")
    def test_get_pos_tags_success(
        self, mock_nltk, mock_text_splitter_class, mock_spacy_load, mock_settings
    ):
        """Test successful POS tagging."""
        # Setup mocks
        mock_nltk.data.find.return_value = True
        mock_spacy_load.return_value = self.mock_nlp
        mock_text_splitter_class.return_value = self.mock_text_splitter

        # Mock tokens
        mock_token1 = MagicMock()
        mock_token1.text = "Hello"
        mock_token1.pos_ = "INTJ"
        mock_token2 = MagicMock()
        mock_token2.text = "world"
        mock_token2.pos_ = "NOUN"

        self.mock_doc.__iter__ = MagicMock(
            return_value=iter([mock_token1, mock_token2])
        )

        # Initialize processor
        processor = TextProcessor(mock_settings)

        # Test POS tagging
        result = processor.get_pos_tags("Hello world")

        # Verify results
        assert result == [("Hello", "INTJ"), ("world", "NOUN")]

    @patch("qdrant_loader.core.text_processing.text_processor.spacy.load")
    @patch(
        "qdrant_loader.core.text_processing.text_processor.RecursiveCharacterTextSplitter"
    )
    @patch("qdrant_loader.core.text_processing.text_processor.nltk")
    def test_get_pos_tags_limit(
        self, mock_nltk, mock_text_splitter_class, mock_spacy_load, mock_settings
    ):
        """Test POS tagging with limit."""
        # Setup mocks
        mock_nltk.data.find.return_value = True
        mock_spacy_load.return_value = self.mock_nlp
        mock_text_splitter_class.return_value = self.mock_text_splitter

        # Mock many tokens (more than limit)
        mock_tokens = []
        for i in range(MAX_POS_TAGS_TO_EXTRACT + 10):
            mock_token = MagicMock()
            mock_token.text = f"word{i}"
            mock_token.pos_ = "NOUN"
            mock_tokens.append(mock_token)

        self.mock_doc.__iter__ = Mock(return_value=iter(mock_tokens))

        # Initialize processor
        processor = TextProcessor(mock_settings)

        # Test POS tagging
        result = processor.get_pos_tags("Many words text")

        # Verify limit is respected
        assert len(result) == MAX_POS_TAGS_TO_EXTRACT

    @patch("qdrant_loader.core.text_processing.text_processor.spacy.load")
    @patch(
        "qdrant_loader.core.text_processing.text_processor.RecursiveCharacterTextSplitter"
    )
    @patch("qdrant_loader.core.text_processing.text_processor.nltk")
    def test_get_pos_tags_exception_handling(
        self, mock_nltk, mock_text_splitter_class, mock_spacy_load, mock_settings
    ):
        """Test POS tagging exception handling."""
        # Setup mocks
        mock_nltk.data.find.return_value = True
        mock_spacy_load.return_value = self.mock_nlp
        mock_text_splitter_class.return_value = self.mock_text_splitter

        # Mock spaCy to raise exception
        self.mock_nlp.side_effect = Exception("POS tagging failed")

        # Initialize processor
        processor = TextProcessor(mock_settings)

        # Test exception handling
        result = processor.get_pos_tags("test text")

        # Verify empty result
        assert result == []

    @patch("qdrant_loader.core.text_processing.text_processor.spacy.load")
    @patch(
        "qdrant_loader.core.text_processing.text_processor.RecursiveCharacterTextSplitter"
    )
    @patch("qdrant_loader.core.text_processing.text_processor.nltk")
    def test_split_into_chunks_default(
        self, mock_nltk, mock_text_splitter_class, mock_spacy_load, mock_settings
    ):
        """Test text splitting with default settings."""
        # Setup mocks
        mock_nltk.data.find.return_value = True
        mock_spacy_load.return_value = self.mock_nlp
        mock_text_splitter_class.return_value = self.mock_text_splitter

        # Initialize processor
        processor = TextProcessor(mock_settings)

        # Test text splitting
        result = processor.split_into_chunks("Some long text to split")

        # Verify default splitter was used
        self.mock_text_splitter.split_text.assert_called_once_with(
            "Some long text to split"
        )
        assert result == ["chunk1", "chunk2"]

    @patch("qdrant_loader.core.text_processing.text_processor.spacy.load")
    @patch(
        "qdrant_loader.core.text_processing.text_processor.RecursiveCharacterTextSplitter"
    )
    @patch("qdrant_loader.core.text_processing.text_processor.nltk")
    def test_split_into_chunks_custom_size(
        self, mock_nltk, mock_text_splitter_class, mock_spacy_load, mock_settings
    ):
        """Test text splitting with custom chunk size."""
        # Setup mocks
        mock_nltk.data.find.return_value = True
        mock_spacy_load.return_value = self.mock_nlp

        # Create separate mock instances for default and custom splitters
        mock_default_splitter = MagicMock()
        mock_default_splitter.split_text = MagicMock(return_value=["chunk1", "chunk2"])

        mock_custom_splitter = MagicMock()
        mock_custom_splitter.split_text = MagicMock(
            return_value=["custom_chunk1", "custom_chunk2"]
        )

        # Set up the text splitter class to return different instances
        mock_text_splitter_class.side_effect = [
            mock_default_splitter,
            mock_custom_splitter,
        ]

        # Initialize processor
        processor = TextProcessor(mock_settings)

        # Test text splitting with custom size
        result = processor.split_into_chunks("Some long text to split", chunk_size=500)

        # Verify custom splitter was created and used
        assert mock_text_splitter_class.call_count == 2
        custom_call = mock_text_splitter_class.call_args_list[1]
        assert custom_call[1]["chunk_size"] == 500
        # The overlap calculation: min(chunk_size // 4, 50) = min(125, 50) = 50
        expected_overlap = 50  # Should be capped at 50, not 125
        actual_overlap = custom_call[1]["chunk_overlap"]
        assert actual_overlap == expected_overlap
        mock_custom_splitter.split_text.assert_called_once_with(
            "Some long text to split"
        )
        assert result == ["custom_chunk1", "custom_chunk2"]

    @patch("qdrant_loader.core.text_processing.text_processor.spacy.load")
    @patch(
        "qdrant_loader.core.text_processing.text_processor.RecursiveCharacterTextSplitter"
    )
    @patch("qdrant_loader.core.text_processing.text_processor.nltk")
    def test_split_into_chunks_exception_handling(
        self, mock_nltk, mock_text_splitter_class, mock_spacy_load, mock_settings
    ):
        """Test text splitting exception handling."""
        # Setup mocks
        mock_nltk.data.find.return_value = True
        mock_spacy_load.return_value = self.mock_nlp
        mock_text_splitter_class.return_value = self.mock_text_splitter

        # Mock text splitter to raise exception
        self.mock_text_splitter.split_text.side_effect = Exception("Splitting failed")

        # Initialize processor
        processor = TextProcessor(mock_settings)

        # Test exception handling
        result = processor.split_into_chunks("test text")

        # Verify fallback result
        assert result == ["test text"]

    @patch("qdrant_loader.core.text_processing.text_processor.spacy.load")
    @patch(
        "qdrant_loader.core.text_processing.text_processor.RecursiveCharacterTextSplitter"
    )
    @patch("qdrant_loader.core.text_processing.text_processor.nltk")
    def test_split_into_chunks_empty_text(
        self, mock_nltk, mock_text_splitter_class, mock_spacy_load, mock_settings
    ):
        """Test text splitting with empty text."""
        # Setup mocks
        mock_nltk.data.find.return_value = True
        mock_spacy_load.return_value = self.mock_nlp
        mock_text_splitter_class.return_value = self.mock_text_splitter

        # Mock text splitter to raise exception
        self.mock_text_splitter.split_text.side_effect = Exception("Splitting failed")

        # Initialize processor
        processor = TextProcessor(mock_settings)

        # Test with empty text
        result = processor.split_into_chunks("")

        # Verify empty result
        assert result == []

    @patch("qdrant_loader.core.text_processing.text_processor.spacy.load")
    @patch(
        "qdrant_loader.core.text_processing.text_processor.RecursiveCharacterTextSplitter"
    )
    @patch("qdrant_loader.core.text_processing.text_processor.nltk")
    def test_pipeline_optimization_no_parser(
        self, mock_nltk, mock_text_splitter_class, mock_spacy_load, mock_settings
    ):
        """Test pipeline optimization when parser is not present."""
        # Setup mocks
        mock_nltk.data.find.return_value = True
        mock_spacy_load.return_value = self.mock_nlp
        mock_text_splitter_class.return_value = self.mock_text_splitter

        # Mock pipeline without parser
        self.mock_nlp.pipe_names = ["tokenizer", "tagger", "ner"]

        # Initialize processor
        TextProcessor(mock_settings)

        # Verify select_pipes was not called (no parser to remove)
        self.mock_nlp.select_pipes.assert_not_called()

    @patch("qdrant_loader.core.text_processing.text_processor.spacy.load")
    @patch(
        "qdrant_loader.core.text_processing.text_processor.RecursiveCharacterTextSplitter"
    )
    @patch("qdrant_loader.core.text_processing.text_processor.nltk")
    def test_custom_chunk_size_overlap_calculation(
        self, mock_nltk, mock_text_splitter_class, mock_spacy_load, mock_settings
    ):
        """Test custom chunk size overlap calculation."""
        # Setup mocks
        mock_nltk.data.find.return_value = True
        mock_spacy_load.return_value = self.mock_nlp
        mock_text_splitter_class.return_value = self.mock_text_splitter

        # Mock custom text splitter
        mock_custom_splitter = MagicMock()
        mock_text_splitter_class.side_effect = [
            self.mock_text_splitter,
            mock_custom_splitter,
        ]

        # Initialize processor
        processor = TextProcessor(mock_settings)

        # Test with large chunk size (should cap overlap at 50)
        processor.split_into_chunks("test", chunk_size=1000)

        # Verify overlap was capped at 50
        custom_call = mock_text_splitter_class.call_args_list[1]
        assert custom_call[1]["chunk_overlap"] == 50  # Capped at 50, not 250
