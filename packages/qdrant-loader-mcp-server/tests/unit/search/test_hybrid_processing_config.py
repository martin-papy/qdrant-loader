import pytest


@pytest.mark.unit
def test_processing_config_disables_hooks_by_default(mock_qdrant_client, mock_openai_client):
    from qdrant_loader_mcp_server.search.hybrid_search import HybridSearchEngine
    from qdrant_loader_mcp_server.search.hybrid.models import HybridProcessingConfig

    engine = HybridSearchEngine(
        qdrant_client=mock_qdrant_client,
        openai_client=mock_openai_client,
        collection_name="test",
        processing_config=HybridProcessingConfig(),
    )

    assert engine.hybrid_pipeline is not None
    assert engine.hybrid_pipeline.reranker is None
    assert engine.hybrid_pipeline.booster is None
    assert engine.hybrid_pipeline.normalizer is None
    assert engine.hybrid_pipeline.deduplicator is None


@pytest.mark.unit
def test_processing_config_enables_selected_hooks(mock_qdrant_client, mock_openai_client):
    from qdrant_loader_mcp_server.search.hybrid_search import HybridSearchEngine
    from qdrant_loader_mcp_server.search.hybrid.models import HybridProcessingConfig

    engine = HybridSearchEngine(
        qdrant_client=mock_qdrant_client,
        openai_client=mock_openai_client,
        collection_name="test",
        processing_config=HybridProcessingConfig(
            enable_reranker=True, enable_booster=True, enable_normalizer=True, enable_deduplicator=True
        ),
    )

    assert engine.hybrid_pipeline is not None
    assert engine.hybrid_pipeline.reranker is not None
    assert engine.hybrid_pipeline.booster is not None
    assert engine.hybrid_pipeline.normalizer is not None
    assert engine.hybrid_pipeline.deduplicator is not None


