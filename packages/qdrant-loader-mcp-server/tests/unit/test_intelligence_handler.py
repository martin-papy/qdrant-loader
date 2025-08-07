"""Tests for intelligence handler functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from qdrant_loader_mcp_server.mcp.intelligence_handler import IntelligenceHandler
from qdrant_loader_mcp_server.search.engine import SearchEngine
from qdrant_loader_mcp_server.mcp.protocol import MCPProtocol


@pytest.fixture
def mock_search_engine():
    """Create a mock search engine."""
    return AsyncMock(spec=SearchEngine)


@pytest.fixture
def mock_protocol():
    """Create a mock MCP protocol."""
    return MagicMock(spec=MCPProtocol)


@pytest.fixture
def intelligence_handler(mock_search_engine, mock_protocol):
    """Create an intelligence handler instance."""
    return IntelligenceHandler(mock_search_engine, mock_protocol)


class TestIntelligenceHandlerAnalyzeRelationships:
    """Test analyze document relationships functionality."""

    @pytest.mark.asyncio
    async def test_handle_analyze_document_relationships_success(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test successful document relationship analysis."""
        # Mock the search engine response
        mock_analysis_result = {
            "total_documents": 10,
            "relationships": [
                {
                    "type": "hierarchical",
                    "source_doc": "doc1",
                    "target_doc": "doc2",
                    "strength": 0.8
                }
            ],
            "clusters": ["cluster1", "cluster2"]
        }
        mock_search_engine.analyze_document_relationships.return_value = mock_analysis_result
        
        # Mock protocol response creation
        mock_response = {"jsonrpc": "2.0", "id": 1, "result": mock_analysis_result}
        mock_protocol.create_response.return_value = mock_response
        
        # Test the handler
        params = {
            "query": "test query",
            "limit": 20
        }
        
        result = await intelligence_handler.handle_analyze_document_relationships(1, params)
        
        # Verify search engine was called correctly
        mock_search_engine.analyze_document_relationships.assert_called_once_with(
            query="test query",
            limit=20,
            project_ids=None,
            source_types=None
        )
        
        # Verify response was created correctly
        mock_protocol.create_response.assert_called_once()
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_handle_analyze_document_relationships_with_filters(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test document relationship analysis with filters."""
        mock_analysis_result = {"total_documents": 5}
        mock_search_engine.analyze_document_relationships.return_value = mock_analysis_result
        mock_protocol.create_response.return_value = {"result": mock_analysis_result}
        
        params = {
            "query": "filtered query",
            "limit": 15,
            "project_ids": ["proj1", "proj2"],
            "source_types": ["git", "confluence"]
        }
        
        await intelligence_handler.handle_analyze_document_relationships(2, params)
        
        # Verify filters were passed correctly
        mock_search_engine.analyze_document_relationships.assert_called_once_with(
            query="filtered query",
            limit=15,
            project_ids=["proj1", "proj2"],
            source_types=["git", "confluence"]
        )

    @pytest.mark.asyncio
    async def test_handle_analyze_document_relationships_missing_query(self, intelligence_handler, mock_protocol):
        """Test error handling when query parameter is missing."""
        mock_error_response = {
            "error": {
                "code": -32602,
                "message": "Invalid params",
                "data": "Missing required parameter: query"
            }
        }
        mock_protocol.create_response.return_value = mock_error_response
        
        params = {}  # Missing query
        
        result = await intelligence_handler.handle_analyze_document_relationships(3, params)
        
        # Verify error response was created
        mock_protocol.create_response.assert_called_once()
        assert result == mock_error_response

    @pytest.mark.asyncio
    async def test_handle_analyze_document_relationships_engine_error(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test error handling when search engine fails."""
        # Mock search engine to raise an exception
        mock_search_engine.analyze_document_relationships.side_effect = Exception("Analysis failed")
        mock_error_response = {"error": {"message": "Internal error"}}
        mock_protocol.create_response.return_value = mock_error_response
        
        params = {"query": "test"}
        
        result = await intelligence_handler.handle_analyze_document_relationships(4, params)
        
        # Verify error response was created
        mock_protocol.create_response.assert_called()
        assert result == mock_error_response


class TestIntelligenceHandlerFindSimilar:
    """Test find similar documents functionality."""

    @pytest.mark.asyncio
    async def test_handle_find_similar_documents_success(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test successful similar document finding."""
        mock_similar_docs = {
            "target_document": {"id": "doc1", "title": "Target Doc"},
            "similar_documents": [
                {"id": "doc2", "title": "Similar Doc", "similarity": 0.9}
            ]
        }
        mock_search_engine.find_similar_documents.return_value = mock_similar_docs
        mock_protocol.create_response.return_value = {"result": mock_similar_docs}
        
        params = {
            "target_query": "target document",
            "comparison_query": "all documents",
            "max_similar": 5
        }
        
        result = await intelligence_handler.handle_find_similar_documents(5, params)
        
        mock_search_engine.find_similar_documents.assert_called_once_with(
            target_query="target document",
            comparison_query="all documents",
            max_similar=5,
            similarity_metrics=None,
            project_ids=None,
            source_types=None
        )
        assert result == {"result": mock_similar_docs}

    @pytest.mark.asyncio
    async def test_handle_find_similar_documents_with_metrics(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test finding similar documents with specific metrics."""
        mock_result = {"similar_documents": []}
        mock_search_engine.find_similar_documents.return_value = mock_result
        mock_protocol.create_response.return_value = {"result": mock_result}
        
        params = {
            "target_query": "target",
            "comparison_query": "comparison", 
            "similarity_metrics": ["semantic_similarity", "entity_overlap"]
        }
        
        await intelligence_handler.handle_find_similar_documents(6, params)
        
        mock_search_engine.find_similar_documents.assert_called_once_with(
            target_query="target",
            comparison_query="comparison",
            max_similar=5,
            similarity_metrics=["semantic_similarity", "entity_overlap"],
            project_ids=None,
            source_types=None
        )


class TestIntelligenceHandlerDetectConflicts:
    """Test document conflict detection functionality."""

    @pytest.mark.asyncio
    async def test_handle_detect_document_conflicts_success(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test successful conflict detection."""
        mock_conflicts = {
            "total_conflicts": 2,
            "conflicts": [
                {
                    "type": "contradiction",
                    "documents": ["doc1", "doc2"],
                    "severity": "high"
                }
            ]
        }
        mock_search_engine.detect_document_conflicts.return_value = mock_conflicts
        mock_protocol.create_response.return_value = {"result": mock_conflicts}
        
        params = {
            "query": "conflict query",
            "limit": 25
        }
        
        result = await intelligence_handler.handle_detect_document_conflicts(7, params)
        
        mock_search_engine.detect_document_conflicts.assert_called_once_with(
            query="conflict query",
            limit=25,
            project_ids=None,
            source_types=None
        )
        assert result == {"result": mock_conflicts}


class TestIntelligenceHandlerFindComplementary:
    """Test find complementary content functionality."""

    @pytest.mark.asyncio
    async def test_handle_find_complementary_content_success(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test successful complementary content finding."""
        mock_complementary = {
            "target_document": {"id": "doc1"},
            "complementary_content": [
                {"id": "doc3", "relevance": 0.8, "type": "supporting"}
            ]
        }
        mock_search_engine.find_complementary_content.return_value = mock_complementary
        mock_protocol.create_response.return_value = {"result": mock_complementary}
        
        params = {
            "target_query": "target content",
            "context_query": "related context",
            "max_recommendations": 10
        }
        
        result = await intelligence_handler.handle_find_complementary_content(8, params)
        
        mock_search_engine.find_complementary_content.assert_called_once_with(
            target_query="target content",
            context_query="related context",
            max_recommendations=10,
            project_ids=None,
            source_types=None
        )
        assert result == {"result": mock_complementary}


class TestIntelligenceHandlerClusterDocuments:
    """Test document clustering functionality."""

    @pytest.mark.asyncio
    async def test_handle_cluster_documents_success(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test successful document clustering."""
        mock_clusters = {
            "total_documents": 50,
            "clusters": [
                {
                    "id": "cluster1",
                    "theme": "API Documentation",
                    "documents": ["doc1", "doc2"],
                    "size": 2
                }
            ]
        }
        mock_search_engine.cluster_documents.return_value = mock_clusters
        mock_protocol.create_response.return_value = {"result": mock_clusters}
        
        params = {
            "query": "clustering query",
            "max_clusters": 5,
            "min_cluster_size": 3
        }
        
        result = await intelligence_handler.handle_cluster_documents(9, params)
        
        mock_search_engine.cluster_documents.assert_called_once_with(
            query="clustering query",
            limit=25,
            max_clusters=5,
            min_cluster_size=3,
            strategy="mixed_features",
            project_ids=None,
            source_types=None
        )
        assert result == {"result": mock_clusters}

    @pytest.mark.asyncio
    async def test_handle_cluster_documents_with_strategy(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test document clustering with specific strategy."""
        mock_clusters = {"clusters": []}
        mock_search_engine.cluster_documents.return_value = mock_clusters
        mock_protocol.create_response.return_value = {"result": mock_clusters}
        
        params = {
            "query": "strategy test",
            "strategy": "hierarchical",
            "limit": 30
        }
        
        await intelligence_handler.handle_cluster_documents(10, params)
        
        mock_search_engine.cluster_documents.assert_called_once_with(
            query="strategy test",
            limit=30,
            max_clusters=10,
            min_cluster_size=2,
            strategy="hierarchical",
            project_ids=None,
            source_types=None
        )


class TestIntelligenceHandlerEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_search_engine, mock_protocol):
        """Test proper initialization of IntelligenceHandler."""
        handler = IntelligenceHandler(mock_search_engine, mock_protocol)
        
        assert handler.search_engine == mock_search_engine
        assert handler.protocol == mock_protocol
        assert handler.formatters is not None

    @pytest.mark.asyncio
    async def test_find_similar_missing_target_query(self, intelligence_handler, mock_protocol):
        """Test find similar documents with missing target_query."""
        mock_error_response = {"error": {"message": "Missing target_query"}}
        mock_protocol.create_response.return_value = mock_error_response
        
        params = {"comparison_query": "all docs"}  # Missing target_query
        
        result = await intelligence_handler.handle_find_similar_documents(11, params)
        
        # Should handle missing parameter gracefully
        assert "error" in result or result == mock_error_response

    @pytest.mark.asyncio
    async def test_find_complementary_missing_context_query(self, intelligence_handler, mock_protocol):
        """Test find complementary content with missing context_query."""
        mock_error_response = {"error": {"message": "Missing context_query"}}
        mock_protocol.create_response.return_value = mock_error_response
        
        params = {"target_query": "target"}  # Missing context_query
        
        result = await intelligence_handler.handle_find_complementary_content(12, params)
        
        # Should handle missing parameter gracefully
        assert "error" in result or result == mock_error_response

    @pytest.mark.asyncio
    async def test_detect_conflicts_missing_query(self, intelligence_handler, mock_protocol):
        """Test detect conflicts with missing query."""
        mock_error_response = {"error": {"message": "Missing query"}}
        mock_protocol.create_response.return_value = mock_error_response
        
        params = {}  # Missing query
        
        result = await intelligence_handler.handle_detect_document_conflicts(13, params)
        
        # Should handle missing parameter gracefully
        assert "error" in result or result == mock_error_response

    @pytest.mark.asyncio
    async def test_cluster_documents_missing_query(self, intelligence_handler, mock_protocol):
        """Test cluster documents with missing query."""
        mock_error_response = {"error": {"message": "Missing query"}}
        mock_protocol.create_response.return_value = mock_error_response
        
        params = {}  # Missing query
        
        result = await intelligence_handler.handle_cluster_documents(14, params)
        
        # Should handle missing parameter gracefully
        assert "error" in result or result == mock_error_response
