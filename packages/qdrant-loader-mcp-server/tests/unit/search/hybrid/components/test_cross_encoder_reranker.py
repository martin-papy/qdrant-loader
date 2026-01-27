import pytest
from unittest.mock import MagicMock, patch

from qdrant_loader_mcp_server.search.hybrid.components.cross_encoder_reranker import CrossEncoderReranker

class DummyResult:
    def __init__(self, text):
        self.text = text

@pytest.fixture
def mock_cross_encoder():
    """Mock CrossEncoder instance."""
    mock = MagicMock()
    mock.predict.return_value = [0.2, 0.9, 0.5]
    return mock

@patch("qdrant_loader_mcp_server.search.hybrid.components.cross_encoder_reranker.CrossEncoder")
def test_disabled_reranker_returns_results_unchanged(mock_ce):
    reranker = CrossEncoderReranker(
        model_name="test-model",
        enabled=False,
    )

    results = [{"text": "a"}, {"text": "b"}]
    output = reranker.rerank("query", results)

    assert output == results
    mock_ce.assert_not_called()

@patch("qdrant_loader_mcp_server.search.hybrid.components.cross_encoder_reranker.CrossEncoder")
def test_model_loads_once(mock_ce, mock_cross_encoder):
    mock_ce.return_value = mock_cross_encoder

    reranker = CrossEncoderReranker("test-model")

    results = [{"text": "a"}]
    reranker.rerank("query", results)
    reranker.rerank("query", results)

    mock_ce.assert_called_once_with("test-model", device="cpu")


@patch("qdrant_loader_mcp_server.search.hybrid.components.cross_encoder_reranker.CrossEncoder")
def test_rerank_sorts_results_by_score(mock_ce, mock_cross_encoder):
    mock_ce.return_value = mock_cross_encoder

    reranker = CrossEncoderReranker("test-model")

    results = [
        {"text": "first"},
        {"text": "second"},
        {"text": "third"},
    ]

    output = reranker.rerank("query", results)

    assert output[0]["text"] == "second"
    assert output[1]["text"] == "third"
    assert output[2]["text"] == "first"

    assert output[0]["cross_encoder_rank"] == 1
    assert output[0]["cross_encoder_score"] == 0.9


@patch("qdrant_loader_mcp_server.search.hybrid.components.cross_encoder_reranker.CrossEncoder")
def test_top_k_is_respected(mock_ce, mock_cross_encoder):
    mock_ce.return_value = mock_cross_encoder

    reranker = CrossEncoderReranker("test-model")

    results = [
        {"text": "a"},
        {"text": "b"},
        {"text": "c"},
    ]

    output = reranker.rerank("query", results, top_k=2)

    assert len(output) == 2
    assert output[0]["cross_encoder_rank"] == 1
    assert output[1]["cross_encoder_rank"] == 2


@patch("qdrant_loader_mcp_server.search.hybrid.components.cross_encoder_reranker.CrossEncoder")
def test_object_results_supported(mock_ce, mock_cross_encoder):
    mock_ce.return_value = mock_cross_encoder

    reranker = CrossEncoderReranker("test-model")

    results = [
        DummyResult("one"),
        DummyResult("two"),
        DummyResult("three"),
    ]

    output = reranker.rerank("query", results)

    assert hasattr(output[0], "cross_encoder_score")
    assert hasattr(output[0], "cross_encoder_rank")
    assert output[0].cross_encoder_rank == 1


@patch("qdrant_loader_mcp_server.search.hybrid.components.cross_encoder_reranker.CrossEncoder")
def test_extract_texts_empty_results_short_circuit(mock_ce, mock_cross_encoder):
    mock_ce.return_value = mock_cross_encoder

    reranker = CrossEncoderReranker("test-model")

    results = [{"text": ""}, {"text": "   "}]

    output = reranker.rerank("query", results)

    assert output == results
    mock_cross_encoder.predict.assert_not_called()


@patch("qdrant_loader_mcp_server.search.hybrid.components.cross_encoder_reranker.CrossEncoder")
def test_model_failure_disables_reranker(mock_ce):
    mock_ce.side_effect = RuntimeError("boom")

    reranker = CrossEncoderReranker("test-model")

    results = [{"text": "hello"}]
    output = reranker.rerank("query", results)

    assert output == results
    assert reranker.enabled is False
    assert reranker.model is None


@patch("qdrant_loader_mcp_server.search.hybrid.components.cross_encoder_reranker.CrossEncoder")
def test_predict_exception_returns_original_results(mock_ce, mock_cross_encoder):
    mock_cross_encoder.predict.side_effect = RuntimeError("predict failed")
    mock_ce.return_value = mock_cross_encoder

    reranker = CrossEncoderReranker("test-model")

    results = [{"text": "a"}, {"text": "b"}]
    output = reranker.rerank("query", results)

    assert output == results
