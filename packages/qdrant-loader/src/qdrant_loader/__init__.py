"""
QDrant Loader - A tool for collecting and vectorizing technical content.
"""

try:
    from importlib.metadata import version

    __version__ = version("qdrant-loader")
except ImportError:
    # Fallback for older Python versions or if package not installed
    __version__ = "unknown"

from qdrant_loader.config import (
    ChunkingConfig,
    GlobalConfig,
    SemanticAnalysisConfig,
    Settings,
)
from qdrant_loader.core import Document
from qdrant_loader.core.embedding import EmbeddingService
from qdrant_loader.core.qdrant_manager import QdrantManager

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
