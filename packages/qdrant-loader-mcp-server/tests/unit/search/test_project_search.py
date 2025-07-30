"""
Tests for project-aware search functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_loader_mcp_server.search.engine import SearchEngine
from qdrant_loader_mcp_server.search.hybrid_search import (
    HybridSearchEngine,
)
from qdrant_loader_mcp_server.search.models import SearchResult


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client."""
    client = AsyncMock(spec=QdrantClient)

    # Mock search results with project information using MagicMock
    mock_points = []
    for i, (project_id, project_name, source_type) in enumerate(
        [
            ("project-a", "Project A", "git"),
            ("project-b", "Project B", "confluence"),
            ("project-a", "Project A", "git"),
        ],
        1,
    ):
        mock_point = MagicMock()
        mock_point.id = str(i)
        mock_point.score = 1.0 - (i * 0.1)
        mock_point.payload = {
            "content": f"Test content from {project_name}",
            "metadata": {
                "title": f"Test Document {project_name}",
                "project_id": project_id,
                "project_name": project_name,
                "project_description": f"Description for {project_name}",
                "collection_name": f"{project_id.replace('-', '_')}_collection",
            },
            "source_type": source_type,
            "project_id": project_id,
        }
        mock_point.vector = None
        mock_points.append(mock_point)

    # Set up async mock methods
    client.search = AsyncMock(return_value=mock_points)
    client.scroll = AsyncMock(return_value=(mock_points, None))
    
    # Mock collection operations for SearchEngine initialization
    collections_response = MagicMock()
    collections_response.collections = []
    client.get_collections = AsyncMock(return_value=collections_response)
    client.create_collection = AsyncMock(return_value=None)
    client.close = AsyncMock(return_value=None)

    return client


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    client = AsyncMock(spec=AsyncOpenAI)

    # Mock embedding response
    mock_response = MagicMock()
    mock_response.data = [MagicMock()]
    mock_response.data[0].embedding = [0.1, 0.2, 0.3] * 512  # 1536 dimensions
    client.embeddings.create = AsyncMock(return_value=mock_response)

    return client


@pytest.fixture
def hybrid_search(mock_qdrant_client, mock_openai_client):
    """Create a HybridSearchEngine instance with mocked dependencies."""
    return HybridSearchEngine(
        qdrant_client=mock_qdrant_client,
        openai_client=mock_openai_client,
        collection_name="test_collection",
    )


@pytest.fixture
def search_engine(mock_qdrant_client, mock_openai_client):
    """Create a SearchEngine instance with mocked dependencies."""
    engine = SearchEngine()
    engine.client = mock_qdrant_client
    engine.openai_client = mock_openai_client
    engine.hybrid_search = HybridSearchEngine(
        qdrant_client=mock_qdrant_client,
        openai_client=mock_openai_client,
        collection_name="test_collection",
    )
    return engine


@pytest.mark.asyncio
async def test_hybrid_search_with_project_filter(hybrid_search, mock_qdrant_client):
    """Test hybrid search with project filtering."""
    # Mock the _get_embedding method to avoid async issues
    with patch.object(
        hybrid_search, "_get_embedding", new_callable=AsyncMock
    ) as mock_embedding:
        mock_embedding.return_value = [0.1, 0.2, 0.3] * 512

        # Test search with specific project filter
        results = await hybrid_search.search(
            query="test query", limit=5, project_ids=["project-a"]
        )

        # Verify filter was applied in search call
        mock_qdrant_client.search.assert_called()
        search_call_args = mock_qdrant_client.search.call_args
        assert search_call_args[1]["query_filter"] is not None

        # Verify results contain project information
        assert len(results) > 0
        for result in results:
            assert isinstance(result, SearchResult)
            assert result.project_id is not None
            assert result.project_name is not None


@pytest.mark.asyncio
async def test_hybrid_search_without_project_filter(hybrid_search, mock_qdrant_client):
    """Test hybrid search without project filtering."""
    # Mock the _get_embedding method to avoid async issues
    with patch.object(
        hybrid_search, "_get_embedding", new_callable=AsyncMock
    ) as mock_embedding:
        mock_embedding.return_value = [0.1, 0.2, 0.3] * 512

        # Test search without project filter
        results = await hybrid_search.search(query="test query", limit=5)

        # Verify no filter was applied
        mock_qdrant_client.search.assert_called()
        search_call_args = mock_qdrant_client.search.call_args
        assert search_call_args[1]["query_filter"] is None

        # Verify results still contain project information from metadata
        assert len(results) > 0


@pytest.mark.asyncio
async def test_hybrid_search_multiple_projects(hybrid_search, mock_qdrant_client):
    """Test hybrid search with multiple project IDs."""
    # Mock the _get_embedding method to avoid async issues
    with patch.object(
        hybrid_search, "_get_embedding", new_callable=AsyncMock
    ) as mock_embedding:
        mock_embedding.return_value = [0.1, 0.2, 0.3] * 512

        # Test search with multiple projects
        results = await hybrid_search.search(
            query="test query", limit=5, project_ids=["project-a", "project-b"]
        )

        # Verify filter was applied with multiple project IDs
        mock_qdrant_client.search.assert_called()
        search_call_args = mock_qdrant_client.search.call_args
        query_filter = search_call_args[1]["query_filter"]
        assert query_filter is not None

        # Verify results
        assert len(results) > 0


