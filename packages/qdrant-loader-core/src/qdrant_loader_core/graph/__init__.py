import asyncio

from .falkor_store import FalkorGraphStore
from .store import GraphEdge, GraphNode, GraphStore, SubGraph
from .schema import init_schema

try:
    from qdrant_loader.config import get_settings
except ImportError:  # pragma: no cover
    get_settings = None

__all__ = [
    "FalkorGraphStore",
    "GraphNode",
    "GraphEdge",
    "GraphStore",
    "SubGraph",
]

# Singleton graph store instance
_graph_store: FalkorGraphStore | None = None
_graph_store_lock = asyncio.Lock()


async def get_graph_store() -> FalkorGraphStore:
    global _graph_store

    if _graph_store is None:
        async with _graph_store_lock:
            if _graph_store is None:
                # Config from settings
                if get_settings is not None:
                    try:
                        settings = get_settings()
                        graph_cfg = getattr(settings.global_config, "graph", None)

                        if graph_cfg is not None:
                            host = host or graph_cfg.connection.host
                            port = port or graph_cfg.connection.port
                            graph_name = graph_name or graph_cfg.graph_name

                    except AttributeError:
                        pass

                # Normalize values
                final_host = host or "localhost"
                final_port = int(port) if port else 6379
                final_graph = graph_name or "default_graph"

                _graph_store = FalkorGraphStore(
                    host=final_host,
                    port=final_port,
                    graph_name=final_graph,
                )

                # Init schema
                await init_schema(_graph_store)

    return _graph_store
