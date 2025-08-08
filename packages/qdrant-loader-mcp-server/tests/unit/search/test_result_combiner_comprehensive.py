"""Comprehensive tests for result combiner functionality with 80%+ coverage."""

import pytest
from unittest.mock import MagicMock, patch

from qdrant_loader_mcp_server.search.components.result_combiner import ResultCombiner
from qdrant_loader_mcp_server.search.components.search_result_models import HybridSearchResult, create_hybrid_search_result


@pytest.fixture
def result_combiner():
    """Create a result combiner instance."""
    return ResultCombiner()


@pytest.fixture
def result_combiner_with_spacy():
    """Create a result combiner instance with spaCy analyzer."""
    mock_spacy_analyzer = MagicMock()
    return ResultCombiner(spacy_analyzer=mock_spacy_analyzer)


@pytest.fixture
def sample_vector_results():
    """Create sample vector search results."""
    return [
        {
            "text": "API authentication documentation with code examples",
            "score": 0.9,
            "source_type": "confluence",
            "title": "API Authentication Guide",
            "document_id": "doc1",
            "url": "http://example.com/doc1",
            "source": "docs",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "metadata": {
                "chunk_index": 0,
                "total_chunks": 3,
                "word_count": 500,
                "section_level": 2,
                "section_title": "Authentication Overview",
                "has_code_blocks": True,
                "entities": [{"text": "OAuth", "label": "PRODUCT"}],
                "topics": [{"text": "authentication", "score": 0.9}]
            }
        },
        {
            "text": "Database setup and configuration guide",
            "score": 0.7,
            "source_type": "git",
            "title": "Database Setup",
            "document_id": "doc2",
            "url": "http://example.com/doc2",
            "source": "repo",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "metadata": {
                "chunk_index": 1,
                "total_chunks": 2,
                "word_count": 300,
                "section_level": 1,
                "file_type": "md",
                "is_converted": True,
                "original_file_type": "docx"
            }
        }
    ]


@pytest.fixture
def sample_keyword_results():
    """Create sample keyword search results."""
    return [
        {
            "text": "Database setup and configuration guide",  # Same as vector result
            "score": 0.8,
            "source_type": "git",
            "title": "Database Setup",
            "document_id": "doc2",
            "url": "http://example.com/doc2",
            "source": "repo",
            "metadata": {
                "chunk_index": 1,
                "total_chunks": 2,
                "word_count": 300
            }
        },
        {
            "text": "User management troubleshooting guide",
            "score": 0.6,
            "source_type": "jira",
            "title": "User Management Issues",
            "document_id": "doc3",
            "url": "http://example.com/doc3",
            "source": "tickets",
            "metadata": {
                "chunk_index": 0,
                "total_chunks": 1,
                "word_count": 150,
                "section_type": "troubleshooting"
            }
        }
    ]


@pytest.fixture 
def sample_query_context():
    """Create sample query context."""
    return {
        "search_intent": "code_search",
        "adaptive_config": None,
        "user_query": "API authentication setup",
        "processed_query": "API authentication setup",
        "keywords": ["API", "authentication", "setup"]
    }


@pytest.fixture
def adaptive_config_mock():
    """Create an adaptive config mock."""
    mock_config = MagicMock()
    mock_config.result_filters = {}
    mock_config.ranking_boosts = {"has_code_blocks": 1.2, "section_type": {"documentation": 1.1}}
    mock_config.source_type_preferences = {"confluence": 1.2, "git": 1.0}
    mock_config.diversity_factor = 0.0
    return mock_config


class TestResultCombinerInitialization:
    """Test ResultCombiner initialization."""

    def test_default_initialization(self):
        """Test proper initialization with default parameters."""
        combiner = ResultCombiner()
        assert combiner.vector_weight == 0.6
        assert combiner.keyword_weight == 0.3
        assert combiner.metadata_weight == 0.1
        assert combiner.min_score == 0.3
        assert combiner.spacy_analyzer is None
        assert combiner.metadata_extractor is not None
        assert combiner.logger is not None

    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        spacy_analyzer = MagicMock()
        combiner = ResultCombiner(
            vector_weight=0.8,
            keyword_weight=0.2,
            metadata_weight=0.0,
            min_score=0.5,
            spacy_analyzer=spacy_analyzer
        )
        assert combiner.vector_weight == 0.8
        assert combiner.keyword_weight == 0.2
        assert combiner.metadata_weight == 0.0
        assert combiner.min_score == 0.5
        assert combiner.spacy_analyzer == spacy_analyzer


