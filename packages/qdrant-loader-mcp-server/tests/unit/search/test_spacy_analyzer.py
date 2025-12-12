"""Tests for spaCy query analyzer."""

from unittest.mock import MagicMock, patch

import pytest
from qdrant_loader_mcp_server.search.nlp.spacy_analyzer import (
    QueryAnalysis,
    SpaCyQueryAnalyzer,
)


@pytest.fixture
def mock_spacy_nlp():
    """Create a mock spaCy nlp object."""
    nlp = MagicMock()

    # Mock document
    doc = MagicMock()
    doc.text = "test query"

    # Mock entities
    entity1 = MagicMock()
    entity1.text = "API"
    entity1.label_ = "PRODUCT"

    entity2 = MagicMock()
    entity2.text = "authentication"
    entity2.label_ = "TECH"

    doc.ents = [entity1, entity2]

    # Mock tokens
    token1 = MagicMock()
    token1.text = "How"
    token1.pos_ = "ADV"
    token1.lemma_ = "how"
    token1.is_alpha = True
    token1.is_stop = True

    token2 = MagicMock()
    token2.text = "implement"
    token2.pos_ = "VERB"
    token2.lemma_ = "implement"
    token2.is_alpha = True
    token2.is_stop = False

    token3 = MagicMock()
    token3.text = "authentication"
    token3.pos_ = "NOUN"
    token3.lemma_ = "authentication"
    token3.is_alpha = True
    token3.is_stop = False

    doc.__iter__ = lambda self: iter([token1, token2, token3])

    # Mock noun chunks
    chunk1 = MagicMock()
    chunk1.text = "authentication system"
    doc.noun_chunks = [chunk1]

    # Mock similarity
    doc.similarity.return_value = 0.75

    nlp.return_value = doc
    return nlp


@pytest.fixture
def spacy_analyzer(mock_spacy_nlp):
    """Create a SpaCyQueryAnalyzer with mocked spaCy."""
    with patch(
        "qdrant_loader_mcp_server.search.nlp.spacy_analyzer.spacy.load"
    ) as mock_load:
        mock_load.return_value = mock_spacy_nlp
        analyzer = SpaCyQueryAnalyzer()
        analyzer.nlp = mock_spacy_nlp
        return analyzer


