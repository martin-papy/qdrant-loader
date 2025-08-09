"""Semantic analysis module for text processing."""

import logging
from dataclasses import dataclass
from typing import Any

import spacy
from gensim import corpora
from gensim.models import LdaModel
from gensim.parsing.preprocessing import preprocess_string
from spacy.cli.download import download as spacy_download
from spacy.tokens import Doc

logger = logging.getLogger(__name__)


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

        # Cache for processed documents
        self._doc_cache = {}

    def analyze_text(
        self, text: str, doc_id: str | None = None
    ) -> SemanticAnalysisResult:
        """Perform comprehensive semantic analysis on text.

        Args:
            text: Text to analyze
            doc_id: Optional document ID for caching

        Returns:
            SemanticAnalysisResult containing all analysis results
        """
        # Check cache
        if doc_id and doc_id in self._doc_cache:
            return self._doc_cache[doc_id]

        # Process with spaCy
        doc = self.nlp(text)

        # Extract entities with linking
        entities = self._extract_entities(doc)

        # Get part-of-speech tags
        pos_tags = self._get_pos_tags(doc)

        # Get dependency parse
        dependencies = self._get_dependencies(doc)

        # Extract topics
        topics = self._extract_topics(text)

        # Extract key phrases
        key_phrases = self._extract_key_phrases(doc)

        # Calculate document similarity
        doc_similarity = self._calculate_document_similarity(text)

        # Create result
        result = SemanticAnalysisResult(
            entities=entities,
            pos_tags=pos_tags,
            dependencies=dependencies,
            topics=topics,
            key_phrases=key_phrases,
            document_similarity=doc_similarity,
        )

        # Cache result
        if doc_id:
            self._doc_cache[doc_id] = result

        return result

    def _extract_entities(self, doc: Doc) -> list[dict[str, Any]]:
        """Extract named entities with linking.

        Args:
            doc: spaCy document

        Returns:
            List of entity dictionaries with linking information
        """
        entities = []
        for ent in doc.ents:
            # Get entity context
            start_sent = ent.sent.start
            end_sent = ent.sent.end
            context = doc[start_sent:end_sent].text

            # Get entity description
            description = self.nlp.vocab.strings[ent.label_]

            # Get related entities
            related = []
            for token in ent.sent:
                if token.ent_type_ and token.text != ent.text:
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
        """Get part-of-speech tags with detailed information.

        Args:
            doc: spaCy document

        Returns:
            List of POS tag dictionaries
        """
        pos_tags = []
        for token in doc:
            pos_tags.append(
                {
                    "text": token.text,
                    "pos": token.pos_,
                    "tag": token.tag_,
                    "lemma": token.lemma_,
                    "is_stop": token.is_stop,
                    "is_punct": token.is_punct,
                    "is_space": token.is_space,
                }
            )
        return pos_tags

    def _get_dependencies(self, doc: Doc) -> list[dict[str, Any]]:
        """Get dependency parse information.

        Args:
            doc: spaCy document

        Returns:
            List of dependency dictionaries
        """
        dependencies = []
        for token in doc:
            dependencies.append(
                {
                    "text": token.text,
                    "dep": token.dep_,
                    "head": token.head.text,
                    "head_pos": token.head.pos_,
                    "children": [child.text for child in token.children],
                }
            )
        return dependencies

    def _extract_topics(self, text: str) -> list[dict[str, Any]]:
        """Extract topics using LDA.

        Args:
            text: Text to analyze

        Returns:
            List of topic dictionaries
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

            # If we have existing models, use and update them
            if self.dictionary is not None and self.lda_model is not None:
                # Add new documents to existing dictionary
                self.dictionary.add_documents([processed_text])

                # Create corpus for the new text
                corpus = [self.dictionary.doc2bow(processed_text)]

                # Update existing LDA model
                self.lda_model.update(corpus)

                # Use the updated model for topic extraction
                current_lda_model = self.lda_model
            else:
                # Create fresh models for first use or when models aren't available
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

    def _calculate_document_similarity(self, text: str) -> dict[str, float]:
        """Calculate similarity with other processed documents.

        Args:
            text: Text to compare

        Returns:
            Dictionary of document similarities
        """
        similarities = {}
        doc = self.nlp(text)

        # Check if the model has word vectors
        has_vectors = self.nlp.vocab.vectors_length > 0

        for doc_id, cached_result in self._doc_cache.items():
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

            similarities[doc_id] = float(similarity)

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
        self._doc_cache.clear()

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