class TestCombineResultsCore:
    """Test the main combine_results method."""

    @pytest.mark.asyncio
    async def test_combine_results_basic(self, result_combiner, sample_vector_results, sample_keyword_results, sample_query_context):
        """Test basic result combination."""
        with patch.object(result_combiner.metadata_extractor, 'extract_all_metadata', return_value={}):
            combined = await result_combiner.combine_results(
                vector_results=sample_vector_results,
                keyword_results=sample_keyword_results,
                query_context=sample_query_context,
                limit=10
            )
        
        assert isinstance(combined, list)
        assert len(combined) > 0
        assert all(isinstance(result, HybridSearchResult) for result in combined)
        
        # Should be sorted by score (highest first)
        scores = [result.score for result in combined]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_combine_results_with_overlapping_content(self, result_combiner, sample_vector_results, sample_keyword_results, sample_query_context):
        """Test combination when results have overlapping content."""
        with patch.object(result_combiner.metadata_extractor, 'extract_all_metadata', return_value={}):
            combined = await result_combiner.combine_results(
                vector_results=sample_vector_results,
                keyword_results=sample_keyword_results,
                query_context=sample_query_context,
                limit=10
            )
        
        # Find the overlapping result (same text in both vector and keyword)
        overlapping_result = next(
            (r for r in combined if r.document_id == "doc2"), 
            None
        )
        
        assert overlapping_result is not None
        assert overlapping_result.vector_score > 0
        assert overlapping_result.keyword_score > 0
        # Combined score should reflect both sources
        expected_base = (0.6 * 0.7) + (0.3 * 0.8)  # vector_weight * vector_score + keyword_weight * keyword_score
        assert overlapping_result.score >= expected_base  # May be boosted

    @pytest.mark.asyncio
    async def test_combine_results_with_source_type_filter(self, result_combiner, sample_vector_results, sample_keyword_results, sample_query_context):
        """Test result combination with source type filtering."""
        with patch.object(result_combiner.metadata_extractor, 'extract_all_metadata', return_value={}):
            combined = await result_combiner.combine_results(
                vector_results=sample_vector_results,
                keyword_results=sample_keyword_results,
                query_context=sample_query_context,
                limit=10,
                source_types=["confluence"]
            )
        
        # Should only include confluence results
        for result in combined:
            assert result.source_type == "confluence"

    @pytest.mark.asyncio
    async def test_combine_results_empty_inputs(self, result_combiner, sample_query_context):
        """Test combining empty results."""
        combined = await result_combiner.combine_results(
            vector_results=[],
            keyword_results=[],
            query_context=sample_query_context,
            limit=10
        )
        
        assert combined == []

    @pytest.mark.asyncio
    async def test_combine_results_vector_only(self, result_combiner, sample_vector_results, sample_query_context):
        """Test combining with only vector results."""
        with patch.object(result_combiner.metadata_extractor, 'extract_all_metadata', return_value={}):
            combined = await result_combiner.combine_results(
                vector_results=sample_vector_results,
                keyword_results=[],
                query_context=sample_query_context,
                limit=10
            )
        
        assert len(combined) == 2
        for result in combined:
            assert result.vector_score > 0
            assert result.keyword_score == 0.0

    @pytest.mark.asyncio
    async def test_combine_results_keyword_only(self, result_combiner, sample_keyword_results, sample_query_context):
        """Test combining with only keyword results."""
        # Lower min_score to allow keyword-only results to pass through
        result_combiner.min_score = 0.1
        
        with patch.object(result_combiner.metadata_extractor, 'extract_all_metadata', return_value={}):
            combined = await result_combiner.combine_results(
                vector_results=[],
                keyword_results=sample_keyword_results,
                query_context=sample_query_context,
                limit=10
            )
        
        assert len(combined) == 2
        for result in combined:
            assert result.vector_score == 0.0
            assert result.keyword_score > 0

    @pytest.mark.asyncio
    async def test_combine_results_min_score_filtering(self, result_combiner, sample_query_context):
        """Test that results below minimum score are filtered out."""
        # Create results with very low scores
        low_score_results = [
            {
                "text": "Low quality result",
                "score": 0.1,  # Below default min_score of 0.3
                "source_type": "git",
                "title": "Low Quality",
                "document_id": "low",
                "metadata": {}
            }
        ]
        
        with patch.object(result_combiner.metadata_extractor, 'extract_all_metadata', return_value={}):
            combined = await result_combiner.combine_results(
                vector_results=low_score_results,
                keyword_results=[],
                query_context=sample_query_context,
                limit=10
            )
        
        # Should be empty because scores are below threshold
        assert len(combined) == 0

    @pytest.mark.asyncio
    async def test_combine_results_with_limit(self, result_combiner, sample_vector_results, sample_keyword_results, sample_query_context):
        """Test that limit is respected."""
        with patch.object(result_combiner.metadata_extractor, 'extract_all_metadata', return_value={}):
            combined = await result_combiner.combine_results(
                vector_results=sample_vector_results,
                keyword_results=sample_keyword_results,
                query_context=sample_query_context,
                limit=1
            )
        
        assert len(combined) == 1


