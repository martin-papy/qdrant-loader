from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_error_handling(hybrid_search, mock_qdrant_client):
    mock_qdrant_client.search = AsyncMock(side_effect=Exception("Test error"))
    with pytest.raises(Exception) as excinfo:
        await hybrid_search.search("test query")
    assert "Test error" in str(excinfo.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_embedding_error_handling(hybrid_search, mock_openai_client):
    mock_openai_client.embeddings.create = AsyncMock(side_effect=Exception("API Error"))
    with pytest.raises(Exception, match="API Error"):
        await hybrid_search._get_embedding("test text")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_topic_chain_generation_error_handling(hybrid_search):
    hybrid_search.topic_chain_generator.generate_search_chain = AsyncMock(
        side_effect=Exception("Topic chain generation failed")
    )
    with pytest.raises(Exception, match="Topic chain generation failed"):
        await hybrid_search.generate_topic_search_chain("test query")
