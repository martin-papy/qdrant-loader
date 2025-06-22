"""Tests for custom node schemas."""

from datetime import datetime

import pytest
from pydantic import ValidationError
from qdrant_loader.schemas.nodes import (
    ChunkNode,
    ConceptNode,
    DocumentNode,
    OrganizationNode,
    PersonNode,
    ProjectNode,
    SourceNode,
)


class TestDocumentNode:
    """Test DocumentNode class."""

    def test_basic_creation(self):
        """Test basic document node creation."""
        node = DocumentNode(
            name="test_document",
            group_id="test_group",
            file_path=None,
            file_type=None,
            file_size=None,
            mime_type=None,
            title=None,
            author=None,
            language=None,
            page_count=None,
            word_count=None,
            processed_at=None,
            chunk_count=None,
            content_summary=None,
        )

        assert node.name == "test_document"
        assert node.processing_status == "pending"
        assert node.keywords == []
        assert node.topics == []

    def test_with_file_metadata(self):
        """Test document node with file metadata."""
        node = DocumentNode(
            name="research_paper.pdf",
            group_id="test_group",
            file_path="/docs/research_paper.pdf",
            file_type="pdf",
            file_size=1024000,
            mime_type="application/pdf",
            title="AI Research Paper",
            author="Dr. Smith",
            language="en",
            page_count=25,
            word_count=5000,
            processed_at=None,
            chunk_count=None,
            content_summary=None,
        )

        assert node.file_path == "/docs/research_paper.pdf"
        assert node.file_type == "pdf"
        assert node.file_size == 1024000
        assert node.mime_type == "application/pdf"
        assert node.title == "AI Research Paper"
        assert node.author == "Dr. Smith"
        assert node.language == "en"
        assert node.page_count == 25
        assert node.word_count == 5000

    def test_with_processing_metadata(self):
        """Test document node with processing metadata."""
        now = datetime.now()
        node = DocumentNode(
            name="processed_doc",
            group_id="test_group",
            file_path=None,
            file_type=None,
            file_size=None,
            mime_type=None,
            title=None,
            author=None,
            language=None,
            page_count=None,
            word_count=None,
            processing_status="completed",
            processed_at=now,
            chunk_count=15,
            content_summary="Document about machine learning",
            keywords=["AI", "ML", "neural networks"],
            topics=["artificial intelligence", "deep learning"],
        )

        assert node.processing_status == "completed"
        assert node.processed_at == now
        assert node.chunk_count == 15
        assert node.content_summary == "Document about machine learning"
        assert node.keywords == ["AI", "ML", "neural networks"]
        assert node.topics == ["artificial intelligence", "deep learning"]

    def test_processing_status_validation_valid(self):
        """Test processing status validation - valid statuses."""
        valid_statuses = ["pending", "processing", "completed", "failed", "skipped"]

        for status in valid_statuses:
            node = DocumentNode(
                name="test_doc",
                group_id="test_group",
                processing_status=status,
                file_path=None,
                file_type=None,
                file_size=None,
                mime_type=None,
                title=None,
                author=None,
                language=None,
                page_count=None,
                word_count=None,
                processed_at=None,
                chunk_count=None,
                content_summary=None,
            )
            assert node.processing_status == status

    def test_processing_status_validation_invalid(self):
        """Test processing status validation - invalid status."""
        with pytest.raises(ValidationError) as exc_info:
            DocumentNode(
                name="test_doc",
                group_id="test_group",
                processing_status="invalid_status",
                file_path=None,
                file_type=None,
                file_size=None,
                mime_type=None,
                title=None,
                author=None,
                language=None,
                page_count=None,
                word_count=None,
                processed_at=None,
                chunk_count=None,
                content_summary=None,
            )

        assert "Status must be one of" in str(exc_info.value)


