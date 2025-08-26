"""
Core data models for intent classification and adaptive search.

This module defines the fundamental data types used throughout the intent
classification system, including intent types, search intent containers,
and adaptive search configurations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..knowledge_graph import TraversalStrategy
else:
    # Runtime import to avoid circular dependencies
    try:
        from ..knowledge_graph import TraversalStrategy
    except ImportError:
        # Fallback if knowledge_graph isn't available
        TraversalStrategy = None


# Sentinel to distinguish between an explicit None and an omitted argument
_UNSET = object()


class IntentType(Enum):
    """Types of search intents for adaptive search strategies."""

    TECHNICAL_LOOKUP = "technical_lookup"  # API docs, code examples, implementation
    BUSINESS_CONTEXT = "business_context"  # Requirements, objectives, strategy
    VENDOR_EVALUATION = "vendor_evaluation"  # Proposals, comparisons, criteria
    PROCEDURAL = "procedural"  # How-to guides, step-by-step
    INFORMATIONAL = "informational"  # What is, definitions, overviews
    EXPLORATORY = "exploratory"  # Broad discovery, browsing
    TROUBLESHOOTING = "troubleshooting"  # Error solving, debugging
    GENERAL = "general"  # Fallback for unclear intent


@dataclass
class SearchIntent:
    """Container for classified search intent with confidence and context."""

    intent_type: IntentType
    confidence: float  # 0.0 - 1.0 confidence score
    secondary_intents: list[tuple[IntentType, float]] = field(default_factory=list)

    # Linguistic evidence
    supporting_evidence: dict[str, Any] = field(default_factory=dict)
    linguistic_features: dict[str, Any] = field(default_factory=dict)

    # Context information
    query_complexity: float = 0.0  # From spaCy analysis
    is_question: bool = False
    is_technical: bool = False

    # Behavioral context
    session_context: dict[str, Any] = field(default_factory=dict)
    previous_intents: list[IntentType] = field(default_factory=list)

    # Processing metadata
    classification_time_ms: float = 0.0


@dataclass
class AdaptiveSearchConfig:
    """Configuration for adaptive search based on intent."""

    # Core search parameters
    search_strategy: str = "hybrid"  # hybrid, vector, keyword
    vector_weight: float = 0.7  # Weight for vector search
    keyword_weight: float = 0.3  # Weight for keyword search

    # Knowledge graph integration
    use_knowledge_graph: bool = False
    # Use Optional[TraversalStrategy] while leveraging a sentinel default to detect omission
    kg_traversal_strategy: TraversalStrategy | None = field(default=_UNSET)
    max_graph_hops: int = 2
    kg_expansion_weight: float = 0.2

    # Result filtering and ranking
    result_filters: dict[str, Any] = field(default_factory=dict)
    ranking_boosts: dict[str, float] = field(default_factory=dict)
    source_type_preferences: dict[str, float] = field(default_factory=dict)

    # Query expansion
    expand_query: bool = True
    expansion_aggressiveness: float = 0.3  # 0.0 - 1.0
    semantic_expansion: bool = True
    entity_expansion: bool = True

    # Performance tuning
    max_results: int = 20
    min_score_threshold: float = 0.1
    diversity_factor: float = 0.0  # 0.0 = relevance only, 1.0 = max diversity

    # Contextual parameters
    temporal_bias: float = 0.0  # Bias toward recent content
    authority_bias: float = 0.0  # Bias toward authoritative sources
    personal_bias: float = 0.0  # Bias toward user's previous interests

    def __post_init__(self):
        """Assign default TraversalStrategy only when the field was omitted.

        This preserves explicit None values provided by callers.
        """
        if self.kg_traversal_strategy is _UNSET:
            if TraversalStrategy is not None:
                self.kg_traversal_strategy = TraversalStrategy.SEMANTIC
            else:
                # If TraversalStrategy isn't available at runtime, keep as None
                self.kg_traversal_strategy = None
