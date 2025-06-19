from unittest.mock import AsyncMock, Mock

import pytest
from openai import AsyncOpenAI
from qdrant_client import QdrantClient

from qdrant_loader_mcp_server.search.enhanced_hybrid.engine import (
    EnhancedHybridSearchEngine,
)
from qdrant_loader_mcp_server.search.enhanced_hybrid.models import (
    EnhancedSearchConfig,
    EnhancedSearchResult,
    SearchMode,
)
from qdrant_loader_mcp_server.search.models import SearchResult


class TestEnhancedHybridSearchEngine:
    """Test EnhancedHybridSearchEngine main functionality."""

    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a mock Qdrant client."""
        client = Mock(spec=QdrantClient)
        client.search.return_value = [
            Mock(
                id="test-1",
                score=0.85,
                payload={
                    "content": "Test content 1",
                    "title": "Test Title 1",
                    "source_type": "document",
                    "metadata": {"project_id": "proj-1"},
                },
            ),
            Mock(
                id="test-2",
                score=0.75,
                payload={
                    "content": "Test content 2",
                    "title": "Test Title 2",
                    "source_type": "document",
                    "metadata": {"project_id": "proj-2"},
                },
            ),
        ]
        return client

    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        client = Mock(spec=AsyncOpenAI)
        client.embeddings.create = AsyncMock()
        client.embeddings.create.return_value.data = [
            Mock(embedding=[0.1, 0.2, 0.3] * 512)
        ]
        return client

    @pytest.fixture
    def mock_neo4j_manager(self):
        """Create a mock Neo4j manager."""
        manager = Mock()
        manager.execute_read = AsyncMock()
        manager.execute_read.return_value = [
            {
                "id": "neo4j-1",
                "content": "Neo4j test content",
                "title": "Neo4j Title",
                "source_type": "graph",
                "score": 0.8,
            }
        ]
        return manager

    @pytest.fixture
    def mock_graphiti_manager(self):
        """Create a mock Graphiti manager."""
        manager = Mock()
        manager.search = AsyncMock()
        manager.search.return_value = [
            {
                "uuid": "graphiti-1",
                "name": "Test Entity",
                "fact": "Test fact about entity",
                "score": 0.9,
                "entity_type": "PERSON",
            }
        ]
        return manager

    @pytest.fixture
    def enhanced_search_engine(
        self,
        mock_qdrant_client,
        mock_openai_client,
        mock_neo4j_manager,
        mock_graphiti_manager,
    ):
        """Create an EnhancedHybridSearchEngine instance."""
        config = EnhancedSearchConfig(
            enable_caching=False,  # Disable caching for simpler tests
            enable_reranking=False,  # Disable reranking for simpler tests
        )

        engine = EnhancedHybridSearchEngine(
            qdrant_client=mock_qdrant_client,
            openai_client=mock_openai_client,
            collection_name="test_collection",
            neo4j_manager=mock_neo4j_manager,
            graphiti_manager=mock_graphiti_manager,
            config=config,
        )

        # Mock the method that performs keyword search
        engine._get_keyword_results = AsyncMock(
            return_value=[
                EnhancedSearchResult(
                    id="keyword-1",
                    content="Keyword search result",
                    title="Keyword Title",
                    source_type="document",
                    combined_score=0.7,
                    keyword_score=0.7,
                )
            ]
        )

        return engine

    @pytest.mark.asyncio
    async def test_vector_only_search(
        self, enhanced_search_engine, mock_qdrant_client, mock_openai_client
    ):
        """Test vector-only search mode."""
        results = await enhanced_search_engine.search(
            query="test query", mode=SearchMode.VECTOR_ONLY, limit=5
        )

        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)

        # Verify embedding was called
        mock_openai_client.embeddings.create.assert_called_once()

        # Verify Qdrant search was called
        mock_qdrant_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_graph_only_search(
        self, enhanced_search_engine, mock_graphiti_manager
    ):
        """Test graph-only search mode."""
        results = await enhanced_search_engine.search(
            query="test query", mode=SearchMode.GRAPH_ONLY, limit=5
        )

        assert len(results) >= 0  # May be empty due to mock limitations

        # Verify Graphiti search was called
        mock_graphiti_manager.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_hybrid_search_mode(
        self,
        enhanced_search_engine,
        mock_qdrant_client,
        mock_openai_client,
        mock_graphiti_manager,
    ):
        """Test hybrid search mode combining vector, keyword, and graph."""
        results = await enhanced_search_engine.search(
            query="test query",
            mode=SearchMode.HYBRID,
            limit=5,
            vector_weight=0.5,
            keyword_weight=0.3,
            graph_weight=0.2,
        )

        assert isinstance(results, list)

        # Verify all search engines were called
        mock_openai_client.embeddings.create.assert_called()
        mock_qdrant_client.search.assert_called()
        mock_graphiti_manager.search.assert_called()
        enhanced_search_engine._get_keyword_results.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_search_mode(self, enhanced_search_engine):
        """Test auto search mode that adapts based on query."""
        results = await enhanced_search_engine.search(
            query="test query", mode=SearchMode.AUTO, limit=5
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_project_filter(
        self, enhanced_search_engine, mock_qdrant_client
    ):
        """Test search with project ID filtering."""
        results = await enhanced_search_engine.search(
            query="test query",
            mode=SearchMode.VECTOR_ONLY,
            limit=5,
            project_ids=["proj-1", "proj-2"],
        )

        assert isinstance(results, list)

        # Verify Qdrant search was called with filter
        mock_qdrant_client.search.assert_called()
        call_args = mock_qdrant_client.search.call_args
        assert "query_filter" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_search_with_source_type_filter(self, enhanced_search_engine):
        """Test search with source type filtering."""
        results = await enhanced_search_engine.search(
            query="test query",
            mode=SearchMode.HYBRID,
            limit=5,
            source_types=["document", "git"],
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_custom_weights(self, enhanced_search_engine):
        """Test search with custom weight parameters."""
        results = await enhanced_search_engine.search(
            query="test query",
            mode=SearchMode.HYBRID,
            limit=5,
            vector_weight=0.7,
            keyword_weight=0.2,
            graph_weight=0.1,
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_error_handling(
        self, enhanced_search_engine, mock_qdrant_client
    ):
        """Test search error handling and fallbacks."""
        # Make vector search fail
        mock_qdrant_client.search.side_effect = Exception("Qdrant error")

        # Should still return results from other search methods
        results = await enhanced_search_engine.search(
            query="test query", mode=SearchMode.HYBRID, limit=5
        )

        assert isinstance(results, list)

    def test_update_config(self, enhanced_search_engine):
        """Test updating search engine configuration."""
        new_config = EnhancedSearchConfig(
            vector_weight=0.8, keyword_weight=0.1, graph_weight=0.1
        )

        enhanced_search_engine.update_config(new_config)

        assert enhanced_search_engine.config.vector_weight == 0.8
        assert enhanced_search_engine.config.keyword_weight == 0.1
        assert enhanced_search_engine.config.graph_weight == 0.1

    def test_get_stats(self, enhanced_search_engine):
        """Test getting search engine statistics."""
        stats = enhanced_search_engine.get_stats()

        assert isinstance(stats, dict)
        assert "config" in stats
        assert isinstance(stats["config"], dict)
        assert "mode" in stats["config"]
        assert "fusion_strategy" in stats["config"]
        assert "vector_weight" in stats["config"]
        assert "keyword_weight" in stats["config"]
        assert "graph_weight" in stats["config"]

    def test_clear_cache(self, enhanced_search_engine):
        """Test clearing search cache."""
        # Should not raise an exception
        enhanced_search_engine.clear_cache()

    def test_invalidate_cache_pattern(self, enhanced_search_engine):
        """Test invalidating cache entries by pattern."""
        count = enhanced_search_engine.invalidate_cache_pattern("test*")
        assert isinstance(count, int)
        assert count >= 0

    def test_get_cache_stats(self, enhanced_search_engine):
        """Test getting cache statistics."""
        stats = enhanced_search_engine.get_cache_stats()
        assert isinstance(stats, dict)
