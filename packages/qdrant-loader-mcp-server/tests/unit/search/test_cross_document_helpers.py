"""Unit tests for cross-document intelligence helper methods and private functions."""

import json
from unittest.mock import AsyncMock, Mock

import pytest
from qdrant_loader_mcp_server.search.components.search_result_models import (
    create_hybrid_search_result,
)
from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
    ClusteringStrategy,
    ComplementaryContentFinder,
    ConflictDetector,
    DocumentClusterAnalyzer,
    DocumentSimilarityCalculator,
)


class TestDocumentSimilarityCalculatorHelpers:
    """Test helper methods in DocumentSimilarityCalculator."""

    @pytest.fixture
    def mock_spacy_analyzer(self):
        """Create a mock SpaCy analyzer."""
        analyzer = Mock()
        mock_doc = Mock()
        mock_doc.similarity.return_value = 0.75
        analyzer.nlp.return_value = mock_doc
        return analyzer

    @pytest.fixture
    def similarity_calculator(self, mock_spacy_analyzer):
        """Create a DocumentSimilarityCalculator instance."""
        return DocumentSimilarityCalculator(mock_spacy_analyzer)

    def test_calculate_content_features_similarity(self, similarity_calculator):
        """Test content features similarity calculation."""
        doc1 = create_hybrid_search_result(
            score=0.9,
            text="This is a comprehensive technical document",
            source_type="confluence",
            source_title="Technical Guide",
            has_code_blocks=True,
            has_tables=True,
            word_count=2500,
            estimated_read_time=12,
        )

        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Another detailed technical reference",
            source_type="confluence",
            source_title="Technical Reference",
            has_code_blocks=True,
            has_tables=False,
            word_count=2800,
            estimated_read_time=14,
        )

        similarity = similarity_calculator._calculate_content_features_similarity(
            doc1, doc2
        )

        assert 0.0 <= similarity <= 1.0
        assert similarity > 0.0  # Should have some similarity due to similar features

    def test_calculate_content_features_similarity_different_features(
        self, similarity_calculator
    ):
        """Test content features similarity with very different features."""
        doc1 = create_hybrid_search_result(
            score=0.9,
            text="Short note",
            source_type="confluence",
            source_title="Quick Note",
            has_code_blocks=False,
            has_tables=False,
            word_count=100,
            estimated_read_time=1,
        )

        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Comprehensive technical documentation",
            source_type="git",
            source_title="Technical Documentation",
            has_code_blocks=True,
            has_tables=True,
            word_count=5000,
            estimated_read_time=25,
        )

        similarity = similarity_calculator._calculate_content_features_similarity(
            doc1, doc2
        )

        assert 0.0 <= similarity <= 1.0
        # Should have lower similarity due to very different features

    def test_calculate_content_features_similarity_none_values(
        self, similarity_calculator
    ):
        """Test content features similarity with None values."""
        doc1 = create_hybrid_search_result(
            score=0.9,
            text="Test document",
            source_type="confluence",
            source_title="Test Doc",
            has_code_blocks=None,
            has_tables=None,
            word_count=None,
            estimated_read_time=None,
        )

        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Another test",
            source_type="confluence",
            source_title="Another Test",
            has_code_blocks=None,
            has_tables=None,
            word_count=None,
            estimated_read_time=None,
        )

        similarity = similarity_calculator._calculate_content_features_similarity(
            doc1, doc2
        )

        # Should handle None values gracefully
        assert 0.0 <= similarity <= 1.0

    def test_calculate_hierarchical_similarity(self, similarity_calculator):
        """Test hierarchical similarity calculation."""
        # Parent-child relationship
        parent_doc = create_hybrid_search_result(
            score=0.9,
            text="Parent document",
            source_type="confluence",
            source_title="Parent Document",
            depth=1,
            breadcrumb_text="Root > Parent",
        )

        child_doc = create_hybrid_search_result(
            score=0.8,
            text="Child document",
            source_type="confluence",
            source_title="Child Document",
            depth=2,
            breadcrumb_text="Root > Parent > Child",
            parent_id="confluence:Parent Document",
        )

        similarity = similarity_calculator._calculate_hierarchical_similarity(
            parent_doc, child_doc
        )

        assert similarity > 0.7  # Should be high for parent-child relationship

    def test_calculate_hierarchical_similarity_siblings(self, similarity_calculator):
        """Test hierarchical similarity for sibling documents."""
        sibling1 = create_hybrid_search_result(
            score=0.9,
            text="First sibling",
            source_type="confluence",
            source_title="Sibling 1",
            depth=2,
            breadcrumb_text="Root > Parent > Sibling 1",
        )

        sibling2 = create_hybrid_search_result(
            score=0.8,
            text="Second sibling",
            source_type="confluence",
            source_title="Sibling 2",
            depth=2,
            breadcrumb_text="Root > Parent > Sibling 2",
        )

        similarity = similarity_calculator._calculate_hierarchical_similarity(
            sibling1, sibling2
        )

        assert similarity > 0.5  # Should have moderate similarity for siblings

    def test_calculate_hierarchical_similarity_unrelated(self, similarity_calculator):
        """Test hierarchical similarity for unrelated documents."""
        doc1 = create_hybrid_search_result(
            score=0.9,
            text="Document one",
            source_type="confluence",
            source_title="Doc 1",
            depth=1,
            breadcrumb_text="Path A > Doc 1",
        )

        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Document two",
            source_type="git",
            source_title="Doc 2",
            depth=3,
            breadcrumb_text="Path B > Sub > Doc 2",
        )

        similarity = similarity_calculator._calculate_hierarchical_similarity(
            doc1, doc2
        )

        assert similarity == 0.0  # Should be 0 for unrelated documents


