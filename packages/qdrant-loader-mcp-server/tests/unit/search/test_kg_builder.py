"""Tests for Knowledge Graph Builder."""

import pytest

from qdrant_loader_mcp_server.search.enhanced.kg import GraphBuilder, NodeType


def test_graph_builder_import():
    """Test that GraphBuilder can be imported successfully."""
    assert GraphBuilder is not None


def test_graph_builder_initialization():
    """Test that GraphBuilder can be initialized."""
    builder = GraphBuilder()
    
    assert builder is not None
    assert builder.spacy_analyzer is not None


def test_graph_builder_with_custom_analyzer():
    """Test GraphBuilder initialization with custom spacy analyzer."""
    # Mock a simple spacy analyzer
    class MockSpaCyAnalyzer:
        def __init__(self):
            self.initialized = True
    
    mock_analyzer = MockSpaCyAnalyzer()
    builder = GraphBuilder(spacy_analyzer=mock_analyzer)
    
    assert builder is not None
    assert builder.spacy_analyzer is mock_analyzer
    assert builder.spacy_analyzer.initialized is True


def test_graph_builder_build_empty():
    """Test building graph with empty search results."""
    builder = GraphBuilder()
    
    # Test with empty search results
    graph = builder.build_from_search_results([])
    
    assert graph is not None
    # Graph should be empty but valid
    assert hasattr(graph, 'nodes')


def test_graph_builder_document_nodes_creation():
    """Test document nodes creation from search results."""
    # Mock a simple search result with all required attributes
    class MockSearchResult:
        def __init__(self):
            self.source_type = "test"
            self.source_title = "Test Document"
            self.source_url = "http://test.com"
            self.text = "This is test content"
            self.project_id = "test_project"
            self.collection_name = "test_collection"
            self.section_title = "Test Section"
            self.parent_title = "Parent Document"
            self.breadcrumb_text = "Home > Test"
            self.section_level = 1
            self.depth = 2
            self.score = 0.5
            self.section_type = "content"
            self.project_name = "Test Project"
            self.hierarchy_context = "test context"
    
    builder = GraphBuilder()
    mock_results = [MockSearchResult()]
    
    # Test document nodes creation
    document_nodes = builder._create_document_nodes(mock_results)
    
    assert len(document_nodes) == 2  # One document node, one section node
    assert any(node.node_type == NodeType.DOCUMENT for node in document_nodes)
    assert any(node.node_type == NodeType.SECTION for node in document_nodes)
