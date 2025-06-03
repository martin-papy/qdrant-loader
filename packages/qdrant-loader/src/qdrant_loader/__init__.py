"""
QDrant Loader - A tool for collecting and vectorizing technical content.
"""

try:
    from importlib.metadata import version

    __version__ = version("qdrant-loader")
except ImportError:
    # Fallback for older Python versions or if package not installed
    __version__ = "unknown"


# Lazy imports to avoid slow package loading
def __getattr__(name):
    """Lazy import heavy modules only when accessed."""
    if name == "ChunkingConfig":
        from qdrant_loader.config import ChunkingConfig

        return ChunkingConfig
    elif name == "GlobalConfig":
        from qdrant_loader.config import GlobalConfig

        return GlobalConfig
    elif name == "SemanticAnalysisConfig":
        from qdrant_loader.config import SemanticAnalysisConfig

        return SemanticAnalysisConfig
    elif name == "Settings":
        from qdrant_loader.config import Settings

        return Settings
    elif name == "Document":
        from qdrant_loader.core import Document

        return Document
    elif name == "EmbeddingService":
        from qdrant_loader.core.embedding import EmbeddingService

        return EmbeddingService
    elif name == "QdrantManager":
        from qdrant_loader.core.qdrant_manager import QdrantManager

        return QdrantManager
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "__version__",
    "Document",
    "EmbeddingService",
    "QdrantManager",
    "Settings",
    "GlobalConfig",
    "SemanticAnalysisConfig",
    "ChunkingConfig",
]
