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
        spacy_model: str = "en_core_web_sm",
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
        # Preprocess text
        processed_text = preprocess_string(text)

        # Create or update dictionary
        if self.dictionary is None:
            self.dictionary = corpora.Dictionary([processed_text])
        else:
            self.dictionary.add_documents([processed_text])

        # Create corpus
        corpus = [self.dictionary.doc2bow(processed_text)]

        # Train or update LDA model
        if self.lda_model is None:
            self.lda_model = LdaModel(
                corpus,
                num_topics=self.num_topics,
                passes=self.passes,
                id2word=self.dictionary,
            )
        else:
            self.lda_model.update(corpus)

        # Get topics
        topics = []
        for topic_id, topic in self.lda_model.print_topics():
            # Parse topic terms
            terms = []
            for term in topic.split("+"):
                weight, word = term.strip().split("*")
                terms.append({"term": word.strip('"'), "weight": float(weight)})

            topics.append(
                {
                    "id": topic_id,
                    "terms": terms,
                    "coherence": self._calculate_topic_coherence(terms),
                }
            )

        return topics

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

        for doc_id, cached_result in self._doc_cache.items():
            cached_doc = self.nlp(cached_result.entities[0]["context"])
            similarity = doc.similarity(cached_doc)
            similarities[doc_id] = float(similarity)

        return similarities

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
        """Clear the document cache."""
        self._doc_cache.clear()
