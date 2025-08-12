"""Linguistic query preprocessing for improved search accuracy."""

import re
import time
from dataclasses import dataclass
from typing import Any

from ...utils.logging import LoggingConfig
from .spacy_analyzer import SpaCyQueryAnalyzer

logger = LoggingConfig.get_logger(__name__)


@dataclass
class PreprocessingResult:
    """Container for query preprocessing results."""

    original_query: str
    preprocessed_query: str
    lemmatized_tokens: list[str]
    filtered_tokens: list[str]
    removed_stopwords: list[str]
    normalized_tokens: list[str]
    processing_steps: list[str]
    processing_time_ms: float


class LinguisticPreprocessor:
    """Linguistic query preprocessing using spaCy for lemmatization and filtering."""

    def __init__(self, spacy_analyzer: SpaCyQueryAnalyzer):
        """Initialize the linguistic preprocessor.

        Args:
            spacy_analyzer: SpaCy analyzer instance for linguistic processing
        """
        self.spacy_analyzer = spacy_analyzer
        self.logger = LoggingConfig.get_logger(__name__)

        # Preprocessing configuration
        self.min_token_length = 2
        self.max_token_length = 50
        self.preserve_entities = True
        self.preserve_numbers = True

        # Custom stop words (in addition to spaCy's)
        self.custom_stopwords = {
            "find",
            "show",
            "give",
            "tell",
            "search",
            "look",
            "get",
            "want",
            "need",
            "please",
            "help",
            "can",
            "could",
            "would",
            "should",
            "may",
            "might",
            "also",
            "just",
            "really",
            "very",
            "quite",
            "rather",
            "pretty",
            "much",
        }

        # Technical terms to preserve (don't lemmatize)
        self.preserve_terms = {
            "api",
            "apis",
            "database",
            "databases",
            "server",
            "servers",
            "authentication",
            "authorization",
            "oauth",
            "jwt",
            "ssl",
            "tls",
            "crud",
            "rest",
            "restful",
            "graphql",
            "json",
            "xml",
            "yaml",
            "git",
            "github",
            "gitlab",
            "jira",
            "confluence",
            "jenkins",
        }

        # Cache for preprocessing results
        self._preprocessing_cache: dict[str, PreprocessingResult] = {}

    def preprocess_query(
        self, query: str, preserve_structure: bool = False
    ) -> PreprocessingResult:
        """Preprocess query with lemmatization, stop word removal, and normalization.

        Args:
            query: The original query to preprocess
            preserve_structure: If True, preserve query structure for phrase queries

        Returns:
            PreprocessingResult containing preprocessed query and metadata
        """
        start_time = time.time()

        # Check cache first
        cache_key = f"{query}:{preserve_structure}"
        if cache_key in self._preprocessing_cache:
            cached = self._preprocessing_cache[cache_key]
            logger.debug(f"Using cached preprocessing for: {query[:50]}...")
            return cached

        processing_steps = []

        try:
            # Step 1: Initial cleaning
            cleaned_query = self._initial_cleaning(query)
            processing_steps.append("initial_cleaning")

            # Step 2: Process with spaCy
            doc = self.spacy_analyzer.nlp(cleaned_query)
            processing_steps.append("spacy_processing")

            # Step 3: Extract and process tokens
            tokens_info = self._extract_tokens(doc)
            processing_steps.append("token_extraction")

            # Step 4: Lemmatization with preservation rules
            lemmatized_tokens = self._lemmatize_tokens(tokens_info)
            processing_steps.append("lemmatization")

            # Step 5: Stop word filtering
            filtered_tokens, removed_stopwords = self._filter_stopwords(
                lemmatized_tokens, doc
            )
            processing_steps.append("stopword_filtering")

            # Step 6: Normalization
            normalized_tokens = self._normalize_tokens(filtered_tokens)
            processing_steps.append("normalization")

            # Step 7: Build preprocessed query
            if preserve_structure:
                preprocessed_query = self._rebuild_structured_query(
                    normalized_tokens, doc
                )
            else:
                preprocessed_query = " ".join(normalized_tokens)
            processing_steps.append("query_reconstruction")

            # Create result
            processing_time_ms = (time.time() - start_time) * 1000

            result = PreprocessingResult(
                original_query=query,
                preprocessed_query=preprocessed_query,
                lemmatized_tokens=lemmatized_tokens,
                filtered_tokens=filtered_tokens,
                removed_stopwords=removed_stopwords,
                normalized_tokens=normalized_tokens,
                processing_steps=processing_steps,
                processing_time_ms=processing_time_ms,
            )

            # Cache the result
            self._preprocessing_cache[cache_key] = result

            logger.debug(
                "🔥 Query preprocessing completed",
                original_query=query[:50],
                preprocessed_query=preprocessed_query[:50],
                tokens_removed=len(removed_stopwords),
                processing_time_ms=processing_time_ms,
            )

            return result

        except Exception as e:
            logger.warning(f"Query preprocessing failed: {e}")
            # Return minimal preprocessing
            processing_time_ms = (time.time() - start_time) * 1000
            return PreprocessingResult(
                original_query=query,
                preprocessed_query=query,
                lemmatized_tokens=[],
                filtered_tokens=[],
                removed_stopwords=[],
                normalized_tokens=[],
                processing_steps=["error"],
                processing_time_ms=processing_time_ms,
            )

    def _initial_cleaning(self, query: str) -> str:
        """Perform initial query cleaning."""
        # Remove extra whitespace
        cleaned = re.sub(r"\s+", " ", query.strip())

        # Normalize punctuation
        cleaned = re.sub(r"[^\w\s\?\!\-\.]", " ", cleaned)

        # Handle contractions
        contractions = {
            "don't": "do not",
            "won't": "will not",
            "can't": "cannot",
            "n't": " not",
            "'re": " are",
            "'ve": " have",
            "'ll": " will",
            "'d": " would",
            "'m": " am",
        }

        for contraction, expansion in contractions.items():
            cleaned = cleaned.replace(contraction, expansion)

        return cleaned

    def _extract_tokens(self, doc) -> list[dict[str, Any]]:
        """Extract token information from spaCy doc."""
        tokens_info = []

        for token in doc:
            if not token.is_space:  # Skip whitespace tokens
                token_info = {
                    "text": token.text,
                    "lemma": token.lemma_,
                    "pos": token.pos_,
                    "tag": token.tag_,
                    "is_alpha": token.is_alpha,
                    "is_stop": token.is_stop,
                    "is_punct": token.is_punct,
                    "is_digit": token.like_num,
                    "ent_type": token.ent_type_,
                    "ent_iob": token.ent_iob_,
                }
                tokens_info.append(token_info)

        return tokens_info

    def _lemmatize_tokens(self, tokens_info: list[dict[str, Any]]) -> list[str]:
        """Lemmatize tokens with preservation rules."""
        lemmatized = []

        for token_info in tokens_info:
            text = token_info["text"].lower()
            lemma = token_info["lemma"].lower()

            # Preserve certain technical terms
            if text in self.preserve_terms:
                lemmatized.append(text)
            # Preserve entities
            elif self.preserve_entities and token_info["ent_type"]:
                lemmatized.append(text)
            # Preserve numbers if configured
            elif self.preserve_numbers and token_info["is_digit"]:
                lemmatized.append(text)
            # Skip punctuation
            elif token_info["is_punct"]:
                continue
            # Use lemma for other words
            elif token_info["is_alpha"] and len(lemma) >= self.min_token_length:
                lemmatized.append(lemma)
            elif len(text) >= self.min_token_length:
                lemmatized.append(text)

        return lemmatized

    def _filter_stopwords(
        self, lemmatized_tokens: list[str], doc
    ) -> tuple[list[str], list[str]]:
        """Filter stop words while preserving important terms."""
        filtered_tokens = []
        removed_stopwords = []

        # Get spaCy stop words
        spacy_stopwords = self.spacy_analyzer.nlp.Defaults.stop_words
        all_stopwords = spacy_stopwords.union(self.custom_stopwords)

        for token in lemmatized_tokens:
            # Always preserve technical terms
            if token in self.preserve_terms:
                filtered_tokens.append(token)
            # Filter stop words
            elif token in all_stopwords:
                removed_stopwords.append(token)
            # Keep other tokens
            else:
                filtered_tokens.append(token)

        return filtered_tokens, removed_stopwords

    def _normalize_tokens(self, filtered_tokens: list[str]) -> list[str]:
        """Normalize tokens for consistent matching."""
        normalized = []

        for token in filtered_tokens:
            # Convert to lowercase
            normalized_token = token.lower()

            # Remove very short or very long tokens
            if (
                self.min_token_length <= len(normalized_token) <= self.max_token_length
                and normalized_token.isalpha()
            ):
                normalized.append(normalized_token)

        return normalized

    def _rebuild_structured_query(self, normalized_tokens: list[str], doc) -> str:
        """Rebuild query preserving some structure for phrase queries."""
        # For now, just join tokens with spaces
        # Future enhancement: preserve quoted phrases, operators, etc.
        return " ".join(normalized_tokens)

    def preprocess_for_search(
        self, query: str, search_type: str = "hybrid"
    ) -> dict[str, Any]:
        """Preprocess query specifically for search operations.

        Args:
            query: The original query
            search_type: Type of search ("vector", "keyword", "hybrid")

        Returns:
            Dictionary with preprocessed variants for different search types
        """
        try:
            # Standard preprocessing
            standard_result = self.preprocess_query(query, preserve_structure=False)

            # Structured preprocessing (preserves more structure)
            structured_result = self.preprocess_query(query, preserve_structure=True)

            return {
                "original_query": query,
                "standard_preprocessed": standard_result.preprocessed_query,
                "structured_preprocessed": structured_result.preprocessed_query,
                "semantic_keywords": standard_result.normalized_tokens,
                "search_variants": {
                    "vector_search": structured_result.preprocessed_query,  # Preserve structure for vector
                    "keyword_search": standard_result.preprocessed_query,  # Normalize for BM25
                    "hybrid_search": standard_result.preprocessed_query,  # Default to normalized
                },
                "preprocessing_metadata": {
                    "removed_stopwords_count": len(standard_result.removed_stopwords),
                    "processing_time_ms": standard_result.processing_time_ms,
                    "processing_steps": standard_result.processing_steps,
                },
            }

        except Exception as e:
            logger.warning(f"Search preprocessing failed: {e}")
            return {
                "original_query": query,
                "standard_preprocessed": query,
                "structured_preprocessed": query,
                "semantic_keywords": query.lower().split(),
                "search_variants": {
                    "vector_search": query,
                    "keyword_search": query,
                    "hybrid_search": query,
                },
                "preprocessing_metadata": {
                    "removed_stopwords_count": 0,
                    "processing_time_ms": 0,
                    "processing_steps": ["error"],
                },
            }

    def clear_cache(self):
        """Clear preprocessing cache."""
        self._preprocessing_cache.clear()
        logger.debug("Cleared linguistic preprocessing cache")

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        return {
            "preprocessing_cache_size": len(self._preprocessing_cache),
        }
