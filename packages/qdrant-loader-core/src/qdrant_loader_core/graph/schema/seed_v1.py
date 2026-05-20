from ..models import GraphEdge, GraphNode


async def apply(graph_store):
    nodes = [
        GraphNode(
            id="doc_1",
            label="Document",
            properties={
                "title": "Graph Intro",
                "source_type": "system",
            },
        ),
        GraphNode(
            id="person_1",
            label="Person",
            properties={
                "display_name": "System",
            },
        ),
    ]

    edges = [
        GraphEdge(
            source="doc_1",
            target="person_1",
            edge_type="AUTHORED_BY",
            properties={"role": "author"},
        ),
    ]

    await graph_store.upsert_nodes_batch(nodes)
    await graph_store.upsert_edges_batch(edges)
