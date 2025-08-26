"""Standard splitter implementation extracted from `section_splitter`."""

import re

from qdrant_loader.core.chunking.strategy.markdown.splitters.base import BaseSplitter


class StandardSplitter(BaseSplitter):
    """Standard markdown text splitter that preserves structure."""

    def split_content(self, content: str, max_size: int) -> list[str]:
        """Split a large section into smaller chunks while preserving markdown structure.

        Args:
            content: Section content to split
            max_size: Maximum chunk size

        Returns:
            List of content chunks
        """
        chunks: list[str] = []

        max_chunks_per_section = min(
            self.settings.global_config.chunking.strategies.markdown.max_chunks_per_section,
            self.settings.global_config.chunking.max_chunks_per_document // 2,
        )

        paragraphs = re.split(r"\n\s*\n", content)

        text_units: list[str] = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(para) > max_size:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                text_units.extend([s.strip() for s in sentences if s.strip()])
            else:
                text_units.append(para)

        i = 0
        while i < len(text_units) and len(chunks) < max_chunks_per_section:
            current_chunk = ""
            units_in_chunk = 0

            j = i
            while j < len(text_units):
                unit = text_units[j]

                if current_chunk and len(current_chunk) + len(unit) + 2 > max_size:
                    break

                if current_chunk:
                    current_chunk += "\n\n" + unit
                else:
                    current_chunk = unit

                units_in_chunk += 1
                j += 1

            if current_chunk.strip():
                chunks.append(current_chunk.strip())

            if units_in_chunk > 0:
                if self.chunk_overlap == 0:
                    advance = units_in_chunk
                else:
                    max_overlap_percent = (
                        self.settings.global_config.chunking.strategies.markdown.max_overlap_percentage
                    )
                    max_overlap_chars = int(len(current_chunk) * max_overlap_percent)
                    overlap_chars = min(self.chunk_overlap, max_overlap_chars)

                    if overlap_chars > 0 and len(current_chunk) > overlap_chars:
                        overlap_units = 0
                        overlap_size = 0
                        for k in range(j - 1, i - 1, -1):
                            unit_size = len(text_units[k])
                            if overlap_size + unit_size <= overlap_chars:
                                overlap_size += unit_size
                                overlap_units += 1
                            else:
                                break

                        advance = max(1, units_in_chunk - overlap_units)
                    else:
                        advance = max(1, units_in_chunk)

                i += advance
            else:
                i += 1

        if i < len(text_units) and len(chunks) >= max_chunks_per_section:
            from qdrant_loader.core.chunking.strategy.markdown import (
                section_splitter as _section_module,
            )

            _section_module.logger.warning(
                f"Section reached maximum chunks limit ({max_chunks_per_section}), truncating remaining content",
                extra={
                    "remaining_units": len(text_units) - i,
                    "max_chunks_per_section": max_chunks_per_section,
                },
            )

        return chunks


__all__ = ["StandardSplitter"]
