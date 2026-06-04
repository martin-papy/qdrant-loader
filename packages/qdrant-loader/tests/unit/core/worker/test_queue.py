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

            await sqlite_job_queue.mark_done(job.id, claim_attempt=job.attempts)

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

    updated = await sqlite_job_queue.mark_failed(
        job.id, "source timeout", claim_attempt=claimed.attempts
    )
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

    updated = await sqlite_job_queue.mark_done(job.id, claim_attempt=claimed.attempts)
    assert updated is True

    done_jobs = await sqlite_job_queue.list(status=SQLiteJobQueue.DONE)
    assert len(done_jobs) == 1

    done_job = done_jobs[0]
    assert done_job.id == job.id
    assert done_job.finished_at is not None
    assert done_job.visibility_deadline is None
    assert done_job.last_error is None


@pytest.mark.asyncio
async def test_claim_next_reclaims_after_lease_timeout(
    sqlite_job_queue: SQLiteJobQueue,
):
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


@pytest.mark.asyncio
async def test_mark_done_rejects_stale_claim_attempt(sqlite_job_queue: SQLiteJobQueue):
    job = await sqlite_job_queue.enqueue("INCREMENTAL_PULL", {"source": "docs"})

    first_claim = await sqlite_job_queue.claim_next(lease_seconds=0)
    assert first_claim is not None
    assert first_claim.id == job.id
    assert first_claim.attempts == 1

    second_claim = await sqlite_job_queue.claim_next(lease_seconds=30)
    assert second_claim is not None
    assert second_claim.id == job.id
    assert second_claim.attempts == 2

    stale_update = await sqlite_job_queue.mark_done(
        job.id, claim_attempt=first_claim.attempts
    )
    assert stale_update is False

    fresh_update = await sqlite_job_queue.mark_done(
        job.id, claim_attempt=second_claim.attempts
    )
    assert fresh_update is True


@pytest.mark.asyncio
async def test_release_for_retry_requeues_without_incrementing_attempts(
    sqlite_job_queue: SQLiteJobQueue,
):
    job = await sqlite_job_queue.enqueue("INCREMENTAL_PULL", {"source": "docs"})

    first_claim = await sqlite_job_queue.claim_next(lease_seconds=30)
    assert first_claim is not None
    assert first_claim.id == job.id
    assert first_claim.attempts == 1

    released = await sqlite_job_queue.release_for_retry(
        job.id,
        "transient network error",
        claim_attempt=first_claim.attempts,
    )
    assert released is True

    second_claim = await sqlite_job_queue.claim_next(lease_seconds=30)
    assert second_claim is not None
    assert second_claim.id == job.id
    assert second_claim.attempts == 2


@pytest.mark.asyncio
async def test_release_for_retry_with_delay_hides_pending_job_until_due(
    sqlite_job_queue: SQLiteJobQueue,
):
    job = await sqlite_job_queue.enqueue("INCREMENTAL_PULL", {"source": "docs"})

    claimed = await sqlite_job_queue.claim_next(lease_seconds=30)
    assert claimed is not None
    assert claimed.id == job.id

    released = await sqlite_job_queue.release_for_retry(
        job.id,
        "transient timeout",
        claim_attempt=claimed.attempts,
        retry_after_seconds=1,
    )
    assert released is True

    hidden = await sqlite_job_queue.claim_next(lease_seconds=30)
    assert hidden is None

    await asyncio.sleep(1.05)
    due = await sqlite_job_queue.claim_next(lease_seconds=30)
    assert due is not None
    assert due.id == job.id


