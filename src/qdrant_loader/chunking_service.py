import logging
from typing import List
from .config import GlobalConfig
from .core.document import Document
from .core.chunking import ChunkingStrategy

class ChunkingService:
    """Service for chunking documents into smaller pieces."""

    def __init__(self, config: GlobalConfig):
        """Initialize the chunking service.
        
        Args:
            config: Global configuration
            
        Raises:
            ValueError: If chunk size or overlap parameters are invalid.
        """
        self.config = config
        self.validate_config()
        self.logger = logging.getLogger(__name__)
        self.chunking_strategy = ChunkingStrategy(
            chunk_size=config.chunking.chunk_size,
            chunk_overlap=config.chunking.chunk_overlap
        )

    def validate_config(self) -> None:
        """Validate chunking configuration."""
        if self.config.chunking.chunk_size <= 0:
            raise ValueError("Chunk size must be greater than 0")
        if self.config.chunking.chunk_overlap < 0:
            raise ValueError("Chunk overlap must be non-negative")
        if self.config.chunking.chunk_overlap >= self.config.chunking.chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")

    def chunk_document(self, document: Document) -> List[Document]:
        """Chunk a document into smaller pieces.
        
        Args:
            document: Document to chunk.
            
        Returns:
            List[Document]: List of chunked documents.
            
        Raises:
            Exception: If there is an error during chunking.
        """
        if not document.content:
            # Return a single empty chunk if document has no content
            empty_doc = document.copy()
            empty_doc.metadata.update({
                "chunk_index": 0,
                "total_chunks": 1
            })
            return [empty_doc]

        try:
            return self.chunking_strategy.chunk_document(document)
        except Exception as e:
            self.logger.error(f"Error chunking document: {str(e)}")
            raise e 