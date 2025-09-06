def test_search_engine_package_reexports():
    import qdrant_loader_mcp_server.search.engine as engine_pkg

    # Package __init__ should re-export the core engine and clients
    for symbol in (
        "SearchEngine",
        "AsyncQdrantClient",
        "AsyncOpenAI",
        "HybridSearchEngine",
    ):
        assert hasattr(engine_pkg, symbol)
