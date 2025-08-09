"""Unit tests for cross-document intelligence algorithms and scoring methods."""

import pytest
from unittest.mock import Mock
import time

from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
    DocumentClusterAnalyzer,
    ComplementaryContentFinder,
    ConflictDetector,
    CrossDocumentIntelligenceEngine,
    ClusteringStrategy,
    RelationshipType
)
from qdrant_loader_mcp_server.search.components.search_result_models import (
    create_hybrid_search_result
)
from tests.fixtures.cross_document_test_data import (
    create_authentication_docs,
    create_minimal_test_dataset
)


class TestComplementaryContentFinderAlgorithms:
    """Test ComplementaryContentFinder algorithms and scoring methods."""

    @pytest.fixture
    def mock_similarity_calculator(self):
        """Create a mock similarity calculator."""
        calc = Mock()
        mock_similarity = Mock()
        mock_similarity.similarity_score = 0.7
        mock_similarity.shared_entities = ["OAuth", "JWT"]
        mock_similarity.shared_topics = ["authentication"]
        calc.calculate_similarity.return_value = mock_similarity
        calc._extract_entity_texts.return_value = ["oauth", "jwt"]
        calc._extract_topic_texts.return_value = ["authentication"]
        return calc

    @pytest.fixture
    def complementary_finder(self, mock_similarity_calculator):
        """Create a ComplementaryContentFinder instance."""
        return ComplementaryContentFinder(mock_similarity_calculator)

    def test_calculate_complementary_score_same_project(self, complementary_finder):
        """Test complementary scoring for documents in same project."""
        target_doc = create_hybrid_search_result(
            score=0.9,
            text="OAuth 2.0 requirements for healthcare app",
            source_type="confluence",
            source_title="OAuth Requirements",
            project_id="healthcare_platform",
            entities=[{"text": "OAuth", "label": "TECH"}],
            topics=[{"text": "requirements", "score": 0.9}]
        )
        
        candidate_doc = create_hybrid_search_result(
            score=0.8,
            text="JWT implementation guide with code examples",
            source_type="git",
            source_title="JWT Implementation Guide",
            project_id="healthcare_platform",
            entities=[{"text": "JWT", "label": "TECH"}],
            topics=[{"text": "implementation", "score": 0.8}],
            has_code_blocks=True
        )
        
        score, reason = complementary_finder._calculate_complementary_score(target_doc, candidate_doc)
        
        assert score > 0.0
        assert "intra-project" in reason.lower() or "requirements-implementation" in reason.lower()

    def test_calculate_complementary_score_different_projects(self, complementary_finder):
        """Test complementary scoring for documents in different projects."""
        target_doc = create_hybrid_search_result(
            score=0.9,
            text="OAuth authentication patterns",
            source_type="confluence",
            source_title="OAuth Patterns",
            project_id="healthcare_platform",
            entities=[{"text": "OAuth", "label": "TECH"}]
        )
        
        candidate_doc = create_hybrid_search_result(
            score=0.8,
            text="OAuth lessons learned from business platform",
            source_type="confluence",
            source_title="Business OAuth Lessons",
            project_id="business_platform",
            entities=[{"text": "OAuth", "label": "TECH"}]
        )
        
        score, reason = complementary_finder._calculate_complementary_score(target_doc, candidate_doc)
        
        assert score >= 0.0
        if score > 0:
            assert "inter-project" in reason.lower()

    def test_score_intra_project_complementary_requirements_implementation(self, complementary_finder):
        """Test intra-project scoring for requirements-implementation pairs."""
        target_doc = create_hybrid_search_result(
            score=0.9,
            text="User authentication requirements",
            source_type="confluence",
            source_title="Authentication Requirements",
            project_id="platform",
            entities=[{"text": "authentication", "label": "CONCEPT"}]
        )
        
        candidate_doc = create_hybrid_search_result(
            score=0.8,
            text="Authentication implementation in Node.js",
            source_type="git",
            source_title="Authentication Implementation",
            project_id="platform",
            entities=[{"text": "authentication", "label": "CONCEPT"}],
            has_code_blocks=True
        )
        
        score, reason = complementary_finder._score_intra_project_complementary(target_doc, candidate_doc)
        
        assert score > 0.5  # Should be high for req-impl pairs
        assert "requirements-implementation" in reason.lower()

    def test_score_intra_project_complementary_abstraction_gap(self, complementary_finder):
        """Test intra-project scoring based on abstraction level differences."""
        high_level_doc = create_hybrid_search_result(
            score=0.9,
            text="Business strategy and vision for authentication",
            source_type="confluence",
            source_title="Authentication Strategy",
            project_id="platform"
        )
        
        low_level_doc = create_hybrid_search_result(
            score=0.8,
            text="Technical implementation details and API configuration",
            source_type="git",
            source_title="API Implementation Details",
            project_id="platform"
        )
        
        score, reason = complementary_finder._score_intra_project_complementary(high_level_doc, low_level_doc)
        
        assert score > 0.0
        if "abstraction" in reason.lower():
            assert score > 0.6  # Good abstraction gap should score well

    def test_score_inter_project_complementary_similar_challenges(self, complementary_finder):
        """Test inter-project scoring for similar challenges."""
        # Mock the _has_similar_challenges method to return True
        complementary_finder._has_similar_challenges = Mock(return_value=True)
        
        doc1 = create_hybrid_search_result(
            score=0.9,
            text="Authentication challenges in healthcare",
            source_type="confluence",
            source_title="Healthcare Auth Challenges",
            project_id="healthcare"
        )
        
        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Authentication solutions for business platform",
            source_type="confluence",
            source_title="Business Auth Solutions",
            project_id="business"
        )
        
        score, reason = complementary_finder._score_inter_project_complementary(doc1, doc2)
        
        assert score > 0.0
        assert "similar challenges" in reason.lower()

    def test_is_requirements_implementation_pair(self, complementary_finder):
        """Test detection of requirements-implementation pairs."""
        req_doc = create_hybrid_search_result(
            score=0.9,
            text="User requirements for login system",
            source_type="confluence",
            source_title="Login System Requirements",
            entities=[{"text": "login", "label": "FEATURE"}]
        )
        
        impl_doc = create_hybrid_search_result(
            score=0.8,
            text="Technical implementation of login API",
            source_type="git",
            source_title="Login API Implementation",
            entities=[{"text": "login", "label": "FEATURE"}]
        )
        
        is_pair = complementary_finder._is_requirements_implementation_pair(req_doc, impl_doc)
        
        assert is_pair is True
        
        # Test non-pair
        other_doc = create_hybrid_search_result(
            score=0.8,
            text="Database schema design",
            source_type="confluence",
            source_title="Database Schema"
        )
        
        is_not_pair = complementary_finder._is_requirements_implementation_pair(req_doc, other_doc)
        
        assert is_not_pair is False

    def test_calculate_abstraction_gap(self, complementary_finder):
        """Test abstraction gap calculation."""
        strategy_doc = create_hybrid_search_result(
            score=0.9,
            text="Strategic overview and business vision",
            source_type="confluence",
            source_title="Business Strategy Overview"
        )
        
        impl_doc = create_hybrid_search_result(
            score=0.8,
            text="Technical implementation and code details",
            source_type="git",
            source_title="Technical Implementation Details"
        )
        
        gap = complementary_finder._calculate_abstraction_gap(strategy_doc, impl_doc)
        
        assert gap >= 0
        assert gap <= 3  # Maximum defined gap
        assert gap > 0  # Should detect difference between strategy and implementation

    def test_get_abstraction_level_classification(self, complementary_finder):
        """Test abstraction level classification for different document types."""
        strategy_doc = create_hybrid_search_result(
            score=0.9,
            text="Test",
            source_type="confluence",
            source_title="Business Strategy and Vision"
        )
        
        requirements_doc = create_hybrid_search_result(
            score=0.9,
            text="Test",
            source_type="confluence",
            source_title="User Requirements Specification"
        )
        
        design_doc = create_hybrid_search_result(
            score=0.9,
            text="Test",
            source_type="confluence",
            source_title="System Architecture Design"
        )
        
        impl_doc = create_hybrid_search_result(
            score=0.9,
            text="Test",
            source_type="git",
            source_title="API Implementation Code"
        )
        
        strategy_level = complementary_finder._get_abstraction_level(strategy_doc)
        requirements_level = complementary_finder._get_abstraction_level(requirements_doc)
        design_level = complementary_finder._get_abstraction_level(design_doc)
        impl_level = complementary_finder._get_abstraction_level(impl_doc)
        
        # Strategy should be highest level (lowest number)
        assert strategy_level <= requirements_level
        assert requirements_level <= design_level
        assert design_level <= impl_level

    def test_has_cross_functional_relationship(self, complementary_finder):
        """Test detection of cross-functional relationships."""
        business_doc = create_hybrid_search_result(
            score=0.9,
            text="Test",
            source_type="confluence",
            source_title="Business Requirements and User Workflow"
        )
        
        technical_doc = create_hybrid_search_result(
            score=0.8,
            text="Test",
            source_type="git",
            source_title="Technical Architecture Implementation"
        )
        
        has_relationship = complementary_finder._has_cross_functional_relationship(business_doc, technical_doc)
        
        assert has_relationship is True
        
        # Test documents in same functional area
        tech_doc1 = create_hybrid_search_result(
            score=0.9,
            text="Test",
            source_type="git",
            source_title="Technical API Documentation"
        )
        
        tech_doc2 = create_hybrid_search_result(
            score=0.8,
            text="Test",
            source_type="git",
            source_title="Technical Implementation Guide"
        )
        
        no_relationship = complementary_finder._has_cross_functional_relationship(tech_doc1, tech_doc2)
        
        assert no_relationship is False

    def test_has_different_document_types(self, complementary_finder):
        """Test detection of different document types."""
        tutorial_doc = create_hybrid_search_result(
            score=0.9,
            text="Step by step tutorial guide",
            source_type="confluence",
            source_title="OAuth Tutorial Guide"
        )
        
        reference_doc = create_hybrid_search_result(
            score=0.8,
            text="Complete API reference documentation",
            source_type="confluence",
            source_title="OAuth API Reference"
        )
        
        different_types = complementary_finder._has_different_document_types(tutorial_doc, reference_doc)
        
        assert different_types is True
        
        # Test same document types
        tutorial_doc2 = create_hybrid_search_result(
            score=0.8,
            text="Another tutorial on JWT",
            source_type="confluence",
            source_title="JWT Tutorial"
        )
        
        same_types = complementary_finder._has_different_document_types(tutorial_doc, tutorial_doc2)
        
        assert same_types is False

    def test_classify_document_type(self, complementary_finder):
        """Test document type classification."""
        tutorial_doc = create_hybrid_search_result(
            score=0.9,
            text="Test",
            source_type="confluence",
            source_title="OAuth Tutorial Guide"
        )
        
        reference_doc = create_hybrid_search_result(
            score=0.9,
            text="Test",
            source_type="confluence",
            source_title="API Reference Documentation"
        )
        
        example_doc = create_hybrid_search_result(
            score=0.9,
            text="Test",
            source_type="git",
            source_title="Code Examples and Samples"
        )
        
        tutorial_type = complementary_finder._classify_document_type(tutorial_doc)
        reference_type = complementary_finder._classify_document_type(reference_doc)
        example_type = complementary_finder._classify_document_type(example_doc)
        
        assert tutorial_type == "tutorial"
        assert reference_type == "reference"
        assert example_type == "example"

    def test_enhanced_fallback_scoring(self, complementary_finder):
        """Test enhanced fallback scoring when no specific factors match."""
        doc1 = create_hybrid_search_result(
            score=0.9,
            text="Generic document about software development",
            source_type="confluence",
            source_title="Software Development Guide",
            entities=[{"text": "software", "label": "CONCEPT"}],
            topics=[{"text": "development", "score": 0.8}]
        )
        
        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Another document about programming practices",
            source_type="confluence",
            source_title="Programming Best Practices",
            entities=[{"text": "programming", "label": "CONCEPT"}],
            topics=[{"text": "development", "score": 0.7}]
        )
        
        score, reason = complementary_finder._enhanced_fallback_scoring(doc1, doc2)
        
        assert score >= 0.0
        assert score <= 1.0
        assert isinstance(reason, str)
        assert len(reason) > 0

    def test_calculate_weighted_score_multiple_factors(self, complementary_finder):
        """Test weighted score calculation with multiple factors."""
        factors = [
            (0.8, "High similarity"),
            (0.6, "Shared entities"),
            (0.7, "Related topics")
        ]
        
        score, reason = complementary_finder._calculate_weighted_score(factors)
        
        assert score > 0.8  # Should be boosted by multiple factors
        assert score <= 0.95  # Capped at 0.95
        assert "High similarity" in reason
        assert "+2 other factors" in reason

    def test_calculate_weighted_score_single_factor(self, complementary_finder):
        """Test weighted score calculation with single factor."""
        factors = [(0.7, "Single factor")]
        
        score, reason = complementary_finder._calculate_weighted_score(factors)
        
        assert score == 0.7
        assert reason == "Single factor"

    def test_calculate_weighted_score_empty_factors(self, complementary_finder):
        """Test weighted score calculation with no factors."""
        target_doc = create_hybrid_search_result(
            score=0.9,
            text="Test",
            source_type="confluence",
            source_title="Test Doc"
        )
        
        candidate_doc = create_hybrid_search_result(
            score=0.8,
            text="Test",
            source_type="confluence",
            source_title="Test Doc 2"
        )
        
        score, reason = complementary_finder._calculate_weighted_score([], target_doc, candidate_doc)
        
        assert score >= 0.0
        # Should fall back to enhanced fallback scoring
        assert isinstance(reason, str)


