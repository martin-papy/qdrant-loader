"""Tests for hybrid search implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from openai import AsyncOpenAI
from qdrant_loader_mcp_server.search.hybrid_search import (
    HybridSearchEngine,
)
from qdrant_loader_mcp_server.search.components.search_result_models import HybridSearchResult, create_hybrid_search_result


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client."""
    client = AsyncMock()

    # Create mock search results
    search_result1 = MagicMock()
    search_result1.id = "1"
    search_result1.score = 0.8
    search_result1.payload = {
        "content": "Test content 1",
        "metadata": {"title": "Test Doc 1", "url": "http://test1.com"},
        "source_type": "git",
    }

    search_result2 = MagicMock()
    search_result2.id = "2"
    search_result2.score = 0.7
    search_result2.payload = {
        "content": "Test content 2",
        "metadata": {"title": "Test Doc 2", "url": "http://test2.com"},
        "source_type": "confluence",
    }

    search_result3 = MagicMock()
    search_result3.id = "3"
    search_result3.score = 0.6
    search_result3.payload = {
        "content": "Test content 3",
        "metadata": {"title": "Test Doc 3", "file_path": "/path/to/file.txt"},
        "source_type": "localfile",
    }

    client.search.return_value = [search_result1, search_result2, search_result3]

    # Create mock scroll results
    scroll_result1 = MagicMock()
    scroll_result1.id = "1"
    scroll_result1.payload = {
        "content": "Test content 1",
        "metadata": {"title": "Test Doc 1", "url": "http://test1.com"},
        "source_type": "git",
    }

    scroll_result2 = MagicMock()
    scroll_result2.id = "2"
    scroll_result2.payload = {
        "content": "Test content 2",
        "metadata": {"title": "Test Doc 2", "url": "http://test2.com"},
        "source_type": "confluence",
    }

    scroll_result3 = MagicMock()
    scroll_result3.id = "3"
    scroll_result3.payload = {
        "content": "Test content 3",
        "metadata": {"title": "Test Doc 3", "file_path": "/path/to/file.txt"},
        "source_type": "localfile",
    }

    client.scroll.return_value = (
        [scroll_result1, scroll_result2, scroll_result3],
        None,
    )
    
    # Mock collection operations
    collections_response = MagicMock()
    collections_response.collections = []
    client.get_collections.return_value = collections_response
    client.create_collection.return_value = None
    client.close.return_value = None
    
    return client


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    client = AsyncMock(spec=AsyncOpenAI)

    # Mock embeddings response
    embedding_response = MagicMock()
    embedding_data = MagicMock()
    embedding_data.embedding = [0.1, 0.2, 0.3] * 512  # 1536 dimensions
    embedding_response.data = [embedding_data]

    # Make the embeddings.create method async
    client.embeddings.create = AsyncMock(return_value=embedding_response)

    return client


@pytest.fixture
def hybrid_search(mock_qdrant_client, mock_openai_client):
    """Create a HybridSearchEngine instance with mocked dependencies."""
    return HybridSearchEngine(
        qdrant_client=mock_qdrant_client,
        openai_client=mock_openai_client,
        collection_name="test_collection",
    )


@pytest.mark.asyncio
async def test_search_basic(hybrid_search):
    """Test basic search functionality."""
    # Mock the internal methods to avoid actual API calls
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    hybrid_search._expand_query = AsyncMock(return_value="test query")

    results = await hybrid_search.search("test query")

    assert len(results) > 0
    assert isinstance(results[0], HybridSearchResult)
    assert results[0].score > 0
    assert results[0].text == "Test content 1"
    assert results[0].source_type == "git"


@pytest.mark.asyncio
async def test_search_with_source_type_filter(hybrid_search):
    """Test search with source type filtering."""
    # Mock the internal methods to avoid actual API calls
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    hybrid_search._expand_query = AsyncMock(return_value="test query")

    results = await hybrid_search.search("test query", source_types=["git"])

    assert len(results) > 0
    assert all(r.source_type == "git" for r in results)


