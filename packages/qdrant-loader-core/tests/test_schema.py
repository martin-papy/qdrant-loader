import pytest
import pytest_asyncio
from qdrant_loader_core.graph import FalkorGraphStore
from qdrant_loader_core.graph.schema.__init__schema import init_schema


@pytest_asyncio.fixture
async def store():
    s = FalkorGraphStore(host="localhost", port=6379, graph_name="test_schema")

    await s.query_cypher("MATCH (n) DETACH DELETE n", {})
    return s


@pytest.mark.asyncio
async def test_init_schema_runs(store):
    await init_schema(store)

    result = await store.query_cypher("MATCH (n) RETURN count(n)", {})

    assert result[0][0] > 0


@pytest.mark.asyncio
async def test_init_schema_idempotent(store):
    await init_schema(store)

    result1 = await store.query_cypher("MATCH (n) RETURN count(n)", {})

    await init_schema(store)

    result2 = await store.query_cypher("MATCH (n) RETURN count(n)", {})

    assert result1 == result2


@pytest.mark.asyncio
async def test_schema_version(store):
    await init_schema(store)

    result = await store.query_cypher(
        "MATCH (s:_SchemaVersion {id:'schema'}) RETURN s.version", {}
    )

    assert result[0][0] == 1


@pytest.mark.asyncio
async def test_seed_data_present(store):
    await init_schema(store)

    result = await store.query_cypher("MATCH (d:Document {id:'doc_1'}) RETURN d", {})

    assert len(result) == 1


@pytest.mark.asyncio
async def test_retry_no_duplicate_nodes(store):
    await init_schema(store)

    await init_schema(store)
    await init_schema(store)

    result = await store.query_cypher("MATCH (n) RETURN count(n)", {})

    assert result[0][0] == 3
