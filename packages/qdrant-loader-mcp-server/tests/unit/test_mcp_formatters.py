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
