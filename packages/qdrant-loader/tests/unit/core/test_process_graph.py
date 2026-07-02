from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from qdrant_loader.core.pipeline.document_pipeline import DocumentPipeline
from qdrant_loader_core.graph.extractor.base_extractor import EntityExtractor


@pytest.fixture
def pipeline():
    return DocumentPipeline(
        chunking_worker=MagicMock(),
        embedding_worker=MagicMock(),
        upsert_worker=MagicMock(),
    )


@pytest.fixture
def document():
    return SimpleNamespace(
        id="doc-1",
        source_type="jira",
    )


def mock_settings(enabled: bool):
    return SimpleNamespace(
        global_config=SimpleNamespace(
            graph=SimpleNamespace(enabled=enabled),
        )
    )


@pytest.mark.asyncio
async def test_process_graph_disabled_returns_early(
    monkeypatch,
    pipeline,
    document,
):
    monkeypatch.setattr(
        "qdrant_loader.core.pipeline.document_pipeline.get_settings",
        lambda: mock_settings(False),
    )

    get_graph_store = AsyncMock()
    monkeypatch.setattr(
        "qdrant_loader.core.pipeline.document_pipeline.get_graph_store",
        get_graph_store,
    )

    await pipeline._process_graph([document])

    get_graph_store.assert_not_called()


@pytest.mark.asyncio
async def test_process_graph_settings_failure_disables_graph(
    monkeypatch,
    pipeline,
    document,
):
    def raise_settings():
        raise RuntimeError("boom")

    mock_logger = MagicMock()

    monkeypatch.setattr(
        "qdrant_loader.core.pipeline.document_pipeline.logger",
        mock_logger,
    )

    monkeypatch.setattr(
        "qdrant_loader.core.pipeline.document_pipeline.get_settings",
        raise_settings,
    )

    monkeypatch.setattr(
        "qdrant_loader.core.pipeline.document_pipeline.EntityExtractor.for_source",
        lambda _: None,
    )

    await pipeline._process_graph([document])

    mock_logger.warning.assert_called_once_with(
        "Graph config not available → graph disabled"
    )


@pytest.mark.asyncio
async def test_process_graph_missing_extractor_logs_warning(
    monkeypatch,
    pipeline,
    document,
):
    mock_logger = MagicMock()

    monkeypatch.setattr(
        "qdrant_loader.core.pipeline.document_pipeline.logger",
        mock_logger,
    )

    monkeypatch.setattr(
        "qdrant_loader.core.pipeline.document_pipeline.get_settings",
        lambda: mock_settings(True),
    )

    monkeypatch.setattr(
        "qdrant_loader.core.pipeline.document_pipeline.EntityExtractor.for_source",
        lambda _: None,
    )

    await pipeline._process_graph([document])

    mock_logger.warning.assert_called_once_with(
        "No extractor found for source_type=%s",
        "jira",
    )


@pytest.mark.asyncio
async def test_process_graph_writes_nodes_and_edges(
    monkeypatch,
    pipeline,
    document,
):
    monkeypatch.setattr(
        "qdrant_loader.core.pipeline.document_pipeline.get_settings",
        lambda: mock_settings(True),
    )

    node = SimpleNamespace(
        id="node-1",
        properties={},
    )

    edge = SimpleNamespace(
        source="a",
        target="b",
        edge_type="RELATES_TO",
        properties={},
    )

    subgraph = SimpleNamespace(
        nodes=[node],
        edges=[edge],
    )

    extractor = MagicMock()
    extractor.extract = AsyncMock(return_value=subgraph)

    monkeypatch.setattr(
        EntityExtractor,
        "for_source",
        lambda _: extractor,
    )

    graph_store = AsyncMock()

    monkeypatch.setattr(
        "qdrant_loader.core.pipeline.document_pipeline.get_graph_store",
        AsyncMock(return_value=graph_store),
    )

    await pipeline._process_graph(
        [document],
        current_project_id="project-123",
    )

    graph_store.upsert_nodes_batch.assert_called_once()
    graph_store.upsert_edges_batch.assert_called_once()

    assert node.properties["project"] == "project-123"
    assert edge.properties["project"] == "project-123"


@pytest.mark.asyncio
async def test_process_graph_empty_subgraph_skips_upsert(
    monkeypatch,
    pipeline,
    document,
):
    monkeypatch.setattr(
        "qdrant_loader.core.pipeline.document_pipeline.get_settings",
        lambda: mock_settings(True),
    )

    extractor = MagicMock()
    extractor.extract = AsyncMock(
        return_value=SimpleNamespace(
            nodes=[],
            edges=[],
        )
    )

    monkeypatch.setattr(
        EntityExtractor,
        "for_source",
        lambda _: None,
    )

    get_graph_store = AsyncMock()

    monkeypatch.setattr(
        "qdrant_loader.core.pipeline.document_pipeline.get_graph_store",
        get_graph_store,
    )

    await pipeline._process_graph([document])

    get_graph_store.assert_not_called()
