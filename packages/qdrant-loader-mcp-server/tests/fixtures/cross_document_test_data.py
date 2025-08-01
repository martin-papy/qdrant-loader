"""Test fixtures for cross-document intelligence testing."""

from typing import List
from qdrant_loader_mcp_server.search.components.search_result_models import HybridSearchResult, create_hybrid_search_result


def create_authentication_docs() -> List[HybridSearchResult]:
    """Create a cluster of related authentication documents."""
    return [
        create_hybrid_search_result(
            score=0.95,
            text="OAuth 2.0 implementation guide with JWT tokens for microservices architecture. This document provides comprehensive security best practices including token expiration policies, refresh token handling, and secure storage mechanisms.",
            source_type="confluence",
            source_title="OAuth 2.0 Implementation Guide",
            source_url="https://docs.company.com/oauth-guide",
            project_id="healthcare_platform",
            project_name="Healthcare Platform",
            entities=[
                {"text": "OAuth 2.0", "label": "TECHNOLOGY"},
                {"text": "JWT", "label": "TECHNOLOGY"}, 
                {"text": "microservices", "label": "ARCHITECTURE"},
                {"text": "security", "label": "CONCEPT"}
            ],
            topics=[
                {"text": "authentication", "score": 0.95},
                {"text": "security", "score": 0.90},
                {"text": "microservices", "score": 0.80}
            ],
            has_code_blocks=True,
            has_tables=True,
            has_links=True,
            word_count=2500,
            estimated_read_time=12,
            depth=2,
            breadcrumb_text="Technical Documentation > Security > Authentication",
            cross_references=[
                {"text": "JWT Best Practices", "url": "/docs/jwt-practices"},
                {"text": "Security Audit Checklist", "url": "/docs/security-audit"}
            ]
        ),
        
        create_hybrid_search_result(
            score=0.90,
            text="JWT token implementation with Node.js Express framework. Code examples for token generation, validation, middleware integration, and refresh token rotation. Includes performance optimization tips.",
            source_type="git",
            source_title="JWT Node.js Implementation",
            source_url="https://github.com/company/auth-service/jwt-impl.js",
            project_id="healthcare_platform",
            project_name="Healthcare Platform",
            entities=[
                {"text": "JWT", "label": "TECHNOLOGY"},
                {"text": "Node.js", "label": "TECHNOLOGY"},
                {"text": "Express", "label": "FRAMEWORK"},
                {"text": "middleware", "label": "PATTERN"}
            ],
            topics=[
                {"text": "implementation", "score": 0.95},
                {"text": "nodejs", "score": 0.90},
                {"text": "authentication", "score": 0.85}
            ],
            has_code_blocks=True,
            has_tables=False,
            has_links=False,
            word_count=1800,
            estimated_read_time=9,
            depth=3,
            breadcrumb_text="Code Repository > Backend > Authentication Service"
        ),
        
        create_hybrid_search_result(
            score=0.88,
            text="Healthcare mobile application authentication requirements including biometric login, social OAuth integration, and offline authentication capabilities. Security requirements specify token expiry of 24 hours.",
            source_type="confluence",
            source_title="Mobile Healthcare Auth Requirements",
            source_url="https://docs.company.com/mobile-auth-req",
            project_id="healthcare_platform", 
            project_name="Healthcare Platform",
            entities=[
                {"text": "Healthcare Platform", "label": "ORG"},
                {"text": "mobile application", "label": "PRODUCT"},
                {"text": "biometric login", "label": "FEATURE"},
                {"text": "social OAuth", "label": "FEATURE"}
            ],
            topics=[
                {"text": "requirements", "score": 0.95},
                {"text": "mobile", "score": 0.90},
                {"text": "authentication", "score": 0.85}
            ],
            has_code_blocks=False,
            has_tables=True,
            has_links=True,
            word_count=3200,
            estimated_read_time=16,
            depth=1,
            breadcrumb_text="Product Requirements > Mobile Application"
        )
    ]