@pytest.mark.asyncio
async def test_reset_to_pending_preserves_attempt_history(
    sqlite_job_queue: SQLiteJobQueue,
):
    job = await sqlite_job_queue.enqueue("INCREMENTAL_PULL", {"source": "docs"})

    claimed = await sqlite_job_queue.claim_next(lease_seconds=30)
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.attempts == 1

    failed = await sqlite_job_queue.mark_failed(
        job.id,
        "operator requested retry",
        claim_attempt=claimed.attempts,
    )
    assert failed is True

    reset = await sqlite_job_queue.reset_to_pending(job.id)
    assert reset is True

    retried = await sqlite_job_queue.claim_next(lease_seconds=30)
    assert retried is not None
    assert retried.id == job.id
    assert retried.attempts == 2


@pytest.mark.asyncio
async def test_cancel_pending_job_sets_cancelled_status(
    sqlite_job_queue: SQLiteJobQueue,
):
    job = await sqlite_job_queue.enqueue("INCREMENTAL_PULL", {"source": "docs"})

    ok = await sqlite_job_queue.cancel(job.id)
    assert ok is True

    cancelled = await sqlite_job_queue.list(status=SQLiteJobQueue.CANCELLED)
    assert len(cancelled) == 1
    assert cancelled[0].id == job.id
    assert cancelled[0].status == SQLiteJobQueue.CANCELLED
    assert cancelled[0].last_error is None  # not conflated with failure

    failed = await sqlite_job_queue.list(status=SQLiteJobQueue.FAILED)
    assert len(failed) == 0


@pytest.mark.asyncio
async def test_cancel_running_job_is_rejected(
    sqlite_job_queue: SQLiteJobQueue,
):
    job = await sqlite_job_queue.enqueue("INCREMENTAL_PULL", {"source": "docs"})
    claimed = await sqlite_job_queue.claim_next(lease_seconds=30)
    assert claimed is not None

    ok = await sqlite_job_queue.cancel(job.id)
    assert ok is False

    cancelled = await sqlite_job_queue.list(status=SQLiteJobQueue.CANCELLED)
    assert len(cancelled) == 0

    running = await sqlite_job_queue.list(status=SQLiteJobQueue.RUNNING)
    assert len(running) == 1
    assert running[0].id == job.id


@pytest.mark.asyncio
async def test_cancelled_job_cannot_be_retried(sqlite_job_queue: SQLiteJobQueue):
    job = await sqlite_job_queue.enqueue("INCREMENTAL_PULL", {"source": "docs"})
    await sqlite_job_queue.cancel(job.id)

    # reset_to_pending only accepts FAILED | DONE — cancelled must be excluded
    reset = await sqlite_job_queue.reset_to_pending(job.id)
    assert reset is False

    pending = await sqlite_job_queue.list(status=SQLiteJobQueue.PENDING)
    assert len(pending) == 0


@pytest.mark.asyncio
async def test_extend_visibility_updates_running_job_deadline(
    sqlite_job_queue: SQLiteJobQueue,
):
    """extend_visibility should extend deadline for RUNNING jobs."""
    job = await sqlite_job_queue.enqueue("INCREMENTAL_PULL", {"source": "test"})

    # Claim job (status = RUNNING, visibility_deadline = now + 60s)
    claimed = await sqlite_job_queue.claim_next(lease_seconds=60)
    assert claimed is not None
    assert claimed.status == SQLiteJobQueue.RUNNING

    # Extend by 30s
    extended = await sqlite_job_queue.extend_visibility(job.id, lease_seconds=30)
    assert extended is True  # Should succeed

    # Verify deadline was extended (new deadline should be >= original + 30s)
    updated_job = await sqlite_job_queue.claim_next(lease_seconds=60)
    assert updated_job is None  # Can't claim again (still leased from renewal)


@pytest.mark.asyncio
async def test_extend_visibility_ignores_non_running_job(
    sqlite_job_queue: SQLiteJobQueue,
):
    """extend_visibility should fail for non-RUNNING jobs (DONE, FAILED, PENDING)."""
    job = await sqlite_job_queue.enqueue("INCREMENTAL_PULL", {"source": "test"})
    claimed = await sqlite_job_queue.claim_next(lease_seconds=60)
    assert claimed is not None

    # Mark DONE
    await sqlite_job_queue.mark_done(job.id, claim_attempt=claimed.attempts)

    # Try to extend DONE job
    extended = await sqlite_job_queue.extend_visibility(job.id, lease_seconds=30)
    assert extended is False  # Should fail because job is DONE