class TestSourceNode:
    """Test SourceNode class."""

    def test_basic_creation(self):
        """Test basic source node creation."""
        node = SourceNode(
            name="git_repo",
            group_id="test_group",
            source_type="git",
            source_url=None,
            last_accessed=None,
            access_method=None,
            credentials_used=None,
            total_documents=None,
            successful_imports=None,
            failed_imports=None,
        )

        assert node.name == "git_repo"
        assert node.source_type == "git"
        assert node.source_config == {}

    def test_with_source_metadata(self):
        """Test source node with metadata."""
        now = datetime.now()
        config = {"branch": "main", "depth": 1}

        node = SourceNode(
            name="company_repo",
            group_id="test_group",
            source_type="git",
            source_url="https://github.com/company/repo.git",
            source_config=config,
            last_accessed=now,
            access_method="clone",
            credentials_used="ssh_key",
            total_documents=150,
            successful_imports=145,
            failed_imports=5,
        )

        assert node.source_url == "https://github.com/company/repo.git"
        assert node.source_config == config
        assert node.last_accessed == now
        assert node.access_method == "clone"
        assert node.credentials_used == "ssh_key"
        assert node.total_documents == 150
        assert node.successful_imports == 145
        assert node.failed_imports == 5

    def test_source_type_validation_valid(self):
        """Test source type validation - valid types."""
        valid_types = [
            "git",
            "confluence",
            "jira",
            "sharepoint",
            "filesystem",
            "database",
            "api",
            "other",
        ]

        for source_type in valid_types:
            node = SourceNode(
                name="test_source",
                group_id="test_group",
                source_type=source_type,
                source_url=None,
                last_accessed=None,
                access_method=None,
                credentials_used=None,
                total_documents=None,
                successful_imports=None,
                failed_imports=None,
            )
            assert node.source_type == source_type

    def test_source_type_validation_invalid(self):
        """Test source type validation - invalid type."""
        with pytest.raises(ValidationError) as exc_info:
            SourceNode(
                name="test_source",
                group_id="test_group",
                source_type="invalid_type",
                source_url=None,
                last_accessed=None,
                access_method=None,
                credentials_used=None,
                total_documents=None,
                successful_imports=None,
                failed_imports=None,
            )

        assert "Source type must be one of" in str(exc_info.value)


class TestConceptNode:
    """Test ConceptNode class."""

    def test_basic_creation(self):
        """Test basic concept node creation."""
        node = ConceptNode(
            name="machine_learning",
            group_id="test_group",
            definition=None,
            domain=None,
            confidence_score=None,
            frequency=None,
        )

        assert node.name == "machine_learning"
        assert node.concept_type == "general"
        assert node.aliases == []
        assert node.parent_concepts == []
        assert node.child_concepts == []

    def test_with_concept_metadata(self):
        """Test concept node with metadata."""
        node = ConceptNode(
            name="neural_networks",
            group_id="test_group",
            concept_type="technical",
            definition="Computational models inspired by biological neural networks",
            aliases=["artificial neural networks", "ANNs"],
            domain="artificial intelligence",
            confidence_score=0.95,
            frequency=42,
            parent_concepts=["machine_learning", "AI"],
            child_concepts=["CNN", "RNN", "transformer"],
        )

        assert node.concept_type == "technical"
        assert (
            node.definition
            == "Computational models inspired by biological neural networks"
        )
        assert node.aliases == ["artificial neural networks", "ANNs"]
        assert node.domain == "artificial intelligence"
        assert node.confidence_score == 0.95
        assert node.frequency == 42
        assert node.parent_concepts == ["machine_learning", "AI"]
        assert node.child_concepts == ["CNN", "RNN", "transformer"]

    def test_confidence_score_validation_low(self):
        """Test confidence score validation - too low."""
        with pytest.raises(ValidationError) as exc_info:
            ConceptNode(
                name="test_concept",
                group_id="test_group",
                confidence_score=-0.1,
                definition=None,
                domain=None,
                frequency=None,
            )

        assert "Confidence score must be between 0.0 and 1.0" in str(exc_info.value)

    def test_confidence_score_validation_high(self):
        """Test confidence score validation - too high."""
        with pytest.raises(ValidationError) as exc_info:
            ConceptNode(
                name="test_concept",
                group_id="test_group",
                confidence_score=1.1,
                definition=None,
                domain=None,
                frequency=None,
            )

        assert "Confidence score must be between 0.0 and 1.0" in str(exc_info.value)

    def test_confidence_score_boundary_values(self):
        """Test confidence score validation - boundary values."""
        # Test 0.0
        node1 = ConceptNode(
            name="test_concept1",
            group_id="test_group",
            confidence_score=0.0,
            definition=None,
            domain=None,
            frequency=None,
        )
        assert node1.confidence_score == 0.0

        # Test 1.0
        node2 = ConceptNode(
            name="test_concept2",
            group_id="test_group",
            confidence_score=1.0,
            definition=None,
            domain=None,
            frequency=None,
        )
        assert node2.confidence_score == 1.0


