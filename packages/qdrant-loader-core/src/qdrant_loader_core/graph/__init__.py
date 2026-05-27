import os

from .falkor_store import FalkorGraphStore
from .store import GraphEdge, GraphNode, GraphStore, SubGraph

try:
    from qdrant_loader.config import get_settings
except ImportError:  # pragma: no cover
    get_settings = None

__all__ = ["FalkorGraphStore", "GraphNode", "GraphEdge", "GraphStore", "SubGraph"]


_graph_store = None


async def get_graph_store():
    global _graph_store

    if _graph_store is None:
        host = os.getenv("GRAPH_HOST")
        port = os.getenv("GRAPH_PORT")
        graph_name = os.getenv("GRAPH_NAME")

        if get_settings is not None:
            try:
                settings = get_settings()
                graph_cfg = getattr(settings.global_config, "graph", None)
                if graph_cfg is not None:
                    host = host or graph_cfg.connection.host
                    port = port or str(graph_cfg.connection.port)
                    graph_name = graph_name or graph_cfg.graph_name
            except Exception:
                # Settings may not be initialized in some runtime contexts.
                pass

        _graph_store = FalkorGraphStore(
            host=host or "localhost",
            port=int(port) if port else 6379,
            graph_name=graph_name or "default_graph",
        )

    return _graph_store
