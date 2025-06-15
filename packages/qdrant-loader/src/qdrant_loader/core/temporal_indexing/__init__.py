"""Temporal indexing package for enhanced time-based data operations.

This package provides advanced temporal indexing capabilities for efficient
time-range queries, temporal joins, and historical data analysis.
"""

from .index_manager import TemporalIndexManager
from .index_types import (
    IndexType,
    TemporalIndex,
    TemporalIndexConfig,
    TemporalIndexStatistics,
)
from .query_optimizer import TemporalQueryOptimizer
from .btree_index import TemporalBTreeIndex
from .composite_index import TemporalCompositeIndex

__all__ = [
    "TemporalIndexManager",
    "IndexType",
    "TemporalIndex",
    "TemporalIndexConfig",
    "TemporalIndexStatistics",
    "TemporalQueryOptimizer",
    "TemporalBTreeIndex",
    "TemporalCompositeIndex",
]
