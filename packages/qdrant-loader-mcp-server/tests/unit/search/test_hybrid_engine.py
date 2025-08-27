"""Unit tests for HybridSearchEngine."""

from unittest.mock import AsyncMock, Mock

import pytest
from qdrant_client import QdrantClient
from qdrant_loader_mcp_server.search.enhanced.knowledge_graph import (
    DocumentKnowledgeGraph,
)
from qdrant_loader_mcp_server.search.hybrid.engine import HybridSearchEngine


class TestHybridSearchEngine:
    """Test the extracted HybridSearchEngine class."""

    def test_engine_imports_correctly(self):
        """Test that HybridSearchEngine can be imported from the engine module."""
        assert HybridSearchEngine is not None
        assert HybridSearchEngine.__name__ == "HybridSearchEngine"

    @pytest.fixture
    def mock_clients(self):
        """Create mock clients for testing."""
        qdrant_client = Mock(spec=QdrantClient)
        openai_client = Mock()
        return qdrant_client, openai_client

    def test_engine_initialization(self, mock_clients):
        """Test that HybridSearchEngine initializes correctly."""
        qdrant_client, openai_client = mock_clients

        engine = HybridSearchEngine(
            qdrant_client=qdrant_client,
            openai_client=openai_client,
            collection_name="test_collection",
        )

        assert engine is not None
        assert engine.qdrant_client == qdrant_client
        assert engine.openai_client == openai_client
        assert engine.collection_name == "test_collection"
        assert engine.vector_weight == 0.6  # DEFAULT_VECTOR_WEIGHT
        assert engine.keyword_weight == 0.3  # DEFAULT_KEYWORD_WEIGHT

    def test_engine_with_custom_weights(self, mock_clients):
        """Test engine initialization with custom weights."""
        qdrant_client, openai_client = mock_clients

        engine = HybridSearchEngine(
            qdrant_client=qdrant_client,
            openai_client=openai_client,
            collection_name="test_collection",
            vector_weight=0.7,
            keyword_weight=0.3,
            min_score=0.1,
        )

        assert engine.vector_weight == 0.7
        assert engine.keyword_weight == 0.3
        assert engine.min_score == 0.1

    def test_engine_with_knowledge_graph(self, mock_clients):
        """Test engine initialization with knowledge graph."""
        qdrant_client, openai_client = mock_clients
        mock_kg = Mock(spec=DocumentKnowledgeGraph)

        engine = HybridSearchEngine(
            qdrant_client=qdrant_client,
            openai_client=openai_client,
            collection_name="test_collection",
            knowledge_graph=mock_kg,
            enable_intent_adaptation=True,
        )

        assert engine.knowledge_graph == mock_kg
        assert engine.enable_intent_adaptation is True
        assert engine.intent_classifier is not None
        assert engine.adaptive_strategy is not None

    def test_engine_without_intent_adaptation(self, mock_clients):
        """Test engine initialization without intent adaptation."""
        qdrant_client, openai_client = mock_clients

        engine = HybridSearchEngine(
            qdrant_client=qdrant_client,
            openai_client=openai_client,
            collection_name="test_collection",
            enable_intent_adaptation=False,
        )

        assert engine.enable_intent_adaptation is False
        assert engine.intent_classifier is None
        assert engine.adaptive_strategy is None

    def test_engine_has_required_components(self, mock_clients):
        """Test that engine initializes all required components."""
        qdrant_client, openai_client = mock_clients

        engine = HybridSearchEngine(
            qdrant_client=qdrant_client,
            openai_client=openai_client,
            collection_name="test_collection",
        )

        # Core components
        assert engine.spacy_analyzer is not None
        assert engine.query_processor is not None
        assert engine.vector_search_service is not None
        assert engine.keyword_search_service is not None
        assert engine.result_combiner is not None
        assert engine.metadata_extractor is not None

        # Enhanced components
        assert engine.topic_chain_generator is not None
        assert engine.faceted_search_engine is not None
        assert engine.cross_document_engine is not None

    @pytest.mark.asyncio
    async def test_engine_search_method_exists(self, mock_clients):
        """Test that the search method exists and has the correct signature."""
        qdrant_client, openai_client = mock_clients

        engine = HybridSearchEngine(
            qdrant_client=qdrant_client,
            openai_client=openai_client,
            collection_name="test_collection",
        )

        # Verify search method exists
        assert hasattr(engine, "search")
        assert callable(engine.search)

        # Mock dependencies to avoid actual search execution
        engine._expand_query = AsyncMock(return_value="expanded query")
        engine._analyze_query = Mock(return_value={"analyzed": True})
        engine.hybrid_pipeline = Mock()
        engine.hybrid_pipeline.run = AsyncMock(return_value=[])

        # Test that search method can be called
        result = await engine.search("test query", limit=5)
        assert isinstance(result, list)

    def test_engine_utility_methods_exist(self, mock_clients):
        """Test that utility methods exist."""
        qdrant_client, openai_client = mock_clients

        engine = HybridSearchEngine(
            qdrant_client=qdrant_client,
            openai_client=openai_client,
            collection_name="test_collection",
        )

        # Test utility methods exist
        assert hasattr(engine, "get_adaptive_search_stats")
        assert callable(engine.get_adaptive_search_stats)

        stats = engine.get_adaptive_search_stats()
        assert isinstance(stats, dict)
        assert "intent_adaptation_enabled" in stats
        assert "has_knowledge_graph" in stats
