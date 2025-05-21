"""Default token-based chunking strategy."""

from typing import TYPE_CHECKING

import structlog
import tiktoken

from qdrant_loader.core.document import Document
from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy

if TYPE_CHECKING:
    from qdrant_loader.config import Settings

logger = structlog.get_logger(__name__)


class DefaultChunkingStrategy(BaseChunkingStrategy):
    """Default token-based chunking strategy.
    
    This strategy splits text into chunks based on token count, with configurable
    chunk size and overlap. It uses tiktoken for tokenization when available,
    falling back to character-based splitting when no tokenizer is configured.
    """

    def _split_text(self, text: str) -> list[str]:
        """Split text into chunks with overlap."""
        # Handle empty text case
        if not text:
            return [""]

        if self.encoding is None:
            # If no tokenizer is available, split by characters
            if len(text) <= self.chunk_size:
                return [text]

            chunks = []
            start_idx = 0

            while start_idx < len(text):
                end_idx = min(start_idx + self.chunk_size, len(text))
                chunk = text[start_idx:end_idx]
                chunks.append(chunk)

                # Move start index forward, accounting for overlap
                new_start_idx = end_idx - self.chunk_overlap
                if new_start_idx <= start_idx:
                    new_start_idx = start_idx + 1
                start_idx = new_start_idx

                if start_idx >= len(text):
                    break

            return chunks

        # Use tokenizer if available
        tokens = self.encoding.encode(text)

        # If text is smaller than chunk size, return it as a single chunk
        if len(tokens) <= self.chunk_size:
            return [text]

        chunks = []
        start_idx = 0

        logger.debug(
            "Starting text chunking",
            total_tokens=len(tokens),
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        while start_idx < len(tokens):
            end_idx = min(start_idx + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start_idx:end_idx]
            chunk_text = self.encoding.decode(chunk_tokens)
            chunks.append(chunk_text)

            logger.debug(
                "Created chunk",
                chunk_index=len(chunks) - 1,
                start_idx=start_idx,
                end_idx=end_idx,
                chunk_length=len(chunk_tokens),
                chunk_text_length=len(chunk_text),
            )

            # Move start index forward, accounting for overlap
            # Ensure we make progress by moving at least one token forward
            new_start_idx = end_idx - self.chunk_overlap
            if new_start_idx <= start_idx:
                new_start_idx = start_idx + 1
            start_idx = new_start_idx

            logger.debug(
                "Updated start index",
                new_start_idx=start_idx,
                remaining_tokens=len(tokens) - start_idx,
            )

            # Safety check to prevent infinite loop
            if start_idx >= len(tokens):
                break

        logger.debug("Finished chunking", total_chunks=len(chunks), total_tokens=len(tokens))

        return chunks

    def chunk_document(self, document: Document) -> list[Document]:
        """Split a document into chunks while preserving metadata.

        Args:
            document: The document to chunk

        Returns:
            List of chunked documents with preserved metadata
        """
        # First, process the entire document to get document-level features
        doc_processed = self._process_text(document.content)
        
        # Add document-level features to metadata
        document.metadata.update({
            "document_entities": doc_processed["entities"],
            "document_pos_tags": doc_processed["pos_tags"],
        })
        
        # Split into chunks
        chunks = self._split_text(document.content)
        chunked_documents = []

        for i, chunk in enumerate(chunks):
            chunk_doc = self._create_chunk_document(
                original_doc=document,
                chunk_content=chunk,
                chunk_index=i,
                total_chunks=len(chunks)
            )
            
            # Generate unique chunk ID
            chunk_doc.id = Document.generate_chunk_id(document.id, i)
            
            # Add parent document reference
            chunk_doc.metadata["parent_document_id"] = document.id
            
            chunked_documents.append(chunk_doc)

        logger.debug(
            "Chunked document",
            source=document.source,
            total_chunks=len(chunks),
            avg_chunk_size=sum(len(c.content) for c in chunked_documents) / len(chunks),
        )

        return chunked_documents 