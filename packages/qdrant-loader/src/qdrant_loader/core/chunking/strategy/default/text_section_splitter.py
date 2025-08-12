"""Text-specific section splitter for intelligent text chunking."""

import re
from typing import Any

from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.strategy.base.section_splitter import (
    BaseSectionSplitter,
)
from qdrant_loader.core.document import Document


class TextSectionSplitter(BaseSectionSplitter):
    """Section splitter for text documents with intelligent boundary detection."""

    def __init__(self, settings: Settings):
        super().__init__(settings)
        # Get strategy-specific configuration
        self.default_config = settings.global_config.chunking.strategies.default
        self.min_chunk_size = self.default_config.min_chunk_size

    def split_sections(
        self, content: str, document: Document | None = None
    ) -> list[dict[str, Any]]:
        """Split text content into intelligent sections."""
        if not content.strip():
            # For empty content, return a single empty section for compatibility
            if content == "":
                return [
                    {
                        "content": "",
                        "metadata": {
                            "section_type": "empty",
                            "paragraph_index": 0,
                            "word_count": 0,
                            "has_formatting": False,
                            "content_characteristics": {
                                "sentence_count": 0,
                                "avg_sentence_length": 0,
                                "has_questions": False,
                                "has_exclamations": False,
                                "capitalization_ratio": 0,
                                "number_count": 0,
                            },
                        },
                    }
                ]
            return []

        # First, try to split by natural boundaries (paragraphs)
        sections = self._split_by_paragraphs(content)

        # If sections are too large, split them further
        final_sections = []
        for section in sections:
            if len(section["content"]) > self.chunk_size:
                subsections = self._split_large_section(section["content"])
                for i, subsection in enumerate(subsections):
                    final_sections.append(
                        {
                            "content": subsection,
                            "metadata": {
                                **section["metadata"],
                                "subsection_index": i,
                                "is_subsection": True,
                                "original_section_size": len(section["content"]),
                            },
                        }
                    )
            else:
                final_sections.append(section)

        # Merge small adjacent sections if beneficial
        merged_sections = self._merge_small_sections(final_sections)

        return merged_sections[: self.max_chunks_per_document]

    def _split_by_paragraphs(self, content: str) -> list[dict[str, Any]]:
        """Split content by paragraph boundaries."""
        paragraphs = re.split(r"\n\s*\n", content)
        sections = []

        for i, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                continue

            sections.append(
                {
                    "content": paragraph.strip(),
                    "metadata": {
                        "section_type": "paragraph",
                        "paragraph_index": i,
                        "word_count": len(paragraph.split()),
                        "has_formatting": self._has_special_formatting(paragraph),
                        "content_characteristics": self._analyze_paragraph_content(
                            paragraph
                        ),
                    },
                }
            )

        return sections

    def _split_large_section(self, content: str) -> list[str]:
        """Split large sections using intelligent boundary detection."""
        if len(content) <= self.chunk_size:
            return [content]

        chunks = []
        remaining = content
        previous_length = len(remaining)

        while len(remaining) > self.chunk_size:
            # Find the best split point within the chunk size limit
            split_point = self._find_best_split_point(remaining, self.chunk_size)

            if split_point <= 0:
                # Fallback: split at chunk size boundary
                split_point = self.chunk_size

            chunk = remaining[:split_point].strip()
            if chunk:
                chunks.append(chunk)

            # Move to next chunk with overlap if configured
            # Ensure we always make meaningful progress to prevent infinite loops
            overlap_start = max(0, split_point - self.chunk_overlap)

            # Safety check: ensure we advance at least min_chunk_size characters
            # This prevents infinite loops when overlap is too large
            min_advance = max(self.min_chunk_size, split_point // 2)
            overlap_start = min(overlap_start, split_point - min_advance)

            remaining = remaining[overlap_start:].strip()

            # Prevent infinite loops - ensure we're making progress
            if len(remaining) >= previous_length:
                # Force progress by advancing more aggressively
                remaining = remaining[min_advance:].strip()

            previous_length = len(remaining)

            # Additional safety: break if remaining content is small
            if len(remaining) <= self.min_chunk_size:
                break

        # Add remaining content if substantial
        if remaining.strip() and len(remaining.strip()) >= self.min_chunk_size:
            chunks.append(remaining.strip())

        return chunks

    def _find_best_split_point(self, content: str, max_size: int) -> int:
        """Find the best point to split content within the size limit."""
        if len(content) <= max_size:
            return len(content)

        # Try tokenizer-based boundary detection if available
        tokenizer_split = self._find_tokenizer_boundary(content, max_size)
        if tokenizer_split > 0:
            return tokenizer_split

        # Search window for optimal split point
        search_start = max(0, max_size - 200)
        search_end = min(len(content), max_size)
        search_text = content[search_start:search_end]

        # Priority order for split points
        split_patterns = [
            (r"\.\s+(?=[A-Z])", "sentence_end"),  # Sentence boundaries
            (r"\n\s*\n", "paragraph_break"),  # Paragraph breaks
            (r"\n(?=\s*[•\-\*\d])", "list_item"),  # List item boundaries
            (r"\.\s", "sentence_fragment"),  # Sentence fragments
            (r"[,;]\s+", "clause_boundary"),  # Clause boundaries
            (r"\s+", "word_boundary"),  # Word boundaries
        ]

        best_split = 0
        best_score = -1

        for pattern, split_type in split_patterns:
            matches = list(re.finditer(pattern, search_text))
            if not matches:
                continue

            for match in reversed(matches):  # Start from the end
                split_pos = search_start + match.end()

                # Score the split point
                score = self._score_split_point(content, split_pos, split_type)

                if score > best_score:
                    best_score = score
                    best_split = split_pos

        return best_split if best_split > 0 else max_size

    def _find_tokenizer_boundary(self, content: str, max_size: int) -> int:
        """Use tokenizer to find optimal boundary if available."""
        try:
            # Access the encoding from the parent strategy if available
            parent_strategy = getattr(self, "_parent_strategy", None)
            if (
                not parent_strategy
                or not hasattr(parent_strategy, "encoding")
                or not parent_strategy.encoding
            ):
                return 0

            encoding = parent_strategy.encoding

            # Get tokens for the content up to max_size
            text_to_encode = content[:max_size]
            tokens = encoding.encode(text_to_encode)

            # Find a good boundary by decoding back from slightly fewer tokens
            if len(tokens) > 10:  # Only if we have enough tokens
                boundary_tokens = tokens[
                    :-5
                ]  # Remove last few tokens to find clean boundary
                decoded_text = encoding.decode(boundary_tokens)

                # Find where the decoded text ends in the original content
                if decoded_text and decoded_text in content:
                    return len(decoded_text)

            return 0
        except Exception:
            # If tokenizer boundary detection fails, fall back to regex patterns
            return 0

    def _score_split_point(
        self, content: str, split_pos: int, split_type: str
    ) -> float:
        """Score a potential split point based on quality criteria."""
        if split_pos <= 0 or split_pos >= len(content):
            return 0.0

        score = 0.0

        # Base score by split type quality
        type_scores = {
            "sentence_end": 1.0,
            "paragraph_break": 0.9,
            "list_item": 0.8,
            "sentence_fragment": 0.6,
            "clause_boundary": 0.4,
            "word_boundary": 0.2,
        }
        score += type_scores.get(split_type, 0.1)

        # Bonus for balanced chunk sizes
        left_size = split_pos
        right_size = len(content) - split_pos
        size_ratio = min(left_size, right_size) / max(left_size, right_size)
        score += size_ratio * 0.3

        # Penalty for very small chunks
        if left_size < self.min_chunk_size:
            score -= 0.5

        return score

    def _merge_small_sections(
        self, sections: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Merge small adjacent sections for better chunk utilization."""
        if not sections:
            return []

        merged = []
        current_content = ""
        current_metadata = None
        accumulated_word_count = 0

        for section in sections:
            content = section["content"]
            word_count = len(content.split())

            # If current section is large enough or we have no accumulated content
            if (len(content) >= self.min_chunk_size and not current_content) or len(
                current_content + " " + content
            ) > self.chunk_size:

                # Save current accumulated content if any
                if current_content:
                    merged.append(
                        {
                            "content": current_content.strip(),
                            "metadata": {
                                **current_metadata,
                                "merged_sections": True,
                                "total_word_count": accumulated_word_count,
                            },
                        }
                    )

                # Start new section
                current_content = content
                current_metadata = section["metadata"].copy()
                accumulated_word_count = word_count
            else:
                # Merge with current content
                if current_content:
                    current_content += "\n\n" + content
                    current_metadata["merged_sections"] = True
                    accumulated_word_count += word_count
                else:
                    current_content = content
                    current_metadata = section["metadata"].copy()
                    accumulated_word_count = word_count

        # Add final accumulated content
        if current_content:
            merged.append(
                {
                    "content": current_content.strip(),
                    "metadata": {
                        **current_metadata,
                        "total_word_count": accumulated_word_count,
                    },
                }
            )

        return merged

    def _has_special_formatting(self, text: str) -> bool:
        """Check if text has special formatting indicators."""
        formatting_patterns = [
            r"^\s*[•\-\*]\s",  # Bullet points
            r"^\s*\d+\.\s",  # Numbered lists
            r"[A-Z][A-Z\s]{2,}",  # All caps (headings)
            r"\*\*.*?\*\*",  # Bold text
            r"_.*?_",  # Italic text
            r"`.*?`",  # Code formatting
        ]

        return any(
            re.search(pattern, text, re.MULTILINE) for pattern in formatting_patterns
        )

    def _analyze_paragraph_content(self, paragraph: str) -> dict[str, Any]:
        """Analyze paragraph content characteristics."""
        return {
            "sentence_count": len(re.split(r"[.!?]+", paragraph)),
            "avg_sentence_length": len(paragraph)
            / max(1, len(re.split(r"[.!?]+", paragraph))),
            "has_questions": "?" in paragraph,
            "has_exclamations": "!" in paragraph,
            "capitalization_ratio": len(re.findall(r"[A-Z]", paragraph))
            / max(1, len(paragraph)),
            "number_count": len(re.findall(r"\d+", paragraph)),
        }
