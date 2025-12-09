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
    # Built-in enrichers
    "EntityEnricher",
    "EntityEnricherConfig",
    "KeywordEnricher",
    "KeywordEnricherConfig",
]
