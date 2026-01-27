import pytest
from unittest.mock import MagicMock, patch
from qdrant_loader_mcp_server.search.hybrid.components.reranking import HybridReranker

@pytest.fixture
def sample_results():
    return [
        {"text": "doc1"},
        {"text": "doc2"},
    ]

def test_disabled_hybrid_reranker_returns_results_unchanged(sample_results):
    reranker = HybridReranker(
        enabled=False,
        model="test-model",
    )

    output = reranker.rerank("query", sample_results)

    assert output == sample_results
    assert reranker.cross_encoder is None


@patch("qdrant_loader_mcp_server.search.hybrid.components.reranking.CrossEncoderReranker")
def test_enabled_hybrid_reranker_calls_cross_encoder(
    mock_cross_encoder_cls,
    sample_results,
):
    mock_cross_encoder = MagicMock()
    mock_cross_encoder.rerank.return_value = ["reranked"]
    mock_cross_encoder_cls.return_value = mock_cross_encoder

    reranker = HybridReranker(
        enabled=True,
        model="test-model",
        device="cpu",
        batch_size=16,
    )

    output = reranker.rerank(
        query="query",
        results=sample_results,
        top_k=5,
        text_key="text",
    )

    mock_cross_encoder_cls.assert_called_once_with(
        model_name="test-model",
        device="cpu",
        batch_size=16,
        enabled=True,
    )

    mock_cross_encoder.rerank.assert_called_once_with(
        query="query",
        results=sample_results,
        top_k=5,
        text_key="text",
    )

    assert output == ["reranked"]


@patch("qdrant_loader_mcp_server.search.hybrid.components.reranking.CrossEncoderReranker")
def test_empty_results_short_circuits(
    mock_cross_encoder_cls,
):
    reranker = HybridReranker(
        enabled=True,
        model="test-model",
    )

    output = reranker.rerank("query", [])

    assert output == []
    mock_cross_encoder_cls.assert_called_once()
    reranker.cross_encoder.rerank.assert_not_called()


@patch("qdrant_loader_mcp_server.search.hybrid.components.reranking.CrossEncoderReranker")
def test_cross_encoder_none_returns_results(
    mock_cross_encoder_cls,
    sample_results,
):
    # Force cross_encoder to None after init
    reranker = HybridReranker(
        enabled=False,
        model="test-model",
    )

    reranker.cross_encoder = None

    output = reranker.rerank("query", sample_results)

    assert output == sample_results
