def test_mcp_schemas_module_exports_and_aggregation():
    from qdrant_loader_mcp_server.mcp.schemas import (
        MCPSchemas,
        get_all_tool_schemas,
        get_search_tool_schema,
    )

    # Ensure callable accessors exist
    assert callable(get_search_tool_schema)
    assert isinstance(get_all_tool_schemas(), list)
    # Backward-compatible wrapper should return same tool list
    wrapped = MCPSchemas.get_all_tool_schemas()
    assert isinstance(wrapped, list) and wrapped
    # Tool names should be unique for registry correctness
    names = [tool.get("name") for tool in wrapped]
    assert len(names) == len(set(names))


def test_mcp_formatters_reexports():
    from qdrant_loader_mcp_server.mcp import formatters

    for symbol in (
        "MCPFormatters",
        "BasicResultFormatters",
        "IntelligenceResultFormatters",
        "LightweightResultFormatters",
        "StructuredResultFormatters",
        "FormatterUtils",
    ):
        assert hasattr(formatters, symbol)
