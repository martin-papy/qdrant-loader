"""Simplified tests for spaCy NLP components."""

from qdrant_loader_mcp_server.search.nlp.linguistic_preprocessor import (
    LinguisticPreprocessor,
    PreprocessingResult,
)
from qdrant_loader_mcp_server.search.nlp.semantic_expander import (
    EntityQueryExpander,
    ExpansionResult,
)
from qdrant_loader_mcp_server.search.nlp.spacy_analyzer import (
    QueryAnalysis,
    SpaCyQueryAnalyzer,
)


class TestSpaCyComponentsIntegration:
    """Integration tests for spaCy components - test functionality, not implementation details."""

    def test_spacy_analyzer_initialization(self):
        """Test that SpaCyQueryAnalyzer can be initialized."""
        analyzer = SpaCyQueryAnalyzer()
        assert analyzer is not None
        assert hasattr(analyzer, "analyze_query_semantic")
        assert hasattr(analyzer, "semantic_similarity_matching")

    def test_spacy_analyzer_basic_analysis(self):
        """Test basic query analysis functionality."""
        analyzer = SpaCyQueryAnalyzer()

        result = analyzer.analyze_query_semantic("How to implement authentication?")

        # Basic structure checks
        assert isinstance(result, QueryAnalysis)
        assert hasattr(result, "entities")
        assert hasattr(result, "semantic_keywords")
        assert hasattr(result, "intent_signals")
        assert hasattr(result, "is_question")
        assert hasattr(result, "is_technical")
        assert hasattr(result, "processing_time_ms")

        # Type checks
        assert isinstance(result.entities, list)
        assert isinstance(result.semantic_keywords, list)
        assert isinstance(result.intent_signals, dict)
        assert isinstance(result.is_question, bool)
        assert isinstance(result.is_technical, bool)
        assert isinstance(result.processing_time_ms, float)
        assert result.processing_time_ms >= 0

    def test_spacy_analyzer_different_queries(self):
        """Test analyzer with different types of queries."""
        analyzer = SpaCyQueryAnalyzer()

        queries = [
            "What is API authentication?",
            "database performance optimization",
            "meeting agenda for next week",
            "JWT token implementation guide",
            "",
        ]

        for query in queries:
            result = analyzer.analyze_query_semantic(query)
            assert isinstance(result, QueryAnalysis)
            assert result.processing_time_ms >= 0

    def test_spacy_analyzer_caching(self):
        """Test that analyzer caching works."""
        analyzer = SpaCyQueryAnalyzer()

        query = "test query for caching"

        # First call
        result1 = analyzer.analyze_query_semantic(query)
        stats1 = analyzer.get_cache_stats()

        # Second call (should use cache)
        result2 = analyzer.analyze_query_semantic(query)
        stats2 = analyzer.get_cache_stats()

        # Results should be the same
        assert result1.intent_signals == result2.intent_signals
        assert stats2["analysis_cache_size"] >= stats1["analysis_cache_size"]

        # Clear cache should work
        analyzer.clear_cache()
        stats3 = analyzer.get_cache_stats()
        assert stats3["analysis_cache_size"] == 0

    def test_semantic_similarity_basic(self):
        """Test basic semantic similarity functionality."""
        analyzer = SpaCyQueryAnalyzer()

        query_analysis = analyzer.analyze_query_semantic("database performance")

        # Test similarity with related term
        similarity = analyzer.semantic_similarity_matching(
            query_analysis, "database optimization"
        )
        assert isinstance(similarity, float)
        assert 0 <= similarity <= 1

    def test_entity_query_expander_initialization(self):
        """Test that EntityQueryExpander can be initialized."""
        analyzer = SpaCyQueryAnalyzer()
        expander = EntityQueryExpander(analyzer)

        assert expander is not None
        assert hasattr(expander, "expand_query")
        assert expander.spacy_analyzer is analyzer

    def test_entity_query_expander_basic_expansion(self):
        """Test basic query expansion functionality."""
        analyzer = SpaCyQueryAnalyzer()
        expander = EntityQueryExpander(analyzer)

        query = "database performance optimization"
        result = expander.expand_query(query)

        # Basic structure checks
        assert isinstance(result, ExpansionResult)
        assert result.original_query == query
        assert isinstance(result.expanded_query, str)
        assert isinstance(result.expansion_terms, list)
        assert isinstance(result.processing_time_ms, float)
        assert result.processing_time_ms >= 0

        # Expanded query should contain original
        assert query in result.expanded_query or len(result.expanded_query) >= len(
            query
        )

    def test_entity_query_expander_with_context(self):
        """Test query expansion with search context."""
        analyzer = SpaCyQueryAnalyzer()
        expander = EntityQueryExpander(analyzer)

        query = "database performance"
        context = {
            "document_entities": ["database optimization", "performance tuning"],
            "related_entities": ["MySQL", "PostgreSQL"],
        }

        result = expander.expand_query(query, context)

        assert isinstance(result, ExpansionResult)
        assert result.original_query == query
        assert isinstance(result.semantic_terms, list)
        assert isinstance(result.entity_terms, list)

    def test_entity_query_expander_caching(self):
        """Test that expander caching works."""
        analyzer = SpaCyQueryAnalyzer()
        expander = EntityQueryExpander(analyzer)

        query = "test query for expansion caching"

        # First call
        result1 = expander.expand_query(query)
        stats1 = expander.get_cache_stats()

        # Second call (should use cache)
        result2 = expander.expand_query(query)
        stats2 = expander.get_cache_stats()

        # Results should be the same
        assert result1.expanded_query == result2.expanded_query
        assert stats2["expansion_cache_size"] >= stats1["expansion_cache_size"]

        # Clear cache should work
        expander.clear_cache()
        stats3 = expander.get_cache_stats()
        assert stats3["expansion_cache_size"] == 0

    def test_linguistic_preprocessor_initialization(self):
        """Test that LinguisticPreprocessor can be initialized."""
        analyzer = SpaCyQueryAnalyzer()
        preprocessor = LinguisticPreprocessor(analyzer)

        assert preprocessor is not None
        assert hasattr(preprocessor, "preprocess_query")
        assert preprocessor.spacy_analyzer is analyzer

    def test_linguistic_preprocessor_basic_preprocessing(self):
        """Test basic query preprocessing functionality."""
        analyzer = SpaCyQueryAnalyzer()
        preprocessor = LinguisticPreprocessor(analyzer)

        query = "How to implement authentication?"
        result = preprocessor.preprocess_query(query)

        # Basic structure checks
        assert isinstance(result, PreprocessingResult)
        assert result.original_query == query
        assert isinstance(result.preprocessed_query, str)
        assert isinstance(result.lemmatized_tokens, list)
        assert isinstance(result.filtered_tokens, list)
        assert isinstance(result.processing_time_ms, float)
        assert result.processing_time_ms >= 0

        # Preprocessed query should not be empty
        assert len(result.preprocessed_query.strip()) > 0

    def test_linguistic_preprocessor_search_variants(self):
        """Test preprocessing for different search types."""
        analyzer = SpaCyQueryAnalyzer()
        preprocessor = LinguisticPreprocessor(analyzer)

        query = "How to implement authentication"

        # Test different search types
        for search_type in ["vector", "keyword", "hybrid"]:
            result = preprocessor.preprocess_for_search(query, search_type)

            assert isinstance(result, dict)
            assert "search_variants" in result
            assert isinstance(result["search_variants"], dict)

            if search_type == "hybrid":
                assert "vector_search" in result["search_variants"]
                assert "keyword_search" in result["search_variants"]

    def test_linguistic_preprocessor_caching(self):
        """Test that preprocessor caching works."""
        analyzer = SpaCyQueryAnalyzer()
        preprocessor = LinguisticPreprocessor(analyzer)

        query = "test query for preprocessing caching"

        # First call
        result1 = preprocessor.preprocess_query(query)
        stats1 = preprocessor.get_cache_stats()

        # Second call (should use cache)
        result2 = preprocessor.preprocess_query(query)
        stats2 = preprocessor.get_cache_stats()

        # Results should be the same
        assert result1.preprocessed_query == result2.preprocessed_query
        assert stats2["preprocessing_cache_size"] >= stats1["preprocessing_cache_size"]

        # Clear cache should work
        preprocessor.clear_cache()
        stats3 = preprocessor.get_cache_stats()
        assert stats3["preprocessing_cache_size"] == 0

    def test_component_integration(self):
        """Test that all components work together."""
        # Initialize components
        analyzer = SpaCyQueryAnalyzer()
        expander = EntityQueryExpander(analyzer)
        preprocessor = LinguisticPreprocessor(analyzer)

        query = "How do I implement JWT authentication in my API?"

        # 1. Analyze query
        analysis = analyzer.analyze_query_semantic(query)
        assert isinstance(analysis, QueryAnalysis)

        # 2. Expand query
        expansion = expander.expand_query(query)
        assert isinstance(expansion, ExpansionResult)

        # 3. Preprocess query
        preprocessing = preprocessor.preprocess_query(query)
        assert isinstance(preprocessing, PreprocessingResult)

        # All should complete without errors
        assert analysis.processing_time_ms >= 0
        assert expansion.processing_time_ms >= 0
        assert preprocessing.processing_time_ms >= 0

    def test_performance_requirements(self):
        """Test that components meet basic performance requirements."""
        analyzer = SpaCyQueryAnalyzer()
        expander = EntityQueryExpander(analyzer)
        preprocessor = LinguisticPreprocessor(analyzer)

        query = "database performance optimization strategies"

        # Test analyzer performance (should be < 100ms for reasonable queries)
        analysis = analyzer.analyze_query_semantic(query)
        assert analysis.processing_time_ms < 100

        # Test expander performance
        expansion = expander.expand_query(query)
        assert expansion.processing_time_ms < 200

        # Test preprocessor performance
        preprocessing = preprocessor.preprocess_query(query)
        assert preprocessing.processing_time_ms < 100

    def test_empty_and_edge_cases(self):
        """Test components with empty and edge case inputs."""
        analyzer = SpaCyQueryAnalyzer()
        expander = EntityQueryExpander(analyzer)
        preprocessor = LinguisticPreprocessor(analyzer)

        edge_cases = [
            "",
            " ",
            "a",
            "?",
            "Hello world!",
            "   multiple   spaces   between   words   ",
        ]

        for query in edge_cases:
            # All components should handle edge cases gracefully
            analysis = analyzer.analyze_query_semantic(query)
            assert isinstance(analysis, QueryAnalysis)

            expansion = expander.expand_query(query)
            assert isinstance(expansion, ExpansionResult)

            preprocessing = preprocessor.preprocess_query(query)
            assert isinstance(preprocessing, PreprocessingResult)
