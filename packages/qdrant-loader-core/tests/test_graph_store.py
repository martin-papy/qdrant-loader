from unittest.mock import AsyncMock

import pytest
from qdrant_loader_core.graph.models import GraphEdge, GraphNode, SubGraph
from qdrant_loader_core.graph.store import GraphStore


class DummyGraphStore(GraphStore):
    def __init__(self):
        self._upsert_node = AsyncMock()
        self._upsert_edge = AsyncMock()
        self._upsert_nodes_batch = AsyncMock()
        self._upsert_edges_batch = AsyncMock()
        self._neighbors = AsyncMock()
        self._query_cypher = AsyncMock()

    async def upsert_node(self, node):
        return await self._upsert_node(node)

    async def upsert_edge(self, edge):
        return await self._upsert_edge(edge)

    async def upsert_nodes_batch(self, nodes):
        return await self._upsert_nodes_batch(nodes)

    async def upsert_edges_batch(self, edges):
        return await self._upsert_edges_batch(edges)

    async def neighbors(self, **kwargs):
        return await self._neighbors(**kwargs)

    async def query_cypher(self, query, params):
        return await self._query_cypher(query, params)


@pytest.mark.asyncio
async def test_upsert_node_called():
    store = DummyGraphStore()

    node = GraphNode(id="1", label="Test")

    await store.upsert_node(node)

    store._upsert_node.assert_awaited_once_with(node)


@pytest.mark.asyncio
async def test_upsert_edge_called():
    store = DummyGraphStore()

    edge = GraphEdge(source="1", target="2", edge_type="REL")

    await store.upsert_edge(edge)

    store._upsert_edge.assert_awaited_once_with(edge)


@pytest.mark.asyncio
async def test_upsert_nodes_batch():
    store = DummyGraphStore()

    nodes = [
        GraphNode(id="1", label="A"),
        GraphNode(id="2", label="B"),
    ]

    await store.upsert_nodes_batch(nodes)

    store._upsert_nodes_batch.assert_awaited_once_with(nodes)


@pytest.mark.asyncio
async def test_upsert_edges_batch():
    store = DummyGraphStore()

    edges = [GraphEdge(source="1", target="2", edge_type="REL")]

    await store.upsert_edges_batch(edges)

    store._upsert_edges_batch.assert_awaited_once_with(edges)


@pytest.mark.asyncio
async def test_neighbors():
    store = DummyGraphStore()

    expected = SubGraph(nodes=[], edges=[])

    store._neighbors.return_value = expected

    result = await store.neighbors(
        node_id="1",
        depth=2,
        edge_types=["REL"],
        project="test",
    )

    assert result == expected
    store._neighbors.assert_awaited_once()


@pytest.mark.asyncio
async def test_query_cypher():
    store = DummyGraphStore()

    expected = [{"a": 1}]
    store._query_cypher.return_value = expected

    result = await store.query_cypher(
        "MATCH (n) RETURN n",
        {},
    )

    assert result == expected
    store._query_cypher.assert_awaited_once_with("MATCH (n) RETURN n", {})
