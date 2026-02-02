"""
Test data for demonstrating the contextual embedding gap.

This module provides test documents and queries specifically designed to show
why contextual embeddings are necessary.

The documents are structured so that:
- Important topic keywords appear in document TITLES but not in chunk content
- Search queries using topic-level terms will FAIL without contextual embeddings
- Search queries using exact chunk terms will PASS (to show system isn't broken)

Usage:
    python -m pytest tests/integration/test_contextual_embedding_gap.py -v

Or run the standalone demo:
    python tests/scripts/demo_contextual_embedding_gap.py

Author: Nguyen Vu (nguyen.vu@cbtw.tech)
"""

from dataclasses import dataclass, field


@dataclass
class TestDocument:
    """A test document with expected chunking behavior."""

    title: str
    source_type: str
    source: str
    content: str
    expected_topics: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class TestQuery:
    """A test query with expected results and failure explanation."""

    query: str
    expected_doc_title: str
    expected_section: str
    should_pass_without_context: bool
    failure_reason: str = ""
    success_reason: str = ""


# =============================================================================
# TEST DOCUMENTS
# =============================================================================
# These documents are designed so that:
# - Document titles contain important topic keywords
# - Chunk content does NOT contain those keywords
# - This creates a retrieval gap that contextual embeddings solve

SECURITY_AUTH_GUIDE = TestDocument(
    title="API Security & Authentication Guide",
    source_type="confluence",
    source="https://wiki.example.com/security/api-auth-guide",
    expected_topics=["security", "authentication", "API", "access control"],
    description="Document about API security - but chunks don't say 'security' or 'authentication'",
    content="""# API Security & Authentication Guide

## Overview

This document covers securing your REST APIs and implementing proper access controls.
All developers should follow these guidelines when building new services.

## Token Management

Tokens should be rotated every 24 hours to minimize risk exposure. Store them in 
httpOnly cookies rather than localStorage to prevent XSS attacks. Always validate 
the signature before processing any request. Implement proper expiration handling
and refresh flows to maintain seamless user experience.

When a token expires, the client should automatically request a new one using the
refresh token. Never store sensitive data in the token payload.

## Session Handling

Sessions should timeout after 30 minutes of inactivity. Use secure, randomly 
generated session identifiers with at least 128 bits of entropy. Never expose 
internal database IDs in URLs or responses.

Implement proper session invalidation on logout. Clear all related cookies and
server-side session data.

## Rate Limiting

Implement progressive delays after failed attempts. Start with 1 second delay,
doubling after each failure. Block IPs after 10 consecutive failures within 
5 minutes. Use CAPTCHA challenges for suspicious patterns.

Monitor for distributed attacks that rotate source IPs. Consider implementing
account-level rate limiting in addition to IP-based limits.
""",
)

DEPLOYMENT_RUNBOOK = TestDocument(
    title="Production Deployment Runbook",
    source_type="confluence",
    source="https://wiki.example.com/ops/deployment-runbook",
    expected_topics=["deployment", "production", "release", "devops"],
    description="Document about deployments - chunks describe processes without using 'deployment'",
    content="""# Production Deployment Runbook

## Pre-deployment Checklist

Before starting, verify all environment variables are properly configured.
Run the full smoke test suite against staging. Create a database backup
and verify the restore procedure works.

Notify the on-call team about the planned release window. Update the
status page if this is a major release.

## Rolling Update Process

Gradually replace old pods with new ones to maintain availability. Ensure
at least 2 replicas remain healthy during the entire process. Monitor 
error rates and latency closely during the transition.

Use readiness probes to ensure traffic only routes to healthy instances.
Set appropriate surge and unavailable thresholds in the deployment spec.

If using blue-green strategy, validate the new environment thoroughly
before switching traffic. Keep the old environment available for quick
rollback.

## Rollback Procedure

If the error rate exceeds 5% or P99 latency doubles, immediately revert
to the previous version. Preserve all logs and metrics for post-mortem
analysis. Notify the on-call team and relevant stakeholders.

Document the failure mode and create follow-up tickets for investigation.
""",
)

DATABASE_OPTIMIZATION = TestDocument(
    title="Database Performance Optimization",
    source_type="confluence",
    source="https://wiki.example.com/eng/database-optimization",
    expected_topics=["database", "performance", "optimization", "SQL"],
    description="Document about database optimization - chunks discuss techniques without keyword",
    content="""# Database Performance Optimization

## Query Optimization

Add indexes on columns that are frequently used in WHERE clauses and JOIN
conditions. Avoid using SELECT * in production code - explicitly list needed
columns. Use EXPLAIN ANALYZE to identify slow queries and understand the
query plan.

Consider materialized views for complex aggregations that are read frequently
but updated rarely. Partition large tables by date or other natural boundaries.

## Connection Pooling

Maintain a pool of 20-50 connections depending on your workload pattern. Set
idle timeout to 5 minutes to reclaim unused connections. Monitor for connection
leaks using your APM tool.

Use PgBouncer in transaction mode for high-traffic scenarios with many short
queries. Configure appropriate pool size based on your database's max_connections
setting.

## Caching Strategy

Cache frequently accessed records for 5 minutes using a TTL-based approach.
Invalidate cache entries immediately on writes to maintain consistency.

Use Redis for distributed caching across multiple application instances.
Implement cache warming for critical data paths during deployment.
""",
)

# All test documents in a list for easy iteration
TEST_DOCUMENTS = [
    SECURITY_AUTH_GUIDE,
    DEPLOYMENT_RUNBOOK,
    DATABASE_OPTIMIZATION,
]


