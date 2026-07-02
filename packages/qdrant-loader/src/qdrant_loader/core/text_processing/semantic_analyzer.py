"""Semantic analysis module for text processing."""

import hashlib
import logging
import threading
from dataclasses import dataclass
from typing import Any

import spacy
from gensim import corpora
from gensim.models import LdaModel
from gensim.parsing.preprocessing import preprocess_string
from spacy.cli.download import download as spacy_download
from spacy.tokens import Doc

logger = logging.getLogger(__name__)


def is_meaningful_text(text: str) -> bool:
    """Check if text contains meaningful content (letters or digits).

    Returns False for text that only contains:
    - Punctuation marks: ., #, @, |, -, _, etc.
    - Whitespace characters
    - Special symbols without semantic meaning (---, ..., |||, etc.)

    """
    # Check if text contains at least one alphanumeric character
    return any(c.isalnum() for c in text)


@dataclass
class SemanticAnalysisResult:
    """Container for semantic analysis results."""

    entities: list[dict[str, Any]]
    pos_tags: list[dict[str, Any]]
    dependencies: list[dict[str, Any]]
    topics: list[dict[str, Any]]
    key_phrases: list[str]
    document_similarity: dict[str, float]


class SemanticAnalyzer:
    """Advanced semantic analysis for text processing."""

    def __init__(
        self,
        spacy_model: str = "en_core_web_md",
        num_topics: int = 5,
        passes: int = 10,
        min_topic_freq: int = 2,
    ):
        """Initialize the semantic analyzer.

        Args:
            spacy_model: Name of the spaCy model to use
            num_topics: Number of topics for LDA
            passes: Number of passes for LDA training
            min_topic_freq: Minimum frequency for topic terms
        """
        self.logger = logging.getLogger(__name__)

        # Initialize spaCy
        try:
            self.nlp = spacy.load(spacy_model)
        except OSError:
            self.logger.info(f"Downloading spaCy model {spacy_model}...")
            spacy_download(spacy_model)
            self.nlp = spacy.load(spacy_model)

        # Initialize LDA parameters
        self.num_topics = num_topics
        self.passes = passes
        self.min_topic_freq = min_topic_freq

        # Initialize LDA model
        self.lda_model = None
        self.dictionary = None

        # Front-loaded (per-document) topic model: trained once over all of a
        # document's chunks via fit_topic_model(), then inferred per chunk. Until it
        # is fitted, _extract_topics falls back to the legacy single-chunk path.
        self._topic_model_fitted = False
        # A corpus smaller than this trains a degenerate model, so we skip fitting
        # and let those chunks use the per-chunk fallback instead.
        self._min_topic_corpus_docs = 3
        # How many of a chunk's most-probable topics to surface, and how many terms
        # per topic — matched to the legacy producer's output shape.
        self._topics_per_chunk = 3
        self._topic_top_n = 10

        # Cache for processed documents
        self._doc_cache: dict = {}
        self._doc_cache_lock = threading.Lock()

    def _build_cache_key(
        self, text: str, doc_id: str | None, include_enhanced: bool
    ) -> tuple[str, bool, str] | None:
        """Build a cache key that includes a content fingerprint.

        Including a fingerprint prevents stale cache hits when the same doc_id
        is reused with different content.
        """
        if not doc_id:
            return None

        text_fingerprint = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return (doc_id, include_enhanced, text_fingerprint)

    def analyze_text(
        self,
        text: str,
        doc_id: str | None = None,
        include_enhanced: bool = False,
    ) -> SemanticAnalysisResult:
        """Perform comprehensive semantic analysis on text.

        Args:
            text: Text to analyze
            doc_id: Optional document ID for caching
            include_enhanced: Whether to compute enhanced NLP fields
                (pos_tags, dependencies, document_similarity)

        Returns:
            SemanticAnalysisResult containing all analysis results
        """
        # Check cache
        cache_key = self._build_cache_key(text, doc_id, include_enhanced)

        # Protected read
        with self._doc_cache_lock:
            cached = self._doc_cache.get(cache_key) if cache_key else None

        if cached is not None:
            if include_enhanced:
                # Compute similarity OUTSIDE the lock (can be slow)
                doc_similarity = self._calculate_document_similarity(
                    text, doc_id=doc_id
                )
                refreshed = SemanticAnalysisResult(
                    entities=cached.entities,
                    pos_tags=cached.pos_tags,
                    dependencies=cached.dependencies,
                    topics=cached.topics,
                    key_phrases=cached.key_phrases,
                    document_similarity=doc_similarity,
                )
                # Protected write-back
                with self._doc_cache_lock:
                    self._doc_cache[cache_key] = refreshed
                return refreshed
            return cached

        # Process with spaCy
        doc = self.nlp(text)

        # Extract entities with linking
        entities = self._extract_entities(doc)

        if include_enhanced:
            # Get part-of-speech tags
            pos_tags = self._get_pos_tags(doc)

            # Get dependency parse
            dependencies = self._get_dependencies(doc)
        else:
            pos_tags = []
            dependencies = []

        # Extract topics
        topics = self._extract_topics(text)

        # Extract key phrases
        key_phrases = self._extract_key_phrases(doc)

        # Calculate document similarity
        doc_similarity = (
            self._calculate_document_similarity(text, doc_id=doc_id)
            if include_enhanced
            else {}
        )

        # Create result
        result = SemanticAnalysisResult(
            entities=entities,
            pos_tags=pos_tags,
            dependencies=dependencies,
            topics=topics,
            key_phrases=key_phrases,
            document_similarity=doc_similarity,
        )

        # Protected write
        if cache_key:
            with self._doc_cache_lock:
                self._doc_cache[cache_key] = result

        return result

    def _extract_entities(self, doc: Doc) -> list[dict[str, Any]]:
        """Extract named entities with linking, filtering garbage entities.

        Filters out entities that:
        - Only contain punctuation/symbols (., #, |, etc.)
        - Don't have any alphanumeric characters
        - Are just whitespace

        Args:
            doc: spaCy document

        Returns:
            List of entity dictionaries with linking information
        """
        entities = []
        for ent in doc.ents:
            # Filter entities that only contain punctuation/symbols
            if not is_meaningful_text(ent.text):
                continue

            # Get entity context
            start_sent = ent.sent.start
            end_sent = ent.sent.end
            context = doc[start_sent:end_sent].text

            # Get entity description
            description = self.nlp.vocab.strings[ent.label_]

            # Get related entities (also filter meaningless ones)
            related = []
            for token in ent.sent:
                if token.ent_type_ and token.text != ent.text:
                    # Only add related entities with meaningful text
                    if is_meaningful_text(token.text):
                        related.append(
                            {
                                "text": token.text,
                                "type": token.ent_type_,
                                "relation": token.dep_,
                            }
                        )

            entities.append(
                {
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "description": description,
                    "context": context,
                    "related_entities": related,
                }
            )

        return entities

    def _get_pos_tags(self, doc: Doc) -> list[dict[str, Any]]:
        """Get part-of-speech tags with detailed information, filtering noise tokens.

        Filters out multiple types of noise:
        - Whitespace tokens (is_space=True)
        - Punctuation tokens (is_punct=True)
        - Symbol-only tokens without alphanumeric content (e.g., ---, ..., |||)

        This is especially important for Excel tables and structured data.

        Args:
            doc: spaCy document

        Returns:
            List of POS tag dictionaries (excluding spaces, punctuation, and symbols)
        """
        pos_tags = []
        for token in doc:
            # Skip whitespace and punctuation - they pollute metadata
            if token.is_space or token.is_punct:
                continue

            # Also skip tokens with no meaningful content (e.g., ---, ...)
            # This catches edge cases where spaCy doesn't mark as punct
            if not is_meaningful_text(token.text):
                continue

            pos_tags.append(
                {
                    "text": token.text,
                    "pos": token.pos_,
                    "tag": token.tag_,
                    "lemma": token.lemma_,
                    "is_stop": token.is_stop,
                }
            )
        return pos_tags

    def _get_dependencies(self, doc: Doc) -> list[dict[str, Any]]:
        """Get dependency parse information with filtering.

        Filters out:
        - Whitespace tokens (is_space=True)
        - Punctuation tokens (is_punct=True)
        - Symbol-only tokens without alphanumeric content
        - Children that are punctuation or meaningless symbols

        Args:
            doc: spaCy document

        Returns:
            List of dependency dictionaries (excluding noise tokens)
        """
        dependencies = []
        for token in doc:
            # Skip whitespace and punctuation tokens
            if token.is_space or token.is_punct:
                continue

            # Skip tokens with no meaningful content (e.g., ---, ...)
            if not is_meaningful_text(token.text):
                continue

            # Filter children to only include meaningful tokens
            meaningful_children = [
                child.text
                for child in token.children
                if not child.is_space
                and not child.is_punct
                and is_meaningful_text(child.text)
            ]

            dependencies.append(
                {
                    "text": token.text,
                    "dep": token.dep_,
                    "head": token.head.text,
                    "head_pos": token.head.pos_,
                    "children": meaningful_children,
                }
            )
        return dependencies

    def fit_topic_model(self, texts: list[str]) -> None:
        """Train one document-level LDA over all of a document's chunk texts.

        Front-loading the model once lets :meth:`_extract_topics` *infer* each
        chunk's topics against a shared corpus model, instead of training a
        degenerate single-document LDA per chunk. When the corpus is too small to be
        meaningful the model is left unfitted, so those chunks fall back to the
        legacy per-chunk path.

        Args:
            texts: The contents of every chunk produced for one document.
        """
        try:
            processed = [preprocess_string(text) for text in texts]
            processed = [tokens for tokens in processed if len(tokens) >= 5]

            if len(processed) < self._min_topic_corpus_docs:
                self.logger.debug(
                    "Corpus too small to fit a document-level topic model "
                    f"({len(processed)} usable chunks); using per-chunk fallback"
                )
                self.dictionary = None
                self.lda_model = None
                self._topic_model_fitted = False
                return

            dictionary = corpora.Dictionary(processed)
            corpus = [dictionary.doc2bow(tokens) for tokens in processed]
            self.dictionary = dictionary
            self.lda_model = LdaModel(
                corpus,
                num_topics=min(self.num_topics, len(processed)),
                passes=self.passes,
                id2word=dictionary,
                random_state=42,  # For reproducibility
                alpha=0.1,  # Fixed positive value for document-topic density
                eta=0.01,  # Fixed positive value for topic-word density
            )
            self._topic_model_fitted = True
        except Exception as e:
            self.logger.warning(
                f"Topic model fit failed; using per-chunk fallback: {e}",
                exc_info=True,
            )
            self.dictionary = None
            self.lda_model = None
            self._topic_model_fitted = False

    def _extract_topics(self, text: str) -> list[dict[str, Any]]:
        """Extract topics for one chunk.

        Uses the front-loaded document-level model when one has been fitted (see
        :meth:`fit_topic_model`), inferring the chunk's dominant topics against it
        without retraining. Otherwise falls back to the legacy per-chunk model.

        Args:
            text: Text to analyze

        Returns:
            List of topic dictionaries:
            ``{"id", "terms": [{"term", "weight"}], "coherence"}``.
        """
        try:
            # Preprocess text
            processed_text = preprocess_string(text)

            # Skip topic extraction for very short texts
            if len(processed_text) < 5:
                self.logger.debug("Text too short for topic extraction")
                return [
                    {
                        "id": 0,
                        "terms": [{"term": "general", "weight": 1.0}],
                        "coherence": 0.5,
                    }
                ]

            # A document-level model was front-loaded: infer this chunk's topics
            # against it, without retraining or mutating the shared model.
            if (
                self._topic_model_fitted
                and self.lda_model is not None
                and self.dictionary is not None
            ):
                return self._infer_chunk_topics(processed_text)

            # Unfitted (the markdown path, or a corpus too small to fit): legacy
            # per-chunk model. Degenerate by construction, but retained so behavior
            # for unfitted callers is unchanged.
            temp_dictionary = corpora.Dictionary([processed_text])
            corpus = [temp_dictionary.doc2bow(processed_text)]

            # Create a fresh LDA model for this specific text
            current_lda_model = LdaModel(
                corpus,
                num_topics=min(
                    self.num_topics, len(processed_text) // 2
                ),  # Ensure reasonable topic count
                passes=self.passes,
                id2word=temp_dictionary,
                random_state=42,  # For reproducibility
                alpha=0.1,  # Fixed positive value for document-topic density
                eta=0.01,  # Fixed positive value for topic-word density
            )

            # Get topics
            topics = []
            for topic_id, topic in current_lda_model.print_topics():
                # Parse topic terms
                terms = []
                for term in topic.split("+"):
                    try:
                        weight, word = term.strip().split("*")
                        terms.append({"term": word.strip('"'), "weight": float(weight)})
                    except ValueError:
                        # Skip malformed terms
                        continue

                topics.append(
                    {
                        "id": topic_id,
                        "terms": terms,
                        "coherence": self._calculate_topic_coherence(terms),
                    }
                )

            return (
                topics
                if topics
                else [
                    {
                        "id": 0,
                        "terms": [{"term": "general", "weight": 1.0}],
                        "coherence": 0.5,
                    }
                ]
            )

        except Exception as e:
            self.logger.warning(f"Topic extraction failed: {e}", exc_info=True)
            # Return fallback topic
            return [
                {
                    "id": 0,
                    "terms": [{"term": "general", "weight": 1.0}],
                    "coherence": 0.5,
                }
            ]

    def _infer_chunk_topics(self, processed_text: list[str]) -> list[dict[str, Any]]:
        """Infer a chunk's dominant topics against the front-loaded model.

        Args:
            processed_text: The chunk's preprocessed tokens.

        Returns:
            The chunk's most-probable topics, in the legacy producer's shape. An
            empty bag-of-words (all tokens out of the trained vocabulary) still
            yields the model's topics ranked by the prior distribution.
        """
        bow = self.dictionary.doc2bow(processed_text)
        distribution = self.lda_model.get_document_topics(bow, minimum_probability=0.0)
        ranked = sorted(distribution, key=lambda pair: pair[1], reverse=True)

        topics: list[dict[str, Any]] = []
        for topic_id, _probability in ranked[: self._topics_per_chunk]:
            terms = [
                {"term": word, "weight": float(weight)}
                for word, weight in self.lda_model.show_topic(
                    topic_id, topn=self._topic_top_n
                )
            ]
            topics.append(
                {
                    "id": int(topic_id),
                    "terms": terms,
                    "coherence": self._calculate_topic_coherence(terms),
                }
            )

        return (
            topics
            if topics
            else [
                {
                    "id": 0,
                    "terms": [{"term": "general", "weight": 1.0}],
                    "coherence": 0.5,
                }
            ]
        )

    def _extract_key_phrases(self, doc: Doc) -> list[str]:
        """Extract key phrases from text.

        Args:
            doc: spaCy document

        Returns:
            List of key phrases
        """
        key_phrases = []

        # Extract noun phrases
        for chunk in doc.noun_chunks:
            if len(chunk.text.split()) >= 2:  # Only multi-word phrases
                key_phrases.append(chunk.text)

        # Extract named entities
        for ent in doc.ents:
            if ent.label_ in ["ORG", "PRODUCT", "WORK_OF_ART", "LAW"]:
                key_phrases.append(ent.text)

        return list(set(key_phrases))  # Remove duplicates

    def _calculate_document_similarity(
        self, text: str, doc_id: str | None = None
    ) -> dict[str, float]:
        """Calculate similarity with other processed documents.

        Args:
            text: Text to compare
            doc_id: Optional current document ID to exclude from results

        Returns:
            Dictionary of document similarities
        """
        similarities = {}
        skipped_ids = {doc_id} if doc_id else set()

        doc = self.nlp(text)

        # Check if the model has word vectors
        has_vectors = self.nlp.vocab.vectors_length > 0

        with self._doc_cache_lock:
            cached_items = list(self._doc_cache.items())

        for cache_key, cached_result in cached_items:
            cached_doc_id = cache_key[0] if isinstance(cache_key, tuple) else cache_key
            if cached_doc_id is None or cached_doc_id in skipped_ids:
                continue

            # Check if cached_result has entities and the first entity has context
            if not cached_result.entities or not cached_result.entities[0].get(
                "context"
            ):
                continue

            cached_doc = self.nlp(cached_result.entities[0]["context"])

            if has_vectors:
                # Use spaCy's built-in similarity which uses word vectors
                similarity = doc.similarity(cached_doc)
            else:
                # Use alternative similarity calculation for models without word vectors
                # This avoids the spaCy warning about missing word vectors
                similarity = self._calculate_alternative_similarity(doc, cached_doc)

            similarities[cached_doc_id] = float(similarity)
            skipped_ids.add(cached_doc_id)

        return similarities

    def _calculate_alternative_similarity(self, doc1: Doc, doc2: Doc) -> float:
        """Calculate similarity for models without word vectors.

        Uses token overlap and shared entities as similarity metrics.

        Args:
            doc1: First document
            doc2: Second document

        Returns:
            Similarity score between 0 and 1
        """
        # Extract lemmatized tokens (excluding stop words and punctuation)
        tokens1 = {
            token.lemma_.lower()
            for token in doc1
            if not token.is_stop and not token.is_punct and token.is_alpha
        }
        tokens2 = {
            token.lemma_.lower()
            for token in doc2
            if not token.is_stop and not token.is_punct and token.is_alpha
        }

        # Calculate token overlap (Jaccard similarity)
        if not tokens1 and not tokens2:
            return 1.0  # Both empty
        if not tokens1 or not tokens2:
            return 0.0  # One empty

        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        token_similarity = intersection / union if union > 0 else 0.0

        # Extract named entities
        entities1 = {ent.text.lower() for ent in doc1.ents}
        entities2 = {ent.text.lower() for ent in doc2.ents}

        # Calculate entity overlap
        entity_similarity = 0.0
        if entities1 or entities2:
            entity_intersection = len(entities1.intersection(entities2))
            entity_union = len(entities1.union(entities2))
            entity_similarity = (
                entity_intersection / entity_union if entity_union > 0 else 0.0
            )

        # Combine token and entity similarities (weighted average)
        # Token similarity gets more weight as it's more comprehensive
        combined_similarity = 0.7 * token_similarity + 0.3 * entity_similarity

        return combined_similarity

    def _calculate_topic_coherence(self, terms: list[dict[str, Any]]) -> float:
        """Calculate topic coherence score.

        Args:
            terms: List of topic terms with weights

        Returns:
            Coherence score between 0 and 1
        """
        # Simple coherence based on term weights
        weights = [term["weight"] for term in terms]
        return sum(weights) / len(weights) if weights else 0.0

    def clear_cache(self):
        """Clear the document cache and release all resources."""
        # Clear document cache
        with self._doc_cache_lock:
            self._doc_cache.clear()

        # A released model is no longer fitted; reset so reuse doesn't infer
        # against a torn-down model.
        self._topic_model_fitted = False

        # Release LDA model resources
        if hasattr(self, "lda_model") and self.lda_model is not None:
            try:
                # Clear LDA model
                self.lda_model = None
            except Exception as e:
                logger.warning(f"Error releasing LDA model: {e}")

        # Release dictionary
        if hasattr(self, "dictionary") and self.dictionary is not None:
            try:
                self.dictionary = None
            except Exception as e:
                logger.warning(f"Error releasing dictionary: {e}")

        # Release spaCy model resources
        if hasattr(self, "nlp") and self.nlp is not None:
            try:
                # Clear spaCy caches and release memory
                if hasattr(self.nlp, "vocab") and hasattr(self.nlp.vocab, "strings"):
                    # Try different methods to clear spaCy caches
                    if hasattr(self.nlp.vocab.strings, "_map") and hasattr(
                        self.nlp.vocab.strings._map, "clear"
                    ):
                        self.nlp.vocab.strings._map.clear()
                    elif hasattr(self.nlp.vocab.strings, "clear"):
                        self.nlp.vocab.strings.clear()
                    # Additional cleanup for different spaCy versions
                    if hasattr(self.nlp.vocab, "_vectors") and hasattr(
                        self.nlp.vocab._vectors, "clear"
                    ):
                        self.nlp.vocab._vectors.clear()
                # Note: We don't set nlp to None as it might be needed for other operations
                # but we clear its internal caches
            except Exception as e:
                logger.debug(f"spaCy cache clearing skipped (version-specific): {e}")

        logger.debug("Semantic analyzer resources cleared")

    def shutdown(self):
        """Shutdown the semantic analyzer and release all resources.

        This method should be called when the analyzer is no longer needed
        to ensure proper cleanup of all resources.
        """
        self.clear_cache()

        # More aggressive cleanup for shutdown
        if hasattr(self, "nlp"):
            try:
                # Release the spaCy model completely
                del self.nlp
            except Exception as e:
                logger.warning(f"Error releasing spaCy model: {e}")

        logger.debug("Semantic analyzer shutdown completed")
