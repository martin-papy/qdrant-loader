"""Unit tests for cross-document intelligence data classes."""

from datetime import datetime
import networkx as nx

from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
    DocumentSimilarity,
    DocumentCluster,
    CitationNetwork,
    ComplementaryContent,
    ConflictAnalysis,
    SimilarityMetric,
    ClusteringStrategy,
    RelationshipType
)


class TestDocumentSimilarity:
    """Test the DocumentSimilarity dataclass."""

    def test_document_similarity_creation(self):
        """Test creation of DocumentSimilarity with default values."""
        similarity = DocumentSimilarity(
            doc1_id="doc1",
            doc2_id="doc2",
            similarity_score=0.8
        )
        
        assert similarity.doc1_id == "doc1"
        assert similarity.doc2_id == "doc2"
        assert similarity.similarity_score == 0.8
        assert similarity.metric_scores == {}
        assert similarity.shared_entities == []
        assert similarity.shared_topics == []
        assert similarity.relationship_type == RelationshipType.SEMANTIC_SIMILARITY
        assert similarity.explanation == ""

    def test_document_similarity_with_all_fields(self):
        """Test DocumentSimilarity with all fields populated."""
        metric_scores = {
            SimilarityMetric.ENTITY_OVERLAP: 0.7,
            SimilarityMetric.TOPIC_OVERLAP: 0.6
        }
        
        similarity = DocumentSimilarity(
            doc1_id="doc1",
            doc2_id="doc2",
            similarity_score=0.75,
            metric_scores=metric_scores,
            shared_entities=["OAuth", "JWT"],
            shared_topics=["authentication", "security"],
            relationship_type=RelationshipType.COMPLEMENTARY,
            explanation="Both documents discuss OAuth implementation"
        )
        
        assert similarity.metric_scores == metric_scores
        assert similarity.shared_entities == ["OAuth", "JWT"]
        assert similarity.shared_topics == ["authentication", "security"]
        assert similarity.relationship_type == RelationshipType.COMPLEMENTARY
        assert similarity.explanation == "Both documents discuss OAuth implementation"

    def test_get_display_explanation_with_custom_explanation(self):
        """Test get_display_explanation returns custom explanation when provided."""
        similarity = DocumentSimilarity(
            doc1_id="doc1",
            doc2_id="doc2",
            similarity_score=0.8,
            explanation="Custom explanation"
        )
        
        assert similarity.get_display_explanation() == "Custom explanation"

    def test_get_display_explanation_with_entities_and_topics(self):
        """Test get_display_explanation generates explanation from entities and topics."""
        similarity = DocumentSimilarity(
            doc1_id="doc1",
            doc2_id="doc2",
            similarity_score=0.8,
            shared_entities=["OAuth", "JWT", "Token", "Refresh"],
            shared_topics=["authentication", "security", "authorization"]
        )
        
        explanation = similarity.get_display_explanation()
        assert "Shared entities: OAuth, JWT, Token" in explanation
        assert "Shared topics: authentication, security, authorization" in explanation

    def test_get_display_explanation_with_metric_scores(self):
        """Test get_display_explanation includes top metric score."""
        metric_scores = {
            SimilarityMetric.ENTITY_OVERLAP: 0.7,
            SimilarityMetric.TOPIC_OVERLAP: 0.9,
            SimilarityMetric.SEMANTIC_SIMILARITY: 0.6
        }
        
        similarity = DocumentSimilarity(
            doc1_id="doc1",
            doc2_id="doc2",
            similarity_score=0.8,
            metric_scores=metric_scores
        )
        
        explanation = similarity.get_display_explanation()
        assert "High topic_overlap: 0.90" in explanation

    def test_get_display_explanation_empty_fallback(self):
        """Test get_display_explanation fallback when no data available."""
        similarity = DocumentSimilarity(
            doc1_id="doc1",
            doc2_id="doc2",
            similarity_score=0.8
        )
        
        assert similarity.get_display_explanation() == "Semantic similarity"

    def test_get_display_explanation_partial_data(self):
        """Test get_display_explanation with partial data."""
        similarity = DocumentSimilarity(
            doc1_id="doc1",
            doc2_id="doc2",
            similarity_score=0.8,
            shared_entities=["OAuth"],
            metric_scores={SimilarityMetric.ENTITY_OVERLAP: 0.5}
        )
        
        explanation = similarity.get_display_explanation()
        assert "Shared entities: OAuth" in explanation
        assert "High entity_overlap: 0.50" in explanation