class TestDocumentClusterAnalyzerAlgorithms:
    """Test DocumentClusterAnalyzer clustering algorithms."""

    @pytest.fixture
    def mock_similarity_calculator(self):
        """Create a mock similarity calculator."""
        calc = Mock()
        mock_similarity = Mock()
        mock_similarity.similarity_score = 0.7
        mock_similarity.shared_entities = ["OAuth"]
        mock_similarity.shared_topics = ["authentication"]
        calc.calculate_similarity.return_value = mock_similarity
        calc._extract_entity_texts.return_value = ["oauth"]
        calc._extract_topic_texts.return_value = ["authentication"]
        return calc

    @pytest.fixture
    def cluster_analyzer(self, mock_similarity_calculator):
        """Create a DocumentClusterAnalyzer instance."""
        return DocumentClusterAnalyzer(mock_similarity_calculator)

    def test_cluster_by_mixed_features_comprehensive(self, cluster_analyzer):
        """Test mixed features clustering algorithm comprehensively."""
        docs = create_authentication_docs()  # Get realistic test data
        
        clusters = cluster_analyzer._cluster_by_mixed_features(
            docs, 
            max_clusters=3, 
            min_cluster_size=2
        )
        
        # Should create some clusters
        assert len(clusters) > 0
        
        for cluster in clusters:
            assert len(cluster.documents) >= 2  # Meets min_cluster_size
            assert cluster.cluster_strategy == ClusteringStrategy.MIXED_FEATURES
            assert cluster.cluster_id is not None
            assert cluster.name is not None

    def test_analyze_cluster_theme_comprehensive(self, cluster_analyzer):
        """Test comprehensive cluster theme analysis."""
        cluster_docs = [
            create_hybrid_search_result(
                score=0.9,
                text="OAuth 2.0 implementation guide with comprehensive examples",
                source_type="confluence",
                source_title="OAuth Implementation Guide",
                entities=[{"text": "OAuth", "label": "TECH"}],
                topics=[{"text": "implementation", "score": 0.9}],
                has_code_blocks=True,
                word_count=2500
            ),
            create_hybrid_search_result(
                score=0.8,
                text="JWT token validation best practices",
                source_type="git", 
                source_title="JWT Validation Guide",
                entities=[{"text": "JWT", "label": "TECH"}],
                topics=[{"text": "security", "score": 0.8}],
                has_code_blocks=True,
                word_count=1800
            )
        ]
        
        from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import DocumentCluster
        cluster = DocumentCluster(
            cluster_id="test",
            name="Test Cluster",
            shared_entities=["OAuth", "JWT"],
            shared_topics=["implementation", "security"],
            cluster_strategy=ClusteringStrategy.ENTITY_BASED
        )
        
        theme_analysis = cluster_analyzer._analyze_cluster_theme(cluster_docs, cluster)
        
        assert "primary_theme" in theme_analysis
        assert "characteristics" in theme_analysis
        assert "document_insights" in theme_analysis
        
        # Should detect technical content
        assert "technical content" in theme_analysis["characteristics"]
        
        # Should generate meaningful primary theme
        primary_theme = theme_analysis["primary_theme"]
        assert len(primary_theme) > 0
        assert ("OAuth" in primary_theme or "JWT" in primary_theme)

    def test_generate_characteristics_edge_cases(self, cluster_analyzer):
        """Test characteristic generation with edge cases."""
        # Test with documents having None word_count
        cluster_docs = [
            create_hybrid_search_result(
                score=0.9,
                text="Test document",
                source_type="confluence",
                source_title="Test Doc",
                word_count=None,  # None word count
                has_code_blocks=False
            ),
            create_hybrid_search_result(
                score=0.8,
                text="Another test",
                source_type="git",
                source_title="Another Doc",
                word_count=0,  # Zero word count
                has_code_blocks=True
            )
        ]
        
        from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import DocumentCluster
        cluster = DocumentCluster(
            cluster_id="test",
            name="Test",
            coherence_score=0.9,
            shared_entities=["test1", "test2", "test3", "test4"]  # Multiple entities
        )
        
        characteristics = cluster_analyzer._generate_characteristics(cluster_docs, cluster, True, 0)
        
        assert isinstance(characteristics, list)
        assert "technical content" in characteristics  # Should detect code blocks
        assert "highly related" in characteristics  # High coherence score
        assert "multi-faceted topics" in characteristics  # Multiple entities

    def test_categorize_cluster_size(self, cluster_analyzer):
        """Test cluster size categorization."""
        assert cluster_analyzer._categorize_cluster_size(1) == "individual"
        assert cluster_analyzer._categorize_cluster_size(3) == "small"
        assert cluster_analyzer._categorize_cluster_size(8) == "medium"
        assert cluster_analyzer._categorize_cluster_size(15) == "large"
        assert cluster_analyzer._categorize_cluster_size(30) == "very large"


