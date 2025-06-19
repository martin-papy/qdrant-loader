"""Tests for custom edge schemas."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from qdrant_loader.schemas.edges import (
    DocumentRelationshipEdge,
    ContainsEdge,
    ReferencesEdge,
    AuthoredByEdge,
    BelongsToEdge,
    RelatedToEdge,
    DerivedFromEdge,
)


class TestDocumentRelationshipEdge:
    """Test DocumentRelationshipEdge base class."""

    def test_basic_creation(self):
        """Test basic edge creation."""
        now = datetime.now()
        edge = DocumentRelationshipEdge(
            name="test_edge",
            fact="test fact",
            group_id="test_group",
            source_node_uuid="source_uuid",
            target_node_uuid="target_uuid",
            relationship_type="test_relationship",
            created_at=now,
            confidence_score=None,
            context=None,
            evidence=None,
            detected_by=None,
            detected_at=None,
        )

        assert edge.name == "test_edge"
        assert edge.relationship_type == "test_relationship"
        assert edge.confidence_score is None
        assert edge.context is None
        assert edge.evidence is None

    def test_with_confidence_score(self):
        """Test edge with valid confidence score."""
        now = datetime.now()
        edge = DocumentRelationshipEdge(
            name="test_edge",
            fact="test fact",
            group_id="test_group",
            source_node_uuid="source_uuid",
            target_node_uuid="target_uuid",
            relationship_type="test_relationship",
            created_at=now,
            confidence_score=0.85,
            context=None,
            evidence=None,
            detected_by=None,
            detected_at=None,
        )

        assert edge.confidence_score == 0.85

    def test_confidence_score_validation_low(self):
        """Test confidence score validation - too low."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            DocumentRelationshipEdge(
                name="test_edge",
                fact="test fact",
                group_id="test_group",
                source_node_uuid="source_uuid",
                target_node_uuid="target_uuid",
                relationship_type="test_relationship",
                created_at=now,
                confidence_score=-0.1,
                context=None,
                evidence=None,
                detected_by=None,
                detected_at=None,
            )

        assert "Confidence score must be between 0.0 and 1.0" in str(exc_info.value)

    def test_confidence_score_validation_high(self):
        """Test confidence score validation - too high."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            DocumentRelationshipEdge(
                name="test_edge",
                fact="test fact",
                group_id="test_group",
                source_node_uuid="source_uuid",
                target_node_uuid="target_uuid",
                relationship_type="test_relationship",
                created_at=now,
                confidence_score=1.1,
                context=None,
                evidence=None,
                detected_by=None,
                detected_at=None,
            )

        assert "Confidence score must be between 0.0 and 1.0" in str(exc_info.value)

    def test_with_metadata(self):
        """Test edge with all metadata fields."""
        now = datetime.now()
        edge = DocumentRelationshipEdge(
            name="test_edge",
            fact="test fact",
            group_id="test_group",
            source_node_uuid="source_uuid",
            target_node_uuid="target_uuid",
            relationship_type="test_relationship",
            created_at=now,
            confidence_score=0.9,
            context="test context",
            evidence="test evidence",
            detected_by="test_model",
            detected_at=now,
        )

        assert edge.context == "test context"
        assert edge.evidence == "test evidence"
        assert edge.detected_by == "test_model"
        assert edge.detected_at == now


class TestContainsEdge:
    """Test ContainsEdge class."""

    def test_basic_creation(self):
        """Test basic contains edge creation."""
        now = datetime.now()
        edge = ContainsEdge(
            name="contains_edge",
            fact="document contains chunk",
            group_id="test_group",
            source_node_uuid="doc_uuid",
            target_node_uuid="chunk_uuid",
            created_at=now,
            confidence_score=None,
            context=None,
            evidence=None,
            detected_by=None,
            detected_at=None,
            container_section=None,
            position_index=None,
            size_ratio=None,
        )

        assert edge.relationship_type == "contains"
        assert edge.container_section is None
        assert edge.position_index is None
        assert edge.size_ratio is None

    def test_with_containment_metadata(self):
        """Test contains edge with containment metadata."""
        now = datetime.now()
        edge = ContainsEdge(
            name="contains_edge",
            fact="document contains chunk",
            group_id="test_group",
            source_node_uuid="doc_uuid",
            target_node_uuid="chunk_uuid",
            created_at=now,
            confidence_score=None,
            context=None,
            evidence=None,
            detected_by=None,
            detected_at=None,
            container_section="introduction",
            position_index=5,
            size_ratio=0.15,
        )

        assert edge.container_section == "introduction"
        assert edge.position_index == 5
        assert edge.size_ratio == 0.15

    def test_position_validation_negative(self):
        """Test position index validation - negative value."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            ContainsEdge(
                name="contains_edge",
                fact="document contains chunk",
                group_id="test_group",
                source_node_uuid="doc_uuid",
                target_node_uuid="chunk_uuid",
                created_at=now,
                confidence_score=None,
                context=None,
                evidence=None,
                detected_by=None,
                detected_at=None,
                container_section=None,
                position_index=-1,
                size_ratio=None,
            )

        assert "Position index must be non-negative" in str(exc_info.value)

    def test_position_validation_zero(self):
        """Test position index validation - zero is valid."""
        now = datetime.now()
        edge = ContainsEdge(
            name="contains_edge",
            fact="document contains chunk",
            group_id="test_group",
            source_node_uuid="doc_uuid",
            target_node_uuid="chunk_uuid",
            created_at=now,
            confidence_score=None,
            context=None,
            evidence=None,
            detected_by=None,
            detected_at=None,
            container_section=None,
            position_index=0,
            size_ratio=None,
        )

        assert edge.position_index == 0


