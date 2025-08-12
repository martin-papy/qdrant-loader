"""
Generic Test Fixtures for Cross-Document Intelligence Testing

This replaces confidential client data with generic healthcare platform examples
to protect client confidentiality while maintaining test coverage.
"""

from qdrant_loader_mcp_server.search.components.search_result_models import (
    HybridSearchResult,
    create_hybrid_search_result,
)


def create_generic_healthcare_docs() -> list[HybridSearchResult]:
    """Create generic healthcare platform documents for testing."""
    return [
        create_hybrid_search_result(
            score=0.95,
            text="User authentication system implementation guide for healthcare platform. Covers OAuth 2.0, JWT tokens, session management, and HIPAA-compliant access control mechanisms.",
            source_type="documentation",
            source_title="Healthcare Auth Implementation",
            project_id="healthcare_platform",
            project_name="Healthcare Platform",
            entities=[
                {"text": "OAuth", "label": "TECHNOLOGY"},
                {"text": "JWT", "label": "TECHNOLOGY"},
                {"text": "HIPAA", "label": "REGULATION"},
            ],
            topics=["authentication", "security", "healthcare", "compliance"],
            key_phrases=["OAuth 2.0", "JWT tokens", "healthcare authentication"],
            content_type_context="Technical implementation guide for healthcare authentication",
        ),
        create_hybrid_search_result(
            score=0.88,
            text="Security requirements for healthcare authentication systems. Includes password policies, multi-factor authentication, biometric login, and compliance with healthcare regulations including HIPAA and GDPR.",
            source_type="documentation",
            source_title="Healthcare Security Requirements",
            project_id="healthcare_platform",
            project_name="Healthcare Platform",
            entities=[
                {"text": "MFA", "label": "TECHNOLOGY"},
                {"text": "biometric", "label": "TECHNOLOGY"},
                {"text": "HIPAA", "label": "REGULATION"},
                {"text": "GDPR", "label": "REGULATION"},
            ],
            topics=["security", "authentication", "compliance", "biometric"],
            key_phrases=[
                "multi-factor authentication",
                "biometric login",
                "healthcare compliance",
            ],
            content_type_context="Security requirements for healthcare systems",
        ),
        create_hybrid_search_result(
            score=0.82,
            text="Healthcare mobile application authentication requirements including biometric login, social OAuth integration, and offline authentication capabilities. Security requirements specify token expiry and secure storage protocols.",
            source_type="requirements",
            source_title="Mobile Healthcare Auth Requirements",
            project_id="healthcare_platform",
            project_name="Healthcare Platform",
            entities=[
                {"text": "Healthcare Platform", "label": "ORG"},
                {"text": "mobile", "label": "PLATFORM"},
                {"text": "biometric", "label": "TECHNOLOGY"},
            ],
            topics=["mobile", "authentication", "healthcare", "biometric"],
            key_phrases=[
                "mobile authentication",
                "biometric login",
                "offline capabilities",
            ],
            content_type_context="Mobile authentication requirements",
        ),
        create_hybrid_search_result(
            score=0.90,
            text="Database design patterns for healthcare applications. Covers patient data modeling, audit trails, encryption at rest, and performance optimization strategies for large healthcare datasets.",
            source_type="documentation",
            source_title="Healthcare Database Design",
            project_id="healthcare_platform",
            project_name="Healthcare Platform",
            entities=[
                {"text": "PostgreSQL", "label": "TECHNOLOGY"},
                {"text": "encryption", "label": "TECHNOLOGY"},
                {"text": "healthcare", "label": "DOMAIN"},
            ],
            topics=["database", "design", "healthcare", "security"],
            key_phrases=["database design", "patient data", "encryption at rest"],
            content_type_context="Database architecture guide for healthcare",
        ),
        create_hybrid_search_result(
            score=0.85,
            text="Microservices architecture patterns for healthcare platform including service mesh configuration, API gateway setup, and inter-service communication protocols using REST and GraphQL.",
            source_type="documentation",
            source_title="Healthcare Platform Architecture",
            project_id="healthcare_platform",
            project_name="Healthcare Platform",
            entities=[
                {"text": "microservices", "label": "ARCHITECTURE"},
                {"text": "API gateway", "label": "TECHNOLOGY"},
                {"text": "GraphQL", "label": "TECHNOLOGY"},
            ],
            topics=["architecture", "microservices", "API", "healthcare"],
            key_phrases=["microservices architecture", "service mesh", "API gateway"],
            content_type_context="Architecture patterns for healthcare systems",
        ),
    ]


