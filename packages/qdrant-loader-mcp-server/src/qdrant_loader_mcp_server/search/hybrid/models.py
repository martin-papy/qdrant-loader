from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HybridStage(Enum):
    VECTOR = "vector"
    KEYWORD = "keyword"
    METADATA = "metadata"
    COMBINE = "combine"


# Default constants (single source of truth for defaults)
DEFAULT_VECTOR_WEIGHT: float = 0.6
DEFAULT_KEYWORD_WEIGHT: float = 0.3
DEFAULT_METADATA_WEIGHT: float = 0.1
DEFAULT_MIN_SCORE: float = 0.3


@dataclass
class HybridWeights:
    vector_weight: float = DEFAULT_VECTOR_WEIGHT
    keyword_weight: float = DEFAULT_KEYWORD_WEIGHT
    metadata_weight: float = DEFAULT_METADATA_WEIGHT


@dataclass
class HybridProcessingConfig:
    enable_booster: bool = False
    enable_normalizer: bool = False
    enable_deduplicator: bool = False
    enable_reranker: bool = False
