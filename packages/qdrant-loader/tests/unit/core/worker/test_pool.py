from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import update

from qdrant_loader.config.state import StateManagementConfig
from qdrant_loader.core.state.models import Job
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
async def test_worker_pool_processes_queue_with_four_workers(
    sqlite_job_queue: SQLiteJobQueue,
):
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
async def test_worker_pool_rejects_invalid_lease_seconds(
    sqlite_job_queue: SQLiteJobQueue,
):
    async def handler(_job_type: str, _payload: dict[str, str]) -> None:
        return None

    with pytest.raises(ValueError, match="lease_seconds must be >= 1"):
        QueueWorkerPool(sqlite_job_queue, handler=handler, lease_seconds=0)


@pytest.mark.asyncio
async def test_worker_pool_retries_transient_errors_until_success(
    sqlite_job_queue: SQLiteJobQueue,
):
    await sqlite_job_queue.enqueue("INCREMENTAL_PULL", {"source": "jira-main"})

    attempts = 0

    async def handler(_job_type: str, _payload: dict[str, str]) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("temporary jira 502")

    pool = QueueWorkerPool(
        sqlite_job_queue,
        handler=handler,
        worker_count=1,
        max_attempts=3,
    )
    processed = await pool.run_until_empty()

    done_jobs = await sqlite_job_queue.list(status=SQLiteJobQueue.DONE)
    failed_jobs = await sqlite_job_queue.list(status=SQLiteJobQueue.FAILED)

    assert processed == 3
    assert attempts == 3
    assert len(done_jobs) == 1
    assert len(failed_jobs) == 0
    assert done_jobs[0].attempts == 3


@pytest.mark.asyncio
async def test_worker_pool_marks_failed_after_max_attempts_exhausted(
    sqlite_job_queue: SQLiteJobQueue,
):
    await sqlite_job_queue.enqueue("INCREMENTAL_PULL", {"source": "jira-main"})

    async def handler(_job_type: str, _payload: dict[str, str]) -> None:
        raise RuntimeError("always failing")

    pool = QueueWorkerPool(
        sqlite_job_queue,
        handler=handler,
        worker_count=1,
        max_attempts=2,
    )
    processed = await pool.run_until_empty()

    done_jobs = await sqlite_job_queue.list(status=SQLiteJobQueue.DONE)
    failed_jobs = await sqlite_job_queue.list(status=SQLiteJobQueue.FAILED)

    assert processed == 2
    assert len(done_jobs) == 0
    assert len(failed_jobs) == 1
    assert failed_jobs[0].attempts == 2


@pytest.mark.asyncio
async def test_worker_pool_rejects_invalid_max_attempts(
    sqlite_job_queue: SQLiteJobQueue,
):
    async def handler(_job_type: str, _payload: dict[str, str]) -> None:
        return None

    with pytest.raises(ValueError, match="max_attempts must be >= 1"):
        QueueWorkerPool(sqlite_job_queue, handler=handler, max_attempts=0)


@pytest.mark.asyncio
async def test_worker_pool_reclaims_job_after_visibility_timeout(
    sqlite_job_queue: SQLiteJobQueue,
):
    """WS-4 AC: Container killed mid-run, restarted — interrupted job picked up
    after visibility timeout expires.

    Simulates a job that was claimed and set to RUNNING (e.g. by a previous
    container that died) with an already-expired visibility_deadline.
    The pool must reclaim and complete it without manual intervention.
    """
    job = await sqlite_job_queue.enqueue("INCREMENTAL_PULL", {"source": "jira-main"})

    # Simulate a previous container that claimed the job but never finished:
    # set status=RUNNING with a visibility_deadline in the past.
    past_deadline = datetime.now(UTC) - timedelta(seconds=10)
    async with sqlite_job_queue._session_factory() as session:
        await session.execute(
            update(Job)
            .where(Job.id == job.id)
            .values(
                status=SQLiteJobQueue.RUNNING,
                started_at=datetime.now(UTC) - timedelta(seconds=70),
                visibility_deadline=past_deadline,
                attempts=1,
            )
        )
        await session.commit()

    completed = []

    async def handler(job_type: str, payload: dict) -> None:
        completed.append(payload["source"])

    pool = QueueWorkerPool(sqlite_job_queue, handler=handler, worker_count=2)
    processed = await pool.run_until_empty()

    done_jobs = await sqlite_job_queue.list(status=SQLiteJobQueue.DONE)
    running_jobs = await sqlite_job_queue.list(status=SQLiteJobQueue.RUNNING)

    assert processed == 1
    assert len(done_jobs) == 1
    assert len(running_jobs) == 0
    assert completed == ["jira-main"]
    # attempts incremented once more by the reclaim
    assert done_jobs[0].attempts == 2


def test_extract_source_key_trims_whitespace():
    key = QueueWorkerPool._extract_source_key({"source": "  jira-main  "})
    assert key == "jira-main"
