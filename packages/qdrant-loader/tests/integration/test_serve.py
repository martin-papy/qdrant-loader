"""
Mini-soak integration test for queue drain.

Simulates a 60-second run with:
  - 5-second scheduler interval (12× clock acceleration → finishes in ~5 real seconds)
  - 10 pre-seeded INCREMENTAL_PULL jobs
  - A no-op job handler so workers drain the queue without real I/O

Assertions:
  - Queue drains to zero pending/running jobs
  - No orphaned RUNNING jobs after shutdown
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from qdrant_loader.config.models import ProjectsConfig
from qdrant_loader.config.workers import IncrementalPullScheduleConfig
from qdrant_loader.core.state.models import Base, Job
from qdrant_loader.core.worker.job_types import JobType
from qdrant_loader.core.worker.pool import QueueWorkerPool
from qdrant_loader.core.worker.queue import SQLiteJobQueue
from qdrant_loader.core.worker.scheduler import IncrementalPullScheduler
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ── SQLAlchemy async in-memory setup ────────────────────────────────────────


async def _make_queue() -> tuple[SQLiteJobQueue, async_sessionmaker, any]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return SQLiteJobQueue(factory), factory, engine


# ── No-op job handler ────────────────────────────────────────────────────────


class _NoopHandler:
    """Instantly succeeds for any job type."""

    async def __call__(self, job_type: str, payload: dict) -> None:
        return None


# ── Simulated-clock scheduler helper ────────────────────────────────────────


class _FakeClock:
    """Monotonic clock that advances at `acceleration` × real time."""

    def __init__(self, acceleration: float = 12.0) -> None:
        self._start_real = time.monotonic()
        self._acceleration = acceleration

    def __call__(self) -> float:
        return (time.monotonic() - self._start_real) * self._acceleration


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def anyio_backend():
    return "asyncio"


# ── Test ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mini_soak_queue_drains():
    """
    60-second simulated run with 5-second intervals.
    10 jobs seeded; workers drain the queue.
    After shutdown: no pending or running jobs remain (no orphans).
    """
    SIMULATED_SECONDS = 60
    SCHEDULE_INTERVAL = 5  # seconds (simulated)
    INITIAL_JOBS = 10
    ACCELERATION = 12.0  # 60s sim → ~5s real

    queue, _, engine = await _make_queue()

    try:
        # Seed 10 initial INCREMENTAL_PULL jobs (include source_lock as required by pool)
        for i in range(INITIAL_JOBS):
            await queue.enqueue(
                JobType.INCREMENTAL_PULL,
                {
                    "source_type": "git",
                    "source": f"repo-{i}",
                    "project_id": "proj",
                    "source_lock": f"proj:git:repo-{i}",
                },
            )

        # Build a minimal ProjectsConfig (no real projects; scheduler will emit 0 new jobs)
        projects_config = MagicMock(spec=ProjectsConfig)
        projects_config.projects = {}

        schedule = IncrementalPullScheduleConfig(
            enabled=True, interval=SCHEDULE_INTERVAL
        )

        fake_clock = _FakeClock(acceleration=ACCELERATION)
        scheduler = IncrementalPullScheduler(
            queue=queue,
            projects_config=projects_config,
            schedule=schedule,
            monotonic=fake_clock,
        )

        handler = _NoopHandler()
        worker_pool = QueueWorkerPool(
            queue=queue,
            handler=handler,
            worker_count=4,
            lease_seconds=10,
            max_attempts=1,
            retry_backoff_base_seconds=0,
        )

        stop_event = asyncio.Event()

        # Stop the loop after SIMULATED_SECONDS of simulated time
        real_duration = SIMULATED_SECONDS / ACCELERATION + 1.0  # +1s safety margin

        async def _auto_stop():
            await asyncio.sleep(real_duration)
            stop_event.set()

        async def _worker_loop():
            while not stop_event.is_set():
                await worker_pool.run_until_empty()
                await asyncio.sleep(0.05)

        async with asyncio.timeout(real_duration + 5):
            await asyncio.gather(
                scheduler.run(stop_event),
                _worker_loop(),
                _auto_stop(),
            )

        # ── Assertions ──────────────────────────────────────────────────────────
        pending = await queue.list(status="pending")
        running = await queue.list(status="running")
        done = await queue.list(status="done")

        assert len(pending) == 0, f"Orphaned pending jobs: {len(pending)}"
        assert len(running) == 0, f"Orphaned running jobs: {len(running)}"
        assert (
            len(done) == INITIAL_JOBS
        ), f"Expected {INITIAL_JOBS} done jobs, got {len(done)}"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_pool_reclaims_interrupted_job_after_visibility_timeout():
    """
    WS-4 AC: Container killed mid-run, restarted — interrupted job picked up
    after visibility timeout expires.

    Simulates a previous container that crashed and left a job marked RUNNING
    with an expired visibility_deadline. When the pool restarts, it should
    reclaim and complete the job without manual intervention.
    """
    queue, factory, engine = await _make_queue()

    try:
        # Step 1: Enqueue a job
        job = await queue.enqueue(
            JobType.INCREMENTAL_PULL,
            {
                "source_type": "git",
                "source": "repo-0",
                "project_id": "proj",
                "source_lock": "proj:git:repo-0",
            },
        )

        # Step 2: Simulate container crash: mark job RUNNING with expired deadline
        # (as if it was claimed 70 seconds ago and never finished)
        past_deadline = datetime.now(UTC) - timedelta(seconds=10)
        async with factory() as session:
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

        # Step 3: Start pool with no-op handler
        handler = _NoopHandler()
        worker_pool = QueueWorkerPool(
            queue=queue,
            handler=handler,
            worker_count=1,
            lease_seconds=10,
        )

        # Step 4: Run pool once (should reclaim and complete the job)
        processed = await worker_pool.run_until_empty()

        # Step 5: Assert job was reclaimed and completed
        done_jobs = await queue.list(status=SQLiteJobQueue.DONE)
        running_jobs = await queue.list(status=SQLiteJobQueue.RUNNING)
        pending_jobs = await queue.list(status=SQLiteJobQueue.PENDING)

        assert processed == 1, f"Expected 1 job processed, got {processed}"
        assert len(done_jobs) == 1, f"Expected 1 done job, got {len(done_jobs)}"
        assert (
            len(running_jobs) == 0
        ), f"Expected 0 running jobs, got {len(running_jobs)}"
        assert (
            len(pending_jobs) == 0
        ), f"Expected 0 pending jobs, got {len(pending_jobs)}"
        # attempts incremented by reclaim + completion
        assert (
            done_jobs[0].attempts == 2
        ), f"Expected attempts=2, got {done_jobs[0].attempts}"
    finally:
        await engine.dispose()
