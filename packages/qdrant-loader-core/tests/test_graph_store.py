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