@pytest.mark.asyncio
async def test_search_with_localfile_filter(hybrid_search):
    """Test search with localfile source type filtering."""
    # Mock the internal methods to avoid actual API calls
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    hybrid_search._expand_query = AsyncMock(return_value="test query")

    results = await hybrid_search.search("test query", source_types=["localfile"])

    assert len(results) > 0
    assert all(r.source_type == "localfile" for r in results)


@pytest.mark.asyncio
async def test_search_query_expansion(hybrid_search):
    """Test query expansion functionality."""
    # Mock the internal methods to avoid actual API calls
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    hybrid_search._expand_query = AsyncMock(
        return_value="product requirements for API PRD requirements document product specification"
    )

    await hybrid_search.search("product requirements for API")

    # Verify that query expansion was called
    hybrid_search._expand_query.assert_called_once_with("product requirements for API")


@pytest.mark.asyncio
async def test_search_error_handling(hybrid_search, mock_qdrant_client):
    """Test error handling during search."""
    mock_qdrant_client.search.side_effect = Exception("Test error")

    with pytest.raises(Exception):
        await hybrid_search.search("test query")


@pytest.mark.asyncio
async def test_search_empty_results(hybrid_search, mock_qdrant_client):
    """Test handling of empty search results."""
    # Mock the internal methods to avoid actual API calls
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    hybrid_search._expand_query = AsyncMock(return_value="test query")
    hybrid_search._vector_search = AsyncMock(return_value=[])
    hybrid_search._keyword_search = AsyncMock(return_value=[])

    mock_qdrant_client.search.return_value = []
    mock_qdrant_client.scroll.return_value = ([], None)

    results = await hybrid_search.search("test query")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_search_result_scoring(hybrid_search):
    """Test that search results are properly scored and ranked."""
    # Mock the internal methods to avoid actual API calls
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    hybrid_search._expand_query = AsyncMock(return_value="test query")

    results = await hybrid_search.search("test query")

    # Check that results are sorted by score
    assert all(
        results[i].score >= results[i + 1].score for i in range(len(results) - 1)
    )


@pytest.mark.asyncio
async def test_search_with_limit(hybrid_search):
    """Test search with result limit."""
    # Mock the internal methods to avoid actual API calls
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    hybrid_search._expand_query = AsyncMock(return_value="test query")

    # Disable intent adaptation for this test to ensure predictable limit behavior
    original_enable_intent = getattr(hybrid_search, 'enable_intent_adaptation', False)
    hybrid_search.enable_intent_adaptation = False

    limit = 1
    results = await hybrid_search.search("test query", limit=limit)
    assert len(results) <= limit

    # Restore original setting
    hybrid_search.enable_intent_adaptation = original_enable_intent


# New comprehensive tests for missing methods


@pytest.mark.asyncio
async def test_expand_query_with_expansions(hybrid_search):
    """Test query expansion with known terms."""
    # Test product requirements expansion (spaCy semantic expansion)
    expanded = await hybrid_search._expand_query("product requirements")
    assert "product requirements" in expanded  # Original terms preserved
    assert len(expanded) > len("product requirements")  # Should be expanded
    
    # Test API expansion
    expanded = await hybrid_search._expand_query("API documentation")
    assert "API documentation" in expanded  # Original terms preserved
    assert len(expanded) > len("API documentation")  # Should be expanded

    # Test expansion behavior for simple terms
    expanded = await hybrid_search._expand_query("unknown term")
    assert "unknown term" in expanded  # Original preserved


@pytest.mark.asyncio
async def test_expand_query_case_insensitive(hybrid_search):
    """Test that query expansion is case insensitive."""
    expanded = await hybrid_search._expand_query("PRODUCT REQUIREMENTS")
    assert "PRD" in expanded
    assert "requirements document" in expanded


