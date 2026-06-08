import asyncio
from typing import TYPE_CHECKING, Any

from .falkor_store import FalkorGraphStore
from .schema.init_schema import init_schema
from .store import GraphEdge, GraphNode, GraphStore, SubGraph

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


_graph_store: FalkorGraphStore | None = None
_graph_store_lock = asyncio.Lock()


async def get_graph_store(
    host: str | None = None,
    port: int | None = None,
    graph_name: str | None = None,
    max_connections: int | None = None,
) -> FalkorGraphStore:
    global _graph_store

    # Check runtime availability
    if not isinstance(FalkorGraphStore, type):
        raise ModuleNotFoundError(
            "FalkorGraphStore requires the 'graph' extra.\n"
            "Install it with:\n"
            "    pip install qdrant-loader-core[graph]"
        )

    if _graph_store is None:
        async with _graph_store_lock:
            if _graph_store is None:
                final_host = host or "localhost"
                final_port = port if port is not None else 6379
                final_graph = graph_name or "default_graph"
                final_max_conn = max_connections

                # merge config (only override if param not provided)
                if get_settings is not None:
                    try:
                        settings = get_settings()
                        graph_cfg = getattr(settings.global_config, "graph", None)

                        if graph_cfg is not None:
                            if host is None:
                                final_host = graph_cfg.connection.host
                            if port is None:
                                final_port = graph_cfg.connection.port
                            if graph_name is None:
                                final_graph = graph_cfg.graph_name
                            if max_connections is None:
                                final_max_conn = getattr(
                                    graph_cfg.pool,
                                    "max_connections",
                                    None,
                                )

                    except AttributeError:
                        pass

                # init store
                _graph_store = FalkorGraphStore(
                    host=final_host,
                    port=int(final_port),
                    graph_name=final_graph,
                    max_connections=final_max_conn if final_max_conn is not None else 10,
                )

                # init schema
                await init_schema(_graph_store)

    return _graph_store
