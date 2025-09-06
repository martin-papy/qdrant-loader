def test_monolithic_mcp_schemas_static_methods():
    # Import direct monolith for better coverage
    from qdrant_loader_mcp_server.mcp.schemas import MCPSchemas

    # Call each accessor to ensure execution paths and validate minimal shape
    schemas = [
        MCPSchemas.get_search_tool_schema(),
        MCPSchemas.get_hierarchy_search_tool_schema(),
        MCPSchemas.get_attachment_search_tool_schema(),
        MCPSchemas.get_analyze_relationships_tool_schema(),
        MCPSchemas.get_find_similar_tool_schema(),
        MCPSchemas.get_detect_conflicts_tool_schema(),
        MCPSchemas.get_find_complementary_tool_schema(),
        MCPSchemas.get_cluster_documents_tool_schema(),
        MCPSchemas.get_expand_document_tool_schema(),
        MCPSchemas.get_expand_cluster_tool_schema(),
    ]

    for s in schemas:
        assert isinstance(s, dict)
        assert "name" in s
        assert "inputSchema" in s
        assert "outputSchema" in s

    # Ensure get_all aggregates and names are unique
    all_schemas = MCPSchemas.get_all_tool_schemas()
    names = [s.get("name") for s in all_schemas]
    assert len(names) == len(set(names))
