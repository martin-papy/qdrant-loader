"""Default chunking strategy for text documents."""

import re
from typing import Any

import structlog

from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy
from qdrant_loader.core.chunking.progress_tracker import ChunkingProgressTracker
from qdrant_loader.core.document import Document
from qdrant_loader.config import Settings

logger = structlog.get_logger(__name__)


class DefaultChunkingStrategy(BaseChunkingStrategy):
    """Default text chunking strategy using simple text splitting."""

    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.progress_tracker = ChunkingProgressTracker(logger)

    def _split_text(self, text: str) -> list[str]:
        """Split text into chunks using sentence boundaries and size limits.

        Args:
            text: The text to split

        Returns:
            List of text chunks
        """
        if not text.strip():
            return []

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
                and len(current_chunk) + len(paragraph) + 2 > self.chunk_size
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
            if len(chunk) <= self.chunk_size:
                final_chunks.append(chunk)
            else:
                # Split large chunks by sentences
                sentences = re.split(r"(?<=[.!?])\s+", chunk)
                current_subchunk = ""

                for sentence in sentences:
                    if (
                        current_subchunk
                        and len(current_subchunk) + len(sentence) + 1 > self.chunk_size
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
            if len(chunk) <= self.chunk_size:
                result_chunks.append(chunk)
            else:
                # Split by character count with word boundaries
                words = chunk.split()
                current_word_chunk = ""

                for word in words:
                    if (
                        current_word_chunk
                        and len(current_word_chunk) + len(word) + 1 > self.chunk_size
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

        return [chunk for chunk in result_chunks if chunk.strip()]

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

        try:
            # Split the text into chunks
            text_chunks = self._split_text(document.content)

            if not text_chunks:
                self.progress_tracker.finish_chunking(document.id, 0, "default")
                return []

            # Create Document objects for each chunk
            chunk_documents = []
            for i, chunk_text in enumerate(text_chunks):
                chunk_metadata = document.metadata.copy()
                chunk_metadata.update(
                    {
                        "chunk_index": i,
                        "total_chunks": len(text_chunks),
                        "chunk_size": len(chunk_text),
                        "chunking_strategy": "default",
                        "parent_document_id": document.id,
                    }
                )

                chunk_doc = Document(
                    title=f"{document.title} (chunk {i+1}/{len(text_chunks)})",
                    content=chunk_text,
                    content_type=document.content_type,
                    source=document.source,
                    source_type=document.source_type,
                    url=document.url,
                    metadata=chunk_metadata,
                    created_at=document.created_at,
                    updated_at=document.updated_at,
                )
                chunk_documents.append(chunk_doc)

            # Finish progress tracking
            self.progress_tracker.finish_chunking(
                document.id, len(chunk_documents), "default"
            )
            return chunk_documents

        except Exception as e:
            self.progress_tracker.log_error(document.id, str(e))
            raise
