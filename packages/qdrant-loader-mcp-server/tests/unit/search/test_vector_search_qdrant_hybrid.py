from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from qdrant_client.http import models

from qdrant_loader_mcp_server.search.components.vector_search_service import (
    VectorSearchService,
)


class _EmbeddingsClient:
    async def embed(self, inputs):  # type: ignore[no-untyped-def]
        return [[0.2, 0.3, 0.4] for _ in inputs]


class _Provider:
    def embeddings(self):
        return _EmbeddingsClient()


@pytest.mark.asyncio
async def test_vector_search_uses_qdrant_hybrid_fusion_when_sparse_available():
    qdrant_client = MagicMock()
    qdrant_client.get_collection = AsyncMock(
        return_value=SimpleNamespace(
            config=SimpleNamespace(
                params=SimpleNamespace(
                    vectors={"dense": {"size": 3}}, sparse_vectors={"sparse": {}}
                )
            )
        )
    )
    hit = MagicMock()
    hit.score = 0.9
    hit.payload = {
        "content": "Test content",
        "metadata": {},
        "source_type": "git",
    }
    qdrant_client.query_points = AsyncMock(
        return_value=SimpleNamespace(points=[hit])
    )

    svc = VectorSearchService(
        qdrant_client=qdrant_client,
        collection_name="test_collection",
        embeddings_provider=_Provider(),
    )

    out = await svc.vector_search("test query", 5)

    assert len(out) == 1
    assert svc.used_qdrant_hybrid_last_query() is True

    query_call = qdrant_client.query_points.call_args
    assert isinstance(query_call.kwargs.get("query"), models.FusionQuery)
    prefetch = query_call.kwargs.get("prefetch")
    assert isinstance(prefetch, list)
    assert len(prefetch) == 2
