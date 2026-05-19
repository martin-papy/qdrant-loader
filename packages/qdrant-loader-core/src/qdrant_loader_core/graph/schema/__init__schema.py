from . import seed_v1
from .versioning import get_version_query, set_version_query

LATEST_VERSION = 1


# ------------------------
# ENTRY POINT
# ------------------------
async def init_schema(graph_store):
    await _ensure_indexes(graph_store)

    current_version = await _get_current_version(graph_store)
    print("current_version: ", current_version)

    # Apply migrations incrementally
    if current_version < 1:
        await seed_v1.apply(graph_store)
        await _set_version(graph_store, 1)


# ------------------------
# INDEXES
# ------------------------
async def _ensure_indexes(graph_store):
    queries = [
        "CREATE INDEX ON :Document(id)",
        "CREATE INDEX ON :Person(id)",
        "CREATE INDEX ON :Container(id)",
        "CREATE INDEX ON :Label(id)",
        "CREATE INDEX ON :Concept(id)",
        "CREATE INDEX ON :Chunk(id)",
    ]

    for q in queries:
        try:
            await graph_store.query_cypher(q, {})
        except Exception:
            # already exists → idempotent
            pass


# ------------------------
# VERSION
# ------------------------
async def _get_current_version(graph_store) -> int:
    result = await graph_store.query_cypher(get_version_query(), {})

    if not result:
        return 0

    return result[0][0]


async def _set_version(graph_store, version: int):
    await graph_store.query_cypher(set_version_query(), {"version": version})