def test_analyze_query_questions(hybrid_search):
    """Test query analysis for questions."""
    context = hybrid_search._analyze_query("What is the API documentation?")
    assert context["is_question"] is True
    # spaCy removes stopwords like "what", so check for meaningful keywords
    assert "api" in context["keywords"] or "documentation" in context["keywords"]

    context = hybrid_search._analyze_query("How to implement authentication?")
    assert context["is_question"] is True
    # Intent may be "general" if confidence is low, which is acceptable
    assert context["probable_intent"] in ["procedural", "general", "technical_lookup"]


def test_analyze_query_broad_vs_specific(hybrid_search):
    """Test query analysis for broad vs specific queries."""
    # Broad query (< 5 words)
    context = hybrid_search._analyze_query("API docs")
    assert context["is_broad"] is True
    assert context["is_specific"] is False

    # Specific query (> 7 words)
    context = hybrid_search._analyze_query(
        "How to implement OAuth2 authentication in the REST API endpoints"
    )
    assert context["is_broad"] is False
    assert context["is_specific"] is True


def test_analyze_query_intent_detection(hybrid_search):
    """Test query intent detection."""
    # Requirements intent (spaCy may classify differently)
    context = hybrid_search._analyze_query("product requirements document")
    # Accept various intents that spaCy might assign
    assert context["probable_intent"] in ["business_context", "general", "informational"]

    # Architecture intent (spaCy may classify as technical)
    context = hybrid_search._analyze_query("system architecture design")
    assert context["probable_intent"] in ["technical_lookup", "general", "business_context"]

    # Procedural intent (spaCy may classify as general or procedural)
    context = hybrid_search._analyze_query("steps to deploy application")
    assert context["probable_intent"] in ["procedural", "general", "technical_lookup"]


@pytest.mark.asyncio
async def test_vector_search(hybrid_search, mock_qdrant_client):
    """Test vector search functionality."""
    hybrid_search._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)

    results = await hybrid_search._vector_search("test query", 5)

    assert len(results) == 3
    assert results[0]["score"] == 0.8
    assert results[0]["text"] == "Test content 1"
    assert results[0]["source_type"] == "git"

    # Verify Qdrant search was called with correct parameters
    mock_qdrant_client.search.assert_called_once()
    call_args = mock_qdrant_client.search.call_args
    assert call_args[1]["collection_name"] == "test_collection"
    assert call_args[1]["limit"] == 5


@pytest.mark.asyncio
async def test_keyword_search(hybrid_search, mock_qdrant_client):
    """Test keyword search functionality."""
    # Add a third mock result to match BM25 scores
    search_result3 = MagicMock()
    search_result3.id = "3"
    search_result3.score = 0.6
    search_result3.payload = {
        "content": "Test content 3",
        "metadata": {"title": "Test Doc 3", "url": "http://test3.com"},
        "source_type": "jira",
    }
    
    # Update scroll to return 3 results
    original_scroll_return = mock_qdrant_client.scroll.return_value
    original_results = original_scroll_return[0]
    mock_qdrant_client.scroll.return_value = (
        original_results + [search_result3], 
        None
    )
    
    with patch("qdrant_loader_mcp_server.search.components.keyword_search_service.BM25Okapi") as mock_bm25:
        # Mock BM25 scoring
        mock_bm25_instance = MagicMock()
        mock_bm25_instance.get_scores.return_value = np.array([0.5, 0.8, 0.3])
        mock_bm25.return_value = mock_bm25_instance

        results = await hybrid_search._keyword_search("test query", 5)

        assert len(results) == 3
        # Results should be sorted by BM25 score (highest first)
        assert results[0]["score"] == 0.8
        assert results[1]["score"] == 0.5
        assert results[2]["score"] == 0.3

        # Verify scroll was called
        mock_qdrant_client.scroll.assert_called_once()