class TestReferencesEdge:
    """Test ReferencesEdge class."""

    def test_basic_creation(self):
        """Test basic references edge creation."""
        now = datetime.now()
        edge = ReferencesEdge(
            name="references_edge",
            fact="document references other",
            group_id="test_group",
            source_node_uuid="doc1_uuid",
            target_node_uuid="doc2_uuid",
            created_at=now,
            confidence_score=None,
            context=None,
            evidence=None,
            detected_by=None,
            detected_at=None,
            reference_context=None,
            page_number=None,
            line_number=None,
            citation_style=None,
        )

        assert edge.relationship_type == "references"
        assert edge.reference_type == "mention"
        assert edge.is_formal_citation is False

    def test_with_reference_metadata(self):
        """Test references edge with metadata."""
        now = datetime.now()
        edge = ReferencesEdge(
            name="references_edge",
            fact="document cites paper",
            group_id="test_group",
            source_node_uuid="doc1_uuid",
            target_node_uuid="doc2_uuid",
            created_at=now,
            confidence_score=None,
            context=None,
            evidence=None,
            detected_by=None,
            detected_at=None,
            reference_type="citation",
            reference_context="literature review",
            page_number=15,
            line_number=23,
            citation_style="APA",
            is_formal_citation=True,
        )

        assert edge.reference_type == "citation"
        assert edge.reference_context == "literature review"
        assert edge.page_number == 15
        assert edge.line_number == 23
        assert edge.citation_style == "APA"
        assert edge.is_formal_citation is True

    def test_reference_type_validation_valid(self):
        """Test reference type validation - valid types."""
        now = datetime.now()
        valid_types = [
            "mention",
            "citation",
            "link",
            "attachment",
            "dependency",
            "other",
        ]

        for ref_type in valid_types:
            edge = ReferencesEdge(
                name="references_edge",
                fact="document references other",
                group_id="test_group",
                source_node_uuid="doc1_uuid",
                target_node_uuid="doc2_uuid",
                created_at=now,
                confidence_score=None,
                context=None,
                evidence=None,
                detected_by=None,
                detected_at=None,
                reference_type=ref_type,
                reference_context=None,
                page_number=None,
                line_number=None,
                citation_style=None,
            )
            assert edge.reference_type == ref_type

    def test_reference_type_validation_invalid(self):
        """Test reference type validation - invalid type."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            ReferencesEdge(
                name="references_edge",
                fact="document references other",
                group_id="test_group",
                source_node_uuid="doc1_uuid",
                target_node_uuid="doc2_uuid",
                created_at=now,
                confidence_score=None,
                context=None,
                evidence=None,
                detected_by=None,
                detected_at=None,
                reference_type="invalid_type",
                reference_context=None,
                page_number=None,
                line_number=None,
                citation_style=None,
            )

        assert "Reference type must be one of" in str(exc_info.value)


class TestAuthoredByEdge:
    """Test AuthoredByEdge class."""

    def test_basic_creation(self):
        """Test basic authored by edge creation."""
        now = datetime.now()
        edge = AuthoredByEdge(
            name="authored_by_edge",
            fact="document authored by person",
            group_id="test_group",
            source_node_uuid="doc_uuid",
            target_node_uuid="person_uuid",
            created_at=now,
            contribution_type=None,
            contribution_percentage=None,
            authored_at=None,
            last_modified_at=None,
            verification_method=None,
        )

        assert edge.author_role == "author"
        assert edge.verified is False

    def test_with_authorship_metadata(self):
        """Test authored by edge with metadata."""
        now = datetime.now()
        edge = AuthoredByEdge(
            name="authored_by_edge",
            fact="document co-authored by person",
            group_id="test_group",
            source_node_uuid="doc_uuid",
            target_node_uuid="person_uuid",
            created_at=now,
            author_role="co-author",
            contribution_type="research",
            contribution_percentage=0.4,
            authored_at=now,
            last_modified_at=now,
            verified=True,
            verification_method="signature_check",
        )

        assert edge.author_role == "co-author"
        assert edge.contribution_type == "research"
        assert edge.contribution_percentage == 0.4
        assert edge.authored_at == now
        assert edge.verified is True
        assert edge.verification_method == "signature_check"

    def test_author_role_validation_valid(self):
        """Test author role validation - valid roles."""
        now = datetime.now()
        valid_roles = [
            "author",
            "co-author",
            "editor",
            "reviewer",
            "contributor",
            "translator",
            "other",
        ]

        for role in valid_roles:
            edge = AuthoredByEdge(
                name="authored_by_edge",
                fact="document authored by person",
                group_id="test_group",
                source_node_uuid="doc_uuid",
                target_node_uuid="person_uuid",
                created_at=now,
                author_role=role,
                contribution_type=None,
                contribution_percentage=None,
                authored_at=None,
                last_modified_at=None,
                verification_method=None,
            )
            assert edge.author_role == role

    def test_author_role_validation_invalid(self):
        """Test author role validation - invalid role."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            AuthoredByEdge(
                name="authored_by_edge",
                fact="document authored by person",
                group_id="test_group",
                source_node_uuid="doc_uuid",
                target_node_uuid="person_uuid",
                created_at=now,
                author_role="invalid_role",
                contribution_type=None,
                contribution_percentage=None,
                authored_at=None,
                last_modified_at=None,
                verification_method=None,
            )

        assert "Author role must be one of" in str(exc_info.value)

    def test_contribution_percentage_validation_low(self):
        """Test contribution percentage validation - too low."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            AuthoredByEdge(
                name="authored_by_edge",
                fact="document authored by person",
                group_id="test_group",
                source_node_uuid="doc_uuid",
                target_node_uuid="person_uuid",
                created_at=now,
                contribution_type=None,
                contribution_percentage=-0.1,
                authored_at=None,
                last_modified_at=None,
                verification_method=None,
            )

        assert "Contribution percentage must be between 0.0 and 1.0" in str(
            exc_info.value
        )

    def test_contribution_percentage_validation_high(self):
        """Test contribution percentage validation - too high."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            AuthoredByEdge(
                name="authored_by_edge",
                fact="document authored by person",
                group_id="test_group",
                source_node_uuid="doc_uuid",
                target_node_uuid="person_uuid",
                created_at=now,
                contribution_type=None,
                contribution_percentage=1.1,
                authored_at=None,
                last_modified_at=None,
                verification_method=None,
            )

        assert "Contribution percentage must be between 0.0 and 1.0" in str(
            exc_info.value
        )


