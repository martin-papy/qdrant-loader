"""Tests for TextMetadataExtractor."""

import pytest
from qdrant_loader.core.chunking.strategy.default.text_metadata_extractor import (
    TextMetadataExtractor,
)
from qdrant_loader.core.document import Document


class TestTextMetadataExtractor:
    """Test the TextMetadataExtractor class."""

    @pytest.fixture
    def extractor(self):
        """Create a TextMetadataExtractor instance."""
        return TextMetadataExtractor()

    @pytest.fixture
    def sample_document(self):
        """Create a sample document for testing."""
        return Document(
            title="Test Document",
            content_type="text",
            content="Sample document content",
            metadata={"source": "test"},
            source="test.txt",
            source_type="file",
            url="file:///test.txt",
        )

    def test_extract_hierarchical_metadata_basic(self, extractor, sample_document):
        """Test basic hierarchical metadata extraction."""
        content = "This is a test document. It has multiple sentences. And multiple paragraphs.\n\nThis is the second paragraph."
        chunk_metadata = {"chunk_index": 0}

        result = extractor.extract_hierarchical_metadata(
            content, chunk_metadata, sample_document
        )

        assert result["word_count"] == 17
        assert result["character_count"] == len(content)
        assert result["paragraph_count"] == 2
        assert result["sentence_count"] == 4
        assert result["content_type"] == "text"
        assert result["language"] == "en"
        assert "text_density" in result
        assert "formatting_indicators" in result

    def test_extract_hierarchical_metadata_empty_content(
        self, extractor, sample_document
    ):
        """Test metadata extraction with empty content."""
        content = ""
        chunk_metadata = {"chunk_index": 0}

        result = extractor.extract_hierarchical_metadata(
            content, chunk_metadata, sample_document
        )

        assert result["word_count"] == 0
        assert result["character_count"] == 0
        assert result["paragraph_count"] == 0
        assert result["sentence_count"] == 0
        assert result["avg_word_length"] == 0.0

    def test_extract_entities_basic(self, extractor):
        """Test basic entity extraction."""
        text = "John Smith works at Microsoft Corporation in Seattle. He knows Dr. Johnson from Stanford University."

        entities = extractor.extract_entities(text)

        assert "John Smith" in entities
        assert "Microsoft Corporation" in entities
        assert "Seattle" in entities
        assert "Stanford University" in entities
        # Should filter out false positives like "He" and "Dr"
        assert "He" not in entities
        assert "Dr" not in entities

    def test_extract_entities_filters_stop_words(self, extractor):
        """Test that entity extraction filters out stop words."""
        text = "The quick brown fox jumps. This is a test. That was interesting."

        entities = extractor.extract_entities(text)

        # Should not include common stop words
        assert "The" not in entities
        assert "This" not in entities
        assert "That" not in entities

    def test_extract_entities_empty_text(self, extractor):
        """Test entity extraction with empty text."""
        entities = extractor.extract_entities("")
        assert entities == []

    def test_split_sentences(self, extractor):
        """Test sentence splitting functionality."""
        content = "First sentence. Second sentence! Third sentence? Short."

        sentences = extractor._split_sentences(content)

        assert len(sentences) == 4
        assert "First sentence." in sentences
        assert "Second sentence!" in sentences
        assert "Third sentence?" in sentences
        assert "Short." in sentences

    def test_split_sentences_filters_short(self, extractor):
        """Test that sentence splitting filters out very short fragments."""
        content = "Real sentence. A. B. Another real sentence."

        sentences = extractor._split_sentences(content)

        # Should include real sentences but filter out single letters
        assert "Real sentence." in sentences
        assert "Another real sentence." in sentences
        assert "A." not in sentences
        assert "B." not in sentences

    def test_calculate_avg_word_length(self, extractor):
        """Test average word length calculation."""
        content = "The quick brown fox"  # Lengths: 3, 5, 5, 3 = avg 4.0

        avg_length = extractor._calculate_avg_word_length(content)

        assert avg_length == 4.0

    def test_calculate_avg_word_length_empty(self, extractor):
        """Test average word length with empty content."""
        avg_length = extractor._calculate_avg_word_length("")
        assert avg_length == 0.0

    def test_estimate_reading_time(self, extractor):
        """Test reading time estimation."""
        # 200 words should take 1 minute
        words = ["word"] * 200
        content = " ".join(words)

        reading_time = extractor._estimate_reading_time(content)

        assert reading_time == 1.0

    def test_detect_language_english(self, extractor):
        """Test English language detection."""
        content = "The quick brown fox jumps over the lazy dog in the park."

        language = extractor._detect_language(content)

        assert language == "en"

    def test_detect_language_unknown(self, extractor):
        """Test unknown language detection."""
        content = "Lorem ipsum dolor sit amet consectetur adipiscing elit."

        language = extractor._detect_language(content)

        assert language == "unknown"

    def test_detect_language_insufficient_content(self, extractor):
        """Test language detection with insufficient content."""
        content = "Short text."

        language = extractor._detect_language(content)

        assert language == "unknown"

    def test_calculate_text_density(self, extractor):
        """Test text density calculation."""
        content = "Hello, World! 123"  # Mix of alphanumeric, whitespace, punctuation

        density = extractor._calculate_text_density(content)

        assert "alphanumeric_ratio" in density
        assert "whitespace_ratio" in density
        assert "punctuation_ratio" in density
        assert 0 <= density["alphanumeric_ratio"] <= 1
        assert 0 <= density["whitespace_ratio"] <= 1
        assert 0 <= density["punctuation_ratio"] <= 1

    def test_calculate_text_density_empty(self, extractor):
        """Test text density calculation with empty content."""
        density = extractor._calculate_text_density("")

        assert density["alphanumeric_ratio"] == 0.0
        assert density["whitespace_ratio"] == 0.0
        assert density["punctuation_ratio"] == 0.0

    def test_analyze_formatting_bullet_points(self, extractor):
        """Test formatting analysis for bullet points."""
        content = "• First item\n• Second item\n• Third item"

        formatting = extractor._analyze_formatting(content)

        assert formatting["has_bullet_points"] is True
        assert formatting["has_numbered_lists"] is False

    def test_analyze_formatting_numbered_lists(self, extractor):
        """Test formatting analysis for numbered lists."""
        content = "1. First item\n2. Second item\n3. Third item"

        formatting = extractor._analyze_formatting(content)

        assert formatting["has_numbered_lists"] is True
        assert formatting["has_bullet_points"] is False

    def test_analyze_formatting_email_and_urls(self, extractor):
        """Test formatting analysis for emails and URLs."""
        content = "Contact us at test@example.com or visit https://example.com"

        formatting = extractor._analyze_formatting(content)

        assert formatting["has_email_addresses"] is True
        assert formatting["has_urls"] is True

    def test_analyze_formatting_phone_numbers(self, extractor):
        """Test formatting analysis for phone numbers."""
        content = "Call us at 123-456-7890 or 555.123.4567"

        formatting = extractor._analyze_formatting(content)

        assert formatting["has_phone_numbers"] is True

    def test_analyze_formatting_dates_and_currency(self, extractor):
        """Test formatting analysis for dates and currency."""
        content = "The meeting is on 12/25/2023 and costs $100.50"

        formatting = extractor._analyze_formatting(content)

        assert formatting["has_dates"] is True
        assert formatting["has_currency"] is True

    def test_analyze_formatting_percentages(self, extractor):
        """Test formatting analysis for percentages."""
        content = "The success rate is 95.5% and growing"

        formatting = extractor._analyze_formatting(content)

        assert formatting["has_percentages"] is True

    def test_analyze_formatting_no_special_formatting(self, extractor):
        """Test formatting analysis with plain text."""
        content = "This is just plain text without any special formatting"

        formatting = extractor._analyze_formatting(content)

        assert formatting["has_bullet_points"] is False
        assert formatting["has_numbered_lists"] is False
        assert formatting["has_email_addresses"] is False
        assert formatting["has_urls"] is False
        assert formatting["has_phone_numbers"] is False
        assert formatting["has_dates"] is False
        assert formatting["has_currency"] is False
        assert formatting["has_percentages"] is False

    def test_preserves_original_metadata(self, extractor, sample_document):
        """Test that original chunk metadata is preserved."""
        content = "Test content"
        original_metadata = {"chunk_index": 5, "original_key": "original_value"}

        result = extractor.extract_hierarchical_metadata(
            content, original_metadata, sample_document
        )

        assert result["chunk_index"] == 5
        assert result["original_key"] == "original_value"

    def test_metadata_structure(self, extractor, sample_document):
        """Test that metadata has the expected structure."""
        content = "This is a comprehensive test of the metadata structure."
        chunk_metadata = {"chunk_index": 0}

        result = extractor.extract_hierarchical_metadata(
            content, chunk_metadata, sample_document
        )

        # Check required keys
        required_keys = [
            "word_count",
            "character_count",
            "paragraph_count",
            "sentence_count",
            "avg_word_length",
            "reading_time_minutes",
            "content_type",
            "language",
            "text_density",
            "formatting_indicators",
        ]

        for key in required_keys:
            assert key in result, f"Missing required key: {key}"

        # Check data types
        assert isinstance(result["word_count"], int)
        assert isinstance(result["character_count"], int)
        assert isinstance(result["paragraph_count"], int)
        assert isinstance(result["sentence_count"], int)
        assert isinstance(result["avg_word_length"], float)
        assert isinstance(result["reading_time_minutes"], float)
        assert isinstance(result["content_type"], str)
        assert isinstance(result["language"], str)
        assert isinstance(result["text_density"], dict)
        assert isinstance(result["formatting_indicators"], dict)
