"""Data models for the enhanced hybrid search engine."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SearchMode(Enum):
    """Search mode enumeration."""

    VECTOR_ONLY = "vector_only"
    GRAPH_ONLY = "graph_only"
    HYBRID = "hybrid"
    AUTO = "auto"


class FusionStrategy(Enum):
    """Result fusion strategy enumeration."""

    WEIGHTED_SUM = "weighted_sum"
    RANK_FUSION = "rank_fusion"
    RECIPROCAL_RANK_FUSION = "reciprocal_rank_fusion"
    MMR = "maximal_marginal_relevance"
    GRAPH_ENHANCED_WEIGHTED = "graph_enhanced_weighted"
    CONFIDENCE_ADAPTIVE = "confidence_adaptive"
    MULTI_STAGE = "multi_stage"
    CONTEXT_AWARE = "context_aware"


class RerankingStrategy(Enum):
    """Reranking strategy enumeration."""

    NONE = "none"
    CROSS_ENCODER = "cross_encoder"
    DIVERSITY_MMR = "diversity_mmr"
    TEMPORAL_BOOST = "temporal_boost"
    CONTEXTUAL_BOOST = "contextual_boost"
    COMBINED = "combined"


@dataclass
class EnhancedSearchConfig:
    """Configuration for enhanced hybrid search operations."""

    # Search mode and strategy
    mode: SearchMode = SearchMode.HYBRID
    fusion_strategy: FusionStrategy = FusionStrategy.RECIPROCAL_RANK_FUSION

    # Weighting parameters
    vector_weight: float = 0.5
    keyword_weight: float = 0.2
    graph_weight: float = 0.3

    # Search limits
    vector_limit: int = 50
    graph_limit: int = 50
    final_limit: int = 10

    # Score thresholds
    min_vector_score: float = 0.3
    min_graph_score: float = 0.1
    min_combined_score: float = 0.2

    # Graph search parameters
    max_graph_depth: int = 3
    include_entity_relationships: bool = True
    include_temporal_context: bool = True
    use_graphiti: bool = True

    # Caching configuration
    enable_caching: bool = True
    cache_ttl: int = 300  # 5 minutes
    cache_max_size: int = 1000  # Maximum number of cached entries
    cache_cleanup_interval: int = 60  # Cleanup interval in seconds

    # Reranking configuration
    enable_reranking: bool = True
    rerank_top_k: int = 20
    reranking_strategy: RerankingStrategy = RerankingStrategy.COMBINED

    # Cross-encoder reranking
    cross_encoder_model: str = "openai"  # "openai" or "bge"
    cross_encoder_threshold: float = 0.5

    # Diversity reranking (MMR-style)
    diversity_lambda: float = 0.7  # Balance between relevance and diversity
    diversity_threshold: float = 0.8  # Similarity threshold for diversity filtering

    # Temporal reranking
    temporal_decay_factor: float = 0.1  # How much to decay scores based on age
    temporal_boost_recent: float = 1.2  # Boost factor for recent content
    temporal_recent_threshold_days: int = 30  # Days to consider "recent"

    # Contextual reranking
    enable_user_feedback: bool = False
    enable_query_context: bool = True
    context_boost_factor: float = 1.1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with enum values as strings for JSON serialization."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                result[key] = value.value
            else:
                result[key] = value
        return result


@dataclass
class QueryWeights:
    """Query-time weight overrides for search result fusion."""

    vector_weight: float | None = None
    keyword_weight: float | None = None
    graph_weight: float | None = None

    def __post_init__(self):
        """Validate weights after initialization."""
        if self.has_weights():
            self._validate_weights()

    def has_weights(self) -> bool:
        """Check if any weights are specified."""
        return any(
            [
                self.vector_weight is not None,
                self.keyword_weight is not None,
                self.graph_weight is not None,
            ]
        )

    def get_effective_weights(
        self, config: "EnhancedSearchConfig"
    ) -> tuple[float, float, float]:
        """Get effective weights, using query-time overrides or config defaults."""
        vector_weight = (
            self.vector_weight
            if self.vector_weight is not None
            else config.vector_weight
        )
        keyword_weight = (
            self.keyword_weight
            if self.keyword_weight is not None
            else config.keyword_weight
        )
        graph_weight = (
            self.graph_weight if self.graph_weight is not None else config.graph_weight
        )

        return vector_weight, keyword_weight, graph_weight

    def _validate_weights(self) -> None:
        """Validate that weights are within valid ranges and sum appropriately."""
        weights = []

        if self.vector_weight is not None:
            if not 0.0 <= self.vector_weight <= 1.0:
                raise ValueError(
                    f"vector_weight must be between 0.0 and 1.0, got {self.vector_weight}"
                )
            weights.append(self.vector_weight)

        if self.keyword_weight is not None:
            if not 0.0 <= self.keyword_weight <= 1.0:
                raise ValueError(
                    f"keyword_weight must be between 0.0 and 1.0, got {self.keyword_weight}"
                )
            weights.append(self.keyword_weight)

        if self.graph_weight is not None:
            if not 0.0 <= self.graph_weight <= 1.0:
                raise ValueError(
                    f"graph_weight must be between 0.0 and 1.0, got {self.graph_weight}"
                )
            weights.append(self.graph_weight)

        # If all three weights are specified, they should sum to 1.0 (with tolerance)
        if len(weights) == 3:
            total = sum(weights)
            if not 0.99 <= total <= 1.01:  # Allow small floating point tolerance
                raise ValueError(f"All three weights must sum to 1.0, got {total}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for caching and serialization."""
        return {
            "vector_weight": self.vector_weight,
            "keyword_weight": self.keyword_weight,
            "graph_weight": self.graph_weight,
        }


