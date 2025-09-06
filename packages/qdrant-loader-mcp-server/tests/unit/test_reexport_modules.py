import runpy
from importlib import import_module
from pathlib import Path


def test_engine_reexport_importable():
    mod = import_module("qdrant_loader_mcp_server.search.engine")

    # Package exports per search/engine/__init__.py
    for symbol in (
        "SearchEngine",
        "AsyncQdrantClient",
        "AsyncOpenAI",
        "HybridSearchEngine",
    ):
        assert hasattr(mod, symbol)


def test_mcp_formatters_reexport_importable():
    import qdrant_loader_mcp_server.mcp.formatters as fm

    for symbol in (
        "MCPFormatters",
        "BasicResultFormatters",
        "IntelligenceResultFormatters",
        "LightweightResultFormatters",
        "StructuredResultFormatters",
        "FormatterUtils",
    ):
        assert hasattr(fm, symbol)


def test_monolithic_schemas_module_executes():
    import qdrant_loader_mcp_server as pkg

    schemas_py = Path(pkg.__file__).resolve().parent / "mcp" / "schemas.py"
    globs = runpy.run_path(str(schemas_py))
    assert "MCPSchemas" in globs