class TestConflictDetectorAlgorithms:
    """Test ConflictDetector pattern detection algorithms."""

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

    def test_find_contradiction_patterns_version_conflicts(self, conflict_detector):
        """Test detection of version-related contradictions."""
        doc1 = create_hybrid_search_result(
            score=0.9,
            text="The application uses Node.js version 16.14.0 for all development work.",
            source_type="confluence",
            source_title="Development Environment Setup"
        )
        
        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Please ensure you have Node.js version 18.15.0 installed for the project.",
            source_type="confluence", 
            source_title="Project Setup Guide"
        )
        
        patterns = conflict_detector._find_contradiction_patterns(doc1, doc2)
        
        # Should detect version conflict
        version_conflicts = [p for p in patterns if "version" in p.get("type", "").lower()]
        assert len(version_conflicts) > 0

    def test_find_contradiction_patterns_procedural_conflicts(self, conflict_detector):
        """Test detection of procedural contradictions."""
        doc1 = create_hybrid_search_result(
            score=0.9,
            text="Always run npm install before starting development work on the project.",
            source_type="confluence",
            source_title="Development Workflow"
        )
        
        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Never use npm install, always use yarn install for package management.",
            source_type="confluence",
            source_title="Package Management Guide"
        )
        
        patterns = conflict_detector._find_contradiction_patterns(doc1, doc2)
        
        # Should detect procedural conflict
        procedural_conflicts = [p for p in patterns if "procedural" in p.get("type", "").lower()]
        assert len(procedural_conflicts) > 0

    def test_detect_version_conflicts_specific(self, conflict_detector):
        """Test specific version conflict detection."""
        doc1 = create_hybrid_search_result(
            score=0.9,
            text="Use Python 3.8.10 for compatibility with legacy systems.",
            source_type="confluence",
            source_title="Legacy System Integration"
        )
        
        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Python 3.10.5 is required for the new features to work properly.",
            source_type="confluence",
            source_title="New Feature Requirements"
        )
        
        version_conflicts = conflict_detector._detect_version_conflicts(doc1, doc2)
        
        assert len(version_conflicts) > 0
        conflict = version_conflicts[0]
        assert "version" in conflict["type"]
        assert "3.8.10" in conflict["summary"] or "3.10.5" in conflict["summary"]

    def test_detect_procedural_conflicts_specific(self, conflict_detector):
        """Test specific procedural conflict detection."""
        doc1 = create_hybrid_search_result(
            score=0.9,
            text="Database migrations should be run manually after deployment.",
            source_type="confluence",
            source_title="Deployment Process"
        )
        
        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Database migrations must be automated as part of the CI/CD pipeline.",
            source_type="confluence",
            source_title="CI/CD Best Practices"
        )
        
        procedural_conflicts = conflict_detector._detect_procedural_conflicts(doc1, doc2)
        
        assert len(procedural_conflicts) > 0
        conflict = procedural_conflicts[0]
        assert "procedural" in conflict["type"]

    def test_extract_context_snippet(self, conflict_detector):
        """Test context snippet extraction."""
        text = "This is a long document with many sentences. The important keyword is right here in the middle. There are more sentences after the keyword as well."
        
        snippet = conflict_detector._extract_context_snippet(text, "keyword", max_length=50)
        
        assert "keyword" in snippet
        assert len(snippet) <= 50 + 20  # Allow some padding for word boundaries
        assert "important keyword" in snippet  # Should include context

    def test_extract_context_snippet_keyword_not_found(self, conflict_detector):
        """Test context snippet when keyword is not found."""
        text = "This document does not contain the target word."
        
        snippet = conflict_detector._extract_context_snippet(text, "nonexistent", max_length=50)
        
        assert len(snippet) <= 50 + 20
        assert snippet.startswith("This document")  # Should return beginning of text

    def test_categorize_conflict_specific_patterns(self, conflict_detector):
        """Test conflict categorization with specific patterns."""
        version_indicators = ["version 1.0", "version 2.0", "incompatible versions"]
        procedural_indicators = ["should always", "never do", "must not"]
        data_indicators = ["different values", "conflicting data", "inconsistent information"]
        
        assert conflict_detector._categorize_conflict(version_indicators) == "version"
        assert conflict_detector._categorize_conflict(procedural_indicators) == "procedural" 
        assert conflict_detector._categorize_conflict(data_indicators) == "data"

    def test_calculate_conflict_confidence_scoring(self, conflict_detector):
        """Test conflict confidence scoring algorithm."""
        # High confidence indicators
        high_conf_indicators = ["version conflict", "incompatible", "contradicts", "different values"]
        high_confidence = conflict_detector._calculate_conflict_confidence(high_conf_indicators)
        
        # Medium confidence indicators
        medium_conf_indicators = ["different approach", "alternative method"]
        medium_confidence = conflict_detector._calculate_conflict_confidence(medium_conf_indicators)
        
        # Low confidence indicators
        low_conf_indicators = ["unclear", "possibly different"]
        low_confidence = conflict_detector._calculate_conflict_confidence(low_conf_indicators)
        
        assert high_confidence > medium_confidence > low_confidence
        assert 0.0 <= high_confidence <= 1.0
        assert 0.0 <= medium_confidence <= 1.0
        assert 0.0 <= low_confidence <= 1.0


