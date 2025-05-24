"""Default token-based chunking strategy."""

from typing import TYPE_CHECKING

import structlog
import tiktoken

from qdrant_loader.core.document import Document
from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy

if TYPE_CHECKING:
    from qdrant_loader.config import Settings

logger = structlog.get_logger(__name__)

# Performance constants to prevent timeouts
MAX_DOCUMENT_SIZE_FOR_NLP = 50_000  # 50KB limit for NLP processing
MAX_CHUNK_SIZE_FOR_NLP = 10_000  # 10KB limit for chunk NLP processing
MAX_CHUNKS_TO_PROCESS = 100  # Limit total chunks to prevent timeouts


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

                # Safety check to prevent too many chunks
                if len(chunks) >= MAX_CHUNKS_TO_PROCESS:
                    logger.warning(
                        f"Reached maximum chunk limit ({MAX_CHUNKS_TO_PROCESS}), truncating"
                    )
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

            # Safety check to prevent too many chunks
            if len(chunks) >= MAX_CHUNKS_TO_PROCESS:
                logger.warning(f"Reached maximum chunk limit ({MAX_CHUNKS_TO_PROCESS}), truncating")
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
        logger.info(
            "Starting default chunking",
            extra={
                "source": document.source,
                "source_type": document.source_type,
                "content_length": len(document.content),
                "file_name": document.metadata.get("file_name", "unknown"),
            },
        )

        # Performance check: skip expensive NLP processing for large documents
        skip_nlp = len(document.content) > MAX_DOCUMENT_SIZE_FOR_NLP

        if skip_nlp:
            logger.info(
                f"Document too large for NLP processing ({len(document.content)} bytes), skipping"
            )
            # Add minimal document-level metadata without NLP processing
            document.metadata.update(
                {
                    "document_entities": [],
                    "document_pos_tags": [],
                    "nlp_skipped": True,
                    "skip_reason": "document_too_large",
                }
            )
        else:
            try:
                # Process the entire document to get document-level features
                doc_processed = self._process_text(document.content)

                # Add document-level features to metadata
                document.metadata.update(
                    {
                        "document_entities": doc_processed["entities"],
                        "document_pos_tags": doc_processed["pos_tags"],
                        "nlp_skipped": False,
                    }
                )
            except Exception as e:
                logger.warning(f"NLP processing failed for document: {e}")
                document.metadata.update(
                    {
                        "document_entities": [],
                        "document_pos_tags": [],
                        "nlp_skipped": True,
                        "skip_reason": "nlp_error",
                    }
                )

        # Split into chunks
        chunks = self._split_text(document.content)
        chunked_documents = []

        # Limit the number of chunks to process
        chunks_to_process = chunks[:MAX_CHUNKS_TO_PROCESS]
        if len(chunks) > MAX_CHUNKS_TO_PROCESS:
            logger.warning(f"Truncating chunks from {len(chunks)} to {MAX_CHUNKS_TO_PROCESS}")

        for i, chunk in enumerate(chunks_to_process):
            # Create chunk document with optimized metadata processing
            chunk_doc = self._create_optimized_chunk_document(
                original_doc=document,
                chunk_content=chunk,
                chunk_index=i,
                total_chunks=len(chunks_to_process),
                skip_nlp=skip_nlp or len(chunk) > MAX_CHUNK_SIZE_FOR_NLP,
            )

            # Generate unique chunk ID
            chunk_doc.id = Document.generate_chunk_id(document.id, i)

            # Add parent document reference
            chunk_doc.metadata["parent_document_id"] = document.id

            chunked_documents.append(chunk_doc)

        logger.info(
            f"Successfully chunked document into {len(chunked_documents)} chunks",
            extra={
                "avg_chunk_size": (
                    sum(len(doc.content) for doc in chunked_documents) / len(chunked_documents)
                    if chunked_documents
                    else 0
                ),
                "nlp_skipped": skip_nlp,
                "total_original_chunks": len(chunks),
                "processed_chunks": len(chunks_to_process),
            },
        )

        return chunked_documents

    def _create_optimized_chunk_document(
        self,
        original_doc: Document,
        chunk_content: str,
        chunk_index: int,
        total_chunks: int,
        skip_nlp: bool = False,
    ) -> Document:
        """Create a new document for a chunk with optimized metadata processing.

        Args:
            original_doc: Original document
            chunk_content: Content of the chunk
            chunk_index: Index of the chunk
            total_chunks: Total number of chunks
            skip_nlp: Whether to skip expensive NLP processing

        Returns:
            Document: New document instance for the chunk
        """
        # Create enhanced metadata
        metadata = original_doc.metadata.copy()
        metadata.update(
            {
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
            }
        )

        if skip_nlp:
            # Skip expensive NLP processing for large chunks
            metadata.update(
                {
                    "entities": [],
                    "pos_tags": [],
                    "nlp_skipped": True,
                    "skip_reason": (
                        "chunk_too_large"
                        if len(chunk_content) > MAX_CHUNK_SIZE_FOR_NLP
                        else "document_too_large"
                    ),
                }
            )
        else:
            try:
                # Process the chunk text to get additional features
                processed = self._process_text(chunk_content)
                metadata.update(
                    {
                        "entities": processed["entities"],
                        "pos_tags": processed["pos_tags"],
                        "nlp_skipped": False,
                    }
                )
            except Exception as e:
                logger.warning(f"NLP processing failed for chunk {chunk_index}: {e}")
                metadata.update(
                    {
                        "entities": [],
                        "pos_tags": [],
                        "nlp_skipped": True,
                        "skip_reason": "nlp_error",
                    }
                )

        return Document(
            content=chunk_content,
            metadata=metadata,
            source=original_doc.source,
            source_type=original_doc.source_type,
            url=original_doc.url,
            title=original_doc.title,
            content_type=original_doc.content_type,
        )
