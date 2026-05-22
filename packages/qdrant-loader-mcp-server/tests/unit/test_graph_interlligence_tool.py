import pytest
from qdrant_loader_mcp_server.mcp.intelligence_handler import IntelligenceHandler


class MockGraphStore:
    def __init__(self, result=None):
        self.result = result or []
        self.last_query = None
        self.last_params = None

    async def query_cypher(self, cypher, params):
        self.last_query = cypher
        self.last_params = params
        return self.result


class DummyFormatter:
    def format_graph(self, result):
        # giả lập format output
        return {
            "formatted": True,
            "data": result
        }

def create_handler(store, monkeypatch):

    handler = IntelligenceHandler(
        search_engine=None,
        protocol=None,
    )

    handler.formatters = DummyFormatter()
    
    async def mock_get_graph_store(self):
        return store

    monkeypatch.setattr(
        IntelligenceHandler,
        "_get_graph_store",
        mock_get_graph_store
    )

    return handler


@pytest.mark.asyncio
async def test_find_ticket_dependencies(monkeypatch):
    store = MockGraphStore([["ok"]])
    handler = create_handler(store, monkeypatch)

    result = await handler.find_ticket_dependencies("ABC-123", depth=2)

    # verify output
    assert result["formatted"] is True

    # verify query
    assert "LINKS_TO" in store.last_query
    assert "blocks" in store.last_query

    # verify param
    assert store.last_params["id"] == "jira:ABC-123"

@pytest.mark.asyncio
async def test_get_epic_tree(monkeypatch):
    store = MockGraphStore([["ok"]])
    handler = create_handler(store, monkeypatch)

    await handler.get_epic_tree("EPIC-1")

    # query contains PART_OF
    assert "PART_OF" in store.last_query

    # correct id format
    assert store.last_params["id"] == "jira:EPIC-1"

@pytest.mark.asyncio
async def test_find_related_documents_with_types(monkeypatch):
    store = MockGraphStore([])
    handler = create_handler(store, monkeypatch)

    await handler.find_related_documents(
        "jira:ABC-1",
        relationship_types=["LINKS_TO", "PART_OF"],
        depth=3,
    )

    # verify multiple rel types
    assert "LINKS_TO|PART_OF" in store.last_query

    # verify depth applied
    assert "1..3" in store.last_query

@pytest.mark.asyncio
async def test_find_related_documents_no_types(monkeypatch):
    store = MockGraphStore([])
    handler = create_handler(store, monkeypatch)

    await handler.find_related_documents(
        "jira:ABC-1",
        relationship_types=None,
        depth=2,
    )

    # no rel filter
    assert "-[*1..2]" in store.last_query or "*1..2" in store.last_query

@pytest.mark.asyncio
async def test_query_knowledge_graph_success(monkeypatch):
    store = MockGraphStore([["ok"]])
    handler = create_handler(store, monkeypatch)

    result = await handler.query_knowledge_graph(
        "MATCH (n) RETURN n",
        {"limit": 10}
    )

    assert result["formatted"] is True
    assert store.last_query.startswith("MATCH")

@pytest.mark.asyncio
async def test_query_knowledge_graph_blocked(monkeypatch):
    store = MockGraphStore([])
    handler = create_handler(store, monkeypatch)

    with pytest.raises(ValueError):
        await handler.query_knowledge_graph("DELETE FROM graph", {})

@pytest.mark.asyncio
async def test_run_graph_query(monkeypatch):
    store = MockGraphStore([["ok"]])
    handler = create_handler(store, monkeypatch)

    result = await handler._run_graph_query("MATCH", {"id": "A"})

    assert result == [["ok"]]
