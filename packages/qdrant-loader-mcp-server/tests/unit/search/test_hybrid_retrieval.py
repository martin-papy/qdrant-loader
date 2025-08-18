from unittest.mock import AsyncMock

import pytest
from qdrant_loader_mcp_server.search.components.search_result_models import (
    HybridSearchResult,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_basic(hybrid_search):
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    hybrid_search._expand_query = AsyncMock(return_value="test query")

    results = await hybrid_search.search("test query")

    assert len(results) > 0
    assert isinstance(results[0], HybridSearchResult)
    assert results[0].score > 0
    assert results[0].text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_with_source_type_filter(hybrid_search):
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    hybrid_search._expand_query = AsyncMock(return_value="test query")

    results = await hybrid_search.search("test query", source_types=["git"]) 
    assert results and all(r.source_type == "git" for r in results)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_empty_results(hybrid_search, mock_qdrant_client):
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    hybrid_search._expand_query = AsyncMock(return_value="test query")
    hybrid_search._vector_search = AsyncMock(return_value=[])
    hybrid_search._keyword_search = AsyncMock(return_value=[])

    mock_qdrant_client.search.return_value = []
    mock_qdrant_client.scroll.return_value = ([], None)

    results = await hybrid_search.search("test query")
    assert results == []


