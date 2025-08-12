"""Text-specific metadata extractor for enhanced text analysis."""

import re
from typing import Any

from qdrant_loader.core.chunking.strategy.base.metadata_extractor import (
    BaseMetadataExtractor,
)
from qdrant_loader.core.document import Document


class TextMetadataExtractor(BaseMetadataExtractor):
    """Metadata extractor for text documents with enhanced text analysis."""

    def extract_hierarchical_metadata(
        self, content: str, chunk_metadata: dict[str, Any], document: Document
    ) -> dict[str, Any]:
        """Extract comprehensive metadata specific to text chunks."""
        metadata = chunk_metadata.copy()

        # Add text-specific metadata
        words = content.split()
        sentences = self._split_sentences(content)
        paragraphs = content.split("\n\n")

        metadata.update(
            {
                "word_count": len(words),
                "character_count": len(content),
                "paragraph_count": len([p for p in paragraphs if p.strip()]),
                "sentence_count": len(sentences),
                "avg_word_length": self._calculate_avg_word_length(content),
                "reading_time_minutes": self._estimate_reading_time(content),
                "content_type": "text",
                "language": self._detect_language(content),
                "text_density": self._calculate_text_density(content),
                "formatting_indicators": self._analyze_formatting(content),
            }
        )

        return metadata

    def extract_entities(self, text: str) -> list[str]:
        """Extract named entities from text using basic pattern matching."""
        entities = []

        # Extract potential entities (capitalized words/phrases)
        capitalized_words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)

        # Filter out common false positives and single letters
        stop_words = {
            "The",
            "This",
            "That",
            "These",
            "Those",
            "When",
            "Where",
            "Why",
            "How",
            "What",
            "He",
            "She",
            "It",
            "We",
            "They",
            "I",
            "You",
            "Dr",
            "Mr",
            "Ms",
            "Mrs",
        }
        entities = [
            word
            for word in capitalized_words
            if word not in stop_words and len(word) > 2
        ]

        # Remove duplicates while preserving order
        seen = set()
        unique_entities = []
        for entity in entities:
            if entity not in seen:
                seen.add(entity)
                unique_entities.append(entity)

        return unique_entities[:10]  # Limit to top 10 entities

    def _split_sentences(self, content: str) -> list[str]:
        """Split content into sentences."""
        sentences = re.split(r"(?<=[.!?])\s+", content)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 3]

    def _calculate_avg_word_length(self, content: str) -> float:
        """Calculate average word length."""
        words = re.findall(r"\b\w+\b", content)
        if not words:
            return 0.0
        return sum(len(word) for word in words) / len(words)

    def _estimate_reading_time(self, content: str) -> float:
        """Estimate reading time in minutes (assuming 200 words per minute)."""
        word_count = len(content.split())
        return word_count / 200

    def _detect_language(self, content: str) -> str:
        """Detect content language using basic heuristics."""
        # Simple English detection based on common words
        english_words = {
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "did",
            "will",
            "would",
            "could",
            "should",
            "can",
            "may",
            "might",
            "must",
            "shall",
        }

        words = re.findall(r"\b\w+\b", content.lower())
        if not words:
            return "unknown"

        english_count = sum(1 for word in words if word in english_words)
        if len(words) >= 10 and english_count / len(words) > 0.10:
            return "en"

        return "unknown"

    def _calculate_text_density(self, content: str) -> dict[str, float]:
        """Calculate text density metrics."""
        total_chars = len(content)
        if total_chars == 0:
            return {
                "alphanumeric_ratio": 0.0,
                "whitespace_ratio": 0.0,
                "punctuation_ratio": 0.0,
            }

        alphanumeric_chars = len(re.findall(r"[a-zA-Z0-9]", content))
        whitespace_chars = len(re.findall(r"\s", content))
        punctuation_chars = len(re.findall(r"[^\w\s]", content))

        return {
            "alphanumeric_ratio": alphanumeric_chars / total_chars,
            "whitespace_ratio": whitespace_chars / total_chars,
            "punctuation_ratio": punctuation_chars / total_chars,
        }

    def _analyze_formatting(self, content: str) -> dict[str, bool]:
        """Analyze text formatting indicators."""
        return {
            "has_bullet_points": bool(
                re.search(r"^\s*[•\-\*]\s", content, re.MULTILINE)
            ),
            "has_numbered_lists": bool(
                re.search(r"^\s*\d+\.\s", content, re.MULTILINE)
            ),
            "has_email_addresses": bool(
                re.search(
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", content
                )
            ),
            "has_urls": bool(re.search(r"https?://\S+", content)),
            "has_phone_numbers": bool(
                re.search(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", content)
            ),
            "has_dates": bool(re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", content)),
            "has_currency": bool(
                re.search(r"\$\d+(?:\.\d{2})?|\d+\s?(?:USD|EUR|GBP)", content)
            ),
            "has_percentages": bool(re.search(r"\d+(?:\.\d+)?%", content)),
        }
