"""Unit tests for CDI orchestration layer similarity threshold filtering."""

from unittest.mock import Mock

import pytest
from qdrant_loader_mcp_server.search.components.search_result_models import (
    create_hybrid_search_result,
)
from qdrant_loader_mcp_server.search.hybrid.orchestration.cdi import (
    find_similar_documents,
)


@pytest.fixture
def mock_engine():
    """
    Create a mock engine configured for similarity tests.
    
    The returned Mock has a `cross_document_engine` attribute that is a Mock, and that object's
    `similarity_calculator` attribute is also a Mock.
    
    Returns:
        Mock: A configured mock engine with `cross_document_engine` and its `similarity_calculator`.
    """
    engine = Mock()
    engine.cross_document_engine = Mock()
    engine.cross_document_engine.similarity_calculator = Mock()
    return engine


@pytest.fixture
def target_document():
    """Create a target document for similarity comparison."""
    return create_hybrid_search_result(
        score=0.9,
        text="OAuth authentication implementation guide",
        source_type="confluence",
        source_title="OAuth Guide - Chunk 1",
        document_id="target-doc-id",
        entities=[{"text": "OAuth", "label": "TECH"}],
        topics=[{"text": "authentication", "score": 0.9}],
    )


@pytest.fixture
def comparison_documents():
    """
    Create three hybrid search result documents with distinct similarity scores for testing.
    
    Each returned document represents a comparison candidate:
    - "high-similarity-doc": score 0.85, contains JWT-related text and an entity.
    - "medium-similarity-doc": score 0.6, database schema text.
    - "low-similarity-doc": score 0.3, marketing text.
    
    Returns:
        list: A list of three hybrid search result objects used as comparison documents in tests.
    """
    return [
        create_hybrid_search_result(
            score=0.85,
            text="JWT token implementation",
            source_type="git",
            source_title="JWT Implementation - Chunk 1",
            document_id="high-similarity-doc",
            entities=[{"text": "JWT", "label": "TECH"}],
        ),
        create_hybrid_search_result(
            score=0.6,
            text="Database schema design",
            source_type="confluence",
            source_title="DB Schema - Chunk 1",
            document_id="medium-similarity-doc",
        ),
        create_hybrid_search_result(
            score=0.3,
            text="Marketing campaign strategy",
            source_type="confluence",
            source_title="Marketing Strategy - Chunk 1",
            document_id="low-similarity-doc",
        ),
    ]