@pytest.mark.asyncio
async def test_search_engine_with_project_filter(search_engine):
    """Test SearchEngine with project filtering."""
    # Mock the _get_embedding method to avoid async issues
    with patch.object(
        search_engine.hybrid_search, "_get_embedding", new_callable=AsyncMock
    ) as mock_embedding:
        mock_embedding.return_value = [0.1, 0.2, 0.3] * 512

        results = await search_engine.search(
            query="test query", limit=5, project_ids=["project-a"]
        )

        assert len(results) > 0
        for result in results:
            assert isinstance(result, SearchResult)
            assert hasattr(result, "project_id")
            assert hasattr(result, "project_name")


def test_build_filter_with_projects(hybrid_search):
    """Test filter building with project IDs."""
    # Test with project IDs
    filter_obj = hybrid_search._build_filter(["project-a", "project-b"])
    assert filter_obj is not None
    assert hasattr(filter_obj, "must")

    # Test without project IDs
    filter_obj = hybrid_search._build_filter(None)
    assert filter_obj is None

    filter_obj = hybrid_search._build_filter([])
    assert filter_obj is None


def test_extract_project_info(hybrid_search):
    """Test project information extraction from metadata."""
    metadata = {
        "project_id": "test-project",
        "project_name": "Test Project",
        "project_description": "A test project",
        "collection_name": "test_collection",
        "title": "Test Document",
    }

    project_info = hybrid_search._extract_project_info(metadata)

    assert project_info["project_id"] == "test-project"
    assert project_info["project_name"] == "Test Project"
    assert project_info["project_description"] == "A test project"
    assert project_info["collection_name"] == "test_collection"


def test_search_result_project_methods():
    """Test SearchResult project-related methods."""
    result = SearchResult(
        score=0.9,
        text="Test content",
        source_type="git",
        source_title="Test Document",
        project_id="test-project",
        project_name="Test Project",
        project_description="A test project",
        collection_name="test_collection",
    )

    # Test get_project_info
    project_info = result.get_project_info()
    assert project_info is not None
    assert "Project: Test Project" in project_info
    assert "A test project" in project_info
    assert "Collection: test_collection" in project_info

    # Test belongs_to_project
    assert result.belongs_to_project("test-project") is True
    assert result.belongs_to_project("other-project") is False

    # Test belongs_to_any_project
    assert result.belongs_to_any_project(["test-project", "other-project"]) is True
    assert result.belongs_to_any_project(["other-project", "another-project"]) is False


def test_search_result_without_project_info():
    """Test SearchResult methods when project info is not available."""
    result = SearchResult(
        score=0.9, text="Test content", source_type="git", source_title="Test Document"
    )

    # Test get_project_info returns None
    assert result.get_project_info() is None

    # Test belongs_to_project returns False
    assert result.belongs_to_project("any-project") is False

    # Test belongs_to_any_project returns False
    assert result.belongs_to_any_project(["any-project"]) is False


@pytest.mark.asyncio
async def test_keyword_search_with_project_filter(hybrid_search, mock_qdrant_client):
    """Test keyword search with project filtering."""
    # Mock the BM25 scoring to return results
    with patch(
        "qdrant_loader_mcp_server.search.components.keyword_search_service.BM25Okapi"
    ) as mock_bm25_class:
        mock_bm25 = MagicMock()
        mock_bm25.get_scores.return_value = [0.9, 0.8, 0.7]  # Scores for 3 documents
        mock_bm25_class.return_value = mock_bm25

        results = await hybrid_search._keyword_search(
            query="test query", limit=5, project_ids=["project-a"]
        )

        # Verify scroll was called with filter
        mock_qdrant_client.scroll.assert_called()
        scroll_call_args = mock_qdrant_client.scroll.call_args
        assert scroll_call_args[1]["scroll_filter"] is not None

        # Verify results
        assert len(results) > 0


@pytest.mark.asyncio
async def test_vector_search_with_project_filter(hybrid_search, mock_qdrant_client):
    """Test vector search with project filtering."""
    # Mock the _get_embedding method to avoid async issues
    with patch.object(
        hybrid_search, "_get_embedding", new_callable=AsyncMock
    ) as mock_embedding:
        mock_embedding.return_value = [0.1, 0.2, 0.3] * 512

        results = await hybrid_search._vector_search(
            query="test query", limit=5, project_ids=["project-a"]
        )

        # Verify search was called with filter
        mock_qdrant_client.search.assert_called()
        search_call_args = mock_qdrant_client.search.call_args
        assert search_call_args[1]["query_filter"] is not None

        # Verify results
        assert len(results) > 0
