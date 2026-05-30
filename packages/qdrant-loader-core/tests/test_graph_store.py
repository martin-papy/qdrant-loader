from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from qdrant_loader_core.graph import FalkorGraphStore, GraphEdge, GraphNode


# Async-compatible mock result wrapper
class MockResult:
    def __init__(self, result_set=None):
        self.result_set = result_set or []

    def __await__(self):
        async def _():
            return self

        return _().__await__()


@pytest_asyncio.fixture
async def store():
    # Mock FalkorDB before creating store
    mock_db = MagicMock()
    mock_graph = MagicMock()
    mock_db.select_graph.return_value = mock_graph

    def default_query(query, params=None):
        return MockResult([])

    mock_graph.query = default_query

    with patch("qdrant_loader_core.graph.falkor_store.FalkorDB", return_value=mock_db):
        s = FalkorGraphStore(
            host="localhost",
            port=6379,
            graph_name="test_graph",
        )

    return s


# -------------------------
# Test: upsert node idempotency
# -------------------------
@pytest.mark.asyncio
async def test_upsert_node_idempotent(store):
    node = GraphNode(id="doc_1", label="Document", properties={"title": "Test"})

    queries = []

    def mock_query(q, p=None):
        queries.append(q)
        return MockResult([])

    store._graph.query = mock_query

    await store.upsert_node(node)
    await store.upsert_node(node)

    assert len(queries) == 2
    assert all("MERGE" in q for q in queries)
    assert all("CREATE " not in q for q in queries)


# -------------------------
# Test: upsert edge idempotency
# -------------------------
@pytest.mark.asyncio
async def test_upsert_edge_idempotent(store):
    node1 = GraphNode(id="doc_1", label="Document", properties={})
    node2 = GraphNode(id="person_1", label="Person", properties={})

    queries = []

    def mock_query(q, p=None):
        queries.append(q)
        return MockResult([])

    store._graph.query = mock_query

    await store.upsert_nodes_batch([node1, node2])

    edge = GraphEdge(
        source="doc_1",
        target="person_1",
        edge_type="AUTHORED_BY",
        properties={"role": "author"},
    )

    await store.upsert_edge(edge)
    await store.upsert_edge(edge)

    # Ensure MERGE relationship is used
    edge_queries = [q for q in queries if "AUTHORED_BY" in q]
    assert len(edge_queries) == 2
    assert all("MERGE" in q for q in edge_queries)
    assert all("CREATE " not in q for q in edge_queries)


# -------------------------
# Test: neighbors mapping
# -------------------------
@pytest.mark.asyncio
async def test_neighbors_returns_graph_edge_and_nodes(store):
    class MockNode:
        def __init__(self, node_id, internal_id, label, props):
            self.id = internal_id
            self.labels = [label]
            self.properties = {"id": node_id, **props}

    class MockRelationship:
        def __init__(self, src, dst, rel_type, props):
            self.src_node = src
            self.dest_node = dst
            self.relation = rel_type
            self.properties = props

    n1 = MockNode("doc_1", 1, "Document", {"title": "Test"})
    n2 = MockNode("person_1", 2, "Person", {"name": "Alice"})
    rel = MockRelationship(1, 2, "AUTHORED_BY", {"role": "author"})

    def mock_query(q, p=None):
        return MockResult([(n1, [rel], n2)])

    store._graph.query = mock_query

    subgraph = await store.neighbors("doc_1", depth=1)

    assert len(subgraph.nodes) == 2
    assert len(subgraph.edges) == 1

    edge = subgraph.edges[0]
    assert edge.source == "doc_1"
    assert edge.target == "person_1"
    assert edge.edge_type == "AUTHORED_BY"
    assert edge.properties == {"role": "author"}


# -------------------------
# Test: neighbors with project filter
# -------------------------
@pytest.mark.asyncio
async def test_neighbors_filters_by_project(store):
    class MockNode:
        def __init__(self, node_id, internal_id, label, props):
            self.id = internal_id
            self.labels = [label]
            self.properties = {"id": node_id, **props}

    class MockRelationship:
        def __init__(self, src, dst, rel_type, props):
            self.src_node = src
            self.dest_node = dst
            self.relation = rel_type
            self.properties = props

    n1 = MockNode("doc_1", 1, "Document", {"project": "project-a"})
    n2 = MockNode("doc_2", 2, "Document", {"project": "project-a"})
    rel = MockRelationship(1, 2, "LINKS_TO", {"relationship": "same-project"})

    def mock_query(q, p=None):
        return MockResult([(n1, [rel], n2)])

    store._graph.query = mock_query

    subgraph = await store.neighbors("doc_1", depth=1, project="project-a")

    assert len(subgraph.nodes) == 2
    assert len(subgraph.edges) == 1
    assert subgraph.edges[0].target == "doc_2"


# -------------------------
# Test: export graph filtering
# -------------------------
@pytest.mark.asyncio
async def test_export_graph_filters_by_project(store):
    calls = {"count": 0}

    def mock_query(q, p=None):
        calls["count"] += 1

        # First query: fetch nodes
        if calls["count"] == 1:
            return MockResult([["doc_1"]])

        # Second query: fetch edges
        return MockResult([])

    store._graph.query = mock_query

    nodes, edges = await store.export_graph(project="project-a")

    assert nodes == [{"id": "doc_1"}]
    assert edges == []
