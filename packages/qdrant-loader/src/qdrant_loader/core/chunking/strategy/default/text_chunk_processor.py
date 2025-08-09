"""Text-specific chunk processor for document creation and management."""

from typing import Any

from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.strategy.base.chunk_processor import BaseChunkProcessor
from qdrant_loader.core.document import Document


class TextChunkProcessor(BaseChunkProcessor):
    """Chunk processor for text documents with enhanced text-specific processing."""

    def __init__(self, settings: Settings):
        super().__init__(settings)
        # Get strategy-specific configuration
        self.default_config = settings.global_config.chunking.strategies.default

    def create_chunk_document(
        self,
        original_doc: Document,
        chunk_content: str,
        chunk_index: int,
        total_chunks: int,
        chunk_metadata: dict[str, Any],
        skip_nlp: bool = False,
    ) -> Document:
        """Create a document for a text chunk with enhanced metadata."""

        # Generate unique chunk ID
        chunk_id = self.generate_chunk_id(original_doc, chunk_index)

        # Create base metadata
        base_metadata = self.create_base_chunk_metadata(
            original_doc, chunk_index, total_chunks, chunk_metadata
        )

        # Add text-specific metadata
        text_metadata = self._create_text_specific_metadata(chunk_content, original_doc)
        base_metadata.update(text_metadata)

        # Create chunk document
        chunk_doc = Document(
            id=chunk_id,
            content=chunk_content,
            metadata=base_metadata,
            source=original_doc.source,
            source_type=original_doc.source_type,
            url=original_doc.url,
            content_type=original_doc.content_type,
            title=f"{original_doc.title} - Chunk {chunk_index + 1}",
        )

        return chunk_doc

    def _create_text_specific_metadata(
        self, content: str, original_doc: Document
    ) -> dict[str, Any]:
        """Create text-specific metadata for the chunk."""
        metadata = {
            "chunk_strategy": "text",
            "processing_method": "intelligent_splitting",
            "content_analysis": self._analyze_chunk_content(content),
            "quality_metrics": self._calculate_quality_metrics(content),
            "text_characteristics": self._extract_text_characteristics(content),
        }

        # Add semantic analysis indicators if enabled
        if self.default_config.enable_semantic_analysis:
            metadata["semantic_analysis_enabled"] = True
            metadata["semantic_indicators"] = self._extract_semantic_indicators(content)

        # Add entity extraction indicators if enabled
        if self.default_config.enable_entity_extraction:
            metadata["entity_extraction_enabled"] = True
            metadata["entity_hints"] = self._extract_entity_hints(content)

        return metadata

    def _analyze_chunk_content(self, content: str) -> dict[str, Any]:
        """Analyze the content structure and characteristics of the chunk."""
        words = content.split()
        sentences = content.split(".")
        paragraphs = content.split("\n\n")

        return {
            "word_count": len(words),
            "sentence_count": len([s for s in sentences if s.strip()]),
            "paragraph_count": len([p for p in paragraphs if p.strip()]),
            "avg_words_per_sentence": len(words)
            / max(1, len([s for s in sentences if s.strip()])),
            "character_count": len(content),
            "content_density": (
                len(content.replace(" ", "")) / len(content) if content else 0
            ),
        }

    def _calculate_quality_metrics(self, content: str) -> dict[str, Any]:
        """Calculate quality metrics for the chunk."""
        words = content.split()

        # Content completeness (does it end with proper punctuation?)
        ends_properly = content.strip().endswith((".", "!", "?", ":", ";"))

        # Content coherence (rough estimate based on word repetition)
        unique_words = len({word.lower() for word in words})
        word_diversity = unique_words / len(words) if words else 0

        # Content readability (simple metric based on sentence structure)
        sentences = [s.strip() for s in content.split(".") if s.strip()]
        avg_sentence_length = (
            sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        )

        return {
            "ends_properly": ends_properly,
            "word_diversity": round(word_diversity, 3),
            "avg_sentence_length": round(avg_sentence_length, 1),
            "readability_score": self._estimate_readability(
                avg_sentence_length, word_diversity
            ),
            "chunk_completeness": self._assess_chunk_completeness(content),
        }

    def _extract_text_characteristics(self, content: str) -> dict[str, Any]:
        """Extract various text characteristics from the chunk."""
        import re

        return {
            "has_numbers": bool(re.search(r"\d+", content)),
            "has_dates": bool(re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", content)),
            "has_urls": bool(re.search(r"https?://\S+", content)),
            "has_email": bool(
                re.search(
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", content
                )
            ),
            "has_phone": bool(re.search(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", content)),
            "has_currency": bool(re.search(r"\$\d+(?:\.\d{2})?", content)),
            "has_percentages": bool(re.search(r"\b\d+(?:\.\d+)?%\b", content)),
            "has_quotes": '"' in content or "'" in content,
            "has_parentheses": "(" in content and ")" in content,
            "has_formatting": bool(re.search(r"[*_`#]", content)),
            "language_indicators": self._detect_language_indicators(content),
        }

    def _extract_semantic_indicators(self, content: str) -> dict[str, Any]:
        """Extract indicators for semantic analysis."""
        import re

        # Topic indicators (simple keyword-based)
        business_keywords = [
            "company",
            "business",
            "market",
            "revenue",
            "profit",
            "customer",
        ]
        tech_keywords = [
            "software",
            "technology",
            "system",
            "data",
            "algorithm",
            "code",
        ]
        academic_keywords = [
            "research",
            "study",
            "analysis",
            "theory",
            "methodology",
            "conclusion",
        ]

        content_lower = content.lower()

        return {
            "topic_indicators": {
                "business": sum(1 for kw in business_keywords if kw in content_lower),
                "technology": sum(1 for kw in tech_keywords if kw in content_lower),
                "academic": sum(1 for kw in academic_keywords if kw in content_lower),
            },
            "discourse_markers": {
                "enumeration": bool(
                    re.search(r"\b(first|second|third|finally|lastly)\b", content_lower)
                ),
                "causation": bool(
                    re.search(
                        r"\b(because|therefore|thus|consequently|as a result)\b",
                        content_lower,
                    )
                ),
                "contrast": bool(
                    re.search(
                        r"\b(however|although|despite|nevertheless|on the other hand)\b",
                        content_lower,
                    )
                ),
                "comparison": bool(
                    re.search(
                        r"\b(similarly|likewise|compared to|in contrast)\b",
                        content_lower,
                    )
                ),
            },
            "complexity_indicators": {
                "has_subordinate_clauses": bool(
                    re.search(r"\b(which|that|who|whom|whose)\b", content_lower)
                ),
                "has_conditionals": bool(
                    re.search(r"\b(if|unless|provided|assuming)\b", content_lower)
                ),
                "has_temporal_references": bool(
                    re.search(r"\b(when|while|before|after|during)\b", content_lower)
                ),
            },
        }

    def _extract_entity_hints(self, content: str) -> dict[str, Any]:
        """Extract hints for entity extraction."""
        import re

        # Potential entity patterns
        proper_nouns = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", content)
        acronyms = re.findall(r"\b[A-Z]{2,}\b", content)

        return {
            "proper_noun_count": len(proper_nouns),
            "acronym_count": len(acronyms),
            "capitalized_words": len(re.findall(r"\b[A-Z][a-z]+\b", content)),
            "potential_names": len(
                [noun for noun in proper_nouns if len(noun.split()) <= 3]
            ),
            "potential_organizations": len(
                [noun for noun in proper_nouns if len(noun.split()) > 1]
            ),
            "has_titles": bool(
                re.search(r"\b(Dr|Mr|Mrs|Ms|Prof|CEO|CTO|VP)\b\.?\s+[A-Z]", content)
            ),
            "has_locations": bool(
                re.search(
                    r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:City|State|Country|Street|Ave|Road))\b",
                    content,
                )
            ),
        }

    def _estimate_readability(
        self, avg_sentence_length: float, word_diversity: float
    ) -> str:
        """Estimate readability level based on simple metrics."""
        if avg_sentence_length < 10 and word_diversity > 0.7:
            return "easy"
        elif avg_sentence_length < 20 and word_diversity > 0.5:
            return "moderate"
        elif avg_sentence_length < 30:
            return "difficult"
        else:
            return "very_difficult"

    def _assess_chunk_completeness(self, content: str) -> float:
        """Assess how complete/coherent the chunk appears to be."""
        score = 0.0

        # Check for proper sentence endings
        if content.strip().endswith((".", "!", "?")):
            score += 0.3

        # Check for proper sentence beginnings
        if content.strip() and content.strip()[0].isupper():
            score += 0.2

        # Check for balanced punctuation
        open_parens = content.count("(")
        close_parens = content.count(")")
        open_quotes = content.count('"') + content.count("'")

        if open_parens == close_parens:
            score += 0.2
        if open_quotes % 2 == 0:  # Even number of quotes
            score += 0.1

        # Check for paragraph structure
        if "\n\n" in content or len(content.split(".")) > 1:
            score += 0.2

        return min(1.0, score)

    def _detect_language_indicators(self, content: str) -> dict[str, Any]:
        """Detect language indicators in the content."""
        content_lower = content.lower()

        # Common English function words
        english_indicators = [
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
        ]
        english_count = sum(
            1 for word in english_indicators if f" {word} " in f" {content_lower} "
        )

        return {
            "english_function_words": english_count,
            "likely_english": english_count >= 3,
            "punctuation_style": "american" if ". " in content else "other",
        }
