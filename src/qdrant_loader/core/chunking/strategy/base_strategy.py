"""Base abstract class for chunking strategies."""

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

import structlog
import tiktoken

from qdrant_loader.core.document import Document
from qdrant_loader.utils.logging import LoggingConfig

if TYPE_CHECKING:
    from qdrant_loader.config import Settings

logger = LoggingConfig.get_logger(__name__)


class BaseChunkingStrategy(ABC):
    """Base abstract class for all chunking strategies.
    
    This class defines the interface that all chunking strategies must implement.
    Each strategy should provide its own implementation of how to split documents
    into chunks while preserving their semantic meaning and structure.
    """

    def __init__(
        self,
        settings: "Settings",
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        """Initialize the chunking strategy.
        
        Args:
            settings: Application settings containing configuration for the strategy
            chunk_size: Maximum number of tokens per chunk (optional, defaults to settings value)
            chunk_overlap: Number of tokens to overlap between chunks (optional, defaults to settings value)
        """
        self.settings = settings
        self.logger = LoggingConfig.get_logger(self.__class__.__name__)
        
        # Initialize token-based chunking parameters
        self.chunk_size = chunk_size or settings.global_config.chunking.chunk_size
        self.chunk_overlap = chunk_overlap or settings.global_config.chunking.chunk_overlap
        self.tokenizer = settings.global_config.embedding.tokenizer

        # Initialize tokenizer based on configuration
        if self.tokenizer == "none":
            self.encoding = None
        else:
            try:
                self.encoding = tiktoken.get_encoding(self.tokenizer)
            except Exception as e:
                logger.warning(
                    "Failed to initialize tokenizer, falling back to simple character counting",
                    error=str(e),
                    tokenizer=self.tokenizer,
                )
                self.encoding = None

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")

    def _count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string."""
        if self.encoding is None:
            # Fallback to character count if no tokenizer is available
            return len(text)
        return len(self.encoding.encode(text))

    @abstractmethod
    def chunk_document(self, document: Document) -> list[Document]:
        """Split a document into chunks while preserving metadata.
        
        This method should:
        1. Split the document content into appropriate chunks
        2. Preserve all metadata from the original document
        3. Add chunk-specific metadata (e.g., chunk index, total chunks)
        4. Return a list of new Document instances
        
        Args:
            document: The document to chunk
            
        Returns:
            List of chunked documents with preserved metadata
            
        Raises:
            NotImplementedError: If the strategy doesn't implement this method
        """
        raise NotImplementedError("Chunking strategy must implement chunk_document method")

    @abstractmethod
    def _split_text(self, text: str) -> list[str]:
        """Split text into chunks based on strategy-specific rules.
        
        This method should:
        1. Implement the specific chunking logic for the strategy
        2. Return a list of text chunks
        3. Preserve the semantic meaning of the content
        
        Args:
            text: The text to split into chunks
            
        Returns:
            List of text chunks
            
        Raises:
            NotImplementedError: If the strategy doesn't implement this method
        """
        raise NotImplementedError("Chunking strategy must implement _split_text method")

    def _create_chunk_document(
        self, 
        original_doc: Document, 
        chunk_content: str, 
        chunk_index: int, 
        total_chunks: int
    ) -> Document:
        """Create a new document for a chunk.
        
        This helper method creates a new Document instance for a chunk while
        preserving the original document's metadata and adding chunk-specific
        metadata.
        
        Args:
            original_doc: The original document being chunked
            chunk_content: The content for this chunk
            chunk_index: The index of this chunk (0-based)
            total_chunks: The total number of chunks
            
        Returns:
            A new Document instance for the chunk
        """
        # Create a copy of the original metadata
        metadata = original_doc.metadata.copy()
        
        # Add chunk-specific metadata
        metadata.update({
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "chunk_strategy": self.__class__.__name__
        })
        
        # Create and return the new document
        return Document(
            content=chunk_content,
            source=original_doc.source,
            source_type=original_doc.source_type,
            metadata=metadata,
            url=original_doc.url,
            title=original_doc.title,
            content_hash=original_doc.content_hash,
            created_at=original_doc.created_at,
            updated_at=original_doc.updated_at,
            id=original_doc.id,
            content_type=original_doc.content_type
        ) 