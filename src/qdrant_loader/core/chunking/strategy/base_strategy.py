"""Base abstract class for chunking strategies."""

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

import structlog
import tiktoken

from qdrant_loader.core.document import Document
from qdrant_loader.core.text_processing.text_processor import TextProcessor
from qdrant_loader.utils.logging import LoggingConfig
from qdrant_loader.config import Settings

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

        # Initialize text processor
        self.text_processor = TextProcessor(settings)

    def _count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string."""
        if self.encoding is None:
            # Fallback to character count if no tokenizer is available
            return len(text)
        return len(self.encoding.encode(text))

    def _process_text(self, text: str) -> dict:
        """Process text using the text processor.
        
        Args:
            text: Text to process
            
        Returns:
            dict: Processed text features
        """
        return self.text_processor.process_text(text)

    def _create_chunk_document(
        self,
        original_doc: Document,
        chunk_content: str,
        chunk_index: int,
        total_chunks: int,
    ) -> Document:
        """Create a new document for a chunk with enhanced metadata.
        
        Args:
            original_doc: Original document
            chunk_content: Content of the chunk
            chunk_index: Index of the chunk
            total_chunks: Total number of chunks
            
        Returns:
            Document: New document instance for the chunk
        """
        # Process the chunk text to get additional features
        processed = self._process_text(chunk_content)
        
        # Create enhanced metadata
        metadata = original_doc.metadata.copy()
        metadata.update({
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "entities": processed["entities"],
            "pos_tags": processed["pos_tags"],
        })
        
        return Document(
            content=chunk_content,
            metadata=metadata,
            source=original_doc.source,
            source_type=original_doc.source_type,
            url=original_doc.url,
            title=original_doc.title,
            content_type=original_doc.content_type,
        )

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