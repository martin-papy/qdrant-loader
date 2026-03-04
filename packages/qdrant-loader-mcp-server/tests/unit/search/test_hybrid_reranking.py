"""
Test the hybrid reranker with the CrossEncoderReranker and WRRF algorithm.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from qdrant_loader_mcp_server.search.hybrid.components.reranking import HybridReranker


@pytest.mark.unit
def test_disabled_reranker_returns_results_unchanged():
    """
    Test that a disabled reranker returns results unchanged.
    """
    reranker = HybridReranker(enabled=False, model="test-model")
    items = [SimpleNamespace(text="a", score=0.2), SimpleNamespace(text="b", score=0.8)]

    out = reranker.rerank(query="test query", results=items)

    assert out == items
    assert reranker.cross_encoder is None


@pytest.mark.unit
@patch(
    "qdrant_loader_mcp_server.search.hybrid.components.reranking.CrossEncoderReranker"
)
def test_enabled_reranker_delegates_to_cross_encoder(mock_cross_encoder_cls):
    """
    Test that an enabled reranker delegates to the cross encoder.
    Args:
        mock_cross_encoder_cls: Mock cross encoder class
    Returns:
        None
    """
    mock_cross_encoder = MagicMock()
    mock_cross_encoder.rerank.return_value = ["reranked_result"]
    mock_cross_encoder_cls.return_value = mock_cross_encoder

    reranker = HybridReranker(
        enabled=True, model="test-model", device="cpu", batch_size=16
    )
    items = [SimpleNamespace(text="a", score=0.5)]

    out = reranker.rerank(query="test query", results=items, top_k=5, text_key="text")

    mock_cross_encoder.rerank.assert_called_once_with(
        query="test query",
        results=items,
        top_k=5,
        text_key="text",
    )
    assert out == ["reranked_result"]


@pytest.mark.unit
@patch(
    "qdrant_loader_mcp_server.search.hybrid.components.reranking.CrossEncoderReranker"
)
def test_empty_results_returns_empty(mock_cross_encoder_cls):
    """
    Test that an empty results list returns an empty list.
    Args:
        mock_cross_encoder_cls: Mock cross encoder class
    Returns:
        None
    """
    mock_cross_encoder_cls.return_value = MagicMock()

    reranker = HybridReranker(enabled=True, model="test-model")

    out = reranker.rerank(query="test query", results=[])

    assert out == []


@pytest.mark.unit
@patch(
    "qdrant_loader_mcp_server.search.hybrid.components.reranking.CrossEncoderReranker"
)
def test_none_cross_encoder_returns_results_unchanged(mock_cross_encoder_cls):
    """
    Test that a none cross encoder returns results unchanged.
    Args:
        mock_cross_encoder_cls: Mock cross encoder class
    Returns:
        None
    """
    mock_cross_encoder_cls.return_value = MagicMock()

    reranker = HybridReranker(enabled=False, model="test-model")
    reranker.cross_encoder = None
    items = [SimpleNamespace(text="a", score=0.5)]

    out = reranker.rerank(query="test query", results=items)

    assert out == items
