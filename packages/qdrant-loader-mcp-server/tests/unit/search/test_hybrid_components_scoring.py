import pytest

from qdrant_loader_mcp_server.search.hybrid.components.scoring import (
    HybridScorer,
    ScoreComponents,
)


@pytest.mark.unit
def test_hybrid_scorer_compute_and_normalize():
    scorer = HybridScorer(vector_weight=0.6, keyword_weight=0.3, metadata_weight=0.1)
    components = ScoreComponents(vector_score=0.5, keyword_score=0.2, metadata_score=0.1)

    score = scorer.compute(components)
    assert score == pytest.approx(0.6 * 0.5 + 0.3 * 0.2 + 0.1 * 0.1)

    normalized = scorer.normalize_many([score, score * 0.5, 0.0])
    assert len(normalized) == 3
    assert normalized[0] == pytest.approx(1.0)
    assert normalized[-1] == pytest.approx(0.0)