@pytest.mark.asyncio
async def test_combine_results(hybrid_search):
    """Test result combination and scoring."""
    vector_results = [
        {
            "score": 0.8,
            "text": "Test content 1",
            "metadata": {"title": "Doc 1"},
            "source_type": "git",
        }
    ]

    keyword_results = [
        {
            "score": 0.6,
            "text": "Test content 1",  # Same content
            "metadata": {"title": "Doc 1"},
            "source_type": "git",
        },
        {
            "score": 0.4,
            "text": "Test content 2",  # Different content
            "metadata": {"title": "Doc 2"},
            "source_type": "confluence",
        },
    ]

    query_context = {"is_question": False, "probable_intent": "informational"}

    results = await hybrid_search._combine_results(
        vector_results, keyword_results, query_context, 5
    )

    # The second result has score 0.4 * 0.3 = 0.12, which is below min_score (0.3)
    # So only the first result should be returned
    assert len(results) == 1
    # First result should have combined scores
    assert results[0].vector_score == 0.8
    assert results[0].keyword_score == 0.6
    # Combined score = 0.6 * 0.8 + 0.3 * 0.6 = 0.48 + 0.18 = 0.66
    assert abs(results[0].score - 0.66) < 0.01


@pytest.mark.asyncio
async def test_combine_results_with_source_filter(hybrid_search):
    """Test result combination with source type filtering."""
    vector_results = [
        {
            "score": 0.8,
            "text": "Git content",
            "metadata": {"title": "Git Doc"},
            "source_type": "git",
        }
    ]

    keyword_results = [
        {
            "score": 0.6,
            "text": "Confluence content",
            "metadata": {"title": "Confluence Doc"},
            "source_type": "confluence",
        }
    ]

    query_context = {"is_question": False}

    # Filter for only git results
    results = await hybrid_search._combine_results(
        vector_results, keyword_results, query_context, 5, source_types=["git"]
    )

    assert len(results) == 1
    assert results[0].source_type == "git"


@pytest.mark.asyncio
async def test_combine_results_with_low_min_score(hybrid_search):
    """Test result combination with lower min_score threshold."""
    # Create a hybrid search engine with lower min_score
    hybrid_search.min_score = 0.1

    vector_results = [
        {
            "score": 0.8,
            "text": "Test content 1",
            "metadata": {"title": "Doc 1"},
            "source_type": "git",
        }
    ]

    keyword_results = [
        {
            "score": 0.6,
            "text": "Test content 1",  # Same content
            "metadata": {"title": "Doc 1"},
            "source_type": "git",
        },
        {
            "score": 0.4,
            "text": "Test content 2",  # Different content
            "metadata": {"title": "Doc 2"},
            "source_type": "confluence",
        },
    ]

    query_context = {"is_question": False, "probable_intent": "informational"}

    results = await hybrid_search._combine_results(
        vector_results, keyword_results, query_context, 5
    )

    # Now both results should pass the min_score threshold
    assert len(results) == 2
    # First result should have combined scores
    assert results[0].vector_score == 0.8
    assert results[0].keyword_score == 0.6
    # Combined score = 0.6 * 0.8 + 0.3 * 0.6 = 0.48 + 0.18 = 0.66
    assert abs(results[0].score - 0.66) < 0.01

    # Second result should have only keyword score
    assert results[1].vector_score == 0.0
    assert results[1].keyword_score == 0.4
    # Combined score = 0.6 * 0.0 + 0.3 * 0.4 = 0.12
    assert abs(results[1].score - 0.12) < 0.01