class TestBelongsToEdge:
    """Test BelongsToEdge class."""

    def test_basic_creation(self):
        """Test basic belongs to edge creation."""
        now = datetime.now()
        edge = BelongsToEdge(
            name="belongs_to_edge",
            fact="document belongs to project",
            group_id="test_group",
            source_node_uuid="doc_uuid",
            target_node_uuid="project_uuid",
            created_at=now,
            start_date=None,
            end_date=None,
            role_in_group=None,
            access_level=None,
        )

        assert edge.membership_type == "belongs_to"
        assert edge.is_active is True
        assert edge.status == "active"
        assert edge.permissions == []

    def test_with_membership_metadata(self):
        """Test belongs to edge with metadata."""
        now = datetime.now()
        start_date = datetime.now()
        end_date = datetime.now()

        edge = BelongsToEdge(
            name="belongs_to_edge",
            fact="person member of organization",
            group_id="test_group",
            source_node_uuid="person_uuid",
            target_node_uuid="org_uuid",
            created_at=now,
            membership_type="member_o",
            start_date=start_date,
            end_date=end_date,
            role_in_group="developer",
            permissions=["read", "write"],
            access_level="full",
            is_active=False,
            status="inactive",
        )

        assert edge.membership_type == "member_o"
        assert edge.start_date == start_date
        assert edge.end_date == end_date
        assert edge.role_in_group == "developer"
        assert edge.permissions == ["read", "write"]
        assert edge.access_level == "full"
        assert edge.is_active is False
        assert edge.status == "inactive"

    def test_membership_type_validation_valid(self):
        """Test membership type validation - valid types."""
        now = datetime.now()
        valid_types = [
            "belongs_to",
            "member_o",
            "part_o",
            "assigned_to",
            "owned_by",
            "other",
        ]

        for membership_type in valid_types:
            edge = BelongsToEdge(
                name="belongs_to_edge",
                fact="entity belongs to group",
                group_id="test_group",
                source_node_uuid="entity_uuid",
                target_node_uuid="group_uuid",
                created_at=now,
                membership_type=membership_type,
                start_date=None,
                end_date=None,
                role_in_group=None,
                access_level=None,
            )
            assert edge.membership_type == membership_type

    def test_membership_type_validation_invalid(self):
        """Test membership type validation - invalid type."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            BelongsToEdge(
                name="belongs_to_edge",
                fact="entity belongs to group",
                group_id="test_group",
                source_node_uuid="entity_uuid",
                target_node_uuid="group_uuid",
                created_at=now,
                membership_type="invalid_type",
                start_date=None,
                end_date=None,
                role_in_group=None,
                access_level=None,
            )

        assert "Membership type must be one of" in str(exc_info.value)

    def test_status_validation_valid(self):
        """Test status validation - valid statuses."""
        now = datetime.now()
        valid_statuses = ["active", "inactive", "pending", "suspended", "terminated"]

        for status in valid_statuses:
            edge = BelongsToEdge(
                name="belongs_to_edge",
                fact="entity belongs to group",
                group_id="test_group",
                source_node_uuid="entity_uuid",
                target_node_uuid="group_uuid",
                created_at=now,
                start_date=None,
                end_date=None,
                role_in_group=None,
                access_level=None,
                status=status,
            )
            assert edge.status == status

    def test_status_validation_invalid(self):
        """Test status validation - invalid status."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            BelongsToEdge(
                name="belongs_to_edge",
                fact="entity belongs to group",
                group_id="test_group",
                source_node_uuid="entity_uuid",
                target_node_uuid="group_uuid",
                created_at=now,
                start_date=None,
                end_date=None,
                role_in_group=None,
                access_level=None,
                status="invalid_status",
            )

        assert "Status must be one of" in str(exc_info.value)