class TestPersonNode:
    """Test PersonNode class."""

    def test_basic_creation(self):
        """Test basic person node creation."""
        node = PersonNode(
            name="John Doe",
            group_id="test_group",
            full_name=None,
            email=None,
            role=None,
            department=None,
            phone=None,
            location=None,
            last_mentioned=None,
            mention_count=None,
        )

        assert node.name == "John Doe"
        assert node.expertise_areas == []
        assert node.projects == []

    def test_with_person_metadata(self):
        """Test person node with metadata."""
        now = datetime.now()
        node = PersonNode(
            name="Dr. Jane Smith",
            group_id="test_group",
            full_name="Dr. Jane Elizabeth Smith",
            email="jane.smith@company.com",
            role="Senior AI Researcher",
            department="Research & Development",
            phone="+1-555-0123",
            location="San Francisco, CA",
            expertise_areas=["machine learning", "computer vision", "NLP"],
            projects=["project_alpha", "project_beta"],
            last_mentioned=now,
            mention_count=15,
        )

        assert node.full_name == "Dr. Jane Elizabeth Smith"
        assert node.email == "jane.smith@company.com"
        assert node.role == "Senior AI Researcher"
        assert node.department == "Research & Development"
        assert node.phone == "+1-555-0123"
        assert node.location == "San Francisco, CA"
        assert node.expertise_areas == ["machine learning", "computer vision", "NLP"]
        assert node.projects == ["project_alpha", "project_beta"]
        assert node.last_mentioned == now
        assert node.mention_count == 15


class TestOrganizationNode:
    """Test OrganizationNode class."""

    def test_basic_creation(self):
        """Test basic organization node creation."""
        node = OrganizationNode(
            name="TechCorp",
            group_id="test_group",
            industry=None,
            size=None,
            website=None,
            headquarters=None,
            parent_organization=None,
            first_mentioned=None,
            last_mentioned=None,
        )

        assert node.name == "TechCorp"
        assert node.organization_type == "company"
        assert node.subsidiaries == []

    def test_with_organization_metadata(self):
        """Test organization node with metadata."""
        now = datetime.now()
        node = OrganizationNode(
            name="AI Innovations Inc",
            group_id="test_group",
            organization_type="company",
            industry="artificial intelligence",
            size="medium",
            website="https://ai-innovations.com",
            headquarters="Palo Alto, CA",
            parent_organization="TechHolding Corp",
            subsidiaries=["AI Labs", "Data Solutions"],
            first_mentioned=now,
            last_mentioned=now,
        )

        assert node.organization_type == "company"
        assert node.industry == "artificial intelligence"
        assert node.size == "medium"
        assert node.website == "https://ai-innovations.com"
        assert node.headquarters == "Palo Alto, CA"
        assert node.parent_organization == "TechHolding Corp"
        assert node.subsidiaries == ["AI Labs", "Data Solutions"]
        assert node.first_mentioned == now
        assert node.last_mentioned == now

    def test_organization_type_validation_valid(self):
        """Test organization type validation - valid types."""
        valid_types = [
            "company",
            "department",
            "team",
            "nonprofit",
            "government",
            "educational",
            "other",
        ]

        for org_type in valid_types:
            node = OrganizationNode(
                name="test_org",
                group_id="test_group",
                organization_type=org_type,
                industry=None,
                size=None,
                website=None,
                headquarters=None,
                parent_organization=None,
                first_mentioned=None,
                last_mentioned=None,
            )
            assert node.organization_type == org_type

    def test_organization_type_validation_invalid(self):
        """Test organization type validation - invalid type."""
        with pytest.raises(ValidationError) as exc_info:
            OrganizationNode(
                name="test_org",
                group_id="test_group",
                organization_type="invalid_type",
                industry=None,
                size=None,
                website=None,
                headquarters=None,
                parent_organization=None,
                first_mentioned=None,
                last_mentioned=None,
            )

        assert "Organization type must be one of" in str(exc_info.value)