class TestDocumentClusterAnalyzerHelpers:
    """Test helper methods in DocumentClusterAnalyzer."""

    @pytest.fixture
    def mock_similarity_calculator(self):
        """Create a mock similarity calculator."""
        calc = Mock()
        mock_similarity = Mock()
        mock_similarity.similarity_score = 0.8
        mock_similarity.shared_entities = ["test"]
        mock_similarity.shared_topics = ["topic"]
        calc.calculate_similarity.return_value = mock_similarity
        calc._extract_entity_texts.return_value = ["test"]
        calc._extract_topic_texts.return_value = ["topic"]
        return calc

    @pytest.fixture
    def cluster_analyzer(self, mock_similarity_calculator):
        """Create a DocumentClusterAnalyzer instance."""
        return DocumentClusterAnalyzer(mock_similarity_calculator)

    def test_generate_primary_theme_entity_based(self, cluster_analyzer):
        """Test primary theme generation for entity-based clusters."""
        from collections import Counter

        from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
            DocumentCluster,
        )

        cluster = DocumentCluster(
            cluster_id="test",
            name="Test",
            shared_entities=["OAuth", "JWT"],
            cluster_strategy=ClusteringStrategy.ENTITY_BASED,
        )

        theme = cluster_analyzer._generate_primary_theme(cluster, [], Counter())

        assert "OAuth" in theme and "JWT" in theme
        assert "Documents focused on" in theme

    def test_generate_primary_theme_topic_based(self, cluster_analyzer):
        """Test primary theme generation for topic-based clusters."""
        from collections import Counter

        from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
            DocumentCluster,
        )

        cluster = DocumentCluster(
            cluster_id="test",
            name="Test",
            shared_topics=["authentication", "security"],
            cluster_strategy=ClusteringStrategy.TOPIC_BASED,
        )

        theme = cluster_analyzer._generate_primary_theme(cluster, [], Counter())

        assert "authentication" in theme.lower() and "security" in theme.lower()
        assert "Content about" in theme

    def test_generate_primary_theme_project_based(self, cluster_analyzer):
        """Test primary theme generation for project-based clusters."""
        from collections import Counter

        from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
            DocumentCluster,
        )

        cluster = DocumentCluster(
            cluster_id="test",
            name="Test",
            cluster_strategy=ClusteringStrategy.PROJECT_BASED,
        )

        source_types = Counter({"confluence": 3, "git": 2})
        theme = cluster_analyzer._generate_primary_theme(cluster, [], source_types)

        assert "Project documents from confluence sources" in theme

    def test_generate_primary_theme_content_based(self, cluster_analyzer):
        """Test primary theme generation based on content words."""
        from collections import Counter

        from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
            DocumentCluster,
        )

        cluster = DocumentCluster(
            cluster_id="test",
            name="Test",
            cluster_strategy=ClusteringStrategy.MIXED_FEATURES,
        )

        common_words = ["authentication", "security"]
        theme = cluster_analyzer._generate_primary_theme(
            cluster, common_words, Counter()
        )

        assert "Authentication" in theme and "Security" in theme
        assert "Documents about" in theme

    def test_generate_primary_theme_fallback(self, cluster_analyzer):
        """Test primary theme generation fallback scenarios."""
        from collections import Counter

        from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
            DocumentCluster,
        )

        # Empty cluster with no identifying features
        cluster = DocumentCluster(
            cluster_id="test",
            name="Test",
            cluster_strategy=ClusteringStrategy.MIXED_FEATURES,
        )

        theme = cluster_analyzer._generate_primary_theme(cluster, [], Counter())

        assert theme == "Related document collection"

    def test_generate_document_insights(self, cluster_analyzer):
        """Test document insights generation."""
        from collections import Counter

        cluster_docs = [
            create_hybrid_search_result(
                score=0.9,
                text="Test document one",
                source_type="confluence",
                source_title="Doc 1",
            ),
            create_hybrid_search_result(
                score=0.8,
                text="Test document two",
                source_type="git",
                source_title="Doc 2",
            ),
            create_hybrid_search_result(
                score=0.7,
                text="Test document three",
                source_type="confluence",
                source_title="Doc 3",
            ),
        ]

        source_types = Counter({"confluence": 2, "git": 1})

        insights = cluster_analyzer._generate_document_insights(
            cluster_docs, source_types
        )

        assert isinstance(insights, str)
        assert len(insights) > 0
        # Should mention document count and source distribution
        assert "3" in insights  # Document count
        assert "confluence" in insights.lower() or "git" in insights.lower()


