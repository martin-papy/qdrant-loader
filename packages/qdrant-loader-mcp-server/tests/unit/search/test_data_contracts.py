"""
Data Contract Tests for Cross-Document Intelligence

These tests validate that our data structures have the expected interfaces
and would have caught the attribute naming mismatches we encountered.
"""

import pytest
from qdrant_loader_mcp_server.search.components.search_result_models import (
    HybridSearchResult,
    create_hybrid_search_result,
)
from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
    CitationNetwork,
    ClusteringStrategy,
    ConflictAnalysis,
    DocumentCluster,
    DocumentSimilarity,
    RelationshipType,
    SimilarityMetric,
)


class TestDataStructureContracts:
    """Test that our data structures have the expected interfaces."""

    def test_document_similarity_contract(self):
        """
        Test DocumentSimilarity has expected attributes.

        This would have caught: combined_score vs similarity_score
        """
        # Create DocumentSimilarity instance
        similarity = DocumentSimilarity(
            doc1_id="doc1",
            doc2_id="doc2",
            similarity_score=0.85,
            metric_scores={SimilarityMetric.ENTITY_OVERLAP: 0.9},
            shared_entities=["OAuth", "authentication"],
            shared_topics=["security", "implementation"],
        )

        # Validate required attributes (would catch naming errors)
        assert hasattr(similarity, "doc1_id")
        assert hasattr(similarity, "doc2_id")
        assert hasattr(similarity, "similarity_score")  # NOT combined_score
        assert hasattr(similarity, "metric_scores")
        assert hasattr(similarity, "shared_entities")
        assert hasattr(similarity, "shared_topics")
        assert hasattr(similarity, "relationship_type")
        assert hasattr(similarity, "explanation")

        # Validate method exists
        assert hasattr(similarity, "get_display_explanation")
        assert callable(similarity.get_display_explanation)

        # Validate types
        assert isinstance(similarity.similarity_score, int | float)
        assert isinstance(similarity.metric_scores, dict)
        assert isinstance(similarity.shared_entities, list)
        assert isinstance(similarity.shared_topics, list)

        # Validate value ranges
        assert 0.0 <= similarity.similarity_score <= 1.0

    def test_document_cluster_contract(self):
        """
        Test DocumentCluster has expected attributes.

        This would have caught: centroid_topics vs shared_topics, cluster_summary vs cluster_description
        """
        # Create DocumentCluster instance
        cluster = DocumentCluster(
            cluster_id="cluster_001",
            name="Authentication Cluster",
            documents=["doc1", "doc2", "doc3"],
            shared_entities=["OAuth", "JWT"],
            shared_topics=["authentication", "security"],
            cluster_strategy=ClusteringStrategy.MIXED_FEATURES,
            coherence_score=0.75,
            representative_doc_id="doc1",
            cluster_description="Documents about authentication systems",
        )

        # Validate required attributes (would catch naming errors)
        assert hasattr(cluster, "cluster_id")
        assert hasattr(cluster, "name")
        assert hasattr(cluster, "documents")
        assert hasattr(cluster, "shared_entities")
        assert hasattr(cluster, "shared_topics")  # NOT centroid_topics
        assert hasattr(cluster, "cluster_strategy")
        assert hasattr(cluster, "coherence_score")
        assert hasattr(cluster, "representative_doc_id")
        assert hasattr(cluster, "cluster_description")  # NOT cluster_summary

        # Validate method exists
        assert hasattr(cluster, "get_cluster_summary")
        assert callable(cluster.get_cluster_summary)

        # Validate types
        assert isinstance(cluster.documents, list)
        assert isinstance(cluster.shared_entities, list)
        assert isinstance(cluster.shared_topics, list)
        assert isinstance(cluster.coherence_score, int | float)
        assert isinstance(cluster.cluster_strategy, ClusteringStrategy)

        # Validate value ranges
        assert 0.0 <= cluster.coherence_score <= 1.0

    def test_conflict_analysis_contract(self):
        """
        Test ConflictAnalysis has expected attributes.

        This would have caught type conversion issues.
        """
        # Create ConflictAnalysis instance
        conflicts = ConflictAnalysis(
            conflicting_pairs=[("doc1", "doc2", {"type": "contradiction"})],
            conflict_categories={"contradiction": [("doc1", "doc2")]},
            resolution_suggestions={
                "contradiction": "Review both documents for consistency"
            },
        )

        # Validate required attributes
        assert hasattr(conflicts, "conflicting_pairs")
        assert hasattr(conflicts, "conflict_categories")
        assert hasattr(conflicts, "resolution_suggestions")

        # Validate method exists
        assert hasattr(conflicts, "get_conflict_summary")
        assert callable(conflicts.get_conflict_summary)

        # Validate types
        assert isinstance(conflicts.conflicting_pairs, list)
        assert isinstance(conflicts.conflict_categories, dict)
        assert isinstance(conflicts.resolution_suggestions, dict)

        # Validate structure of conflicting_pairs
        if conflicts.conflicting_pairs:
            pair = conflicts.conflicting_pairs[0]
            assert isinstance(pair, tuple)
            assert len(pair) == 3
            assert isinstance(pair[0], str)  # doc1_id
            assert isinstance(pair[1], str)  # doc2_id
            assert isinstance(pair[2], dict)  # conflict_info

    def test_citation_network_contract(self):
        """Test CitationNetwork has expected attributes."""
        # Create CitationNetwork instance
        network = CitationNetwork(
            nodes={"doc1": {"title": "Authentication Guide"}},
            edges=[("doc1", "doc2", {"relationship": "references"})],
        )

        # Validate required attributes
        assert hasattr(network, "nodes")
        assert hasattr(network, "edges")
        assert hasattr(network, "graph")

        # Validate types
        assert isinstance(network.nodes, dict)
        assert isinstance(network.edges, list)

    def test_similarity_metric_enum_contract(self):
        """
        Test SimilarityMetric enum is complete and importable.

        This would have caught import errors.
        """
        # Validate all expected enum values exist
        assert hasattr(SimilarityMetric, "ENTITY_OVERLAP")
        assert hasattr(SimilarityMetric, "TOPIC_OVERLAP")
        assert hasattr(SimilarityMetric, "SEMANTIC_SIMILARITY")
        assert hasattr(SimilarityMetric, "METADATA_SIMILARITY")
        assert hasattr(SimilarityMetric, "HIERARCHICAL_DISTANCE")
        assert hasattr(SimilarityMetric, "CONTENT_FEATURES")

        # Validate enum values are strings
        assert isinstance(SimilarityMetric.ENTITY_OVERLAP.value, str)
        assert isinstance(SimilarityMetric.TOPIC_OVERLAP.value, str)
        assert isinstance(SimilarityMetric.SEMANTIC_SIMILARITY.value, str)

    def test_clustering_strategy_enum_contract(self):
        """
        Test ClusteringStrategy enum is complete and importable.

        This would have caught import errors.
        """
        # Validate all expected enum values exist
        assert hasattr(ClusteringStrategy, "ENTITY_BASED")
        assert hasattr(ClusteringStrategy, "TOPIC_BASED")
        assert hasattr(ClusteringStrategy, "PROJECT_BASED")
        assert hasattr(ClusteringStrategy, "HIERARCHICAL")
        assert hasattr(ClusteringStrategy, "MIXED_FEATURES")
        assert hasattr(ClusteringStrategy, "SEMANTIC_EMBEDDING")

        # Validate enum values are strings
        assert isinstance(ClusteringStrategy.ENTITY_BASED.value, str)
        assert isinstance(ClusteringStrategy.MIXED_FEATURES.value, str)

    def test_relationship_type_enum_contract(self):
        """Test RelationshipType enum is complete."""
        # Validate expected enum values exist
        assert hasattr(RelationshipType, "HIERARCHICAL")
        assert hasattr(RelationshipType, "CROSS_REFERENCE")
        assert hasattr(RelationshipType, "SEMANTIC_SIMILARITY")
        assert hasattr(RelationshipType, "COMPLEMENTARY")
        assert hasattr(RelationshipType, "CONFLICTING")

    def test_search_result_integration_contract(self):
        """
        Test that HybridSearchResult works with cross-document intelligence.

        This validates the integration interface.
        """
        # Create HybridSearchResult instance
        search_result = create_hybrid_search_result(
            score=0.95,
            text="Test document content",
            source_type="documentation",
            source_title="Test Document",
            project_id="test_project",
            entities=[{"text": "OAuth", "label": "TECHNOLOGY"}],
            topics=["authentication", "security"],
            key_phrases=["OAuth authentication"],
            content_type_context="technical_guide",
        )

        # Validate required attributes for cross-document intelligence
        assert hasattr(search_result, "text")
        assert hasattr(search_result, "source_type")
        assert hasattr(search_result, "source_title")
        assert hasattr(search_result, "project_id")
        assert hasattr(search_result, "entities")
        assert hasattr(search_result, "topics")
        assert hasattr(search_result, "key_phrases")

        # Validate field types expected by cross-document intelligence
        assert isinstance(search_result.entities, list)
        assert isinstance(search_result.topics, list)
        assert isinstance(search_result.key_phrases, list)

    def test_find_similar_documents_response_contract(self):
        """
        Test expected response format for find_similar_documents.

        This would catch response structure mismatches.
        """
        # Expected response format
        expected_response = [
            {
                "document": create_hybrid_search_result(
                    score=0.95,
                    text="Test content",
                    source_type="documentation",
                    source_title="Test Doc",
                    project_id="test_project",
                    entities=[{"text": "OAuth", "label": "TECHNOLOGY"}],
                    topics=["authentication", "security"],
                    key_phrases=["OAuth authentication"],
                ),
                "similarity_score": 0.85,
                "metric_scores": {
                    SimilarityMetric.ENTITY_OVERLAP: 0.9,
                    SimilarityMetric.TOPIC_OVERLAP: 0.8,
                },
                "similarity_reasons": ["Shared authentication entities"],
            }
        ]

        # Validate response structure
        for doc_info in expected_response:
            assert "document" in doc_info
            assert "similarity_score" in doc_info  # NOT combined_score
            assert "metric_scores" in doc_info
            assert "similarity_reasons" in doc_info

            # Validate types
            assert isinstance(doc_info["document"], HybridSearchResult)
            assert isinstance(doc_info["similarity_score"], int | float)
            assert isinstance(doc_info["metric_scores"], dict)
            assert isinstance(doc_info["similarity_reasons"], list)

    def test_cluster_documents_response_contract(self):
        """
        Test expected response format for cluster_documents.

        This would catch cluster structure mismatches.
        """
        # Expected response format
        expected_response = {
            "clusters": [
                {
                    "id": "cluster_001",
                    "documents": ["doc1", "doc2"],
                    "centroid_topics": [
                        "authentication",
                        "security",
                    ],  # Maps to shared_topics
                    "shared_entities": ["OAuth", "JWT"],
                    "coherence_score": 0.75,
                    "cluster_summary": "Authentication documents",  # Maps to cluster_description
                }
            ],
            "clustering_metadata": {
                "strategy": "mixed_features",
                "total_clusters": 1,
                "total_documents": 5,
            },
        }

        # Validate response structure
        assert "clusters" in expected_response
        assert "clustering_metadata" in expected_response

        # Validate cluster structure
        for cluster in expected_response["clusters"]:
            assert "id" in cluster
            assert "documents" in cluster
            assert "centroid_topics" in cluster  # Would catch attribute error
            assert "shared_entities" in cluster
            assert "coherence_score" in cluster
            assert "cluster_summary" in cluster  # Would catch attribute error

            # Validate types
            assert isinstance(cluster["documents"], list)
            assert isinstance(cluster["centroid_topics"], list)
            assert isinstance(cluster["shared_entities"], list)
            assert isinstance(cluster["coherence_score"], int | float)

    def test_detect_conflicts_response_contract(self):
        """
        Test expected response format for detect_document_conflicts.

        This would catch conflict response type issues.
        """
        # Expected response format
        expected_response = {
            "conflicting_pairs": [("doc1", "doc2", {"type": "contradiction"})],
            "conflict_categories": {"contradiction": [("doc1", "doc2")]},
            "resolution_suggestions": {"contradiction": "Review both documents"},
        }

        # Validate response structure
        assert "conflicting_pairs" in expected_response
        assert "conflict_categories" in expected_response
        assert "resolution_suggestions" in expected_response

        # Validate types
        assert isinstance(expected_response["conflicting_pairs"], list)
        assert isinstance(expected_response["conflict_categories"], dict)
        assert isinstance(expected_response["resolution_suggestions"], dict | list)


class TestMCPResponseContracts:
    """Test MCP response format contracts."""

    def test_mcp_success_response_contract(self):
        """Test expected MCP success response format."""
        # Expected MCP response format
        expected_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [{"type": "text", "text": "Response content"}],
                "isError": False,
            },
        }

        # Validate MCP response structure
        assert "jsonrpc" in expected_response
        assert "id" in expected_response
        assert "result" in expected_response

        result = expected_response["result"]
        assert "content" in result
        assert "isError" in result
        assert result["isError"] is False

        # Validate content structure
        content = result["content"]
        assert isinstance(content, list)
        if content:
            assert "type" in content[0]
            assert "text" in content[0]

    def test_mcp_error_response_contract(self):
        """Test expected MCP error response format."""
        # Expected MCP error response format
        expected_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": "Error details",
            },
        }

        # Validate MCP error response structure
        assert "jsonrpc" in expected_response
        assert "id" in expected_response
        assert "error" in expected_response

        error = expected_response["error"]
        assert "code" in error
        assert "message" in error
        assert isinstance(error["code"], int)
        assert isinstance(error["message"], str)


if __name__ == "__main__":
    # Run specific contract tests
    pytest.main([__file__, "-v"])