class TestRelatedToEdge:
    """Test RelatedToEdge class."""

    def test_basic_creation(self):
        """Test basic related to edge creation."""
        now = datetime.now()
        edge = RelatedToEdge(
            name="related_to_edge",
            fact="document related to other",
            group_id="test_group",
            source_node_uuid="doc1_uuid",
            target_node_uuid="doc2_uuid",
            created_at=now,
            confidence_score=None,
            context=None,
            evidence=None,
            detected_by=None,
            detected_at=None,
            semantic_similarity=None,
            relationship_strength=None,
            discovered_through=None,
            discovery_algorithm=None,
        )

        assert edge.relationship_type == "related_to"
        assert edge.bidirectional is True
        assert edge.topic_overlap == []
        assert edge.keyword_overlap == []

    def test_with_semantic_metadata(self):
        """Test related to edge with semantic metadata."""
        now = datetime.now()
        edge = RelatedToEdge(
            name="related_to_edge",
            fact="documents are semantically related",
            group_id="test_group",
            source_node_uuid="doc1_uuid",
            target_node_uuid="doc2_uuid",
            created_at=now,
            confidence_score=None,
            context=None,
            evidence=None,
            detected_by=None,
            detected_at=None,
            semantic_similarity=0.85,
            topic_overlap=["AI", "machine learning"],
            keyword_overlap=["neural", "network"],
            relationship_strength="strong",
            bidirectional=False,
            discovered_through="semantic_analysis",
            discovery_algorithm="cosine_similarity",
        )

        assert edge.semantic_similarity == 0.85
        assert edge.topic_overlap == ["AI", "machine learning"]
        assert edge.keyword_overlap == ["neural", "network"]
        assert edge.relationship_strength == "strong"
        assert edge.bidirectional is False
        assert edge.discovered_through == "semantic_analysis"
        assert edge.discovery_algorithm == "cosine_similarity"

    def test_semantic_similarity_validation_low(self):
        """Test semantic similarity validation - too low."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            RelatedToEdge(
                name="related_to_edge",
                fact="documents are related",
                group_id="test_group",
                source_node_uuid="doc1_uuid",
                target_node_uuid="doc2_uuid",
                created_at=now,
                confidence_score=None,
                context=None,
                evidence=None,
                detected_by=None,
                detected_at=None,
                semantic_similarity=-0.1,
                relationship_strength=None,
                discovered_through=None,
                discovery_algorithm=None,
            )

        assert "Semantic similarity must be between 0.0 and 1.0" in str(exc_info.value)

    def test_semantic_similarity_validation_high(self):
        """Test semantic similarity validation - too high."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            RelatedToEdge(
                name="related_to_edge",
                fact="documents are related",
                group_id="test_group",
                source_node_uuid="doc1_uuid",
                target_node_uuid="doc2_uuid",
                created_at=now,
                confidence_score=None,
                context=None,
                evidence=None,
                detected_by=None,
                detected_at=None,
                semantic_similarity=1.1,
                relationship_strength=None,
                discovered_through=None,
                discovery_algorithm=None,
            )

        assert "Semantic similarity must be between 0.0 and 1.0" in str(exc_info.value)

    def test_relationship_strength_validation_valid(self):
        """Test relationship strength validation - valid values."""
        now = datetime.now()
        valid_strengths = ["weak", "moderate", "strong", "very_strong"]

        for strength in valid_strengths:
            edge = RelatedToEdge(
                name="related_to_edge",
                fact="documents are related",
                group_id="test_group",
                source_node_uuid="doc1_uuid",
                target_node_uuid="doc2_uuid",
                created_at=now,
                confidence_score=None,
                context=None,
                evidence=None,
                detected_by=None,
                detected_at=None,
                semantic_similarity=None,
                relationship_strength=strength,
                discovered_through=None,
                discovery_algorithm=None,
            )
            assert edge.relationship_strength == strength

    def test_relationship_strength_validation_invalid(self):
        """Test relationship strength validation - invalid value."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            RelatedToEdge(
                name="related_to_edge",
                fact="documents are related",
                group_id="test_group",
                source_node_uuid="doc1_uuid",
                target_node_uuid="doc2_uuid",
                created_at=now,
                confidence_score=None,
                context=None,
                evidence=None,
                detected_by=None,
                detected_at=None,
                semantic_similarity=None,
                relationship_strength="invalid_strength",
                discovered_through=None,
                discovery_algorithm=None,
            )

        assert "Relationship strength must be one of" in str(exc_info.value)


class TestDerivedFromEdge:
    """Test DerivedFromEdge class."""

    def test_basic_creation(self):
        """Test basic derived from edge creation."""
        now = datetime.now()
        edge = DerivedFromEdge(
            name="derived_from_edge",
            fact="summary derived from document",
            group_id="test_group",
            source_node_uuid="summary_uuid",
            target_node_uuid="doc_uuid",
            created_at=now,
            confidence_score=None,
            context=None,
            evidence=None,
            detected_by=None,
            detected_at=None,
            derivation_type="summary",
            derivation_method=None,
            transformation_applied=None,
            fidelity_score=None,
            completeness_score=None,
            derived_at=None,
            derived_by=None,
            processing_time=None,
        )

        assert edge.relationship_type == "derived_from"
        assert edge.derivation_type == "summary"

    def test_with_derivation_metadata(self):
        """Test derived from edge with metadata."""
        now = datetime.now()
        edge = DerivedFromEdge(
            name="derived_from_edge",
            fact="translation derived from original",
            group_id="test_group",
            source_node_uuid="translation_uuid",
            target_node_uuid="original_uuid",
            created_at=now,
            confidence_score=None,
            context=None,
            evidence=None,
            detected_by=None,
            detected_at=None,
            derivation_type="translation",
            derivation_method="neural_translation",
            transformation_applied="language_conversion",
            fidelity_score=0.92,
            completeness_score=0.88,
            derived_at=now,
            derived_by="translation_model",
            processing_time=45.5,
        )

        assert edge.derivation_type == "translation"
        assert edge.derivation_method == "neural_translation"
        assert edge.transformation_applied == "language_conversion"
        assert edge.fidelity_score == 0.92
        assert edge.completeness_score == 0.88
        assert edge.derived_at == now
        assert edge.derived_by == "translation_model"
        assert edge.processing_time == 45.5

    def test_derivation_type_validation_valid(self):
        """Test derivation type validation - valid types."""
        now = datetime.now()
        valid_types = [
            "summary",
            "translation",
            "extraction",
            "transformation",
            "annotation",
            "enhancement",
            "compression",
            "other",
        ]

        for derivation_type in valid_types:
            edge = DerivedFromEdge(
                name="derived_from_edge",
                fact="derived document",
                group_id="test_group",
                source_node_uuid="derived_uuid",
                target_node_uuid="original_uuid",
                created_at=now,
                confidence_score=None,
                context=None,
                evidence=None,
                detected_by=None,
                detected_at=None,
                derivation_type=derivation_type,
                derivation_method=None,
                transformation_applied=None,
                fidelity_score=None,
                completeness_score=None,
                derived_at=None,
                derived_by=None,
                processing_time=None,
            )
            assert edge.derivation_type == derivation_type

    def test_derivation_type_validation_invalid(self):
        """Test derivation type validation - invalid type."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            DerivedFromEdge(
                name="derived_from_edge",
                fact="derived document",
                group_id="test_group",
                source_node_uuid="derived_uuid",
                target_node_uuid="original_uuid",
                created_at=now,
                confidence_score=None,
                context=None,
                evidence=None,
                detected_by=None,
                detected_at=None,
                derivation_type="invalid_type",
                derivation_method=None,
                transformation_applied=None,
                fidelity_score=None,
                completeness_score=None,
                derived_at=None,
                derived_by=None,
                processing_time=None,
            )

        assert "Derivation type must be one of" in str(exc_info.value)

    def test_fidelity_score_validation_low(self):
        """Test fidelity score validation - too low."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            DerivedFromEdge(
                name="derived_from_edge",
                fact="derived document",
                group_id="test_group",
                source_node_uuid="derived_uuid",
                target_node_uuid="original_uuid",
                created_at=now,
                confidence_score=None,
                context=None,
                evidence=None,
                detected_by=None,
                detected_at=None,
                derivation_type="summary",
                derivation_method=None,
                transformation_applied=None,
                fidelity_score=-0.1,
                completeness_score=None,
                derived_at=None,
                derived_by=None,
                processing_time=None,
            )

        assert "Fidelity score must be between 0.0 and 1.0" in str(exc_info.value)

    def test_fidelity_score_validation_high(self):
        """Test fidelity score validation - too high."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            DerivedFromEdge(
                name="derived_from_edge",
                fact="derived document",
                group_id="test_group",
                source_node_uuid="derived_uuid",
                target_node_uuid="original_uuid",
                created_at=now,
                confidence_score=None,
                context=None,
                evidence=None,
                detected_by=None,
                detected_at=None,
                derivation_type="summary",
                derivation_method=None,
                transformation_applied=None,
                fidelity_score=1.1,
                completeness_score=None,
                derived_at=None,
                derived_by=None,
                processing_time=None,
            )

        assert "Fidelity score must be between 0.0 and 1.0" in str(exc_info.value)

    def test_completeness_score_validation_low(self):
        """Test completeness score validation - too low."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            DerivedFromEdge(
                name="derived_from_edge",
                fact="derived document",
                group_id="test_group",
                source_node_uuid="derived_uuid",
                target_node_uuid="original_uuid",
                created_at=now,
                confidence_score=None,
                context=None,
                evidence=None,
                detected_by=None,
                detected_at=None,
                derivation_type="summary",
                derivation_method=None,
                transformation_applied=None,
                fidelity_score=None,
                completeness_score=-0.1,
                derived_at=None,
                derived_by=None,
                processing_time=None,
            )

        assert "Completeness score must be between 0.0 and 1.0" in str(exc_info.value)

    def test_completeness_score_validation_high(self):
        """Test completeness score validation - too high."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            DerivedFromEdge(
                name="derived_from_edge",
                fact="derived document",
                group_id="test_group",
                source_node_uuid="derived_uuid",
                target_node_uuid="original_uuid",
                created_at=now,
                confidence_score=None,
                context=None,
                evidence=None,
                detected_by=None,
                detected_at=None,
                derivation_type="summary",
                derivation_method=None,
                transformation_applied=None,
                fidelity_score=None,
                completeness_score=1.1,
                derived_at=None,
                derived_by=None,
                processing_time=None,
            )

        assert "Completeness score must be between 0.0 and 1.0" in str(exc_info.value)
