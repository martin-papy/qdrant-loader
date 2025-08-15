"""Advanced tests for the search engine implementation to reach 80% coverage."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_loader_mcp_server.config import OpenAIConfig, QdrantConfig, SearchConfig
from qdrant_loader_mcp_server.search.components.search_result_models import (
    create_hybrid_search_result,
)
from qdrant_loader_mcp_server.search.engine import SearchEngine
from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
    ClusteringStrategy,
)
from qdrant_loader_mcp_server.search.enhanced.topic_search_chain import (
    ChainStrategy,
    TopicChainLink,
    TopicSearchChain,
)


@pytest.fixture
def search_engine():
    """Create a search engine instance."""
    return SearchEngine()


@pytest.fixture
def qdrant_config():
    """Create Qdrant configuration."""
    return QdrantConfig(
        url="http://localhost:6333",
        api_key="test_key",
        collection_name="test_collection",
    )


@pytest.fixture
def openai_config():
    """Create OpenAI configuration."""
    return OpenAIConfig(api_key="test_key")


@pytest.fixture
def search_config():
    """Create search configuration."""
    return SearchConfig(
        vector_weight=0.7,
        keyword_weight=0.3,
        min_score=0.5,
        enable_query_expansion=True,
    )


@pytest.fixture
def sample_search_results():
    """Create sample search results for testing."""
    return [
        create_hybrid_search_result(
            score=0.9,
            text="Sample document about AI and machine learning",
            source_type="confluence",
            source_title="AI Documentation",
            source_url="http://test.com/ai-doc",
            document_id="doc1",
            project_id="proj1",
            entities=["AI", "machine learning", "neural networks"],
            topics=["artificial intelligence", "technology"],
            breadcrumb_text="Technology > AI > Documentation",
        ),
        create_hybrid_search_result(
            score=0.8,
            text="Development guide for implementing ML models",
            source_type="git",
            source_title="ML Implementation Guide",
            source_url="http://test.com/ml-guide",
            document_id="doc2",
            project_id="proj1",
            entities=["models", "implementation", "Python"],
            topics=["development", "machine learning"],
            breadcrumb_text="Development > ML > Guides",
        ),
        create_hybrid_search_result(
            score=0.7,
            text="Best practices for data preprocessing in ML pipelines",
            source_type="confluence",
            source_title="Data Preprocessing Guide",
            source_url="http://test.com/data-guide",
            document_id="doc3",
            project_id="proj2",
            entities=["data", "preprocessing", "pipelines"],
            topics=["data science", "machine learning"],
            breadcrumb_text="Data Science > Preprocessing",
        ),
    ]


@pytest.fixture
def mock_topic_chain():
    """Create a mock topic search chain."""
    chain_link1 = TopicChainLink(
        query="machine learning basics",
        topic_focus="ML fundamentals",
        related_topics=["algorithms", "basics"],
        chain_position=1,
        relevance_score=0.9,
        reasoning="Starting with ML fundamentals",
    )
    chain_link2 = TopicChainLink(
        query="neural networks implementation",
        topic_focus="deep learning",
        related_topics=["neural networks", "implementation"],
        chain_position=2,
        relevance_score=0.7,
        reasoning="Exploring neural network implementations",
    )

    return TopicSearchChain(
        original_query="AI and machine learning",
        chain_links=[chain_link1, chain_link2],
        strategy=ChainStrategy.MIXED_EXPLORATION,
        total_topics_covered=4,
        estimated_discovery_potential=0.85,
        chain_coherence_score=0.8,
        generation_time_ms=150,
    )


# ============================================================================
# Topic Chain Tests
# ============================================================================


@pytest.mark.asyncio
async def test_generate_topic_chain_success(
    search_engine,
    qdrant_config,
    openai_config,
    mock_qdrant_client,
    mock_openai_client,
    mock_topic_chain,
):
    """Test successful topic chain generation."""
    mock_hybrid_search = AsyncMock()
    mock_hybrid_search.generate_topic_search_chain.return_value = mock_topic_chain

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):
        await search_engine.initialize(qdrant_config, openai_config)

        result = await search_engine.generate_topic_chain(
            query="AI and machine learning", strategy="mixed_exploration", max_links=5
        )

        assert result == mock_topic_chain
        assert result.original_query == "AI and machine learning"
        assert len(result.chain_links) == 2
        assert result.strategy == ChainStrategy.MIXED_EXPLORATION

        mock_hybrid_search.generate_topic_search_chain.assert_called_once_with(
            query="AI and machine learning",
            strategy=ChainStrategy.MIXED_EXPLORATION,
            max_links=5,
        )


@pytest.mark.asyncio
async def test_generate_topic_chain_invalid_strategy(
    search_engine,
    qdrant_config,
    openai_config,
    mock_qdrant_client,
    mock_openai_client,
    mock_topic_chain,
):
    """Test topic chain generation with invalid strategy falls back to default."""
    mock_hybrid_search = AsyncMock()
    mock_hybrid_search.generate_topic_search_chain.return_value = mock_topic_chain

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):
        await search_engine.initialize(qdrant_config, openai_config)

        result = await search_engine.generate_topic_chain(
            query="test query", strategy="invalid_strategy", max_links=3
        )

        assert result == mock_topic_chain
        # Should have fallen back to MIXED_EXPLORATION
        mock_hybrid_search.generate_topic_search_chain.assert_called_once_with(
            query="test query", strategy=ChainStrategy.MIXED_EXPLORATION, max_links=3
        )


@pytest.mark.asyncio
async def test_execute_topic_chain_success(
    search_engine,
    qdrant_config,
    openai_config,
    mock_qdrant_client,
    mock_openai_client,
    mock_topic_chain,
    sample_search_results,
):
    """Test successful topic chain execution."""
    mock_hybrid_search = AsyncMock()
    chain_results = {
        "machine learning basics": sample_search_results[:2],
        "neural networks implementation": sample_search_results[1:],
    }
    mock_hybrid_search.execute_topic_chain_search.return_value = chain_results

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):
        await search_engine.initialize(qdrant_config, openai_config)

        result = await search_engine.execute_topic_chain(
            topic_chain=mock_topic_chain,
            results_per_link=3,
            source_types=["confluence"],
            project_ids=["proj1"],
        )

        assert result == chain_results
        assert len(result) == 2
        assert "machine learning basics" in result
        assert "neural networks implementation" in result

        mock_hybrid_search.execute_topic_chain_search.assert_called_once_with(
            topic_chain=mock_topic_chain,
            results_per_link=3,
            source_types=["confluence"],
            project_ids=["proj1"],
        )


@pytest.mark.asyncio
async def test_search_with_topic_chain_success(
    search_engine,
    qdrant_config,
    openai_config,
    mock_qdrant_client,
    mock_openai_client,
    mock_topic_chain,
    sample_search_results,
):
    """Test successful combined topic chain generation and execution."""
    mock_hybrid_search = AsyncMock()
    mock_hybrid_search.generate_topic_search_chain.return_value = mock_topic_chain

    chain_results = {
        "machine learning basics": sample_search_results[:2],
        "neural networks implementation": sample_search_results[1:],
    }
    mock_hybrid_search.execute_topic_chain_search.return_value = chain_results

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):
        await search_engine.initialize(qdrant_config, openai_config)

        result = await search_engine.search_with_topic_chain(
            query="AI and machine learning",
            strategy="breadth_first",
            max_links=4,
            results_per_link=2,
            source_types=["git", "confluence"],
            project_ids=["proj1", "proj2"],
        )

        assert result == chain_results
        assert len(result) == 2

        # Verify both methods were called
        mock_hybrid_search.generate_topic_search_chain.assert_called_once()
        mock_hybrid_search.execute_topic_chain_search.assert_called_once()


# ============================================================================
# Faceted Search Tests
# ============================================================================


@pytest.mark.asyncio
async def test_search_with_facets_success(
    search_engine,
    qdrant_config,
    openai_config,
    mock_qdrant_client,
    mock_openai_client,
    sample_search_results,
):
    """Test successful faceted search."""
    mock_hybrid_search = AsyncMock()

    # Create mock faceted results
    mock_faceted_results = MagicMock()
    mock_faceted_results.results = sample_search_results
    mock_faceted_results.total_results = 10
    mock_faceted_results.filtered_count = 3
    mock_faceted_results.applied_filters = []
    mock_faceted_results.generation_time_ms = 250

    # Mock facets
    mock_facet = MagicMock()
    mock_facet.facet_type.value = "source_type"
    mock_facet.name = "source_type"
    mock_facet.display_name = "Source Type"
    mock_facet.description = "Type of document source"

    mock_facet_value = MagicMock()
    mock_facet_value.value = "confluence"
    mock_facet_value.count = 2
    mock_facet_value.display_name = "Confluence"
    mock_facet_value.description = "Confluence documents"

    mock_facet.get_top_values.return_value = [mock_facet_value]
    mock_faceted_results.facets = [mock_facet]

    mock_hybrid_search.search_with_facets.return_value = mock_faceted_results

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):
        await search_engine.initialize(qdrant_config, openai_config)

        result = await search_engine.search_with_facets(
            query="machine learning",
            limit=5,
            source_types=["confluence"],
            project_ids=["proj1"],
            facet_filters=[
                {
                    "facet_type": "source_type",
                    "values": ["confluence"],
                    "operator": "OR",
                }
            ],
        )

        assert "results" in result
        assert "facets" in result
        assert "total_results" in result
        assert "filtered_count" in result
        assert "applied_filters" in result
        assert "generation_time_ms" in result

        assert len(result["results"]) == 3
        assert result["total_results"] == 10
        assert result["filtered_count"] == 3
        assert len(result["facets"]) == 1

        facet = result["facets"][0]
        assert facet["type"] == "source_type"
        assert facet["name"] == "source_type"
        assert facet["display_name"] == "Source Type"
        assert len(facet["values"]) == 1


@pytest.mark.asyncio
async def test_get_facet_suggestions_success(
    search_engine,
    qdrant_config,
    openai_config,
    mock_qdrant_client,
    mock_openai_client,
    sample_search_results,
):
    """Test successful facet suggestions."""
    mock_hybrid_search = AsyncMock()
    mock_hybrid_search.search.return_value = sample_search_results

    mock_suggestions = [
        {
            "facet_type": "source_type",
            "facet_display_name": "Source Type",
            "value": "confluence",
            "display_name": "Confluence",
            "current_count": 3,
            "filtered_count": 2,
            "reduction_percent": 33,
        },
        {
            "facet_type": "project_id",
            "facet_display_name": "Project",
            "value": "proj1",
            "display_name": "Project 1",
            "current_count": 3,
            "filtered_count": 2,
            "reduction_percent": 33,
        },
    ]
    # Ensure the mock returns the value directly, not as a coroutine
    mock_hybrid_search.suggest_facet_refinements = MagicMock(
        return_value=mock_suggestions
    )

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):
        await search_engine.initialize(qdrant_config, openai_config)

        result = await search_engine.get_facet_suggestions(
            query="machine learning",
            current_filters=[
                {
                    "facet_type": "source_type",
                    "values": ["confluence"],
                    "operator": "OR",
                }
            ],
            limit=20,
        )

        assert result == mock_suggestions
        assert len(result) == 2
        assert result[0]["facet_type"] == "source_type"
        assert result[1]["facet_type"] == "project_id"

        # Verify search was called to get current results
        mock_hybrid_search.search.assert_called_once_with(
            query="machine learning", limit=20, source_types=None, project_ids=None
        )


# ============================================================================
# Cross-Document Intelligence Tests
# ============================================================================


@pytest.mark.asyncio
async def test_analyze_document_relationships_success(
    search_engine,
    qdrant_config,
    openai_config,
    mock_qdrant_client,
    mock_openai_client,
    sample_search_results,
):
    """Test successful document relationship analysis."""
    mock_hybrid_search = AsyncMock()
    mock_hybrid_search.search.return_value = sample_search_results

    mock_analysis = {
        "entity_relationships": [
            {
                "entity_pair": ["AI", "machine learning"],
                "relationship_type": "semantic_overlap",
                "strength": 0.9,
                "documents": ["doc1", "doc2"],
            }
        ],
        "topic_clusters": [
            {
                "cluster_id": "cluster1",
                "central_topic": "machine learning",
                "related_topics": ["AI", "neural networks"],
                "documents": ["doc1", "doc2", "doc3"],
            }
        ],
        "semantic_connections": [
            {
                "source_doc": "doc1",
                "target_doc": "doc2",
                "connection_type": "conceptual_similarity",
                "strength": 0.8,
            }
        ],
    }
    mock_hybrid_search.analyze_document_relationships.return_value = mock_analysis

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):
        await search_engine.initialize(qdrant_config, openai_config)

        result = await search_engine.analyze_document_relationships(
            query="machine learning",
            limit=20,
            source_types=["confluence"],
            project_ids=["proj1"],
        )

        assert "entity_relationships" in result
        assert "topic_clusters" in result
        assert "semantic_connections" in result
        assert "query_metadata" in result

        query_metadata = result["query_metadata"]
        assert query_metadata["original_query"] == "machine learning"
        assert query_metadata["document_count"] == 3
        assert query_metadata["source_types"] == ["confluence"]
        assert query_metadata["project_ids"] == ["proj1"]


@pytest.mark.asyncio
async def test_analyze_document_relationships_insufficient_docs(
    search_engine,
    qdrant_config,
    openai_config,
    mock_qdrant_client,
    mock_openai_client,
    sample_search_results,
):
    """Test document relationship analysis with insufficient documents."""
    mock_hybrid_search = AsyncMock()
    mock_hybrid_search.search.return_value = [
        sample_search_results[0]
    ]  # Only 1 document

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):
        await search_engine.initialize(qdrant_config, openai_config)

        result = await search_engine.analyze_document_relationships(
            query="machine learning", limit=20
        )

        assert "error" in result
        assert "document_count" in result
        assert result["document_count"] == 1
        assert "Need at least 2 documents" in result["error"]


@pytest.mark.asyncio
async def test_find_similar_documents_success(
    search_engine,
    qdrant_config,
    openai_config,
    mock_qdrant_client,
    mock_openai_client,
    sample_search_results,
):
    """Test successful similar documents search."""
    mock_hybrid_search = AsyncMock()
    mock_hybrid_search.search.side_effect = [
        [sample_search_results[0]],  # Target document
        sample_search_results[1:],  # Comparison documents
    ]

    mock_similar_docs = [
        {
            "document": sample_search_results[1],
            "similarity_scores": {
                "semantic_similarity": 0.85,
                "entity_overlap": 0.7,
                "topic_overlap": 0.9,
            },
            "overall_similarity": 0.82,
            "explanation": "High semantic and topic overlap",
        }
    ]
    mock_hybrid_search.find_similar_documents.return_value = mock_similar_docs

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):
        await search_engine.initialize(qdrant_config, openai_config)

        result = await search_engine.find_similar_documents(
            target_query="AI documentation",
            comparison_query="machine learning guides",
            similarity_metrics=["semantic_similarity", "entity_overlap"],
            max_similar=3,
            source_types=["confluence"],
            project_ids=["proj1"],
        )

        assert result == mock_similar_docs
        assert len(result) == 1
        assert "similarity_scores" in result[0]
        assert "overall_similarity" in result[0]

        # Verify both searches were called
        assert mock_hybrid_search.search.call_count == 2


@pytest.mark.asyncio
async def test_find_similar_documents_no_target(
    search_engine, qdrant_config, openai_config, mock_qdrant_client, mock_openai_client
):
    """Test similar documents search with no target document found."""
    mock_hybrid_search = AsyncMock()
    mock_hybrid_search.search.return_value = []  # No target document found

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):
        await search_engine.initialize(qdrant_config, openai_config)

        result = await search_engine.find_similar_documents(
            target_query="nonexistent document",
            comparison_query="machine learning guides",
        )

        assert result == []


@pytest.mark.asyncio
async def test_detect_document_conflicts_success(
    search_engine,
    qdrant_config,
    openai_config,
    mock_qdrant_client,
    mock_openai_client,
    sample_search_results,
):
    """Test successful document conflict detection."""
    mock_hybrid_search = AsyncMock()
    mock_hybrid_search.search.return_value = sample_search_results

    mock_conflicts = {
        "conflicts": [
            {
                "conflict_type": "contradictory_information",
                "documents": ["doc1", "doc2"],
                "description": "Conflicting ML approaches",
                "severity": "medium",
                "confidence": 0.7,
            }
        ],
        "resolution_suggestions": [
            {
                "conflict_id": "conf1",
                "suggestion": "Review both approaches and create unified guidance",
                "priority": "high",
            }
        ],
    }
    mock_hybrid_search.detect_document_conflicts.return_value = mock_conflicts

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):
        await search_engine.initialize(qdrant_config, openai_config)

        result = await search_engine.detect_document_conflicts(
            query="machine learning approaches",
            limit=15,
            source_types=["confluence"],
            project_ids=["proj1"],
        )

        assert "conflicts" in result
        assert "resolution_suggestions" in result
        assert "query_metadata" in result
        assert "original_documents" in result

        query_metadata = result["query_metadata"]
        assert query_metadata["original_query"] == "machine learning approaches"
        assert query_metadata["document_count"] == 3

        # Verify original documents are stored in lightweight form
        original_docs = result["original_documents"]
        assert isinstance(original_docs, list) and len(original_docs) == len(sample_search_results)
        # Compare by IDs and safe fields only
        expected = [
            {
                "document_id": d.document_id,
                "title": (
                    getattr(d, "get_display_title")()
                    if hasattr(d, "get_display_title")
                    else getattr(d, "source_title", None) or "Untitled"
                ),
                "source_type": getattr(d, "source_type", "unknown") or "unknown",
            }
            for d in sample_search_results
        ]
        assert original_docs == expected


@pytest.mark.asyncio
async def test_detect_document_conflicts_insufficient_docs(
    search_engine,
    qdrant_config,
    openai_config,
    mock_qdrant_client,
    mock_openai_client,
    sample_search_results,
):
    """Test conflict detection with insufficient documents."""
    mock_hybrid_search = AsyncMock()
    mock_hybrid_search.search.return_value = [
        sample_search_results[0]
    ]  # Only 1 document

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):
        await search_engine.initialize(qdrant_config, openai_config)

        result = await search_engine.detect_document_conflicts(
            query="test query", limit=15
        )

        assert "conflicts" in result
        assert "resolution_suggestions" in result
        assert "message" in result
        assert "document_count" in result
        assert result["document_count"] == 1
        assert "Need at least 2 documents" in result["message"]


@pytest.mark.asyncio
async def test_find_complementary_content_success(
    search_engine,
    qdrant_config,
    openai_config,
    mock_qdrant_client,
    mock_openai_client,
    sample_search_results,
):
    """Test successful complementary content search."""
    mock_hybrid_search = AsyncMock()
    mock_hybrid_search.search.side_effect = [
        [sample_search_results[0]],  # Target document
        sample_search_results[1:],  # Context documents
    ]

    mock_complementary = [
        {
            "document": sample_search_results[1],
            "complementary_score": 0.85,
            "relationship_type": "implementation_example",
            "explanation": "Provides practical implementation details",
        },
        {
            "document": sample_search_results[2],
            "complementary_score": 0.72,
            "relationship_type": "supporting_data",
            "explanation": "Contains relevant preprocessing techniques",
        },
    ]
    mock_hybrid_search.find_complementary_content.return_value = mock_complementary

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):
        await search_engine.initialize(qdrant_config, openai_config)

        result = await search_engine.find_complementary_content(
            target_query="AI documentation",
            context_query="machine learning guides",
            max_recommendations=5,
            source_types=["confluence"],
            project_ids=["proj1"],
        )

        assert "complementary_recommendations" in result
        assert "target_document" in result
        assert "context_documents_analyzed" in result

        # Engine now returns JSON-safe recommendation dicts; ensure non-empty and keys exist
        recs = result["complementary_recommendations"]
        assert isinstance(recs, list) and len(recs) == len(mock_complementary)
        for r in recs:
            assert set(["document_id", "title", "relevance_score", "reason", "strategy"]) <= set(r.keys())
        # target_document is now a lightweight dict
        assert isinstance(result["target_document"], dict)
        assert result["target_document"].get("document_id") == sample_search_results[0].document_id
        assert result["context_documents_analyzed"] == 2


@pytest.mark.asyncio
async def test_find_complementary_content_no_target(
    search_engine, qdrant_config, openai_config, mock_qdrant_client, mock_openai_client
):
    """Test complementary content search with no target document."""
    mock_hybrid_search = AsyncMock()
    mock_hybrid_search.search.return_value = []  # No target document found

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):
        await search_engine.initialize(qdrant_config, openai_config)

        result = await search_engine.find_complementary_content(
            target_query="nonexistent document", context_query="machine learning guides"
        )

        assert result["complementary_recommendations"] == []
        assert result["target_document"] is None
        assert result["context_documents_analyzed"] == 0


# ============================================================================
# Document Clustering Tests
# ============================================================================


@pytest.mark.asyncio
async def test_cluster_documents_success(
    search_engine,
    qdrant_config,
    openai_config,
    mock_qdrant_client,
    mock_openai_client,
    sample_search_results,
):
    """Test successful document clustering."""
    mock_hybrid_search = AsyncMock()
    mock_hybrid_search.search.return_value = sample_search_results

    mock_cluster_results = {
        "clusters": [
            {
                "cluster_id": "cluster1",
                "documents": [sample_search_results[0], sample_search_results[1]],
                "cluster_metadata": {
                    "central_topic": "machine learning",
                    "coherence_score": 0.85,
                    "size": 2,
                },
            },
            {
                "cluster_id": "cluster2",
                "documents": [sample_search_results[2]],
                "cluster_metadata": {
                    "central_topic": "data preprocessing",
                    "coherence_score": 0.9,
                    "size": 1,
                },
            },
        ],
        "clustering_metadata": {
            "strategy": "mixed_features",
            "total_documents": 3,
            "num_clusters": 2,
            "overall_coherence": 0.875,
        },
    }
    mock_hybrid_search.cluster_documents.return_value = mock_cluster_results

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):
        await search_engine.initialize(qdrant_config, openai_config)

        result = await search_engine.cluster_documents(
            query="machine learning guides",
            strategy="mixed_features",
            max_clusters=10,
            min_cluster_size=2,
            limit=25,
            source_types=["confluence"],
            project_ids=["proj1"],
        )

        assert "clusters" in result
        assert "clustering_metadata" in result

        assert len(result["clusters"]) == 2
        assert result["clustering_metadata"]["strategy"] == "mixed_features"
        assert result["clustering_metadata"]["total_documents"] == 3

        # Verify query metadata was added
        clustering_metadata = result["clustering_metadata"]
        assert clustering_metadata["original_query"] == "machine learning guides"
        assert clustering_metadata["source_types"] == ["confluence"]
        assert clustering_metadata["project_ids"] == ["proj1"]


@pytest.mark.asyncio
async def test_cluster_documents_insufficient_docs(
    search_engine,
    qdrant_config,
    openai_config,
    mock_qdrant_client,
    mock_openai_client,
    sample_search_results,
):
    """Test clustering with insufficient documents."""
    mock_hybrid_search = AsyncMock()
    mock_hybrid_search.search.return_value = [
        sample_search_results[0]
    ]  # Only 1 document

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):
        await search_engine.initialize(qdrant_config, openai_config)

        result = await search_engine.cluster_documents(
            query="test query", min_cluster_size=2
        )

        assert "clusters" in result
        assert "clustering_metadata" in result
        assert result["clusters"] == []

        clustering_metadata = result["clustering_metadata"]
        assert "message" in clustering_metadata
        assert "document_count" in clustering_metadata
        assert clustering_metadata["document_count"] == 1
        assert "Need at least 2 documents" in clustering_metadata["message"]


@pytest.mark.asyncio
async def test_cluster_documents_adaptive_strategy(
    search_engine,
    qdrant_config,
    openai_config,
    mock_qdrant_client,
    mock_openai_client,
    sample_search_results,
):
    """Test clustering with adaptive strategy selection."""
    mock_hybrid_search = AsyncMock()
    mock_hybrid_search.search.return_value = sample_search_results

    mock_cluster_results = {
        "clusters": [],
        "clustering_metadata": {
            "strategy": "entity_based",  # Adaptive selected this
            "total_documents": 3,
            "num_clusters": 0,
        },
    }
    mock_hybrid_search.cluster_documents.return_value = mock_cluster_results

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):
        await search_engine.initialize(qdrant_config, openai_config)

        # Mock _select_optimal_strategy to return entity_based
        with patch.object(
            search_engine, "_select_optimal_strategy", return_value="entity_based"
        ):
            result = await search_engine.cluster_documents(
                query="test query", strategy="adaptive"
            )

        assert "clusters" in result
        assert "clustering_metadata" in result

        # Verify adaptive strategy was used
        mock_hybrid_search.cluster_documents.assert_called_once()
        call_args = mock_hybrid_search.cluster_documents.call_args
        assert call_args[1]["strategy"] == ClusteringStrategy.ENTITY_BASED


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_search_error_handling(
    search_engine, qdrant_config, openai_config, mock_qdrant_client, mock_openai_client
):
    """Test search error handling."""
    mock_hybrid_search = AsyncMock()
    mock_hybrid_search.search.side_effect = Exception("Search failed")

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):
        await search_engine.initialize(qdrant_config, openai_config)

        with pytest.raises(Exception, match="Search failed"):
            await search_engine.search("test query")


@pytest.mark.asyncio
async def test_topic_chain_generation_error_handling(
    search_engine, qdrant_config, openai_config, mock_qdrant_client, mock_openai_client
):
    """Test topic chain generation error handling."""
    mock_hybrid_search = AsyncMock()
    mock_hybrid_search.generate_topic_search_chain.side_effect = Exception(
        "Generation failed"
    )

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):
        await search_engine.initialize(qdrant_config, openai_config)

        with pytest.raises(Exception, match="Generation failed"):
            await search_engine.generate_topic_chain("test query")


@pytest.mark.asyncio
async def test_topic_chain_execution_error_handling(
    search_engine,
    qdrant_config,
    openai_config,
    mock_qdrant_client,
    mock_openai_client,
    mock_topic_chain,
):
    """Test topic chain execution error handling."""
    mock_hybrid_search = AsyncMock()
    mock_hybrid_search.execute_topic_chain_search.side_effect = Exception(
        "Execution failed"
    )

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):
        await search_engine.initialize(qdrant_config, openai_config)

        with pytest.raises(Exception, match="Execution failed"):
            await search_engine.execute_topic_chain(mock_topic_chain)


# ============================================================================
# Additional Edge Cases and Boundary Conditions
# ============================================================================


@pytest.mark.asyncio
async def test_initialization_client_none_error(
    search_engine, qdrant_config, openai_config, mock_openai_client
):
    """Test initialization when qdrant client creation returns None."""
    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=None,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
    ):
        with pytest.raises(RuntimeError, match="Failed to connect to Qdrant server"):
            await search_engine.initialize(qdrant_config, openai_config)


def test_select_optimal_strategy_empty_documents():
    """Test strategy selection with empty document list."""
    search_engine = SearchEngine()

    strategy = search_engine._select_optimal_strategy([])
    assert strategy == "mixed_features"


def test_analyze_document_characteristics_with_breadcrumbs():
    """Test document characteristics analysis with breadcrumb data."""
    search_engine = SearchEngine()

    # Create documents with various breadcrumb depths
    documents = [
        MagicMock(breadcrumb_text="Root > Level1 > Level2 > Level3"),
        MagicMock(breadcrumb_text="Root > Level1"),
        MagicMock(breadcrumb_text="Root"),
        MagicMock(breadcrumb_text=""),  # No breadcrumb
    ]

    # Mock other attributes to avoid AttributeError
    for doc in documents:
        doc.entities = []
        doc.topics = []
        doc.project_id = "proj1"
        doc.source_type = "confluence"

    characteristics = search_engine._analyze_document_characteristics(documents)

    # Should calculate hierarchical structure based on breadcrumb depth
    assert "hierarchical_structure" in characteristics
    assert characteristics["hierarchical_structure"] >= 0.0
    assert characteristics["hierarchical_structure"] <= 1.0
