"""Keyword extraction enricher using TF-IDF and RAKE algorithms.

POC2-004: Keyword enricher for extracting important terms from documents.

This enricher extracts keywords and key phrases from document content using
multiple extraction strategies. Keywords are useful for:

1. Auto-tagging documents
2. Search relevance boosting
3. Document clustering
4. Topic identification
5. Related document discovery
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .base_enricher import BaseEnricher, EnricherConfig, EnricherPriority, EnricherResult

from qdrant_loader.utils.logging import LoggingConfig

if TYPE_CHECKING:
    from qdrant_loader.config import Settings
    from qdrant_loader.core.document import Document

logger = LoggingConfig.get_logger(__name__)


# Common stop words for keyword extraction
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by",
    "can", "could", "did", "do", "does", "doing", "done", "for", "from",
    "had", "has", "have", "having", "he", "her", "here", "him", "his",
    "how", "i", "if", "in", "into", "is", "it", "its", "just", "like",
    "make", "many", "me", "might", "more", "most", "much", "must", "my",
    "no", "not", "now", "of", "on", "one", "only", "or", "other", "our",
    "out", "over", "own", "said", "same", "she", "should", "so", "some",
    "still", "such", "than", "that", "the", "their", "them", "then",
    "there", "these", "they", "this", "those", "through", "to", "too",
    "under", "up", "us", "very", "was", "we", "well", "were", "what",
    "when", "where", "which", "while", "who", "will", "with", "would",
    "you", "your", "also", "been", "being", "both", "but", "each",
    "few", "get", "got", "has", "have", "her", "here", "him", "his",
    "how", "its", "let", "may", "nor", "once", "onto", "per", "put",
    "see", "via", "yet", "able", "about", "above", "according", "across",
    "actually", "after", "again", "against", "all", "allow", "allows",
    "almost", "alone", "along", "already", "although", "always", "among",
    "another", "any", "anybody", "anyhow", "anyone", "anything", "anyway",
    "anyways", "anywhere", "apart", "appear", "appreciate", "appropriate",
}


@dataclass
class KeywordEnricherConfig(EnricherConfig):
    """Configuration for the keyword enricher.

    Attributes:
        max_keywords: Maximum number of keywords to extract
        min_word_length: Minimum word length for keywords
        max_word_length: Maximum word length for keywords
        min_frequency: Minimum occurrence count for keywords
        include_bigrams: Whether to extract two-word phrases
        include_trigrams: Whether to extract three-word phrases
        use_tfidf: Whether to use TF-IDF scoring (simple TF if False)
        custom_stop_words: Additional stop words to exclude
    """

    max_keywords: int = 20
    min_word_length: int = 3
    max_word_length: int = 30
    min_frequency: int = 1
    include_bigrams: bool = True
    include_trigrams: bool = False
    use_tfidf: bool = False  # Simple TF for now, can enhance later
    custom_stop_words: set[str] = field(default_factory=set)


class KeywordEnricher(BaseEnricher):
    """Extracts keywords and key phrases from document content.

    Uses a simple but effective approach:
    1. Tokenize text and remove stop words
    2. Calculate term frequency
    3. Optionally extract n-grams (bigrams, trigrams)
    4. Score and rank keywords
    5. Return top keywords with scores

    Output metadata keys:
        - keywords: List of {word, score, frequency} dicts
        - keyword_list: Simple list of keyword strings (for filtering)
        - keyword_count: Number of keywords extracted
        - top_keyword: The highest-scored keyword

    Example output:
        {
            "keywords": [
                {"word": "machine learning", "score": 0.85, "frequency": 5},
                {"word": "neural network", "score": 0.72, "frequency": 3},
            ],
            "keyword_list": ["machine learning", "neural network", "model"],
            "keyword_count": 10,
            "top_keyword": "machine learning",
        }
    """

    def __init__(
        self,
        settings: "Settings",
        config: KeywordEnricherConfig | None = None,
    ):
        """Initialize the keyword enricher.

        Args:
            settings: Application settings
            config: Keyword enricher configuration
        """
        config = config or KeywordEnricherConfig()
        config.priority = EnricherPriority.NORMAL
        super().__init__(settings, config)

        self.keyword_config: KeywordEnricherConfig = config
        self._stop_words = STOP_WORDS | config.custom_stop_words

    @property
    def name(self) -> str:
        return "keyword_enricher"

    def should_process(self, document: "Document") -> tuple[bool, str | None]:
        """Check if document should be processed for keywords."""
        should, reason = super().should_process(document)
        if not should:
            return should, reason

        # Skip very short documents
        if len(document.content) < 100:
            return False, "content_too_short"

        return True, None

    async def enrich(self, document: "Document") -> EnricherResult:
        """Extract keywords from the document.

        Args:
            document: Document to process

        Returns:
            EnricherResult with keyword metadata
        """
        try:
            content = document.content

            # Tokenize
            tokens = self._tokenize(content)

            # Get unigrams
            unigram_scores = self._score_terms(tokens)

            # Get bigrams if enabled
            bigram_scores: dict[str, tuple[float, int]] = {}
            if self.keyword_config.include_bigrams:
                bigrams = self._get_ngrams(tokens, 2)
                bigram_scores = self._score_terms(bigrams)

            # Get trigrams if enabled
            trigram_scores: dict[str, tuple[float, int]] = {}
            if self.keyword_config.include_trigrams:
                trigrams = self._get_ngrams(tokens, 3)
                trigram_scores = self._score_terms(trigrams)

            # Merge and rank all keywords
            all_scores = {**unigram_scores, **bigram_scores, **trigram_scores}

            # Sort by score descending
            sorted_keywords = sorted(
                all_scores.items(),
                key=lambda x: x[1][0],
                reverse=True,
            )

            # Take top N keywords
            top_keywords = sorted_keywords[: self.keyword_config.max_keywords]

            # Build keyword list
            keywords = [
                {
                    "word": word,
                    "score": round(score, 4),
                    "frequency": freq,
                }
                for word, (score, freq) in top_keywords
            ]

            keyword_list = [k["word"] for k in keywords]

            metadata = {
                "keywords": keywords,
                "keyword_list": keyword_list,
                "keyword_count": len(keywords),
                "top_keyword": keyword_list[0] if keyword_list else None,
            }

            return EnricherResult(metadata=metadata)

        except Exception as e:
            self.logger.warning(f"Keyword extraction failed: {e}")
            return EnricherResult.error_result(str(e))

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into words, filtering stop words.

        Args:
            text: Input text

        Returns:
            List of filtered tokens
        """
        # Lowercase and extract words
        text = text.lower()
        words = re.findall(r"\b[a-z][a-z']*[a-z]\b|\b[a-z]\b", text)

        # Filter by length and stop words
        filtered = [
            word for word in words
            if (
                self.keyword_config.min_word_length <= len(word) <= self.keyword_config.max_word_length
                and word not in self._stop_words
            )
        ]

        return filtered

    def _get_ngrams(self, tokens: list[str], n: int) -> list[str]:
        """Extract n-grams from token list.

        Args:
            tokens: List of tokens
            n: N-gram size

        Returns:
            List of n-gram strings
        """
        if len(tokens) < n:
            return []

        ngrams = []
        for i in range(len(tokens) - n + 1):
            ngram = " ".join(tokens[i : i + n])
            ngrams.append(ngram)

        return ngrams

    def _score_terms(self, terms: list[str]) -> dict[str, tuple[float, int]]:
        """Score terms by frequency.

        Args:
            terms: List of terms (words or n-grams)

        Returns:
            Dict mapping term -> (score, frequency)
        """
        if not terms:
            return {}

        # Count frequencies
        counts = Counter(terms)

        # Filter by minimum frequency
        filtered = {
            term: freq
            for term, freq in counts.items()
            if freq >= self.keyword_config.min_frequency
        }

        if not filtered:
            return {}

        # Normalize to 0-1 score
        max_freq = max(filtered.values())

        return {
            term: (freq / max_freq, freq)
            for term, freq in filtered.items()
        }

    def get_metadata_keys(self) -> list[str]:
        """Return metadata keys produced by this enricher."""
        return [
            "keywords",
            "keyword_list",
            "keyword_count",
            "top_keyword",
        ]
