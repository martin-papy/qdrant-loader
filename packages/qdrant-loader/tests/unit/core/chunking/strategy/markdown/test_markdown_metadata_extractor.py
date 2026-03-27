"""Tests for markdown metadata extractor semantic toggle behavior."""

from unittest.mock import Mock

from qdrant_loader.core.chunking.strategy.markdown.metadata_extractor import (
    MetadataExtractor,
)


def _build_settings(enable_semantic_analysis: bool):
    settings = Mock()
    settings.global_config = Mock()
    settings.global_config.chunking = Mock()
    settings.global_config.chunking.enable_semantic_analysis = enable_semantic_analysis
    settings.global_config.chunking.strategies = Mock()
    settings.global_config.chunking.strategies.markdown = Mock()
    settings.global_config.chunking.strategies.markdown.words_per_minute_reading = 200
    return settings


def test_extract_all_metadata_semantic_disabled_returns_no_entities_or_topics():
    settings = _build_settings(enable_semantic_analysis=False)
    extractor = MetadataExtractor(settings)

    metadata = extractor.extract_all_metadata(
        "This is a sample text with Microsoft and Apple.",
        {"title": "Section"},
    )

    assert metadata["entities"] == []
    assert metadata["topic_analysis"] == {"topics": [], "coherence": 0.0}


def test_extract_all_metadata_semantic_enabled_keeps_entity_extraction():
    settings = _build_settings(enable_semantic_analysis=True)
    extractor = MetadataExtractor(settings)

    metadata = extractor.extract_all_metadata(
        "This is a sample text with Microsoft and Apple.",
        {"title": "Section"},
    )

    assert isinstance(metadata["entities"], list)
    assert len(metadata["entities"]) > 0
    assert metadata["topic_analysis"]["topics"] == ["general"]
