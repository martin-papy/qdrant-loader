import logging
from typing import List
from .config import Config
from .core.document import Document
from .core.chunking import ChunkingStrategy

class ChunkingService:
    """Service for chunking documents into smaller pieces."""

    def __init__(self, config: Config):
        """Initialize the chunking service.
        
        Args:
            config: Configuration object containing chunking parameters.
            
        Raises:
            ValueError: If chunk size or overlap parameters are invalid.
        """
        self.config = config
        self._validate_params()
        self.logger = logging.getLogger(__name__)
        self.chunking_strategy = ChunkingStrategy(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap
        )

    def _validate_params(self):
        """Validate chunking parameters.
        
        Raises:
            ValueError: If chunk size or overlap parameters are invalid.
        """
        if self.config.chunk_size <= 0:
            raise ValueError("Chunk size must be greater than 0")
        if self.config.chunk_overlap < 0:
            raise ValueError("Chunk overlap must be non-negative")
        if self.config.chunk_overlap >= self.config.chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")

    def chunk_document(self, document: Document) -> List[Document]:
        """Chunk a document into smaller pieces.
        
        Args:
            document: Document to chunk.
            
        Returns:
            List[Document]: List of chunked documents.
        """
        chunks = self.chunking_strategy._split_text(document.content)
        chunked_docs = []
        
        for i, chunk in enumerate(chunks):
            chunked_doc = Document(
                content=chunk,
                metadata={
                    **document.metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                },
                source=document.source,
                source_type=document.source_type,
                created_at=document.created_at,
                url=document.url,
                project=document.project,
                author=document.author,
                last_updated=document.last_updated
            )
            chunked_docs.append(chunked_doc)
            
        self.logger.debug({
            "event": "Document chunked",
            "total_chunks": len(chunked_docs),
            "average_chunk_size": sum(len(doc.content) for doc in chunked_docs) / len(chunked_docs) if chunked_docs else 0
        })
        
        return chunked_docs 