"""Factory for creating enricher pipelines with default configurations.

POC2-005: Provides easy-to-use factory functions for creating enricher
pipelines with sensible defaults.
"""

from typing import TYPE_CHECKING

from .entity_enricher import EntityEnricher, EntityEnricherConfig
from .keyword_enricher import KeywordEnricher, KeywordEnricherConfig
from .pipeline import EnricherPipeline
from .base_enricher import EnricherPriority

from qdrant_loader.utils.logging import LoggingConfig

if TYPE_CHECKING:
    from qdrant_loader.config import Settings

logger = LoggingConfig.get_logger(__name__)


def create_default_pipeline(
    settings: "Settings",
    enable_entities: bool = True,
    enable_keywords: bool = True,
    parallel: bool = False,
) -> EnricherPipeline:
    """Create an enricher pipeline with default enrichers.

    This factory function creates a pipeline with commonly used enrichers
    configured with sensible defaults.

    Args:
        settings: Application settings
        enable_entities: Whether to include entity extraction (requires spaCy)
        enable_keywords: Whether to include keyword extraction
        parallel: Whether to run enrichers in parallel

    Returns:
        Configured EnricherPipeline

    Example:
        from qdrant_loader.core.enrichers.factory import create_default_pipeline

        pipeline = create_default_pipeline(settings)
        result = await pipeline.enrich(document)
    """
    enrichers = []

    if enable_keywords:
        keyword_config = KeywordEnricherConfig(
            max_keywords=20,
            include_bigrams=True,
            include_trigrams=False,
        )
        keyword_enricher = KeywordEnricher(settings, keyword_config)
        enrichers.append(keyword_enricher)
        logger.debug("Added KeywordEnricher to pipeline")

    if enable_entities:
        try:
            entity_config = EntityEnricherConfig(
                model_name="en_core_web_sm",
                extract_people=True,
                extract_organizations=True,
                extract_locations=True,
            )
            entity_enricher = EntityEnricher(settings, entity_config)
            enrichers.append(entity_enricher)
            logger.debug("Added EntityEnricher to pipeline")
        except Exception as e:
            logger.warning(
                f"Failed to initialize EntityEnricher (spaCy model may not be installed): {e}. "
                f"Entity extraction will be disabled."
            )

    pipeline = EnricherPipeline(enrichers=enrichers, parallel=parallel)
    logger.info(
        f"Created enricher pipeline with {len(enrichers)} enrichers "
        f"(parallel={parallel})"
    )

    return pipeline


def create_lightweight_pipeline(settings: "Settings") -> EnricherPipeline:
    """Create a lightweight pipeline with only keyword extraction.

    This is a faster alternative that skips entity extraction (which
    requires spaCy model loading).

    Args:
        settings: Application settings

    Returns:
        Configured EnricherPipeline with only KeywordEnricher
    """
    return create_default_pipeline(
        settings,
        enable_entities=False,
        enable_keywords=True,
        parallel=False,
    )


def create_full_pipeline(settings: "Settings") -> EnricherPipeline:
    """Create a full pipeline with all available enrichers.

    Includes both entity and keyword extraction running in parallel
    for maximum throughput.

    Args:
        settings: Application settings

    Returns:
        Configured EnricherPipeline with all enrichers
    """
    return create_default_pipeline(
        settings,
        enable_entities=True,
        enable_keywords=True,
        parallel=True,
    )