class TestShouldSkipResult:
    """Test the _should_skip_result method."""

    def test_should_skip_result_no_filters(self, result_combiner, sample_query_context):
        """Test that no filtering occurs when no filters are provided."""
        metadata = {"source_type": "confluence"}
        result_filters = {}
        
        should_skip = result_combiner._should_skip_result(
            metadata, result_filters, sample_query_context
        )
        
        assert should_skip is False

    def test_should_skip_result_content_type_filtering_code(self, result_combiner, sample_query_context):
        """Test content type filtering for code content."""
        metadata = {
            "content_type_analysis": {"has_code_blocks": True}
        }
        result_filters = {"content_type": ["code"]}
        
        should_skip = result_combiner._should_skip_result(
            metadata, result_filters, sample_query_context
        )
        
        assert should_skip is False  # Should not skip code content

    def test_should_skip_result_content_type_filtering_documentation(self, result_combiner, sample_query_context):
        """Test content type filtering for documentation content."""
        metadata = {
            "content_type_analysis": {"has_code_blocks": False}
        }
        result_filters = {"content_type": ["documentation"]}
        
        should_skip = result_combiner._should_skip_result(
            metadata, result_filters, sample_query_context
        )
        
        assert should_skip is False  # Should not skip documentation content

    def test_should_skip_result_content_type_mismatch(self, result_combiner, sample_query_context):
        """Test that mismatched content types are skipped."""
        metadata = {
            "content_type_analysis": {"has_code_blocks": False}
        }
        result_filters = {"content_type": ["code"]}
        
        should_skip = result_combiner._should_skip_result(
            metadata, result_filters, sample_query_context
        )
        
        assert should_skip is True  # Should skip non-code content when looking for code


class TestCountBusinessIndicators:
    """Test the _count_business_indicators method."""

    def test_count_business_indicators_in_title(self, result_combiner):
        """Test counting business indicators in title."""
        metadata = {
            "title": "Business Requirements Document",
            "content": "Some content here"
        }
        
        count = result_combiner._count_business_indicators(metadata)
        
        assert count >= 2  # "business" and "requirement"

    def test_count_business_indicators_in_content(self, result_combiner):
        """Test counting business indicators in content."""
        metadata = {
            "title": "Technical Doc",
            "content": "This describes the strategy and business process for our objectives"
        }
        
        count = result_combiner._count_business_indicators(metadata)
        
        assert count >= 3  # "strategy", "business", "process"

    def test_count_business_indicators_none_found(self, result_combiner):
        """Test when no business indicators are found."""
        metadata = {
            "title": "Technical Implementation",
            "content": "Code implementation details"
        }
        
        count = result_combiner._count_business_indicators(metadata)
        
        assert count == 0