class TestSimilarityThresholdFiltering:
    """Test similarity threshold filtering in find_similar_documents."""

    @pytest.mark.asyncio
    async def test_default_threshold_filters_low_scores(
        self, mock_engine, target_document, comparison_documents
    ):
        """Test that default threshold (0.7) filters out low similarity documents."""
        # Mock similarity scores: 0.85, 0.65, 0.35
        mock_similarities = [
            Mock(
                similarity_score=0.85,
                metric_scores={},
                get_display_explanation=lambda: "High similarity",
            ),
            Mock(
                similarity_score=0.65,
                metric_scores={},
                get_display_explanation=lambda: "Medium similarity",
            ),
            Mock(
                similarity_score=0.35,
                metric_scores={},
                get_display_explanation=lambda: "Low similarity",
            ),
        ]
        mock_engine.cross_document_engine.similarity_calculator.calculate_similarity.side_effect = (
            mock_similarities
        )

        # Call with default threshold (0.7)
        result = await find_similar_documents(
            mock_engine,
            target_document,
            comparison_documents,
            similarity_metrics=None,
            max_similar=5,
            similarity_threshold=0.7,  # Default
        )

        # Should only return documents with score >= 0.7
        assert len(result) == 1
        assert result[0]["similarity_score"] == 0.85
        assert result[0]["document_id"] == "high-similarity-doc"

    @pytest.mark.asyncio
    async def test_low_threshold_returns_more_documents(
        self, mock_engine, target_document, comparison_documents
    ):
        """Test that lower threshold (0.5) includes more documents."""
        mock_similarities = [
            Mock(
                similarity_score=0.85,
                metric_scores={},
                get_display_explanation=lambda: "High",
            ),
            Mock(
                similarity_score=0.65,
                metric_scores={},
                get_display_explanation=lambda: "Medium",
            ),
            Mock(
                similarity_score=0.35,
                metric_scores={},
                get_display_explanation=lambda: "Low",
            ),
        ]
        mock_engine.cross_document_engine.similarity_calculator.calculate_similarity.side_effect = (
            mock_similarities
        )

        # Call with lower threshold (0.5)
        result = await find_similar_documents(
            mock_engine,
            target_document,
            comparison_documents,
            similarity_metrics=None,
            max_similar=5,
            similarity_threshold=0.5,  # Lower threshold
        )

        # Should return 2 documents with score >= 0.5
        assert len(result) == 2
        assert result[0]["similarity_score"] == 0.85
        assert result[1]["similarity_score"] == 0.65

    @pytest.mark.asyncio
    async def test_high_threshold_filters_aggressively(
        self, mock_engine, target_document, comparison_documents
    ):
        """Test that high threshold (0.9) filters out most documents."""
        mock_similarities = [
            Mock(
                similarity_score=0.85,
                metric_scores={},
                get_display_explanation=lambda: "High",
            ),
            Mock(
                similarity_score=0.65,
                metric_scores={},
                get_display_explanation=lambda: "Medium",
            ),
            Mock(
                similarity_score=0.35,
                metric_scores={},
                get_display_explanation=lambda: "Low",
            ),
        ]
        mock_engine.cross_document_engine.similarity_calculator.calculate_similarity.side_effect = (
            mock_similarities
        )

        # Call with high threshold (0.9)
        result = await find_similar_documents(
            mock_engine,
            target_document,
            comparison_documents,
            similarity_metrics=None,
            max_similar=5,
            similarity_threshold=0.9,  # Very high threshold
        )

        # Should return no documents (none reach 0.9)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_threshold_zero_returns_all_documents(
        self, mock_engine, target_document, comparison_documents
    ):
        """Test that threshold 0.0 returns all non-identical documents."""
        mock_similarities = [
            Mock(
                similarity_score=0.85,
                metric_scores={},
                get_display_explanation=lambda: "High",
            ),
            Mock(
                similarity_score=0.65,
                metric_scores={},
                get_display_explanation=lambda: "Medium",
            ),
            Mock(
                similarity_score=0.35,
                metric_scores={},
                get_display_explanation=lambda: "Low",
            ),
        ]
        mock_engine.cross_document_engine.similarity_calculator.calculate_similarity.side_effect = (
            mock_similarities
        )

        # Call with threshold 0.0
        result = await find_similar_documents(
            mock_engine,
            target_document,
            comparison_documents,
            similarity_metrics=None,
            max_similar=5,
            similarity_threshold=0.0,  # No filtering
        )

        # Should return all 3 documents
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_threshold_respects_max_similar_limit(
        self, mock_engine, target_document
    ):
        """Test that max_similar is applied after threshold filtering."""
        # Create 5 comparison documents all above threshold
        many_docs = [
            create_hybrid_search_result(
                score=0.8,
                text=f"Document {i}",
                source_type="confluence",
                source_title=f"Doc {i} - Chunk 1",
                document_id=f"doc-{i}",
            )
            for i in range(5)
        ]

        # All have similarity > 0.7
        mock_similarities = [
            Mock(
                similarity_score=0.8 + i * 0.01,
                metric_scores={},
                get_display_explanation=lambda idx=i: f"Doc {idx}",
            )
            for i in range(5)
        ]
        mock_engine.cross_document_engine.similarity_calculator.calculate_similarity.side_effect = (
            mock_similarities
        )

        # Call with threshold 0.7 and max_similar=3
        result = await find_similar_documents(
            mock_engine,
            target_document,
            many_docs,
            similarity_metrics=None,
            max_similar=3,  # Limit to 3
            similarity_threshold=0.7,
        )

        # Should return only 3 documents (top 3 by score)
        assert len(result) == 3
        # Should be sorted by score (descending)
        assert result[0]["similarity_score"] >= result[1]["similarity_score"]
        assert result[1]["similarity_score"] >= result[2]["similarity_score"]

    @pytest.mark.asyncio
    async def test_threshold_filtering_preserves_document_structure(
        self, mock_engine, target_document, comparison_documents
    ):
        """Test that threshold filtering preserves complete document structure."""
        mock_similarity = Mock(
            similarity_score=0.85,
            metric_scores={"semantic": 0.9, "entity": 0.8},
            get_display_explanation=lambda: "High similarity based on shared entities",
        )
        mock_engine.cross_document_engine.similarity_calculator.calculate_similarity.return_value = (
            mock_similarity
        )

        result = await find_similar_documents(
            mock_engine,
            target_document,
            [comparison_documents[0]],  # Just one doc
            similarity_metrics=None,
            max_similar=5,
            similarity_threshold=0.7,
        )

        # Should preserve all fields
        assert len(result) == 1
        assert "document_id" in result[0]
        assert "document" in result[0]
        assert "similarity_score" in result[0]
        assert "metric_scores" in result[0]
        assert "similarity_reasons" in result[0]
        assert result[0]["similarity_score"] == 0.85
        assert result[0]["metric_scores"] == {"semantic": 0.9, "entity": 0.8}

    @pytest.mark.asyncio
    async def test_skips_target_document_in_comparisons(
        self, mock_engine, target_document
    ):
        """Test that target document is skipped even if in comparison list."""
        # Include target document in comparison list
        comparison_docs = [
            target_document,  # Same document
            create_hybrid_search_result(
                score=0.8,
                text="Different document",
                source_type="git",
                source_title="Different - Chunk 1",
                document_id="different-doc",
            ),
        ]

        mock_similarity = Mock(
            similarity_score=0.85,
            metric_scores={},
            get_display_explanation=lambda: "Similar",
        )
        mock_engine.cross_document_engine.similarity_calculator.calculate_similarity.return_value = (
            mock_similarity
        )

        result = await find_similar_documents(
            mock_engine,
            target_document,
            comparison_docs,
            similarity_metrics=None,
            max_similar=5,
            similarity_threshold=0.7,
        )

        # Should only return 1 document (target excluded)
        assert len(result) == 1
        assert result[0]["document_id"] == "different-doc"
        # calculate_similarity should only be called once (for non-target doc)
        assert (
            mock_engine.cross_document_engine.similarity_calculator.calculate_similarity.call_count
            == 1
        )