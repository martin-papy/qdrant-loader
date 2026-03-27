"""Unit tests for markdown ChunkProcessor semantic-analysis flags."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from qdrant_loader.core.chunking.strategy.markdown.chunk_processor import ChunkProcessor


def _make_settings(
    *,
    enable_semantic_analysis: bool,
    enable_enhanced_semantic_analysis: bool,
):
    """Build minimal settings object required by ChunkProcessor."""
    return SimpleNamespace(
        global_config=SimpleNamespace(
            chunking=SimpleNamespace(
                enable_semantic_analysis=enable_semantic_analysis,
                enable_enhanced_semantic_analysis=enable_enhanced_semantic_analysis,
                chunk_size=1200,
                strategies=SimpleNamespace(
                    markdown=SimpleNamespace(max_workers=1, estimation_buffer=0.25)
                ),
            ),
            semantic_analysis=SimpleNamespace(
                spacy_model="en_core_web_sm",
                num_topics=3,
                lda_passes=5,
            ),
        )
    )


def test_init_skips_semantic_analyzer_when_semantic_disabled():
    settings = _make_settings(
        enable_semantic_analysis=False,
        enable_enhanced_semantic_analysis=False,
    )

    with patch(
        "qdrant_loader.core.chunking.strategy.markdown.chunk_processor.SemanticAnalyzer"
    ) as mock_analyzer:
        processor = ChunkProcessor(settings)
        try:
            assert processor.semantic_analyzer is None
            mock_analyzer.assert_not_called()
        finally:
            processor.shutdown()


def test_init_creates_semantic_analyzer_when_semantic_enabled():
    settings = _make_settings(
        enable_semantic_analysis=True,
        enable_enhanced_semantic_analysis=False,
    )

    with patch(
        "qdrant_loader.core.chunking.strategy.markdown.chunk_processor.SemanticAnalyzer"
    ) as mock_analyzer:
        processor = ChunkProcessor(settings)
        try:
            mock_analyzer.assert_called_once_with(
                spacy_model="en_core_web_sm",
                num_topics=3,
                passes=5,
            )
        finally:
            processor.shutdown()


def test_process_chunk_uses_base_semantic_fields_when_enhanced_disabled():
    settings = _make_settings(
        enable_semantic_analysis=True,
        enable_enhanced_semantic_analysis=False,
    )

    analysis_result = Mock()
    analysis_result.entities = [{"text": "Apple", "label": "ORG"}]
    analysis_result.topics = [{"id": 0}]
    analysis_result.key_phrases = ["Apple Inc"]
    analysis_result.pos_tags = [{"text": "Apple", "pos": "NOUN"}]
    analysis_result.dependencies = [{"text": "Apple", "dep": "nsubj"}]
    analysis_result.document_similarity = {"doc1": 0.8}

    with patch(
        "qdrant_loader.core.chunking.strategy.markdown.chunk_processor.SemanticAnalyzer"
    ) as mock_analyzer:
        mock_analyzer.return_value.analyze_text.return_value = analysis_result
        processor = ChunkProcessor(settings)
        try:
            result = processor.process_chunk("Apple builds products", 0, 1)

            processor.semantic_analyzer.analyze_text.assert_called_once_with(
                "Apple builds products",
                doc_id="chunk_0",
                include_enhanced=False,
            )
            assert "entities" in result
            assert "topics" in result
            assert "key_phrases" in result
            assert "pos_tags" not in result
            assert "dependencies" not in result
            assert "document_similarity" not in result
        finally:
            processor.shutdown()


def test_process_chunk_includes_enhanced_fields_when_enhanced_enabled():
    settings = _make_settings(
        enable_semantic_analysis=True,
        enable_enhanced_semantic_analysis=True,
    )

    analysis_result = Mock()
    analysis_result.entities = [{"text": "Apple", "label": "ORG"}]
    analysis_result.topics = [{"id": 0}]
    analysis_result.key_phrases = ["Apple Inc"]
    analysis_result.pos_tags = [{"text": "Apple", "pos": "NOUN"}]
    analysis_result.dependencies = [{"text": "Apple", "dep": "nsubj"}]
    analysis_result.document_similarity = {"doc1": 0.8}

    with patch(
        "qdrant_loader.core.chunking.strategy.markdown.chunk_processor.SemanticAnalyzer"
    ) as mock_analyzer:
        mock_analyzer.return_value.analyze_text.return_value = analysis_result
        processor = ChunkProcessor(settings)
        try:
            result = processor.process_chunk("Apple builds products", 1, 3)

            processor.semantic_analyzer.analyze_text.assert_called_once_with(
                "Apple builds products",
                doc_id="chunk_1",
                include_enhanced=True,
            )
            assert "pos_tags" in result
            assert "dependencies" in result
            assert "document_similarity" in result
        finally:
            processor.shutdown()


def test_process_chunk_returns_empty_semantic_data_when_semantic_disabled():
    settings = _make_settings(
        enable_semantic_analysis=False,
        enable_enhanced_semantic_analysis=False,
    )

    with patch(
        "qdrant_loader.core.chunking.strategy.markdown.chunk_processor.SemanticAnalyzer"
    ):
        processor = ChunkProcessor(settings)
        try:
            result = processor.process_chunk("Plain text", 0, 1)
            assert result == {"entities": [], "topics": [], "key_phrases": []}
        finally:
            processor.shutdown()