def create_cross_platform_docs() -> list[HybridSearchResult]:
    """Create documents from multiple platforms for cross-document testing."""
    docs = create_generic_healthcare_docs()

    # Add fintech platform documents
    fintech_docs = [
        create_hybrid_search_result(
            score=0.87,
            text="React Native authentication components for fintech mobile app. Includes biometric authentication integration, social login buttons, and secure token storage using device keychain.",
            source_type="code",
            source_title="Fintech Mobile Auth Components",
            source_url="https://github.com/company/fintech-mobile/auth-components",
            project_id="fintech_platform",
            project_name="Fintech Platform",
            entities=[
                {"text": "React Native", "label": "TECHNOLOGY"},
                {"text": "biometric", "label": "TECHNOLOGY"},
                {"text": "keychain", "label": "TECHNOLOGY"},
            ],
            topics=["mobile", "authentication", "fintech", "components"],
            key_phrases=["React Native", "biometric authentication", "social login"],
            content_type_context="Code implementation for React Native authentication components",
        ),
        create_hybrid_search_result(
            score=0.83,
            text="RESTful API design guidelines for fintech platform. Payment processing, account management, and transaction history endpoints with rate limiting and fraud detection.",
            source_type="documentation",
            source_title="Fintech API Guidelines",
            project_id="fintech_platform",
            project_name="Fintech Platform",
            entities=[
                {"text": "REST", "label": "TECHNOLOGY"},
                {"text": "payment", "label": "BUSINESS"},
                {"text": "fraud detection", "label": "SECURITY"},
            ],
            topics=["api", "fintech", "payments", "security"],
            key_phrases=["RESTful API", "payment processing", "fraud detection"],
            content_type_context="API design guidelines for fintech platform",
        ),
    ]

    # Add education platform documents
    education_docs = [
        create_hybrid_search_result(
            score=0.79,
            text="Student authentication system for education platform. Single sign-on integration with university systems, role-based access control for students, faculty, and administrators.",
            source_type="documentation",
            source_title="Education Platform Authentication",
            project_id="education_platform",
            project_name="Education Platform",
            entities=[
                {"text": "SSO", "label": "TECHNOLOGY"},
                {"text": "RBAC", "label": "SECURITY"},
                {"text": "university", "label": "ORG"},
            ],
            topics=["authentication", "education", "SSO", "access_control"],
            key_phrases=["single sign-on", "role-based access", "university systems"],
            content_type_context="Technical implementation guide for education platform authentication",
        )
    ]

    return docs + fintech_docs + education_docs


def create_comprehensive_test_dataset() -> list[HybridSearchResult]:
    """Create a comprehensive dataset for thorough cross-document intelligence testing."""
    base_docs = create_cross_platform_docs()

    # Add more diverse content types
    additional_docs = [
        create_hybrid_search_result(
            score=0.91,
            text="Data privacy requirements for healthcare applications. GDPR compliance, patient consent management, data retention policies, and cross-border data transfer restrictions.",
            source_type="requirements",
            source_title="Healthcare Data Privacy Requirements",
            project_id="healthcare_platform",
            project_name="Healthcare Platform",
            entities=[
                {"text": "GDPR", "label": "REGULATION"},
                {"text": "patient consent", "label": "LEGAL"},
                {"text": "data retention", "label": "POLICY"},
            ],
            topics=["privacy", "healthcare", "compliance", "GDPR"],
            key_phrases=["data privacy", "GDPR compliance", "patient consent"],
            content_type_context="Data privacy requirements for healthcare applications",
        ),
        create_hybrid_search_result(
            score=0.86,
            text="Automated testing strategies for authentication systems. Unit tests for OAuth flows, integration tests for SSO, security testing for token validation and session management.",
            source_type="documentation",
            source_title="Authentication Testing Guide",
            project_id="healthcare_platform",
            project_name="Healthcare Platform",
            entities=[
                {"text": "OAuth", "label": "TECHNOLOGY"},
                {"text": "SSO", "label": "TECHNOLOGY"},
                {"text": "unit tests", "label": "TESTING"},
            ],
            topics=["testing", "authentication", "automation", "security"],
            key_phrases=["automated testing", "OAuth flows", "security testing"],
            content_type_context="Testing guide for authentication systems",
        ),
    ]

    return base_docs + additional_docs


def create_conflicting_docs() -> list[HybridSearchResult]:
    """Create documents with potential conflicts for conflict detection testing."""
    return [
        create_hybrid_search_result(
            score=0.92,
            text="Authentication policy version 1: Password requirements include 8 characters minimum, special characters required, password expiry every 90 days. Two-factor authentication is optional for standard users.",
            source_type="policy",
            source_title="Authentication Policy v1.0",
            project_id="healthcare_platform",
            project_name="Healthcare Platform",
            entities=[
                {"text": "password", "label": "SECURITY"},
                {"text": "two-factor", "label": "SECURITY"},
            ],
            topics=["authentication", "policy", "security"],
            key_phrases=["password requirements", "90 days", "optional two-factor"],
            content_type_context="Authentication policy version 1",
        ),
        create_hybrid_search_result(
            score=0.94,
            text="Authentication policy version 2: Password requirements include 12 characters minimum, special characters required, password expiry every 180 days. Two-factor authentication is mandatory for all users.",
            source_type="policy",
            source_title="Authentication Policy v2.0",
            project_id="healthcare_platform",
            project_name="Healthcare Platform",
            entities=[
                {"text": "password", "label": "SECURITY"},
                {"text": "two-factor", "label": "SECURITY"},
            ],
            topics=["authentication", "policy", "security"],
            key_phrases=["password requirements", "180 days", "mandatory two-factor"],
            content_type_context="Authentication policy version 2",
        ),
        create_hybrid_search_result(
            score=0.88,
            text="Implementation guide: Implement password validation with 8-character minimum as per company policy. Two-factor authentication should be implemented as optional feature with user preference settings.",
            source_type="documentation",
            source_title="Authentication Implementation Guide",
            project_id="healthcare_platform",
            project_name="Healthcare Platform",
            entities=[
                {"text": "password validation", "label": "IMPLEMENTATION"},
                {"text": "optional feature", "label": "FEATURE"},
            ],
            topics=["implementation", "authentication", "development"],
            key_phrases=[
                "password validation",
                "8-character minimum",
                "optional feature",
            ],
            content_type_context="Implementation guide for password validation",
        ),
    ]


# Export functions for easy access
__all__ = [
    "create_generic_healthcare_docs",
    "create_cross_platform_docs",
    "create_comprehensive_test_dataset",
    "create_conflicting_docs",
]
