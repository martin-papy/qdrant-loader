from types import SimpleNamespace

import pytest


def _r(id, st, title, sec, score):
    return SimpleNamespace(
        document_id=id,
        source_type=st,
        source_title=title,
        section_type=sec,
        section_title=title,
        score=score,
    )


def test_apply_diversity_filtering_basic():
    from qdrant_loader_mcp_server.search.hybrid.components.diversity import (
        apply_diversity_filtering,
    )

    results = [
        _r("1", "confluence", "A", "doc", 1.0),
        _r("2", "confluence", "B", "doc", 0.9),
        _r("3", "jira", "C", "ticket", 0.8),
        _r("4", "git", "D", "code", 0.7),
    ]

    out = apply_diversity_filtering(results, diversity_factor=0.5, limit=3)
    assert len(out) == 3
    # Should promote variety in source types
    assert {r.source_type for r in out} >= {"confluence", "jira"}


def test_apply_diversity_filtering_edge_cases():
    from qdrant_loader_mcp_server.search.hybrid.components.diversity import (
        apply_diversity_filtering,
    )

    # No penalty if diversity_factor is 0 or results fit within limit
    r = [_r("1", "confluence", "A", "doc", 1.0)]
    assert apply_diversity_filtering(r, diversity_factor=0.0, limit=5) == r

    # Invalid factor
    with pytest.raises(ValueError):
        apply_diversity_filtering(r, diversity_factor=2.0, limit=1)


