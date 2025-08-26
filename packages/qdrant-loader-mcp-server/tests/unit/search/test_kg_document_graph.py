"""Tests for Document Knowledge Graph Interface."""

from qdrant_loader_mcp_server.search.enhanced.kg import DocumentKnowledgeGraph


def test_document_knowledge_graph_import():
    """Test that DocumentKnowledgeGraph can be imported successfully."""
    assert DocumentKnowledgeGraph is not None


def test_document_knowledge_graph_initialization():
    """Test that DocumentKnowledgeGraph can be initialized."""
    dkg = DocumentKnowledgeGraph()

    assert dkg is not None
    assert dkg.spacy_analyzer is not None
    assert dkg.graph_builder is not None
    assert dkg.knowledge_graph is None  # Not built yet
    assert dkg.traverser is None  # Not built yet


def test_document_knowledge_graph_with_custom_analyzer():
    """Test DocumentKnowledgeGraph initialization with custom spacy analyzer."""

    # Mock a simple spacy analyzer
    class MockSpaCyAnalyzer:
        def __init__(self):
            self.initialized = True

    mock_analyzer = MockSpaCyAnalyzer()
    dkg = DocumentKnowledgeGraph(spacy_analyzer=mock_analyzer)

    assert dkg is not None
    assert dkg.spacy_analyzer is mock_analyzer
    assert dkg.spacy_analyzer.initialized is True


def test_document_knowledge_graph_build_empty():
    """Test building graph with empty search results."""
    dkg = DocumentKnowledgeGraph()

    # Test with empty search results
    result = dkg.build_graph([])

    assert result is True  # Should succeed even with empty results
    assert dkg.knowledge_graph is not None
    assert dkg.traverser is not None


def test_document_knowledge_graph_find_related_content_no_graph():
    """Test finding related content without built graph."""
    dkg = DocumentKnowledgeGraph()

    # Don't build graph
    results = dkg.find_related_content("test query")

    assert results == []


def test_document_knowledge_graph_statistics():
    """Test getting graph statistics."""
    dkg = DocumentKnowledgeGraph()

    # Before building graph
    stats = dkg.get_graph_statistics()
    assert stats is None

    # After building empty graph
    dkg.build_graph([])
    stats = dkg.get_graph_statistics()
    assert stats is not None
    assert "total_nodes" in stats
