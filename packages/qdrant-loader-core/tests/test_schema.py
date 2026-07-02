from unittest.mock import AsyncMock, call

import pytest
from qdrant_loader_core.graph.models import CoreEdgeType, CoreNodeLabel
from qdrant_loader_core.graph.schema.init_schema import (
    LATEST_VERSION,
    _ensure_indexes,
    _get_current_version,
    _set_version,
    apply,
    init_schema,
)


@pytest.mark.asyncio
async def test_get_current_version_no_result():
    graph_store = AsyncMock()
    graph_store.query_cypher.return_value = []

    version = await _get_current_version(graph_store)

    assert version == 0


@pytest.mark.asyncio
async def test_get_current_version_with_result():
    graph_store = AsyncMock()
    graph_store.query_cypher.return_value = [[1]]

    version = await _get_current_version(graph_store)

    assert version == 1


@pytest.mark.asyncio
async def test_set_version():
    graph_store = AsyncMock()

    await _set_version(graph_store, 3)

    graph_store.query_cypher.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_indexes_success():
    graph_store = AsyncMock()

    await _ensure_indexes(graph_store)

    assert graph_store.query_cypher.await_count == 8


@pytest.mark.asyncio
async def test_ensure_indexes_ignore_existing():
    graph_store = AsyncMock()

    async def mock_query(query, params):
        raise Exception("Index already exists")

    graph_store.query_cypher.side_effect = mock_query

    # should NOT raise
    await _ensure_indexes(graph_store)


@pytest.mark.asyncio
async def test_apply_creates_schema_nodes_and_edges():
    graph_store = AsyncMock()

    await apply(graph_store)

    expected_calls = []

    # Node labels
    for label in CoreNodeLabel:
        expected_calls.append(
            call(
                """
            MERGE (:SchemaNodeType {name: $name})
            """,
                {"name": label.value},
            )
        )

    # Edge types
    for edge in CoreEdgeType:
        expected_calls.append(
            call(
                """
            MERGE (:SchemaEdgeType {name: $name})
            """,
                {"name": edge.value},
            )
        )

    graph_store.query_cypher.assert_has_awaits(expected_calls, any_order=True)


@pytest.mark.asyncio
async def test_init_schema_runs_migration():
    graph_store = AsyncMock()

    # version = 0
    graph_store.query_cypher.return_value = []

    await init_schema(graph_store)

    assert graph_store.query_cypher.await_count > 0


@pytest.mark.asyncio
async def test_init_schema_no_migration_needed():
    graph_store = AsyncMock()

    graph_store.query_cypher.return_value = [[LATEST_VERSION]]

    await init_schema(graph_store)

    # chỉ gọi get_version
    graph_store.query_cypher.assert_awaited_once()
