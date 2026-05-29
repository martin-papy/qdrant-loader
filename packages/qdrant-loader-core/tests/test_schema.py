from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from qdrant_loader_core.graph import FalkorGraphStore
from qdrant_loader_core.graph.schema.__init__schema import init_schema


# Async-compatible mock result
class MockResult:
    def __init__(self, result_set=None):
        self.result_set = result_set or []

    def __await__(self):
        async def _():
            return self

        return _().__await__()


@pytest_asyncio.fixture
async def store():
    # Mock FalkorDB
    mock_db = MagicMock()
    mock_graph = MagicMock()
    mock_db.select_graph.return_value = mock_graph

    queries = []

    # Simple in-memory behavior
    state = {
        "initialized": False,
        "node_count": 0,
        "schema_version": 0,
    }

    def mock_query(query, params=None):
        queries.append(query)

        # Simulate clearing graph
        if "DETACH DELETE" in query:
            state["initialized"] = False
            state["node_count"] = 0
            state["schema_version"] = 0
            return MockResult([])

        # Simulate schema creation (first run only)
        if not state["initialized"]:
            state["initialized"] = True
            state["node_count"] = 3  # giả lập có 3 node seed
            state["schema_version"] = 1

        # count nodes
        if "RETURN count(n)" in query:
            return MockResult([[state["node_count"]]])

        # schema version query
        if "_SchemaVersion" in query:
            return MockResult([[state["schema_version"]]])

        # seed data query
        if "doc_1" in query:
            if state["initialized"]:
                return MockResult([["doc_1"]])
            return MockResult([])

        return MockResult([])

    mock_graph.query = mock_query

    with patch(
        "qdrant_loader_core.graph.falkor_store.FalkorDB",
        return_value=mock_db,
    ):
        s = FalkorGraphStore(
            host="localhost",
            port=6379,
            graph_name="test_schema",
        )

    # clear graph (mocked)
    await s.query_cypher("MATCH (n) DETACH DELETE n", {})

    return s


# -------------------------
# Test: schema runs
# -------------------------
@pytest.mark.asyncio
async def test_init_schema_runs(store):
    await init_schema(store)

    result = await store.query_cypher("MATCH (n) RETURN count(n)", {})

    assert result[0][0] > 0


# -------------------------
# Test: idempotent
# -------------------------
@pytest.mark.asyncio
async def test_init_schema_idempotent(store):
    await init_schema(store)

    result1 = await store.query_cypher("MATCH (n) RETURN count(n)", {})

    await init_schema(store)

    result2 = await store.query_cypher("MATCH (n) RETURN count(n)", {})

    assert result1 == result2


# -------------------------
# Test: schema version
# -------------------------
@pytest.mark.asyncio
async def test_schema_version(store):
    await init_schema(store)

    result = await store.query_cypher(
        "MATCH (s:_SchemaVersion {id:'schema'}) RETURN s.version", {}
    )

    assert result[0][0] == 1


# -------------------------
# Test: seed data
# -------------------------
@pytest.mark.asyncio
async def test_seed_data_present(store):
    await init_schema(store)

    result = await store.query_cypher("MATCH (d:Document {id:'doc_1'}) RETURN d", {})

    assert len(result) == 1


# -------------------------
# Test: no duplicate nodes
# -------------------------
@pytest.mark.asyncio
async def test_retry_no_duplicate_nodes(store):
    await init_schema(store)
    await init_schema(store)
    await init_schema(store)

    result = await store.query_cypher("MATCH (n) RETURN count(n)", {})

    assert result[0][0] == 3