def create_database_docs() -> List[HybridSearchResult]:
    """Create a cluster of database-related documents."""
    return [
        create_hybrid_search_result(
            score=0.85,
            text="User management database schema design with tables for users, roles, permissions, authentication sessions, and audit logs. Includes indexing strategies and performance considerations for high-scale systems.",
            source_type="confluence",
            source_title="User Database Schema Design",
            source_url="https://docs.company.com/db-schema",
            project_id="healthcare_platform",
            project_name="Healthcare Platform", 
            entities=[
                {"text": "database schema", "label": "DESIGN"},
                {"text": "user management", "label": "SYSTEM"},
                {"text": "permissions", "label": "CONCEPT"},
                {"text": "audit logs", "label": "FEATURE"}
            ],
            topics=[
                {"text": "database", "score": 0.95},
                {"text": "schema", "score": 0.90},
                {"text": "users", "score": 0.85}
            ],
            has_code_blocks=True,
            has_tables=True,
            has_links=False,
            word_count=2100,
            estimated_read_time=10,
            depth=2,
            breadcrumb_text="Technical Documentation > Database > Schema Design"
        ),
        
        create_hybrid_search_result(
            score=0.82,
            text="Microservices architecture patterns for healthcare platform including service mesh configuration, API gateway setup, and inter-service communication protocols using REST and GraphQL.",
            source_type="confluence",
            source_title="Microservices Architecture Overview",
            source_url="https://docs.company.com/microservices-arch",
            project_id="healthcare_platform",
            project_name="Healthcare Platform",
            entities=[
                {"text": "microservices", "label": "ARCHITECTURE"},
                {"text": "service mesh", "label": "PATTERN"},
                {"text": "API gateway", "label": "COMPONENT"},
                {"text": "GraphQL", "label": "TECHNOLOGY"}
            ],
            topics=[
                {"text": "architecture", "score": 0.95},
                {"text": "microservices", "score": 0.90},
                {"text": "api design", "score": 0.80}
            ],
            has_code_blocks=False,
            has_tables=True,
            has_links=True,
            word_count=2800,
            estimated_read_time=14,
            depth=1,
            breadcrumb_text="Architecture > System Design"
        )
    ]


def create_conflicting_docs() -> List[HybridSearchResult]:
    """Create documents with conflicting information for conflict detection testing."""
    return [
        create_hybrid_search_result(
            score=0.88,
            text="Healthcare mobile application authentication requirements including biometric login, social OAuth integration, and offline authentication capabilities. Security requirements specify token expiry of 24 hours.",
            source_type="confluence",
            source_title="Mobile Healthcare Auth Requirements",
            source_url="https://docs.company.com/mobile-auth-req",
            project_id="healthcare_platform", 
            project_name="Healthcare Platform",
            entities=[
                {"text": "token expiry", "label": "POLICY"},
                {"text": "24 hours", "label": "DURATION"}
            ],
            topics=[
                {"text": "requirements", "score": 0.95},
                {"text": "security", "score": 0.80}
            ],
            has_code_blocks=False,
            has_tables=True,
            has_links=True,
            word_count=3200,
            estimated_read_time=16
        ),
        
        create_hybrid_search_result(
            score=0.80,
            text="Security audit findings and recommendations for authentication system. CRITICAL: Token expiry should be reduced to 4 hours maximum for enhanced security. Previous 24-hour expiry policy is insufficient for current threat landscape.",
            source_type="confluence",
            source_title="Q4 Security Audit Report", 
            source_url="https://docs.company.com/security-audit-q4",
            project_id="healthcare_platform",
            project_name="Healthcare Platform",
            entities=[
                {"text": "security audit", "label": "PROCESS"},
                {"text": "token expiry", "label": "POLICY"},
                {"text": "4 hours", "label": "DURATION"},
                {"text": "24-hour", "label": "DURATION"}
            ],
            topics=[
                {"text": "security", "score": 0.95},
                {"text": "audit", "score": 0.90},
                {"text": "recommendations", "score": 0.85}
            ],
            has_code_blocks=False,
            has_tables=True,
            has_links=True,
            word_count=1500,
            estimated_read_time=7
        )
    ]


