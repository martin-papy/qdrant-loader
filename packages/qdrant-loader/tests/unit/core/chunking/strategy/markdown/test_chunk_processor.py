"""Unit tests for markdown ChunkProcessor — delegates enrichment to ChunkEnricher."""

from types import SimpleNamespace
from unittest.mock import Mock

from qdrant_loader.core.chunking.strategy.markdown.chunk_processor import ChunkProcessor


def _make_settings():
    """Disabled semantic analysis so the real ChunkEnricher builds no spaCy model."""
    return SimpleNamespace(
        global_config=SimpleNamespace(
            chunking=SimpleNamespace(
                enable_semantic_analysis=False,
                enable_enhanced_semantic_analysis=False,
                chunk_size=1200,
                strategies=SimpleNamespace(
                    markdown=SimpleNamespace(max_workers=1, estimation_buffer=0.25)
                ),
            ),
            semantic_analysis=SimpleNamespace(
                spacy_model="en_core_web_sm", num_topics=3, lda_passes=5
            ),
        )
    )


def test_process_chunk_delegates_to_enricher_with_chunk_doc_id():
    processor = ChunkProcessor(_make_settings())
    try:
        processor._enricher = Mock()
        processor._enricher.enrich.return_value = {
            "entities": [{"text": "X"}],
            "topics": [],
            "key_phrases": [],
        }
        result = processor.process_chunk("some text", 2, 5)
        processor._enricher.enrich.assert_called_once_with(
            "some text", doc_id="chunk_2"
        )
        assert result == {"entities": [{"text": "X"}], "topics": [], "key_phrases": []}
    finally:
        processor.shutdown()


def test_process_chunk_caches_result_by_chunk_text():
    processor = ChunkProcessor(_make_settings())
    try:
        processor._enricher = Mock()
        processor._enricher.enrich.return_value = {
            "entities": [],
            "topics": [],
            "key_phrases": [],
        }
        processor.process_chunk("text-a", 0, 1)
        assert "text-a" in processor._processed_chunks
    finally:
        processor.shutdown()


def test_disabled_settings_build_enricher_without_analyzer():
    processor = ChunkProcessor(_make_settings())
    try:
        assert processor._enricher.enabled is False
    finally:
        processor.shutdown()
