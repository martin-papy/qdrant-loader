from typing import TYPE_CHECKING

import structlog
import tiktoken

from qdrant_loader.core.document import Document

if TYPE_CHECKING:
    from qdrant_loader.config import Settings

logger = structlog.get_logger()


class ChunkingStrategy:
    """Handles text chunking with overlap and token counting."""

    def __init__(
        self,
        settings: "Settings",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        """
        Initialize the chunking strategy.

        Args:
            settings: The application settings
            chunk_size: Maximum number of tokens per chunk
            chunk_overlap: Number of tokens to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
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

        if chunk_overlap >= chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")

    def _count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string."""
        if self.encoding is None:
            # Fallback to character count if no tokenizer is available
            return len(text)
        return len(self.encoding.encode(text))

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
        """
        Split a document into chunks while preserving metadata.

        Args:
            document: The document to chunk

        Returns:
            List of chunked documents with preserved metadata
        """
        chunks = self._split_text(document.content)
        chunked_documents = []

        for i, chunk in enumerate(chunks):
            # Create a new document for each chunk
            metadata = document.metadata.copy()
            metadata.update({"chunk_index": i, "total_chunks": len(chunks)})

            chunk_doc = Document(
                content=chunk,
                source=document.source,
                source_type=document.source_type,
                metadata=metadata,
                url=document.url,
                title=document.title,
                content_hash=document.content_hash,
                created_at=document.created_at,
                updated_at=document.updated_at,
                id=document.id,
            )

            chunked_documents.append(chunk_doc)

        logger.debug(
            "Chunked document",
            source=document.source,
            total_chunks=len(chunks),
            avg_chunk_size=sum(len(c.content) for c in chunked_documents) / len(chunks),
        )

        return chunked_documents
