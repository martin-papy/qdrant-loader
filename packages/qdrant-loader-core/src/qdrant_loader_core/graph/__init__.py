from .falkor_store import FalkorGraphStore
from .store import GraphEdge, GraphNode, GraphStore, SubGraph

__all__ = ["FalkorGraphStore", "GraphNode", "GraphEdge", "GraphStore", "SubGraph"]


_graph_store = None


async def get_graph_store():
    global _graph_store

    if _graph_store is None:
        _graph_store = FalkorGraphStore(
            host="localhost",
            port=6379,
            graph_name="default",
        )

    return _graph_store
