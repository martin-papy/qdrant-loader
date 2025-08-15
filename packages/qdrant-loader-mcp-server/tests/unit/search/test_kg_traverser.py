"""Tests for Knowledge Graph Traverser."""

import pytest

from qdrant_loader_mcp_server.search.enhanced.kg import GraphTraverser, TraversalStrategy


def test_graph_traverser_import():
    """Test that GraphTraverser can be imported successfully."""
    assert GraphTraverser is not None


def test_graph_traverser_initialization():
    """Test that GraphTraverser can be initialized."""
    # Mock a simple knowledge graph
    class MockGraph:
        nodes = {}
        
        def get_neighbors(self, node_id):
            return []
    
    mock_graph = MockGraph()
    traverser = GraphTraverser(mock_graph)
    
    assert traverser is not None
    assert traverser.graph is mock_graph
    assert traverser.spacy_analyzer is not None


def test_graph_traverser_traverse_empty():
    """Test traversal with empty start nodes."""
    class MockGraph:
        nodes = {}
        
        def get_neighbors(self, node_id):
            return []
    
    mock_graph = MockGraph()
    traverser = GraphTraverser(mock_graph)
    
    # Test with empty start nodes
    results = traverser.traverse([])
    assert results == []
    
    # Test with non-existent start node
    results = traverser.traverse(["non_existent"])
    assert results == []


def test_traversal_strategies():
    """Test that all traversal strategies are accessible."""
    strategies = [
        TraversalStrategy.BREADTH_FIRST,
        TraversalStrategy.WEIGHTED,
        TraversalStrategy.CENTRALITY,
        TraversalStrategy.SEMANTIC,
    ]
    
    for strategy in strategies:
        assert strategy is not None
