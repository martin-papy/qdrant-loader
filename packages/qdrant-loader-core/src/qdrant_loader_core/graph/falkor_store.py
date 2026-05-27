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

        project = node.project or node.properties.get("project")
        if project is not None:
            query = f"""
            MERGE (n:{node.label} {{id: $id, project: $project}})
            SET n += $props
            """
            params = {"id": node.id, "project": project, "props": node.properties}
        else:
            query = f"""
            MERGE (n:{node.label} {{id: $id}})
            SET n += $props
            """
            params = {"id": node.id, "props": node.properties}

        self._graph.query(query, params)

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

        payload = [
            {
                "id": n.id,
                "project": n.project or n.properties.get("project"),
                "props": n.properties,
            }
            for n in nodes
        ]

        if all(node_payload["project"] is not None for node_payload in payload):
            query = f"""
            UNWIND $nodes AS node
            MERGE (n:{label} {{id: node.id, project: node.project}})
            SET n += node.props
            """
        else:
            query = f"""
            UNWIND $nodes AS node
            MERGE (n:{label} {{id: node.id}})
            SET n += node.props
            """

        await self._graph.query(query, {"nodes": payload})

    # ------------------------
    # Edge
    # ------------------------
    async def upsert_edge(self, edge: GraphEdge) -> None:
        self._validate_edge(edge)

        query = """
        MATCH (a {id: $source, project: $project}),
            (b {id: $target, project: $project})
        MERGE (a)-[r:BELONGS_TO]->(b)
        SET r += $props
        """


        project = edge.project or edge.properties.get("project")
        params = {
            "source": edge.source,
            "target": edge.target,
            "props": edge.properties,
        }
        if project is not None:
            params["project"] = project
            query = f"""
            MATCH (a {{id: $source, project: $project}}),
                  (b {{id: $target, project: $project}})
            MERGE (a)-[r:{edge.edge_type}]->(b)
            SET r += $props
            """
        else:
            query = f"""
            MATCH (a {{id: $source}}),
                  (b {{id: $target}})
            MERGE (a)-[r:{edge.edge_type}]->(b)
            SET r += $props
            """

        self._graph.query(query, params)

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
        project: str | None = None,
    ) -> SubGraph:

        edge_filter = ""
        if edge_types:
            invalid = [e for e in edge_types if e not in VALID_EDGE_TYPES]
            if invalid:
                raise ValueError(f"Invalid edge types: {invalid}")

            edge_filter = ":" + "|".join(edge_types)

        params = {"id": node_id}
        if project:
            params["project"] = project
            query = f"""
            MATCH (n {{id: $id, project: $project}})-[r{edge_filter}*1..{depth}]-(m {{project: $project}})
            RETURN n, r, m
            """
        else:
            query = f"""
            MATCH (n {{id: $id}})-[r{edge_filter}*1..{depth}]-(m)
            RETURN n, r, m
            """

        result = self._graph.query(query, params)
        nodes_map: dict[str, GraphNode] = {}
        internal_node_id_map: dict[int, str] = {}
        edges: list[GraphEdge] = []

        def _extract_node(node_value):
            if hasattr(node_value, "properties"):
                node_id = node_value.properties.get("id")
                label = node_value.labels[0] if getattr(node_value, "labels", None) else "Unknown"
                properties = node_value.properties or {}
            elif isinstance(node_value, dict):
                node_id = node_value.get("id")
                label = node_value.get("label", "Unknown")
                properties = node_value
            else:
                node_id = str(node_value)
                label = "Unknown"
                properties = {}
            return node_id, label, properties

        def _normalize_relationships(rels_value):
            if rels_value is None:
                return []
            if isinstance(rels_value, list):
                return rels_value
            return [rels_value]

        def _resolve_internal_node_id(node_value):
            if isinstance(node_value, int):
                return internal_node_id_map.get(node_value, str(node_value))
            return node_value

        def _extract_edge(rel):
            if hasattr(rel, "src_node") and hasattr(rel, "dest_node"):
                source = _resolve_internal_node_id(rel.src_node)
                target = _resolve_internal_node_id(rel.dest_node)
                edge_type = getattr(rel, "relation", getattr(rel, "edge_type", None))
                properties = rel.properties or {}
                return GraphEdge(source=source, target=target, edge_type=edge_type, properties=properties)
            if isinstance(rel, dict):
                return GraphEdge(
                    source=rel.get("source"),
                    target=rel.get("target"),
                    edge_type=rel.get("edge_type"),
                    properties=rel.get("properties", {}),
                )
            raise ValueError("Unsupported relationship result type")

        for row in result.result_set:
            if len(row) != 3:
                continue

            n, rels, m = row
            n_id, n_label, n_props = _extract_node(n)
            if hasattr(n, "id") and isinstance(n.id, int):
                internal_node_id_map[n.id] = n_id
            if n_id not in nodes_map:
                nodes_map[n_id] = GraphNode(id=n_id, label=n_label, properties=n_props)

            m_id, m_label, m_props = _extract_node(m)
            if hasattr(m, "id") and isinstance(m.id, int):
                internal_node_id_map[m.id] = m_id
            if m_id not in nodes_map:
                nodes_map[m_id] = GraphNode(id=m_id, label=m_label, properties=m_props)

            for rel in _normalize_relationships(rels):
                try:
                    edge = _extract_edge(rel)
                except ValueError:
                    continue
                edges.append(edge)

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
    async def export_graph(self, project: str | None = None) -> tuple[list[dict], list[dict]]:
        """
        Returns:
            nodes = [{"id": str}]
            edges = [{"source": str, "target": str}]
        """

        if project:
            node_query = """
            MATCH (n {project: $project})
            RETURN DISTINCT n.id
            """

            edge_query = """
            MATCH (a {project: $project})-[r]->(b {project: $project})
            RETURN DISTINCT a.id, b.id
            """

            node_result = self._graph.query(node_query, {"project": project})
            edge_result = self._graph.query(edge_query, {"project": project})
        else:
            node_query = """
            MATCH (n)
            RETURN DISTINCT n.id
            """

            edge_query = """
            MATCH (a)-[r]->(b)
            RETURN DISTINCT a.id, b.id
            """

            node_result = self._graph.query(node_query)
            edge_result = self._graph.query(edge_query)

        nodes = [{"id": row[0]} for row in node_result.result_set]

        edges = [{"source": row[0], "target": row[1]} for row in edge_result.result_set]

        return nodes, edges

    # -------------------------
    # Batch update cluster_id
    # -------------------------
    async def update_clusters_batch(self, updates: list[dict], project: str | None = None):
        async def _run(row):
            if project:
                query = """
                MATCH (n:Document {id: $id, project: $project})
                SET n.cluster_id = $cluster_id
                """
                await asyncio.to_thread(
                    self._graph.query,
                    query,
                    {"id": row["id"], "cluster_id": row["cluster_id"], "project": project},
                )
            else:
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
    