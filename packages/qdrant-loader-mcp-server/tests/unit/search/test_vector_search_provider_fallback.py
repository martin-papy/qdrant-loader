from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from qdrant_loader_mcp_server.search.components.vector_search_service import (
    VectorSearchService,
)


@pytest.fixture
def mock_qdrant_client():
    client = MagicMock()
    client.search = AsyncMock()
    return client


class _EmbeddingsClient:
    def __init__(self, vector):
        self._vector = vector

    async def embed(self, inputs):  # type: ignore[no-untyped-def]
        # Return the same vector per input
        return [self._vector for _ in inputs]


class _Provider:
    def __init__(self, vector):
        self._vector = vector

    def embeddings(self):
        return _EmbeddingsClient(self._vector)


@pytest.mark.asyncio
async def test_get_embedding_uses_provider_first(mock_qdrant_client):
    provider = _Provider([0.9, 0.8, 0.7])
    openai_client = MagicMock()
    openai_client.embeddings = MagicMock()
    openai_client.embeddings.create = AsyncMock()

    svc = VectorSearchService(
        qdrant_client=mock_qdrant_client,
        collection_name="test_collection",
        embeddings_provider=provider,
        openai_client=openai_client,
    )

    vec = await svc.get_embedding("hello")
    assert vec == [0.9, 0.8, 0.7]
    # Ensure OpenAI fallback was not used
    openai_client.embeddings.create.assert_not_called()


@pytest.mark.asyncio
async def test_get_embedding_falls_back_to_openai_when_no_provider(mock_qdrant_client):
    # Mock OpenAI response shape: response.data[0].embedding
    embedding_item = SimpleNamespace(embedding=[0.1, 0.2, 0.3])
    response = SimpleNamespace(data=[embedding_item])

    openai_client = MagicMock()
    openai_client.embeddings = MagicMock()
    openai_client.embeddings.create = AsyncMock(return_value=response)

    svc = VectorSearchService(
        qdrant_client=mock_qdrant_client,
        collection_name="test_collection",
        embeddings_provider=None,
        openai_client=openai_client,
    )

    vec = await svc.get_embedding("hello")
    assert vec == [0.1, 0.2, 0.3]
    openai_client.embeddings.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_embedding_raises_when_no_provider_and_no_openai(mock_qdrant_client):
    svc = VectorSearchService(
        qdrant_client=mock_qdrant_client,
        collection_name="test_collection",
        embeddings_provider=None,
        openai_client=None,
    )

    with pytest.raises(RuntimeError):
        await svc.get_embedding("hello")


