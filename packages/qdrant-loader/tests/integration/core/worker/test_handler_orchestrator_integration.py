from __future__ import annotations

import sys
import types
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from qdrant_loader.core.worker.handlers import IngestionJobHandler


def _setup_qdrant_loader_core_stubs(monkeypatch: pytest.MonkeyPatch):
    """Ensure qdrant_loader_core and its submodules are importable in all environments."""
    workspace_root = Path(__file__).resolve().parents[6]
    core_src = workspace_root / "packages" / "qdrant-loader-core" / "src"
    monkeypatch.syspath_prepend(str(core_src))

    pkg = types.ModuleType("qdrant_loader_core")
    pkg.__path__ = []
    monkeypatch.setitem(sys.modules, "qdrant_loader_core", pkg)

    config_mod = types.ModuleType("qdrant_loader_core.config")
    config_mod.CollectionVectorCapabilities = object
    config_mod.SparseRuntimeConfig = object

    def _parse_collection_capabilities(*_args, **_kwargs):
        return None

    config_mod.parse_collection_capabilities = _parse_collection_capabilities
    monkeypatch.setitem(sys.modules, "qdrant_loader_core.config", config_mod)

    sparse_mod = types.ModuleType("qdrant_loader_core.sparse")

    def _get_sparse_encoder(*_args, **_kwargs):
        return None

    sparse_mod.get_sparse_encoder = _get_sparse_encoder
    monkeypatch.setitem(sys.modules, "qdrant_loader_core.sparse", sparse_mod)


@pytest.mark.asyncio
async def test_incremental_pull_accepts_since_param(monkeypatch):
    """Integration guard: handler passes `since` to orchestrator and it is accepted.

    Ensures that PipelineOrchestrator.process_documents accepts the `since` kwarg
    forwarded by IngestionJobHandler.handle_incremental_pull without raising TypeError.
    The orchestrator logs a warning (connectors not yet filtering by time) but does not
    raise.
    """
    _setup_qdrant_loader_core_stubs(monkeypatch)

    from qdrant_loader.core.pipeline.orchestrator import PipelineOrchestrator

    orchestrator = PipelineOrchestrator(
        settings=MagicMock(),
        components=MagicMock(),
        project_manager=MagicMock(),
    )
    # Stub deep enough so orchestrator.process_documents reaches
    # _stream_batches_from_sources without needing real DB/Qdrant.
    recorded_calls: list[dict[str, object]] = []

    async def fake_stream_batches(
        filtered_config,
        batch_size=256,
        since=None,
        project_id=None,
        seen_uris=None,
        resume=True,
    ):
        recorded_calls.append(
            {
                "filtered_config": filtered_config,
                "batch_size": batch_size,
                "since": since,
                "project_id": project_id,
                "seen_uris": seen_uris,
                "resume": resume,
            }
        )
        if False:
            yield

    orchestrator._stream_batches_from_sources = fake_stream_batches

    history = MagicMock()
    history.last_successful_ingestion = datetime(2026, 5, 20, 10, 0, 0, tzinfo=UTC)

    import qdrant_loader.core.worker.handlers as handlers_module

    monkeypatch.setattr(
        handlers_module, "get_last_ingestion", AsyncMock(return_value=history)
    )

    handler = IngestionJobHandler(orchestrator, session_factory=MagicMock())

    # Should complete without TypeError; `since` is accepted by orchestrator.
    await handler.handle_incremental_pull(
        {
            "source_lock": "git:repo",
            "source_type": "git",
            "source": "repo",
            "project_id": "proj-1",
        }
    )

    assert recorded_calls, "_stream_batches_from_sources was not called"
    assert recorded_calls[0]["since"] == datetime(2026, 5, 20, 9, 55, 0, tzinfo=UTC)
