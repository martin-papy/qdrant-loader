"""Tests for Knowledge Graph Core Implementation."""

from qdrant_loader_mcp_server.search.enhanced.kg import (
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
    NodeType,
    RelationshipType,
)


def test_knowledge_graph_import():
    """Test that KnowledgeGraph can be imported successfully."""
    assert KnowledgeGraph is not None


def test_knowledge_graph_initialization():
    """Test that KnowledgeGraph can be initialized."""
    kg = KnowledgeGraph()

    assert kg is not None
    assert hasattr(kg, "nodes")
    assert hasattr(kg, "edges")
    assert hasattr(kg, "graph")
    assert len(kg.nodes) == 0
    assert len(kg.edges) == 0


def test_knowledge_graph_add_node():
    """Test adding a node to the knowledge graph."""
    kg = KnowledgeGraph()

    node = GraphNode(
        id="test_node",
        node_type=NodeType.DOCUMENT,
        title="Test Document",
        content="Test content",
    )

    result = kg.add_node(node)
    assert result is True
    assert len(kg.nodes) == 1
    assert "test_node" in kg.nodes
    assert kg.nodes["test_node"] is node


def test_knowledge_graph_add_edge():
    """Test adding an edge between two nodes."""
    kg = KnowledgeGraph()

    # Create two nodes
    node1 = GraphNode(id="node1", node_type=NodeType.DOCUMENT, title="Doc 1")
    node2 = GraphNode(id="node2", node_type=NodeType.SECTION, title="Section 1")

    kg.add_node(node1)
    kg.add_node(node2)

    # Create edge
    edge = GraphEdge(
        source_id="node1",
        target_id="node2",
        relationship_type=RelationshipType.CONTAINS,
        weight=1.0,
    )

    result = kg.add_edge(edge)
    assert result is True
    assert len(kg.edges) == 1


def test_knowledge_graph_find_nodes_by_type():
    """Test finding nodes by type."""
    kg = KnowledgeGraph()

    doc_node = GraphNode(id="doc", node_type=NodeType.DOCUMENT, title="Document")
    section_node = GraphNode(id="section", node_type=NodeType.SECTION, title="Section")

    kg.add_node(doc_node)
    kg.add_node(section_node)

    doc_nodes = kg.find_nodes_by_type(NodeType.DOCUMENT)
    section_nodes = kg.find_nodes_by_type(NodeType.SECTION)

    assert len(doc_nodes) == 1
    assert len(section_nodes) == 1
    assert doc_nodes[0] is doc_node
    assert section_nodes[0] is section_node


def test_knowledge_graph_statistics():
    """Test graph statistics calculation."""
    kg = KnowledgeGraph()

    # Add some nodes
    node1 = GraphNode(id="n1", node_type=NodeType.DOCUMENT, title="Doc")
    node2 = GraphNode(id="n2", node_type=NodeType.SECTION, title="Section")

    kg.add_node(node1)
    kg.add_node(node2)

    stats = kg.get_statistics()

    assert stats["total_nodes"] == 2
    assert stats["total_edges"] == 0
    assert NodeType.DOCUMENT.value in stats["node_types"]
    assert NodeType.SECTION.value in stats["node_types"]
