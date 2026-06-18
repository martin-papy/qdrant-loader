"""Unit tests for ChunkEnricher — the shared chunk NLP enrichment contract."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from qdrant_loader.core.text_processing.chunk_enricher import ChunkEnricher

PATCH_TARGET = "qdrant_loader.core.text_processing.chunk_enricher.SemanticAnalyzer"


def _make_settings(*, enable_semantic_analysis, enable_enhanced_semantic_analysis):
    return SimpleNamespace(
        global_config=SimpleNamespace(
            chunking=SimpleNamespace(
                enable_semantic_analysis=enable_semantic_analysis,
                enable_enhanced_semantic_analysis=enable_enhanced_semantic_analysis,
            ),
            semantic_analysis=SimpleNamespace(
                spacy_model="en_core_web_sm",
                num_topics=3,
                lda_passes=5,
            ),
        )
    )


def _analysis_result():
    r = Mock()
    r.entities = [{"text": "Apple", "label": "ORG"}]
    r.topics = [{"id": 0}]
    r.key_phrases = ["Apple Inc"]
    r.pos_tags = [{"text": "Apple", "pos": "NOUN"}]
    r.dependencies = [{"text": "Apple", "dep": "nsubj"}]
    r.document_similarity = {"doc1": 0.8}
    return r


def test_disabled_builds_no_analyzer_and_returns_empty_shape():
    settings = _make_settings(
        enable_semantic_analysis=False, enable_enhanced_semantic_analysis=False
    )
    with patch(PATCH_TARGET) as mock_analyzer:
        enricher = ChunkEnricher(settings)
        mock_analyzer.assert_not_called()
        assert enricher.enabled is False
        assert enricher.enrich("text", doc_id="c0") == {
            "entities": [],
            "topics": [],
            "key_phrases": [],
        }


def test_enabled_constructs_analyzer_with_config():
    settings = _make_settings(
        enable_semantic_analysis=True, enable_enhanced_semantic_analysis=False
    )
    with patch(PATCH_TARGET) as mock_analyzer:
        enricher = ChunkEnricher(settings)
        mock_analyzer.assert_called_once_with(
            spacy_model="en_core_web_sm", num_topics=3, passes=5
        )
        assert enricher.enabled is True


def test_enrich_default_tier_omits_enhanced_fields():
    settings = _make_settings(
        enable_semantic_analysis=True, enable_enhanced_semantic_analysis=False
    )
    with patch(PATCH_TARGET) as mock_analyzer:
        mock_analyzer.return_value.analyze_text.return_value = _analysis_result()
        enricher = ChunkEnricher(settings)
        result = enricher.enrich("Apple builds products", doc_id="c0")
        mock_analyzer.return_value.analyze_text.assert_called_once_with(
            "Apple builds products", doc_id="c0", include_enhanced=False
        )
        assert set(result) == {"entities", "topics", "key_phrases"}


def test_enrich_enhanced_tier_includes_enhanced_fields():
    settings = _make_settings(
        enable_semantic_analysis=True, enable_enhanced_semantic_analysis=True
    )
    with patch(PATCH_TARGET) as mock_analyzer:
        mock_analyzer.return_value.analyze_text.return_value = _analysis_result()
        enricher = ChunkEnricher(settings)
        result = enricher.enrich("Apple builds products", doc_id="c1")
        mock_analyzer.return_value.analyze_text.assert_called_once_with(
            "Apple builds products", doc_id="c1", include_enhanced=True
        )
        assert {"pos_tags", "dependencies", "document_similarity"} <= set(result)


def test_enrich_swallows_analyzer_errors_and_returns_empty_shape():
    settings = _make_settings(
        enable_semantic_analysis=True, enable_enhanced_semantic_analysis=False
    )
    with patch(PATCH_TARGET) as mock_analyzer:
        mock_analyzer.return_value.analyze_text.side_effect = RuntimeError("boom")
        enricher = ChunkEnricher(settings)
        result = enricher.enrich("text", doc_id="c0")
        assert result == {"entities": [], "topics": [], "key_phrases": []}


def test_empty_shape_results_do_not_share_list_instances():
    settings = _make_settings(
        enable_semantic_analysis=False, enable_enhanced_semantic_analysis=False
    )
    with patch(PATCH_TARGET):
        enricher = ChunkEnricher(settings)
        a = enricher.enrich("x", doc_id="a")
        b = enricher.enrich("y", doc_id="b")
        a["entities"].append("mutated")
        assert b["entities"] == []
