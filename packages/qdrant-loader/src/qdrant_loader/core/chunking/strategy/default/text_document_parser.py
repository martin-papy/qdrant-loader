"""Document parser for plain text documents."""

import re
from typing import Any

from qdrant_loader.core.chunking.strategy.base.document_parser import BaseDocumentParser


class TextDocumentParser(BaseDocumentParser):
    """Parser for plain text documents.

    This parser analyzes text structure including paragraphs, sentences,
    and basic content characteristics to support intelligent chunking.
    """

    def parse_document_structure(self, content: str) -> dict[str, Any]:
        """Analyze text structure (paragraphs, sentences, formatting).

        Args:
            content: The text content to analyze

        Returns:
            Dictionary containing structural analysis of the text
        """
        paragraphs = self._split_paragraphs(content)
        sentences = self._split_sentences(content)

        # Analyze content characteristics
        analysis = self.analyze_content_characteristics(content)

        # Add text-specific structure information
        structure = {
            "structure_type": "plain_text",
            "paragraph_count": len(paragraphs),
            "sentence_count": len(sentences),
            "avg_paragraph_length": (
                sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0
            ),
            "avg_sentence_length": (
                sum(len(s) for s in sentences) / len(sentences) if sentences else 0
            ),
            "has_list_items": self._has_list_items(content),
            "has_numbered_sections": self._has_numbered_sections(content),
            "formatting_indicators": self._analyze_formatting(content),
            "content_density": self._calculate_content_density(content),
        }

        # Merge with base analysis
        structure.update(analysis)

        return structure

    def extract_section_metadata(self, section: Any) -> dict[str, Any]:
        """Extract metadata from a text section.

        Args:
            section: The text section (string content)

        Returns:
            Dictionary containing section metadata
        """
        if not isinstance(section, str):
            section = str(section)

        metadata = {
            "section_type": "text_paragraph",
            "length": len(section),
            "word_count": len(section.split()),
            "sentence_count": len(self._split_sentences(section)),
            "has_formatting": self._has_formatting_markers(section),
            "is_list_item": self._is_list_item(section),
            "is_numbered_item": self._is_numbered_item(section),
            "content_type": self._classify_content_type(section),
        }

        return metadata

    def _split_paragraphs(self, content: str) -> list[str]:
        """Split content into paragraphs.

        Args:
            content: The content to split

        Returns:
            List of paragraph strings
        """
        # Split on double newlines, but also handle single newlines with significant whitespace
        paragraphs = []

        # First split on double newlines
        double_newline_splits = content.split("\n\n")

        for split in double_newline_splits:
            # Further split on single newlines if they separate distinct content
            lines = split.split("\n")
            current_paragraph = []

            for line in lines:
                line = line.strip()
                if not line:
                    # Empty line - finish current paragraph if it has content
                    if current_paragraph:
                        paragraphs.append("\n".join(current_paragraph))
                        current_paragraph = []
                elif self._is_new_paragraph_start(line, current_paragraph):
                    # This line starts a new paragraph
                    if current_paragraph:
                        paragraphs.append("\n".join(current_paragraph))
                    current_paragraph = [line]
                else:
                    # This line continues the current paragraph
                    current_paragraph.append(line)

            # Add any remaining paragraph
            if current_paragraph:
                paragraphs.append("\n".join(current_paragraph))

        return [p.strip() for p in paragraphs if p.strip()]

    def _split_sentences(self, content: str) -> list[str]:
        """Split content into sentences.

        Args:
            content: The content to split

        Returns:
            List of sentence strings
        """
        # Use a more sophisticated sentence splitting pattern
        sentence_pattern = r"(?<=[.!?])\s+(?=[A-Z])"
        sentences = re.split(sentence_pattern, content)

        # Clean up and filter sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 3:  # Filter out very short fragments
                cleaned_sentences.append(sentence)

        return cleaned_sentences

    def _has_list_items(self, content: str) -> bool:
        """Check if content contains list items.

        Args:
            content: The content to check

        Returns:
            True if content contains list items
        """
        list_patterns = [
            r"^\s*[-*+]\s+",  # Bullet points
            r"^\s*\d+\.\s+",  # Numbered lists
            r"^\s*[a-zA-Z]\.\s+",  # Lettered lists
            r"^\s*[ivxlcdm]+\.\s+",  # Roman numerals
        ]

        for pattern in list_patterns:
            if re.search(pattern, content, re.MULTILINE):
                return True

        return False

    def _has_numbered_sections(self, content: str) -> bool:
        """Check if content has numbered sections.

        Args:
            content: The content to check

        Returns:
            True if content has numbered sections
        """
        # Look for patterns like "1. Introduction", "Section 1", "Chapter 1", etc.
        section_patterns = [
            r"^\s*\d+\.\s+[A-Z]",  # "1. Section Title"
            r"^\s*Section\s+\d+",  # "Section 1"
            r"^\s*Chapter\s+\d+",  # "Chapter 1"
            r"^\s*Part\s+\d+",  # "Part 1"
        ]

        for pattern in section_patterns:
            if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                return True

        return False

    def _analyze_formatting(self, content: str) -> dict[str, bool]:
        """Analyze formatting indicators in the text.

        Args:
            content: The content to analyze

        Returns:
            Dictionary of formatting indicators
        """
        return {
            "has_bold_text": bool(re.search(r"\*\*.*?\*\*|__.*?__", content)),
            "has_italic_text": bool(re.search(r"\*.*?\*|_.*?_", content)),
            "has_quotes": bool(re.search(r'["""].*?["""]', content)),
            "has_parenthetical": bool(re.search(r"\(.*?\)", content)),
            "has_brackets": bool(re.search(r"\[.*?\]", content)),
            "has_caps_words": bool(re.search(r"\b[A-Z]{2,}\b", content)),
            "has_email_addresses": bool(
                re.search(
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", content
                )
            ),
            "has_urls": bool(re.search(r"https?://[^\s]+", content)),
        }

    def _calculate_content_density(self, content: str) -> float:
        """Calculate content density (ratio of content to whitespace).

        Args:
            content: The content to analyze

        Returns:
            Content density ratio (0.0 to 1.0)
        """
        if not content:
            return 0.0

        non_whitespace_chars = len(re.sub(r"\s", "", content))
        total_chars = len(content)

        return non_whitespace_chars / total_chars if total_chars > 0 else 0.0

    def _is_new_paragraph_start(self, line: str, current_paragraph: list[str]) -> bool:
        """Determine if a line starts a new paragraph.

        Args:
            line: The line to check
            current_paragraph: Current paragraph content

        Returns:
            True if line should start a new paragraph
        """
        if not current_paragraph:
            return True

        # Check for list items
        if self._is_list_item(line) or self._is_numbered_item(line):
            return True

        # Check for section headers
        if self._looks_like_header(line):
            return True

        # Check for significant indentation change
        prev_line = current_paragraph[-1] if current_paragraph else ""
        if self._has_significant_indentation_change(prev_line, line):
            return True

        return False

    def _has_formatting_markers(self, text: str) -> bool:
        """Check if text has formatting markers.

        Args:
            text: The text to check

        Returns:
            True if text has formatting markers
        """
        formatting_patterns = [
            r"\*\*.*?\*\*",  # Bold
            r"__.*?__",  # Bold alternative
            r"\*.*?\*",  # Italic
            r"_.*?_",  # Italic alternative
            r"`.*?`",  # Code
        ]

        for pattern in formatting_patterns:
            if re.search(pattern, text):
                return True

        return False

    def _is_list_item(self, text: str) -> bool:
        """Check if text is a list item.

        Args:
            text: The text to check

        Returns:
            True if text is a list item
        """
        return bool(re.match(r"^\s*[-*+]\s+", text))

    def _is_numbered_item(self, text: str) -> bool:
        """Check if text is a numbered item.

        Args:
            text: The text to check

        Returns:
            True if text is a numbered item
        """
        return bool(re.match(r"^\s*\d+\.\s+", text))

    def _classify_content_type(self, text: str) -> str:
        """Classify the type of content.

        Args:
            text: The text to classify

        Returns:
            Content type classification
        """
        if self._is_list_item(text):
            return "list_item"
        elif self._is_numbered_item(text):
            return "numbered_item"
        elif self._looks_like_header(text):
            return "header"
        elif len(text.split()) < 5:
            return "fragment"
        elif "." not in text:
            return "title_or_label"
        else:
            return "paragraph"

    def _looks_like_header(self, text: str) -> bool:
        """Check if text looks like a header or title.

        Args:
            text: The text to check

        Returns:
            True if text looks like a header
        """
        # Headers typically:
        # - Are short
        # - Don't end with punctuation
        # - May be in title case
        # - May have numbers

        if len(text) > 100:  # Too long for a header
            return False

        if text.endswith((".", "!", "?")):  # Headers usually don't end with punctuation
            return False

        # Check for title case or all caps
        words = text.split()
        if len(words) > 1:
            title_case_words = sum(1 for word in words if word[0].isupper())
            if title_case_words / len(words) > 0.5:
                return True

        # Check for section numbering
        if re.match(r"^\d+\.?\s+", text):
            return True

        return False

    def _has_significant_indentation_change(
        self, prev_line: str, current_line: str
    ) -> bool:
        """Check for significant indentation change between lines.

        Args:
            prev_line: Previous line
            current_line: Current line

        Returns:
            True if there's a significant indentation change
        """
        if not prev_line:
            return False

        prev_indent = len(prev_line) - len(prev_line.lstrip())
        current_indent = len(current_line) - len(current_line.lstrip())

        # Significant change is more than 4 spaces
        return abs(current_indent - prev_indent) > 4
