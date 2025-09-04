"""Tests for the search engine implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_loader_mcp_server.config import OpenAIConfig, QdrantConfig
from qdrant_loader_mcp_server.search.components.search_result_models import (
    create_hybrid_search_result,
)
from qdrant_loader_mcp_server.search.engine import SearchEngine


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


@pytest.mark.asyncio
async def test_search_engine_initialization(
    search_engine, qdrant_config, openai_config, mock_qdrant_client, mock_openai_client
):
    """Test search engine initialization."""
    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine"
        ) as mock_hybrid,
    ):

        await search_engine.initialize(qdrant_config, openai_config)

        assert search_engine.client is not None
        assert search_engine.openai_client is not None
        assert search_engine.hybrid_search is not None
        mock_hybrid.assert_called_once()


@pytest.mark.asyncio
async def test_search_engine_initialization_failure(
    search_engine, qdrant_config, openai_config
):
    """Test search engine initialization failure."""
    with patch(
        "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
        side_effect=Exception("Connection failed"),
    ):
        with pytest.raises(RuntimeError, match="Failed to connect to Qdrant server"):
            await search_engine.initialize(qdrant_config, openai_config)


@pytest.mark.asyncio
async def test_search_engine_search(
    search_engine, qdrant_config, openai_config, mock_qdrant_client, mock_openai_client
):
    """Test search functionality."""
    # Mock hybrid search
    mock_hybrid_search = AsyncMock()
    mock_results = [
        create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="git",
            source_title="Test Doc",
            source_url="http://test.com",
        )
    ]
    mock_hybrid_search.search.return_value = mock_results

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine",
            return_value=mock_hybrid_search,
        ),
    ):

        await search_engine.initialize(qdrant_config, openai_config)
        results = await search_engine.search("test query", ["git"], 5)

        assert len(results) == 1
        assert results[0].text == "Test content"
        assert results[0].source_type == "git"
        mock_hybrid_search.search.assert_called_once_with(
            query="test query", source_types=["git"], limit=5, project_ids=None
        )


@pytest.mark.asyncio
async def test_search_engine_search_not_initialized(search_engine):
    """Test search when engine is not initialized."""
    with pytest.raises(RuntimeError, match="Search engine not initialized"):
        await search_engine.search("test query")


@pytest.mark.asyncio
async def test_search_engine_cleanup(
    search_engine, qdrant_config, openai_config, mock_qdrant_client, mock_openai_client
):
    """Test search engine cleanup."""
    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch("qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine"),
    ):

        await search_engine.initialize(qdrant_config, openai_config)
        await search_engine.cleanup()

        mock_qdrant_client.close.assert_called_once()
        assert search_engine.client is None


@pytest.mark.asyncio
async def test_search_engine_collection_creation(
    search_engine, qdrant_config, openai_config, mock_qdrant_client, mock_openai_client
):
    """Test collection creation when it doesn't exist."""
    # Mock empty collections list
    collections_response = MagicMock()
    collections_response.collections = []
    mock_qdrant_client.get_collections.return_value = collections_response

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch("qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine"),
    ):

        await search_engine.initialize(qdrant_config, openai_config)

        mock_qdrant_client.create_collection.assert_called_once()


@pytest.mark.asyncio
async def test_search_engine_collection_exists(
    search_engine, qdrant_config, openai_config, mock_qdrant_client, mock_openai_client
):
    """Test when collection already exists."""
    # Mock existing collection
    collection = MagicMock()
    collection.name = "test_collection"
    collections_response = MagicMock()
    collections_response.collections = [collection]
    mock_qdrant_client.get_collections.return_value = collections_response

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch("qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine"),
    ):

        await search_engine.initialize(qdrant_config, openai_config)

        mock_qdrant_client.create_collection.assert_not_called()


@pytest.mark.asyncio
async def test_search_engine_generate_topic_chain_not_initialized():
    """Test topic chain generation when not initialized."""
    search_engine = SearchEngine()

    with pytest.raises(RuntimeError, match="Search engine not initialized"):
        await search_engine.generate_topic_chain("test query")