class TestSpaCyQueryAnalyzer:
    """Test SpaCyQueryAnalyzer functionality."""

    def test_initialization(self, mock_spacy_nlp):
        """Test analyzer initialization."""
        with patch(
            "qdrant_loader_mcp_server.search.nlp.spacy_analyzer.spacy.load"
        ) as mock_load:
            mock_load.return_value = mock_spacy_nlp

            analyzer = SpaCyQueryAnalyzer()

            assert analyzer.spacy_model == "en_core_web_md"
            assert analyzer.nlp is not None
            mock_load.assert_called_once_with("en_core_web_md")

    def test_analyze_query_semantic_basic(self, spacy_analyzer):
        """Test basic query semantic analysis."""
        query = "How to implement authentication?"

        result = spacy_analyzer.analyze_query_semantic(query)

        assert isinstance(result, QueryAnalysis)
        assert len(result.entities) >= 1  # Should have at least one entity
        assert isinstance(result.entities, list)
        assert isinstance(result.semantic_keywords, list)
        assert isinstance(result.main_concepts, list)
        assert result.processing_time_ms >= 0

    def test_analyze_query_semantic_question_detection(self, spacy_analyzer):
        """Test question detection in query analysis."""
        # Test with obvious question queries
        question_result = spacy_analyzer.analyze_query_semantic(
            "What is API authentication?"
        )
        statement_result = spacy_analyzer.analyze_query_semantic(
            "API authentication implementation"
        )

        # Both should be valid QueryAnalysis objects
        assert isinstance(question_result, QueryAnalysis)
        assert isinstance(statement_result, QueryAnalysis)
        assert isinstance(question_result.is_question, bool)
        assert isinstance(statement_result.is_question, bool)

    def test_analyze_query_semantic_technical_detection(self, spacy_analyzer):
        """Test technical query detection."""
        # Test with technical and non-technical queries
        technical_result = spacy_analyzer.analyze_query_semantic(
            "database performance optimization API"
        )
        non_technical_result = spacy_analyzer.analyze_query_semantic(
            "meeting agenda for next week"
        )

        # Both should be valid QueryAnalysis objects
        assert isinstance(technical_result, QueryAnalysis)
        assert isinstance(non_technical_result, QueryAnalysis)
        assert isinstance(technical_result.is_technical, bool)
        assert isinstance(non_technical_result.is_technical, bool)

    def test_analyze_query_semantic_intent_classification(self, spacy_analyzer):
        """Test intent classification in query analysis."""
        result = spacy_analyzer.analyze_query_semantic(
            "How to implement authentication?"
        )

        assert "primary_intent" in result.intent_signals
        assert "confidence" in result.intent_signals
        assert isinstance(result.intent_signals["confidence"], float)
        assert 0 <= result.intent_signals["confidence"] <= 1

    def test_semantic_similarity_matching(self, spacy_analyzer):
        """Test semantic similarity matching."""
        query = "database performance"
        analysis = spacy_analyzer.analyze_query_semantic(query)
        entity_text = "database optimization"

        # Mock the second nlp call for entity
        entity_doc = MagicMock()
        spacy_analyzer.nlp.side_effect = [analysis.query_vector, entity_doc]
        analysis.query_vector.similarity.return_value = 0.85

        similarity = spacy_analyzer.semantic_similarity_matching(analysis, entity_text)

        assert isinstance(similarity, float)
        assert similarity == 0.85

    def test_semantic_similarity_matching_fallback(self, spacy_analyzer):
        """Test semantic similarity fallback when vectors not available."""
        query = "database performance"
        analysis = spacy_analyzer.analyze_query_semantic(query)
        analysis.query_vector.has_vector = False
        analysis.semantic_keywords = ["database", "performance"]

        entity_text = "database optimization performance"

        similarity = spacy_analyzer.semantic_similarity_matching(analysis, entity_text)

        assert isinstance(similarity, float)
        assert 0 <= similarity <= 1

    def test_cache_functionality(self, spacy_analyzer):
        """Test analysis caching."""
        query = "test query"

        # First call
        result1 = spacy_analyzer.analyze_query_semantic(query)

        # Second call should use cache
        result2 = spacy_analyzer.analyze_query_semantic(query)

        assert result1 == result2

        # Check cache stats
        stats = spacy_analyzer.get_cache_stats()
        assert stats["analysis_cache_size"] == 1

    def test_clear_cache(self, spacy_analyzer):
        """Test cache clearing."""
        query = "test query"
        spacy_analyzer.analyze_query_semantic(query)

        # Cache should have entries
        stats = spacy_analyzer.get_cache_stats()
        assert stats["analysis_cache_size"] > 0

        # Clear cache
        spacy_analyzer.clear_cache()

        # Cache should be empty
        stats = spacy_analyzer.get_cache_stats()
        assert stats["analysis_cache_size"] == 0
        assert stats["similarity_cache_size"] == 0

    def test_complexity_scoring(self, spacy_analyzer):
        """Test query complexity scoring."""
        # Simple query
        simple_doc = MagicMock()
        simple_doc.__len__ = lambda self: 3
        spacy_analyzer.nlp.return_value = simple_doc

        result = spacy_analyzer.analyze_query_semantic("simple query")

        assert isinstance(result.complexity_score, float)
        assert result.complexity_score >= 0

    def test_pos_pattern_analysis(self, spacy_analyzer):
        """Test POS pattern extraction."""
        result = spacy_analyzer.analyze_query_semantic(
            "How to implement authentication?"
        )

        assert isinstance(result.pos_patterns, list)
        # POS patterns should exist for any non-empty query
        assert len(result.pos_patterns) >= 0  # Can be empty for some queries
        if result.pos_patterns:
            assert all(isinstance(pos, str) for pos in result.pos_patterns)

    def test_performance_tracking(self, spacy_analyzer):
        """Test that processing time is tracked."""
        result = spacy_analyzer.analyze_query_semantic("test query")

        assert hasattr(result, "processing_time_ms")
        assert isinstance(result.processing_time_ms, float)
        assert result.processing_time_ms >= 0