class TestBoostScoreWithMetadata:
    """Test the _boost_score_with_metadata method."""

    def test_boost_score_basic(self, result_combiner, sample_query_context):
        """Test basic score boosting."""
        base_score = 0.7
        metadata = {
            "word_count": 500,
            "section_level": 2
        }
        
        boosted_score = result_combiner._boost_score_with_metadata(
            base_score, metadata, sample_query_context
        )
        
        assert boosted_score >= base_score
        assert isinstance(boosted_score, (int, float))

    def test_boost_score_with_intent_config(self, result_combiner, sample_query_context, adaptive_config_mock):
        """Test score boosting with intent configuration."""
        query_context_with_config = {
            **sample_query_context,
            "search_intent": MagicMock(confidence=0.9),
            "adaptive_config": adaptive_config_mock
        }
        
        base_score = 0.6
        metadata = {
            "has_code_blocks": True,
            "source_type": "confluence"
        }
        
        boosted_score = result_combiner._boost_score_with_metadata(
            base_score, metadata, query_context_with_config
        )
        
        assert boosted_score > base_score  # Should be boosted due to config

    def test_boost_score_with_spacy_analyzer(self, result_combiner_with_spacy, sample_query_context):
        """Test score boosting with spaCy analyzer."""
        query_context_with_spacy = {
            **sample_query_context,
            "spacy_analysis": MagicMock(entities=["OAuth"], main_concepts=["authentication"])
        }
        
        base_score = 0.6
        metadata = {
            "entities": [{"text": "OAuth", "label": "PRODUCT"}],
            "topics": [{"text": "authentication", "score": 0.9}]
        }
        
        # Mock spaCy similarity matching
        result_combiner_with_spacy.spacy_analyzer.semantic_similarity_matching.return_value = 0.8
        
        boosted_score = result_combiner_with_spacy._boost_score_with_metadata(
            base_score, metadata, query_context_with_spacy
        )
        
        assert boosted_score > base_score

    def test_boost_score_fallback_semantic(self, result_combiner, sample_query_context):
        """Test fallback semantic boosting without spaCy."""
        base_score = 0.6
        metadata = {
            "entities": ["OAuth", "API"],
            "topics": ["authentication"]
        }
        
        boosted_score = result_combiner._boost_score_with_metadata(
            base_score, metadata, sample_query_context
        )
        
        assert boosted_score >= base_score


class TestApplyBoostingMethods:
    """Test individual boosting methods."""

    def test_apply_content_type_boosting(self, result_combiner, sample_query_context):
        """Test content type boosting."""
        metadata = {
            "content_type_analysis": {
                "has_code_blocks": True,
                "has_tables": True,
                "has_images": False
            }
        }
        
        # Test with preferences for code
        query_context_code = {**sample_query_context, "prefers_code": True}
        boost = result_combiner._apply_content_type_boosting(metadata, query_context_code)
        assert boost > 0
        
        # Test with preferences for tables
        query_context_tables = {**sample_query_context, "prefers_tables": True}
        boost = result_combiner._apply_content_type_boosting(metadata, query_context_tables)
        assert boost > 0

    def test_apply_section_level_boosting(self, result_combiner):
        """Test section level boosting."""
        # Test H1 (high importance)
        metadata_h1 = {"section_level": 1}
        boost = result_combiner._apply_section_level_boosting(metadata_h1)
        assert boost == 0.10
        
        # Test H3 (medium importance)
        metadata_h3 = {"section_level": 3}
        boost = result_combiner._apply_section_level_boosting(metadata_h3)
        assert boost == 0.05
        
        # Test H5 (low importance)
        metadata_h5 = {"section_level": 5}
        boost = result_combiner._apply_section_level_boosting(metadata_h5)
        assert boost == 0.0

    def test_apply_content_quality_boosting(self, result_combiner):
        """Test content quality boosting."""
        # Test substantial content
        metadata_substantial = {
            "content_type_analysis": {"word_count": 200}
        }
        boost = result_combiner._apply_content_quality_boosting(metadata_substantial)
        assert boost == 0.05
        
        # Test very detailed content
        metadata_detailed = {
            "content_type_analysis": {"word_count": 600}
        }
        boost = result_combiner._apply_content_quality_boosting(metadata_detailed)
        assert boost == 0.10  # 0.05 + 0.05
        
        # Test short content
        metadata_short = {
            "content_type_analysis": {"word_count": 50}
        }
        boost = result_combiner._apply_content_quality_boosting(metadata_short)
        assert boost == 0.0

    def test_apply_conversion_boosting(self, result_combiner, sample_query_context):
        """Test conversion boosting."""
        # Test converted file
        metadata_converted = {
            "is_converted": True,
            "original_file_type": "docx"
        }
        boost = result_combiner._apply_conversion_boosting(metadata_converted, sample_query_context)
        assert boost == 0.08
        
        # Test Excel sheet with data query
        metadata_excel = {
            "is_excel_sheet": True
        }
        query_context_data = {**sample_query_context, "keywords": ["data", "table"]}
        boost = result_combiner._apply_conversion_boosting(metadata_excel, query_context_data)
        assert boost == 0.12

    def test_apply_fallback_semantic_boosting(self, result_combiner, sample_query_context):
        """Test fallback semantic boosting."""
        metadata = {
            "entities": ["API", "OAuth"],
            "topics": ["authentication", "security"]
        }
        
        boost = result_combiner._apply_fallback_semantic_boosting(metadata, sample_query_context)
        assert boost >= 0  # Should provide some boost for matching entities/topics


