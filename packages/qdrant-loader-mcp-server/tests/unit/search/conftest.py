import pytest

from qdrant_loader_mcp_server.search.hybrid.engine import HybridSearchEngine


@pytest.fixture
def hybrid_search(mock_qdrant_client, mock_openai_client):
    """HybridSearchEngine instance using shared mocks from package conftest."""
    return HybridSearchEngine(
        qdrant_client=mock_qdrant_client,
        openai_client=mock_openai_client,
        collection_name="test_collection",
    )