class TestProjectNode:
    """Test ProjectNode class."""

    def test_basic_creation(self):
        """Test basic project node creation."""
        node = ProjectNode(
            name="AI Research Project",
            group_id="test_group",
            start_date=None,
            end_date=None,
            deadline=None,
            priority=None,
            budget=None,
            progress=None,
            project_manager=None,
        )

        assert node.name == "AI Research Project"
        assert node.project_status == "active"
        assert node.team_members == []
        assert node.stakeholders == []
        assert node.requirements == []
        assert node.deliverables == []

    def test_with_project_metadata(self):
        """Test project node with metadata."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        deadline = datetime(2024, 11, 30)

        node = ProjectNode(
            name="ML Platform Development",
            group_id="test_group",
            project_status="active",
            start_date=start_date,
            end_date=end_date,
            deadline=deadline,
            priority="high",
            budget=500000.0,
            progress=0.65,
            project_manager="Alice Johnson",
            team_members=["Bob Smith", "Carol Brown", "David Wilson"],
            stakeholders=["CEO", "CTO", "Product Manager"],
            requirements=["scalability", "security", "performance"],
            deliverables=["API", "dashboard", "documentation"],
        )

        assert node.project_status == "active"
        assert node.start_date == start_date
        assert node.end_date == end_date
        assert node.deadline == deadline
        assert node.priority == "high"
        assert node.budget == 500000.0
        assert node.progress == 0.65
        assert node.project_manager == "Alice Johnson"
        assert node.team_members == ["Bob Smith", "Carol Brown", "David Wilson"]
        assert node.stakeholders == ["CEO", "CTO", "Product Manager"]
        assert node.requirements == ["scalability", "security", "performance"]
        assert node.deliverables == ["API", "dashboard", "documentation"]

    def test_project_status_validation_valid(self):
        """Test project status validation - valid statuses."""
        valid_statuses = [
            "planning",
            "active",
            "on-hold",
            "completed",
            "cancelled",
        ]

        for status in valid_statuses:
            node = ProjectNode(
                name="test_project",
                group_id="test_group",
                project_status=status,
                start_date=None,
                end_date=None,
                deadline=None,
                priority=None,
                budget=None,
                progress=None,
                project_manager=None,
            )
            assert node.project_status == status

    def test_project_status_validation_invalid(self):
        """Test project status validation - invalid status."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectNode(
                name="test_project",
                group_id="test_group",
                project_status="invalid_status",
                start_date=None,
                end_date=None,
                deadline=None,
                priority=None,
                budget=None,
                progress=None,
                project_manager=None,
            )

        assert "Project status must be one of" in str(exc_info.value)

    def test_progress_validation_low(self):
        """Test progress validation - too low."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectNode(
                name="test_project",
                group_id="test_group",
                progress=-0.1,
                start_date=None,
                end_date=None,
                deadline=None,
                priority=None,
                budget=None,
                project_manager=None,
            )

        assert "Progress must be between 0.0 and 1.0" in str(exc_info.value)

    def test_progress_validation_high(self):
        """Test progress validation - too high."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectNode(
                name="test_project",
                group_id="test_group",
                progress=1.1,
                start_date=None,
                end_date=None,
                deadline=None,
                priority=None,
                budget=None,
                project_manager=None,
            )

        assert "Progress must be between 0.0 and 1.0" in str(exc_info.value)

    def test_progress_boundary_values(self):
        """Test progress validation - boundary values."""
        # Test 0.0
        node1 = ProjectNode(
            name="test_project1",
            group_id="test_group",
            progress=0.0,
            start_date=None,
            end_date=None,
            deadline=None,
            priority=None,
            budget=None,
            project_manager=None,
        )
        assert node1.progress == 0.0

        # Test 1.0
        node2 = ProjectNode(
            name="test_project2",
            group_id="test_group",
            progress=1.0,
            start_date=None,
            end_date=None,
            deadline=None,
            priority=None,
            budget=None,
            project_manager=None,
        )
        assert node2.progress == 1.0


