"""
Real End-to-End Integration Tests for Cross-Document Intelligence

These tests exercise the complete real implementation path:
MCP Handler → SearchEngine → HybridSearchEngine → CrossDocumentIntelligenceEngine

This would have caught the import/attribute errors we encountered in production.
"""

import pytest
import pytest_asyncio
import asyncio
import time
import os
from unittest.mock import AsyncMock, MagicMock
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load test environment variables
load_dotenv('tests/.env.test')

from qdrant_loader_mcp_server.search.engine import SearchEngine
from qdrant_loader_mcp_server.search.hybrid_search import HybridSearchEngine
from qdrant_loader_mcp_server.search.components.search_result_models import HybridSearchResult, create_hybrid_search_result
from qdrant_loader_mcp_server.mcp.handler import MCPHandler
from qdrant_loader_mcp_server.search.processor import QueryProcessor
from qdrant_loader_mcp_server.config import QdrantConfig, OpenAIConfig

# Generic test data (no confidential client information)
def create_generic_test_documents() -> List[HybridSearchResult]:
    """Create generic test documents for cross-document intelligence testing."""
    return [
        create_hybrid_search_result(
            score=0.95,
            text="User authentication system implementation guide. Covers OAuth 2.0, JWT tokens, and session management for secure access control.",
            source_type="documentation",
            source_title="Authentication Implementation Guide",
            project_id="healthcare_platform",
            entities=[
                {"text": "OAuth", "label": "TECHNOLOGY"},
                {"text": "JWT", "label": "TECHNOLOGY"}
            ],
            topics=["authentication", "security", "implementation"],
            key_phrases=["user authentication", "OAuth 2.0", "JWT tokens"],
            content_type_context="technical_guide"
        ),
        create_hybrid_search_result(
            score=0.88,
            text="Security requirements for authentication systems. Includes password policies, multi-factor authentication, and compliance standards.",
            source_type="documentation",
            source_title="Authentication Security Requirements",
            project_id="healthcare_platform",
            entities=[
                {"text": "MFA", "label": "TECHNOLOGY"},
                {"text": "GDPR", "label": "REGULATION"}
            ],
            topics=["security", "authentication", "compliance"],
            key_phrases=["security requirements", "multi-factor authentication", "compliance"],
            content_type_context="requirements"
        ),
        create_hybrid_search_result(
            score=0.82,
            text="Database design patterns for healthcare applications. Covers data modeling, relationships, and performance optimization strategies.",
            source_type="documentation", 
            source_title="Database Design Patterns",
            project_id="healthcare_platform",
            entities=[
                {"text": "PostgreSQL", "label": "TECHNOLOGY"},
                {"text": "healthcare", "label": "DOMAIN"}
            ],
            topics=["database", "design", "healthcare"],
            key_phrases=["database design", "data modeling", "performance optimization"],
            content_type_context="technical_guide"
        ),
        create_hybrid_search_result(
            score=0.90,
            text="RESTful API design guidelines for healthcare platform. Authentication, rate limiting, and data validation best practices.",
            source_type="documentation",
            source_title="API Design Guidelines", 
            project_id="healthcare_platform",
            entities=[
                {"text": "REST", "label": "TECHNOLOGY"},
                {"text": "API", "label": "TECHNOLOGY"}
            ],
            topics=["api", "design", "authentication"],
            key_phrases=["RESTful API", "authentication", "rate limiting"],
            content_type_context="guidelines"
        ),
        create_hybrid_search_result(
            score=0.85,
            text="Mobile application requirements for patient engagement. User interface design, offline capabilities, and data synchronization.",
            source_type="requirements",
            source_title="Mobile Application Requirements",
            project_id="healthcare_platform", 
            entities=[
                {"text": "mobile", "label": "PLATFORM"},
                {"text": "patient", "label": "USER_TYPE"}
            ],
            topics=["mobile", "requirements", "patient_engagement"],
            key_phrases=["mobile application", "patient engagement", "offline capabilities"],
            content_type_context="requirements"
        )
    ]


