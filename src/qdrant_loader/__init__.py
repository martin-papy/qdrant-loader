"""
QDrant Loader - A tool for collecting and vectorizing technical content.
"""

from qdrant_loader.config import Settings
from qdrant_loader.core.embedding_service import EmbeddingService
from qdrant_loader.core.qdrant_manager import QdrantManager
from qdrant_loader.core import Document, ChunkingStrategy

__all__ = [
    'Settings',
    'EmbeddingService',
    'QdrantManager',
    'Document',
    'ChunkingStrategy'
]