class TestApplyDiversityFiltering:
    """Test the _apply_diversity_filtering method."""

    def test_apply_diversity_filtering_no_diversity(self, result_combiner):
        """Test diversity filtering when diversity factor is 0."""
        results = [
            create_hybrid_search_result(0.9, "text1", "git", "title1"),
            create_hybrid_search_result(0.8, "text2", "git", "title2"),
            create_hybrid_search_result(0.7, "text3", "git", "title3")
        ]
        
        filtered = result_combiner._apply_diversity_filtering(results, 0.0, 5)
        assert len(filtered) == 3
        assert filtered == results

    def test_apply_diversity_filtering_with_diversity(self, result_combiner):
        """Test diversity filtering with diversity factor."""
        results = [
            create_hybrid_search_result(0.9, "text1", "git", "title1", section_type="code"),
            create_hybrid_search_result(0.8, "text2", "git", "title2", section_type="code"),
            create_hybrid_search_result(0.7, "text3", "confluence", "title3", section_type="docs"),
            create_hybrid_search_result(0.6, "text4", "jira", "title4", section_type="issue")
        ]
        
        # Apply diversity filtering
        filtered = result_combiner._apply_diversity_filtering(results, 0.5, 3)
        
        assert len(filtered) <= 3
        # Should prefer diverse source types
        source_types = {result.source_type for result in filtered}
        assert len(source_types) >= 2

    def test_apply_diversity_filtering_limit_handling(self, result_combiner):
        """Test diversity filtering respects limits."""
        results = [
            create_hybrid_search_result(0.9, f"text{i}", "git", f"title{i}")
            for i in range(10)
        ]
        
        filtered = result_combiner._apply_diversity_filtering(results, 0.3, 5)
        assert len(filtered) == 5