class TestRealEndToEndPhase2_3:
    """Real end-to-end tests for Cross-Document Intelligence."""

    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a mock Qdrant client that returns our test documents."""
        mock_client = AsyncMock()
        
        # Mock search to return our test documents
        test_docs = create_generic_test_documents()
        mock_results = []
        for i, doc in enumerate(test_docs):
            mock_result = MagicMock()
            mock_result.id = f"doc_{i+1}"  # Create mock IDs for Qdrant results
            mock_result.score = doc.score
            mock_result.payload = {
                "content": doc.text,
                "entities": doc.entities if hasattr(doc, 'entities') else [],
                "topics": doc.topics if hasattr(doc, 'topics') else [],
                "key_phrases": doc.key_phrases if hasattr(doc, 'key_phrases') else [],
                "source_type": doc.source_type,
                "source_title": doc.source_title,
                "project_id": doc.project_id,
                "content_type_context": doc.content_type_context if hasattr(doc, 'content_type_context') else ""
            }
            mock_results.append(mock_result)
        
        # Mock search method
        mock_client.search.return_value = mock_results
        
        # Mock scroll method for BM25 keyword search (returns all documents for corpus)
        mock_scroll_results = []
        for i, doc in enumerate(test_docs):
            mock_point = MagicMock()
            mock_point.id = f"scroll_doc_{i+1}"
            mock_point.payload = {
                "content": doc.text,
                "metadata": {
                    "title": doc.source_title,
                    "source_type": doc.source_type
                },
                "source_type": doc.source_type
            }
            mock_scroll_results.append(mock_point)
        
        # scroll method returns tuple: (list_of_points, next_page_offset)
        mock_client.scroll.return_value = (mock_scroll_results, None)
        
        return mock_client

    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        mock_client = AsyncMock()
        
        # Mock embeddings
        embedding_response = MagicMock()
        embedding_data = MagicMock()
        embedding_data.embedding = [0.1] * 1536  # Standard OpenAI embedding size
        embedding_response.data = [embedding_data]
        mock_client.embeddings.create.return_value = embedding_response
        
        return mock_client

    @pytest_asyncio.fixture
    async def real_search_engine(self, mock_qdrant_client, mock_openai_client):
        """Create a REAL SearchEngine with only external dependencies mocked."""
        search_engine = SearchEngine()
        
        # Use test environment configuration
        qdrant_config = QdrantConfig(
            url=os.getenv('QDRANT_URL', 'http://localhost:6333'),
            api_key=os.getenv('QDRANT_API_KEY'),
            collection_name=os.getenv('QDRANT_COLLECTION_NAME', 'test_collection')
        )
        openai_config = OpenAIConfig(
            api_key=os.getenv('OPENAI_API_KEY', 'test_key')
        )
        
        # Initialize with test configuration
        await search_engine.initialize(qdrant_config, openai_config)
        
        # Replace only external dependencies with mocks, keep all internal logic real
        search_engine.hybrid_search.qdrant_client = mock_qdrant_client
        search_engine.hybrid_search.openai_client = mock_openai_client
        
        return search_engine

    @pytest_asyncio.fixture
    async def real_mcp_handler(self, real_search_engine):
        """Create a REAL MCP Handler with real SearchEngine."""
        openai_config = OpenAIConfig(
            api_key=os.getenv('OPENAI_API_KEY', 'test_key')
        )
        query_processor = QueryProcessor(openai_config)
        
        # Mock only the external OpenAI API
        query_processor.openai_client = AsyncMock()
        
        # Mock OpenAI chat completion for query processing
        chat_response = MagicMock()
        chat_choice = MagicMock()
        chat_message = MagicMock()
        chat_message.content = "general"
        chat_choice.message = chat_message
        chat_response.choices = [chat_choice]
        query_processor.openai_client.chat.completions.create.return_value = chat_response
        
        handler = MCPHandler(real_search_engine, query_processor)
        
        return handler

    @pytest.mark.asyncio
    async def test_real_find_similar_documents_integration(self, real_search_engine):
        """
        Test REAL find_similar_documents integration path.
        
        This would have caught:
        - Import errors (SimilarityMetric not defined)
        - Attribute errors (combined_score vs similarity_score)
        - Type mismatches (object vs dictionary returns)
        """
        # Test the REAL path: SearchEngine → HybridSearchEngine → CrossDocumentIntelligenceEngine
        similar_docs = await real_search_engine.find_similar_documents(
            target_query="authentication system implementation",
            comparison_query="security requirements",
            similarity_metrics=["entity_overlap", "topic_overlap", "semantic_similarity"],
            max_similar=3
        )
        
        # Validate the result structure (this would catch attribute errors)
        assert isinstance(similar_docs, list)
        
        if similar_docs:
            for doc_info in similar_docs:
                # These assertions would have caught our attribute errors
                assert "document" in doc_info
                assert "similarity_score" in doc_info  # Would catch combined_score error
                assert "metric_scores" in doc_info
                assert "similarity_reasons" in doc_info
                
                # Validate similarity score is a valid float
                assert isinstance(doc_info["similarity_score"], (int, float))
                assert 0 <= doc_info["similarity_score"] <= 1
                
                # Validate metric scores structure
                assert isinstance(doc_info["metric_scores"], dict)
                
                # Validate similarity reasons
                assert isinstance(doc_info["similarity_reasons"], list)

    @pytest.mark.asyncio
    async def test_real_cluster_documents_integration(self, real_search_engine):
        """
        Test REAL cluster_documents integration path.
        
        This would have caught:
        - Attribute errors (centroid_topics vs shared_topics)
        - Object structure mismatches
        """
        # Ensure enough test documents are returned by patching the search method
        from unittest.mock import patch
        test_docs = create_generic_test_documents()
        
        with patch.object(real_search_engine.hybrid_search, "search", return_value=test_docs):
            # Test the REAL path: SearchEngine → HybridSearchEngine → CrossDocumentIntelligenceEngine
            cluster_results = await real_search_engine.cluster_documents(
                query="healthcare platform documentation",
                strategy="mixed_features",
                max_clusters=3,
                min_cluster_size=2,
                limit=10
            )
            
            # Validate the result structure (this would catch attribute errors)
            assert isinstance(cluster_results, dict)
            assert "clusters" in cluster_results
            assert "clustering_metadata" in cluster_results
            
            # Validate clustering metadata
            metadata = cluster_results["clustering_metadata"]
            assert "strategy" in metadata
            assert "total_clusters" in metadata
            assert "total_documents" in metadata
            
            # Validate cluster structure (would catch centroid_topics error)
            clusters = cluster_results["clusters"]
            assert isinstance(clusters, list)
            
            for cluster in clusters:
                assert "id" in cluster
                assert "documents" in cluster
                assert "centroid_topics" in cluster  # Would catch attribute error
                assert "shared_entities" in cluster
                assert "coherence_score" in cluster
                assert "cluster_summary" in cluster  # Would catch attribute error
                
                # Validate data types
                assert isinstance(cluster["documents"], list)
                assert isinstance(cluster["centroid_topics"], list)
                assert isinstance(cluster["shared_entities"], list)
                assert isinstance(cluster["coherence_score"], (int, float))

    @pytest.mark.asyncio
    async def test_real_detect_conflicts_integration(self, real_search_engine):
        """
        Test REAL detect_document_conflicts integration path.
        
        This would have caught type conversion issues.
        """
        # Ensure enough test documents are returned by patching the search method
        from unittest.mock import patch
        test_docs = create_generic_test_documents()
        
        with patch.object(real_search_engine.hybrid_search, "search", return_value=test_docs):
            # Test the REAL path: SearchEngine → HybridSearchEngine → CrossDocumentIntelligenceEngine
            conflicts = await real_search_engine.detect_document_conflicts(
                query="authentication requirements",
                limit=8
            )
            
            # Validate the result structure (this would catch type conversion errors)
            assert isinstance(conflicts, dict)
            assert "conflicting_pairs" in conflicts
            assert "conflict_categories" in conflicts
            assert "resolution_suggestions" in conflicts
            
            # Validate data types
            assert isinstance(conflicts["conflicting_pairs"], list)
            assert isinstance(conflicts["conflict_categories"], dict)
            assert isinstance(conflicts["resolution_suggestions"], (dict, list))

    @pytest.mark.asyncio  
    async def test_real_mcp_handler_integration(self, real_mcp_handler):
        """
        Test REAL MCP Handler integration path.
        
        This would have caught:
        - All import/attribute errors in the full request flow
        - Response format issues
        - Type conversion problems
        """
        # Test find_similar_documents through REAL MCP path
        request = {
            "jsonrpc": "2.0",
            "method": "find_similar_documents",
            "params": {
                "target_query": "authentication implementation",
                "comparison_query": "security guidelines",
                "similarity_metrics": ["entity_overlap", "topic_overlap"],
                "max_similar": 3
            },
            "id": 1,
        }

        response = await real_mcp_handler.handle_request(request)
        
        # Validate MCP response structure
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["isError"] is False
        assert "content" in response["result"]
        
        # Test cluster_documents through REAL MCP path
        request = {
            "jsonrpc": "2.0", 
            "method": "cluster_documents",
            "params": {
                "query": "healthcare platform",
                "strategy": "mixed_features",
                "max_clusters": 3,
                "limit": 8
            },
            "id": 2,
        }

        response = await real_mcp_handler.handle_request(request)
        
        # Validate MCP response structure
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "result" in response
        assert response["result"]["isError"] is False

    @pytest.mark.asyncio
    async def test_data_structure_contracts(self, real_search_engine):
        """
        Test that our data structures have the expected attributes.
        
        This would have caught our attribute naming mismatches.
        """
        from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
            DocumentSimilarity, DocumentCluster, ConflictAnalysis, SimilarityMetric
        )
        
        # Test DocumentSimilarity contract
        similarity = DocumentSimilarity(
            doc1_id="test1",
            doc2_id="test2", 
            similarity_score=0.85
        )
        
        # These assertions would have caught our attribute errors
        assert hasattr(similarity, 'similarity_score')  # NOT combined_score
        assert hasattr(similarity, 'metric_scores')
        assert hasattr(similarity, 'get_display_explanation')  # For similarity_reasons
        
        # Test DocumentCluster contract
        cluster = DocumentCluster(
            cluster_id="test_cluster",
            name="Test Cluster"
        )
        
        # These assertions would have caught our attribute errors
        assert hasattr(cluster, 'shared_topics')  # NOT centroid_topics
        assert hasattr(cluster, 'shared_entities')
        assert hasattr(cluster, 'cluster_description')  # NOT cluster_summary
        assert hasattr(cluster, 'coherence_score')
        
        # Test ConflictAnalysis contract
        conflicts = ConflictAnalysis()
        assert hasattr(conflicts, 'conflicting_pairs')
        assert hasattr(conflicts, 'conflict_categories')
        assert hasattr(conflicts, 'resolution_suggestions')
        
        # Test SimilarityMetric enum exists and is importable
        assert SimilarityMetric.ENTITY_OVERLAP
        assert SimilarityMetric.TOPIC_OVERLAP
        assert SimilarityMetric.SEMANTIC_SIMILARITY

    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, real_search_engine):
        """Test that real integration performance meets expectations."""
        # Test find_similar_documents performance
        start_time = time.time()
        await real_search_engine.find_similar_documents(
            target_query="test query",
            comparison_query="test comparison",
            max_similar=3
        )
        find_similar_time = (time.time() - start_time) * 1000
        
        # Should complete in reasonable time
        assert find_similar_time < 5000, f"find_similar_documents took {find_similar_time:.2f}ms (target < 5000ms)"
        
        # Test cluster_documents performance
        start_time = time.time()
        await real_search_engine.cluster_documents(
            query="test clustering query",
            limit=5
        )
        clustering_time = (time.time() - start_time) * 1000
        
        # Should complete in reasonable time
        assert clustering_time < 3000, f"cluster_documents took {clustering_time:.2f}ms (target < 3000ms)"


if __name__ == "__main__":
    # Run specific test to debug issues
    pytest.main([__file__ + "::TestRealEndToEndPhase2_3::test_real_find_similar_documents_integration", "-v"]) 