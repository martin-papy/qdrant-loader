"""Unit tests for the keyword enricher.

POC2-006: Tests for keyword extraction functionality.
"""

import pytest

from qdrant_loader.core.enrichers.keyword_enricher import (
    KeywordEnricher,
    KeywordEnricherConfig,
    STOP_WORDS,
)
from qdrant_loader.core.document import Document


# Create a minimal mock settings object
class MockSettings:
    """Minimal mock settings for testing."""
    pass


def create_test_document(content: str, **kwargs) -> Document:
    """Create a document for testing."""
    return Document(
        content=content,
        source="test",
        source_type="test",
        url="http://test.com",
        title=kwargs.get("title", "Test Document"),
        content_type="text/plain",
        metadata=kwargs.get("metadata", {}),
    )


class TestKeywordEnricherConfig:
    """Tests for KeywordEnricherConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = KeywordEnricherConfig()
        assert config.max_keywords == 20
        assert config.min_word_length == 3
        assert config.max_word_length == 30
        assert config.min_frequency == 1
        assert config.include_bigrams is True
        assert config.include_trigrams is False

    def test_custom_values(self):
        """Test custom configuration values."""
        config = KeywordEnricherConfig(
            max_keywords=10,
            include_bigrams=False,
            custom_stop_words={"custom"},
        )
        assert config.max_keywords == 10
        assert config.include_bigrams is False
        assert "custom" in config.custom_stop_words


class TestKeywordEnricher:
    """Tests for KeywordEnricher class."""

    @pytest.fixture
    def enricher(self):
        """Create a keyword enricher for testing."""
        return KeywordEnricher(MockSettings())

    @pytest.fixture
    def enricher_no_bigrams(self):
        """Create enricher without bigrams."""
        config = KeywordEnricherConfig(include_bigrams=False)
        return KeywordEnricher(MockSettings(), config)

    def test_enricher_name(self, enricher):
        """Test enricher name property."""
        assert enricher.name == "keyword_enricher"

    def test_should_process_normal_document(self, enricher):
        """Test that normal documents are processed."""
        # Content must be > 100 chars to pass the check
        doc = create_test_document(
            "This is a normal document with enough content to process. "
            "It contains multiple sentences and should be long enough for processing."
        )
        should, reason = enricher.should_process(doc)
        assert should is True
        assert reason is None

    def test_should_skip_short_document(self, enricher):
        """Test that short documents are skipped."""
        doc = create_test_document("Short")
        should, reason = enricher.should_process(doc)
        assert should is False
        assert reason == "content_too_short"

    @pytest.mark.asyncio
    async def test_enrich_extracts_keywords(self, enricher):
        """Test that keywords are extracted from content."""
        doc = create_test_document(
            "Machine learning is transforming how we analyze data. "
            "Machine learning models can process large datasets efficiently. "
            "Data analysis with machine learning provides valuable insights."
        )

        result = await enricher.enrich(doc)

        assert result.success is True
        assert "keywords" in result.metadata
        assert "keyword_list" in result.metadata
        assert "keyword_count" in result.metadata
        assert result.metadata["keyword_count"] > 0

    @pytest.mark.asyncio
    async def test_enrich_frequency_scoring(self, enricher_no_bigrams):
        """Test that frequently occurring words score higher."""
        doc = create_test_document(
            "Python is great. Python is powerful. Python is popular. "
            "Ruby is nice. Ruby works."
        )

        result = await enricher_no_bigrams.enrich(doc)

        keywords = result.metadata["keywords"]
        # Find python and ruby scores
        python_kw = next((k for k in keywords if k["word"] == "python"), None)
        ruby_kw = next((k for k in keywords if k["word"] == "ruby"), None)

        assert python_kw is not None
        assert python_kw["frequency"] == 3

        if ruby_kw:
            assert python_kw["score"] >= ruby_kw["score"]

    @pytest.mark.asyncio
    async def test_enrich_stop_words_filtered(self, enricher_no_bigrams):
        """Test that stop words are not included in keywords."""
        doc = create_test_document(
            "The quick brown fox jumps over the lazy dog. "
            "The fox was very quick and the dog was very lazy."
        )

        result = await enricher_no_bigrams.enrich(doc)

        keyword_list = result.metadata["keyword_list"]
        # Common stop words should not be in keywords
        for stop_word in ["the", "and", "was", "over"]:
            assert stop_word not in keyword_list

    @pytest.mark.asyncio
    async def test_enrich_bigrams(self, enricher):
        """Test that bigrams are extracted when enabled."""
        doc = create_test_document(
            "Machine learning algorithms are powerful. "
            "Machine learning models work well. "
            "Machine learning is transforming data science."
        )

        result = await enricher.enrich(doc)

        keyword_list = result.metadata["keyword_list"]
        # Should find "machine learning" bigram
        has_bigram = any(" " in kw for kw in keyword_list)
        assert has_bigram is True

    @pytest.mark.asyncio
    async def test_enrich_max_keywords_limit(self):
        """Test that max_keywords limit is respected."""
        config = KeywordEnricherConfig(max_keywords=5, include_bigrams=False)
        enricher = KeywordEnricher(MockSettings(), config)

        # Create document with many unique words
        words = " ".join([f"word{i} " * 2 for i in range(50)])
        doc = create_test_document(words)

        result = await enricher.enrich(doc)

        assert result.metadata["keyword_count"] <= 5
        assert len(result.metadata["keywords"]) <= 5

    @pytest.mark.asyncio
    async def test_enrich_returns_top_keyword(self, enricher_no_bigrams):
        """Test that top_keyword contains the highest scored keyword."""
        doc = create_test_document(
            "Python Python Python Python "
            "Java Java "
            "Ruby"
        )

        result = await enricher_no_bigrams.enrich(doc)

        assert result.metadata["top_keyword"] == "python"

    @pytest.mark.asyncio
    async def test_enrich_empty_content(self, enricher):
        """Test handling of empty content."""
        doc = create_test_document("")

        # Should be skipped due to short content
        should, _ = enricher.should_process(doc)
        assert should is False

    def test_get_metadata_keys(self, enricher):
        """Test metadata keys documentation."""
        keys = enricher.get_metadata_keys()
        assert "keywords" in keys
        assert "keyword_list" in keys
        assert "keyword_count" in keys
        assert "top_keyword" in keys


class TestTokenization:
    """Tests for tokenization internals."""

    @pytest.fixture
    def enricher(self):
        return KeywordEnricher(MockSettings())

    def test_tokenize_lowercase(self, enricher):
        """Test that tokenization lowercases text."""
        tokens = enricher._tokenize("Hello World PYTHON")
        assert "hello" in tokens
        assert "world" in tokens
        assert "python" in tokens
        assert "Hello" not in tokens

    def test_tokenize_min_length(self, enricher):
        """Test minimum word length filtering."""
        # Default min_word_length is 3
        tokens = enricher._tokenize("a ab abc abcd")
        assert "a" not in tokens
        assert "ab" not in tokens
        assert "abc" in tokens
        assert "abcd" in tokens

    def test_tokenize_removes_stop_words(self, enricher):
        """Test stop word removal."""
        tokens = enricher._tokenize("the quick brown fox and the lazy dog")
        assert "the" not in tokens
        assert "and" not in tokens
        assert "quick" in tokens
        assert "brown" in tokens

    def test_get_ngrams(self, enricher):
        """Test n-gram extraction."""
        tokens = ["machine", "learning", "algorithm"]

        bigrams = enricher._get_ngrams(tokens, 2)
        assert "machine learning" in bigrams
        assert "learning algorithm" in bigrams
        assert len(bigrams) == 2

        trigrams = enricher._get_ngrams(tokens, 3)
        assert "machine learning algorithm" in trigrams
        assert len(trigrams) == 1

    def test_score_terms(self, enricher):
        """Test term scoring."""
        terms = ["python", "python", "python", "java", "java", "ruby"]
        scores = enricher._score_terms(terms)

        assert scores["python"][0] == 1.0  # Max frequency -> score 1.0
        assert scores["java"][0] < scores["python"][0]
        assert scores["python"][1] == 3  # frequency count
        assert scores["java"][1] == 2


class TestStopWords:
    """Tests for stop words list."""

    def test_common_stop_words_included(self):
        """Test that common stop words are in the list."""
        common = {"the", "a", "an", "is", "are", "was", "were", "be", "been"}
        for word in common:
            assert word in STOP_WORDS

    def test_stop_words_all_lowercase(self):
        """Test that all stop words are lowercase."""
        for word in STOP_WORDS:
            assert word == word.lower()
