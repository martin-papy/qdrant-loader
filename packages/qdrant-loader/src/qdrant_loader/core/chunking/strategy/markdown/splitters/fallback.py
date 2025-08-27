"""Fallback splitter implementation extracted from `section_splitter`."""

import re

from qdrant_loader.core.chunking.strategy.markdown.splitters.base import BaseSplitter


class FallbackSplitter(BaseSplitter):
    """Simple fallback splitter for when other strategies fail."""

    def split_content(self, content: str, max_size: int) -> list[str]:
        """Simple chunking implementation based on fixed size.

        Args:
            content: Content to split
            max_size: Maximum chunk size

        Returns:
            List of content chunks
        """
        chunks: list[str] = []

        paragraphs = re.split(r"\n\s*\n", content)
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) <= max_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks


__all__ = ["FallbackSplitter"]