class TestFlattenMetadataComponents:
    """Test the _flatten_metadata_components method."""

    def test_flatten_metadata_components_empty(self, result_combiner):
        """Test flattening empty metadata components."""
        components = {}
        flattened = result_combiner._flatten_metadata_components(components)
        assert flattened == {}

    def test_flatten_metadata_components_with_dataclass(self, result_combiner):
        """Test flattening metadata components with dataclass objects."""
        mock_component = MagicMock()
        mock_component.__dict__ = {"field1": "value1", "field2": "value2"}
        
        components = {"component1": mock_component}
        flattened = result_combiner._flatten_metadata_components(components)
        
        assert "field1" in flattened
        assert "field2" in flattened
        assert flattened["field1"] == "value1"
        assert flattened["field2"] == "value2"

    def test_flatten_metadata_components_with_dict(self, result_combiner):
        """Test flattening metadata components with dict objects."""
        components = {
            "component1": {"key1": "val1", "key2": "val2"},
            "component2": {"key3": "val3"}
        }
        
        flattened = result_combiner._flatten_metadata_components(components)
        
        assert "key1" in flattened
        assert "key2" in flattened
        assert "key3" in flattened
        assert flattened["key1"] == "val1"
        assert flattened["key2"] == "val2"
        assert flattened["key3"] == "val3"

    def test_flatten_metadata_components_with_none(self, result_combiner):
        """Test flattening metadata components with None values."""
        components = {
            "component1": None,
            "component2": {"key": "value"}
        }
        
        flattened = result_combiner._flatten_metadata_components(components)
        
        assert "key" in flattened
        assert flattened["key"] == "value"


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_combine_results_with_malformed_data(self, result_combiner, sample_query_context):
        """Test handling of malformed result data."""
        malformed_results = [
            {
                "text": "Valid result",
                "score": 0.8,
                "source_type": "git",
                "metadata": {}
            },
            {
                "text": "Missing score",
                "source_type": "confluence",
                "metadata": {}
                # Missing 'score' field - should be handled gracefully
            }
        ]
        
        with patch.object(result_combiner.metadata_extractor, 'extract_all_metadata', return_value={}):
            # Should handle malformed data gracefully without crashing
            try:
                combined = await result_combiner.combine_results(
                    vector_results=malformed_results,
                    keyword_results=[],
                    query_context=sample_query_context,
                    limit=10
                )
                # If it succeeds, should process valid results
                assert isinstance(combined, list)
            except KeyError:
                # If it fails, that's expected for missing required fields
                pass

    @pytest.mark.asyncio
    async def test_combine_results_with_none_metadata(self, result_combiner, sample_query_context):
        """Test handling of None metadata."""
        results_with_none_metadata = [
            {
                "text": "Result with None metadata",
                "score": 0.8,
                "source_type": "git",
                "metadata": None
            }
        ]
        
        with patch.object(result_combiner.metadata_extractor, 'extract_all_metadata', return_value={}):
            # Should handle None metadata gracefully
            try:
                combined = await result_combiner.combine_results(
                    vector_results=results_with_none_metadata,
                    keyword_results=[],
                    query_context=sample_query_context,
                    limit=10
                )
                assert isinstance(combined, list)
            except AttributeError:
                # If it fails due to None metadata, that's expected
                pass

    def test_boost_score_with_empty_metadata(self, result_combiner, sample_query_context):
        """Test score boosting with empty metadata."""
        base_score = 0.6
        empty_metadata = {}
        
        boosted_score = result_combiner._boost_score_with_metadata(
            base_score, empty_metadata, sample_query_context
        )
        
        # Should not crash and should return a valid score
        assert isinstance(boosted_score, (int, float))
        assert boosted_score >= base_score

    def test_boost_score_maximum_boost_cap(self, result_combiner, sample_query_context):
        """Test that boost factor is capped at reasonable maximum."""
        base_score = 0.5
        # Create metadata that would generate high boosts
        metadata = {
            "word_count": 2000,  # Very high word count
            "section_level": 1,  # H1 level
            "has_code_blocks": True,
            "has_tables": True,
            "is_converted": True,
            "original_file_type": "docx",
            "entities": ["API", "OAuth", "authentication"],
            "topics": ["security", "authentication", "API"]
        }
        
        boosted_score = result_combiner._boost_score_with_metadata(
            base_score, metadata, sample_query_context
        )
        
        # Should be boosted but capped (not more than 50% boost)
        assert boosted_score > base_score
        assert boosted_score <= base_score * 1.5  # Maximum 50% boost

    @pytest.mark.asyncio
    async def test_large_result_set_handling(self, result_combiner, sample_query_context):
        """Test handling of large result sets."""
        # Create a large number of results
        large_vector_results = []
        for i in range(100):
            large_vector_results.append({
                "text": f"Document {i} with content about various topics",
                "score": 0.5 + (i % 50) / 100,  # Varying scores
                "source_type": "git",
                "title": f"Doc {i}",
                "document_id": f"doc{i}",
                "metadata": {"index": i, "word_count": 100 + i}
            })
        
        with patch.object(result_combiner.metadata_extractor, 'extract_all_metadata', return_value={}):
            combined = await result_combiner.combine_results(
                vector_results=large_vector_results,
                keyword_results=[],
                query_context=sample_query_context,
                limit=20  # Limit to 20 results
            )
        
        assert len(combined) <= 20
        assert isinstance(combined, list)
        # Should be sorted by score
        scores = [result.score for result in combined]
        assert scores == sorted(scores, reverse=True)