class TestChunkNode:
    """Test ChunkNode class."""

    def test_basic_creation(self):
        """Test basic chunk node creation."""
        node = ChunkNode(
            name="chunk_1",
            group_id="test_group",
            document_id="doc_123",
            chunk_index=0,
            content="This is the first chunk of the document.",
            content_length=40,
            word_count=8,
            chunk_id=None,
            start_position=None,
            end_position=None,
            page_number=None,
            embedding_model=None,
            embedding_dimension=None,
            processed_at=None,
            sentiment=None,
        )

        assert node.name == "chunk_1"
        assert node.document_id == "doc_123"
        assert node.chunk_index == 0
        assert node.content == "This is the first chunk of the document."
        assert node.content_length == 40
        assert node.word_count == 8
        assert node.topics == []
        assert node.entities == []

    def test_with_chunk_metadata(self):
        """Test chunk node with metadata."""
        now = datetime.now()
        node = ChunkNode(
            name="chunk_5",
            group_id="test_group",
            document_id="doc_456",
            chunk_index=4,
            chunk_id="chunk_456_4",
            content="Machine learning algorithms require large datasets for training.",
            content_length=65,
            word_count=9,
            start_position=1200,
            end_position=1265,
            page_number=3,
            embedding_model="text-embedding-ada-002",
            embedding_dimension=1536,
            processed_at=now,
            topics=["machine learning", "datasets"],
            entities=["algorithms", "training"],
            sentiment="neutral",
        )

        assert node.chunk_id == "chunk_456_4"
        assert node.start_position == 1200
        assert node.end_position == 1265
        assert node.page_number == 3
        assert node.embedding_model == "text-embedding-ada-002"
        assert node.embedding_dimension == 1536
        assert node.processed_at == now
        assert node.topics == ["machine learning", "datasets"]
        assert node.entities == ["algorithms", "training"]
        assert node.sentiment == "neutral"

    def test_chunk_index_validation_negative(self):
        """Test chunk index validation - negative value."""
        with pytest.raises(ValidationError) as exc_info:
            ChunkNode(
                name="chunk_test",
                group_id="test_group",
                document_id="doc_123",
                chunk_index=-1,
                content="Test content",
                content_length=12,
                word_count=2,
                chunk_id=None,
                start_position=None,
                end_position=None,
                page_number=None,
                embedding_model=None,
                embedding_dimension=None,
                processed_at=None,
                sentiment=None,
            )

        assert "Chunk index must be non-negative" in str(exc_info.value)

    def test_chunk_index_validation_zero(self):
        """Test chunk index validation - zero is valid."""
        node = ChunkNode(
            name="chunk_test",
            group_id="test_group",
            document_id="doc_123",
            chunk_index=0,
            content="Test content",
            content_length=12,
            word_count=2,
            chunk_id=None,
            start_position=None,
            end_position=None,
            page_number=None,
            embedding_model=None,
            embedding_dimension=None,
            processed_at=None,
            sentiment=None,
        )

        assert node.chunk_index == 0

    def test_content_length_validation_negative(self):
        """Test content length validation - negative value."""
        with pytest.raises(ValidationError) as exc_info:
            ChunkNode(
                name="chunk_test",
                group_id="test_group",
                document_id="doc_123",
                chunk_index=0,
                content="Test content",
                content_length=-1,
                word_count=2,
                chunk_id=None,
                start_position=None,
                end_position=None,
                page_number=None,
                embedding_model=None,
                embedding_dimension=None,
                processed_at=None,
                sentiment=None,
            )

        assert "Content length must be non-negative" in str(exc_info.value)

    def test_content_length_validation_zero(self):
        """Test content length validation - zero is valid."""
        node = ChunkNode(
            name="chunk_test",
            group_id="test_group",
            document_id="doc_123",
            chunk_index=0,
            content="",
            content_length=0,
            word_count=0,
            chunk_id=None,
            start_position=None,
            end_position=None,
            page_number=None,
            embedding_model=None,
            embedding_dimension=None,
            processed_at=None,
            sentiment=None,
        )

        assert node.content_length == 0

    def test_word_count_negative_allowed(self):
        """Test word count allows negative values (no validation in schema)."""
        # Note: The schema doesn't validate word_count, so negative values are allowed
        node = ChunkNode(
            name="chunk_test",
            group_id="test_group",
            document_id="doc_123",
            chunk_index=0,
            content="Test content",
            content_length=12,
            word_count=-1,
            chunk_id=None,
            start_position=None,
            end_position=None,
            page_number=None,
            embedding_model=None,
            embedding_dimension=None,
            processed_at=None,
            sentiment=None,
        )

        assert node.word_count == -1

    def test_word_count_validation_zero(self):
        """Test word count validation - zero is valid."""
        node = ChunkNode(
            name="chunk_test",
            group_id="test_group",
            document_id="doc_123",
            chunk_index=0,
            content="",
            content_length=0,
            word_count=0,
            chunk_id=None,
            start_position=None,
            end_position=None,
            page_number=None,
            embedding_model=None,
            embedding_dimension=None,
            processed_at=None,
            sentiment=None,
        )

        assert node.word_count == 0