class TestDocumentCluster:
    """Test the DocumentCluster dataclass."""

    def test_document_cluster_creation(self):
        """Test creation of DocumentCluster with default values."""
        cluster = DocumentCluster(
            cluster_id="cluster_1",
            name="Test Cluster"
        )
        
        assert cluster.cluster_id == "cluster_1"
        assert cluster.name == "Test Cluster"
        assert cluster.documents == []
        assert cluster.shared_entities == []
        assert cluster.shared_topics == []
        assert cluster.cluster_strategy == ClusteringStrategy.MIXED_FEATURES
        assert cluster.coherence_score == 0.0
        assert cluster.representative_doc_id == ""
        assert cluster.cluster_description == ""

    def test_document_cluster_with_all_fields(self):
        """Test DocumentCluster with all fields populated."""
        cluster = DocumentCluster(
            cluster_id="cluster_2",
            name="Authentication Cluster",
            documents=["doc1", "doc2", "doc3"],
            shared_entities=["OAuth", "JWT"],
            shared_topics=["authentication", "security"],
            cluster_strategy=ClusteringStrategy.ENTITY_BASED,
            coherence_score=0.85,
            representative_doc_id="doc1",
            cluster_description="Documents about OAuth authentication"
        )
        
        assert cluster.documents == ["doc1", "doc2", "doc3"]
        assert cluster.shared_entities == ["OAuth", "JWT"]
        assert cluster.shared_topics == ["authentication", "security"]
        assert cluster.cluster_strategy == ClusteringStrategy.ENTITY_BASED
        assert cluster.coherence_score == 0.85
        assert cluster.representative_doc_id == "doc1"
        assert cluster.cluster_description == "Documents about OAuth authentication"

    def test_get_cluster_summary(self):
        """Test get_cluster_summary method."""
        cluster = DocumentCluster(
            cluster_id="cluster_3",
            name="Database Cluster",
            documents=["doc1", "doc2"],
            shared_entities=["PostgreSQL", "Schema", "Migration", "Index", "Query"],
            shared_topics=["database", "sql", "performance", "optimization"],
            cluster_strategy=ClusteringStrategy.TOPIC_BASED,
            coherence_score=0.92,
            cluster_description="Database design and optimization documents"
        )
        
        summary = cluster.get_cluster_summary()
        
        assert summary["cluster_id"] == "cluster_3"
        assert summary["name"] == "Database Cluster"
        assert summary["document_count"] == 2
        assert summary["coherence_score"] == 0.92
        assert summary["primary_entities"] == ["PostgreSQL", "Schema", "Migration", "Index", "Query"]
        assert summary["primary_topics"] == ["database", "sql", "performance", "optimization"]
        assert summary["strategy"] == "topic_based"
        assert summary["description"] == "Database design and optimization documents"

    def test_get_cluster_summary_with_many_entities_and_topics(self):
        """Test get_cluster_summary limits entities and topics to 5."""
        cluster = DocumentCluster(
            cluster_id="cluster_4",
            name="Large Cluster",
            documents=["doc1"],
            shared_entities=["E1", "E2", "E3", "E4", "E5", "E6", "E7"],
            shared_topics=["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"]
        )
        
        summary = cluster.get_cluster_summary()
        
        assert len(summary["primary_entities"]) == 5
        assert summary["primary_entities"] == ["E1", "E2", "E3", "E4", "E5"]
        assert len(summary["primary_topics"]) == 5
        assert summary["primary_topics"] == ["T1", "T2", "T3", "T4", "T5"]

    def test_get_cluster_summary_empty_cluster(self):
        """Test get_cluster_summary with empty cluster."""
        cluster = DocumentCluster(
            cluster_id="empty_cluster",
            name="Empty"
        )
        
        summary = cluster.get_cluster_summary()
        
        assert summary["document_count"] == 0
        assert summary["primary_entities"] == []
        assert summary["primary_topics"] == []