class TestCrossDocumentIntelligenceEnginePerformance:
    """Test performance characteristics of the main engine."""

    @pytest.fixture
    def mock_spacy_analyzer(self):
        """Create a mock SpaCy analyzer."""
        analyzer = Mock()
        mock_doc = Mock()
        mock_doc.similarity.return_value = 0.6
        analyzer.nlp.return_value = mock_doc
        return analyzer

    @pytest.fixture
    def intelligence_engine(self, mock_spacy_analyzer):
        """Create a CrossDocumentIntelligenceEngine instance."""
        return CrossDocumentIntelligenceEngine(mock_spacy_analyzer)

    def test_analyze_document_relationships_timing(self, intelligence_engine):
        """Test that document relationship analysis completes in reasonable time."""
        docs = create_minimal_test_dataset() * 3  # 6 documents for testing
        
        start_time = time.time()
        analysis = intelligence_engine.analyze_document_relationships(docs)
        execution_time = time.time() - start_time
        
        # Should complete quickly in lightweight mode
        assert execution_time < 5.0  # 5 seconds max
        assert analysis["summary"]["analysis_mode"] == "lightweight"
        assert analysis["summary"]["total_documents"] == len(docs)

    def test_find_document_relationships_performance(self, intelligence_engine):
        """Test performance of finding specific document relationships."""
        docs = create_authentication_docs()
        target_doc_id = f"{docs[0].source_type}:{docs[0].source_title}"
        
        start_time = time.time()
        relationships = intelligence_engine.find_document_relationships(
            target_doc_id, 
            docs, 
            [RelationshipType.SEMANTIC_SIMILARITY]
        )
        execution_time = time.time() - start_time
        
        assert execution_time < 3.0  # Should be fast for specific relationships
        assert RelationshipType.SEMANTIC_SIMILARITY.value in relationships

    def test_build_similarity_matrix_performance(self, intelligence_engine):
        """Test similarity matrix building performance."""
        docs = create_minimal_test_dataset()
        
        start_time = time.time()
        matrix = intelligence_engine._build_similarity_matrix(docs)
        execution_time = time.time() - start_time
        
        assert execution_time < 2.0  # Matrix building should be fast for small datasets
        assert len(matrix) == len(docs)
        
        # Verify matrix structure
        for doc in docs:
            doc_id = f"{doc.source_type}:{doc.source_title}"
            assert doc_id in matrix
            assert len(matrix[doc_id]) == len(docs)

    def test_extract_similarity_insights(self, intelligence_engine):
        """Test similarity insights extraction."""
        # Create a simple similarity matrix
        similarity_matrix = {
            "doc1": {"doc1": 1.0, "doc2": 0.8, "doc3": 0.6},
            "doc2": {"doc1": 0.8, "doc2": 1.0, "doc3": 0.7},
            "doc3": {"doc1": 0.6, "doc2": 0.7, "doc3": 1.0}
        }
        
        insights = intelligence_engine._extract_similarity_insights(similarity_matrix)
        
        assert "average_similarity" in insights
        assert "max_similarity" in insights
        assert "min_similarity" in insights
        assert "highly_similar_pairs" in insights
        
        # Verify calculated values are reasonable
        assert 0.0 <= insights["average_similarity"] <= 1.0
        assert insights["max_similarity"] <= 1.0
        assert insights["min_similarity"] >= 0.0
        assert isinstance(insights["highly_similar_pairs"], int)
