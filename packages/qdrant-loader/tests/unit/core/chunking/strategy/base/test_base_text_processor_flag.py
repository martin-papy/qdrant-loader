"""The _uses_base_text_processor flag gates the base TextProcessor build."""

from types import SimpleNamespace
from unittest.mock import patch

from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy


def _settings():
    # tokenizer "none" keeps base_strategy from calling tiktoken (offline-safe).
    return SimpleNamespace(
        global_config=SimpleNamespace(
            chunking=SimpleNamespace(
                chunk_size=1000,
                chunk_overlap=200,
                enable_semantic_analysis=True,
            ),
            embedding=SimpleNamespace(tokenizer="none"),
        )
    )


class _UsesProcessor(BaseChunkingStrategy):
    def chunk_document(self, document):
        return []


class _SkipsProcessor(BaseChunkingStrategy):
    _uses_base_text_processor = False

    def chunk_document(self, document):
        return []


def test_default_builds_text_processor_when_semantic_enabled():
    with patch(
        "qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"
    ) as mock_tp:
        strategy = _UsesProcessor(_settings())
        mock_tp.assert_called_once()
        assert strategy.text_processor is not None


def test_flag_false_skips_text_processor_even_when_semantic_enabled():
    with patch(
        "qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"
    ) as mock_tp:
        strategy = _SkipsProcessor(_settings())
        mock_tp.assert_not_called()
        assert strategy.text_processor is None
