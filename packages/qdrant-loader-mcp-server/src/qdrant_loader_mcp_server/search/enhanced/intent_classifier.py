"""Intent-Aware Adaptive Search for Phase 2.2 Search Enhancement.

This module implements advanced intent classification and adaptive search strategies
that leverage Phase 1.0 spaCy analysis and Phase 2.1 knowledge graph capabilities.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from collections import defaultdict, Counter
import math

from ...utils.logging import LoggingConfig
from ..nlp.spacy_analyzer import SpaCyQueryAnalyzer, QueryAnalysis
from ..models import SearchResult
from .knowledge_graph import DocumentKnowledgeGraph, TraversalStrategy

logger = LoggingConfig.get_logger(__name__)


class IntentType(Enum):
    """Types of search intents for adaptive search strategies."""
    TECHNICAL_LOOKUP = "technical_lookup"       # API docs, code examples, implementation
    BUSINESS_CONTEXT = "business_context"       # Requirements, objectives, strategy
    VENDOR_EVALUATION = "vendor_evaluation"     # Proposals, comparisons, criteria
    PROCEDURAL = "procedural"                   # How-to guides, step-by-step
    INFORMATIONAL = "informational"             # What is, definitions, overviews
    EXPLORATORY = "exploratory"                 # Broad discovery, browsing
    TROUBLESHOOTING = "troubleshooting"         # Error solving, debugging
    GENERAL = "general"                         # Fallback for unclear intent


@dataclass
class SearchIntent:
    """Container for classified search intent with confidence and context."""
    
    intent_type: IntentType
    confidence: float                           # 0.0 - 1.0 confidence score
    secondary_intents: List[Tuple[IntentType, float]] = field(default_factory=list)
    
    # Linguistic evidence
    supporting_evidence: Dict[str, Any] = field(default_factory=dict)
    linguistic_features: Dict[str, Any] = field(default_factory=dict)
    
    # Context information
    query_complexity: float = 0.0              # From spaCy analysis
    is_question: bool = False
    is_technical: bool = False
    
    # Behavioral context
    session_context: Dict[str, Any] = field(default_factory=dict)
    previous_intents: List[IntentType] = field(default_factory=list)
    
    # Processing metadata
    classification_time_ms: float = 0.0


@dataclass 
class AdaptiveSearchConfig:
    """Configuration for adaptive search based on intent."""
    
    # Core search parameters
    search_strategy: str = "hybrid"             # hybrid, vector, keyword
    vector_weight: float = 0.7                  # Weight for vector search
    keyword_weight: float = 0.3                 # Weight for keyword search
    
    # Knowledge graph integration
    use_knowledge_graph: bool = False
    kg_traversal_strategy: TraversalStrategy = TraversalStrategy.SEMANTIC
    max_graph_hops: int = 2
    kg_expansion_weight: float = 0.2
    
    # Result filtering and ranking
    result_filters: Dict[str, Any] = field(default_factory=dict)
    ranking_boosts: Dict[str, float] = field(default_factory=dict)
    source_type_preferences: Dict[str, float] = field(default_factory=dict)
    
    # Query expansion
    expand_query: bool = True
    expansion_aggressiveness: float = 0.3       # 0.0 - 1.0
    semantic_expansion: bool = True
    entity_expansion: bool = True
    
    # Performance tuning
    max_results: int = 20
    min_score_threshold: float = 0.1
    diversity_factor: float = 0.0               # 0.0 = relevance only, 1.0 = max diversity
    
    # Contextual parameters
    temporal_bias: float = 0.0                  # Bias toward recent content
    authority_bias: float = 0.0                 # Bias toward authoritative sources
    personal_bias: float = 0.0                  # Bias toward user's previous interests


class IntentClassifier:
    """Advanced intent classification using spaCy analysis and behavioral patterns."""
    
    def __init__(self, spacy_analyzer: SpaCyQueryAnalyzer):
        """Initialize the intent classifier."""
        self.spacy_analyzer = spacy_analyzer
        self.logger = LoggingConfig.get_logger(__name__)
        
        # Intent classification patterns using spaCy linguistic features
        self.intent_patterns = {
            IntentType.TECHNICAL_LOOKUP: {
                "keywords": {
                    "api", "apis", "endpoint", "endpoints", "function", "functions",
                    "method", "methods", "class", "classes", "library", "libraries",
                    "framework", "frameworks", "code", "implementation", "syntax",
                    "documentation", "docs", "reference", "specification", "protocol"
                },
                "pos_patterns": [
                    ["NOUN", "NOUN"],           # "API documentation"
                    ["ADJ", "NOUN"],            # "REST API"
                    ["VERB", "NOUN"],           # "implement authentication"
                    ["NOUN", "VERB"],           # "code example"
                ],
                "entity_types": {"PRODUCT", "ORG", "LANGUAGE"},
                "question_words": {"how", "what"},
                "linguistic_indicators": {
                    "has_code_terms": True,
                    "technical_complexity": 0.6,
                    "verb_imperative": True
                },
                "weight": 1.0
            },
            
            IntentType.BUSINESS_CONTEXT: {
                "keywords": {
                    "requirements", "requirement", "objectives", "objective", "goals", "goal",
                    "strategy", "strategies", "business", "scope", "stakeholder", "stakeholders",
                    "budget", "timeline", "deliverable", "deliverables", "milestone",
                    "criteria", "specification", "specifications", "priority", "priorities"
                },
                "pos_patterns": [
                    ["NOUN", "NOUN"],           # "business requirements"
                    ["ADJ", "NOUN"],            # "functional requirements"
                    ["MODAL", "VERB"],          # "should implement"
                    ["DET", "NOUN", "VERB"],    # "the system should"
                ],
                "entity_types": {"ORG", "MONEY", "PERCENT", "CARDINAL"},
                "question_words": {"what", "why", "which"},
                "linguistic_indicators": {
                    "has_business_terms": True,
                    "formal_language": True,
                    "future_tense": True
                },
                "weight": 1.0
            },
            
            IntentType.VENDOR_EVALUATION: {
                "keywords": {
                    "vendor", "vendors", "supplier", "suppliers", "proposal", "proposals",
                    "bid", "bids", "quote", "quotes", "cost", "costs", "price", "pricing",
                    "comparison", "compare", "evaluate", "evaluation", "criteria",
                    "selection", "recommendation", "assessment", "analysis"
                },
                "pos_patterns": [
                    ["NOUN", "NOUN"],           # "vendor proposal"
                    ["VERB", "NOUN"],           # "compare vendors"
                    ["ADJ", "NOUN"],            # "best vendor"
                    ["NOUN", "VERB", "ADJ"],    # "vendor is better"
                ],
                "entity_types": {"ORG", "MONEY", "PERSON"},
                "question_words": {"which", "who", "what", "how much"},
                "linguistic_indicators": {
                    "has_comparison": True,
                    "has_evaluation_terms": True,
                    "superlative_forms": True
                },
                "weight": 1.0
            },
            
            IntentType.PROCEDURAL: {
                "keywords": {
                    "how", "steps", "step", "process", "procedure", "guide", "tutorial",
                    "walkthrough", "instructions", "setup", "configure", "install",
                    "deploy", "implement", "create", "build", "make", "do"
                },
                "pos_patterns": [
                    ["VERB", "NOUN"],           # "install package"
                    ["VERB", "DET", "NOUN"],    # "setup the system"
                    ["ADV", "VERB"],            # "how configure"
                    ["NOUN", "VERB"],           # "steps install"
                ],
                "entity_types": set(),
                "question_words": {"how", "when", "where"},
                "linguistic_indicators": {
                    "imperative_mood": True,
                    "action_oriented": True,
                    "sequential_indicators": True
                },
                "weight": 1.0
            },
            
            IntentType.INFORMATIONAL: {
                "keywords": {
                    "what", "definition", "meaning", "explain", "overview", "about",
                    "introduction", "basics", "fundamentals", "concept", "concepts",
                    "understand", "learn", "know", "information", "details"
                },
                "pos_patterns": [
                    ["NOUN"],                   # "authentication"
                    ["ADJ", "NOUN"],            # "basic concept"
                    ["VERB", "NOUN"],           # "understand API"
                    ["NOUN", "VERB"],           # "concept explains"
                ],
                "entity_types": set(),
                "question_words": {"what", "who", "when", "where"},
                "linguistic_indicators": {
                    "knowledge_seeking": True,
                    "present_tense": True,
                    "general_terms": True
                },
                "weight": 1.0
            },
            
            IntentType.TROUBLESHOOTING: {
                "keywords": {
                    "error", "errors", "problem", "problems", "issue", "issues",
                    "bug", "bugs", "fix", "fixes", "solve", "solution", "solutions",
                    "troubleshoot", "debug", "debugging", "failed", "failing",
                    "broken", "not working", "doesn't work"
                },
                "pos_patterns": [
                    ["NOUN", "VERB"],           # "error occurs"
                    ["VERB", "NOUN"],           # "fix error"
                    ["ADJ", "NOUN"],            # "broken system"
                    ["NOUN", "ADJ"],            # "system broken"
                ],
                "entity_types": set(),
                "question_words": {"why", "how", "what"},
                "linguistic_indicators": {
                    "negative_sentiment": True,
                    "problem_indicators": True,
                    "past_tense": True
                },
                "weight": 1.0
            },
            
            IntentType.EXPLORATORY: {
                "keywords": {
                    "explore", "discover", "find", "search", "browse", "look",
                    "see", "show", "list", "available", "options", "alternatives",
                    "similar", "related", "examples", "samples"
                },
                "pos_patterns": [
                    ["VERB"],                   # "explore"
                    ["VERB", "NOUN"],           # "find examples"
                    ["ADJ", "NOUN"],            # "similar tools"
                    ["DET", "NOUN"],            # "some options"
                ],
                "entity_types": set(),
                "question_words": {"what", "which"},
                "linguistic_indicators": {
                    "open_ended": True,
                    "discovery_oriented": True,
                    "broad_scope": True
                },
                "weight": 0.8
            }
        }
        
        # Behavioral pattern recognition
        self.session_patterns = {
            "technical_session": [IntentType.TECHNICAL_LOOKUP, IntentType.PROCEDURAL],
            "business_session": [IntentType.BUSINESS_CONTEXT, IntentType.VENDOR_EVALUATION],
            "learning_session": [IntentType.INFORMATIONAL, IntentType.EXPLORATORY, IntentType.PROCEDURAL],
            "problem_solving": [IntentType.TROUBLESHOOTING, IntentType.PROCEDURAL, IntentType.TECHNICAL_LOOKUP]
        }
        
        # Cache for intent classification results
        self._intent_cache: Dict[str, SearchIntent] = {}
        
        logger.info("Initialized intent classifier with spaCy integration")
    
    def classify_intent(
        self, 
        query: str, 
        session_context: Optional[Dict[str, Any]] = None,
        behavioral_context: Optional[List[str]] = None
    ) -> SearchIntent:
        """Classify search intent using comprehensive spaCy analysis."""
        
        start_time = time.time()
        
        # Check cache first
        cache_key = f"{query}:{str(session_context)}:{str(behavioral_context)}"
        if cache_key in self._intent_cache:
            cached = self._intent_cache[cache_key]
            logger.debug(f"Using cached intent classification for: {query[:50]}...")
            return cached
        
        try:
            # Step 1: Perform spaCy semantic analysis (leveraging Phase 1.0)
            spacy_analysis = self.spacy_analyzer.analyze_query_semantic(query)
            
            # Step 2: Extract linguistic features for intent classification
            linguistic_features = self._extract_linguistic_features(spacy_analysis, query)
            
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
            secondary_intents = self._select_secondary_intents(intent_scores, primary_intent)
            
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
                classification_time_ms=classification_time
            )
            
            # Cache the result
            self._intent_cache[cache_key] = search_intent
            
            logger.debug(
                f"Classified intent in {classification_time:.2f}ms",
                query_length=len(query),
                primary_intent=primary_intent.value,
                confidence=confidence,
                secondary_count=len(secondary_intents)
            )
            
            return search_intent
            
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            # Return fallback intent
            classification_time = (time.time() - start_time) * 1000
            return SearchIntent(
                intent_type=IntentType.GENERAL,
                confidence=0.5,
                classification_time_ms=classification_time
            )
    
    def _extract_linguistic_features(
        self, 
        spacy_analysis: QueryAnalysis, 
        query: str
    ) -> Dict[str, Any]:
        """Extract comprehensive linguistic features for intent classification."""
        
        features = {
            # Basic query characteristics
            "query_length": len(query.split()),
            "has_question_mark": "?" in query,
            "starts_with_question_word": False,
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
            "has_product_entities": any(ent[1] == "PRODUCT" for ent in spacy_analysis.entities),
            "has_person_entities": any(ent[1] == "PERSON" for ent in spacy_analysis.entities),
            "has_money_entities": any(ent[1] == "MONEY" for ent in spacy_analysis.entities),
        }
        
        # Analyze question word patterns
        question_words = {"what", "how", "why", "when", "who", "where", "which", "whose"}
        query_lower = query.lower()
        first_word = query_lower.split()[0] if query_lower.split() else ""
        features["starts_with_question_word"] = first_word in question_words
        
        # Count technical, business, and procedural indicators
        technical_terms = {"api", "code", "function", "method", "library", "framework", "implementation"}
        business_terms = {"requirements", "objectives", "strategy", "business", "scope", "criteria"}
        procedural_terms = {"how", "steps", "process", "guide", "setup", "install", "configure"}
        problem_terms = {"error", "problem", "issue", "bug", "fix", "solve", "broken", "failed"}
        
        keywords_lower = [kw.lower() for kw in spacy_analysis.semantic_keywords]
        features["technical_indicators"] = sum(1 for term in technical_terms if term in keywords_lower)
        features["business_indicators"] = sum(1 for term in business_terms if term in keywords_lower)
        features["procedural_indicators"] = sum(1 for term in procedural_terms if term in keywords_lower)
        features["problem_indicators"] = sum(1 for term in problem_terms if term in keywords_lower)
        
        # POS pattern analysis
        pos_patterns = spacy_analysis.pos_patterns
        features["has_imperative_verbs"] = "VERB" in pos_patterns and features["starts_with_question_word"]
        features["has_modal_verbs"] = any(pos in ["MD", "MODAL"] for pos in pos_patterns)
        
        return features
    
    def _score_intent_patterns(
        self, 
        spacy_analysis: QueryAnalysis, 
        linguistic_features: Dict[str, Any], 
        query: str
    ) -> Dict[IntentType, float]:
        """Score each intent type using pattern matching."""
        
        intent_scores = {}
        query_words = set(query.lower().split())
        keywords_set = set(kw.lower() for kw in spacy_analysis.semantic_keywords)
        
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
            question_score = self._match_question_words(query, pattern["question_words"])
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
        self, 
        query_pos: List[str], 
        target_patterns: List[List[str]]
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
    
    def _contains_pos_sequence(self, pos_tags: List[str], sequence: List[str]) -> bool:
        """Check if POS sequence exists in the query."""
        if len(sequence) > len(pos_tags):
            return False
        
        for i in range(len(pos_tags) - len(sequence) + 1):
            if pos_tags[i:i+len(sequence)] == sequence:
                return True
        
        return False
    
    def _match_entity_types(
        self, 
        query_entities: List[Tuple[str, str]], 
        target_types: Set[str]
    ) -> float:
        """Match entity types in the query."""
        if not target_types:
            return 0.0
        
        query_entity_types = set(ent[1] for ent in query_entities)
        matches = len(query_entity_types.intersection(target_types))
        
        return matches / len(target_types)
    
    def _match_question_words(self, query: str, target_words: Set[str]) -> float:
        """Match question words in the query."""
        if not target_words:
            return 0.0
        
        query_words = set(query.lower().split())
        matches = len(query_words.intersection(target_words))
        
        return matches / len(target_words)
    
    def _match_linguistic_indicators(
        self, 
        features: Dict[str, Any], 
        target_indicators: Dict[str, Any]
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
                elif isinstance(expected_value, (int, float)):
                    # For numeric indicators, use similarity
                    actual_value = features.get(indicator, 0)
                    if isinstance(actual_value, (int, float)):
                        similarity = 1.0 - abs(actual_value - expected_value) / max(expected_value, 1.0)
                        score += max(0.0, similarity)
        
        return score / max(total_indicators, 1)
    
    def _apply_behavioral_weighting(
        self, 
        intent_scores: Dict[IntentType, float], 
        behavioral_context: List[str]
    ) -> Dict[IntentType, float]:
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
            IntentType.INFORMATIONAL: [IntentType.PROCEDURAL, IntentType.TECHNICAL_LOOKUP],
            IntentType.TECHNICAL_LOOKUP: [IntentType.PROCEDURAL, IntentType.TROUBLESHOOTING],
            IntentType.BUSINESS_CONTEXT: [IntentType.VENDOR_EVALUATION, IntentType.TECHNICAL_LOOKUP],
            IntentType.VENDOR_EVALUATION: [IntentType.BUSINESS_CONTEXT, IntentType.TECHNICAL_LOOKUP],
            IntentType.PROCEDURAL: [IntentType.TROUBLESHOOTING, IntentType.TECHNICAL_LOOKUP],
            IntentType.TROUBLESHOOTING: [IntentType.PROCEDURAL, IntentType.TECHNICAL_LOOKUP]
        }
        
        most_recent_intent = previous_intents[-1]
        likely_next_intents = intent_transitions.get(most_recent_intent, [])
        
        for intent_type in likely_next_intents:
            if intent_type in weighted_scores:
                weighted_scores[intent_type] *= 1.2  # 20% boost
        
        # Apply session pattern recognition
        for pattern_name, pattern_intents in self.session_patterns.items():
            pattern_match_score = sum(
                1 for intent in previous_intents if intent in pattern_intents
            ) / len(pattern_intents)
            
            if pattern_match_score > 0.5:  # More than half of pattern matched
                for intent_type in pattern_intents:
                    if intent_type in weighted_scores:
                        weighted_scores[intent_type] *= (1.0 + pattern_match_score * 0.3)
        
        return weighted_scores
    
    def _apply_session_context(
        self, 
        intent_scores: Dict[IntentType, float], 
        session_context: Dict[str, Any]
    ) -> Dict[IntentType, float]:
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
        self, 
        intent_scores: Dict[IntentType, float]
    ) -> Tuple[IntentType, float]:
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
        self, 
        intent_scores: Dict[IntentType, float], 
        primary_intent: IntentType
    ) -> List[Tuple[IntentType, float]]:
        """Select secondary intents with meaningful confidence."""
        
        secondary_intents = []
        
        # Sort intents by score, excluding primary
        sorted_intents = sorted(
            [(intent, score) for intent, score in intent_scores.items() if intent != primary_intent],
            key=lambda x: x[1],
            reverse=True
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
        spacy_analysis: QueryAnalysis, 
        linguistic_features: Dict[str, Any], 
        intent_scores: Dict[IntentType, float]
    ) -> Dict[str, Any]:
        """Build supporting evidence for the intent classification."""
        
        return {
            "spacy_processing_time": spacy_analysis.processing_time_ms,
            "query_complexity": spacy_analysis.complexity_score,
            "semantic_keywords": spacy_analysis.semantic_keywords[:5],  # Top 5
            "extracted_entities": [ent[0] for ent in spacy_analysis.entities[:3]],  # Top 3
            "main_concepts": spacy_analysis.main_concepts[:3],  # Top 3
            "intent_signals": spacy_analysis.intent_signals,
            "linguistic_features": {
                "technical_indicators": linguistic_features.get("technical_indicators", 0),
                "business_indicators": linguistic_features.get("business_indicators", 0),
                "procedural_indicators": linguistic_features.get("procedural_indicators", 0),
                "problem_indicators": linguistic_features.get("problem_indicators", 0)
            },
            "top_intent_scores": dict(sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)[:3])
        }
    
    def clear_cache(self):
        """Clear intent classification cache."""
        self._intent_cache.clear()
        logger.debug("Cleared intent classification cache")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "intent_cache_size": len(self._intent_cache),
        }


class AdaptiveSearchStrategy:
    """Adaptive search strategy that configures search based on classified intent."""
    
    def __init__(self, knowledge_graph: Optional[DocumentKnowledgeGraph] = None):
        """Initialize the adaptive search strategy."""
        self.knowledge_graph = knowledge_graph
        self.logger = LoggingConfig.get_logger(__name__)
        
        # Define intent-specific search configurations
        self.intent_configs = {
            IntentType.TECHNICAL_LOOKUP: AdaptiveSearchConfig(
                search_strategy="hybrid",
                vector_weight=0.8,                 # Higher vector weight for semantic similarity
                keyword_weight=0.2,
                use_knowledge_graph=True,
                kg_traversal_strategy=TraversalStrategy.SEMANTIC,
                max_graph_hops=2,
                kg_expansion_weight=0.3,
                result_filters={"content_type": ["code", "documentation", "technical"]},
                ranking_boosts={"source_type": {"git": 1.4, "confluence": 1.2}},
                source_type_preferences={"git": 1.5, "documentation": 1.3},
                expand_query=True,
                expansion_aggressiveness=0.4,
                semantic_expansion=True,
                entity_expansion=True,
                max_results=25,
                min_score_threshold=0.15,
                authority_bias=0.3
            ),
            
            IntentType.BUSINESS_CONTEXT: AdaptiveSearchConfig(
                search_strategy="hybrid",
                vector_weight=0.6,                 # Balanced approach
                keyword_weight=0.4,
                use_knowledge_graph=True,
                kg_traversal_strategy=TraversalStrategy.WEIGHTED,
                max_graph_hops=3,
                kg_expansion_weight=0.2,
                result_filters={"content_type": ["requirements", "business", "strategy"]},
                ranking_boosts={"section_type": {"requirements": 1.5, "objectives": 1.4}},
                source_type_preferences={"confluence": 1.4, "documentation": 1.2},
                expand_query=True,
                expansion_aggressiveness=0.3,
                semantic_expansion=True,
                entity_expansion=False,
                max_results=20,
                min_score_threshold=0.1,
                authority_bias=0.4
            ),
            
            IntentType.VENDOR_EVALUATION: AdaptiveSearchConfig(
                search_strategy="hybrid",
                vector_weight=0.5,                 # Equal weight for structured comparison
                keyword_weight=0.5,
                use_knowledge_graph=True,
                kg_traversal_strategy=TraversalStrategy.CENTRALITY,
                max_graph_hops=2,
                kg_expansion_weight=0.25,
                result_filters={"content_type": ["proposal", "evaluation", "comparison"]},
                ranking_boosts={"has_money_entities": 1.3, "has_org_entities": 1.2},
                source_type_preferences={"confluence": 1.3, "documentation": 1.1},
                expand_query=True,
                expansion_aggressiveness=0.35,
                semantic_expansion=True,
                entity_expansion=True,
                max_results=15,
                min_score_threshold=0.12,
                diversity_factor=0.3,              # Encourage diverse vendor options
                authority_bias=0.2
            ),
            
            IntentType.PROCEDURAL: AdaptiveSearchConfig(
                search_strategy="hybrid",
                vector_weight=0.7,                 # Higher semantic matching for procedures
                keyword_weight=0.3,
                use_knowledge_graph=True,
                kg_traversal_strategy=TraversalStrategy.BREADTH_FIRST,
                max_graph_hops=2,
                kg_expansion_weight=0.2,
                result_filters={"content_type": ["guide", "tutorial", "procedure"]},
                ranking_boosts={"section_type": {"steps": 1.5, "procedure": 1.4, "guide": 1.3}},
                source_type_preferences={"documentation": 1.4, "git": 1.2},
                expand_query=True,
                expansion_aggressiveness=0.25,
                semantic_expansion=True,
                entity_expansion=False,
                max_results=15,
                min_score_threshold=0.15,
                temporal_bias=0.2                  # Prefer recent procedures
            ),
            
            IntentType.INFORMATIONAL: AdaptiveSearchConfig(
                search_strategy="vector",           # Vector-first for conceptual understanding
                vector_weight=0.9,
                keyword_weight=0.1,
                use_knowledge_graph=True,
                kg_traversal_strategy=TraversalStrategy.SEMANTIC,
                max_graph_hops=3,
                kg_expansion_weight=0.4,           # More expansion for discovery
                result_filters={},
                ranking_boosts={"section_type": {"overview": 1.4, "introduction": 1.3}},
                source_type_preferences={"documentation": 1.3, "confluence": 1.1},
                expand_query=True,
                expansion_aggressiveness=0.5,      # Aggressive expansion for discovery
                semantic_expansion=True,
                entity_expansion=True,
                max_results=30,
                min_score_threshold=0.05,
                diversity_factor=0.4,              # Encourage diverse perspectives
                authority_bias=0.3
            ),
            
            IntentType.TROUBLESHOOTING: AdaptiveSearchConfig(
                search_strategy="hybrid",
                vector_weight=0.6,
                keyword_weight=0.4,                # Higher keyword weight for specific errors
                use_knowledge_graph=True,
                kg_traversal_strategy=TraversalStrategy.WEIGHTED,
                max_graph_hops=2,
                kg_expansion_weight=0.15,
                result_filters={"content_type": ["troubleshooting", "fix", "solution"]},
                ranking_boosts={"has_problem_indicators": 1.4, "section_type": {"solution": 1.5}},
                source_type_preferences={"git": 1.3, "documentation": 1.2},
                expand_query=False,                # Don't expand error-specific queries
                expansion_aggressiveness=0.1,
                semantic_expansion=False,
                entity_expansion=False,
                max_results=10,
                min_score_threshold=0.2,
                temporal_bias=0.3                  # Prefer recent solutions
            ),
            
            IntentType.EXPLORATORY: AdaptiveSearchConfig(
                search_strategy="vector",           # Vector-first for exploration
                vector_weight=0.85,
                keyword_weight=0.15,
                use_knowledge_graph=True,
                kg_traversal_strategy=TraversalStrategy.BREADTH_FIRST,
                max_graph_hops=4,                  # Deeper exploration
                kg_expansion_weight=0.5,           # Maximum expansion
                result_filters={},
                ranking_boosts={},
                source_type_preferences={},
                expand_query=True,
                expansion_aggressiveness=0.6,      # Very aggressive expansion
                semantic_expansion=True,
                entity_expansion=True,
                max_results=40,                    # More results for exploration
                min_score_threshold=0.03,          # Lower threshold
                diversity_factor=0.6,              # Maximum diversity
                authority_bias=0.1
            ),
            
            # Fallback configuration
            IntentType.GENERAL: AdaptiveSearchConfig(
                search_strategy="hybrid",
                vector_weight=0.7,
                keyword_weight=0.3,
                use_knowledge_graph=False,
                expand_query=True,
                expansion_aggressiveness=0.3,
                semantic_expansion=True,
                entity_expansion=True,
                max_results=20,
                min_score_threshold=0.1
            )
        }
        
        logger.info("Initialized adaptive search strategy with intent-specific configurations")
    
    def adapt_search(
        self, 
        search_intent: SearchIntent, 
        query: str,
        base_results: Optional[List[SearchResult]] = None
    ) -> AdaptiveSearchConfig:
        """Adapt search configuration based on classified intent."""
        
        try:
            # Get base configuration for the primary intent
            config = self._get_base_config(search_intent.intent_type)
            
            # Apply confidence-based adjustments
            config = self._apply_confidence_adjustments(config, search_intent)
            
            # Apply secondary intent blending
            if search_intent.secondary_intents:
                config = self._blend_secondary_intents(config, search_intent.secondary_intents)
            
            # Apply query-specific adaptations
            config = self._apply_query_adaptations(config, search_intent, query)
            
            # Apply session context adaptations
            if search_intent.session_context:
                config = self._apply_session_adaptations(config, search_intent.session_context)
            
            logger.debug(
                f"Adapted search configuration for {search_intent.intent_type.value}",
                confidence=search_intent.confidence,
                vector_weight=config.vector_weight,
                use_kg=config.use_knowledge_graph,
                max_results=config.max_results
            )
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to adapt search configuration: {e}")
            return self.intent_configs[IntentType.GENERAL]
    
    def _get_base_config(self, intent_type: IntentType) -> AdaptiveSearchConfig:
        """Get base configuration for intent type."""
        return self.intent_configs.get(intent_type, self.intent_configs[IntentType.GENERAL])
    
    def _apply_confidence_adjustments(
        self, 
        config: AdaptiveSearchConfig, 
        search_intent: SearchIntent
    ) -> AdaptiveSearchConfig:
        """Apply confidence-based adjustments to the configuration."""
        
        # Low confidence: reduce aggressiveness, increase diversity
        if search_intent.confidence < 0.5:
            config.expansion_aggressiveness *= 0.7
            config.diversity_factor = min(1.0, config.diversity_factor + 0.2)
            config.min_score_threshold *= 0.8
            
        # High confidence: increase precision, reduce diversity
        elif search_intent.confidence > 0.8:
            config.expansion_aggressiveness *= 1.3
            config.diversity_factor *= 0.7
            config.min_score_threshold *= 1.2
        
        return config
    
    def _blend_secondary_intents(
        self, 
        config: AdaptiveSearchConfig, 
        secondary_intents: List[Tuple[IntentType, float]]
    ) -> AdaptiveSearchConfig:
        """Blend secondary intent configurations with primary."""
        
        for intent_type, confidence in secondary_intents:
            if confidence > 0.3:  # Only blend significant secondary intents
                secondary_config = self.intent_configs.get(intent_type)
                if secondary_config:
                    blend_factor = confidence * 0.3  # Max 30% blending
                    
                    # Blend key parameters
                    config.vector_weight = (
                        config.vector_weight * (1 - blend_factor) +
                        secondary_config.vector_weight * blend_factor
                    )
                    config.expansion_aggressiveness = (
                        config.expansion_aggressiveness * (1 - blend_factor) +
                        secondary_config.expansion_aggressiveness * blend_factor
                    )
                    config.diversity_factor = max(
                        config.diversity_factor,
                        secondary_config.diversity_factor * blend_factor
                    )
        
        return config
    
    def _apply_query_adaptations(
        self, 
        config: AdaptiveSearchConfig, 
        search_intent: SearchIntent, 
        query: str
    ) -> AdaptiveSearchConfig:
        """Apply query-specific adaptations."""
        
        # Short queries: increase expansion
        if len(query.split()) <= 3:
            config.expansion_aggressiveness *= 1.4
            config.semantic_expansion = True
            
        # Long queries: reduce expansion, increase precision
        elif len(query.split()) >= 8:
            config.expansion_aggressiveness *= 0.7
            config.min_score_threshold *= 1.2
        
        # Very complex queries: use knowledge graph more aggressively
        if search_intent.query_complexity > 0.7:
            config.use_knowledge_graph = True
            config.kg_expansion_weight *= 1.3
            config.max_graph_hops = min(4, config.max_graph_hops + 1)
        
        # Question queries: increase semantic weight
        if search_intent.is_question:
            config.vector_weight = min(0.9, config.vector_weight + 0.1)
            config.semantic_expansion = True
        
        # Technical queries: boost technical sources
        if search_intent.is_technical:
            config.source_type_preferences["git"] = config.source_type_preferences.get("git", 1.0) * 1.2
            config.authority_bias *= 1.2
        
        return config
    
    def _apply_session_adaptations(
        self, 
        config: AdaptiveSearchConfig, 
        session_context: Dict[str, Any]
    ) -> AdaptiveSearchConfig:
        """Apply session context adaptations."""
        
        # Time-sensitive sessions: increase temporal bias
        if session_context.get("urgency") == "high":
            config.temporal_bias = min(1.0, config.temporal_bias + 0.3)
            config.max_results = min(15, config.max_results)
        
        # Learning sessions: increase diversity and expansion
        session_type = session_context.get("session_type", "")
        if session_type == "learning":
            config.diversity_factor = min(1.0, config.diversity_factor + 0.2)
            config.expansion_aggressiveness *= 1.2
            config.max_results = min(30, config.max_results + 5)
        
        # Focused sessions: increase precision
        elif session_type == "focused":
            config.min_score_threshold *= 1.3
            config.expansion_aggressiveness *= 0.8
            config.max_results = max(10, config.max_results - 5)
        
        # User experience level
        experience_level = session_context.get("experience_level", "intermediate")
        if experience_level == "beginner":
            config.source_type_preferences["documentation"] = 1.4
            config.ranking_boosts["section_type"] = {"introduction": 1.5, "overview": 1.4}
        elif experience_level == "expert":
            config.source_type_preferences["git"] = 1.3
            config.ranking_boosts["section_type"] = {"implementation": 1.4, "advanced": 1.3}
        
        return config
    
    def get_strategy_stats(self) -> Dict[str, Any]:
        """Get adaptive search strategy statistics."""
        return {
            "intent_types_supported": len(self.intent_configs),
            "has_knowledge_graph": self.knowledge_graph is not None,
            "strategy_types": list(set(config.search_strategy for config in self.intent_configs.values())),
            "traversal_strategies": list(set(config.kg_traversal_strategy.value for config in self.intent_configs.values() if config.use_knowledge_graph))
        } 