"""
Comprehensive unit tests for GraphitiManager.

This test suite covers:
- Initialization and configuration
- Client lifecycle management
- Search operations and optimizations
- Node and edge retrieval with error handling
- Performance monitoring
- Query optimization
- Error handling and edge cases
- Resource cleanup
- Context manager functionality
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from qdrant_loader.config.graphiti import (
    GraphitiConfig,
    GraphitiEmbedderConfig,
    GraphitiLLMConfig,
    GraphitiOperationalConfig,
)
from qdrant_loader.config.neo4j import Neo4jConfig
from qdrant_loader.core.managers.graphiti_manager import GraphitiManager


class TestGraphitiManager:
    """Comprehensive tests for GraphitiManager."""

    @pytest.fixture
    def mock_graphiti_config(self):
        """Create a mock GraphitiConfig for testing."""
        config = Mock(spec=GraphitiConfig)

        # Mock LLM config
        llm_config = Mock(spec=GraphitiLLMConfig)
        llm_config.model = "gpt-4"
        llm_config.api_key = "test-api-key"
        llm_config.max_tokens = 4000
        llm_config.temperature = 0.1
        config.llm = llm_config

        # Mock embedder config
        embedder_config = Mock(spec=GraphitiEmbedderConfig)
        embedder_config.model = "text-embedding-ada-002"
        embedder_config.api_key = "test-embedding-key"
        embedder_config.dimensions = None
        config.embedder = embedder_config

        # Mock operational config
        operational_config = Mock(spec=GraphitiOperationalConfig)
        operational_config.search_limit_max = 100
        operational_config.enable_auto_indexing = True
        operational_config.batch_size = 50
        config.operational = operational_config

        return config

    @pytest.fixture
    def mock_neo4j_config(self):
        """Create mock Neo4j configuration."""
        config = Mock(spec=Neo4jConfig)
        config.uri = "bolt://localhost:7687"
        config.user = "neo4j"
        config.password = "test-password"
        config.database = "neo4j"
        return config

    @pytest.fixture
    def graphiti_manager(self, mock_graphiti_config, mock_neo4j_config):
        """Create a GraphitiManager instance for testing."""
        return GraphitiManager(
            neo4j_config=mock_neo4j_config,
            graphiti_config=mock_graphiti_config,
            openai_api_key="test-openai-key",
        )

    @pytest.fixture
    def mock_graphiti_client(self):
        """Create a mock Graphiti client."""
        client = AsyncMock()
        client.search = AsyncMock()
        client.add_episode = AsyncMock()
        client.close = AsyncMock()
        client.build_indices_and_constraints = Mock()
        return client

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def mock_embedder(self):
        """Create a mock embedder."""
        embedder = AsyncMock()
        return embedder

    # Initialization Tests

    def test_graphiti_manager_initialization(
        self, mock_graphiti_config, mock_neo4j_config
    ):
        """Test GraphitiManager initialization."""
        manager = GraphitiManager(
            neo4j_config=mock_neo4j_config,
            graphiti_config=mock_graphiti_config,
            openai_api_key="test-key",
        )

        assert manager.neo4j_config == mock_neo4j_config
        assert manager.graphiti_config == mock_graphiti_config
        assert manager.openai_api_key == "test-key"
        assert manager._graphiti is None
        assert manager._llm_client is None
        assert manager._embedder is None
        assert not manager.is_initialized

    # Client Lifecycle Tests
    @pytest.mark.asyncio
    async def test_initialize_success(
        self, graphiti_manager, mock_graphiti_client, mock_llm_client, mock_embedder
    ):
        """Test successful initialization."""
        with (
            patch(
                "qdrant_loader.core.managers.graphiti_manager.Graphiti"
            ) as mock_graphiti_class,
            patch(
                "qdrant_loader.core.managers.graphiti_manager.OpenAIClient"
            ) as mock_openai_client,
            patch(
                "qdrant_loader.core.managers.graphiti_manager.OpenAIEmbedder"
            ) as mock_embedder_class,
            patch("asyncio.to_thread") as mock_to_thread,
        ):

            mock_graphiti_class.return_value = mock_graphiti_client
            mock_openai_client.return_value = mock_llm_client
            mock_embedder_class.return_value = mock_embedder
            mock_to_thread.return_value = None

            await graphiti_manager.initialize()

            assert graphiti_manager.is_initialized
            assert graphiti_manager._graphiti == mock_graphiti_client
            assert graphiti_manager._llm_client == mock_llm_client
            assert graphiti_manager._embedder == mock_embedder

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, graphiti_manager):
        """Test initialization when already initialized."""
        existing_client = Mock()
        graphiti_manager._graphiti = existing_client
        graphiti_manager._llm_client = Mock()
        graphiti_manager._embedder = Mock()
        graphiti_manager._initialized = True

        await graphiti_manager.initialize()

        # Should not change existing clients
        assert graphiti_manager._graphiti == existing_client
        assert graphiti_manager._llm_client is not None
        assert graphiti_manager._embedder is not None

    @pytest.mark.asyncio
    async def test_initialize_failure(self, graphiti_manager):
        """Test initialization failure."""
        with patch(
            "qdrant_loader.core.managers.graphiti_manager.OpenAIClient"
        ) as mock_openai_client:
            mock_openai_client.side_effect = Exception("Client initialization failed")

            with pytest.raises(Exception, match="Client initialization failed"):
                await graphiti_manager.initialize()

            assert not graphiti_manager.is_initialized

    @pytest.mark.asyncio
    async def test_close_success(self, graphiti_manager, mock_graphiti_client):
        """Test successful cleanup."""
        graphiti_manager._graphiti = mock_graphiti_client
        graphiti_manager._llm_client = Mock()
        graphiti_manager._embedder = Mock()
        graphiti_manager._initialized = True

        await graphiti_manager.close()

        mock_graphiti_client.close.assert_called_once()
        assert graphiti_manager._graphiti is None
        assert graphiti_manager._llm_client is None
        assert graphiti_manager._embedder is None
        assert not graphiti_manager.is_initialized

    @pytest.mark.asyncio
    async def test_close_not_initialized(self, graphiti_manager):
        """Test cleanup when not initialized."""
        await graphiti_manager.close()

        # Should not raise error
        assert not graphiti_manager.is_initialized

    @pytest.mark.asyncio
    async def test_close_with_error(self, graphiti_manager, mock_graphiti_client):
        """Test cleanup with error during close."""
        mock_graphiti_client.close.side_effect = Exception("Close failed")
        graphiti_manager._graphiti = mock_graphiti_client
        graphiti_manager._initialized = True

        # Should not raise exception
        await graphiti_manager.close()

        # Should still clean up references
        assert graphiti_manager._graphiti is None
        assert not graphiti_manager.is_initialized

    # Search Operations Tests

    @pytest.mark.asyncio
    async def test_search_success(self, graphiti_manager, mock_graphiti_client):
        """Test successful search operation."""
        graphiti_manager._graphiti = mock_graphiti_client
        graphiti_manager._llm_client = Mock()
        graphiti_manager._embedder = Mock()
        graphiti_manager._initialized = True

        mock_results = [
            {"uuid": "test-1", "name": "Test Entity 1", "score": 0.9},
            {"uuid": "test-2", "name": "Test Entity 2", "score": 0.8},
        ]
        mock_graphiti_client.search.return_value = mock_results

        results = await graphiti_manager.search("test query", limit=10)

        assert len(results) == 2
        assert results == mock_results
        mock_graphiti_client.search.assert_called_once_with(
            query="test query", num_results=10, center_node_uuid=None
        )

    @pytest.mark.asyncio
    async def test_search_with_center_node(
        self, graphiti_manager, mock_graphiti_client
    ):
        """Test search with center node."""
        graphiti_manager._graphiti = mock_graphiti_client
        graphiti_manager._llm_client = Mock()
        graphiti_manager._embedder = Mock()
        graphiti_manager._initialized = True

        mock_results = [{"uuid": "test-1", "name": "Test Entity"}]
        mock_graphiti_client.search.return_value = mock_results

        results = await graphiti_manager.search(
            "test query", limit=5, center_node_uuid="center-uuid"
        )

        assert len(results) == 1
        mock_graphiti_client.search.assert_called_once_with(
            query="test query", num_results=5, center_node_uuid="center-uuid"
        )

    @pytest.mark.asyncio
    async def test_search_limit_enforcement(
        self, graphiti_manager, mock_graphiti_client
    ):
        """Test search limit enforcement."""
        graphiti_manager._graphiti = mock_graphiti_client
        graphiti_manager._llm_client = Mock()
        graphiti_manager._embedder = Mock()
        graphiti_manager._initialized = True

        # Set max limit to 50
        graphiti_manager.graphiti_config.operational.search_limit_max = 50

        mock_graphiti_client.search.return_value = []

        await graphiti_manager.search("test query", limit=100)

        # Should be limited to max
        mock_graphiti_client.search.assert_called_once_with(
            query="test query", num_results=50, center_node_uuid=None
        )

    @pytest.mark.asyncio
    async def test_search_not_initialized(self, graphiti_manager):
        """Test search when not initialized."""
        with pytest.raises(RuntimeError, match="Graphiti client not initialized"):
            await graphiti_manager.search("test query")

    @pytest.mark.asyncio
    async def test_search_failure(self, graphiti_manager, mock_graphiti_client):
        """Test search failure handling."""
        graphiti_manager._graphiti = mock_graphiti_client
        graphiti_manager._llm_client = Mock()
        graphiti_manager._embedder = Mock()
        graphiti_manager._initialized = True

        mock_graphiti_client.search.side_effect = Exception("Search failed")

        with pytest.raises(Exception, match="Search failed"):
            await graphiti_manager.search("test query")

    # Node Retrieval Tests

    @pytest.mark.asyncio
    async def test_get_nodes_specific_uuids(
        self, graphiti_manager, mock_graphiti_client
    ):
        """Test retrieving specific nodes by UUID."""
        graphiti_manager._graphiti = mock_graphiti_client
        graphiti_manager._llm_client = Mock()
        graphiti_manager._embedder = Mock()
        graphiti_manager._initialized = True

        # Mock search results for specific UUIDs
        mock_graphiti_client.search.side_effect = [
            [{"uuid": "uuid-1", "name": "Node 1"}],
            [{"uuid": "uuid-2", "name": "Node 2"}],
        ]

        results = await graphiti_manager.get_nodes(["uuid-1", "uuid-2"])

        assert len(results) == 2
        assert mock_graphiti_client.search.call_count == 2

    @pytest.mark.asyncio
    async def test_get_nodes_general_search(
        self, graphiti_manager, mock_graphiti_client
    ):
        """Test general node retrieval."""
        graphiti_manager._graphiti = mock_graphiti_client
        graphiti_manager._llm_client = Mock()
        graphiti_manager._embedder = Mock()
        graphiti_manager._initialized = True

        mock_results = [
            {"uuid": "node-1", "name": "Node 1"},
            {"uuid": "node-2", "name": "Node 2"},
        ]
        mock_graphiti_client.search.return_value = mock_results

        results = await graphiti_manager.get_nodes(limit=50)

        assert len(results) == 2
        mock_graphiti_client.search.assert_called_once_with(query="*", num_results=50)

    @pytest.mark.asyncio
    async def test_get_nodes_not_initialized(self, graphiti_manager):
        """Test get_nodes when not initialized."""
        with pytest.raises(RuntimeError, match="Graphiti client not initialized"):
            await graphiti_manager.get_nodes()

    @pytest.mark.asyncio
    async def test_get_nodes_with_partial_failure(
        self, graphiti_manager, mock_graphiti_client
    ):
        """Test get_nodes with search failure for one UUID but success for others."""
        graphiti_manager._graphiti = mock_graphiti_client
        graphiti_manager._llm_client = Mock()
        graphiti_manager._embedder = Mock()
        graphiti_manager._initialized = True

        # First call fails, second succeeds - should continue with warning
        mock_graphiti_client.search.side_effect = [
            Exception("Search failed for uuid-1"),
            [{"uuid": "uuid-2", "name": "Node 2"}],
        ]

        results = await graphiti_manager.get_nodes(["uuid-1", "uuid-2"])

        # Should get one result despite one failure
        assert len(results) == 1
        assert results[0]["uuid"] == "uuid-2"
        assert mock_graphiti_client.search.call_count == 2

    @pytest.mark.asyncio
    async def test_get_nodes_general_failure(
        self, graphiti_manager, mock_graphiti_client
    ):
        """Test get_nodes with general search failure."""
        graphiti_manager._graphiti = mock_graphiti_client
        graphiti_manager._llm_client = Mock()
        graphiti_manager._embedder = Mock()
        graphiti_manager._initialized = True

        mock_graphiti_client.search.side_effect = Exception("General search failed")

        with pytest.raises(Exception, match="General search failed"):
            await graphiti_manager.get_nodes(limit=50)

    # Edge Retrieval Tests

    @pytest.mark.asyncio
    async def test_get_edges_specific_uuids(
        self, graphiti_manager, mock_graphiti_client
    ):
        """Test edge retrieval with specific UUIDs."""
        graphiti_manager._graphiti = mock_graphiti_client
        graphiti_manager._llm_client = Mock()
        graphiti_manager._embedder = Mock()
        graphiti_manager._initialized = True

        # Edge retrieval is limited by Graphiti API
        results = await graphiti_manager.get_edges(["edge-1", "edge-2"])

        assert len(results) == 0  # API limitation

    @pytest.mark.asyncio
    async def test_get_edges_general(self, graphiti_manager, mock_graphiti_client):
        """Test general edge retrieval."""
        graphiti_manager._graphiti = mock_graphiti_client
        graphiti_manager._llm_client = Mock()
        graphiti_manager._embedder = Mock()
        graphiti_manager._initialized = True

        # Edge retrieval is limited by Graphiti API
        results = await graphiti_manager.get_edges()

        assert len(results) == 0  # API limitation

    @pytest.mark.asyncio
    async def test_get_edges_not_initialized(self, graphiti_manager):
        """Test get_edges when not initialized."""
        with pytest.raises(RuntimeError, match="Graphiti client not initialized"):
            await graphiti_manager.get_edges()

    # Optimized Search Tests

    @pytest.mark.asyncio
    async def test_optimized_search_success(
        self, graphiti_manager, mock_graphiti_client
    ):
        """Test optimized search functionality."""
        graphiti_manager._graphiti = mock_graphiti_client
        graphiti_manager._llm_client = Mock()
        graphiti_manager._embedder = Mock()
        graphiti_manager._initialized = True

        mock_results = [{"uuid": "test-1", "name": "Test Entity"}]
        mock_graphiti_client.search.return_value = mock_results

        results = await graphiti_manager.optimized_search(
            "test query", limit=10, center_node_uuid="center-uuid", use_cache=True
        )

        assert len(results) == 1
        assert results == mock_results
        mock_graphiti_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_optimized_search_not_initialized(self, graphiti_manager):
        """Test optimized search when not initialized."""
        with pytest.raises(RuntimeError, match="Graphiti client not initialized"):
            await graphiti_manager.optimized_search("test query")

    @pytest.mark.asyncio
    async def test_optimized_search_with_failure(
        self, graphiti_manager, mock_graphiti_client
    ):
        """Test optimized search with failure."""
        graphiti_manager._graphiti = mock_graphiti_client
        graphiti_manager._llm_client = Mock()
        graphiti_manager._embedder = Mock()
        graphiti_manager._initialized = True

        mock_graphiti_client.search.side_effect = Exception("Search failed")

        with pytest.raises(Exception, match="Search failed"):
            await graphiti_manager.optimized_search("test query")

    # Performance Statistics Tests

    @pytest.mark.asyncio
    async def test_get_search_performance_stats_success(
        self, graphiti_manager, mock_graphiti_client
    ):
        """Test getting search performance statistics."""
        graphiti_manager._graphiti = mock_graphiti_client
        graphiti_manager._llm_client = Mock()
        graphiti_manager._embedder = Mock()
        graphiti_manager._initialized = True

        mock_graphiti_client.search.return_value = [{"uuid": "test"}]

        stats = await graphiti_manager.get_search_performance_stats()

        assert "test_search" in stats
        assert "configuration" in stats
        assert "client_status" in stats
        assert stats["test_search"]["status"] == "success"
        assert stats["client_status"]["initialized"] is True

    @pytest.mark.asyncio
    async def test_get_search_performance_stats_not_initialized(self, graphiti_manager):
        """Test performance stats when not initialized."""
        stats = await graphiti_manager.get_search_performance_stats()

        assert "error" in stats
        assert stats["error"] == "Graphiti client not initialized"

    @pytest.mark.asyncio
    async def test_get_search_performance_stats_with_failure(
        self, graphiti_manager, mock_graphiti_client
    ):
        """Test performance stats with search failure."""
        graphiti_manager._graphiti = mock_graphiti_client
        graphiti_manager._llm_client = Mock()
        graphiti_manager._embedder = Mock()
        graphiti_manager._initialized = True

        mock_graphiti_client.search.side_effect = Exception("Test search failed")

        stats = await graphiti_manager.get_search_performance_stats()

        assert "error" in stats
        assert "Test search failed" in stats["error"]

    # Query Optimization Tests

    def test_get_query_optimization_recommendations_short_query(self, graphiti_manager):
        """Test recommendations for short queries."""
        recommendations = graphiti_manager.get_query_optimization_recommendations("hi")

        assert any("very short" in rec for rec in recommendations)

    def test_get_query_optimization_recommendations_long_query(self, graphiti_manager):
        """Test recommendations for long queries."""
        long_query = "a" * 250
        recommendations = graphiti_manager.get_query_optimization_recommendations(
            long_query
        )

        assert any("very long" in rec for rec in recommendations)

    def test_get_query_optimization_recommendations_find_prefix(self, graphiti_manager):
        """Test recommendations for queries with 'find' prefix."""
        recommendations = graphiti_manager.get_query_optimization_recommendations(
            "find something"
        )

        assert any("Remove 'find' prefix" in rec for rec in recommendations)

    def test_get_query_optimization_recommendations_question_mark(
        self, graphiti_manager
    ):
        """Test recommendations for queries with question marks."""
        recommendations = graphiti_manager.get_query_optimization_recommendations(
            "what is this?"
        )

        assert any("Remove question marks" in rec for rec in recommendations)

    def test_get_query_optimization_recommendations_entity_types(
        self, graphiti_manager
    ):
        """Test recommendations for queries mentioning entity types."""
        recommendations = graphiti_manager.get_query_optimization_recommendations(
            "find a person named John"
        )

        assert any("entity type filters" in rec for rec in recommendations)

    def test_get_query_optimization_recommendations_temporal_terms(
        self, graphiti_manager
    ):
        """Test recommendations for queries with temporal terms."""
        recommendations = graphiti_manager.get_query_optimization_recommendations(
            "recent events"
        )

        assert any("temporal search parameters" in rec for rec in recommendations)

    def test_get_query_optimization_recommendations_general(self, graphiti_manager):
        """Test general recommendations are always included."""
        recommendations = graphiti_manager.get_query_optimization_recommendations(
            "normal query"
        )

        assert any("specific nouns" in rec for rec in recommendations)
        assert any("breaking complex queries" in rec for rec in recommendations)
        assert any("center_node_uuid" in rec for rec in recommendations)

    # Context Manager Tests

    @pytest.mark.asyncio
    async def test_context_manager_success(
        self, mock_graphiti_config, mock_neo4j_config
    ):
        """Test GraphitiManager as async context manager."""
        with (
            patch(
                "qdrant_loader.core.managers.graphiti_manager.Graphiti"
            ) as mock_graphiti_class,
            patch(
                "qdrant_loader.core.managers.graphiti_manager.OpenAIClient"
            ) as mock_openai_client,
            patch(
                "qdrant_loader.core.managers.graphiti_manager.OpenAIEmbedder"
            ) as mock_embedder_class,
            patch("asyncio.to_thread") as mock_to_thread,
        ):
            mock_client = AsyncMock()
            mock_graphiti_class.return_value = mock_client
            mock_openai_client.return_value = AsyncMock()
            mock_embedder_class.return_value = AsyncMock()
            mock_to_thread.return_value = None

            async with GraphitiManager(
                neo4j_config=mock_neo4j_config,
                graphiti_config=mock_graphiti_config,
                openai_api_key="test-key",
            ) as manager:
                assert manager.is_initialized
                assert manager._graphiti is not None

            # Should be cleaned up after context
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_with_exception(
        self, mock_graphiti_config, mock_neo4j_config
    ):
        """Test context manager cleanup with exception."""
        with (
            patch(
                "qdrant_loader.core.managers.graphiti_manager.Graphiti"
            ) as mock_graphiti_class,
            patch(
                "qdrant_loader.core.managers.graphiti_manager.OpenAIClient"
            ) as mock_openai_client,
            patch(
                "qdrant_loader.core.managers.graphiti_manager.OpenAIEmbedder"
            ) as mock_embedder_class,
            patch("asyncio.to_thread") as mock_to_thread,
        ):
            mock_client = AsyncMock()
            mock_graphiti_class.return_value = mock_client
            mock_openai_client.return_value = AsyncMock()
            mock_embedder_class.return_value = AsyncMock()
            mock_to_thread.return_value = None

            try:
                async with GraphitiManager(
                    neo4j_config=mock_neo4j_config,
                    graphiti_config=mock_graphiti_config,
                    openai_api_key="test-key",
                ) as manager:
                    assert manager.is_initialized
                    raise ValueError("Test exception")
            except ValueError:
                pass

            # Should still be cleaned up
            mock_client.close.assert_called_once()

    # Property Tests

    def test_is_initialized_property(self, graphiti_manager):
        """Test is_initialized property."""
        assert not graphiti_manager.is_initialized

        graphiti_manager._graphiti = Mock()
        graphiti_manager._llm_client = Mock()
        graphiti_manager._embedder = Mock()
        graphiti_manager._initialized = True

        assert graphiti_manager.is_initialized

        graphiti_manager._graphiti = None
        assert not graphiti_manager.is_initialized

    # Integration Tests

    @pytest.mark.asyncio
    async def test_full_workflow(self, mock_graphiti_config, mock_neo4j_config):
        """Test a complete workflow from initialization to cleanup."""
        with (
            patch(
                "qdrant_loader.core.managers.graphiti_manager.Graphiti"
            ) as mock_graphiti_class,
            patch(
                "qdrant_loader.core.managers.graphiti_manager.OpenAIClient"
            ) as mock_openai_client,
            patch(
                "qdrant_loader.core.managers.graphiti_manager.OpenAIEmbedder"
            ) as mock_embedder_class,
            patch("asyncio.to_thread") as mock_to_thread,
        ):

            mock_client = AsyncMock()
            mock_client.search.return_value = [{"uuid": "test", "name": "Test Entity"}]
            mock_graphiti_class.return_value = mock_client
            mock_openai_client.return_value = AsyncMock()
            mock_embedder_class.return_value = AsyncMock()
            mock_to_thread.return_value = None

            manager = GraphitiManager(
                neo4j_config=mock_neo4j_config,
                graphiti_config=mock_graphiti_config,
                openai_api_key="test-key",
            )

            # Initialize
            await manager.initialize()
            assert manager.is_initialized

            # Perform operations
            search_results = await manager.search("test query")
            assert len(search_results) == 1

            nodes = await manager.get_nodes()
            assert len(nodes) == 1

            stats = await manager.get_search_performance_stats()
            assert "test_search" in stats

            recommendations = manager.get_query_optimization_recommendations(
                "test query"
            )
            assert len(recommendations) > 0

            # Cleanup
            await manager.close()
            assert not manager.is_initialized
            mock_client.close.assert_called_once()
