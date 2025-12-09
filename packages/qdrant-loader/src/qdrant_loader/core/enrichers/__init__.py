"""Pluggable metadata enrichers for document processing.

POC2: LlamaIndex-style Pluggable Enricher Pipeline

This module provides a flexible, plugin-based enrichment system that allows
users to configure and chain metadata enrichers. Enrichers process documents
and chunks to extract and add structured metadata.

Architecture:
- BaseEnricher: Abstract interface all enrichers must implement
- EnricherPipeline: Orchestrates running multiple enrichers in sequence
- Built-in enrichers: Entity, Keyword, Hierarchy, Custom

Example usage:
    # Option 1: Use factory for quick setup
    from qdrant_loader.core.enrichers import create_default_pipeline

    pipeline = create_default_pipeline(settings)
    result = await pipeline.enrich(document)

    # Option 2: Manual configuration
    from qdrant_loader.core.enrichers import (
        EnricherPipeline,
        EntityEnricher,
        KeywordEnricher,
    )

    pipeline = EnricherPipeline([
        EntityEnricher(settings),
        KeywordEnricher(settings),
    ])

    enriched_doc = await pipeline.enrich(document)
"""

from .base_enricher import BaseEnricher, EnricherConfig, EnricherPriority, EnricherResult
from .entity_enricher import EntityEnricher, EntityEnricherConfig
from .factory import create_default_pipeline, create_full_pipeline, create_lightweight_pipeline
from .keyword_enricher import KeywordEnricher, KeywordEnricherConfig
from .pipeline import EnricherPipeline, PipelineResult

__all__ = [
    # Base classes
    "BaseEnricher",
    "EnricherConfig",
    "EnricherPriority",
    "EnricherResult",
    # Pipeline
    "EnricherPipeline",
    "PipelineResult",
    # Factory functions
    "create_default_pipeline",
    "create_full_pipeline",
    "create_lightweight_pipeline",
    # Built-in enrichers
    "EntityEnricher",
    "EntityEnricherConfig",
    "KeywordEnricher",
    "KeywordEnricherConfig",
]