def validate_query_weights(
    vector_weight: float | None = None,
    keyword_weight: float | None = None,
    graph_weight: float | None = None,
) -> QueryWeights:
    """Validate and create QueryWeights instance.

    Args:
        vector_weight: Weight for vector search results (0.0-1.0)
        keyword_weight: Weight for keyword search results (0.0-1.0)
        graph_weight: Weight for graph search results (0.0-1.0)

    Returns:
        Validated QueryWeights instance

    Raises:
        ValueError: If weights are invalid
    """
    return QueryWeights(
        vector_weight=vector_weight,
        keyword_weight=keyword_weight,
        graph_weight=graph_weight,
    )


@dataclass
class EnhancedSearchResult:
    """Enhanced search result with vector, keyword, and graph components."""

    # Core result data
    id: str
    content: str
    title: str
    source_type: str

    # Scoring information
    combined_score: float
    vector_score: float = 0.0
    keyword_score: float = 0.0
    graph_score: float = 0.0
    rerank_score: float = 0.0

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    # Vector search specific
    vector_distance: float = 0.0
    embedding_model: str | None = None

    # Graph search specific
    entity_ids: list[str] = field(default_factory=list)
    relationship_types: list[str] = field(default_factory=list)
    graph_distance: int = 0
    centrality_score: float = 0.0
    temporal_relevance: float = 0.0

    # Additional context
    explanation: str | None = None
    debug_info: dict[str, Any] = field(default_factory=dict)

    def to_search_result(self):
        """Convert to standard SearchResult for API compatibility."""
        from ..models import SearchResult

        # Extract relevant fields from metadata
        return SearchResult(
            score=self.combined_score,
            text=self.content,
            source_type=self.source_type,
            source_title=self.title,
            source_url=self.metadata.get("source_url"),
            file_path=self.metadata.get("file_path"),
            repo_name=self.metadata.get("repo_name"),
            project_id=self.metadata.get("project_id"),
            project_name=self.metadata.get("project_name"),
            project_description=self.metadata.get("project_description"),
            collection_name=self.metadata.get("collection_name"),
        )