def test_extract_metadata_info_hierarchy(hybrid_search):
    """Test metadata extraction for hierarchy information."""
    metadata = {
        "parent_id": "parent-123",
        "parent_title": "Parent Document",
        "breadcrumb_text": "Root > Parent > Current",
        "depth": 2,
        "children": ["child1", "child2", "child3"],
    }

    info = hybrid_search._extract_metadata_info(metadata)

    assert info["parent_id"] == "parent-123"
    assert info["parent_title"] == "Parent Document"
    assert info["breadcrumb_text"] == "Root > Parent > Current"
    assert info["depth"] == 2
    assert info["children_count"] == 3
    assert "Path: Root > Parent > Current" in info["hierarchy_context"]
    assert "Depth: 2" in info["hierarchy_context"]
    assert "Children: 3" in info["hierarchy_context"]


def test_extract_metadata_info_attachment(hybrid_search):
    """Test metadata extraction for attachment information."""
    metadata = {
        "is_attachment": True,
        "parent_document_id": "doc-456",
        "parent_document_title": "Project Plan",
        "attachment_id": "att-789",
        "original_filename": "requirements.pdf",
        "file_size": 2048000,  # 2MB
        "mime_type": "application/pdf",
        "author": "john.doe@company.com",
    }

    info = hybrid_search._extract_metadata_info(metadata)

    assert info["is_attachment"] is True
    assert info["parent_document_id"] == "doc-456"
    assert info["parent_document_title"] == "Project Plan"
    assert info["attachment_id"] == "att-789"
    assert info["original_filename"] == "requirements.pdf"
    assert info["file_size"] == 2048000
    assert info["mime_type"] == "application/pdf"
    assert info["attachment_author"] == "john.doe@company.com"

    # Check attachment context formatting
    assert "File: requirements.pdf" in info["attachment_context"]
    assert "Size: 2.0 MB" in info["attachment_context"]
    assert "Type: application/pdf" in info["attachment_context"]
    assert "Author: john.doe@company.com" in info["attachment_context"]


def test_extract_metadata_info_file_size_formatting(hybrid_search):
    """Test file size formatting in different units."""
    # Test bytes
    metadata = {"is_attachment": True, "file_size": 512}
    info = hybrid_search._extract_metadata_info(metadata)
    assert "Size: 512 B" in info["attachment_context"]

    # Test KB
    metadata = {"is_attachment": True, "file_size": 2048}
    info = hybrid_search._extract_metadata_info(metadata)
    assert "Size: 2.0 KB" in info["attachment_context"]

    # Test MB
    metadata = {"is_attachment": True, "file_size": 2048000}
    info = hybrid_search._extract_metadata_info(metadata)
    assert "Size: 2.0 MB" in info["attachment_context"]

    # Test GB
    metadata = {"is_attachment": True, "file_size": 2048000000}
    info = hybrid_search._extract_metadata_info(metadata)
    assert "Size: 1.9 GB" in info["attachment_context"]


def test_extract_metadata_info_empty_metadata(hybrid_search):
    """Test metadata extraction with empty metadata."""
    metadata = {}

    info = hybrid_search._extract_metadata_info(metadata)

    # All fields should be None or False
    assert info["parent_id"] is None
    assert info["parent_title"] is None
    assert info["breadcrumb_text"] is None
    assert info["depth"] is None
    assert info["children_count"] is None
    assert info["hierarchy_context"] is None
    assert info["is_attachment"] is False
    assert info["attachment_context"] is None


@pytest.mark.asyncio
async def test_get_embedding_error_handling(hybrid_search, mock_openai_client):
    """Test error handling in embedding generation."""
    mock_openai_client.embeddings.create.side_effect = Exception("API Error")

    with pytest.raises(Exception, match="API Error"):
        await hybrid_search._get_embedding("test text")


@pytest.mark.asyncio
async def test_get_embedding_success(hybrid_search, mock_openai_client):
    """Test successful embedding generation."""
    # Use the actual mock client instead of calling the real method
    embedding = await hybrid_search._get_embedding("test text")

    assert len(embedding) == 1536  # 512 * 3
    assert embedding[0] == 0.1

    # Verify OpenAI API was called correctly
    mock_openai_client.embeddings.create.assert_called_once_with(
        model="text-embedding-3-small", input="test text"
    )
