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
async def test_scheduler_enqueues_and_workers_drain():
    """
    Verify that the scheduler actually emits jobs for configured sources and
    workers drain them.

    Setup: 2 projects × 3 sources each = 6 sources total.
    The scheduler runs for 3 ticks; deduplication prevents re-enqueuing while
    a job is still pending/running. Because workers drain each batch before the
    next tick, we expect exactly 6 jobs × 3 ticks = 18 done jobs total.
    """
    from qdrant_loader.config.models import ProjectConfig, ProjectsConfig
    from qdrant_loader.config.sources import SourcesConfig

    TICKS = 3
    PROJECTS = 2
    SOURCES_PER_PROJECT = 3  # 2 git + 1 confluence per project
    EXPECTED_TOTAL = PROJECTS * SOURCES_PER_PROJECT * TICKS

    # Build real ProjectsConfig: 2 projects, each with 2 git repos + 1 confluence space
    def _make_projects() -> ProjectsConfig:
        configs = {}
        for p in range(PROJECTS):
            sources = SourcesConfig()
            sources.git = {f"repo-{p}-{i}": object() for i in range(2)}
            sources.confluence = {f"space-{p}": object()}
            project = ProjectConfig(
                project_id=f"proj-{p}",
                display_name=f"Project {p}",
                sources=sources,
            )
            configs[project.project_id] = project
        return ProjectsConfig(projects=configs)

    queue, _, engine = await _make_queue()

    try:
        schedule = IncrementalPullScheduleConfig(enabled=True, interval=5)
        projects_config = _make_projects()

        # Drain workers completely between ticks by running pool inline after each tick
        handler = _NoopHandler()
        worker_pool = QueueWorkerPool(
            queue=queue,
            handler=handler,
            worker_count=4,
            lease_seconds=30,
            max_attempts=1,
            retry_backoff_base_seconds=0,
        )

        scheduler = IncrementalPullScheduler(
            queue=queue,
            projects_config=projects_config,
            schedule=schedule,
        )

        for tick in range(TICKS):
            created = await scheduler.run_once()
            assert (
                created == PROJECTS * SOURCES_PER_PROJECT
            ), f"Tick {tick}: expected {PROJECTS * SOURCES_PER_PROJECT} new jobs, got {created}"
            # Drain before next tick so dedup doesn't suppress re-enqueue
            processed = await worker_pool.run_until_empty()
            assert (
                processed == PROJECTS * SOURCES_PER_PROJECT
            ), f"Tick {tick}: expected {PROJECTS * SOURCES_PER_PROJECT} processed, got {processed}"

        done = await queue.list(status="done")
        pending = await queue.list(status="pending")
        running = await queue.list(status="running")

        assert (
            len(done) == EXPECTED_TOTAL
        ), f"Expected {EXPECTED_TOTAL} done jobs, got {len(done)}"
        assert len(pending) == 0, f"Orphaned pending jobs: {len(pending)}"
        assert len(running) == 0, f"Orphaned running jobs: {len(running)}"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_scheduler_deduplicates_while_jobs_are_active():
    """
    Verify dedup: if a job from tick 1 is still pending when tick 2 fires,
    the scheduler must NOT create a duplicate for that source.
    """
    from qdrant_loader.config.models import ProjectConfig, ProjectsConfig
    from qdrant_loader.config.sources import SourcesConfig

    SOURCES = 3  # 2 git + 1 confluence in a single project

    sources = SourcesConfig()
    sources.git = {"repo-0": object(), "repo-1": object()}
    sources.confluence = {"space-0": object()}
    project = ProjectConfig(project_id="proj-0", display_name="Proj 0", sources=sources)
    projects_config = ProjectsConfig(projects={"proj-0": project})

    queue, _, engine = await _make_queue()

    try:
        schedule = IncrementalPullScheduleConfig(enabled=True, interval=5)
        scheduler = IncrementalPullScheduler(
            queue=queue, projects_config=projects_config, schedule=schedule
        )

        # Tick 1: all sources get a job
        created_1 = await scheduler.run_once()
        assert created_1 == SOURCES, f"Expected {SOURCES}, got {created_1}"

        # Tick 2 (no drain between): jobs still pending → dedup suppresses all
        created_2 = await scheduler.run_once()
        assert created_2 == 0, f"Dedup failed: tick 2 created {created_2} duplicates"

        # Total enqueued is still SOURCES
        pending = await queue.list(status="pending")
        assert len(pending) == SOURCES
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


@pytest.mark.asyncio
async def test_scheduler_dedup_pagination_handles_large_job_count():
    """Verify scheduler._load_active_dedup_keys() paginates through >page_size jobs.

    Previously, the scheduler only called list(status=..., limit=10000) once,
    which meant if a status had >10k jobs, dedup would miss the ones beyond that.

    This test creates 2500 PENDING jobs (>page_size of 1000) and verifies that
    the scheduler correctly identifies all of them as active dedup keys when
    computing which sources to enqueue next.
    """
    from qdrant_loader.config.models import ProjectConfig, ProjectsConfig
    from qdrant_loader.config.sources import SourcesConfig

    queue, _, engine = await _make_queue()

    try:
        # Create 2500 PENDING jobs (exceeds default page_size of 1000)
        NUM_JOBS = 2500
        for i in range(NUM_JOBS):
            await queue.enqueue(
                JobType.INCREMENTAL_PULL,
                {
                    "project_id": f"proj-{i % 5}",
                    "source_type": "git",
                    "source": f"repo-{i}",
                    "source_lock": f"proj-{i % 5}:git:repo-{i}",
                },
            )

        # Build a single project with 1 source to attempt to schedule
        sources = SourcesConfig()
        sources.git = {"new-repo": object()}
        project = ProjectConfig(
            project_id="proj-new", display_name="New", sources=sources
        )
        projects_config = ProjectsConfig(projects={"proj-new": project})

        schedule = IncrementalPullScheduleConfig(enabled=True, interval=5)
        scheduler = IncrementalPullScheduler(
            queue=queue,
            projects_config=projects_config,
            schedule=schedule,
        )

        # Load dedup keys (should paginate through all 2500 PENDING jobs)
        dedup_keys = await scheduler._load_active_dedup_keys()

        # Verify all 2500 jobs are in dedup (not just first 1000)
        assert len(dedup_keys) == NUM_JOBS, (
            f"Pagination failed: expected {NUM_JOBS} dedup keys, got {len(dedup_keys)}. "
            "Likely missed jobs beyond first page."
        )

        # Verify scheduler correctly sees new source is safe to enqueue
        created = await scheduler.run_once()
        assert created == 1, f"Expected 1 new job for new source, got {created}"

    finally:
        await engine.dispose()
