"""Backwards-compatible re-exports for search result models."""

from .models import (
    BaseSearchResult,
    ProjectInfo,
    HierarchyInfo,
    AttachmentInfo,
    SectionInfo,
    ContentAnalysis,
    SemanticAnalysis,
    NavigationContext,
    ChunkingContext,
    ConversionInfo,
    CrossReferenceInfo,
    HybridSearchResult,
    create_hybrid_search_result,
)

__all__ = [
    "BaseSearchResult",
    "ProjectInfo",
    "HierarchyInfo",
    "AttachmentInfo",
    "SectionInfo",
    "ContentAnalysis",
    "SemanticAnalysis",
    "NavigationContext",
    "ChunkingContext",
    "ConversionInfo",
    "CrossReferenceInfo",
    "HybridSearchResult",
    "create_hybrid_search_result",
]


