"""Contract tests for the FastMCP tool surface.

Replaces the legacy hand-written-schema tests. These assert the registered
tool catalogue and key input-schema properties without starting the server
lifespan (no Qdrant/OpenAI needed) — listing tools introspects registration.
"""

import asyncio

from qdrant_loader_mcp_server.fastmcp_app import mcp

EXPECTED_TOOLS = {
    "search",
    "hierarchy_search",
    "attachment_search",
    "analyze_relationships",
    "find_similar_documents",
    "detect_document_conflicts",
    "find_complementary_content",
    "cluster_documents",
    "expand_document",
    "expand_cluster",
    "expand_chunk_context",
}


def _list_tools():
    return {t.name: t for t in asyncio.run(mcp.list_tools())}


def test_all_tools_registered():
    tools = _list_tools()
    assert set(tools) == EXPECTED_TOOLS
    assert len(tools) == 11


def test_conflict_tool_keeps_legacy_name():
    """Backward-compat: advertised as detect_document_conflicts, not detect_conflicts."""
    tools = _list_tools()
    assert "detect_document_conflicts" in tools
    assert "detect_conflicts" not in tools


def test_search_tools_are_read_only():
    tools = _list_tools()
    for name in ("search", "hierarchy_search", "attachment_search"):
        assert tools[name].annotations.readOnlyHint is True


def test_search_input_schema_contract():
    schema = _list_tools()["search"].parameters
    props = schema["properties"]
    assert schema["required"] == ["query"]
    assert props["query"]["type"] == "string"
    assert props["limit"]["type"] == "integer"
    # ctx is injected by FastMCP and must not leak into the client-facing schema
    assert "ctx" not in props


def test_find_similar_requires_target_and_comparison():
    schema = _list_tools()["find_similar_documents"].parameters
    assert set(schema["required"]) == {"target_query", "comparison_query"}
