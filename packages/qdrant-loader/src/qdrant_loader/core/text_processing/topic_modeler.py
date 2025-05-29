"""Topic modeling module for document analysis."""

from typing import Any

import spacy
from gensim import corpora, models
from spacy.cli.download import download

from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class TopicModeler:
    """Handles batched LDA topic modeling for document analysis."""

    def __init__(self, num_topics: int = 3, passes: int = 10):
        """Initialize the topic modeler.

        Args:
            num_topics: Number of topics to extract
            passes: Number of passes for LDA training
        """
        self.num_topics = num_topics
        self.passes = passes
        self.dictionary = None
        self.lda_model = None
        self._cached_topics = {}  # Cache for topic inference results
        self._processed_texts = set()  # Track processed texts

        # Initialize spaCy for text preprocessing
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.info("Downloading spaCy model...")
            download("en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")

    def _preprocess_text(self, text: str) -> list[str]:
        """Preprocess text for topic modeling.

        Args:
            text: Input text

        Returns:
            List of preprocessed tokens
        """
        # Check if text is too short for meaningful topic modeling
        if len(text.split()) < 5:
            return []

        doc = self.nlp(text)
        return [
            token.text.lower()
            for token in doc
            if not token.is_stop and not token.is_punct
        ]

    def train_model(self, texts: list[str]) -> None:
        """Train LDA model on a batch of texts.

        Args:
            texts: List of texts to train on
        """
        if not texts:
            logger.warning("No texts provided for training")
            return

        # Filter out short texts and already processed ones
        new_texts = [
            text
            for text in texts
            if text not in self._processed_texts and len(text.split()) >= 5
        ]
        if not new_texts:
            logger.info("No new texts to process")
            return

        # Preprocess all texts
        processed_texts = [self._preprocess_text(text) for text in new_texts]
        processed_texts = [
            text for text in processed_texts if text
        ]  # Remove empty texts

        if not processed_texts:
            logger.warning("No valid texts after preprocessing")
            return

        # Create or update dictionary
        if self.dictionary is None:
            self.dictionary = corpora.Dictionary(processed_texts)
        else:
            self.dictionary.add_documents(processed_texts)

        # Create document-term matrix
        corpus = [self.dictionary.doc2bow(text) for text in processed_texts]

        # Train LDA model with optimized settings
        if self.lda_model is None:
            self.lda_model = models.LdaModel(
                corpus,
                num_topics=self.num_topics,
                id2word=self.dictionary,
                passes=self.passes,
                chunksize=2000,
                update_every=1,
                alpha="auto",
                eta="auto",
                decay=0.5,
                offset=1.0,
                eval_every=10,
                iterations=50,
                gamma_threshold=0.001,
                minimum_probability=0.01,
            )
        else:
            # Update existing model
            self.lda_model.update(corpus)

        # Update processed texts set
        self._processed_texts.update(new_texts)

        # Clear cache when model is updated
        self._cached_topics.clear()

        logger.info(
            "Trained/Updated LDA model",
            num_documents=len(new_texts),
            num_topics=self.num_topics,
            dictionary_size=len(self.dictionary),
        )

    def infer_topics(self, text: str) -> dict[str, Any]:
        """Infer topics for a single text using the trained model.

        Args:
            text: Text to analyze

        Returns:
            Dictionary containing topic analysis results
        """
        if not self.lda_model or not self.dictionary:
            logger.warning("LDA model not trained")
            return {"topics": [], "coherence": 0.0}

        # Check cache first
        if text in self._cached_topics:
            return self._cached_topics[text]

        try:
            # Preprocess text
            tokens = self._preprocess_text(text)
            if not tokens:
                logger.debug("No tokens found for topic analysis")
                return {"topics": [], "coherence": 0.0}

            # Create document-term matrix
            doc_bow = self.dictionary.doc2bow(tokens)

            # Get topic distribution for this document
            doc_topics = self.lda_model[doc_bow]

            # Get topics without coherence calculation for speed
            topics = self.lda_model.print_topics(num_words=5)

            # Calculate topic coherence only for longer texts
            coherence = 0.0
            if len(tokens) > 20:  # Increased threshold for coherence calculation
                try:
                    coherence_model = models.CoherenceModel(
                        model=self.lda_model,
                        texts=[tokens],
                        dictionary=self.dictionary,
                        coherence="c_v",
                        processes=1,  # Use single process for stability
                    )
                    coherence = coherence_model.get_coherence()
                except Exception as e:
                    logger.warning("Failed to calculate coherence", error=str(e))

            result = {
                "topics": topics,
                "doc_topics": doc_topics,
                "coherence": coherence,
            }

            # Cache the result
            self._cached_topics[text] = result

            return result

        except Exception as e:
            logger.error(
                "Error in topic inference",
                error=str(e),
                error_type=type(e).__name__,
                text_length=len(text),
            )
            return {"topics": [], "coherence": 0.0}
