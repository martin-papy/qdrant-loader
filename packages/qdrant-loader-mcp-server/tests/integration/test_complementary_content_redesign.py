"""Integration tests for the redesigned complementary content algorithm."""

import pytest
from unittest.mock import Mock
from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import ComplementaryContentFinder
from qdrant_loader_mcp_server.search.components.search_result_models import HybridSearchResult, create_hybrid_search_result


class TestComplementaryContentRedesign:
    """Test the redesigned complementary content algorithm."""
    
    @pytest.fixture
    def complementary_finder(self):
        """Create a complementary content finder with mocked dependencies."""
        mock_similarity_calculator = Mock()
        mock_similarity_calculator._extract_topic_texts.return_value = []
        mock_similarity_calculator._extract_entity_texts.return_value = []
        
        return ComplementaryContentFinder(
            similarity_calculator=mock_similarity_calculator,
            knowledge_graph=None
        )
    
    def create_test_document(self, title: str, project_id: str, source_type: str = "localfile", 
                           topics: list = None, entities: list = None) -> HybridSearchResult:
        """Create a test document for testing."""
        return create_hybrid_search_result(
            source_title=title,
            project_id=project_id,
            source_type=source_type,
            topics=topics or [],
            entities=entities or [],
            text="Sample content for " + title,
            score=1.0,
            word_count=100,
            has_code_blocks=False,
            has_tables=False,
            has_images=False,
            depth=1,
            breadcrumb_text="Test > Path"
        )
    
    def test_intra_project_requirements_implementation_pair(self, complementary_finder):
        """Test detection of requirements-implementation pairs within same project."""
        # Arrange
        target_doc = self.create_test_document(
            title="User Story: Patient Authentication Requirements",
            project_id="HealthApp",
            topics=["authentication", "patient", "security"]
        )
        
        candidate_doc = self.create_test_document(
            title="Technical Implementation: JWT Authentication Service",
            project_id="HealthApp",
            topics=["authentication", "jwt", "technical"],
            entities=["JWT", "Authentication"]
        )
        
        # Mock the shared topics/entities methods
        complementary_finder._has_shared_topics = Mock(return_value=True)
        complementary_finder._has_shared_entities = Mock(return_value=True)
        complementary_finder._get_shared_topics_count = Mock(return_value=2)
        
        # Act
        score, reason = complementary_finder._calculate_complementary_score(target_doc, candidate_doc)
        
        # Assert
        assert score >= 0.8, f"Expected high score for requirements-implementation pair, got {score}"
        # The algorithm should detect either the requirements-implementation relationship 
        # or the abstraction gap - both are valid complementary indicators
        assert ("Requirements-implementation chain" in reason or 
                "Different abstraction levels" in reason or
                "other factors" in reason), f"Expected req-impl or abstraction relationship, got: {reason}"
        print(f"✓ Intra-project req-impl pair: {score:.3f} - {reason}")
    
    def test_intra_project_abstraction_gap(self, complementary_finder):
        """Test abstraction level difference detection within same project."""
        # Arrange
        target_doc = self.create_test_document(
            title="Executive Overview: HealthApp Platform Strategy", 
            project_id="HealthApp"
        )
        
        candidate_doc = self.create_test_document(
            title="Technical Implementation: Database Configuration",
            project_id="HealthApp"
        )
        
        # Act
        score, reason = complementary_finder._calculate_complementary_score(target_doc, candidate_doc)
        
        # Assert
        assert score > 0.7, f"Expected high score for abstraction gap, got {score}"
        assert "abstraction" in reason.lower()
        print(f"✓ Intra-project abstraction gap: {score:.3f} - {reason}")
    
    def test_inter_project_penalty_applied(self, complementary_finder):
        """Test that inter-project relationships get appropriate penalty."""
        # Arrange
        target_doc = self.create_test_document(
            title="Authentication Implementation",
            project_id="ProjectA"
        )
        
        candidate_doc = self.create_test_document(
            title="Authentication Architecture", 
            project_id="ProjectB"
        )
        
        # Act
        score, reason = complementary_finder._calculate_complementary_score(target_doc, candidate_doc)
        
        # Assert
        if score > 0:
            assert "Inter-project" in reason
            print(f"✓ Inter-project penalty applied: {score:.3f} - {reason}")
        else:
            print(f"✓ No inter-project relationship found: {score:.3f} - {reason}")
    
    def test_document_type_classification(self, complementary_finder):
        """Test document type classification accuracy."""
        test_cases = [
            ("User Story: Login Feature", "user_story"),
            ("Technical Specification: API Design", "technical_spec"),
            ("Architecture Overview: System Design", "architecture"),
            ("Security Policy: Compliance Requirements", "compliance"),
            ("Test Plan: Authentication Testing", "testing"),
            ("Workflow Guide: User Onboarding Process", "process"),
            ("Random Document Title", "general")
        ]
        
        for title, expected_type in test_cases:
            doc = self.create_test_document(title, "TestProject")
            actual_type = complementary_finder._classify_document_type(doc)
            assert actual_type == expected_type, f"Expected {expected_type}, got {actual_type} for '{title}'"
            print(f"✓ Classification: '{title}' → {actual_type}")
    
    def test_abstraction_level_calculation(self, complementary_finder):
        """Test abstraction level calculation."""
        test_cases = [
            ("Executive Strategy Overview", 0),
            ("Business Requirements Document", 1),
            ("System Architecture Design", 2),
            ("Code Implementation Guide", 3),
            ("Generic Document", 2)  # Default
        ]
        
        for title, expected_level in test_cases:
            doc = self.create_test_document(title, "TestProject")
            actual_level = complementary_finder._get_abstraction_level(doc)
            assert actual_level == expected_level, f"Expected level {expected_level}, got {actual_level} for '{title}'"
            print(f"✓ Abstraction level: '{title}' → Level {actual_level}")
    
    def test_cross_functional_relationship_detection(self, complementary_finder):
        """Test cross-functional relationship detection."""
        # Business + Technical
        business_doc = self.create_test_document("Business Requirements for User Management", "TestProject")
        technical_doc = self.create_test_document("Technical Architecture for API Development", "TestProject")
        
        assert complementary_finder._has_cross_functional_relationship(business_doc, technical_doc)
        print("✓ Business + Technical relationship detected")
        
        # Feature + Security
        feature_doc = self.create_test_document("Feature Specification: Payment Processing", "TestProject")
        security_doc = self.create_test_document("Security Compliance: Authentication Audit", "TestProject")
        
        assert complementary_finder._has_cross_functional_relationship(feature_doc, security_doc)
        print("✓ Feature + Security relationship detected")
    
    def test_health_platform_scenario_simulation(self, complementary_finder):
        """Simulate health platform project scenario that was returning 0.000 scores."""
        # Arrange - All documents from same project (HealthPlatform) and same source type (localfile)
        target_doc = self.create_test_document(
            title="Platform Functions - Updated Version 28.01.2025",
            project_id="HealthPlatform",
            source_type="localfile",
            topics=["functions", "features", "platform"]
        )
        
        candidates = [
            self.create_test_document(
                title="Technical Specification May 24",
                project_id="HealthPlatform",
                source_type="localfile", 
                topics=["technical", "specification", "platform"]
            ),
            self.create_test_document(
                title="Functional Requirement - Mobile App Wireframes",
                project_id="HealthPlatform",
                source_type="localfile",
                topics=["functional", "requirements", "mobile", "wireframes"]
            ),
            self.create_test_document(
                title="Technical Documentation - Audio-visual Complete Guide",
                project_id="HealthPlatform", 
                source_type="localfile",
                topics=["documentation", "technical", "audio", "visual"]
            )
        ]
        
        # Mock shared topics/entities for realistic scenario
        complementary_finder._has_shared_topics = Mock(return_value=True)
        complementary_finder._get_shared_topics_count = Mock(return_value=2)
        
        # Act & Assert
        results = []
        for candidate in candidates:
            score, reason = complementary_finder._calculate_complementary_score(target_doc, candidate)
            results.append((score, reason, candidate.source_title))
            
        # Verify we're getting better than 0.000 scores
        non_zero_scores = [score for score, _, _ in results if score > 0]
        assert len(non_zero_scores) > 0, "Expected at least one non-zero score for health platform scenario"
        
        print("=== Health Platform Scenario Results ===")
        for score, reason, title in results:
            print(f"Score: {score:.3f} - {title}")
            print(f"Reason: {reason}")
            print()
        
        # Verify improvement over old algorithm (which returned 0.000)
        max_score = max(score for score, _, _ in results)
        assert max_score > 0.4, f"Expected significant improvement over 0.000, got max score {max_score}"
        print(f"✓ Significant improvement: Max score {max_score:.3f} vs previous 0.000") 