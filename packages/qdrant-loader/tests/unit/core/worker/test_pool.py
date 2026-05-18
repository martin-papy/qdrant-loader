from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import pytest_asyncio
from qdrant_loader.config.state import StateManagementConfig
from qdrant_loader.core.state.session import (
    create_tables,
    dispose_engine,
    initialize_engine_and_session,
)
from qdrant_loader.core.worker.pool import QueueWorkerPool
from qdrant_loader.core.worker.queue import SQLiteJobQueue


@pytest_asyncio.fixture
async def sqlite_job_queue(tmp_path: Path):
    db_path = tmp_path / "worker_pool.db"
    config = StateManagementConfig(database_path=str(db_path))
    engine, session_factory = initialize_engine_and_session(config)
    await create_tables(engine)

    queue = SQLiteJobQueue(session_factory)
    try:
        yield queue
    finally:
        await dispose_engine(engine)


@pytest.mark.asyncio
async def test_worker_pool_processes_queue_with_four_workers(sqlite_job_queue: SQLiteJobQueue):
    total_jobs = 100
    for i in range(total_jobs):
        await sqlite_job_queue.enqueue("INCREMENTAL_PULL", {"source": f"source-{i}"})

    in_flight = 0
    max_in_flight = 0
    guard = asyncio.Lock()

    async def handler(_job_type: str, _payload: dict[str, str]) -> None:
        nonlocal in_flight, max_in_flight
        async with guard:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)

        await asyncio.sleep(0.005)

        async with guard:
            in_flight -= 1

    pool = QueueWorkerPool(sqlite_job_queue, handler=handler, worker_count=4)
    processed = await pool.run_until_empty()

    done_jobs = await sqlite_job_queue.list(status=SQLiteJobQueue.DONE)
    failed_jobs = await sqlite_job_queue.list(status=SQLiteJobQueue.FAILED)

    assert processed == total_jobs
    assert len(done_jobs) == total_jobs
    assert len(failed_jobs) == 0
    assert max_in_flight <= 4


@pytest.mark.asyncio
async def test_worker_pool_uses_per_source_lock(sqlite_job_queue: SQLiteJobQueue):
    total_jobs = 20
    sources = ("jira-main", "confluence-main")
    for i in range(total_jobs):
        await sqlite_job_queue.enqueue("BULK_INGEST", {"source": sources[i % 2]})

    active_by_source: dict[str, int] = {}
    max_by_source: dict[str, int] = {}
    guard = asyncio.Lock()

    async def handler(_job_type: str, payload: dict[str, str]) -> None:
        source = payload["source"]

        async with guard:
            active_now = active_by_source.get(source, 0) + 1
            active_by_source[source] = active_now
            max_by_source[source] = max(max_by_source.get(source, 0), active_now)

        await asyncio.sleep(0.005)

        async with guard:
            active_by_source[source] -= 1

    pool = QueueWorkerPool(sqlite_job_queue, handler=handler, worker_count=4)
    processed = await pool.run_until_empty()

    done_jobs = await sqlite_job_queue.list(status=SQLiteJobQueue.DONE)

    assert processed == total_jobs
    assert len(done_jobs) == total_jobs
    assert max_by_source["jira-main"] == 1
    assert max_by_source["confluence-main"] == 1


@pytest.mark.asyncio
async def test_worker_pool_rejects_invalid_lease_seconds(sqlite_job_queue: SQLiteJobQueue):
    async def handler(_job_type: str, _payload: dict[str, str]) -> None:
        return None

    with pytest.raises(ValueError, match="lease_seconds must be >= 1"):
        QueueWorkerPool(sqlite_job_queue, handler=handler, lease_seconds=0)


def test_extract_source_key_trims_whitespace():
    key = QueueWorkerPool._extract_source_key({"source": "  jira-main  "})
    assert key == "jira-main"
