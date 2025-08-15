"""Unit tests for IntentClassifier."""

import pytest
from unittest.mock import Mock, MagicMock

from qdrant_loader_mcp_server.search.enhanced.intent.classifier import IntentClassifier
from qdrant_loader_mcp_server.search.enhanced.intent.models import IntentType, SearchIntent


class TestIntentClassifier:
    """Test the extracted IntentClassifier class."""

    @pytest.fixture
    def mock_spacy_analyzer(self):
        """Create a mock spaCy analyzer."""
        analyzer = Mock()
        analyzer.analyze_query_semantic.return_value = Mock(
            complexity_score=0.5,
            is_question=False,
            is_technical=True,
            entities=[("API", "PRODUCT"), ("documentation", "NOUN")],
            main_concepts=["API", "documentation", "integration"],
            semantic_keywords=["api", "docs", "integration", "endpoints"],
            pos_patterns=["NOUN", "NOUN", "VERB"],
            intent_signals=["technical", "lookup"],
            processing_time_ms=25.0
        )
        return analyzer

    def test_classifier_imports_correctly(self):
        """Test that IntentClassifier can be imported from the classifier module."""
        assert IntentClassifier is not None
        assert IntentClassifier.__name__ == "IntentClassifier"

    def test_classifier_initialization(self, mock_spacy_analyzer):
        """Test that IntentClassifier initializes correctly."""
        classifier = IntentClassifier(mock_spacy_analyzer)
        
        assert classifier is not None
        assert classifier.spacy_analyzer == mock_spacy_analyzer
        assert hasattr(classifier, 'intent_patterns')
        assert hasattr(classifier, 'session_patterns')
        assert hasattr(classifier, '_intent_cache')
        assert len(classifier.intent_patterns) == 7  # All intent types except GENERAL

    def test_classifier_has_intent_patterns(self, mock_spacy_analyzer):
        """Test that classifier has patterns for all major intent types."""
        classifier = IntentClassifier(mock_spacy_analyzer)
        
        expected_intents = [
            IntentType.TECHNICAL_LOOKUP,
            IntentType.BUSINESS_CONTEXT,
            IntentType.VENDOR_EVALUATION,
            IntentType.PROCEDURAL,
            IntentType.INFORMATIONAL,
            IntentType.TROUBLESHOOTING,
            IntentType.EXPLORATORY
        ]
        
        for intent_type in expected_intents:
            assert intent_type in classifier.intent_patterns
            pattern = classifier.intent_patterns[intent_type]
            assert "keywords" in pattern
            assert "pos_patterns" in pattern
            assert "entity_types" in pattern
            assert "question_words" in pattern
            assert "weight" in pattern

    def test_classify_intent_method_exists(self, mock_spacy_analyzer):
        """Test that classify_intent method exists and returns SearchIntent."""
        classifier = IntentClassifier(mock_spacy_analyzer)
        
        assert hasattr(classifier, 'classify_intent')
        assert callable(classifier.classify_intent)
        
        # Test basic classification
        result = classifier.classify_intent("How to use the API?")
        
        assert isinstance(result, SearchIntent)
        assert isinstance(result.intent_type, IntentType)
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0

    def test_technical_intent_classification(self, mock_spacy_analyzer):
        """Test classification of technical queries."""
        classifier = IntentClassifier(mock_spacy_analyzer)
        
        technical_queries = [
            "How to use the API documentation?",
            "Show me code examples for authentication",
            "What functions are available in the library?"
        ]
        
        for query in technical_queries:
            result = classifier.classify_intent(query)
            # Technical queries should have reasonable confidence
            assert result.confidence > 0.0
            assert isinstance(result.intent_type, IntentType)

    def test_cache_functionality(self, mock_spacy_analyzer):
        """Test that intent classification caching works."""
        classifier = IntentClassifier(mock_spacy_analyzer)
        
        query = "test query for caching"
        
        # First call should use spaCy analyzer
        result1 = classifier.classify_intent(query)
        call_count_1 = mock_spacy_analyzer.analyze_query_semantic.call_count
        
        # Second call should use cache
        result2 = classifier.classify_intent(query)
        call_count_2 = mock_spacy_analyzer.analyze_query_semantic.call_count
        
        # Call count should be the same (cached result)
        assert call_count_1 == call_count_2
        assert result1.intent_type == result2.intent_type
        assert result1.confidence == result2.confidence

    def test_cache_methods(self, mock_spacy_analyzer):
        """Test cache management methods."""
        classifier = IntentClassifier(mock_spacy_analyzer)
        
        # Add something to cache
        classifier.classify_intent("test query")
        
        # Test cache stats
        stats = classifier.get_cache_stats()
        assert isinstance(stats, dict)
        assert "intent_cache_size" in stats
        assert stats["intent_cache_size"] > 0
        
        # Test cache clear
        classifier.clear_cache()
        stats_after_clear = classifier.get_cache_stats()
        assert stats_after_clear["intent_cache_size"] == 0

    def test_linguistic_feature_extraction(self, mock_spacy_analyzer):
        """Test that linguistic features are extracted properly."""
        classifier = IntentClassifier(mock_spacy_analyzer)
        
        result = classifier.classify_intent("How to configure the API endpoints?")
        
        # Check that linguistic features are populated
        assert "linguistic_features" in result.__dict__
        if result.linguistic_features:
            # Basic checks for feature structure
            assert isinstance(result.linguistic_features, dict)

    def test_fallback_on_error(self, mock_spacy_analyzer):
        """Test that classifier handles errors gracefully."""
        # Make spaCy analyzer raise an exception
        mock_spacy_analyzer.analyze_query_semantic.side_effect = Exception("Test error")
        
        classifier = IntentClassifier(mock_spacy_analyzer)
        result = classifier.classify_intent("test query")
        
        # Should return fallback intent
        assert result.intent_type == IntentType.GENERAL
        assert result.confidence == 0.5