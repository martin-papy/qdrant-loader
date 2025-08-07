"""Tests for result combiner functionality."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from typing import List, Dict, Any

from qdrant_loader_mcp_server.search.components.result_combiner import ResultCombiner
from qdrant_loader_mcp_server.search.components.search_result_models import HybridSearchResult


@pytest.fixture
def result_combiner():
    """Create a result combiner instance."""
    return ResultCombiner()


@pytest.fixture
def sample_vector_results():
    """Create sample vector search results."""
    return [
        {
            "text": "High quality document about API",
            "score": 0.9,
            "source_type": "confluence",
            "title": "API Documentation",
            "document_id": "doc1",
            "url": "http://example.com/doc1",
            "source": "docs",
            "metadata": {
                "chunk_index": 0,
                "total_chunks": 1,
                "word_count": 100
            }
        },
        {
            "text": "Medium quality setup guide",
            "score": 0.7,
            "source_type": "git",
            "title": "Setup Guide",
            "document_id": "doc2",
            "url": "http://example.com/doc2",
            "source": "repo",
            "metadata": {
                "chunk_index": 0,
                "total_chunks": 1,
                "word_count": 200
            }
        }
    ]


@pytest.fixture
def sample_keyword_results():
    """Create sample keyword search results."""
    return [
        {
            "text": "Medium quality setup guide",
            "score": 0.8,
            "source_type": "git",
            "title": "Setup Guide",
            "document_id": "doc2",
            "url": "http://example.com/doc2",
            "source": "repo",
            "metadata": {
                "chunk_index": 0,
                "total_chunks": 1,
                "word_count": 200
            }
        },
        {
            "text": "Lower quality reference",
            "score": 0.6,
            "source_type": "jira",
            "title": "Bug Report",
            "document_id": "doc3",
            "url": "http://example.com/doc3",
            "source": "tickets",
            "metadata": {
                "chunk_index": 0,
                "total_chunks": 1,
                "word_count": 50
            }
        }
    ]


@pytest.fixture
def sample_query_context():
    """Create sample query context."""
    return {
        "search_intent": "code_search",
        "adaptive_config": None,
        "user_query": "API documentation",
        "processed_query": "API documentation"
    }


class TestResultCombinerBasic:
    """Test basic result combiner functionality."""

    def test_initialization(self):
        """Test proper initialization of ResultCombiner."""
        combiner = ResultCombiner()
        assert combiner is not None
        assert combiner.vector_weight == 0.6
        assert combiner.keyword_weight == 0.3
        assert combiner.metadata_weight == 0.1
        assert combiner.min_score == 0.3

    def test_initialization_with_custom_weights(self):
        """Test initialization with custom weights."""
        combiner = ResultCombiner(
            vector_weight=0.7,
            keyword_weight=0.2,
            metadata_weight=0.1,
            min_score=0.4
        )
        assert combiner.vector_weight == 0.7
        assert combiner.keyword_weight == 0.2
        assert combiner.metadata_weight == 0.1
        assert combiner.min_score == 0.4

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
        assert len(combined) <= 10
        assert all(isinstance(result, HybridSearchResult) for result in combined)

    @pytest.mark.asyncio
    async def test_combine_results_with_filters(self, result_combiner, sample_vector_results, sample_keyword_results, sample_query_context):
        """Test result combination with source type filters."""
        with patch.object(result_combiner.metadata_extractor, 'extract_all_metadata', return_value={}):
            combined = await result_combiner.combine_results(
                vector_results=sample_vector_results,
                keyword_results=sample_keyword_results,
                query_context=sample_query_context,
                limit=10,
                source_types=["confluence"]
            )
        
        assert isinstance(combined, list)
        # Should only include confluence results
        for result in combined:
            assert result.source_type == "confluence"

    @pytest.mark.asyncio
    async def test_combine_results_empty_input(self, result_combiner, sample_query_context):
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
        assert all(result.vector_score > 0 for result in combined)
        assert all(result.keyword_score == 0.0 for result in combined)

    @pytest.mark.asyncio
    async def test_combine_results_keyword_only(self, result_combiner, sample_keyword_results, sample_query_context):
        """Test combining with only keyword results."""
        with patch.object(result_combiner.metadata_extractor, 'extract_all_metadata', return_value={}):
            combined = await result_combiner.combine_results(
                vector_results=[],
                keyword_results=sample_keyword_results,
                query_context=sample_query_context,
                limit=10
            )
        
        assert len(combined) == 2
        assert all(result.vector_score == 0.0 for result in combined)
        assert all(result.keyword_score > 0 for result in combined)


class TestResultCombinerScoring:
    """Test result scoring and ranking functionality."""

    @pytest.mark.asyncio
    async def test_combined_scoring(self, result_combiner, sample_vector_results, sample_keyword_results, sample_query_context):
        """Test that combined scores are calculated correctly."""
        with patch.object(result_combiner.metadata_extractor, 'extract_all_metadata', return_value={}):
            combined = await result_combiner.combine_results(
                vector_results=sample_vector_results,
                keyword_results=sample_keyword_results,
                query_context=sample_query_context,
                limit=10
            )
        
        # Find the result that appears in both vector and keyword results
        overlapping_result = next(
            (r for r in combined if r.document_id == "doc2"), 
            None
        )
        
        if overlapping_result:
            # Should have both vector and keyword scores
            assert overlapping_result.vector_score > 0
            assert overlapping_result.keyword_score > 0
            # Combined score should be weighted sum
            expected_score = (
                result_combiner.vector_weight * 0.7 +  # vector score
                result_combiner.keyword_weight * 0.8   # keyword score
            )
            assert abs(overlapping_result.combined_score - expected_score) < 0.1

    @pytest.mark.asyncio
    async def test_score_filtering(self, result_combiner, sample_query_context):
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

    def test_boost_score_with_metadata(self, result_combiner, sample_query_context):
        """Test metadata-based score boosting."""
        base_score = 0.7
        metadata = {
            "word_count": 500,
            "has_code_blocks": True,
            "section_type": "documentation"
        }
        
        boosted_score = result_combiner._boost_score_with_metadata(
            base_score, metadata, sample_query_context
        )
        
        assert boosted_score >= base_score
        assert isinstance(boosted_score, (int, float))

    def test_calculate_metadata_boost(self, result_combiner, sample_query_context):
        """Test metadata boost calculation."""
        metadata = {
            "word_count": 1000,
            "has_images": True,
            "section_level": 2
        }
        
        boost = result_combiner._calculate_metadata_boost(metadata, sample_query_context)
        
        assert isinstance(boost, (int, float))
        assert boost >= 0

    def test_calculate_freshness_boost(self, result_combiner):
        """Test freshness boost calculation."""
        metadata = {
            "last_modified": "2024-01-01T00:00:00Z",
            "created_at": "2023-01-01T00:00:00Z"
        }
        
        boost = result_combiner._calculate_freshness_boost(metadata)
        
        assert isinstance(boost, (int, float))
        assert boost >= 0

    def test_calculate_authority_boost(self, result_combiner):
        """Test authority boost calculation."""
        metadata = {
            "author": "admin",
            "source_authority": "high",
            "is_official": True
        }
        
        boost = result_combiner._calculate_authority_boost(metadata)
        
        assert isinstance(boost, (int, float))
        assert boost >= 0


class TestResultCombinerFiltering:
    """Test result filtering functionality."""

    def test_should_skip_result_basic(self, result_combiner, sample_query_context):
        """Test basic result filtering logic."""
        metadata = {"source_type": "confluence"}
        result_filters = {"allowed_sources": ["git", "jira"]}
        
        should_skip = result_combiner._should_skip_result(
            metadata, result_filters, sample_query_context
        )
        
        assert isinstance(should_skip, bool)

    def test_should_skip_result_no_filters(self, result_combiner, sample_query_context):
        """Test that no filtering occurs when no filters are provided."""
        metadata = {"source_type": "confluence"}
        result_filters = {}
        
        should_skip = result_combiner._should_skip_result(
            metadata, result_filters, sample_query_context
        )
        
        assert should_skip is False

    @pytest.mark.asyncio
    async def test_apply_intent_specific_filtering(self, result_combiner, sample_vector_results, sample_query_context):
        """Test intent-specific filtering."""
        # Modify query context to include filtering
        query_context_with_filters = {
            **sample_query_context,
            "adaptive_config": MagicMock(result_filters={"min_word_count": 150})
        }
        
        with patch.object(result_combiner.metadata_extractor, 'extract_all_metadata', return_value={}):
            with patch.object(result_combiner, '_should_skip_result', return_value=False):
                combined = await result_combiner.combine_results(
                    vector_results=sample_vector_results,
                    keyword_results=[],
                    query_context=query_context_with_filters,
                    limit=10
                )
        
        assert isinstance(combined, list)


class TestResultCombinerHelperMethods:
    """Test helper methods of ResultCombiner."""

    def test_extract_project_relevance(self, result_combiner):
        """Test project relevance extraction."""
        metadata = {
            "project_id": "proj-123",
            "project_relevance": 0.9
        }
        query_context = {"target_project": "proj-123"}
        
        relevance = result_combiner._extract_project_relevance(metadata, query_context)
        
        assert isinstance(relevance, (int, float))
        assert 0 <= relevance <= 1

    def test_extract_content_richness(self, result_combiner):
        """Test content richness extraction."""
        metadata = {
            "has_code_blocks": True,
            "has_images": True,
            "has_tables": False,
            "word_count": 500
        }
        
        richness = result_combiner._extract_content_richness(metadata)
        
        assert isinstance(richness, (int, float))
        assert richness >= 0

    def test_extract_semantic_relevance(self, result_combiner, sample_query_context):
        """Test semantic relevance extraction."""
        metadata = {
            "semantic_score": 0.85,
            "keyword_matches": 5
        }
        
        relevance = result_combiner._extract_semantic_relevance(metadata, sample_query_context)
        
        assert isinstance(relevance, (int, float))
        assert relevance >= 0

    def test_normalize_score(self, result_combiner):
        """Test score normalization."""
        # Test various score values
        assert result_combiner._normalize_score(0.5) == 0.5
        assert result_combiner._normalize_score(1.5) == 1.0
        assert result_combiner._normalize_score(-0.1) == 0.0

    def test_calculate_position_boost(self, result_combiner):
        """Test position-based boost calculation."""
        # Earlier positions should get higher boosts
        boost_pos_0 = result_combiner._calculate_position_boost(0)
        boost_pos_5 = result_combiner._calculate_position_boost(5)
        
        assert boost_pos_0 >= boost_pos_5
        assert isinstance(boost_pos_0, (int, float))

    @pytest.mark.asyncio
    async def test_async_score_enhancement(self, result_combiner, sample_query_context):
        """Test asynchronous score enhancement."""
        base_score = 0.7
        metadata = {"word_count": 300}
        
        enhanced_score = await result_combiner._async_score_enhancement(
            base_score, metadata, sample_query_context
        )
        
        assert isinstance(enhanced_score, (int, float))
        assert enhanced_score >= 0


class TestResultCombinerEdgeCases:
    """Test edge cases and error conditions."""

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
                # Missing 'score' field
            }
        ]
        
        with patch.object(result_combiner.metadata_extractor, 'extract_all_metadata', return_value={}):
            # Should handle malformed data gracefully
            combined = await result_combiner.combine_results(
                vector_results=malformed_results,
                keyword_results=[],
                query_context=sample_query_context,
                limit=10
            )
        
        # Should process valid results and skip invalid ones
        assert isinstance(combined, list)

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
            combined = await result_combiner.combine_results(
                vector_results=results_with_none_metadata,
                keyword_results=[],
                query_context=sample_query_context,
                limit=10
            )
        
        assert isinstance(combined, list)

    def test_boost_score_with_empty_metadata(self, result_combiner, sample_query_context):
        """Test score boosting with empty metadata."""
        base_score = 0.6
        empty_metadata = {}
        
        boosted_score = result_combiner._boost_score_with_metadata(
            base_score, empty_metadata, sample_query_context
        )
        
        # Should not crash and should return a valid score
        assert isinstance(boosted_score, (int, float))
        assert boosted_score >= 0

    @pytest.mark.asyncio
    async def test_large_result_set_handling(self, result_combiner, sample_query_context):
        """Test handling of large result sets."""
        # Create a large number of results
        large_vector_results = []
        for i in range(1000):
            large_vector_results.append({
                "text": f"Document {i}",
                "score": 0.5 + (i % 100) / 200,  # Varying scores
                "source_type": "git",
                "title": f"Doc {i}",
                "document_id": f"doc{i}",
                "metadata": {"index": i}
            })
        
        with patch.object(result_combiner.metadata_extractor, 'extract_all_metadata', return_value={}):
            combined = await result_combiner.combine_results(
                vector_results=large_vector_results,
                keyword_results=[],
                query_context=sample_query_context,
                limit=50  # Limit to 50 results
            )
        
        assert len(combined) <= 50
        assert isinstance(combined, list)
