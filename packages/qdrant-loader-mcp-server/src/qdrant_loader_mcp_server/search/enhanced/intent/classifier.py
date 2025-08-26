"""
Intent Classification Engine for Search Enhancement.

This module implements the main IntentClassifier that uses spaCy analysis and
behavioral patterns to classify search intents with high accuracy.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from ....utils.logging import LoggingConfig
from .models import IntentType, SearchIntent

_SPACY_IMPORT_ERROR: BaseException | None = None

if TYPE_CHECKING:
    from ...nlp.spacy_analyzer import QueryAnalysis, SpaCyQueryAnalyzer
else:
    try:
        from ...nlp.spacy_analyzer import QueryAnalysis, SpaCyQueryAnalyzer
    except (
        ImportError,
        ModuleNotFoundError,
    ) as _exc:  # pragma: no cover - optional dep
        # Provide safe sentinels for runtime to avoid NameErrors in annotations
        QueryAnalysis = Any  # type: ignore[assignment]
        SpaCyQueryAnalyzer = Any  # type: ignore[assignment]
        _SPACY_IMPORT_ERROR = _exc

logger = LoggingConfig.get_logger(__name__)


class IntentClassifier:
    """Advanced intent classification using spaCy analysis and behavioral patterns."""

    def __init__(self, spacy_analyzer):
        """Initialize the intent classifier.

        The constructor validates that the spaCy analyzer dependency is available.
        If a valid analyzer instance is not provided, it attempts a runtime import.
        On failure, it raises an ImportError with actionable guidance so callers
        fail fast rather than encountering None-attribute errors later.
        """
        if spacy_analyzer is None:
            # Do not perform ad-hoc imports here; require explicit injection
            if _SPACY_IMPORT_ERROR is not None:
                raise ImportError(
                    "SpaCyQueryAnalyzer is not available. Install optional NLP deps (spacy and model) "
                    "and provide an initialized analyzer instance to IntentClassifier."
                ) from _SPACY_IMPORT_ERROR
            raise ImportError(
                "A spaCy analyzer instance must be provided to IntentClassifier. "
                "Use SpaCyQueryAnalyzer() and pass it explicitly."
            )
        self.spacy_analyzer = spacy_analyzer

        # Final sanity check to fail fast if analyzer is misconfigured
        if not hasattr(self.spacy_analyzer, "analyze_query_semantic"):
            raise ImportError(
                "Provided spaCy analyzer does not implement 'analyze_query_semantic'. "
                "Pass a compatible analyzer or install the default SpaCyQueryAnalyzer."
            )
        self.logger = LoggingConfig.get_logger(__name__)

        # Intent classification patterns using spaCy linguistic features
        self.intent_patterns = {
            IntentType.TECHNICAL_LOOKUP: {
                "keywords": {
                    "api",
                    "apis",
                    "endpoint",
                    "endpoints",
                    "function",
                    "functions",
                    "method",
                    "methods",
                    "class",
                    "classes",
                    "library",
                    "libraries",
                    "framework",
                    "frameworks",
                    "code",
                    "implementation",
                    "syntax",
                    "documentation",
                    "docs",
                    "reference",
                    "specification",
                    "protocol",
                },
                "pos_patterns": [
                    ["NOUN", "NOUN"],  # "API documentation"
                    ["ADJ", "NOUN"],  # "REST API"
                    ["VERB", "NOUN"],  # "implement authentication"
                    ["NOUN", "VERB"],  # "code example"
                ],
                "entity_types": {"PRODUCT", "ORG", "LANGUAGE"},
                "question_words": {"how", "what"},
                "linguistic_indicators": {
                    "has_code_terms": True,
                    "technical_complexity": 0.6,
                    "verb_imperative": True,
                },
                "weight": 1.0,
            },
            IntentType.BUSINESS_CONTEXT: {
                "keywords": {
                    "requirements",
                    "requirement",
                    "objectives",
                    "objective",
                    "goals",
                    "goal",
                    "strategy",
                    "strategies",
                    "business",
                    "scope",
                    "stakeholder",
                    "stakeholders",
                    "budget",
                    "timeline",
                    "deliverable",
                    "deliverables",
                    "milestone",
                    "criteria",
                    "specification",
                    "specifications",
                    "priority",
                    "priorities",
                },
                "pos_patterns": [
                    ["NOUN", "NOUN"],  # "business requirements"
                    ["ADJ", "NOUN"],  # "functional requirements"
                    ["MODAL", "VERB"],  # "should implement"
                    ["DET", "NOUN", "VERB"],  # "the system should"
                ],
                "entity_types": {"ORG", "MONEY", "PERCENT", "CARDINAL"},
                "question_words": {"what", "why", "which"},
                "linguistic_indicators": {
                    "has_business_terms": True,
                    "formal_language": True,
                    "future_tense": True,
                },
                "weight": 1.0,
            },
            IntentType.VENDOR_EVALUATION: {
                "keywords": {
                    "vendor",
                    "vendors",
                    "supplier",
                    "suppliers",
                    "proposal",
                    "proposals",
                    "bid",
                    "bids",
                    "quote",
                    "quotes",
                    "cost",
                    "costs",
                    "price",
                    "pricing",
                    "comparison",
                    "compare",
                    "evaluate",
                    "evaluation",
                    "criteria",
                    "selection",
                    "recommendation",
                    "assessment",
                    "analysis",
                },
                "pos_patterns": [
                    ["NOUN", "NOUN"],  # "vendor proposal"
                    ["VERB", "NOUN"],  # "compare vendors"
                    ["ADJ", "NOUN"],  # "best vendor"
                    ["NOUN", "VERB", "ADJ"],  # "vendor is better"
                ],
                "entity_types": {"ORG", "MONEY", "PERSON"},
                "question_words": {"which", "who", "what", "how much"},
                "linguistic_indicators": {
                    "has_comparison": True,
                    "has_evaluation_terms": True,
                    "superlative_forms": True,
                },
                "weight": 1.0,
            },
            IntentType.PROCEDURAL: {
                "keywords": {
                    "how",
                    "steps",
                    "step",
                    "process",
                    "procedure",
                    "guide",
                    "tutorial",
                    "walkthrough",
                    "instructions",
                    "setup",
                    "configure",
                    "install",
                    "deploy",
                    "implement",
                    "create",
                    "build",
                    "make",
                    "do",
                },
                "pos_patterns": [
                    ["VERB", "NOUN"],  # "install package"
                    ["VERB", "DET", "NOUN"],  # "setup the system"
                    ["ADV", "VERB"],  # "how configure"
                    ["NOUN", "VERB"],  # "steps install"
                ],
                "entity_types": set(),
                "question_words": {"how", "when", "where"},
                "linguistic_indicators": {
                    "imperative_mood": True,
                    "action_oriented": True,
                    "sequential_indicators": True,
                },
                "weight": 1.0,
            },
            IntentType.INFORMATIONAL: {
                "keywords": {
                    "what",
                    "definition",
                    "meaning",
                    "explain",
                    "overview",
                    "about",
                    "introduction",
                    "basics",
                    "fundamentals",
                    "concept",
                    "concepts",
                    "understand",
                    "learn",
                    "know",
                    "information",
                    "details",
                },
                "pos_patterns": [
                    ["NOUN"],  # "authentication"
                    ["ADJ", "NOUN"],  # "basic concept"
                    ["VERB", "NOUN"],  # "understand API"
                    ["NOUN", "VERB"],  # "concept explains"
                ],
                "entity_types": set(),
                "question_words": {"what", "who", "when", "where"},
                "linguistic_indicators": {
                    "knowledge_seeking": True,
                    "present_tense": True,
                    "general_terms": True,
                },
                "weight": 1.0,
            },
            IntentType.TROUBLESHOOTING: {
                "keywords": {
                    "error",
                    "errors",
                    "problem",
                    "problems",
                    "issue",
                    "issues",
                    "bug",
                    "bugs",
                    "fix",
                    "fixes",
                    "solve",
                    "solution",
                    "solutions",
                    "troubleshoot",
                    "debug",
                    "debugging",
                    "failed",
                    "failing",
                    "broken",
                    "not working",
                    "doesn't work",
                },
                "pos_patterns": [
                    ["NOUN", "VERB"],  # "error occurs"
                    ["VERB", "NOUN"],  # "fix error"
                    ["ADJ", "NOUN"],  # "broken system"
                    ["NOUN", "ADJ"],  # "system broken"
                ],
                "entity_types": set(),
                "question_words": {"why", "how", "what"},
                "linguistic_indicators": {
                    "negative_sentiment": True,
                    "problem_indicators": True,
                    "past_tense": True,
                },
                "weight": 1.0,
            },
            IntentType.EXPLORATORY: {
                "keywords": {
                    "explore",
                    "discover",
                    "find",
                    "search",
                    "browse",
                    "look",
                    "see",
                    "show",
                    "list",
                    "available",
                    "options",
                    "alternatives",
                    "similar",
                    "related",
                    "examples",
                    "samples",
                },
                "pos_patterns": [
                    ["VERB"],  # "explore"
                    ["VERB", "NOUN"],  # "find examples"
                    ["ADJ", "NOUN"],  # "similar tools"
                    ["DET", "NOUN"],  # "some options"
                ],
                "entity_types": set(),
                "question_words": {"what", "which"},
                "linguistic_indicators": {
                    "open_ended": True,
                    "discovery_oriented": True,
                    "broad_scope": True,
                },
                "weight": 0.8,
            },
        }

        # Behavioral pattern recognition
        self.session_patterns = {
            "technical_session": [IntentType.TECHNICAL_LOOKUP, IntentType.PROCEDURAL],
            "business_session": [
                IntentType.BUSINESS_CONTEXT,
                IntentType.VENDOR_EVALUATION,
            ],
            "learning_session": [
                IntentType.INFORMATIONAL,
                IntentType.EXPLORATORY,
                IntentType.PROCEDURAL,
            ],
            "problem_solving": [
                IntentType.TROUBLESHOOTING,
                IntentType.PROCEDURAL,
                IntentType.TECHNICAL_LOOKUP,
            ],
        }

        # Cache for intent classification results
        self._intent_cache: dict[str, SearchIntent] = {}

        logger.info("Initialized intent classifier with spaCy integration")

    def classify_intent(
        self,
        query: str,
        session_context: dict[str, Any] | None = None,
        behavioral_context: list[str] | None = None,
    ) -> SearchIntent:
        """Classify search intent using comprehensive spaCy analysis."""

        start_time = time.time()

        # Check cache first
        cache_key = f"{query}:{str(session_context)}:{str(behavioral_context)}"
        if cache_key in self._intent_cache:
            cached = self._intent_cache[cache_key]
            logger.debug(f"Using cached intent classification for: {query[:50]}...")
            return cached

        # Ensure analyzer is available and valid (extra safety beyond __init__)
        if not hasattr(self.spacy_analyzer, "analyze_query_semantic"):
            raise ImportError(
                "SpaCy analyzer is not initialized correctly. Missing 'analyze_query_semantic'."
            )

        try:
            # Step 1: Perform spaCy semantic analysis
            spacy_analysis = self.spacy_analyzer.analyze_query_semantic(query)

            # Step 2: Extract linguistic features for intent classification
            linguistic_features = self._extract_linguistic_features(
                spacy_analysis, query
            )

            # Step 3: Score each intent type using pattern matching
            intent_scores = self._score_intent_patterns(
                spacy_analysis, linguistic_features, query
            )

            # Step 4: Apply behavioral context weighting
            if behavioral_context:
                intent_scores = self._apply_behavioral_weighting(
                    intent_scores, behavioral_context
                )

            # Step 5: Apply session context boosting
            if session_context:
                intent_scores = self._apply_session_context(
                    intent_scores, session_context
                )

            # Step 6: Determine primary and secondary intents
            primary_intent, confidence = self._select_primary_intent(intent_scores)
            secondary_intents = self._select_secondary_intents(
                intent_scores, primary_intent
            )

            # Step 7: Build supporting evidence
            supporting_evidence = self._build_evidence(
                spacy_analysis, linguistic_features, intent_scores
            )

            # Step 8: Create intent result
            classification_time = (time.time() - start_time) * 1000

            search_intent = SearchIntent(
                intent_type=primary_intent,
                confidence=confidence,
                secondary_intents=secondary_intents,
                supporting_evidence=supporting_evidence,
                linguistic_features=linguistic_features,
                query_complexity=spacy_analysis.complexity_score,
                is_question=spacy_analysis.is_question,
                is_technical=spacy_analysis.is_technical,
                session_context=session_context or {},
                previous_intents=behavioral_context or [],
                classification_time_ms=classification_time,
            )

            # Cache the result
            self._intent_cache[cache_key] = search_intent

            logger.debug(
                f"Classified intent in {classification_time:.2f}ms",
                query_length=len(query),
                primary_intent=primary_intent.value,
                confidence=confidence,
                secondary_count=len(secondary_intents),
            )

            return search_intent

        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            # Return fallback intent
            classification_time = (time.time() - start_time) * 1000
            return SearchIntent(
                intent_type=IntentType.GENERAL,
                confidence=0.5,
                classification_time_ms=classification_time,
            )

    def _extract_linguistic_features(
        self, spacy_analysis, query: str
    ) -> dict[str, Any]:
        """Extract comprehensive linguistic features for intent classification."""

        features = {
            # Basic query characteristics
            "query_length": len(query.split()),
            "has_question_mark": "?" in query,
            "starts_with_question_word": False,
            "starts_with_verb": False,
            "has_imperative_verbs": False,
            "has_modal_verbs": False,
            # spaCy-derived features
            "entity_count": len(spacy_analysis.entities),
            "concept_count": len(spacy_analysis.main_concepts),
            "keyword_count": len(spacy_analysis.semantic_keywords),
            "pos_diversity": len(set(spacy_analysis.pos_patterns)),
            # Semantic features
            "technical_indicators": 0,
            "business_indicators": 0,
            "procedural_indicators": 0,
            "problem_indicators": 0,
            # Entity type analysis
            "entity_types": [ent[1] for ent in spacy_analysis.entities],
            "has_org_entities": any(ent[1] == "ORG" for ent in spacy_analysis.entities),
            "has_product_entities": any(
                ent[1] == "PRODUCT" for ent in spacy_analysis.entities
            ),
            "has_person_entities": any(
                ent[1] == "PERSON" for ent in spacy_analysis.entities
            ),
            "has_money_entities": any(
                ent[1] == "MONEY" for ent in spacy_analysis.entities
            ),
        }

        # Analyze question word patterns
        question_words = {
            "what",
            "how",
            "why",
            "when",
            "who",
            "where",
            "which",
            "whose",
        }
        query_lower = query.lower()
        first_word = query_lower.split()[0] if query_lower.split() else ""
        features["starts_with_question_word"] = first_word in question_words

        # Count technical, business, and procedural indicators
        technical_terms = {
            "api",
            "code",
            "function",
            "method",
            "library",
            "framework",
            "implementation",
        }
        business_terms = {
            "requirements",
            "objectives",
            "strategy",
            "business",
            "scope",
            "criteria",
        }
        procedural_terms = {
            "how",
            "steps",
            "process",
            "guide",
            "setup",
            "install",
            "configure",
        }
        problem_terms = {
            "error",
            "problem",
            "issue",
            "bug",
            "fix",
            "solve",
            "broken",
            "failed",
        }

        keywords_lower = [kw.lower() for kw in spacy_analysis.semantic_keywords]
        features["technical_indicators"] = sum(
            1 for term in technical_terms if term in keywords_lower
        )
        features["business_indicators"] = sum(
            1 for term in business_terms if term in keywords_lower
        )
        features["procedural_indicators"] = sum(
            1 for term in procedural_terms if term in keywords_lower
        )
        features["problem_indicators"] = sum(
            1 for term in problem_terms if term in keywords_lower
        )

        # POS pattern analysis
        pos_patterns = spacy_analysis.pos_patterns
        features["starts_with_verb"] = bool(pos_patterns) and pos_patterns[0] == "VERB"
        # Imperative: sentence starts with a verb and does not start with a question word
        features["has_imperative_verbs"] = (
            ("VERB" in pos_patterns)
            and features["starts_with_verb"]
            and not features.get("starts_with_question_word", False)
        )
        features["has_modal_verbs"] = any(
            pos in ["MD", "MODAL"] for pos in pos_patterns
        )

        return features

    def _score_intent_patterns(
        self,
        spacy_analysis,
        linguistic_features: dict[str, Any],
        query: str,
    ) -> dict[IntentType, float]:
        """Score each intent type using pattern matching."""

        intent_scores = {}
        keywords_set = {kw.lower() for kw in spacy_analysis.semantic_keywords}

        for intent_type, pattern in self.intent_patterns.items():
            score = 0.0

            # 1. Keyword matching (40% weight)
            keyword_matches = len(keywords_set.intersection(pattern["keywords"]))
            keyword_score = keyword_matches / max(len(pattern["keywords"]), 1)
            score += keyword_score * 0.4

            # 2. POS pattern matching (25% weight)
            pos_score = self._match_pos_patterns(
                spacy_analysis.pos_patterns, pattern["pos_patterns"]
            )
            score += pos_score * 0.25

            # 3. Entity type matching (20% weight)
            entity_score = self._match_entity_types(
                spacy_analysis.entities, pattern["entity_types"]
            )
            score += entity_score * 0.20

            # 4. Question word matching (10% weight)
            question_score = self._match_question_words(
                query, pattern["question_words"]
            )
            score += question_score * 0.10

            # 5. Linguistic indicator bonus (5% weight)
            indicator_score = self._match_linguistic_indicators(
                linguistic_features, pattern.get("linguistic_indicators", {})
            )
            score += indicator_score * 0.05

            # Apply pattern weight
            score *= pattern.get("weight", 1.0)

            intent_scores[intent_type] = score

        return intent_scores

    def _match_pos_patterns(
        self, query_pos: list[str], target_patterns: list[list[str]]
    ) -> float:
        """Match POS tag patterns in the query."""
        if not target_patterns or not query_pos:
            return 0.0

        matches = 0
        total_patterns = len(target_patterns)

        for pattern in target_patterns:
            if self._contains_pos_sequence(query_pos, pattern):
                matches += 1

        return matches / total_patterns

    def _contains_pos_sequence(self, pos_tags: list[str], sequence: list[str]) -> bool:
        """Check if POS sequence exists in the query."""
        if len(sequence) > len(pos_tags):
            return False

        for i in range(len(pos_tags) - len(sequence) + 1):
            if pos_tags[i : i + len(sequence)] == sequence:
                return True

        return False

    def _match_entity_types(
        self, query_entities: list[tuple[str, str]], target_types: set[str]
    ) -> float:
        """Match entity types in the query."""
        if not target_types:
            return 0.0

        query_entity_types = {ent[1] for ent in query_entities}
        matches = len(query_entity_types.intersection(target_types))

        return matches / len(target_types)

    def _match_question_words(self, query: str, target_words: set[str]) -> float:
        """Match question words in the query."""
        if not target_words:
            return 0.0

        query_words = set(query.lower().split())
        matches = len(query_words.intersection(target_words))

        return matches / len(target_words)

    def _match_linguistic_indicators(
        self, features: dict[str, Any], target_indicators: dict[str, Any]
    ) -> float:
        """Match linguistic indicators."""
        if not target_indicators:
            return 0.0

        score = 0.0
        total_indicators = len(target_indicators)

        for indicator, expected_value in target_indicators.items():
            if indicator in features:
                if isinstance(expected_value, bool):
                    if features[indicator] == expected_value:
                        score += 1.0
                elif isinstance(expected_value, int | float):
                    # For numeric indicators, use magnitude-aware similarity
                    actual_value = features.get(indicator, 0)
                    if isinstance(actual_value, int | float):
                        denom = max(abs(expected_value), abs(actual_value), 1.0)
                        similarity = 1.0 - abs(actual_value - expected_value) / denom
                        score += max(0.0, similarity)

        return score / max(total_indicators, 1)

    def _apply_behavioral_weighting(
        self, intent_scores: dict[IntentType, float], behavioral_context: list[str]
    ) -> dict[IntentType, float]:
        """Apply behavioral context weighting to intent scores."""

        if not behavioral_context:
            return intent_scores

        # Convert string intents to IntentType
        previous_intents = []
        for intent_str in behavioral_context[-5:]:  # Last 5 intents
            try:
                previous_intents.append(IntentType(intent_str))
            except ValueError:
                continue

        if not previous_intents:
            return intent_scores

        weighted_scores = intent_scores.copy()

        # Boost scores for intents that commonly follow previous intents
        intent_transitions = {
            IntentType.INFORMATIONAL: [
                IntentType.PROCEDURAL,
                IntentType.TECHNICAL_LOOKUP,
            ],
            IntentType.TECHNICAL_LOOKUP: [
                IntentType.PROCEDURAL,
                IntentType.TROUBLESHOOTING,
            ],
            IntentType.BUSINESS_CONTEXT: [
                IntentType.VENDOR_EVALUATION,
                IntentType.TECHNICAL_LOOKUP,
            ],
            IntentType.VENDOR_EVALUATION: [
                IntentType.BUSINESS_CONTEXT,
                IntentType.TECHNICAL_LOOKUP,
            ],
            IntentType.PROCEDURAL: [
                IntentType.TROUBLESHOOTING,
                IntentType.TECHNICAL_LOOKUP,
            ],
            IntentType.TROUBLESHOOTING: [
                IntentType.PROCEDURAL,
                IntentType.TECHNICAL_LOOKUP,
            ],
        }

        most_recent_intent = previous_intents[-1]
        likely_next_intents = intent_transitions.get(most_recent_intent, [])

        for intent_type in likely_next_intents:
            if intent_type in weighted_scores:
                weighted_scores[intent_type] *= 1.2  # 20% boost

        # Apply session pattern recognition
        for _pattern_name, pattern_intents in self.session_patterns.items():
            pattern_match_score = sum(
                1 for intent in previous_intents if intent in pattern_intents
            ) / len(pattern_intents)

            if pattern_match_score > 0.5:  # More than half of pattern matched
                for intent_type in pattern_intents:
                    if intent_type in weighted_scores:
                        weighted_scores[intent_type] *= 1.0 + pattern_match_score * 0.3

        return weighted_scores

    def _apply_session_context(
        self, intent_scores: dict[IntentType, float], session_context: dict[str, Any]
    ) -> dict[IntentType, float]:
        """Apply session context to intent scores."""

        weighted_scores = intent_scores.copy()

        # Apply domain context boosting
        domain = session_context.get("domain", "")
        if domain == "technical":
            weighted_scores[IntentType.TECHNICAL_LOOKUP] *= 1.3
            weighted_scores[IntentType.PROCEDURAL] *= 1.2
        elif domain == "business":
            weighted_scores[IntentType.BUSINESS_CONTEXT] *= 1.3
            weighted_scores[IntentType.VENDOR_EVALUATION] *= 1.2

        # Apply user role context
        user_role = session_context.get("user_role", "")
        if user_role in ["developer", "engineer", "architect"]:
            weighted_scores[IntentType.TECHNICAL_LOOKUP] *= 1.2
            weighted_scores[IntentType.PROCEDURAL] *= 1.1
        elif user_role in ["manager", "analyst", "consultant"]:
            weighted_scores[IntentType.BUSINESS_CONTEXT] *= 1.2
            weighted_scores[IntentType.VENDOR_EVALUATION] *= 1.1

        # Apply urgency context
        urgency = session_context.get("urgency", "normal")
        if urgency == "high":
            weighted_scores[IntentType.TROUBLESHOOTING] *= 1.4
            weighted_scores[IntentType.PROCEDURAL] *= 1.2

        return weighted_scores

    def _select_primary_intent(
        self, intent_scores: dict[IntentType, float]
    ) -> tuple[IntentType, float]:
        """Select the primary intent with highest confidence."""

        if not intent_scores:
            return IntentType.GENERAL, 0.5

        # Find the highest scoring intent
        primary_intent = max(intent_scores, key=intent_scores.get)
        raw_score = intent_scores[primary_intent]

        # Normalize confidence score
        total_score = sum(intent_scores.values())
        confidence = raw_score / max(total_score, 1.0)

        # Apply confidence threshold
        if confidence < 0.3:
            return IntentType.GENERAL, confidence

        return primary_intent, confidence

    def _select_secondary_intents(
        self, intent_scores: dict[IntentType, float], primary_intent: IntentType
    ) -> list[tuple[IntentType, float]]:
        """Select secondary intents with meaningful confidence."""

        secondary_intents = []

        # If primary intent is GENERAL (fallback), don't calculate secondary intents
        if primary_intent == IntentType.GENERAL or primary_intent not in intent_scores:
            return secondary_intents

        # Sort intents by score, excluding primary
        sorted_intents = sorted(
            [
                (intent, score)
                for intent, score in intent_scores.items()
                if intent != primary_intent
            ],
            key=lambda x: x[1],
            reverse=True,
        )

        # Include intents with score > 30% of primary intent score
        primary_score = intent_scores[primary_intent]
        threshold = primary_score * 0.3

        for intent, score in sorted_intents[:3]:  # Max 3 secondary intents
            if score >= threshold:
                confidence = score / max(sum(intent_scores.values()), 1.0)
                secondary_intents.append((intent, confidence))

        return secondary_intents

    def _build_evidence(
        self,
        spacy_analysis,
        linguistic_features: dict[str, Any],
        intent_scores: dict[IntentType, float],
    ) -> dict[str, Any]:
        """Build supporting evidence for the intent classification."""

        return {
            "spacy_processing_time": spacy_analysis.processing_time_ms,
            "query_complexity": spacy_analysis.complexity_score,
            "semantic_keywords": spacy_analysis.semantic_keywords[:5],  # Top 5
            "extracted_entities": [
                ent[0] for ent in spacy_analysis.entities[:3]
            ],  # Top 3
            "main_concepts": spacy_analysis.main_concepts[:3],  # Top 3
            "intent_signals": spacy_analysis.intent_signals,
            "linguistic_features": {
                "technical_indicators": linguistic_features.get(
                    "technical_indicators", 0
                ),
                "business_indicators": linguistic_features.get(
                    "business_indicators", 0
                ),
                "procedural_indicators": linguistic_features.get(
                    "procedural_indicators", 0
                ),
                "problem_indicators": linguistic_features.get("problem_indicators", 0),
            },
            "top_intent_scores": dict(
                sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)[:3]
            ),
        }

    def clear_cache(self):
        """Clear intent classification cache."""
        self._intent_cache.clear()
        logger.debug("Cleared intent classification cache")

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        return {
            "intent_cache_size": len(self._intent_cache),
        }
