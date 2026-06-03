from qdrant_loader_core.graph.models import GraphNode, GraphEdge, SubGraph

import pytest
from unittest.mock import AsyncMock

from qdrant_loader_core.graph.store import GraphStore


class DummyGraphStore(GraphStore):
    def __init__(self):
        self.upsert_node = AsyncMock()
        self.upsert_edge = AsyncMock()
        self.upsert_nodes_batch = AsyncMock()
        self.upsert_edges_batch = AsyncMock()
        self.neighbors = AsyncMock()
        self.query_cypher = AsyncMock()

    @pytest.mark.asyncio
    async def test_upsert_node_called():
        store = DummyGraphStore()

        node = GraphNode(id="1", label="Test")

        await store.upsert_node(node)

        store.upsert_node.assert_awaited_once_with(node)

    @pytest.mark.asyncio
    async def test_upsert_edge_called():
        store = DummyGraphStore()

        edge = GraphEdge(source="1", target="2", edge_type="REL")

        await store.upsert_edge(edge)

        store.upsert_edge.assert_awaited_once_with(edge)

    @pytest.mark.asyncio
    async def test_upsert_nodes_batch():
        store = DummyGraphStore()

        nodes = [
            GraphNode(id="1", label="A"),
            GraphNode(id="2", label="B"),
        ]

        await store.upsert_nodes_batch(nodes)

        store.upsert_nodes_batch.assert_awaited_once_with(nodes)

    @pytest.mark.asyncio
    async def test_upsert_edges_batch():
        store = DummyGraphStore()

        edges = [GraphEdge(source="1", target="2", edge_type="REL")]

        await store.upsert_edges_batch(edges)

        store.upsert_edges_batch.assert_awaited_once_with(edges)

    @pytest.mark.asyncio
    async def test_neighbors():
        store = DummyGraphStore()

        expected = SubGraph(nodes=[], edges=[])

        store.neighbors.return_value = expected

        result = await store.neighbors(
            node_id="1",
            depth=2,
            edge_types=["REL"],
            project="test",
        )

        assert result == expected
        store.neighbors.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_query_cypher():
        store = DummyGraphStore()

        expected = [{"a": 1}]
        store.query_cypher.return_value = expected

        result = await store.query_cypher(
            "MATCH (n) RETURN n",
            {},
        )

        assert result == expected
        store.query_cypher.assert_awaited_once_with("MATCH (n) RETURN n", {})