# =============================================================================
# QUERIES THAT WILL FAIL WITHOUT CONTEXTUAL EMBEDDINGS
# =============================================================================
# These queries use topic-level terms that appear in document titles
# but NOT in the actual chunk content

FAILING_QUERIES = [
    TestQuery(
        query="authentication best practices",
        expected_doc_title="API Security & Authentication Guide",
        expected_section="Token Management, Session Handling",
        should_pass_without_context=False,
        failure_reason=(
            "The word 'authentication' appears in the document TITLE but not in any chunk. "
            "Chunks discuss 'tokens', 'sessions', 'cookies' without saying 'authentication'. "
            "Vector search won't find semantic similarity between 'authentication' and chunk content."
        ),
    ),
    TestQuery(
        query="how to secure our API",
        expected_doc_title="API Security & Authentication Guide",
        expected_section="Token Management, Rate Limiting",
        should_pass_without_context=False,
        failure_reason=(
            "Neither 'secure' nor 'API' appear in the chunk text. "
            "The chunks talk about 'tokens', 'signatures', 'rate limiting' without using these terms."
        ),
    ),
    TestQuery(
        query="security guidelines for developers",
        expected_doc_title="API Security & Authentication Guide",
        expected_section="All sections",
        should_pass_without_context=False,
        failure_reason=(
            "The word 'security' is ONLY in the document title. "
            "No chunk contains 'security' or 'guidelines'. "
            "This is a common user search pattern that completely fails."
        ),
    ),
    TestQuery(
        query="what are our auth requirements",
        expected_doc_title="API Security & Authentication Guide",
        expected_section="Token Management, Session Handling",
        should_pass_without_context=False,
        failure_reason=(
            "'auth' is an abbreviation of 'authentication' which only appears in title. "
            "'requirements' doesn't appear anywhere in the content."
        ),
    ),
    TestQuery(
        query="deployment security checklist",
        expected_doc_title="Production Deployment Runbook",
        expected_section="Pre-deployment Checklist",
        should_pass_without_context=False,
        failure_reason=(
            "'security' doesn't appear in the deployment runbook at all. "
            "'deployment' only appears in the title, not in chunk content. "
            "The chunk talks about 'environment variables', 'smoke tests' etc."
        ),
    ),
    TestQuery(
        query="database security best practices",
        expected_doc_title="Database Performance Optimization",
        expected_section="Connection Pooling",
        should_pass_without_context=False,
        failure_reason=(
            "'security' doesn't appear in this document. "
            "'database' only appears in the title. "
            "Chunks discuss 'indexes', 'connections', 'caching' without context."
        ),
    ),
    TestQuery(
        query="API rate limiting configuration",
        expected_doc_title="API Security & Authentication Guide",
        expected_section="Rate Limiting",
        should_pass_without_context=False,
        failure_reason=(
            "'API' is only in the document title. "
            "The rate limiting chunk doesn't mention 'API' at all."
        ),
    ),
]


# =============================================================================
# QUERIES THAT WILL PASS (to prove system isn't broken)
# =============================================================================
# These queries use terms that ARE in the chunk content

PASSING_QUERIES = [
    TestQuery(
        query="token rotation policy",
        expected_doc_title="API Security & Authentication Guide",
        expected_section="Token Management",
        should_pass_without_context=True,
        success_reason="'tokens' and 'rotated' are directly in the chunk content.",
    ),
    TestQuery(
        query="how to handle session timeout",
        expected_doc_title="API Security & Authentication Guide",
        expected_section="Session Handling",
        should_pass_without_context=True,
        success_reason="'session' and 'timeout' are in the chunk content.",
    ),
    TestQuery(
        query="rolling update with readiness probes",
        expected_doc_title="Production Deployment Runbook",
        expected_section="Rolling Update Process",
        should_pass_without_context=True,
        success_reason="'rolling', 'readiness probes' are directly in chunk.",
    ),
    TestQuery(
        query="database connection pool configuration",
        expected_doc_title="Database Performance Optimization",
        expected_section="Connection Pooling",
        should_pass_without_context=True,
        success_reason="'connection', 'pool' are in the chunk content.",
    ),
    TestQuery(
        query="Redis caching strategy",
        expected_doc_title="Database Performance Optimization",
        expected_section="Caching Strategy",
        should_pass_without_context=True,
        success_reason="'Redis', 'caching' are directly in the chunk.",
    ),
]


# =============================================================================
# EXPECTED RESULTS WITH CONTEXTUAL EMBEDDINGS
# =============================================================================
# This shows what SHOULD happen after implementing contextual embeddings

CONTEXTUAL_EMBEDDING_FORMAT = """
[Document: {title} | Source: {source_type} | Topics: {topics}]

{chunk_content}
"""


def get_contextual_chunk(doc: TestDocument, chunk_content: str) -> str:
    """Format a chunk with contextual embedding prefix."""
    return CONTEXTUAL_EMBEDDING_FORMAT.format(
        title=doc.title,
        source_type=doc.source_type,
        topics=", ".join(doc.expected_topics),
        chunk_content=chunk_content,
    )


# Example of what contextual embedding would produce
EXAMPLE_CONTEXTUAL_CHUNK = """
[Document: API Security & Authentication Guide | Source: confluence | Topics: security, authentication, API, access control]

Tokens should be rotated every 24 hours to minimize risk exposure. Store them in 
httpOnly cookies rather than localStorage to prevent XSS attacks. Always validate 
the signature before processing any request.
"""
