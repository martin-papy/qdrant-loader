from __future__ import annotations

import os
import time
from collections import Counter, defaultdict

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from qdrant_loader_mcp_server.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


# --- Simple CLI Graph HTTP server ---
app = FastAPI(title="QDrant Loader CLI Graph Server")
router = APIRouter(prefix="/api/graph")


def _get_graph_config():
    try:
        from qdrant_loader.config import get_settings

        settings = get_settings()
        return getattr(settings.global_config, "graph", None)
    except Exception:
        return None


def _create_graph_store():
    graph_cfg = _get_graph_config()
    host = os.getenv("GRAPH_HOST")
    port = os.getenv("GRAPH_PORT")
    graph_name = os.getenv("GRAPH_NAME")

    if graph_cfg is not None:
        host = host or graph_cfg.connection.host
        port = port or str(graph_cfg.connection.port)
        graph_name = graph_name or graph_cfg.graph_name

    try:
        # Lazy import so optional backend deps don't break module import
        from qdrant_loader_core.graph.falkor_store import FalkorGraphStore

        return FalkorGraphStore(
            host=host or "localhost",
            port=int(port) if port else 6379,
            graph_name=graph_name or "default_graph",
        )
    except Exception as exc:  # pragma: no cover - surface import/runtime errors
        raise RuntimeError(
            "Failed to create GraphStore. Ensure graph backend dependencies are installed: "
            f"{exc}"
        )


# Module-level graph store instance (created lazily so imports don't require
# optional backend dependencies during development/tests)
graph_store = None


def _get_graph_store():
    global graph_store
    if graph_store is None:
        graph_store = _create_graph_store()
    return graph_store


def _build_graph_adjacency(nodes: list[dict], edges: list[dict]) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = {}
    for node in nodes:
        node_id = node.get("id")
        if node_id is None:
            continue
        adjacency.setdefault(node_id, set())

    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if not source or not target:
            continue
        adjacency.setdefault(source, set()).add(target)
        adjacency.setdefault(target, set()).add(source)

    return adjacency


def _find_bridges(adjacency: dict[str, set[str]]) -> list[tuple[str, str]]:
    visited: set[str] = set()
    tin: dict[str, int] = {}
    low: dict[str, int] = {}
    bridges: list[tuple[str, str]] = []
    timer = 0

    def dfs(node: str, parent: str | None) -> None:
        nonlocal timer
        visited.add(node)
        tin[node] = timer
        low[node] = timer
        timer += 1

        for neighbor in adjacency.get(node, set()):
            if neighbor == parent:
                continue
            if neighbor in visited:
                low[node] = min(low[node], tin[neighbor])
            else:
                dfs(neighbor, node)
                low[node] = min(low[node], low[neighbor])
                if low[neighbor] > tin[node]:
                    bridges.append((node, neighbor))

    for node in sorted(adjacency.keys()):
        if node not in visited:
            dfs(node, None)

    return bridges


def _components_from_adjacency(adjacency: dict[str, set[str]]) -> list[list[str]]:
    visited: set[str] = set()
    components: list[list[str]] = []

    for node in sorted(adjacency.keys()):
        if node in visited:
            continue
        stack = [node]
        comp: list[str] = []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            comp.append(current)
            for neighbor in sorted(adjacency.get(current, set())):
                if neighbor not in visited:
                    stack.append(neighbor)
        components.append(sorted(comp))

    return components


def _label_propagation_clusters(
    adjacency: dict[str, set[str]], max_iter: int = 20
) -> dict[str, str]:
    labels: dict[str, str] = {node: node for node in sorted(adjacency.keys())}
    nodes = sorted(adjacency.keys())

    for _ in range(max_iter):
        updated = False
        for node in nodes:
            neighbor_labels = [
                labels[neighbor]
                for neighbor in adjacency.get(node, set())
                if neighbor in labels
            ]
            if not neighbor_labels:
                continue
            counts = Counter(neighbor_labels)
            best_count = max(counts.values())
            candidates = [
                label for label, count in counts.items() if count == best_count
            ]
            chosen_label = sorted(candidates)[0]
            if labels[node] != chosen_label:
                labels[node] = chosen_label
                updated = True
        if not updated:
            break

    return labels


def _cluster_labels(labels: dict[str, str], edges: list[dict]) -> list[dict]:
    groups: dict[str, list[str]] = defaultdict(list)
    for node, label in labels.items():
        groups[label].append(node)

    clusters: list[dict] = []
    for i, (_, members) in enumerate(
        sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])), start=1
    ):
        member_set = set(members)
        internal_edge_count = sum(
            1
            for edge in edges
            if edge.get("source") in member_set and edge.get("target") in member_set
        )
        max_possible = len(members) * (len(members) - 1) / 2
        density = round(internal_edge_count / max_possible, 3) if max_possible else 0.0
        clusters.append(
            {
                "id": f"cluster_{i}",
                "members": sorted(members),
                "size": len(members),
                "internal_edge_count": internal_edge_count,
                "density": density,
            }
        )

    return clusters