def create_cross_project_docs() -> List[HybridSearchResult]:
    """Create documents from different projects for cross-project analysis."""
    return [
        create_hybrid_search_result(
            score=0.78,
            text="Enterprise OAuth implementation patterns and security best practices from the business platform project. Includes lessons learned and recommended token management strategies for multi-tenant applications.",
            source_type="confluence",
            source_title="Business Platform OAuth Lessons Learned",
            source_url="https://docs.company.com/business-platform-oauth",
            project_id="business_platform",
            project_name="Business Platform",
            entities=[
                {"text": "OAuth", "label": "TECHNOLOGY"},
                {"text": "multi-tenant", "label": "ARCHITECTURE"},
                {"text": "token management", "label": "PATTERN"},
                {"text": "enterprise", "label": "SCALE"}
            ],
            topics=[
                {"text": "oauth", "score": 0.90},
                {"text": "enterprise", "score": 0.85},
                {"text": "lessons learned", "score": 0.80}
            ],
            has_code_blocks=False,
            has_tables=False,
            has_links=True,
            word_count=1200,
            estimated_read_time=6,
            depth=1,
            breadcrumb_text="Projects > Business Platform > Architecture"
        ),
        
        create_hybrid_search_result(
            score=0.75,
            text="React Native authentication components for healthcare mobile app. Includes biometric authentication integration, social login buttons, and secure token storage using device keychain.",
            source_type="git",
            source_title="React Native Auth Components",
            source_url="https://github.com/company/healthcare-mobile/auth-components",
            project_id="healthcare_platform",
            project_name="Healthcare Platform",
            entities=[
                {"text": "React Native", "label": "FRAMEWORK"},
                {"text": "biometric authentication", "label": "FEATURE"},
                {"text": "keychain", "label": "SECURITY"},
                {"text": "mobile app", "label": "PRODUCT"}
            ],
            topics=[
                {"text": "frontend", "score": 0.90},
                {"text": "mobile", "score": 0.85},
                {"text": "authentication", "score": 0.80}
            ],
            has_code_blocks=True,
            has_tables=False,
            has_links=False,
            word_count=950,
            estimated_read_time=5,
            depth=3,
            breadcrumb_text="Code Repository > Frontend > Mobile Components"
        )
    ]


def create_tutorial_docs() -> List[HybridSearchResult]:
    """Create tutorial and documentation for complementary content testing."""
    return [
        create_hybrid_search_result(
            score=0.72,
            text="Step-by-step authentication integration tutorial for new developers. Covers OAuth flow, JWT handling, error scenarios, and testing strategies. Includes postman collection and environment setup.",
            source_type="confluence",
            source_title="Authentication Integration Tutorial",
            source_url="https://docs.company.com/auth-tutorial",
            project_id="healthcare_platform",
            project_name="Healthcare Platform",
            entities=[
                {"text": "tutorial", "label": "CONTENT"},
                {"text": "OAuth flow", "label": "PROCESS"},
                {"text": "postman collection", "label": "TOOL"},
                {"text": "testing strategies", "label": "METHODOLOGY"}
            ],
            topics=[
                {"text": "tutorial", "score": 0.95},
                {"text": "integration", "score": 0.85},
                {"text": "testing", "score": 0.75}
            ],
            has_code_blocks=True,
            has_tables=False,
            has_links=True,
            word_count=1600,
            estimated_read_time=8,
            depth=2,
            breadcrumb_text="Documentation > Tutorials > Authentication"
        )
    ]


def create_comprehensive_test_dataset() -> List[HybridSearchResult]:
    """Create a comprehensive dataset combining all test document types."""
    docs = []
    docs.extend(create_authentication_docs())
    docs.extend(create_database_docs())
    docs.extend(create_conflicting_docs())
    docs.extend(create_cross_project_docs())
    docs.extend(create_tutorial_docs())
    return docs


def create_minimal_test_dataset() -> List[HybridSearchResult]:
    """Create a minimal dataset for quick unit tests."""
    return [
        create_hybrid_search_result(
            score=0.9,
            text="OAuth 2.0 authentication with JWT tokens",
            source_type="confluence",
            source_title="OAuth Guide",
            source_url="https://docs.company.com/oauth",
            project_id="healthcare_platform",
            entities=[{"text": "OAuth", "label": "TECHNOLOGY"}],
            topics=[{"text": "authentication", "score": 0.9}]
        ),
        create_hybrid_search_result(
            score=0.8,
            text="JWT implementation in Node.js",
            source_type="git", 
            source_title="JWT Implementation",
            source_url="https://github.com/company/jwt",
            project_id="healthcare_platform",
            entities=[{"text": "JWT", "label": "TECHNOLOGY"}],
            topics=[{"text": "implementation", "score": 0.8}]
        )
    ] 