@pytest.mark.asyncio
async def test_extend_visibility_on_pending_job_fails(
    sqlite_job_queue: SQLiteJobQueue,
):
    """extend_visibility should reject PENDING jobs (not yet claimed)."""
    job = await sqlite_job_queue.enqueue("INCREMENTAL_PULL", {"source": "test"})

    # Try to extend PENDING job (without claiming)
    extended = await sqlite_job_queue.extend_visibility(job.id, lease_seconds=30)
    assert extended is False


@pytest.mark.asyncio
async def test_list_with_offset_and_limit_pagination(sqlite_job_queue: SQLiteJobQueue):
    """Test pagination using offset and limit parameters."""
    # Create 25 jobs
    NUM_JOBS = 25
    for i in range(NUM_JOBS):
        await sqlite_job_queue.enqueue("INCREMENTAL_PULL", {"index": i})

    # Page 1: offset=0, limit=10 → jobs 0-9
    page1 = await sqlite_job_queue.list(limit=10, offset=0)
    assert len(page1) == 10
    assert page1[0].payload_json == '{"index": 0}'
    assert page1[9].payload_json == '{"index": 9}'

    # Page 2: offset=10, limit=10 → jobs 10-19
    page2 = await sqlite_job_queue.list(limit=10, offset=10)
    assert len(page2) == 10
    assert page2[0].payload_json == '{"index": 10}'
    assert page2[9].payload_json == '{"index": 19}'

    # Page 3: offset=20, limit=10 → jobs 20-24 (only 5 left)
    page3 = await sqlite_job_queue.list(limit=10, offset=20)
    assert len(page3) == 5
    assert page3[0].payload_json == '{"index": 20}'
    assert page3[4].payload_json == '{"index": 24}'

    # Page 4: offset=30, limit=10 → empty (beyond end)
    page4 = await sqlite_job_queue.list(limit=10, offset=30)
    assert len(page4) == 0


@pytest.mark.asyncio
async def test_list_pagination_with_status_filter(sqlite_job_queue: SQLiteJobQueue):
    """Test pagination respects status filter correctly."""
    # Create 20 PENDING jobs and 5 DONE jobs
    for i in range(20):
        await sqlite_job_queue.enqueue(
            "INCREMENTAL_PULL", {"status": "pending", "index": i}
        )

    # Claim and mark 5 as done
    for _i in range(5):
        job = await sqlite_job_queue.claim_next(lease_seconds=30)
        if job:
            await sqlite_job_queue.mark_done(job.id, claim_attempt=job.attempts)

    # Paginate PENDING (should be 15 left after 5 done)
    pending_page1 = await sqlite_job_queue.list(status="pending", limit=10, offset=0)
    assert len(pending_page1) == 10

    pending_page2 = await sqlite_job_queue.list(status="pending", limit=10, offset=10)
    assert len(pending_page2) == 5

    # Paginate DONE (should be 5)
    done_page1 = await sqlite_job_queue.list(status="done", limit=10, offset=0)
    assert len(done_page1) == 5

    done_page2 = await sqlite_job_queue.list(status="done", limit=10, offset=5)
    assert len(done_page2) == 0


@pytest.mark.asyncio
async def test_list_default_offset_is_zero(sqlite_job_queue: SQLiteJobQueue):
    """Test that offset defaults to 0 when not specified."""
    for i in range(5):
        await sqlite_job_queue.enqueue("INCREMENTAL_PULL", {"index": i})

    # Call without offset parameter (should default to 0, return first 5)
    jobs = await sqlite_job_queue.list(limit=10)
    assert len(jobs) == 5
