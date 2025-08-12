"""spaCy-powered query analysis for intelligent search."""

from dataclasses import dataclass
from typing import Any

import spacy
from spacy.cli.download import download as spacy_download
from spacy.tokens import Doc

from ...utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


@dataclass
class QueryAnalysis:
    """Container for spaCy-based query analysis results."""

    # Core linguistic analysis
    entities: list[tuple[str, str]]  # (text, label)
    pos_patterns: list[str]  # Part-of-speech tags
    semantic_keywords: list[str]  # Lemmatized, filtered keywords
    intent_signals: dict[str, Any]  # Intent detection based on linguistic patterns
    main_concepts: list[str]  # Noun chunks representing main concepts

    # Semantic understanding
    query_vector: Any  # spaCy Doc vector for similarity matching
    semantic_similarity_cache: dict[str, float]  # Cache for similarity scores

    # Query characteristics
    is_question: bool
    is_technical: bool
    complexity_score: float  # 0-1 score based on linguistic complexity

    # Processing metadata
    processed_tokens: int
    processing_time_ms: float


class SpaCyQueryAnalyzer:
    """Enhanced query analysis using spaCy NLP with en_core_web_md model."""

    def __init__(self, spacy_model: str = "en_core_web_md"):
        """Initialize the spaCy query analyzer.

        Args:
            spacy_model: spaCy model to use (default: en_core_web_md with 20k word vectors)
        """
        self.spacy_model = spacy_model
        self.nlp = self._load_spacy_model()
        self.logger = LoggingConfig.get_logger(__name__)

        # Intent pattern definitions using POS tags and linguistic features
        self.intent_patterns = {
            "technical_lookup": {
                "entities": {"ORG", "PRODUCT", "PERSON", "GPE"},
                "pos_sequences": [["NOUN", "NOUN"], ["ADJ", "NOUN"], ["VERB", "NOUN"]],
                "keywords": {
                    "api",
                    "database",
                    "architecture",
                    "implementation",
                    "system",
                    "code",
                    "function",
                },
                "question_words": set(),
            },
            "business_context": {
                "entities": {"ORG", "MONEY", "PERCENT", "CARDINAL"},
                "pos_sequences": [["NOUN", "NOUN"], ["ADJ", "NOUN", "NOUN"]],
                "keywords": {
                    "requirements",
                    "objectives",
                    "strategy",
                    "business",
                    "scope",
                    "goals",
                },
                "question_words": {"what", "why", "how"},
            },
            "vendor_evaluation": {
                "entities": {"ORG", "MONEY", "PERSON"},
                "pos_sequences": [["NOUN", "NOUN"], ["VERB", "NOUN"], ["ADJ", "NOUN"]],
                "keywords": {
                    "proposal",
                    "criteria",
                    "cost",
                    "vendor",
                    "comparison",
                    "evaluation",
                },
                "question_words": {"which", "what", "how much"},
            },
            "procedural": {
                "entities": set(),
                "pos_sequences": [["VERB", "NOUN"], ["VERB", "DET", "NOUN"]],
                "keywords": {
                    "how",
                    "steps",
                    "process",
                    "procedure",
                    "guide",
                    "tutorial",
                },
                "question_words": {"how", "when", "where"},
            },
            "informational": {
                "entities": set(),
                "pos_sequences": [["NOUN"], ["ADJ", "NOUN"]],
                "keywords": {"what", "definition", "meaning", "overview", "about"},
                "question_words": {"what", "who", "when", "where"},
            },
        }

        # Cache for processed queries to improve performance
        self._analysis_cache: dict[str, QueryAnalysis] = {}
        self._similarity_cache: dict[tuple[str, str], float] = {}

    def _load_spacy_model(self) -> spacy.Language:
        """Load spaCy model with error handling and auto-download."""
        try:
            nlp = spacy.load(self.spacy_model)
            # Verify model has vectors for semantic similarity
            if not nlp.meta.get("vectors", {}).get("vectors", 0):
                logger.warning(
                    f"spaCy model {self.spacy_model} loaded but has no word vectors. "
                    "Semantic similarity features will be limited."
                )
            else:
                logger.info(
                    f"spaCy model {self.spacy_model} loaded successfully with "
                    f"{nlp.meta['vectors']['vectors']} word vectors"
                )
            return nlp
        except OSError:
            logger.info(f"spaCy model {self.spacy_model} not found. Downloading...")
            try:
                spacy_download(self.spacy_model)
                nlp = spacy.load(self.spacy_model)
                logger.info(f"Successfully downloaded and loaded {self.spacy_model}")
                return nlp
            except Exception as e:
                logger.error(f"Failed to download spaCy model {self.spacy_model}: {e}")
                # Fallback to a basic model
                try:
                    logger.warning("Falling back to en_core_web_sm model")
                    spacy_download("en_core_web_sm")
                    return spacy.load("en_core_web_sm")
                except Exception as fallback_error:
                    logger.error(f"Failed to load fallback model: {fallback_error}")
                    raise RuntimeError(
                        f"Could not load any spaCy model. Please install {self.spacy_model} manually."
                    )

    def analyze_query_semantic(self, query: str) -> QueryAnalysis:
        """Enhanced query analysis using spaCy NLP.

        Args:
            query: The search query to analyze

        Returns:
            QueryAnalysis containing comprehensive linguistic analysis
        """
        import time

        start_time = time.time()

        # Check cache first
        if query in self._analysis_cache:
            cached = self._analysis_cache[query]
            logger.debug(f"Using cached analysis for query: {query[:50]}...")
            return cached

        # Process query with spaCy
        doc = self.nlp(query)

        # Extract entities with confidence
        entities = [(ent.text, ent.label_) for ent in doc.ents]

        # Get POS patterns
        pos_patterns = [token.pos_ for token in doc if not token.is_space]

        # Extract semantic keywords (lemmatized, filtered)
        semantic_keywords = [
            token.lemma_.lower()
            for token in doc
            if (
                token.is_alpha
                and not token.is_stop
                and not token.is_punct
                and len(token.text) > 2
            )
        ]

        # Extract main concepts (noun chunks)
        main_concepts = [
            chunk.text.strip()
            for chunk in doc.noun_chunks
            if len(chunk.text.strip()) > 2
        ]

        # Detect intent using linguistic patterns
        intent_signals = self._detect_intent_patterns(
            doc, entities, pos_patterns, semantic_keywords
        )

        # Query characteristics
        is_question = self._is_question(doc)
        is_technical = self._is_technical_query(doc, entities, semantic_keywords)
        complexity_score = self._calculate_complexity_score(doc)

        # Processing metadata
        processing_time_ms = (time.time() - start_time) * 1000

        # Create analysis result
        analysis = QueryAnalysis(
            entities=entities,
            pos_patterns=pos_patterns,
            semantic_keywords=semantic_keywords,
            intent_signals=intent_signals,
            main_concepts=main_concepts,
            query_vector=doc,  # Store the spaCy Doc for similarity calculations
            semantic_similarity_cache={},
            is_question=is_question,
            is_technical=is_technical,
            complexity_score=complexity_score,
            processed_tokens=len(doc),
            processing_time_ms=processing_time_ms,
        )

        # Cache the result
        self._analysis_cache[query] = analysis

        logger.debug(
            f"Analyzed query in {processing_time_ms:.2f}ms",
            query_length=len(query),
            entities_found=len(entities),
            keywords_extracted=len(semantic_keywords),
            intent=intent_signals.get("primary_intent", "unknown"),
        )

        return analysis

    def semantic_similarity_matching(
        self, query_analysis: QueryAnalysis, entity_text: str
    ) -> float:
        """Calculate semantic similarity using spaCy word vectors.

        Args:
            query_analysis: Analyzed query containing the query vector
            entity_text: Text to compare similarity with

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Check cache first
        cache_key = (str(query_analysis.query_vector), entity_text)
        if cache_key in self._similarity_cache:
            return self._similarity_cache[cache_key]

        try:
            # Process entity text
            entity_doc = self.nlp(entity_text)

            # Calculate similarity using spaCy vectors
            if query_analysis.query_vector.has_vector and entity_doc.has_vector:
                similarity = query_analysis.query_vector.similarity(entity_doc)
            else:
                # Fallback to token-based similarity if no vectors
                similarity = self._token_similarity_fallback(
                    query_analysis.semantic_keywords, entity_text.lower()
                )

            # Cache the result
            self._similarity_cache[cache_key] = similarity

            return similarity

        except Exception as e:
            logger.warning(f"Error calculating similarity for '{entity_text}': {e}")
            return 0.0

    def _detect_intent_patterns(
        self,
        doc: Doc,
        entities: list[tuple[str, str]],
        pos_patterns: list[str],
        semantic_keywords: list[str],
    ) -> dict[str, Any]:
        """Detect query intent using POS patterns and linguistic features."""
        intent_scores = {}

        # Convert entities and keywords to sets for faster lookup
        entity_labels = {label for _, label in entities}
        keyword_set = set(semantic_keywords)

        # Score each intent pattern
        for intent_name, pattern in self.intent_patterns.items():
            score = 0.0

            # Entity type matching
            entity_match = len(entity_labels.intersection(pattern["entities"])) / max(
                len(pattern["entities"]), 1
            )
            score += entity_match * 0.3

            # POS sequence matching
            pos_match = self._match_pos_sequences(
                pos_patterns, pattern["pos_sequences"]
            )
            score += pos_match * 0.3

            # Keyword matching
            keyword_match = len(keyword_set.intersection(pattern["keywords"])) / max(
                len(pattern["keywords"]), 1
            )
            score += keyword_match * 0.2

            # Question word matching
            question_match = self._match_question_words(doc, pattern["question_words"])
            score += question_match * 0.2

            intent_scores[intent_name] = score

        # Find primary intent
        primary_intent = (
            max(intent_scores, key=intent_scores.get) if intent_scores else "general"
        )
        primary_score = intent_scores.get(primary_intent, 0.0)

        # Only use intent if confidence is above threshold
        if primary_score < 0.3:
            primary_intent = "general"

        return {
            "primary_intent": primary_intent,
            "confidence": primary_score,
            "all_scores": intent_scores,
            "linguistic_features": {
                "has_entities": len(entities) > 0,
                "has_question_words": any(
                    token.text.lower() in {"what", "how", "why", "when", "who", "where"}
                    for token in doc
                ),
                "verb_count": sum(1 for pos in pos_patterns if pos in {"VERB", "AUX"}),
                "noun_count": sum(1 for pos in pos_patterns if pos == "NOUN"),
            },
        }

    def _match_pos_sequences(
        self, pos_patterns: list[str], target_sequences: list[list[str]]
    ) -> float:
        """Match POS tag sequences in the query."""
        if not target_sequences or not pos_patterns:
            return 0.0

        matches = 0
        total_sequences = len(target_sequences)

        for sequence in target_sequences:
            if self._contains_sequence(pos_patterns, sequence):
                matches += 1

        return matches / total_sequences

    def _contains_sequence(self, pos_patterns: list[str], sequence: list[str]) -> bool:
        """Check if POS patterns contain a specific sequence."""
        if len(sequence) > len(pos_patterns):
            return False

        for i in range(len(pos_patterns) - len(sequence) + 1):
            if pos_patterns[i : i + len(sequence)] == sequence:
                return True

        return False

    def _match_question_words(self, doc: Doc, question_words: set[str]) -> float:
        """Match question words in the query."""
        if not question_words:
            return 0.0

        found_words = {
            token.text.lower() for token in doc if token.text.lower() in question_words
        }
        return len(found_words) / len(question_words)

    def _is_question(self, doc: Doc) -> bool:
        """Detect if the query is a question using linguistic features."""
        # Check for question marks
        if "?" in doc.text:
            return True

        # Check for question words at the beginning
        question_words = {
            "what",
            "how",
            "why",
            "when",
            "who",
            "where",
            "which",
            "whose",
            "whom",
        }
        first_token = doc[0] if doc else None
        if first_token and first_token.text.lower() in question_words:
            return True

        # Check for auxiliary verbs at the beginning (e.g., "Can you", "Do we", "Is there")
        if len(doc) >= 2:
            first_two = [token.text.lower() for token in doc[:2]]
            aux_patterns = {
                ("can", "you"),
                ("do", "we"),
                ("is", "there"),
                ("are", "there"),
                ("will", "you"),
            }
            if tuple(first_two) in aux_patterns:
                return True

        return False

    def _is_technical_query(
        self, doc: Doc, entities: list[tuple[str, str]], keywords: list[str]
    ) -> bool:
        """Detect if the query is technical in nature."""
        technical_indicators = {
            "api",
            "database",
            "system",
            "code",
            "function",
            "architecture",
            "implementation",
            "framework",
            "library",
            "server",
            "client",
            "protocol",
            "algorithm",
            "data",
            "query",
            "schema",
            "endpoint",
        }

        # Check keywords
        keyword_set = set(keywords)
        if keyword_set.intersection(technical_indicators):
            return True

        # Check for technical entity types
        technical_entities = {
            "ORG",
            "PRODUCT",
            "LANGUAGE",
        }  # Often technical in this context
        entity_labels = {label for _, label in entities}
        if entity_labels.intersection(technical_entities):
            return True

        return False

    def _calculate_complexity_score(self, doc: Doc) -> float:
        """Calculate query complexity based on linguistic features."""
        if not doc:
            return 0.0

        # Factors that contribute to complexity
        factors = {
            "length": min(len(doc) / 20, 1.0),  # Longer queries are more complex
            "entities": min(len(doc.ents) / 5, 1.0),  # More entities = more complex
            "noun_chunks": min(
                len(list(doc.noun_chunks)) / 5, 1.0
            ),  # More concepts = more complex
            "question_words": min(
                sum(
                    1
                    for token in doc
                    if token.text.lower()
                    in {"what", "how", "why", "when", "who", "where", "which"}
                )
                / 3,
                1.0,
            ),
            "dependency_depth": min(self._max_dependency_depth(doc) / 5, 1.0),
        }

        # Weighted average
        weights = {
            "length": 0.2,
            "entities": 0.3,
            "noun_chunks": 0.2,
            "question_words": 0.15,
            "dependency_depth": 0.15,
        }

        complexity = sum(factors[key] * weights[key] for key in factors)
        return min(complexity, 1.0)

    def _max_dependency_depth(self, doc: Doc) -> int:
        """Calculate maximum dependency tree depth."""
        max_depth = 0

        def get_depth(token, current_depth=0):
            nonlocal max_depth
            max_depth = max(max_depth, current_depth)
            for child in token.children:
                get_depth(child, current_depth + 1)

        for token in doc:
            if token.head == token:  # Root token
                get_depth(token)

        return max_depth

    def _token_similarity_fallback(
        self, query_keywords: list[str], entity_text: str
    ) -> float:
        """Fallback similarity calculation when word vectors are unavailable."""
        if not query_keywords:
            return 0.0

        entity_words = set(entity_text.lower().split())
        query_word_set = set(query_keywords)

        # Simple Jaccard similarity
        intersection = query_word_set.intersection(entity_words)
        union = query_word_set.union(entity_words)

        return len(intersection) / len(union) if union else 0.0

    def clear_cache(self):
        """Clear analysis and similarity caches."""
        self._analysis_cache.clear()
        self._similarity_cache.clear()
        logger.debug("Cleared spaCy analyzer caches")

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics for monitoring."""
        return {
            "analysis_cache_size": len(self._analysis_cache),
            "similarity_cache_size": len(self._similarity_cache),
        }
