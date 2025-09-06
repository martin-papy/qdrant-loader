import sys
from importlib import machinery, util
from pathlib import Path


def _load_module_from_path(module_name: str, path: Path, package: str):
    # Ensure parent package is imported so relative imports in the target file resolve
    __import__(package)
    loader = machinery.SourceFileLoader(module_name, str(path))
    spec = util.spec_from_loader(module_name, loader)
    module = util.module_from_spec(spec)
    module.__package__ = package
    sys.modules[module_name] = module
    loader.exec_module(module)
    return module


def test_mcp_formatters_reexport_file_executes():
    import qdrant_loader_mcp_server as pkg

    fmt_path = Path(pkg.__file__).resolve().parent / "mcp" / "formatters.py"
    mod = _load_module_from_path(
        "qdrant_loader_mcp_server.mcp._formatters_reexport",
        fmt_path,
        "qdrant_loader_mcp_server.mcp",
    )

    for symbol in (
        "MCPFormatters",
        "BasicResultFormatters",
        "IntelligenceResultFormatters",
        "LightweightResultFormatters",
        "StructuredResultFormatters",
        "FormatterUtils",
    ):
        assert hasattr(mod, symbol)


def test_search_engine_reexport_file_executes():
    import qdrant_loader_mcp_server as pkg

    engine_path = Path(pkg.__file__).resolve().parent / "search" / "engine.py"
    mod = _load_module_from_path(
        "qdrant_loader_mcp_server.search._engine_reexport",
        engine_path,
        "qdrant_loader_mcp_server.search",
    )

    for symbol in (
        "SearchEngine",
        "HybridSearchResult",
        "ClusteringStrategy",
        "SimilarityMetric",
        "ChainStrategy",
        "TopicSearchChain",
    ):
        assert hasattr(mod, symbol)
