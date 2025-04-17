"""
QDrant Loader - A tool for collecting and vectorizing technical content.
"""

from qdrant_loader.config import Settings
from qdrant_loader.core import ChunkingStrategy, Document
from qdrant_loader.core.embedding_service import EmbeddingService
from qdrant_loader.core.qdrant_manager import QdrantManager

__all__ = ["ChunkingStrategy", "Document", "EmbeddingService", "QdrantManager", "Settings"]
