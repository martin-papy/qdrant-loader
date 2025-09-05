from types import SimpleNamespace


def _doc(**kwargs):
    defaults = {
        "entities": [],
        "topics": [],
        "project_id": None,
        "breadcrumb_text": "",
        "source_type": "confluence",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_strategy_selector_empty_defaults_to_mixed_features():
    from qdrant_loader_mcp_server.search.engine.strategies import (
        StrategySelector,
    )
    from qdrant_loader_mcp_server.search.enhanced.cdi import ClusteringStrategy

    selector = StrategySelector(engine=None)  # engine is not used in logic here
    assert (
        selector.select_optimal_strategy([]) == ClusteringStrategy.MIXED_FEATURES
    )


def test_strategy_selection_prefers_entity_based_with_rich_entities(monkeypatch):
    from qdrant_loader_mcp_server.search.engine.strategies import (
        StrategySelector,
    )
    from qdrant_loader_mcp_server.search.enhanced.cdi import ClusteringStrategy

    # Create documents with many entities
    docs = [_doc(entities=list(range(6))) for _ in range(5)]

    selector = StrategySelector(engine=None)

    # Make topic clarity low to avoid tie with topic strategy
    monkeypatch.setattr(
        selector,
        "analyze_document_characteristics",
        lambda d: {
            "entity_richness": 0.9,
            "topic_clarity": 0.2,
            "project_distribution": 0.0,
            "hierarchical_structure": 0.0,
            "source_diversity": 0.0,
        },
        raising=True,
    )

    strategy = selector.select_optimal_strategy(docs)
    assert strategy in {
        ClusteringStrategy.ENTITY_BASED,
        ClusteringStrategy.MIXED_FEATURES,
    }


def test_analyze_document_characteristics_edge_cases():
    from qdrant_loader_mcp_server.search.engine.strategies import (
        StrategySelector,
    )

    selector = StrategySelector(engine=None)

    # No docs case
    analysis = selector.analyze_document_characteristics([])
    assert analysis == {
        "entity_richness": 0,
        "topic_clarity": 0,
        "project_distribution": 0,
        "hierarchical_structure": 0,
        "source_diversity": 0,
    }

    # Mixed docs with breadcrumbs and projects
    docs = [
        _doc(entities=[1, 2, 3, 4, 5], topics=[1, 2, 3], project_id="p1"),
        _doc(entities=[1], topics=[1], project_id="p2", breadcrumb_text="A > B > C"),
        _doc(entities=[], topics=[], project_id="p2", breadcrumb_text="Root > Child"),
    ]
    analysis = selector.analyze_document_characteristics(docs)

    # Verify normalized ranges 0..1
    for key in (
        "entity_richness",
        "topic_clarity",
        "project_distribution",
        "hierarchical_structure",
        "source_diversity",
    ):
        assert 0 <= analysis[key] <= 1