class TestCitationNetwork:
    """Test the CitationNetwork dataclass."""

    def test_citation_network_creation(self):
        """Test creation of CitationNetwork with default values."""
        network = CitationNetwork()
        
        assert network.nodes == {}
        assert network.edges == []
        assert network.graph is None
        assert network.authority_scores == {}
        assert network.hub_scores == {}
        assert network.pagerank_scores == {}

    def test_citation_network_with_data(self):
        """Test CitationNetwork with initial data."""
        nodes = {"doc1": {"title": "Document 1"}, "doc2": {"title": "Document 2"}}
        edges = [("doc1", "doc2", {"weight": 1.0})]
        
        network = CitationNetwork(
            nodes=nodes,
            edges=edges
        )
        
        assert network.nodes == nodes
        assert network.edges == edges

    def test_build_graph(self):
        """Test building NetworkX graph from nodes and edges."""
        network = CitationNetwork(
            nodes={"doc1": {"title": "Doc 1"}, "doc2": {"title": "Doc 2"}},
            edges=[("doc1", "doc2", {"weight": 1.0})]
        )
        
        graph = network.build_graph()
        
        assert isinstance(graph, nx.DiGraph)
        assert "doc1" in graph.nodes
        assert "doc2" in graph.nodes
        assert graph.has_edge("doc1", "doc2")
        assert graph["doc1"]["doc2"]["weight"] == 1.0
        assert graph.nodes["doc1"]["title"] == "Doc 1"

    def test_build_graph_caching(self):
        """Test that build_graph caches the graph object."""
        network = CitationNetwork(
            nodes={"doc1": {"title": "Doc 1"}},
            edges=[]
        )
        
        graph1 = network.build_graph()
        graph2 = network.build_graph()
        
        assert graph1 is graph2  # Same object reference

    def test_calculate_centrality_scores_empty_graph(self):
        """Test centrality calculation with empty graph."""
        network = CitationNetwork()
        network.calculate_centrality_scores()
        
        # Should handle empty graph gracefully
        assert network.authority_scores == {}
        assert network.hub_scores == {}
        assert network.pagerank_scores == {}

    def test_calculate_centrality_scores_no_edges(self):
        """Test centrality calculation with nodes but no edges."""
        network = CitationNetwork(
            nodes={"doc1": {}, "doc2": {}},
            edges=[]
        )
        
        network.calculate_centrality_scores()
        
        # Should use degree centrality fallback
        assert "doc1" in network.authority_scores
        assert "doc2" in network.authority_scores
        assert all(score == 0.0 for score in network.authority_scores.values())

    def test_calculate_centrality_scores_with_edges(self):
        """Test centrality calculation with actual edges."""
        network = CitationNetwork(
            nodes={"doc1": {}, "doc2": {}, "doc3": {}},
            edges=[("doc1", "doc2", {}), ("doc2", "doc3", {}), ("doc1", "doc3", {})]
        )
        
        network.calculate_centrality_scores()
        
        assert len(network.authority_scores) == 3
        assert len(network.hub_scores) == 3
        assert len(network.pagerank_scores) == 3
        
        # Basic sanity checks
        assert all(isinstance(score, (int, float)) for score in network.authority_scores.values())
        assert all(score >= 0 for score in network.pagerank_scores.values())

    def test_calculate_centrality_scores_error_handling(self):
        """Test centrality calculation error handling."""
        # Create a problematic graph that might cause computation issues
        network = CitationNetwork(
            nodes={"doc1": {}},
            # Include at least one edge so nx.hits and nx.pagerank are invoked
            edges=[("doc1", "doc1", {})]
        )
        
        # Mock the networkx functions to raise an exception
        original_hits = nx.hits
        original_pagerank = nx.pagerank
        
        def mock_hits(*args, **kwargs):
            raise ValueError("Test error")
            
        def mock_pagerank(*args, **kwargs):
            raise ValueError("Test error")
        
        try:
            nx.hits = mock_hits
            nx.pagerank = mock_pagerank
            
            network.calculate_centrality_scores()
            
            # Should fall back to degree centrality
            assert "doc1" in network.authority_scores
            assert "doc1" in network.hub_scores
            assert "doc1" in network.pagerank_scores
            # For single nodes, degree centrality returns 1 (normalized)
            assert network.authority_scores["doc1"] >= 0.0
            assert network.hub_scores["doc1"] >= 0.0
            assert network.pagerank_scores["doc1"] >= 0.0
            
        finally:
            nx.hits = original_hits
            nx.pagerank = original_pagerank


