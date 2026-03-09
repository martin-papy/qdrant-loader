"""
Embedding components for document processing.
"""

from qdrant_loader.core.embedding.contextual_embedding import build_contextual_text
from qdrant_loader.core.embedding.embedding_service import EmbeddingService

__all__ = ["EmbeddingService", "build_contextual_text"]
