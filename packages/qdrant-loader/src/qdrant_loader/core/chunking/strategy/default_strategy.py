"""Default chunking strategy for text documents."""

import re
from typing import Any

import structlog

from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy
from qdrant_loader.core.chunking.progress_tracker import ChunkingProgressTracker
from qdrant_loader.core.document import Document
from qdrant_loader.config import Settings

logger = structlog.get_logger(__name__)

# Maximum number of chunks to process to prevent performance issues
MAX_CHUNKS_TO_PROCESS = 1000


class DefaultChunkingStrategy(BaseChunkingStrategy):
    """Default text chunking strategy using simple text splitting."""

    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.progress_tracker = ChunkingProgressTracker(logger)

        # Log configuration for debugging
        logger.info(
            "DefaultChunkingStrategy initialized",
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            tokenizer=self.tokenizer,
            has_encoding=self.encoding is not None,
        )

        # Warn about suspiciously small chunk sizes
        if self.chunk_size < 100:
            logger.warning(
                f"Very small chunk_size detected: {self.chunk_size}. "
                f"This may cause performance issues and excessive chunking. "
                f"Consider using a larger value (e.g., 1000-1500 characters)."
            )

    def _split_text(self, text: str) -> list[str]:
        """Split text into chunks using sentence boundaries and size limits.

        Args:
            text: The text to split

        Returns:
            List of text chunks
        """
        if not text.strip():
            return [""]

        # Use tokenizer-based chunking if available
        if self.encoding is not None:
            return self._split_text_with_tokenizer(text)
        else:
            return self._split_text_without_tokenizer(text)

    def _split_text_with_tokenizer(self, text: str) -> list[str]:
        """Split text using tokenizer for accurate token counting.

        Args:
            text: The text to split

        Returns:
            List of text chunks
        """
        if self.encoding is None:
            # Fallback to character-based chunking
            return self._split_text_without_tokenizer(text)

        tokens = self.encoding.encode(text)

        if len(tokens) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(tokens) and len(chunks) < MAX_CHUNKS_TO_PROCESS:
            # Calculate end position
            end = min(start + self.chunk_size, len(tokens))

            # Extract chunk tokens
            chunk_tokens = tokens[start:end]

            # Decode tokens back to text
            chunk_text = self.encoding.decode(chunk_tokens)
            chunks.append(chunk_text)

            # Move start position forward, accounting for overlap
            # Ensure we always make progress by advancing at least 1 token
            advance = max(1, self.chunk_size - self.chunk_overlap)
            start += advance

            # If we're near the end and the remaining tokens are small, include them in the last chunk
            if start < len(tokens) and (len(tokens) - start) <= self.chunk_overlap:
                # Create final chunk with remaining tokens
                final_chunk_tokens = tokens[start:]
                if final_chunk_tokens:  # Only add if there are tokens
                    final_chunk_text = self.encoding.decode(final_chunk_tokens)
                    chunks.append(final_chunk_text)
                break

        # Log warning if we hit the chunk limit
        if len(chunks) >= MAX_CHUNKS_TO_PROCESS and start < len(tokens):
            logger.warning(
                f"Reached maximum chunk limit of {MAX_CHUNKS_TO_PROCESS}. "
                f"Document may be truncated."
            )

        return chunks

    def _split_text_without_tokenizer(self, text: str) -> list[str]:
        """Split text without tokenizer using character-based chunking.

        Args:
            text: The text to split

        Returns:
            List of text chunks
        """
        # Safety check: if chunk_size is invalid, use a reasonable default
        if self.chunk_size <= 0:
            logger.warning(f"Invalid chunk_size {self.chunk_size}, using default 1000")
            effective_chunk_size = 1000
        else:
            effective_chunk_size = self.chunk_size

        if len(text) <= effective_chunk_size:
            return [text]

        # First, try to split by paragraphs (double newlines)
        paragraphs = re.split(r"\n\s*\n", text.strip())
        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # If adding this paragraph would exceed chunk size, finalize current chunk
            if (
                current_chunk
                and len(current_chunk) + len(paragraph) + 2 > effective_chunk_size
            ):
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph

        # Add the last chunk if it exists
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # If we still have chunks that are too large, split them further
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= effective_chunk_size:
                final_chunks.append(chunk)
            else:
                # Split large chunks by sentences
                sentences = re.split(r"(?<=[.!?])\s+", chunk)
                current_subchunk = ""

                for sentence in sentences:
                    if (
                        current_subchunk
                        and len(current_subchunk) + len(sentence) + 1
                        > effective_chunk_size
                    ):
                        if current_subchunk.strip():
                            final_chunks.append(current_subchunk.strip())
                        current_subchunk = sentence
                    else:
                        if current_subchunk:
                            current_subchunk += " " + sentence
                        else:
                            current_subchunk = sentence

                if current_subchunk.strip():
                    final_chunks.append(current_subchunk.strip())

        # Final fallback: if chunks are still too large, split by character count
        result_chunks = []
        for chunk in final_chunks:
            if len(chunk) <= effective_chunk_size:
                result_chunks.append(chunk)
            else:
                # Split by character count with word boundaries
                words = chunk.split()
                current_word_chunk = ""

                for word in words:
                    if (
                        current_word_chunk
                        and len(current_word_chunk) + len(word) + 1
                        > effective_chunk_size
                    ):
                        if current_word_chunk.strip():
                            result_chunks.append(current_word_chunk.strip())
                        current_word_chunk = word
                    else:
                        if current_word_chunk:
                            current_word_chunk += " " + word
                        else:
                            current_word_chunk = word

                if current_word_chunk.strip():
                    result_chunks.append(current_word_chunk.strip())

        # Ultimate fallback: if chunks are still too large (no word boundaries), split by character count
        final_result_chunks = []
        for chunk in result_chunks:
            if len(chunk) <= effective_chunk_size:
                final_result_chunks.append(chunk)
            else:
                # Split by pure character count as last resort
                for i in range(0, len(chunk), effective_chunk_size):
                    char_chunk = chunk[i : i + effective_chunk_size]
                    if char_chunk.strip():
                        final_result_chunks.append(char_chunk)

        # Safety check: if we somehow generated too many chunks from a small document, something is wrong
        if len(text) < 1000 and len(final_result_chunks) > 100:
            logger.error(
                f"Suspicious chunking result: {len(text)} chars generated {len(final_result_chunks)} chunks. "
                f"Chunk size: {effective_chunk_size}. Returning single chunk as fallback."
            )
            return [text]

        # Apply chunk limit
        if len(final_result_chunks) > MAX_CHUNKS_TO_PROCESS:
            logger.warning(
                f"Reached maximum chunk limit of {MAX_CHUNKS_TO_PROCESS}. "
                f"Document may be truncated. Text length: {len(text)}, Chunk size: {effective_chunk_size}"
            )
            final_result_chunks = final_result_chunks[:MAX_CHUNKS_TO_PROCESS]

        return [chunk for chunk in final_result_chunks if chunk.strip()]

    def chunk_document(self, document: Document) -> list[Document]:
        """Split a document into chunks while preserving metadata.

        Args:
            document: The document to chunk

        Returns:
            List of chunked documents with preserved metadata
        """
        file_name = (
            document.metadata.get("file_name")
            or document.metadata.get("original_filename")
            or document.title
            or f"{document.source_type}:{document.source}"
        )

        # Start progress tracking
        self.progress_tracker.start_chunking(
            document.id,
            document.source,
            document.source_type,
            len(document.content),
            file_name,
        )

        logger.debug(
            "Starting default chunking",
            document_id=document.id,
            content_length=len(document.content),
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        try:
            # Split the text into chunks
            text_chunks = self._split_text(document.content)

            if not text_chunks:
                self.progress_tracker.finish_chunking(document.id, 0, "default")
                return []

            # Apply chunk limit at document level too
            if len(text_chunks) > MAX_CHUNKS_TO_PROCESS:
                logger.warning(
                    f"Document {document.id} generated {len(text_chunks)} chunks, "
                    f"limiting to {MAX_CHUNKS_TO_PROCESS}"
                )
                text_chunks = text_chunks[:MAX_CHUNKS_TO_PROCESS]

            # Create Document objects for each chunk using base class method
            chunk_documents = []
            for i, chunk_text in enumerate(text_chunks):
                chunk_doc = self._create_chunk_document(
                    original_doc=document,
                    chunk_content=chunk_text,
                    chunk_index=i,
                    total_chunks=len(text_chunks),
                    skip_nlp=False,
                )

                # Generate unique chunk ID
                chunk_doc.id = Document.generate_chunk_id(document.id, i)

                # Add strategy-specific metadata
                chunk_doc.metadata.update(
                    {
                        "chunking_strategy": "default",
                        "parent_document_id": document.id,
                    }
                )

                chunk_documents.append(chunk_doc)

            # Finish progress tracking
            self.progress_tracker.finish_chunking(
                document.id, len(chunk_documents), "default"
            )

            logger.debug(
                "Successfully chunked document",
                document_id=document.id,
                num_chunks=len(chunk_documents),
                strategy="default",
            )

            return chunk_documents

        except Exception as e:
            self.progress_tracker.log_error(document.id, str(e))
            raise