class TestComplementaryContent:
    """Test the ComplementaryContent dataclass."""

    def test_complementary_content_creation(self):
        """Test creation of ComplementaryContent."""
        content = ComplementaryContent(target_doc_id="doc1")
        
        assert content.target_doc_id == "doc1"
        assert content.recommendations == []
        assert content.recommendation_strategy == "mixed"
        assert isinstance(content.generated_at, datetime)

    def test_complementary_content_with_recommendations(self):
        """Test ComplementaryContent with recommendations."""
        recommendations = [
            ("doc2", 0.8, "Similar topic"),
            ("doc3", 0.7, "Complementary approach"),
            ("doc4", 0.6, "Related technology")
        ]
        
        content = ComplementaryContent(
            target_doc_id="doc1",
            recommendations=recommendations,
            recommendation_strategy="entity_based"
        )
        
        assert content.recommendations == recommendations
        assert content.recommendation_strategy == "entity_based"

    def test_get_top_recommendations(self):
        """Test get_top_recommendations method."""
        recommendations = [
            ("doc2", 0.9, "High similarity"),
            ("doc3", 0.7, "Medium similarity"),
            ("doc4", 0.8, "Good match"),
            ("doc5", 0.6, "Low similarity"),
            ("doc6", 0.75, "Decent match")
        ]
        
        content = ComplementaryContent(
            target_doc_id="doc1",
            recommendations=recommendations
        )
        
        top_3 = content.get_top_recommendations(3)
        
        assert len(top_3) == 3
        assert top_3[0]["document_id"] == "doc2"
        assert top_3[0]["relevance_score"] == 0.9
        assert top_3[0]["recommendation_reason"] == "High similarity"
        assert top_3[0]["strategy"] == "mixed"
        
        assert top_3[1]["document_id"] == "doc4"  # Second highest score
        assert top_3[1]["relevance_score"] == 0.8

    def test_get_top_recommendations_empty(self):
        """Test get_top_recommendations with empty recommendations."""
        content = ComplementaryContent(target_doc_id="doc1")
        
        top_recs = content.get_top_recommendations(5)
        
        assert top_recs == []

    def test_get_top_recommendations_fewer_than_limit(self):
        """Test get_top_recommendations when fewer recommendations than limit."""
        recommendations = [("doc2", 0.8, "Good match")]
        content = ComplementaryContent(
            target_doc_id="doc1",
            recommendations=recommendations
        )
        
        top_5 = content.get_top_recommendations(5)
        
        assert len(top_5) == 1
        assert top_5[0]["document_id"] == "doc2"


class TestConflictAnalysis:
    """Test the ConflictAnalysis dataclass."""

    def test_conflict_analysis_creation(self):
        """Test creation of ConflictAnalysis."""
        analysis = ConflictAnalysis()
        
        assert analysis.conflicting_pairs == []
        assert analysis.conflict_categories == {}
        assert analysis.resolution_suggestions == {}

    def test_conflict_analysis_with_data(self):
        """Test ConflictAnalysis with conflict data."""
        conflicting_pairs = [
            ("doc1", "doc2", {"type": "version", "confidence": 0.8}),
            ("doc1", "doc3", {"type": "procedural", "confidence": 0.7})
        ]
        
        conflict_categories = {
            "version": [("doc1", "doc2")],
            "procedural": [("doc1", "doc3")]
        }
        
        resolution_suggestions = {
            "version": "Update to latest version",
            "procedural": "Clarify procedure steps"
        }
        
        analysis = ConflictAnalysis(
            conflicting_pairs=conflicting_pairs,
            conflict_categories=conflict_categories,
            resolution_suggestions=resolution_suggestions
        )
        
        assert analysis.conflicting_pairs == conflicting_pairs
        assert analysis.conflict_categories == conflict_categories
        assert analysis.resolution_suggestions == resolution_suggestions

    def test_get_conflict_summary(self):
        """Test get_conflict_summary method."""
        conflicting_pairs = [
            ("doc1", "doc2", {"type": "version"}),
            ("doc1", "doc3", {"type": "procedural"}),
            ("doc2", "doc4", {"type": "version"})
        ]
        
        conflict_categories = {
            "version": [("doc1", "doc2"), ("doc2", "doc4")],
            "procedural": [("doc1", "doc3")]
        }
        
        resolution_suggestions = {
            "1": "First suggestion",
            "2": "Second suggestion",
            "3": "Third suggestion",
            "4": "Fourth suggestion"
        }
        
        analysis = ConflictAnalysis(
            conflicting_pairs=conflicting_pairs,
            conflict_categories=conflict_categories,
            resolution_suggestions=resolution_suggestions
        )
        
        summary = analysis.get_conflict_summary()
        
        assert summary["total_conflicts"] == 3
        assert summary["conflict_categories"]["version"] == 2
        assert summary["conflict_categories"]["procedural"] == 1
        assert summary["most_common_conflicts"] == ["version", "procedural"]
        assert len(summary["resolution_suggestions"]) == 3  # Limited to 3

    def test_get_most_common_conflicts(self):
        """Test _get_most_common_conflicts method."""
        conflict_categories = {
            "procedural": [("doc1", "doc2")],
            "version": [("doc1", "doc3"), ("doc2", "doc4"), ("doc3", "doc5")],
            "data": [("doc1", "doc4"), ("doc2", "doc5")]
        }
        
        analysis = ConflictAnalysis(conflict_categories=conflict_categories)
        
        most_common = analysis._get_most_common_conflicts()
        
        assert most_common == ["version", "data", "procedural"]  # Sorted by frequency

    def test_get_conflict_summary_empty(self):
        """Test get_conflict_summary with empty analysis."""
        analysis = ConflictAnalysis()
        
        summary = analysis.get_conflict_summary()
        
        assert summary["total_conflicts"] == 0
        assert summary["conflict_categories"] == {}
        assert summary["most_common_conflicts"] == []
        assert summary["resolution_suggestions"] == []
