from __future__ import annotations

import logging

from ..models import CoreEdgeType, CoreNodeLabel
from .versioning import get_version_query, set_version_query

logger = logging.getLogger(__name__)

LATEST_VERSION = 1


# ------------------------
# ENTRY POINT
# ------------------------
async def init_schema(graph_store):
    current_version = await _get_current_version(graph_store)

    logger.info(
        "Current graph schema version=%s",
        current_version,
    )

    for version in range(current_version + 1, LATEST_VERSION + 1):
        logger.info(
            "Applying graph schema migration v%s",
            version,
        )

        await _ensure_indexes(graph_store)
        await apply(graph_store)
        await _set_version(graph_store, version)

        logger.info(
            "Graph schema migration v%s applied successfully",
            version,
        )


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

    for query in queries:
        try:
            await graph_store.query_cypher(query, {})
        except Exception as exc:
            if "already exists" in str(exc).lower():
                continue
            raise


# ------------------------
# VERSION
# ------------------------
async def _get_current_version(graph_store) -> int:
    result = await graph_store.query_cypher(
        get_version_query(),
        {},
    )

    if not result:
        return 0

    return int(result[0][0])


async def _set_version(
    graph_store,
    version: int,
):
    await graph_store.query_cypher(
        set_version_query(),
        {"version": version},
    )


async def apply(graph_store):
    """
    Initialize canonical graph schema metadata.

    These nodes are informational metadata used to
    document supported node labels and edge types.
    """

    for label in CoreNodeLabel:
        await graph_store.query_cypher(
            """
            MERGE (:SchemaNodeType {name: $name})
            """,
            {"name": label.value},
        )

    for edge_type in CoreEdgeType:
        await graph_store.query_cypher(
            """
            MERGE (:SchemaEdgeType {name: $name})
            """,
            {"name": edge_type.value},
        )
