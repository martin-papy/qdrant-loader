from unittest.mock import AsyncMock, Mock

import pytest
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_loader_mcp_server.search.enhanced_hybrid.vector_search import (
    VectorSearchModule,
)


class TestVectorSearchModule:
    """Test VectorSearchModule functionality."""

    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a mock Qdrant client."""
        client = Mock(spec=QdrantClient)
        return client

    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        client = Mock(spec=AsyncOpenAI)
        return client

    @pytest.fixture
    def vector_search_module(self, mock_qdrant_client, mock_openai_client):
        """Create a VectorSearchModule instance."""
        return VectorSearchModule(
            qdrant_client=mock_qdrant_client,
            openai_client=mock_openai_client,
            collection_name="test_collection",
        )

    @pytest.mark.asyncio
    async def test_vector_search_basic(
        self, vector_search_module, mock_qdrant_client, mock_openai_client
    ):
        """Test basic vector search functionality."""
        # Mock embedding response
        mock_openai_client.embeddings.create = AsyncMock()
        mock_openai_client.embeddings.create.return_value.data = [
            Mock(embedding=[0.1, 0.2, 0.3])
        ]

        # Mock Qdrant search response
        mock_qdrant_client.search.return_value = [
            Mock(
                id="test-1",
                score=0.85,
                payload={
                    "content": "Test content",
                    "title": "Test Title",
                    "source_type": "document",
                    "metadata": {"project_id": "proj-1"},
                },
            )
        ]

        results = await vector_search_module.search(
            query="test query", limit=5, min_score=0.3
        )

        assert len(results) == 1
        assert results[0].id == "test-1"
        assert results[0].vector_score == 0.85
        assert results[0].content == "Test content"

        # Verify API calls
        mock_openai_client.embeddings.create.assert_called_once()
        mock_qdrant_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_vector_search_with_filters(
        self, vector_search_module, mock_qdrant_client, mock_openai_client
    ):
        """Test vector search with project ID filters."""
        # Mock embedding response
        mock_openai_client.embeddings.create = AsyncMock()
        mock_openai_client.embeddings.create.return_value.data = [
            Mock(embedding=[0.1, 0.2, 0.3])
        ]

        # Mock Qdrant search response
        mock_qdrant_client.search.return_value = []

        await vector_search_module.search(
            query="test query", limit=5, project_ids=["proj-1", "proj-2"]
        )

        # Verify that search was called with filter
        call_args = mock_qdrant_client.search.call_args
        assert call_args[1]["query_filter"] is not None

    @pytest.mark.asyncio
    async def test_vector_search_embedding_error(
        self, vector_search_module, mock_openai_client
    ):
        """Test vector search with embedding error."""
        # Mock embedding to raise an exception
        mock_openai_client.embeddings.create = AsyncMock()
        mock_openai_client.embeddings.create.side_effect = Exception("API Error")

        with pytest.raises(Exception):
            await vector_search_module.search(query="test query", limit=5)