def _compute_graph_clusters(
    nodes: list[dict], edges: list[dict]
) -> tuple[str, list[dict]]:
    adjacency = _build_graph_adjacency(nodes, edges)
    if not adjacency:
        return "singletons", []

    bridges = _find_bridges(adjacency)
    if bridges:
        # Cut weak bridge edges to expose natural communities.
        adjacency_copy = {node: set(neighbors) for node, neighbors in adjacency.items()}
        for a, b in bridges:
            adjacency_copy[a].discard(b)
            adjacency_copy[b].discard(a)
        components = _components_from_adjacency(adjacency_copy)
        labels = {
            node: f"bridge_{i+1}" for i, comp in enumerate(components) for node in comp
        }
        algorithm = "bridge_cut"
    else:
        labels = _label_propagation_clusters(adjacency)
        algorithm = "label_propagation"

    clusters = _cluster_labels(labels, edges)
    return algorithm, clusters


# In-memory cache for cluster results: { project_id: {"ts": float, "clusters": ...} }
_clusters_cache: dict[str, dict] = {}
_CACHE_TTL = int(os.getenv("GRAPH_CLUSTER_CACHE_TTL", "300"))


@router.get("/subgraph")
async def get_subgraph(
    root: str = Query(..., description="Root node id"),
    project: str = Query(..., description="Project id"),
    depth: int = Query(1, ge=1, description="Hop depth"),
    edge_types: str | None = Query(
        None, description="Comma-separated edge types to filter"
    ),
):
    """Return a subgraph (nodes + edges) suitable for UI graph viz.

    Uses the GraphStore.neighbors() API as the authoritative source.
    """
    types = edge_types.split(",") if edge_types else None

    try:
        gs = _get_graph_store()
    except RuntimeError as exc:
        return JSONResponse(status_code=501, content={"detail": str(exc)})

    try:
        subgraph = await gs.neighbors(root, depth, types, project)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - bubble up unexpected errors
        raise HTTPException(status_code=500, detail=f"Error building subgraph: {exc}")

    nodes = [
        {"id": n.id, "label": str(n.label), "properties": n.properties or {}}
        for n in subgraph.nodes
    ]

    edges_out = []
    for e in subgraph.edges:
        # GraphEdge implementations may name the type field differently
        edge_type = getattr(e, "edge_type", None) or getattr(e, "type", None)
        edges_out.append(
            {
                "source": e.source,
                "target": e.target,
                "edge_type": str(edge_type) if edge_type is not None else None,
                "properties": e.properties or {},
            }
        )

    return {"nodes": nodes, "edges": edges_out}


@router.get("/clusters")
async def get_clusters(
    project: str = Query(..., description="Project id for clustering")
):
    """Return cached cluster results for a project.

    If no cached result exists, compute clusters from the graph export
    (graph stores that implement `export_graph()`), fall back with 501
    if the backend doesn't support export. Results are filtered by project.
    """
    now = time.time()
    cached = _clusters_cache.get(project)
    if cached and now - cached["ts"] < _CACHE_TTL:
        return {
            "project": project,
            "cached": True,
            "algorithm": cached.get("algorithm", "unknown"),
            "clusters": cached["clusters"],
            "generated_at": cached["ts"],
        }

    # Attempt to export a simple edge-list from the graph store
    try:
        gs = _get_graph_store()
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc))

    if not hasattr(gs, "export_graph"):
        raise HTTPException(
            status_code=501,
            detail="Graph store does not support export_graph() required for clustering",
        )

    try:
        nodes, edges = await gs.export_graph(project)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error exporting graph: {exc}")

    algorithm, clusters = _compute_graph_clusters(nodes, edges)
    _clusters_cache[project] = {"ts": now, "clusters": clusters, "algorithm": algorithm}

    return {
        "project": project,
        "cached": False,
        "algorithm": algorithm,
        "clusters": clusters,
        "generated_at": now,
    }


@router.get("/all")
async def get_all_graph():
    """Return all graph nodes and edges from the GraphStore."""
    try:
        gs = _get_graph_store()
        logger.info("Exporting full graph for all nodes/edges endpoint: %s", gs)
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc))

    if not hasattr(gs, "export_graph"):
        raise HTTPException(
            status_code=501,
            detail="Graph store does not support export_graph() required for full graph export",
        )

    try:
        nodes, edges = await gs.export_graph()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error exporting graph: {exc}")

    return {"nodes": nodes, "edges": edges}


app.include_router(router)
