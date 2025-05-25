"""Tests for the MarkdownChunkingStrategy class."""

import pytest
from qdrant_loader.config import GlobalConfig, SemanticAnalysisConfig, Settings
from qdrant_loader.core.chunking.strategy.markdown_strategy import (
    MarkdownChunkingStrategy,
)
from qdrant_loader.core.document import Document


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        # Qdrant configuration
        QDRANT_URL="http://localhost:6333",
        QDRANT_API_KEY="test-key",
        QDRANT_COLLECTION_NAME="test-collection",
        # OpenAI configuration
        OPENAI_API_KEY="test-key",
        # State management
        STATE_DB_PATH=":memory:",
        # Git repository configuration
        REPO_TOKEN="test-token",
        REPO_URL="https://github.com/test/repo",
        # Confluence configuration
        CONFLUENCE_URL="https://test.atlassian.net",
        CONFLUENCE_SPACE_KEY="TEST",
        CONFLUENCE_TOKEN="test-token",
        CONFLUENCE_EMAIL="test@example.com",
        # Jira configuration
        JIRA_URL="https://test.atlassian.net",
        JIRA_PROJECT_KEY="TEST",
        JIRA_TOKEN="test-token",
        JIRA_EMAIL="test@example.com",
        # Global configuration
        global_config=GlobalConfig(
            semantic_analysis=SemanticAnalysisConfig(num_topics=3, lda_passes=10)
        ),
    )


@pytest.fixture
def markdown_strategy(settings):
    """Create a MarkdownChunkingStrategy instance for testing."""
    return MarkdownChunkingStrategy(settings)


def test_chunk_document_with_headers(markdown_strategy):
    """Test chunking a document with headers."""
    content = """# Introduction
This is the introduction.

## Section 1
Content for section 1.

### Subsection 1.1
Content for subsection 1.1.

## Section 2
Content for section 2.
"""
    document = Document(
        content=content,
        source="test.md",
        source_type="markdown",
        url="file://test.md",
        content_type="text/markdown",
        title="Test Document",
        metadata={},
    )

    chunks = markdown_strategy.chunk_document(document)

    assert len(chunks) == 4  # Introduction + 2 sections + 1 subsection
    assert chunks[0].metadata["section_title"] == "Introduction"
    assert chunks[1].metadata["section_title"] == "Section 1"
    assert chunks[2].metadata["section_title"] == "Subsection 1.1"
    assert chunks[3].metadata["section_title"] == "Section 2"

    # Check that topic analysis was performed
    assert "topic_analysis" in chunks[0].metadata
    assert isinstance(chunks[0].metadata["topic_analysis"], dict)
    assert "topics" in chunks[0].metadata["topic_analysis"]
    assert "coherence" in chunks[0].metadata["topic_analysis"]


def test_chunk_document_without_headers(markdown_strategy):
    """Test chunking a document without headers."""
    content = "This is a document without headers.\nIt has multiple lines."
    document = Document(
        content=content,
        source="test.md",
        source_type="markdown",
        url="file://test.md",
        content_type="text/markdown",
        title="Test Document",
        metadata={},
    )

    chunks = markdown_strategy.chunk_document(document)

    assert len(chunks) == 1
    assert chunks[0].metadata["section_title"] == "Introduction"
    assert "topic_analysis" in chunks[0].metadata


def test_chunk_document_with_cross_references(markdown_strategy):
    """Test chunking a document with cross-references."""
    content = """# Section 1
This section has a [link](https://example.com) and a reference to [Section 2](#section-2).

# Section 2
This section has a reference back to [Section 1](#section-1).
"""
    document = Document(
        content=content,
        source="test.md",
        source_type="markdown",
        url="file://test.md",
        content_type="text/markdown",
        title="Test Document",
        metadata={},
    )

    chunks = markdown_strategy.chunk_document(document)

    assert len(chunks) == 2
    assert len(chunks[0].metadata["cross_references"]) == 2
    assert len(chunks[1].metadata["cross_references"]) == 1


def test_chunk_document_with_entities(markdown_strategy):
    """Test chunking a document with named entities."""
    content = """# Introduction
This document mentions Google and Microsoft, which are companies in the United States.
"""
    document = Document(
        content=content,
        source="test.md",
        source_type="markdown",
        url="file://test.md",
        content_type="text/markdown",
        title="Test Document",
        metadata={},
    )

    chunks = markdown_strategy.chunk_document(document)

    assert len(chunks) == 1
    entities = chunks[0].metadata["entities"]
    assert len(entities) > 0
    assert any(e["text"] == "Google" for e in entities)
    assert any(e["text"] == "Microsoft" for e in entities)
    assert any(e["text"] == "United States" for e in entities)


def test_chunk_document_with_hierarchy(markdown_strategy):
    """Test chunking a document with hierarchical structure."""
    content = """# Main Section
Content for main section.

## Subsection 1
Content for subsection 1.

### Subsubsection 1.1
Content for subsubsection 1.1.

## Subsection 2
Content for subsection 2.
"""
    document = Document(
        content=content,
        source="test.md",
        source_type="markdown",
        url="file://test.md",
        content_type="text/markdown",
        title="Test Document",
        metadata={},
    )

    chunks = markdown_strategy.chunk_document(document)

    assert len(chunks) == 4
    hierarchy = chunks[0].metadata["hierarchy"]
    assert "Main Section" in hierarchy
    assert "Subsection 1" in hierarchy["Main Section"]
    assert "Subsection 2" in hierarchy["Main Section"]


def test_chunk_document_with_small_corpus(markdown_strategy):
    """Test chunking a document with small corpus (less than 5 chunks)."""
    content = """# Section 1
Content for section 1.

# Section 2
Content for section 2.
"""
    document = Document(
        content=content,
        source="test.md",
        source_type="markdown",
        url="file://test.md",
        content_type="text/markdown",
        title="Test Document",
        metadata={},
    )

    chunks = markdown_strategy.chunk_document(document)

    assert len(chunks) == 2
    # Topic analysis should still be performed, but with a warning
    assert "topic_analysis" in chunks[0].metadata
    assert "topic_analysis" in chunks[1].metadata
