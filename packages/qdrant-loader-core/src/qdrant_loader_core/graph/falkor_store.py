from __future__ import annotations

import asyncio
from typing import Any

from falkordb import FalkorDB

from .models import (
    CoreEdgeType,
    CoreNodeLabel,
    GraphEdge,
    GraphNode,
    SubGraph,
)
from .store import GraphStore

VALID_NODE_LABELS = list(CoreNodeLabel)

VALID_EDGE_TYPES = list(CoreEdgeType)


class FalkorGraphStore(GraphStore):

    def __init__(self, host="localhost", port=6379, graph_name="default_graph"):
        self._db = FalkorDB(host=host, port=port)
        self._graph = self._db.select_graph(graph_name)

    # ------------------------
    # Validation
    # ------------------------
    def _validate_node(self, node: GraphNode):
        if node.label not in VALID_NODE_LABELS:
            raise ValueError(f"Invalid node label: {node.label}")

    def _validate_edge(self, edge: GraphEdge):
        if edge.edge_type not in VALID_EDGE_TYPES:
            raise ValueError(f"Invalid edge type: {edge.edge_type}")

    # ------------------------
    # Node
    # ------------------------
    async def upsert_node(self, node: GraphNode) -> None:
        self._validate_node(node)

        query = f"""
        MERGE (n:{node.label} {{id: $id}})
        SET n += $props
        """

        self._graph.query(
            query,
            {
                "id": node.id,
                "props": node.properties,
            },
        )

    async def upsert_nodes_batch(self, nodes: list[GraphNode]) -> None:
        if not nodes:
            return

        label = nodes[0].label
        if any(n.label != label for n in nodes):
            # fallback if mixed label
            for n in nodes:
                n.properties = self._clean_props(n.properties)
                await self.upsert_node(n)
            return

        query = f"""
        UNWIND $nodes AS node
        MERGE (n:{label} {{id: node.id}})
        SET n += node.props
        """

        payload = [{"id": n.id, "props": n.properties} for n in nodes]

        await self._graph.query(query, {"nodes": payload})

    # ------------------------
    # Edge
    # ------------------------
    async def upsert_edge(self, edge: GraphEdge) -> None:
        self._validate_edge(edge)

        query = f"""
        MATCH (a {{id: $source}})
        MATCH (b {{id: $target}})
        MERGE (a)-[r:{edge.edge_type}]->(b)
        SET r += $props
        """

        self._graph.query(
            query,
            {
                "source": edge.source,
                "target": edge.target,
                "props": edge.properties,
            },
        )

    async def upsert_edges_batch(self, edges: list[GraphEdge]) -> None:
        for e in edges:
            e.properties = self._clean_props(e.properties)
            await self.upsert_edge(e)

    # ------------------------
    # Query
    # ------------------------
    async def neighbors(
        self,
        node_id: str,
        depth: int,
        edge_types: list[str] | None = None,
    ) -> SubGraph:

        edge_filter = ""
        if edge_types:
            invalid = [e for e in edge_types if e not in VALID_EDGE_TYPES]
            if invalid:
                raise ValueError(f"Invalid edge types: {invalid}")

            edge_filter = ":" + "|".join(edge_types)

        query = f"""
        MATCH (n {{id: $id}})-[r{edge_filter}*1..{depth}]-(m)
        RETURN n, r, m
        """

        result = self._graph.query(query, {"id": node_id})
        nodes_map: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []

        for row in result.result_set:
            n, rels, m = row
            # ------- node n-----------
            n_id = n.properties.get("id")
            if n_id not in nodes_map:
                nodes_map[n_id] = GraphNode(
                    id=n_id,
                    label=n.labels[0],
                    properties=n.properties,
                )

            # ------- node m-----------
            m_id = m.properties.get("id")
            if m_id not in nodes_map:
                nodes_map[m_id] = GraphNode(
                    id=m_id,
                    label=m.labels[0],
                    properties=m.properties,
                )

            # ---------- relationships ----------
            for r in rels:
                edges.append(
                    GraphEdge(
                        source=r.src_node.properties.get("id"),
                        target=r.dest_node.properties.get("id"),
                        type=r.type,
                        properties=r.properties,
                    )
                )

        return SubGraph(
            nodes=list(nodes_map.values()),
            edges=edges,
        )

    async def query_cypher(
        self,
        cypher: str,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:

        result = await asyncio.to_thread(
            self._graph.query,
            cypher,
            params or {},
        )

        return result.result_set


    # -------------------------
    # Export graph for clustering
    # -------------------------
    async def export_graph(self) -> tuple[list[dict], list[dict]]:
        """
        Returns:
            nodes = [{"id": str}]
            edges = [{"source": str, "target": str}]
        """

        node_query = """
        MATCH (n:Document)
        RETURN n.id
        """

        edge_query = """
        MATCH (a:Document)-[:LINKS_TO]->(b:Document)
        RETURN a.id, b.id
        """

        node_result = self._graph.query(node_query)
        edge_result = self._graph.query(edge_query)

        nodes = [{"id": row[0]} for row in node_result.result_set]

        edges = [{"source": row[0], "target": row[1]} for row in edge_result.result_set]

        return nodes, edges

    # -------------------------
    # Batch update cluster_id
    # -------------------------
    async def update_clusters_batch(self, updates: list[dict]):
        async def _run(row):
            query = """
            MATCH (n:Document {id: $id})
            SET n.cluster_id = $cluster_id
            """
            await asyncio.to_thread(
                self._graph.query,
                query,
                {"id": row["id"], "cluster_id": row["cluster_id"]},
            )

        await asyncio.gather(*[_run(row) for row in updates])

    def _clean_props(self, props: dict) -> dict:
        clean = {}

        for k, v in props.items():
            if v is None:
                continue  # ❌ loại bỏ None

            if isinstance(v, (str, int, float, bool)):
                clean[k] = v
            elif isinstance(v, list):
                clean[k] = [
                    x for x in v if isinstance(x, (str, int, float, bool))
                ]
            else:
                clean[k] = str(v)  # fallback

        return clean
    