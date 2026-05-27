import pytest
import pytest_asyncio
from qdrant_loader_core.graph import FalkorGraphStore, GraphEdge, GraphNode


@pytest_asyncio.fixture
async def store():
    s = FalkorGraphStore(host="localhost", port=6379, graph_name="test_graph")
    await s.query_cypher("MATCH (n) DETACH DELETE n", {})
    return s


@pytest.mark.asyncio
async def test_upsert_node_idempotent(store):
    node = GraphNode(id="doc_1", label="Document", properties={"title": "Test"})

    await store.upsert_node(node)
    await store.upsert_node(node)

    result = await store.query_cypher(
        "MATCH (n:Document {id:'doc_1'}) RETURN count(n)", {}
    )

    assert result[0][0] == 1


@pytest.mark.asyncio
async def test_upsert_edge_idempotent(store):
    node1 = GraphNode(id="doc_1", label="Document", properties={})
    node2 = GraphNode(id="person_1", label="Person", properties={})

    await store.upsert_nodes_batch([node1, node2])

    edge = GraphEdge(
        source="doc_1",
        target="person_1",
        edge_type="AUTHORED_BY",
        properties={"role": "author"},
    )

    await store.upsert_edge(edge)
    await store.upsert_edge(edge)  # retry

    result = await store.query_cypher(
        "MATCH ()-[r:AUTHORED_BY]->() RETURN count(r)", {}
    )

    assert result[0][0] == 1


@pytest.mark.asyncio
async def test_neighbors_returns_graph_edge_and_nodes(store):
    node1 = GraphNode(id="doc_1", label="Document", properties={"title": "Test"})
    node2 = GraphNode(id="person_1", label="Person", properties={"name": "Alice"})

    await store.upsert_nodes_batch([node1, node2])

    edge = GraphEdge(
        source="doc_1",
        target="person_1",
        edge_type="AUTHORED_BY",
        properties={"role": "author"},
    )

    await store.upsert_edge(edge)

    subgraph = await store.neighbors("doc_1", depth=1)

    assert len(subgraph.nodes) == 2
    assert len(subgraph.edges) == 1
    assert subgraph.edges[0].source == "doc_1"
    assert subgraph.edges[0].target == "person_1"
    assert subgraph.edges[0].type == "AUTHORED_BY"
    assert subgraph.edges[0].properties == {"role": "author"}


@pytest.mark.asyncio
async def test_neighbors_filters_by_project(store):
    node1 = GraphNode(
        id="doc_1",
        label="Document",
        project="project-a",
        properties={"title": "Project A Doc", "project": "project-a"},
    )
    node2 = GraphNode(
        id="doc_2",
        label="Document",
        project="project-a",
        properties={"title": "Project A Neighbor", "project": "project-a"},
    )
    node3 = GraphNode(
        id="doc_3",
        label="Document",
        project="project-b",
        properties={"title": "Project B Doc", "project": "project-b"},
    )

    await store.upsert_nodes_batch([node1, node2, node3])

    edge_a = GraphEdge(
        source="doc_1",
        target="doc_2",
        edge_type="LINKS_TO",
        project="project-a",
        properties={"relationship": "same-project"},
    )
    edge_b = GraphEdge(
        source="doc_1",
        target="doc_3",
        edge_type="LINKS_TO",
        project="project-a",
        properties={"relationship": "cross-project"},
    )

    await store.upsert_edge(edge_a)
    # This edge should not be created because doc_3 does not belong to project-a
    await store.upsert_edge(edge_b)

    subgraph = await store.neighbors("doc_1", depth=1, project="project-a")

    assert len(subgraph.nodes) == 2
    assert len(subgraph.edges) == 1
    assert subgraph.edges[0].source == "doc_1"
    assert subgraph.edges[0].target == "doc_2"
    assert subgraph.edges[0].properties == {"relationship": "same-project"}


@pytest.mark.asyncio
async def test_export_graph_filters_by_project(store):
    node1 = GraphNode(
        id="doc_1",
        label="Document",
        project="project-a",
        properties={"title": "Project A Doc", "project": "project-a"},
    )
    node2 = GraphNode(
        id="doc_2",
        label="Document",
        project="project-b",
        properties={"title": "Project B Doc", "project": "project-b"},
    )

    await store.upsert_nodes_batch([node1, node2])

    edge = GraphEdge(
        source="doc_1",
        target="doc_2",
        edge_type="LINKS_TO",
        project="project-a",
        properties={"relationship": "cross-project"},
    )

    await store.upsert_edge(edge)

    nodes, edges = await store.export_graph(project="project-a")
    assert nodes == [{"id": "doc_1"}]
    assert edges == []
