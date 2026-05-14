from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import pytest_asyncio
from qdrant_loader.config.state import StateManagementConfig
from qdrant_loader.core.state.session import create_tables, dispose_engine
from qdrant_loader.core.state.session import initialize_engine_and_session
from qdrant_loader.core.worker.queue import SQLiteJobQueue


@pytest_asyncio.fixture
async def sqlite_job_queue(tmp_path: Path):
    db_path = tmp_path / "worker_queue.db"
    config = StateManagementConfig(database_path=str(db_path))
    engine, session_factory = initialize_engine_and_session(config)
    await create_tables(engine)

    queue = SQLiteJobQueue(session_factory)
    try:
        yield queue
    finally:
        await dispose_engine(engine)


@pytest.mark.asyncio
async def test_enqueue_and_list(sqlite_job_queue: SQLiteJobQueue):
    await sqlite_job_queue.enqueue("BULK_INGEST", {"source": "jira"})
    await sqlite_job_queue.enqueue("INCREMENTAL_PULL", {"source": "git"})

    jobs = await sqlite_job_queue.list()
    pending_jobs = await sqlite_job_queue.list(status=SQLiteJobQueue.PENDING)

    assert len(jobs) == 2
    assert len(pending_jobs) == 2
    assert jobs[0].payload_json


@pytest.mark.asyncio
async def test_claim_next_no_duplicates_under_race(sqlite_job_queue: SQLiteJobQueue):
    total_jobs = 100
    workers = 4

    for i in range(total_jobs):
        await sqlite_job_queue.enqueue("INCREMENTAL_PULL", {"sequence": i})

    claimed_ids: set[int] = set()
    duplicate_claims: list[int] = []
    lock = asyncio.Lock()

    async def worker() -> None:
        while True:
            job = await sqlite_job_queue.claim_next(lease_seconds=30)
            if job is None:
                return

            async with lock:
                if job.id in claimed_ids:
                    duplicate_claims.append(job.id)
                claimed_ids.add(job.id)

            await sqlite_job_queue.mark_done(job.id)

    await asyncio.gather(*(worker() for _ in range(workers)))

    done_jobs = await sqlite_job_queue.list(status=SQLiteJobQueue.DONE)
    pending_jobs = await sqlite_job_queue.list(status=SQLiteJobQueue.PENDING)
    running_jobs = await sqlite_job_queue.list(status=SQLiteJobQueue.RUNNING)

    assert len(duplicate_claims) == 0
    assert len(claimed_ids) == total_jobs
    assert len(done_jobs) == total_jobs
    assert len(pending_jobs) == 0
    assert len(running_jobs) == 0


@pytest.mark.asyncio
async def test_mark_failed_sets_error(sqlite_job_queue: SQLiteJobQueue):
    job = await sqlite_job_queue.enqueue("INCREMENTAL_PULL", {"source": "docs"})

    claimed = await sqlite_job_queue.claim_next()
    assert claimed is not None
    assert claimed.id == job.id

    updated = await sqlite_job_queue.mark_failed(job.id, "source timeout")
    assert updated is True

    failed_jobs = await sqlite_job_queue.list(status=SQLiteJobQueue.FAILED)
    assert len(failed_jobs) == 1
    assert failed_jobs[0].last_error == "source timeout"


@pytest.mark.asyncio
async def test_mark_done_sets_status_and_completion_fields(
    sqlite_job_queue: SQLiteJobQueue,
):
    job = await sqlite_job_queue.enqueue("BULK_INGEST", {"source": "jira"})

    claimed = await sqlite_job_queue.claim_next()
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == SQLiteJobQueue.RUNNING
    assert claimed.started_at is not None
    assert claimed.visibility_deadline is not None
    assert claimed.attempts == 1

    updated = await sqlite_job_queue.mark_done(job.id)
    assert updated is True

    done_jobs = await sqlite_job_queue.list(status=SQLiteJobQueue.DONE)
    assert len(done_jobs) == 1

    done_job = done_jobs[0]
    assert done_job.id == job.id
    assert done_job.finished_at is not None
    assert done_job.visibility_deadline is None
    assert done_job.last_error is None


@pytest.mark.asyncio
async def test_claim_next_reclaims_after_lease_timeout(sqlite_job_queue: SQLiteJobQueue):
    job = await sqlite_job_queue.enqueue("INCREMENTAL_PULL", {"source": "docs"})

    first_claim = await sqlite_job_queue.claim_next(lease_seconds=0)
    assert first_claim is not None
    assert first_claim.id == job.id
    assert first_claim.status == SQLiteJobQueue.RUNNING
    assert first_claim.attempts == 1

    second_claim = await sqlite_job_queue.claim_next(lease_seconds=30)
    assert second_claim is not None
    assert second_claim.id == job.id
    assert second_claim.status == SQLiteJobQueue.RUNNING
    assert second_claim.attempts == 2