class TestConflictDetectorHelpers:
    """Test helper methods in ConflictDetector."""

    @pytest.fixture
    def mock_spacy_analyzer(self):
        """Create a mock SpaCy analyzer."""
        analyzer = Mock()
        mock_doc = Mock()
        mock_doc.similarity.return_value = 0.6
        mock_doc.ents = []
        analyzer.nlp.return_value = mock_doc
        return analyzer

    @pytest.fixture
    def conflict_detector(self, mock_spacy_analyzer):
        """Create a ConflictDetector instance."""
        return ConflictDetector(mock_spacy_analyzer)

    def test_have_content_overlap(self, conflict_detector):
        """Test content overlap detection."""
        doc1 = create_hybrid_search_result(
            score=0.9,
            text="OAuth authentication implementation guide with JWT tokens",
            source_type="confluence",
            source_title="OAuth Guide",
        )

        doc2 = create_hybrid_search_result(
            score=0.8,
            text="JWT token implementation and OAuth best practices",
            source_type="confluence",
            source_title="JWT Guide",
        )

        has_overlap = conflict_detector._have_content_overlap(doc1, doc2)

        assert has_overlap is True

        # Test documents with no overlap
        doc3 = create_hybrid_search_result(
            score=0.8,
            text="Database schema design and optimization techniques",
            source_type="confluence",
            source_title="Database Guide",
        )

        no_overlap = conflict_detector._have_content_overlap(doc1, doc3)

        assert no_overlap is False

    def test_have_semantic_similarity(self, conflict_detector):
        """Test semantic similarity detection."""
        doc1 = create_hybrid_search_result(
            score=0.9,
            text="User authentication and login security",
            source_type="confluence",
            source_title="Authentication Security",
        )

        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Secure user access and authentication methods",
            source_type="confluence",
            source_title="Secure Access Methods",
        )

        has_similarity = conflict_detector._have_semantic_similarity(doc1, doc2)

        assert has_similarity is True

        # Test documents with different topics
        doc3 = create_hybrid_search_result(
            score=0.8,
            text="Coffee brewing techniques and recipes",
            source_type="confluence",
            source_title="Coffee Guide",
        )

        no_similarity = conflict_detector._have_semantic_similarity(doc1, doc3)

        assert no_similarity is False

    def test_describe_conflict(self, conflict_detector):
        """Test conflict description generation."""
        indicators = [
            "version conflict",
            "incompatible versions",
            "different requirements",
        ]

        description = conflict_detector._describe_conflict(indicators)

        assert isinstance(description, str)
        assert len(description) > 0
        assert (
            "version" in description.lower()
            or "incompatible" in description.lower()
            or "different" in description.lower()
        )

    def test_generate_resolution_suggestions(self, conflict_detector):
        """Test resolution suggestions generation."""
        from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
            ConflictAnalysis,
        )

        conflicts = ConflictAnalysis(
            conflict_categories={
                "version": [("doc1", "doc2")],
                "procedural": [("doc1", "doc3")],
                "data": [("doc2", "doc3")],
            }
        )

        suggestions = conflict_detector._generate_resolution_suggestions(conflicts)

        assert isinstance(suggestions, dict)
        assert len(suggestions) > 0

        # Should have suggestions for different conflict types
        for suggestion in suggestions.values():
            assert isinstance(suggestion, str)
            assert len(suggestion) > 0

    @pytest.mark.asyncio
    async def test_get_document_embeddings_no_client(self, conflict_detector):
        """Test getting document embeddings when no Qdrant client is available."""
        conflict_detector.qdrant_client = None

        embeddings = await conflict_detector._get_document_embeddings(["doc1", "doc2"])

        assert embeddings == {}  # Should return empty dict when no client

    @pytest.mark.asyncio
    async def test_get_document_embeddings_with_client(self, conflict_detector):
        """Test getting document embeddings with Qdrant client."""
        mock_client = AsyncMock()
        mock_point = Mock()
        mock_point.vector = [0.1, 0.2, 0.3]
        mock_client.retrieve.return_value = [mock_point]
        conflict_detector.qdrant_client = mock_client

        embeddings = await conflict_detector._get_document_embeddings(["doc1"])

        assert "doc1" in embeddings
        assert embeddings["doc1"] == [0.1, 0.2, 0.3]

    def test_calculate_vector_similarity(self, conflict_detector):
        """Test vector similarity calculation."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]  # Identical vectors

        similarity = conflict_detector._calculate_vector_similarity(vec1, vec2)

        assert abs(similarity - 1.0) < 0.001  # Should be very close to 1.0

        # Test orthogonal vectors
        vec3 = [0.0, 1.0, 0.0]
        similarity2 = conflict_detector._calculate_vector_similarity(vec1, vec3)

        assert abs(similarity2) < 0.001  # Should be close to 0.0

    def test_calculate_vector_similarity_edge_cases(self, conflict_detector):
        """Test vector similarity calculation edge cases."""
        # Empty vectors
        empty_vec = []
        result = conflict_detector._calculate_vector_similarity(empty_vec, empty_vec)
        assert result == 0.0

        # Zero vectors
        zero_vec = [0.0, 0.0, 0.0]
        result2 = conflict_detector._calculate_vector_similarity(zero_vec, zero_vec)
        assert result2 == 0.0

        # Different length vectors
        vec1 = [1.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        result3 = conflict_detector._calculate_vector_similarity(vec1, vec2)
        assert result3 == 0.0  # Should handle gracefully

    @pytest.mark.asyncio
    async def test_llm_analyze_conflicts_json_parsing(self, conflict_detector):
        """Test LLM conflict analysis JSON parsing scenarios."""
        mock_client = AsyncMock()
        conflict_detector.openai_client = mock_client

        # Test valid JSON response
        valid_json_response = {
            "has_conflicts": True,
            "conflicts": [
                {
                    "type": "version",
                    "explanation": "Version mismatch detected",
                    "confidence": 0.8,
                    "doc1_snippet": "version 1.0",
                    "doc2_snippet": "version 2.0",
                }
            ],
        }

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(valid_json_response)
        mock_client.chat.completions.create.return_value = mock_response

        doc1 = create_hybrid_search_result(
            score=0.9,
            text="Version 1.0 requirements",
            source_type="confluence",
            source_title="Doc 1",
        )

        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Version 2.0 implementation",
            source_type="confluence",
            source_title="Doc 2",
        )

        result = await conflict_detector._llm_analyze_conflicts(doc1, doc2, 0.8)

        assert result is not None
        assert result["type"] == "version"
        assert result["confidence"] == 0.8

    @pytest.mark.asyncio
    async def test_llm_analyze_conflicts_malformed_json(self, conflict_detector):
        """Test LLM conflict analysis with malformed JSON."""
        mock_client = AsyncMock()
        conflict_detector.openai_client = mock_client

        # Test malformed JSON with extractable content
        malformed_response = 'Some text before {"has_conflicts": true, "conflicts": [{"type": "test"}]} some text after'

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = malformed_response
        mock_client.chat.completions.create.return_value = mock_response

        doc1 = create_hybrid_search_result(
            score=0.9,
            text="Test document",
            source_type="confluence",
            source_title="Doc 1",
        )

        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Another document",
            source_type="confluence",
            source_title="Doc 2",
        )

        result = await conflict_detector._llm_analyze_conflicts(doc1, doc2, 0.8)

        assert result is not None  # Should extract JSON from malformed response
        assert "type" in result

    @pytest.mark.asyncio
    async def test_llm_analyze_conflicts_no_conflicts(self, conflict_detector):
        """Test LLM conflict analysis when no conflicts are found."""
        mock_client = AsyncMock()
        conflict_detector.openai_client = mock_client

        no_conflict_response = {"has_conflicts": False, "conflicts": []}

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(no_conflict_response)
        mock_client.chat.completions.create.return_value = mock_response

        doc1 = create_hybrid_search_result(
            score=0.9,
            text="Consistent information",
            source_type="confluence",
            source_title="Doc 1",
        )

        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Also consistent information",
            source_type="confluence",
            source_title="Doc 2",
        )

        result = await conflict_detector._llm_analyze_conflicts(doc1, doc2, 0.8)

        assert result is None  # Should return None when no conflicts


class TestComplementaryContentFinderHelpers:
    """Test helper methods in ComplementaryContentFinder."""

    @pytest.fixture
    def mock_similarity_calculator(self):
        """Create a mock similarity calculator."""
        calc = Mock()
        mock_similarity = Mock()
        mock_similarity.similarity_score = 0.7
        calc.calculate_similarity.return_value = mock_similarity
        calc._extract_entity_texts.return_value = ["test"]
        calc._extract_topic_texts.return_value = ["topic"]
        return calc

    @pytest.fixture
    def complementary_finder(self, mock_similarity_calculator):
        """Create a ComplementaryContentFinder instance."""
        return ComplementaryContentFinder(mock_similarity_calculator)

    def test_has_shared_technologies(self, complementary_finder):
        """Test detection of shared technologies."""
        doc1 = create_hybrid_search_result(
            score=0.9,
            text="React and Node.js application development",
            source_type="confluence",
            source_title="React Guide",
            entities=[
                {"text": "React", "label": "TECH"},
                {"text": "Node.js", "label": "TECH"},
            ],
        )

        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Node.js backend with Express framework",
            source_type="git",
            source_title="Backend Guide",
            entities=[
                {"text": "Node.js", "label": "TECH"},
                {"text": "Express", "label": "TECH"},
            ],
        )

        has_shared = complementary_finder._has_shared_technologies(doc1, doc2)

        assert has_shared is True

        # Test with no shared technologies
        doc3 = create_hybrid_search_result(
            score=0.8,
            text="Python Django framework",
            source_type="git",
            source_title="Django Guide",
            entities=[
                {"text": "Python", "label": "TECH"},
                {"text": "Django", "label": "TECH"},
            ],
        )

        no_shared = complementary_finder._has_shared_technologies(doc1, doc3)

        assert no_shared is False

    def test_get_shared_technologies_count(self, complementary_finder):
        """Test counting shared technologies."""
        doc1 = create_hybrid_search_result(
            score=0.9,
            text="React, Node.js, and MongoDB development",
            source_type="confluence",
            source_title="Full Stack Guide",
            entities=[
                {"text": "React", "label": "TECH"},
                {"text": "Node.js", "label": "TECH"},
                {"text": "MongoDB", "label": "TECH"},
            ],
        )

        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Node.js backend with MongoDB database",
            source_type="git",
            source_title="Backend Guide",
            entities=[
                {"text": "Node.js", "label": "TECH"},
                {"text": "MongoDB", "label": "TECH"},
                {"text": "Express", "label": "TECH"},
            ],
        )

        # Mock the entity extraction to return the expected values
        complementary_finder.similarity_calculator._extract_entity_texts.side_effect = [
            ["react", "node.js", "mongodb"],  # doc1 entities
            ["node.js", "mongodb", "express"],  # doc2 entities
        ]

        count = complementary_finder._get_shared_technologies_count(doc1, doc2)

        assert count == 2  # Node.js and MongoDB

    def test_has_different_content_complexity(self, complementary_finder):
        """Test detection of different content complexity."""
        simple_doc = create_hybrid_search_result(
            score=0.9,
            text="Quick start guide",
            source_type="confluence",
            source_title="Quick Start",
            word_count=200,
            estimated_read_time=2,
        )

        complex_doc = create_hybrid_search_result(
            score=0.8,
            text="Comprehensive technical documentation",
            source_type="confluence",
            source_title="Complete Guide",
            word_count=5000,
            estimated_read_time=25,
        )

        different_complexity = complementary_finder._has_different_content_complexity(
            simple_doc, complex_doc
        )

        assert different_complexity is True

        # Test similar complexity
        similar_doc = create_hybrid_search_result(
            score=0.8,
            text="Another quick guide",
            source_type="confluence",
            source_title="Another Quick Guide",
            word_count=250,
            estimated_read_time=3,
        )

        same_complexity = complementary_finder._has_different_content_complexity(
            simple_doc, similar_doc
        )

        assert same_complexity is False

    def test_get_complementary_content_type_score(self, complementary_finder):
        """Test complementary content type scoring."""
        tutorial_doc = create_hybrid_search_result(
            score=0.9,
            text="Step by step tutorial",
            source_type="confluence",
            source_title="Tutorial Guide",
        )

        reference_doc = create_hybrid_search_result(
            score=0.8,
            text="API reference documentation",
            source_type="confluence",
            source_title="API Reference",
        )

        score = complementary_finder._get_complementary_content_type_score(
            tutorial_doc, reference_doc
        )

        assert score > 0.0  # Tutorial and reference should be complementary
        assert score <= 1.0

    def test_calculate_fallback_score(self, complementary_finder):
        """Test fallback scoring algorithm."""
        doc1 = create_hybrid_search_result(
            score=0.9,
            text="OAuth authentication implementation",
            source_type="confluence",
            source_title="OAuth Guide",
            entities=[{"text": "OAuth", "label": "TECH"}],
            topics=[{"text": "authentication", "score": 0.9}],
        )

        doc2 = create_hybrid_search_result(
            score=0.8,
            text="JWT token validation methods",
            source_type="git",
            source_title="JWT Validation",
            entities=[{"text": "JWT", "label": "TECH"}],
            topics=[{"text": "authentication", "score": 0.8}],
        )

        # Mock the shared methods
        complementary_finder._has_shared_entities = Mock(return_value=False)
        complementary_finder._has_shared_topics = Mock(return_value=True)
        complementary_finder._get_shared_topics_count = Mock(return_value=1)

        score = complementary_finder._calculate_fallback_score(doc1, doc2)

        assert 0.0 <= score <= 1.0
        assert score > 0.0  # Should have some score due to shared topics
