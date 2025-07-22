"""Default chunking strategy for text documents.

This strategy uses character-based chunking for consistency with other strategies.
When a tokenizer is available, it's used for better boundary detection to avoid
splitting in the middle of tokens, but the chunk size limits are still based on
character count.
"""

import re

import structlog

from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.progress_tracker import ChunkingProgressTracker
from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy
from qdrant_loader.core.document import Document

logger = structlog.get_logger(__name__)

# Maximum number of chunks to process to prevent performance issues
MAX_CHUNKS_TO_PROCESS = 1000


class DefaultChunkingStrategy(BaseChunkingStrategy):
    """Default text chunking strategy using character-based splitting.
    
    This strategy splits text into chunks based on character count, ensuring
    consistency with other chunking strategies like the markdown strategy.
    When a tokenizer is available, it's used to find better split boundaries
    (avoiding splits in the middle of tokens/words), but the size limits
    are always based on character count.
    """

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
            chunking_method="character-based" + (" with token boundary detection" if self.encoding is not None else ""),
        )

        # Warn about suspiciously small chunk sizes
        if self.chunk_size < 100:
            logger.warning(
                f"Very small chunk_size detected: {self.chunk_size} characters. "
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
        """Split text using tokenizer for accurate token boundary detection but character-based sizing.

        Args:
            text: The text to split

        Returns:
            List of text chunks
        """
        if self.encoding is None:
            # Fallback to character-based chunking
            return self._split_text_without_tokenizer(text)

        # Use character-based size limit (consistent with markdown strategy)
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start_char = 0
        
        while start_char < len(text) and len(chunks) < MAX_CHUNKS_TO_PROCESS:
            # Calculate end position based on character count
            end_char = min(start_char + self.chunk_size, len(text))
            
            # Get the chunk text
            chunk_text = text[start_char:end_char]
            
            # If we're not at the end of the text, try to find a good token boundary
            # to avoid splitting in the middle of words/tokens
            if end_char < len(text):
                # Try to encode/decode to find a clean token boundary
                try:
                    # Get tokens for the chunk
                    tokens = self.encoding.encode(chunk_text)
                    
                    # If the chunk ends mid-token, back up to the last complete token
                    # by decoding and checking if we get the same text
                    decoded_text = self.encoding.decode(tokens)
                    if len(decoded_text) < len(chunk_text):
                        # The last token was incomplete, use the decoded text
                        chunk_text = decoded_text
                        end_char = start_char + len(chunk_text)
                    
                    # Alternatively, try to find a word boundary near the target end
                    remaining_chars = self.chunk_size - len(chunk_text)
                    if remaining_chars > 0 and end_char < len(text):
                        # Look ahead a bit to find a word boundary
                        lookahead_end = min(end_char + min(100, remaining_chars), len(text))
                        lookahead_text = text[end_char:lookahead_end]
                        
                        # Find the first word boundary (space, newline, punctuation)
                        import re
                        word_boundary_match = re.search(r'[\s\n\.\!\?\;]', lookahead_text)
                        if word_boundary_match:
                            boundary_pos = word_boundary_match.start()
                            end_char = end_char + boundary_pos + 1
                            chunk_text = text[start_char:end_char]
                
                except Exception:
                    # If tokenizer operations fail, stick with character-based splitting
                    pass
            
            chunks.append(chunk_text)

            # Calculate overlap in characters and move start position forward
            if self.chunk_overlap > 0 and end_char < len(text):
                # Calculate how much to advance (chunk_size - overlap)
                advance = max(1, self.chunk_size - self.chunk_overlap)
                start_char += advance
            else:
                # No overlap, advance by full chunk size
                start_char = end_char

            # If we're near the end and the remaining text is small, include it in the last chunk
            if start_char < len(text) and (len(text) - start_char) <= self.chunk_overlap:
                # Create final chunk with remaining text
                final_chunk_text = text[start_char:]
                if final_chunk_text.strip():  # Only add if there's meaningful content
                    chunks.append(final_chunk_text)
                break

        # Log warning if we hit the chunk limit
        if len(chunks) >= MAX_CHUNKS_TO_PROCESS and start_char < len(text):
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
