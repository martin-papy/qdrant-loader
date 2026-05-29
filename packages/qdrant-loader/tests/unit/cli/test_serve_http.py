"""Unit tests for the CLI graph HTTP server clustering implementation."""

import asyncio

from qdrant_loader.cli.serve import http


class TestGraphClusteringHelpers:
    def test_build_graph_adjacency(self):
        nodes = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        edges = [{"source": "a", "target": "b"}, {"source": "b", "target": "c"}]

        adjacency = http._build_graph_adjacency(nodes, edges)

        assert adjacency == {
            "a": {"b"},
            "b": {"a", "c"},
            "c": {"b"},
        }

    def test_compute_graph_clusters_bridge_cut(self):
        nodes = [
            {"id": "a"},
            {"id": "b"},
            {"id": "c"},
            {"id": "d"},
            {"id": "e"},
            {"id": "f"},
        ]
        edges = [
            {"source": "a", "target": "b"},
            {"source": "a", "target": "c"},
            {"source": "b", "target": "c"},
            {"source": "d", "target": "e"},
            {"source": "d", "target": "f"},
            {"source": "e", "target": "f"},
            {"source": "c", "target": "d"},
        ]

        algorithm, clusters = http._compute_graph_clusters(nodes, edges)

        assert algorithm == "bridge_cut"
        assert len(clusters) == 2
        assert clusters[0]["members"] == ["a", "b", "c"]
        assert clusters[1]["members"] == ["d", "e", "f"]
        assert clusters[0]["density"] == 1.0
        assert clusters[1]["density"] == 1.0

    def test_compute_graph_clusters_label_propagation(self):
        nodes = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        edges = [
            {"source": "a", "target": "b"},
            {"source": "b", "target": "c"},
            {"source": "c", "target": "a"},
        ]

        algorithm, clusters = http._compute_graph_clusters(nodes, edges)

        assert algorithm == "label_propagation"
        assert len(clusters) == 1
        assert clusters[0]["members"] == ["a", "b", "c"]
        assert clusters[0]["density"] == 1.0


class TestGraphClustersEndpoint:
    def test_get_clusters_caches_results(self, monkeypatch):
        nodes = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        edges = [
            {"source": "a", "target": "b"},
            {"source": "b", "target": "c"},
            {"source": "c", "target": "a"},
        ]

        class FakeGraphStore:
            async def export_graph(self, project=None):
                return nodes, edges

        monkeypatch.setattr(http, "_get_graph_store", lambda: FakeGraphStore())
        http._clusters_cache.clear()

        result = asyncio.run(http.get_clusters("project-x"))

        assert result["project"] == "project-x"
        assert result["cached"] is False
        assert result["algorithm"] == "label_propagation"
        assert result["clusters"][0]["members"] == ["a", "b", "c"]

        cached_result = asyncio.run(http.get_clusters("project-x"))
        assert cached_result["cached"] is True
        assert cached_result["algorithm"] == result["algorithm"]
        assert cached_result["clusters"] == result["clusters"]

    def test_get_all_graph_returns_nodes_and_edges(self, monkeypatch):
        nodes = [{"id": "a"}, {"id": "b"}]
        edges = [{"source": "a", "target": "b"}]

        class FakeGraphStore:
            async def export_graph(self):
                return nodes, edges

        monkeypatch.setattr(http, "_get_graph_store", lambda: FakeGraphStore())

        result = asyncio.run(http.get_all_graph())

        assert result["nodes"] == nodes
        assert result["edges"] == edges

    def test_get_subgraph_returns_nodes_and_edges(self, monkeypatch):
        class FakeNode:
            def __init__(self, id, label, properties):
                self.id = id
                self.label = label
                self.properties = properties

        class FakeEdge:
            def __init__(self, source, target, edge_type, properties):
                self.source = source
                self.target = target
                self.edge_type = edge_type
                self.properties = properties

        nodes = [
            FakeNode("a", "Alpha", {"type": "source"}),
            FakeNode("b", "Beta", {"type": "target"}),
        ]
        edges = [FakeEdge("a", "b", "connects", {"weight": 1})]

        class FakeSubgraph:
            def __init__(self, nodes, edges):
                self.nodes = nodes
                self.edges = edges

        class FakeGraphStore:
            async def neighbors(self, root, depth, types, project=None):
                return FakeSubgraph(nodes, edges)

        monkeypatch.setattr(http, "_get_graph_store", lambda: FakeGraphStore())

        result = asyncio.run(http.get_subgraph("a", "project-x", 1, None))

        assert result["nodes"] == [
            {"id": "a", "label": "Alpha", "properties": {"type": "source"}},
            {"id": "b", "label": "Beta", "properties": {"type": "target"}},
        ]
        assert result["edges"] == [
            {
                "source": "a",
                "target": "b",
                "edge_type": "connects",
                "properties": {"weight": 1},
            }
        ]