@pytest.mark.asyncio
async def test_search_engine_execute_topic_chain_not_initialized():
    """Test topic chain execution when not initialized."""
    search_engine = SearchEngine()

    # Mock topic chain
    mock_chain = AsyncMock()

    with pytest.raises(RuntimeError, match="Search engine not initialized"):
        await search_engine.execute_topic_chain(mock_chain)


@pytest.mark.asyncio
async def test_search_engine_search_with_topic_chain_not_initialized():
    """Test search with topic chain when not initialized."""
    search_engine = SearchEngine()

    with pytest.raises(RuntimeError, match="Search engine not initialized"):
        await search_engine.search_with_topic_chain("test query")


@pytest.mark.asyncio
async def test_search_engine_search_with_facets_not_initialized():
    """Test faceted search when not initialized."""
    search_engine = SearchEngine()

    with pytest.raises(RuntimeError, match="Search engine not initialized"):
        await search_engine.search_with_facets("test query")


@pytest.mark.asyncio
async def test_search_engine_get_facet_suggestions_not_initialized():
    """Test facet suggestions when not initialized."""
    search_engine = SearchEngine()

    with pytest.raises(RuntimeError, match="Search engine not initialized"):
        await search_engine.get_facet_suggestions("test query")


@pytest.mark.asyncio
async def test_search_engine_analyze_document_relationships_not_initialized():
    """Test document relationship analysis when not initialized."""
    search_engine = SearchEngine()

    with pytest.raises(RuntimeError, match="Search engine not initialized"):
        await search_engine.analyze_document_relationships("test query")


@pytest.mark.asyncio
async def test_search_engine_find_similar_documents_not_initialized():
    """Test finding similar documents when not initialized."""
    search_engine = SearchEngine()

    with pytest.raises(RuntimeError, match="Search engine not initialized"):
        await search_engine.find_similar_documents("target", "comparison")


@pytest.mark.asyncio
async def test_search_engine_detect_document_conflicts_not_initialized():
    """Test document conflict detection when not initialized."""
    search_engine = SearchEngine()

    with pytest.raises(RuntimeError, match="Search engine not initialized"):
        await search_engine.detect_document_conflicts("test query")


@pytest.mark.asyncio
async def test_search_engine_find_complementary_content_not_initialized():
    """Test finding complementary content when not initialized."""
    search_engine = SearchEngine()

    with pytest.raises(RuntimeError, match="Search engine not initialized"):
        await search_engine.find_complementary_content("target", "context")


@pytest.mark.asyncio
async def test_search_engine_cluster_documents_not_initialized():
    """Test document clustering when not initialized."""
    search_engine = SearchEngine()

    with pytest.raises(RuntimeError, match="Search engine not initialized"):
        await search_engine.cluster_documents("test query")


def test_search_engine_select_optimal_strategy():
    """Test optimal clustering strategy selection."""
    search_engine = SearchEngine()

    # Test with mixed document types
    documents = [
        {"source_type": "git", "project_id": "proj1", "has_entities": True},
        {"source_type": "confluence", "project_id": "proj1", "has_entities": False},
        {"source_type": "jira", "project_id": "proj2", "has_entities": True},
    ]

    strategy = search_engine._select_optimal_strategy(documents)

    # Should select mixed_features for diverse document types
    assert strategy in ["mixed_features", "adaptive", "entity_based", "project_based"]


def test_search_engine_select_optimal_strategy_project_based():
    """Test strategy selection for project-heavy scenarios."""
    search_engine = SearchEngine()

    # Test with multiple projects but same source type
    documents = [
        {"source_type": "git", "project_id": "proj1"},
        {"source_type": "git", "project_id": "proj2"},
        {"source_type": "git", "project_id": "proj3"},
        {"source_type": "git", "project_id": "proj4"},
        {"source_type": "git", "project_id": "proj5"},
    ]

    strategy = search_engine._select_optimal_strategy(documents)

    # Should favor project_based for multiple projects
    assert strategy in ["project_based", "mixed_features"]


