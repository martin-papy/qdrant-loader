from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from qdrant_loader.core.worker.handlers import (
    BaseJobHandler,
    HandlerRegistry,
    IngestionJobHandler,
    PermanentJobError,
    TransientJobError,
    handle_cluster_recompute,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_handler(last_ingestion: datetime | None = None) -> IngestionJobHandler:
    """Return an IngestionJobHandler backed by mocks."""
    orchestrator = MagicMock()
    orchestrator.process_documents = AsyncMock()

    session_factory = MagicMock()

    history = None
    if last_ingestion is not None:
        history = MagicMock()
        history.last_successful_ingestion = last_ingestion

    handler = IngestionJobHandler(orchestrator, session_factory)
    # Patch get_last_ingestion so tests don't need a real DB
    handler._get_last_ingestion = AsyncMock(return_value=history)
    return handler


# ---------------------------------------------------------------------------
# BaseJobHandler dispatch
# ---------------------------------------------------------------------------


class ConcreteHandler(BaseJobHandler):
    def __init__(self) -> None:
        self.bulk_called_with: dict | None = None
        self.incremental_called_with: dict | None = None

    async def handle_bulk_ingest(self, payload: dict) -> None:
        self.bulk_called_with = payload

    async def handle_incremental_pull(self, payload: dict) -> None:
        self.incremental_called_with = payload


@pytest.mark.asyncio
async def test_base_handler_dispatches_bulk_ingest():
    handler = ConcreteHandler()
    payload = {"source_lock": "s1", "source_type": "git", "source": "repo"}
    await handler("BULK_INGEST", payload)
    assert handler.bulk_called_with == payload
    assert handler.incremental_called_with is None


@pytest.mark.asyncio
async def test_base_handler_dispatches_incremental_pull():
    handler = ConcreteHandler()
    payload = {"source_lock": "s1", "source_type": "git", "source": "repo"}
    await handler("INCREMENTAL_PULL", payload)
    assert handler.incremental_called_with == payload
    assert handler.bulk_called_with is None


@pytest.mark.asyncio
async def test_base_handler_raises_permanent_error_for_unknown_job_type():
    handler = ConcreteHandler()
    with pytest.raises(PermanentJobError, match="Unknown job type"):
        await handler("UNKNOWN_TYPE", {})


# ---------------------------------------------------------------------------
# _calculate_since_timestamp
# ---------------------------------------------------------------------------


def test_calculate_since_timestamp_subtracts_five_minutes():
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    result = ConcreteHandler._calculate_since_timestamp(ts)
    assert result == ts - timedelta(minutes=5)


def test_calculate_since_timestamp_returns_none_for_none():
    assert ConcreteHandler._calculate_since_timestamp(None) is None


# ---------------------------------------------------------------------------
# IngestionJobHandler.handle_bulk_ingest
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ingestion_handler_bulk_ingest_calls_orchestrator_with_force_true():
    orchestrator = MagicMock()
    orchestrator.process_documents = AsyncMock()
    handler = IngestionJobHandler(orchestrator, MagicMock())

    payload = {
        "source_lock": "confluence:space-A",
        "source_type": "confluence",
        "source": "space-A",
        "project_id": "proj-1",
    }
    await handler.handle_bulk_ingest(payload)

    orchestrator.process_documents.assert_awaited_once_with(
        source_type="confluence",
        source="space-A",
        project_id="proj-1",
        force=True,
    )


@pytest.mark.asyncio
async def test_ingestion_handler_bulk_ingest_without_project_id_raises_permanent_error():
    orchestrator = MagicMock()
    orchestrator.process_documents = AsyncMock()
    handler = IngestionJobHandler(orchestrator, MagicMock())

    with pytest.raises(PermanentJobError, match="project_id"):
        await handler.handle_bulk_ingest(
            {"source_lock": "git:repo", "source_type": "git", "source": "repo"}
        )

    orchestrator.process_documents.assert_not_awaited()


# ---------------------------------------------------------------------------
# IngestionJobHandler.handle_incremental_pull
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ingestion_handler_incremental_pull_passes_since_and_force_false(
    monkeypatch,
):
    """since = last_successful_ingestion - 5min is passed to orchestrator."""
    orchestrator = MagicMock()
    orchestrator.process_documents = AsyncMock()

    last_ts = datetime(2026, 5, 20, 10, 0, 0, tzinfo=UTC)
    expected_since = last_ts - timedelta(minutes=5)
    history = MagicMock()
    history.last_successful_ingestion = last_ts

    import qdrant_loader.core.worker.handlers as handlers_module

    monkeypatch.setattr(
        handlers_module, "get_last_ingestion", AsyncMock(return_value=history)
    )

    handler = IngestionJobHandler(orchestrator, MagicMock())
    payload = {
        "source_lock": "confluence:space-A",
        "source_type": "confluence",
        "source": "space-A",
        "project_id": "proj-1",
    }
    await handler.handle_incremental_pull(payload)

    orchestrator.process_documents.assert_awaited_once_with(
        source_type="confluence",
        source="space-A",
        project_id="proj-1",
        force=False,
        since=expected_since,
    )


@pytest.mark.asyncio
async def test_ingestion_handler_incremental_pull_no_history_passes_since_none(
    monkeypatch,
):
    """When no prior ingestion exists, since=None is passed to orchestrator."""
    orchestrator = MagicMock()
    orchestrator.process_documents = AsyncMock()

    import qdrant_loader.core.worker.handlers as handlers_module

    monkeypatch.setattr(
        handlers_module, "get_last_ingestion", AsyncMock(return_value=None)
    )

    handler = IngestionJobHandler(orchestrator, MagicMock())
    await handler.handle_incremental_pull(
        {
            "source_lock": "git:repo",
            "source_type": "git",
            "source": "repo",
            "project_id": "proj-1",
        }
    )

    orchestrator.process_documents.assert_awaited_once_with(
        source_type="git",
        source="repo",
        project_id="proj-1",
        force=False,
        since=None,
    )


@pytest.mark.asyncio
async def test_bulk_ingest_invalid_required_fields_raise_permanent_error():
    orchestrator = MagicMock()
    orchestrator.process_documents = AsyncMock()
    handler = IngestionJobHandler(orchestrator, MagicMock())

    with pytest.raises(
        PermanentJobError,
        match=r"missing or invalid required field\(s\): source",
    ):
        await handler.handle_bulk_ingest(
            {
                "source_lock": "git:repo",
                "source_type": "git",
                "source": "   ",
                "project_id": "proj-1",
            }
        )

    orchestrator.process_documents.assert_not_awaited()


@pytest.mark.asyncio
async def test_incremental_pull_invalid_required_fields_raise_permanent_error(
    monkeypatch,
):
    orchestrator = MagicMock()
    orchestrator.process_documents = AsyncMock()

    import qdrant_loader.core.worker.handlers as handlers_module

    monkeypatch.setattr(
        handlers_module, "get_last_ingestion", AsyncMock(return_value=None)
    )

    handler = IngestionJobHandler(orchestrator, MagicMock())
    with pytest.raises(PermanentJobError, match="source_type"):
        await handler.handle_incremental_pull(
            {
                "source_lock": "git:repo",
                "source": "repo",
                "project_id": "proj-1",
            }
        )

    orchestrator.process_documents.assert_not_awaited()


# ---------------------------------------------------------------------------
# HandlerRegistry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_registry_dispatches_to_registered_handler():
    registry = HandlerRegistry()
    concrete = ConcreteHandler()
    registry.register("BULK_INGEST", concrete)

    payload = {"source_lock": "s1", "source_type": "git", "source": "repo"}
    await registry.handle("BULK_INGEST", payload)
    assert concrete.bulk_called_with == payload


@pytest.mark.asyncio
async def test_registry_raises_permanent_error_for_unregistered_type():
    registry = HandlerRegistry()
    with pytest.raises(PermanentJobError, match="Unknown job type"):
        await registry.handle("NOT_REGISTERED", {})


def test_registry_list_handlers():
    registry = HandlerRegistry()
    registry.register("BULK_INGEST", ConcreteHandler())
    assert registry.list_handlers() == {"BULK_INGEST": "ConcreteHandler"}


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


def test_transient_error_is_job_handler_error():
    err = TransientJobError("retry me")
    assert isinstance(err, Exception)


def test_permanent_error_is_job_handler_error():
    err = PermanentJobError("no retry")
    assert isinstance(err, Exception)


# ---------------------------------------------------------------------------
# Error wrapping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bulk_ingest_wraps_orchestrator_exception_as_transient(monkeypatch):
    """Generic exceptions from orchestrator become TransientJobError."""
    orchestrator = MagicMock()
    orchestrator.process_documents = AsyncMock(side_effect=RuntimeError("network blip"))
    handler = IngestionJobHandler(orchestrator, MagicMock())

    with pytest.raises(TransientJobError, match="network blip"):
        await handler.handle_bulk_ingest(
            {
                "source_lock": "git:repo",
                "source_type": "git",
                "source": "repo",
                "project_id": "proj-1",
            }
        )


@pytest.mark.asyncio
async def test_bulk_ingest_reraises_permanent_error_unchanged():
    """PermanentJobError from orchestrator is not re-wrapped."""
    orchestrator = MagicMock()
    orchestrator.process_documents = AsyncMock(
        side_effect=PermanentJobError("bad config")
    )
    handler = IngestionJobHandler(orchestrator, MagicMock())

    with pytest.raises(PermanentJobError, match="bad config"):
        await handler.handle_bulk_ingest(
            {
                "source_lock": "git:repo",
                "source_type": "git",
                "source": "repo",
                "project_id": "proj-1",
            }
        )


@pytest.mark.asyncio
async def test_incremental_pull_wraps_orchestrator_exception_as_transient(monkeypatch):
    """Generic exceptions from orchestrator become TransientJobError."""
    orchestrator = MagicMock()
    orchestrator.process_documents = AsyncMock(side_effect=ConnectionError("timeout"))

    import qdrant_loader.core.worker.handlers as handlers_module

    monkeypatch.setattr(
        handlers_module, "get_last_ingestion", AsyncMock(return_value=None)
    )

    handler = IngestionJobHandler(orchestrator, MagicMock())
    with pytest.raises(TransientJobError, match="timeout"):
        await handler.handle_incremental_pull(
            {
                "source_lock": "git:repo",
                "source_type": "git",
                "source": "repo",
                "project_id": "proj-1",
            }
        )


@pytest.mark.asyncio
async def test_cluster_recompute():
    # -------------------------
    # Mock GraphStore
    # -------------------------
    class MockGraphStore:
        def __init__(self):
            self.updated = None

        async def export_graph(self):
            return (
                [{"id": "A"}, {"id": "B"}, {"id": "C"}],
                [
                    {"source": "A", "target": "B"},
                    {"source": "B", "target": "C"},
                ],
            )

        async def update_clusters_batch(self, updates):
            self.updated = updates

    # -------------------------
    # Mock DB session
    # -------------------------
    class MockSession:
        def __init__(self):
            self.queries = []
            self.committed = False

        async def execute(self, query, params):
            self.queries.append(params)

        async def commit(self):
            self.committed = True

    class MockSessionCtx:
        async def __aenter__(self):
            self.session = MockSession()
            return self.session

        async def __aexit__(self, *args):
            pass

    def session_factory():
        return MockSessionCtx()

    # -------------------------
    # Run
    # -------------------------
    graph_store = MockGraphStore()

    await handle_cluster_recompute(
        graph_store=graph_store, session_factory=session_factory
    )

    # -------------------------
    # Assertions
    # -------------------------
    assert graph_store.updated is not None
    assert len(graph_store.updated) == 3

    for u in graph_store.updated:
        assert "cluster_id" in u


@pytest.mark.asyncio
async def test_cluster_empty():
    class MockGraphStore:
        async def export_graph(self):
            return [], []

    def session_factory():
        raise AssertionError("Should not call DB")

    await handle_cluster_recompute(
        graph_store=MockGraphStore(), session_factory=session_factory
    )


@pytest.mark.asyncio
async def test_cluster_deterministic(monkeypatch):
    class MockGraphStore:
        async def export_graph(self):
            return (
                [{"id": "A"}, {"id": "B"}],
                [{"source": "A", "target": "B"}],
            )

        async def update_clusters_batch(self, updates):
            self.updates = updates

    # fake louvain
    def fake_partition(G):
        return {"A": 0, "B": 0}

    import community

    monkeypatch.setattr(community, "best_partition", fake_partition)

    class DummySession:
        async def execute(self, *a, **k):
            pass

        async def commit(self):
            pass

    class Ctx:
        async def __aenter__(self):
            return DummySession()

        async def __aexit__(self, *a):
            pass

    def session_factory():
        return Ctx()

    store = MockGraphStore()

    await handle_cluster_recompute(graph_store=store, session_factory=session_factory)

    assert store.updates[0]["cluster_id"] == 0
