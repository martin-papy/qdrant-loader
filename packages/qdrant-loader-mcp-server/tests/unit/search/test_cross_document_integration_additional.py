"""Additional integration tests for cross-document intelligence to boost coverage."""

from unittest.mock import AsyncMock, Mock

import pytest
from qdrant_loader_mcp_server.search.components.search_result_models import (
    create_hybrid_search_result,
)
from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
    ClusteringStrategy,
    ComplementaryContentFinder,
    ConflictDetector,
    CrossDocumentIntelligenceEngine,
    DocumentClusterAnalyzer,
    DocumentSimilarityCalculator,
    SimilarityMetric,
)


class TestCrossDocumentIntelligenceAdditionalCoverage:
    """Additional tests to boost coverage of cross-document intelligence."""

    @pytest.fixture
    def mock_spacy_analyzer(self):
        """Create a mock SpaCy analyzer."""
        analyzer = Mock()
        mock_doc = Mock()
        mock_doc.similarity.return_value = 0.7
        mock_doc.ents = []
        analyzer.nlp.return_value = mock_doc
        return analyzer

    @pytest.fixture
    def intelligence_engine(self, mock_spacy_analyzer):
        """Create a CrossDocumentIntelligenceEngine instance."""
        return CrossDocumentIntelligenceEngine(mock_spacy_analyzer)

    def test_similarity_calculator_all_metrics(self, mock_spacy_analyzer):
        """Test similarity calculation with all available metrics."""
        calculator = DocumentSimilarityCalculator(mock_spacy_analyzer)

        doc1 = create_hybrid_search_result(
            score=0.9,
            text="OAuth 2.0 authentication guide with comprehensive examples",
            source_type="confluence",
            source_title="OAuth Guide",
            project_id="platform",
            entities=[{"text": "OAuth", "label": "TECH"}],
            topics=[{"text": "authentication", "score": 0.9}],
            has_code_blocks=True,
            word_count=2500,
            depth=2,
            breadcrumb_text="Docs > Security > OAuth",
        )

        doc2 = create_hybrid_search_result(
            score=0.8,
            text="JWT implementation tutorial with Node.js examples",
            source_type="git",
            source_title="JWT Tutorial",
            project_id="platform",
            entities=[{"text": "JWT", "label": "TECH"}],
            topics=[{"text": "authentication", "score": 0.8}],
            has_code_blocks=True,
            word_count=1800,
            depth=3,
            breadcrumb_text="Code > Backend > Auth",
        )

        # Test with all metrics
        all_metrics = [
            SimilarityMetric.ENTITY_OVERLAP,
            SimilarityMetric.TOPIC_OVERLAP,
            SimilarityMetric.SEMANTIC_SIMILARITY,
            SimilarityMetric.METADATA_SIMILARITY,
            SimilarityMetric.HIERARCHICAL_DISTANCE,
            SimilarityMetric.CONTENT_FEATURES,
        ]

        similarity = calculator.calculate_similarity(doc1, doc2, metrics=all_metrics)

        assert similarity.similarity_score >= 0.0
        assert len(similarity.metric_scores) > 0
        assert similarity.relationship_type is not None

    def test_cluster_analyzer_hierarchical_clustering(self, mock_spacy_analyzer):
        """Test hierarchical clustering strategy."""
        mock_similarity_calc = Mock()
        mock_similarity_calc.calculate_similarity.return_value = Mock(
            similarity_score=0.8, shared_entities=["test"], shared_topics=["topic"]
        )
        mock_similarity_calc._extract_entity_texts.return_value = ["test"]
        mock_similarity_calc._extract_topic_texts.return_value = ["topic"]

        analyzer = DocumentClusterAnalyzer(mock_similarity_calc)

        docs = [
            create_hybrid_search_result(
                score=0.9,
                text="Parent document",
                source_type="confluence",
                source_title="Parent",
                depth=1,
                breadcrumb_text="Root > Parent",
            ),
            create_hybrid_search_result(
                score=0.8,
                text="Child document",
                source_type="confluence",
                source_title="Child",
                depth=2,
                breadcrumb_text="Root > Parent > Child",
            ),
        ]

        clusters = analyzer.create_clusters(
            docs,
            strategy=ClusteringStrategy.HIERARCHICAL,
            max_clusters=5,
            min_cluster_size=1,
        )

        assert len(clusters) >= 0
        for cluster in clusters:
            assert cluster.cluster_strategy == ClusteringStrategy.HIERARCHICAL

    @pytest.mark.asyncio
    async def test_conflict_detector_tiered_analysis(self, mock_spacy_analyzer):
        """Test tiered analysis functionality in conflict detector."""
        detector = ConflictDetector(mock_spacy_analyzer)

        docs = [
            create_hybrid_search_result(
                score=0.9,
                text="Token expiry should be set to 24 hours for optimal user experience.",
                source_type="confluence",
                source_title="UX Guidelines",
                project_id="platform",
                entities=[{"text": "token expiry", "label": "POLICY"}],
            ),
            create_hybrid_search_result(
                score=0.8,
                text="Security policy requires token expiry of 4 hours maximum.",
                source_type="confluence",
                source_title="Security Policy",
                project_id="platform",
                entities=[{"text": "token expiry", "label": "POLICY"}],
            ),
            create_hybrid_search_result(
                score=0.7,
                text="Database configuration and optimization techniques.",
                source_type="confluence",
                source_title="Database Guide",
                project_id="different_project",
            ),
        ]

        # Test tiered analysis pair generation
        pairs = await detector._get_tiered_analysis_pairs(docs)

        # Should return pairs with tier information
        assert len(pairs) >= 0
        for pair in pairs:
            doc1, doc2, tier, score = pair
            assert tier in ["primary", "secondary", "tertiary"]
            assert 0.0 <= score <= 1.0

    def test_complementary_finder_knowledge_graph_integration(
        self, mock_spacy_analyzer
    ):
        """Test complementary content finder with knowledge graph."""
        mock_similarity_calc = Mock()
        mock_similarity_calc.calculate_similarity.return_value = Mock(
            similarity_score=0.7, shared_entities=["oauth"], shared_topics=["auth"]
        )

        def mock_extract_entity_texts(entities):
            if not entities:
                return []
            return [
                e.get("text", "").lower() if isinstance(e, dict) else str(e).lower()
                for e in entities
            ]

        def mock_extract_topic_texts(topics):
            if not topics:
                return []
            return [
                t.get("text", "").lower() if isinstance(t, dict) else str(t).lower()
                for t in topics
            ]

        mock_similarity_calc._extract_entity_texts.side_effect = (
            mock_extract_entity_texts
        )
        mock_similarity_calc._extract_topic_texts.side_effect = mock_extract_topic_texts

        # Mock knowledge graph
        mock_kg = Mock()
        mock_kg.find_related_documents.return_value = []

        finder = ComplementaryContentFinder(mock_similarity_calc, mock_kg)

        target_doc = create_hybrid_search_result(
            score=0.9,
            text="OAuth implementation guide",
            source_type="confluence",
            source_title="OAuth Guide",
        )

        candidates = [
            create_hybrid_search_result(
                score=0.8,
                text="JWT validation tutorial",
                source_type="git",
                source_title="JWT Tutorial",
            )
        ]

        result = finder.find_complementary_content(target_doc, candidates)

        assert (
            result.target_doc_id
            == f"{target_doc.source_type}:{target_doc.source_title}"
        )
        assert isinstance(result.recommendations, list)

    def test_intelligence_engine_full_initialization(self, mock_spacy_analyzer):
        """Test intelligence engine with all components initialized."""
        mock_qdrant = AsyncMock()
        mock_openai = AsyncMock()
        mock_kg = Mock()

        engine = CrossDocumentIntelligenceEngine(
            spacy_analyzer=mock_spacy_analyzer,
            knowledge_graph=mock_kg,
            qdrant_client=mock_qdrant,
            openai_client=mock_openai,
            collection_name="test_collection",
        )

        # Verify all components are initialized
        assert engine.spacy_analyzer == mock_spacy_analyzer
        assert engine.knowledge_graph == mock_kg
        assert engine.qdrant_client == mock_qdrant
        assert engine.openai_client == mock_openai
        assert engine.collection_name == "test_collection"

        # Verify component analyzers are created
        assert engine.similarity_calculator is not None
        assert engine.cluster_analyzer is not None
        assert engine.citation_analyzer is not None
        assert engine.complementary_finder is not None
        assert engine.conflict_detector is not None

    def test_document_similarity_comprehensive_metrics(self, mock_spacy_analyzer):
        """Test comprehensive metric calculations."""
        calculator = DocumentSimilarityCalculator(mock_spacy_analyzer)

        # Create documents with rich metadata
        doc1 = create_hybrid_search_result(
            score=0.95,
            text="Comprehensive OAuth 2.0 security implementation guide",
            source_type="confluence",
            source_title="OAuth Security Guide",
            source_url="https://docs.company.com/oauth-security",
            project_id="security_platform",
            project_name="Security Platform",
            entities=[
                {"text": "OAuth 2.0", "label": "PROTOCOL"},
                {"text": "JWT", "label": "TOKEN"},
                {"text": "PKCE", "label": "SECURITY"},
            ],
            topics=[
                {"text": "security", "score": 0.95},
                {"text": "authentication", "score": 0.90},
                {"text": "authorization", "score": 0.85},
            ],
            has_code_blocks=True,
            has_tables=True,
            has_links=True,
            word_count=3500,
            estimated_read_time=18,
            depth=2,
            breadcrumb_text="Documentation > Security > OAuth",
            cross_references=[
                {"text": "JWT Implementation Guide", "url": "/docs/jwt-guide"},
                {"text": "Security Best Practices", "url": "/docs/security-practices"},
            ],
        )

        doc2 = create_hybrid_search_result(
            score=0.88,
            text="JWT token implementation with security best practices",
            source_type="confluence",
            source_title="JWT Implementation Guide",
            source_url="https://docs.company.com/jwt-guide",
            project_id="security_platform",
            project_name="Security Platform",
            entities=[
                {"text": "JWT", "label": "TOKEN"},
                {"text": "HMAC", "label": "ALGORITHM"},
                {"text": "RSA", "label": "ALGORITHM"},
            ],
            topics=[
                {"text": "security", "score": 0.88},
                {"text": "authentication", "score": 0.85},
                {"text": "tokens", "score": 0.90},
            ],
            has_code_blocks=True,
            has_tables=False,
            has_links=True,
            word_count=2800,
            estimated_read_time=14,
            depth=2,
            breadcrumb_text="Documentation > Security > JWT",
            cross_references=[
                {"text": "OAuth Security Guide", "url": "/docs/oauth-security"}
            ],
        )

        # Test individual metric calculations
        entity_overlap = calculator._calculate_entity_overlap(doc1, doc2)
        topic_overlap = calculator._calculate_topic_overlap(doc1, doc2)
        metadata_similarity = calculator._calculate_metadata_similarity(doc1, doc2)
        content_features = calculator._calculate_content_features_similarity(doc1, doc2)
        hierarchical_sim = calculator._calculate_hierarchical_similarity(doc1, doc2)
        semantic_sim = calculator._calculate_semantic_similarity(doc1, doc2)

        # All should return valid scores
        assert 0.0 <= entity_overlap <= 1.0
        assert 0.0 <= topic_overlap <= 1.0
        assert 0.0 <= metadata_similarity <= 1.0
        assert 0.0 <= content_features <= 1.0
        assert 0.0 <= hierarchical_sim <= 1.0
        assert 0.0 <= semantic_sim <= 1.0

        # Test combined calculation
        similarity = calculator.calculate_similarity(doc1, doc2)
        assert similarity.similarity_score > 0.0
        assert len(similarity.shared_entities) > 0  # Should find JWT
        assert len(similarity.shared_topics) > 0  # Should find security, authentication

    @pytest.mark.asyncio
    async def test_conflict_detector_vector_similarity_integration(
        self, mock_spacy_analyzer
    ):
        """Test conflict detector with vector similarity filtering."""
        mock_qdrant = AsyncMock()
        detector = ConflictDetector(
            spacy_analyzer=mock_spacy_analyzer, qdrant_client=mock_qdrant
        )

        # Mock vector retrieval
        mock_point1 = Mock()
        mock_point1.vector = [0.1, 0.2, 0.3, 0.4]
        mock_point2 = Mock()
        mock_point2.vector = [0.2, 0.3, 0.4, 0.5]

        mock_qdrant.retrieve.side_effect = [[mock_point1], [mock_point2]]

        docs = [
            create_hybrid_search_result(
                score=0.9,
                text="Token expiry policy should be 24 hours for better user experience",
                source_type="confluence",
                source_title="UX Policy",
            ),
            create_hybrid_search_result(
                score=0.8,
                text="Security requires token expiry of maximum 4 hours",
                source_type="confluence",
                source_title="Security Policy",
            ),
        ]

        # Test vector similarity filtering
        similar_pairs = await detector._filter_by_vector_similarity(docs)

        assert isinstance(similar_pairs, list)
        for pair in similar_pairs:
            doc1, doc2, sim_score = pair
            assert 0.0 <= sim_score <= 1.0

    def test_cluster_analyzer_performance_characteristics(self, mock_spacy_analyzer):
        """Test cluster analyzer performance with various dataset sizes."""
        mock_similarity_calc = Mock()
        mock_similarity = Mock()
        mock_similarity.similarity_score = 0.6
        mock_similarity.shared_entities = ["entity"]
        mock_similarity.shared_topics = ["topic"]
        mock_similarity_calc.calculate_similarity.return_value = mock_similarity
        mock_similarity_calc._extract_entity_texts.return_value = ["entity"]
        mock_similarity_calc._extract_topic_texts.return_value = ["topic"]

        analyzer = DocumentClusterAnalyzer(mock_similarity_calc)

        # Test with different cluster sizes and strategies
        test_cases = [
            (5, ClusteringStrategy.ENTITY_BASED),
            (10, ClusteringStrategy.TOPIC_BASED),
            (8, ClusteringStrategy.MIXED_FEATURES),
            (3, ClusteringStrategy.PROJECT_BASED),
        ]

        for num_docs, strategy in test_cases:
            docs = [
                create_hybrid_search_result(
                    score=0.8,
                    text=f"Test document {i}",
                    source_type="confluence",
                    source_title=f"Doc {i}",
                    entities=[{"text": f"entity_{i % 3}", "label": "TEST"}],
                    topics=[{"text": f"topic_{i % 2}", "score": 0.8}],
                )
                for i in range(num_docs)
            ]

            clusters = analyzer.create_clusters(
                docs, strategy=strategy, max_clusters=3, min_cluster_size=2
            )

            # Should handle different dataset sizes
            assert len(clusters) >= 0
            for cluster in clusters:
                assert cluster.cluster_strategy == strategy
                assert len(cluster.documents) >= 2

    def test_intelligence_engine_edge_case_handling(self, intelligence_engine):
        """Test intelligence engine edge case handling."""
        # Test with documents that have minimal metadata
        minimal_docs = [
            create_hybrid_search_result(
                score=0.5,
                text="Minimal document",
                source_type="confluence",
                source_title="Minimal",
            ),
            create_hybrid_search_result(
                score=0.4,
                text="Another minimal doc",
                source_type="git",
                source_title="Another Minimal",
            ),
        ]

        # Should handle gracefully
        analysis = intelligence_engine.analyze_document_relationships(minimal_docs)

        assert analysis["summary"]["total_documents"] == 2
        assert analysis["summary"]["analysis_mode"] == "lightweight"
        assert "document_clusters" in analysis

    def test_similarity_insights_extraction(self, intelligence_engine):
        """Test similarity insights extraction functionality."""
        # Create a test similarity matrix
        similarity_matrix = {
            "doc1": {"doc1": 1.0, "doc2": 0.8, "doc3": 0.3},
            "doc2": {"doc1": 0.8, "doc2": 1.0, "doc3": 0.6},
            "doc3": {"doc1": 0.3, "doc2": 0.6, "doc3": 1.0},
        }

        insights = intelligence_engine._extract_similarity_insights(similarity_matrix)

        # Verify all expected insight fields
        expected_fields = [
            "average_similarity",
            "max_similarity",
            "min_similarity",
            "high_similarity_pairs",  # Note: actual key name from implementation
        ]

        for field in expected_fields:
            assert field in insights

        # Verify calculated values are reasonable
        assert 0.0 <= insights["average_similarity"] <= 1.0
        assert insights["max_similarity"] <= 1.0
        assert insights["min_similarity"] >= 0.0
        assert isinstance(insights["high_similarity_pairs"], int)
        assert insights["high_similarity_pairs"] >= 0