def test_search_engine_select_optimal_strategy_entity_based():
    """Test strategy selection for entity-rich documents."""
    search_engine = SearchEngine()

    # Test with entity-rich documents
    documents = [
        {
            "source_type": "confluence",
            "project_id": "proj1",
            "entities": ["Entity1", "Entity2"],
        },
        {
            "source_type": "confluence",
            "project_id": "proj1",
            "entities": ["Entity3", "Entity4"],
        },
        {"source_type": "confluence", "project_id": "proj1", "entities": ["Entity5"]},
    ]

    strategy = search_engine._select_optimal_strategy(documents)

    # Should consider entity_based for entity-rich documents
    assert strategy in ["entity_based", "mixed_features", "topic_based"]


def test_search_engine_analyze_document_characteristics():
    """Test document characteristics analysis."""
    search_engine = SearchEngine()

    documents = [
        {
            "source_type": "git",
            "project_id": "proj1",
            "entities": ["Entity1", "Entity2"],
            "topics": ["topic1"],
            "parent_id": None,
        },
        {
            "source_type": "confluence",
            "project_id": "proj2",
            "entities": ["Entity3"],
            "topics": ["topic2", "topic3"],
            "parent_id": "parent1",
        },
        {
            "source_type": "jira",
            "project_id": "proj1",
            "entities": [],
            "topics": [],
            "parent_id": "parent2",
        },
    ]

    characteristics = search_engine._analyze_document_characteristics(documents)

    # Verify characteristics analysis - use the actual keys returned
    assert "source_diversity" in characteristics
    assert "entity_richness" in characteristics

    # Check reasonable values for what exists
    assert all(isinstance(value, int | float) for value in characteristics.values())
    assert all(value >= 0.0 for value in characteristics.values())


def test_search_engine_analyze_document_characteristics_empty():
    """Test document characteristics analysis with empty input."""
    search_engine = SearchEngine()

    characteristics = search_engine._analyze_document_characteristics([])

    # All characteristics should be 0.0 for empty input
    for value in characteristics.values():
        assert value == 0.0


def test_search_engine_analyze_document_characteristics_edge_cases():
    """Test document characteristics analysis with edge cases."""
    search_engine = SearchEngine()

    # Test with documents missing optional fields
    documents = [
        {"source_type": "git"},  # Missing most fields
        {"source_type": "git", "project_id": "proj1"},  # Missing entities, topics, etc.
    ]

    characteristics = search_engine._analyze_document_characteristics(documents)

    # Should handle missing fields gracefully
    assert all(isinstance(value, int | float) for value in characteristics.values())
    assert all(value >= 0.0 for value in characteristics.values())


# The not_initialized tests are already covered by the individual method tests above


@pytest.mark.asyncio
async def test_search_engine_initialization_with_search_config(
    search_engine, qdrant_config, openai_config, mock_qdrant_client, mock_openai_client
):
    """Test search engine initialization with custom search config."""
    from qdrant_loader_mcp_server.config import SearchConfig

    search_config = SearchConfig(
        vector_weight=0.8,
        keyword_weight=0.2,
        min_score=0.4,
        enable_query_expansion=False,
    )

    with (
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.AsyncOpenAI",
            return_value=mock_openai_client,
        ),
        patch(
            "qdrant_loader_mcp_server.search.engine.core.HybridSearchEngine"
        ) as mock_hybrid,
    ):
        await search_engine.initialize(qdrant_config, openai_config, search_config)

        # Verify HybridSearchEngine was created with search config
        mock_hybrid.assert_called_once_with(
            qdrant_client=mock_qdrant_client,
            openai_client=mock_openai_client,
            collection_name=qdrant_config.collection_name,
            search_config=search_config,
        )

        assert search_engine.hybrid_search is not None
