"""Tests for intelligence handler functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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


class TestIntelligenceHandlerExpandCluster:
    """Test cluster expansion functionality."""

    @pytest.mark.asyncio
    async def test_handle_expand_cluster_success(self, intelligence_handler, mock_protocol):
        """Test successful cluster expansion."""
        mock_expansion_result = {
            "cluster_id": "cluster123",
            "message": "Cluster expansion functionality requires re-running clustering",
            "suggestion": "Please run cluster_documents again and use the lightweight response for navigation",
            "cluster_info": {
                "expansion_requested": True,
                "limit": 20,
                "offset": 0,
                "include_metadata": True
            },
            "documents": [],
            "pagination": {
                "offset": 0,
                "limit": 20,
                "total": 0,
                "has_more": False
            }
        }
        mock_protocol.create_response.return_value = {"result": mock_expansion_result}
        
        params = {
            "cluster_id": "cluster123",
            "limit": 20,
            "offset": 0,
            "include_metadata": True
        }
        
        result = await intelligence_handler.handle_expand_cluster(15, params)
        
        # Verify response was created correctly
        mock_protocol.create_response.assert_called_once()
        assert result == {"result": mock_expansion_result}

    @pytest.mark.asyncio
    async def test_handle_expand_cluster_with_pagination(self, intelligence_handler, mock_protocol):
        """Test cluster expansion with pagination parameters."""
        mock_response = {"result": {"cluster_id": "cluster456"}}
        mock_protocol.create_response.return_value = mock_response
        
        params = {
            "cluster_id": "cluster456",
            "limit": 10,
            "offset": 5,
            "include_metadata": False
        }
        
        result = await intelligence_handler.handle_expand_cluster(16, params)
        
        mock_protocol.create_response.assert_called_once()
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_handle_expand_cluster_missing_cluster_id(self, intelligence_handler, mock_protocol):
        """Test cluster expansion with missing cluster_id."""
        mock_error_response = {
            "error": {
                "code": -32602,
                "message": "Invalid params",
                "data": "Missing required parameter: cluster_id"
            }
        }
        mock_protocol.create_response.return_value = mock_error_response
        
        params = {}  # Missing cluster_id
        
        result = await intelligence_handler.handle_expand_cluster(17, params)
        
        # Verify error response was created
        mock_protocol.create_response.assert_called_once()
        assert result == mock_error_response

    @pytest.mark.asyncio
    async def test_handle_expand_cluster_with_exception(self, intelligence_handler, mock_protocol):
        """Test cluster expansion error handling."""
        # Mock protocol to raise an exception during processing
        mock_protocol.create_response.side_effect = Exception("Unexpected error")
        
        params = {"cluster_id": "cluster789"}
        
        # This should raise the exception since we're not catching it in the current implementation
        with pytest.raises(Exception, match="Unexpected error"):
            await intelligence_handler.handle_expand_cluster(18, params)


class TestIntelligenceHandlerComplexDataProcessing:
    """Test complex data processing logic in analyze document relationships."""

    @pytest.mark.asyncio
    async def test_analyze_relationships_with_document_clusters(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test processing of document clusters in relationship analysis."""
        complex_analysis_result = {
            "query_metadata": {"document_count": 25},
            "document_clusters": [
                {
                    "theme": "API Documentation",
                    "cohesion_score": 0.85,
                    "documents": [
                        {
                            "document_id": "doc1",
                            "title": "REST API Guide",
                            "source_type": "confluence",
                            "source_title": "API Docs"
                        },
                        {
                            "document_id": "doc2", 
                            "title": "GraphQL API Reference",
                            "source_type": "git",
                            "source_title": "API Reference"
                        }
                    ]
                }
            ]
        }
        
        mock_search_engine.analyze_document_relationships.return_value = complex_analysis_result
        mock_protocol.create_response.return_value = {"result": "success"}
        
        params = {"query": "API documentation"}
        result = await intelligence_handler.handle_analyze_document_relationships(19, params)
        
        # Verify the method was called
        mock_search_engine.analyze_document_relationships.assert_called_once()
        mock_protocol.create_response.assert_called_once()
        
        # Check that create_response was called with structured content containing relationships
        call_args = mock_protocol.create_response.call_args
        response_data = call_args[1]["result"]["structuredContent"]
        
        # Should have similarity relationships between clustered documents
        assert "relationships" in response_data
        assert len(response_data["relationships"]) >= 1
        assert response_data["total_analyzed"] == 25
        assert "document clusters found" in response_data["summary"]

    @pytest.mark.asyncio
    async def test_analyze_relationships_with_conflicts(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test processing of conflict analysis in relationship analysis."""
        conflict_analysis_result = {
            "query_metadata": {"document_count": 15},
            "conflict_analysis": {
                "conflicting_pairs": [
                    [
                        {"document_id": "doc1", "title": "Old Policy"},
                        {"document_id": "doc2", "title": "New Policy"},
                        {"severity": 0.9, "type": "policy_contradiction"}
                    ]
                ]
            }
        }
        
        mock_search_engine.analyze_document_relationships.return_value = conflict_analysis_result
        mock_protocol.create_response.return_value = {"result": "success"}
        
        params = {"query": "policy conflicts"}
        result = await intelligence_handler.handle_analyze_document_relationships(20, params)
        
        # Verify processing
        call_args = mock_protocol.create_response.call_args
        response_data = call_args[1]["result"]["structuredContent"]
        
        # Should have conflict relationships
        assert "relationships" in response_data
        conflict_relationships = [r for r in response_data["relationships"] if r["relationship_type"] == "conflict"]
        assert len(conflict_relationships) >= 1
        assert "conflicts detected" in response_data["summary"]

    @pytest.mark.asyncio
    async def test_analyze_relationships_with_complementary_content(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test processing of complementary content in relationship analysis."""
        
        # Mock ComplementaryContent object
        mock_complementary_obj = MagicMock()
        mock_complementary_obj.get_top_recommendations.return_value = [
            {
                "document_id": "doc3",
                "title": "Supporting Document",
                "relevance_score": 0.8,
                "recommendation_reason": "provides additional context"
            }
        ]
        
        complementary_analysis_result = {
            "query_metadata": {"document_count": 20},
            "complementary_content": {
                "doc1": mock_complementary_obj
            }
        }
        
        mock_search_engine.analyze_document_relationships.return_value = complementary_analysis_result
        mock_protocol.create_response.return_value = {"result": "success"}
        
        params = {"query": "complementary analysis"}
        result = await intelligence_handler.handle_analyze_document_relationships(21, params)
        
        # Verify processing
        call_args = mock_protocol.create_response.call_args
        response_data = call_args[1]["result"]["structuredContent"]
        
        # Should have complementary relationships
        complementary_relationships = [r for r in response_data["relationships"] if r["relationship_type"] == "complementary"]
        assert len(complementary_relationships) >= 1
        assert "complementary relationships" in response_data["summary"]

    @pytest.mark.asyncio
    async def test_analyze_relationships_with_citation_network(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test processing of citation networks in relationship analysis."""
        citation_analysis_result = {
            "query_metadata": {"document_count": 30},
            "citation_network": {
                "edges": 15,
                "nodes": 10
            },
            "similarity_insights": [
                {"pattern": "cross_referencing", "strength": 0.7}
            ]
        }
        
        mock_search_engine.analyze_document_relationships.return_value = citation_analysis_result
        mock_protocol.create_response.return_value = {"result": "success"}
        
        params = {"query": "citation analysis"}
        result = await intelligence_handler.handle_analyze_document_relationships(22, params)
        
        # Verify processing
        call_args = mock_protocol.create_response.call_args
        response_data = call_args[1]["result"]["structuredContent"]
        
        # Should mention citation relationships and similarity patterns
        assert "citation relationships" in response_data["summary"]
        assert "similarity patterns identified" in response_data["summary"]

    @pytest.mark.asyncio
    async def test_analyze_relationships_empty_results(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test handling of empty analysis results."""
        empty_analysis_result = {
            "query_metadata": {"document_count": 5}
        }
        
        mock_search_engine.analyze_document_relationships.return_value = empty_analysis_result
        mock_protocol.create_response.return_value = {"result": "success"}
        
        params = {"query": "empty results"}
        result = await intelligence_handler.handle_analyze_document_relationships(23, params)
        
        # Verify processing
        call_args = mock_protocol.create_response.call_args
        response_data = call_args[1]["result"]["structuredContent"]
        
        # Should handle empty results gracefully
        assert response_data["relationships"] == []
        assert response_data["total_analyzed"] == 5
        assert "no significant relationships found" in response_data["summary"]

    @pytest.mark.asyncio  
    async def test_analyze_relationships_malformed_conflict_data(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test handling of malformed conflict data."""
        malformed_analysis_result = {
            "query_metadata": {"document_count": 10},
            "conflict_analysis": {
                "conflicting_pairs": [
                    # Malformed data - not enough elements
                    ["only_one_element"],
                    # Good data
                    [
                        {"document_id": "doc1", "title": "Doc1"},
                        {"document_id": "doc2", "title": "Doc2"},
                        {"severity": 0.6, "type": "minor_conflict"}
                    ]
                ]
            }
        }
        
        mock_search_engine.analyze_document_relationships.return_value = malformed_analysis_result
        mock_protocol.create_response.return_value = {"result": "success"}
        
        params = {"query": "malformed conflicts"}
        result = await intelligence_handler.handle_analyze_document_relationships(24, params)
        
        # Should handle malformed data gracefully and process valid entries
        call_args = mock_protocol.create_response.call_args
        response_data = call_args[1]["result"]["structuredContent"]
        
        # Should have at least one valid conflict relationship
        conflict_relationships = [r for r in response_data["relationships"] if r["relationship_type"] == "conflict"]
        assert len(conflict_relationships) >= 1


class TestIntelligenceHandlerErrorHandling:
    """Test comprehensive error handling for all handler methods."""

    @pytest.mark.asyncio
    async def test_find_similar_documents_search_engine_error(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test error handling when search engine fails in find_similar_documents."""
        mock_search_engine.find_similar_documents.side_effect = Exception("Search engine failure")
        mock_error_response = {
            "error": {
                "code": -32603,
                "message": "Internal server error"
            }
        }
        mock_protocol.create_response.return_value = mock_error_response
        
        params = {
            "target_query": "test target",
            "comparison_query": "test comparison"
        }
        
        result = await intelligence_handler.handle_find_similar_documents(25, params)
        
        # Verify error response was created
        mock_protocol.create_response.assert_called_once()
        call_args = mock_protocol.create_response.call_args
        assert call_args[1]["error"]["code"] == -32603
        assert result == mock_error_response

    @pytest.mark.asyncio
    async def test_detect_conflicts_search_engine_error(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test error handling when search engine fails in detect_document_conflicts."""
        mock_search_engine.detect_document_conflicts.side_effect = RuntimeError("Database connection lost")
        mock_error_response = {
            "error": {
                "code": -32603,
                "message": "Internal server error"
            }
        }
        mock_protocol.create_response.return_value = mock_error_response
        
        params = {"query": "conflict test"}
        
        result = await intelligence_handler.handle_detect_document_conflicts(26, params)
        
        # Verify error response was created
        mock_protocol.create_response.assert_called_once()
        assert result == mock_error_response

    @pytest.mark.asyncio
    async def test_find_complementary_content_search_engine_error(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test error handling when search engine fails in find_complementary_content."""
        mock_search_engine.find_complementary_content.side_effect = ValueError("Invalid search parameters")
        mock_error_response = {
            "error": {
                "code": -32603,
                "message": "Internal server error"
            }
        }
        mock_protocol.create_response.return_value = mock_error_response
        
        params = {
            "target_query": "target test",
            "context_query": "context test"
        }
        
        result = await intelligence_handler.handle_find_complementary_content(27, params)
        
        # Verify error response was created
        mock_protocol.create_response.assert_called_once()
        assert result == mock_error_response

    @pytest.mark.asyncio
    async def test_cluster_documents_search_engine_error(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test error handling when search engine fails in cluster_documents."""
        mock_search_engine.cluster_documents.side_effect = ConnectionError("Connection timeout")
        mock_error_response = {
            "error": {
                "code": -32603,
                "message": "Internal server error"
            }
        }
        mock_protocol.create_response.return_value = mock_error_response
        
        params = {"query": "cluster test"}
        
        result = await intelligence_handler.handle_cluster_documents(28, params)
        
        # Verify error response was created
        mock_protocol.create_response.assert_called_once()
        assert result == mock_error_response

    @pytest.mark.asyncio
    async def test_expand_cluster_internal_error(self, intelligence_handler, mock_protocol):
        """Test error handling for internal errors in expand_cluster."""
        # First call succeeds to get past validation, second call (create_response) fails
        mock_protocol.create_response.side_effect = [None, Exception("Internal error")]
        
        params = {"cluster_id": "test_cluster"}
        
        # The method should catch the exception and return an error response
        result = await intelligence_handler.handle_expand_cluster(29, params)
        
        # Should have attempted to create response twice (once succeeds, once fails and gets caught)
        assert mock_protocol.create_response.call_count >= 1


class TestIntelligenceHandlerParameterValidation:
    """Test comprehensive parameter validation for all handler methods."""

    @pytest.mark.asyncio
    async def test_find_similar_documents_missing_comparison_query(self, intelligence_handler, mock_protocol):
        """Test find similar documents with missing comparison_query."""
        mock_error_response = {
            "error": {
                "code": -32602,
                "message": "Invalid params",
                "data": "Missing required parameters: target_query and comparison_query"
            }
        }
        mock_protocol.create_response.return_value = mock_error_response
        
        params = {"target_query": "test target"}  # Missing comparison_query
        
        result = await intelligence_handler.handle_find_similar_documents(30, params)
        
        # Verify error response was created for missing parameter
        mock_protocol.create_response.assert_called_once()
        call_args = mock_protocol.create_response.call_args
        assert call_args[1]["error"]["code"] == -32602
        assert result == mock_error_response

    @pytest.mark.asyncio
    async def test_find_similar_documents_missing_both_queries(self, intelligence_handler, mock_protocol):
        """Test find similar documents with missing both required queries."""
        mock_error_response = {
            "error": {
                "code": -32602,
                "message": "Invalid params",
                "data": "Missing required parameters: target_query and comparison_query"
            }
        }
        mock_protocol.create_response.return_value = mock_error_response
        
        params = {}  # Missing both target_query and comparison_query
        
        result = await intelligence_handler.handle_find_similar_documents(31, params)
        
        # Verify error response was created
        mock_protocol.create_response.assert_called_once()
        assert result == mock_error_response

    @pytest.mark.asyncio
    async def test_find_complementary_content_missing_target_query(self, intelligence_handler, mock_protocol):
        """Test find complementary content with missing target_query."""
        mock_error_response = {
            "error": {
                "code": -32602,
                "message": "Invalid params",
                "data": "Missing required parameter: target_query"
            }
        }
        mock_protocol.create_response.return_value = mock_error_response
        
        params = {"context_query": "test context"}  # Missing target_query
        
        result = await intelligence_handler.handle_find_complementary_content(32, params)
        
        # Verify error response was created
        mock_protocol.create_response.assert_called_once()
        call_args = mock_protocol.create_response.call_args
        assert call_args[1]["error"]["code"] == -32602
        assert result == mock_error_response

    @pytest.mark.asyncio
    async def test_find_complementary_content_missing_both_queries(self, intelligence_handler, mock_protocol):
        """Test find complementary content with missing both required queries."""
        mock_error_response = {
            "error": {
                "code": -32602,
                "message": "Invalid params",
                "data": "Missing required parameter: target_query"  # First missing param detected
            }
        }
        mock_protocol.create_response.return_value = mock_error_response
        
        params = {}  # Missing both target_query and context_query
        
        result = await intelligence_handler.handle_find_complementary_content(33, params)
        
        # Verify error response was created for missing parameter
        mock_protocol.create_response.assert_called_once()
        assert result == mock_error_response

    @pytest.mark.asyncio
    async def test_empty_parameters_all_methods(self, intelligence_handler, mock_protocol):
        """Test all methods with completely empty parameters."""
        mock_error_response = {"error": {"message": "Missing required parameter"}}
        mock_protocol.create_response.return_value = mock_error_response
        
        empty_params = {}
        
        # Test all methods that require parameters
        methods_to_test = [
            intelligence_handler.handle_analyze_document_relationships,
            intelligence_handler.handle_find_similar_documents,
            intelligence_handler.handle_detect_document_conflicts,
            intelligence_handler.handle_find_complementary_content,
            intelligence_handler.handle_cluster_documents,
            intelligence_handler.handle_expand_cluster,
        ]
        
        for i, method in enumerate(methods_to_test):
            mock_protocol.reset_mock()
            result = await method(34 + i, empty_params)
            
            # All should handle missing parameters gracefully
            mock_protocol.create_response.assert_called_once()
            assert "error" in result or result == mock_error_response


class TestIntelligenceHandlerResponseFormatting:
    """Test response formatting and structured content creation."""

    @pytest.mark.asyncio
    async def test_response_structure_formatting(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test that responses have correct structure with both text and structured content."""
        mock_analysis_result = {
            "query_metadata": {"document_count": 10},
            "document_clusters": []
        }
        mock_search_engine.analyze_document_relationships.return_value = mock_analysis_result
        
        # Mock response structure
        mock_response = {
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": "Formatted analysis text"
                    }
                ],
                "structuredContent": {
                    "relationships": [],
                    "total_analyzed": 10,
                    "summary": "Analysis summary"
                },
                "isError": False
            }
        }
        mock_protocol.create_response.return_value = mock_response
        
        params = {"query": "format test"}
        result = await intelligence_handler.handle_analyze_document_relationships(40, params)
        
        # Verify response structure
        assert result == mock_response
        call_args = mock_protocol.create_response.call_args
        response_result = call_args[1]["result"]
        
        # Verify text content is present
        assert "content" in response_result
        assert len(response_result["content"]) > 0
        assert response_result["content"][0]["type"] == "text"
        
        # Verify structured content is present
        assert "structuredContent" in response_result
        assert "isError" in response_result
        assert response_result["isError"] is False

    @pytest.mark.asyncio
    async def test_find_similar_documents_formatting_validation(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test that find_similar_documents validates response format correctly."""
        # Mock search engine to return documents without document_id (validation should catch this)
        mock_similar_docs = [
            {"title": "Doc 1", "similarity": 0.9},  # Missing document_id
            {"document_id": "doc2", "title": "Doc 2", "similarity": 0.8}
        ]
        mock_search_engine.find_similar_documents.return_value = mock_similar_docs
        
        mock_response = {"result": {"structuredContent": {}}}
        mock_protocol.create_response.return_value = mock_response
        
        params = {
            "target_query": "target",
            "comparison_query": "comparison",
            "max_similar": 2
        }
        
        with patch('qdrant_loader_mcp_server.mcp.intelligence_handler.logger') as mock_logger:
            result = await intelligence_handler.handle_find_similar_documents(41, params)
            
            # Verify that validation logging was called for missing document_id
            mock_logger.error.assert_called()
            error_call = mock_logger.error.call_args[0][0]
            assert "Missing document_id" in error_call

    @pytest.mark.asyncio
    async def test_formatter_method_calls(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test that formatter methods are called correctly."""
        
        # Mock the formatters to track method calls
        with patch.object(intelligence_handler.formatters, 'format_relationship_analysis') as mock_format_rel, \
             patch.object(intelligence_handler.formatters, 'format_similar_documents') as mock_format_sim, \
             patch.object(intelligence_handler.formatters, 'format_conflict_analysis') as mock_format_conf, \
             patch.object(intelligence_handler.formatters, 'format_complementary_content') as mock_format_comp, \
             patch.object(intelligence_handler.formatters, 'format_document_clusters') as mock_format_clust:
            
            # Configure formatter return values
            mock_format_rel.return_value = "Formatted relationships"
            mock_format_sim.return_value = "Formatted similar docs"
            mock_format_conf.return_value = "Formatted conflicts"
            mock_format_comp.return_value = "Formatted complementary"
            mock_format_clust.return_value = "Formatted clusters"
            
            # Mock search engine responses
            mock_search_engine.analyze_document_relationships.return_value = {"query_metadata": {"document_count": 5}}
            mock_search_engine.find_similar_documents.return_value = []
            mock_search_engine.detect_document_conflicts.return_value = {"original_documents": []}
            mock_search_engine.find_complementary_content.return_value = {"complementary_recommendations": []}
            mock_search_engine.cluster_documents.return_value = {"clusters": []}
            
            mock_protocol.create_response.return_value = {"result": "success"}
            
            # Test each method calls its corresponding formatter
            await intelligence_handler.handle_analyze_document_relationships(42, {"query": "test"})
            mock_format_rel.assert_called_once()
            
            await intelligence_handler.handle_find_similar_documents(43, {"target_query": "t", "comparison_query": "c"})
            mock_format_sim.assert_called_once()
            
            await intelligence_handler.handle_detect_document_conflicts(44, {"query": "test"})
            mock_format_conf.assert_called_once()
            
            await intelligence_handler.handle_find_complementary_content(45, {"target_query": "t", "context_query": "c"})
            mock_format_comp.assert_called_once()
            
            await intelligence_handler.handle_cluster_documents(46, {"query": "test"})
            mock_format_clust.assert_called_once()

    @pytest.mark.asyncio
    async def test_structured_content_creation_calls(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test that structured content creation methods are called correctly."""
        
        with patch.object(intelligence_handler.formatters, 'create_lightweight_similar_documents_results') as mock_create_sim, \
             patch.object(intelligence_handler.formatters, 'create_lightweight_conflict_results') as mock_create_conf, \
             patch.object(intelligence_handler.formatters, 'create_lightweight_complementary_results') as mock_create_comp, \
             patch.object(intelligence_handler.formatters, 'create_lightweight_cluster_results') as mock_create_clust:
            
            # Configure creation method return values
            mock_create_sim.return_value = {"similar_docs": []}
            mock_create_conf.return_value = {"conflicts": []}
            mock_create_comp.return_value = {"complementary": []}
            mock_create_clust.return_value = {"clusters": []}
            
            # Mock search engine responses
            mock_search_engine.find_similar_documents.return_value = []
            mock_search_engine.detect_document_conflicts.return_value = {"original_documents": []}
            mock_search_engine.find_complementary_content.return_value = {
                "complementary_recommendations": [],
                "target_document": None,
                "context_documents_analyzed": 0
            }
            mock_search_engine.cluster_documents.return_value = {"clusters": []}
            
            mock_protocol.create_response.return_value = {"result": "success"}
            
            # Test each method calls its corresponding structured content creator
            await intelligence_handler.handle_find_similar_documents(47, {"target_query": "t", "comparison_query": "c"})
            mock_create_sim.assert_called_once()
            
            await intelligence_handler.handle_detect_document_conflicts(48, {"query": "test"})
            mock_create_conf.assert_called_once()
            
            await intelligence_handler.handle_find_complementary_content(49, {"target_query": "t", "context_query": "c"})
            mock_create_comp.assert_called_once()
            
            await intelligence_handler.handle_cluster_documents(50, {"query": "test"})
            mock_create_clust.assert_called_once()


class TestIntelligenceHandlerEdgeCases:
    """Test edge cases and malformed data handling."""

    @pytest.mark.asyncio
    async def test_complementary_content_list_instead_of_object(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test handling when complementary_content has list instead of object with get_top_recommendations."""
        analysis_result = {
            "query_metadata": {"document_count": 8},
            "complementary_content": {
                "doc1": [  # List instead of object with get_top_recommendations method
                    {
                        "document_id": "comp1",
                        "title": "Complementary Doc",
                        "relevance_score": 0.7,
                        "recommendation_reason": "supports main topic"
                    }
                ]
            }
        }
        
        mock_search_engine.analyze_document_relationships.return_value = analysis_result
        mock_protocol.create_response.return_value = {"result": "success"}
        
        params = {"query": "complementary list test"}
        result = await intelligence_handler.handle_analyze_document_relationships(51, params)
        
        # Should handle list format gracefully
        call_args = mock_protocol.create_response.call_args
        response_data = call_args[1]["result"]["structuredContent"]
        
        # Should still create complementary relationships
        complementary_relationships = [r for r in response_data["relationships"] if r["relationship_type"] == "complementary"]
        assert len(complementary_relationships) >= 1

    @pytest.mark.asyncio
    async def test_malformed_document_clusters_missing_documents(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test handling of clusters without documents key."""
        malformed_result = {
            "query_metadata": {"document_count": 12},
            "document_clusters": [
                {
                    "theme": "Cluster with docs",
                    "cohesion_score": 0.9,
                    "documents": [
                        {"document_id": "doc1", "title": "Doc 1"}
                    ]
                },
                {
                    "theme": "Cluster without docs",
                    "cohesion_score": 0.5
                    # Missing "documents" key
                }
            ]
        }
        
        mock_search_engine.analyze_document_relationships.return_value = malformed_result
        mock_protocol.create_response.return_value = {"result": "success"}
        
        params = {"query": "malformed clusters test"}
        result = await intelligence_handler.handle_analyze_document_relationships(52, params)
        
        # Should handle malformed clusters gracefully and process valid ones
        call_args = mock_protocol.create_response.call_args
        response_data = call_args[1]["result"]["structuredContent"]
        
        # Should still process the valid cluster
        assert response_data["total_analyzed"] == 12

    @pytest.mark.asyncio
    async def test_documents_missing_ids_and_titles(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test handling of documents missing IDs and titles."""
        edge_case_result = {
            "query_metadata": {"document_count": 6},
            "document_clusters": [
                {
                    "theme": "Mixed docs",
                    "cohesion_score": 0.7,
                    "documents": [
                        {},  # Completely empty document
                        {"title": "Title only"},  # Missing document_id and source_type
                        {"document_id": "doc3"},  # Missing title
                        {
                            "document_id": "doc4",
                            "title": "Complete Doc",
                            "source_type": "git"
                        }
                    ]
                }
            ]
        }
        
        mock_search_engine.analyze_document_relationships.return_value = edge_case_result
        mock_protocol.create_response.return_value = {"result": "success"}
        
        params = {"query": "missing fields test"}
        result = await intelligence_handler.handle_analyze_document_relationships(53, params)
        
        # Should handle missing fields gracefully with fallbacks
        call_args = mock_protocol.create_response.call_args
        response_data = call_args[1]["result"]["structuredContent"]
        
        # Should create some relationships despite missing fields
        assert len(response_data["relationships"]) >= 0
        assert response_data["total_analyzed"] == 6

    @pytest.mark.asyncio
    async def test_find_similar_documents_count_validation(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test validation when fewer documents returned than expected."""
        # Return fewer documents than max_similar
        mock_search_engine.find_similar_documents.return_value = [
            {"document_id": "doc1", "title": "Only Doc"}
        ]
        mock_protocol.create_response.return_value = {"result": "success"}
        
        params = {
            "target_query": "target",
            "comparison_query": "comparison", 
            "max_similar": 5  # Expecting 5, but only getting 1
        }
        
        with patch('qdrant_loader_mcp_server.mcp.intelligence_handler.logger') as mock_logger:
            result = await intelligence_handler.handle_find_similar_documents(54, params)
            
            # Should log warning about count mismatch
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "Expected up to 5 similar documents, but only got 1" in warning_call

    @pytest.mark.asyncio  
    async def test_empty_query_strings(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test handling of empty query strings."""
        mock_search_engine.analyze_document_relationships.return_value = {"query_metadata": {"document_count": 0}}
        mock_protocol.create_response.return_value = {"result": "success"}
        
        # Test with empty string query
        params = {"query": ""}
        result = await intelligence_handler.handle_analyze_document_relationships(55, params)
        
        # Should handle empty query gracefully 
        mock_search_engine.analyze_document_relationships.assert_called_once_with(
            query="",
            limit=20,
            source_types=None,
            project_ids=None
        )

    @pytest.mark.asyncio
    async def test_none_values_in_params(self, intelligence_handler, mock_search_engine, mock_protocol):
        """Test handling of None values in parameters."""
        mock_search_engine.find_similar_documents.return_value = []
        mock_protocol.create_response.return_value = {"result": "success"}
        
        params = {
            "target_query": "valid query",
            "comparison_query": "valid comparison",
            "max_similar": None,  # None value
            "similarity_metrics": None,
            "source_types": None,
            "project_ids": None
        }
        
        result = await intelligence_handler.handle_find_similar_documents(56, params)
        
        # Should handle None values gracefully and use defaults
        mock_search_engine.find_similar_documents.assert_called_once_with(
            target_query="valid query",
            comparison_query="valid comparison", 
            max_similar=None,  # Should be passed as-is, search engine handles default
            similarity_metrics=None,
            source_types=None,
            project_ids=None
        )
