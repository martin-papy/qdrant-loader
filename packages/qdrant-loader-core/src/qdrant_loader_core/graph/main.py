import asyncio
import os

from qdrant_loader_core.graph import FalkorGraphStore
from qdrant_loader_core.graph.schema.__init__schema import init_schema


async def main():

    store = FalkorGraphStore(host="localhost", port=6379, graph_name="knowledge_graph")

    if os.getenv("QDANT_LOADER_RESET_GRAPH") == "1":
        print("Clearing DB...")
        await store.query_cypher("MATCH (n) DETACH DELETE n", {})
    else:
        print("Skipping destructive reset; set QDANT_LOADER_RESET_GRAPH=1 to enable.")
    print("store._graph: ", store._graph._name)

    try:
        result = await store.query_cypher("RETURN 1 AS test", {})
        print("OK:", result)
    except Exception as e:
        print("ERROR:", e)

    print("Running schema init...")
    await init_schema(store)

    print("Running schema init AGAIN (idempotency test)...")
    await init_schema(store)

    print("Query version...")
    result = await store.query_cypher("MATCH (s:_SchemaVersion) RETURN s.version", {})
    print(result)

    print("Query nodes count...")
    result = await store.query_cypher("MATCH (n) RETURN count(n) as count", {})
    print(result)

    print("Query edges count...")
    result = await store.query_cypher("MATCH ()-[r]->() RETURN count(r) as count", {})
    print(result)
    result = await store.query_cypher("MATCH (n) RETURN labels(n), n.id", {})
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
