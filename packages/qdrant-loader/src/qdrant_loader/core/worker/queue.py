from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from qdrant_loader.core.state.models import Job


class JobQueue(Protocol):
    """Queue protocol to allow backend swaps without changing worker logic."""

    async def enqueue(self, job_type: str, payload: dict[str, Any]) -> Job:
        """Create and persist a new pending job."""

    async def claim_next(
        self, lease_seconds: int = 60, job_types: list[str] | None = None
    ) -> Job | None:
        """Atomically claim the next visible pending job.

        Args:
            lease_seconds: Visibility lease duration.
            job_types: If provided, only claim jobs whose type is in this list.
        """

    def notify(self) -> asyncio.Event:
        """Return an event that fires when a job becomes available for claiming.

        The event is raised whenever:
        - A new job is enqueued (status=PENDING).
        - A job is released for retry (status goes back to PENDING).

        Worker loops await this event (with timeout for visibility timeout reclaim)
        to avoid constant polling. Long-poll backends (SQS) get this for free.
        """

    async def mark_done(self, job_id: int, claim_attempt: int) -> bool:
        """Mark a claimed job as completed if claim ownership still matches."""

    async def mark_failed(
        self, job_id: int, error_message: str, claim_attempt: int
    ) -> bool:
        """Mark a claimed job as failed if claim ownership still matches."""

    async def release_for_retry(
        self,
        job_id: int,
        error_message: str,
        claim_attempt: int,
        retry_after_seconds: int = 0,
    ) -> bool:
        """Release a claimed job back to pending for a later retry."""

    async def extend_visibility(
        self, job_id: int, lease_seconds: int, claim_attempt: int
    ) -> bool:
        """Extend the visibility deadline of a RUNNING job by lease_seconds.

        Used to prevent lease expiration during long-running handler execution.
        Returns True if successfully extended, False if claim ownership changed.
        """

    async def list(
        self, status: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[Job]:
        """List jobs with optional status filter and pagination (offset/limit).

        Args:
            status: Filter by job status (e.g., 'pending', 'running'). None = all statuses.
            limit: Max jobs per page (default 100).
            offset: Pagination offset; skip first N results.

        Returns:
            List of Job objects ordered by (enqueued_at, id). May return <limit results.
        """

    async def reset_to_pending(self, job_id: int) -> bool:
        """Reset a failed or done job back to pending so it can be retried."""

    async def cancel(self, job_id: int) -> bool:
        """Cancel a pending job (sets status to CANCELLED)."""


class SQLiteJobQueue:
    """SQLite-backed job queue implementation using SQLAlchemy async sessions."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        self._pending_event = asyncio.Event()

    def notify(self) -> asyncio.Event:
        """Return the event used to signal when jobs become available."""
        return self._pending_event

    async def enqueue(self, job_type: str, payload: dict[str, Any]) -> Job:
        now = datetime.now(UTC)
        job = Job(
            type=job_type,
            payload_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            status=self.PENDING,
            enqueued_at=now,
            attempts=0,
            started_at=None,
            finished_at=None,
            last_error=None,
            visibility_deadline=None,
        )

        async with self._session_factory() as session:
            session.add(job)
            await session.commit()
            await session.refresh(job)
            self._pending_event.set()
            return job

    async def claim_next(
        self, lease_seconds: int = 60, job_types: list[str] | None = None
    ) -> Job | None:
        if lease_seconds < 0:
            raise ValueError("lease_seconds must be non-negative")
        now = datetime.now(UTC)
        visibility_deadline = now + timedelta(seconds=lease_seconds)
        claimable_filter = or_(
            (Job.status == self.PENDING)
            & ((Job.visibility_deadline.is_(None)) | (Job.visibility_deadline <= now)),
            (Job.status == self.RUNNING) & (Job.visibility_deadline <= now),
        )

        async with self._session_factory() as session:
            select_stmt = select(Job.id).where(claimable_filter)
            if job_types:
                select_stmt = select_stmt.where(Job.type.in_(job_types))
            candidate_job_id = await session.scalar(
                select_stmt.order_by(Job.enqueued_at.asc(), Job.id.asc()).limit(1)
            )

            if candidate_job_id is None:
                await session.commit()
                return None

            result = await session.execute(
                update(Job)
                .where(Job.id == candidate_job_id, claimable_filter)
                .values(
                    status=self.RUNNING,
                    started_at=now,
                    finished_at=None,
                    visibility_deadline=visibility_deadline,
                    attempts=Job.attempts + 1,
                    last_error=None,
                )
            )
            claimed = result.rowcount > 0
            if not claimed:
                await session.commit()
                return None

            claimed_job = await session.get(Job, candidate_job_id)
            await session.commit()
            return claimed_job

    async def mark_done(self, job_id: int, claim_attempt: int) -> bool:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            result = await session.execute(
                update(Job)
                .where(
                    Job.id == job_id,
                    Job.status == self.RUNNING,
                    Job.attempts == claim_attempt,
                )
                .values(
                    status=self.DONE,
                    finished_at=now,
                    visibility_deadline=None,
                    last_error=None,
                )
            )
            updated = result.rowcount > 0
            await session.commit()
            return updated

    async def mark_failed(
        self, job_id: int, error_message: str, claim_attempt: int
    ) -> bool:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            result = await session.execute(
                update(Job)
                .where(
                    Job.id == job_id,
                    Job.status == self.RUNNING,
                    Job.attempts == claim_attempt,
                )
                .values(
                    status=self.FAILED,
                    finished_at=now,
                    visibility_deadline=None,
                    last_error=error_message,
                )
            )
            updated = result.rowcount > 0
            await session.commit()
            return updated

    async def release_for_retry(
        self,
        job_id: int,
        error_message: str,
        claim_attempt: int,
        retry_after_seconds: int = 0,
    ) -> bool:
        if retry_after_seconds < 0:
            raise ValueError("retry_after_seconds must be non-negative")

        now = datetime.now(UTC)
        retry_deadline = (
            now + timedelta(seconds=retry_after_seconds)
            if retry_after_seconds > 0
            else None
        )

        async with self._session_factory() as session:
            result = await session.execute(
                update(Job)
                .where(
                    Job.id == job_id,
                    Job.status == self.RUNNING,
                    Job.attempts == claim_attempt,
                )
                .values(
                    status=self.PENDING,
                    started_at=None,
                    finished_at=None,
                    visibility_deadline=retry_deadline,
                    last_error=error_message,
                )
            )
            updated = result.rowcount > 0
            await session.commit()
            if updated:
                self._pending_event.set()
            return updated

    async def extend_visibility(
        self, job_id: int, lease_seconds: int, claim_attempt: int
    ) -> bool:
        """Extend the visibility deadline of a RUNNING job by lease_seconds.

        Used to prevent lease expiration during long-running handler execution.
        Returns True if successfully extended, False if claim ownership changed.
        """
        now = datetime.now(UTC)
        new_deadline = now + timedelta(seconds=lease_seconds)

        async with self._session_factory() as session:
            result = await session.execute(
                update(Job)
                .where(
                    Job.id == job_id,
                    Job.status == self.RUNNING,
                    Job.attempts == claim_attempt,
                )
                .values(
                    visibility_deadline=new_deadline,
                )
            )
            updated = result.rowcount > 0
            await session.commit()
            return updated

    async def list(
        self, status: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[Job]:
        """List jobs with optional status filter and pagination support.

        Args:
            status: Filter by job status (e.g., 'pending', 'running'). None = all statuses.
            limit: Max jobs to return per page (default 100).
            offset: Pagination offset; skip first N results.

        Returns:
            List of Job objects ordered by (enqueued_at ASC, id ASC). May return <limit results.

        Example (paginate through all pending jobs):
            offset = 0
            while True:
                jobs = await queue.list(status='pending', limit=1000, offset=offset)
                if not jobs:
                    break
                for job in jobs:
                    process(job)
                if len(jobs) < 1000:
                    break
                offset += 1000
        """
        async with self._session_factory() as session:
            stmt = select(Job)
            if status:
                stmt = stmt.where(Job.status == status)
            stmt = (
                stmt.order_by(Job.enqueued_at.asc(), Job.id.asc())
                .offset(offset)
                .limit(limit)
            )

            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def reset_to_pending(self, job_id: int) -> bool:
        """Reset a failed/done job back to pending for retry.

        Preserve attempts so operator retries do not erase retry history.
        Does not reset CANCELLED jobs (operator must explicitly delete them).
        """
        async with self._session_factory() as session:
            result = await session.execute(
                update(Job)
                .where(
                    Job.id == job_id,
                    Job.status.in_([self.FAILED, self.DONE]),
                )
                .values(
                    status=self.PENDING,
                    started_at=None,
                    finished_at=None,
                    visibility_deadline=None,
                    last_error=None,
                )
            )
            updated = result.rowcount > 0
            await session.commit()
            return updated

    async def cancel(self, job_id: int) -> bool:
        """Cancel a pending job."""
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            result = await session.execute(
                update(Job)
                .where(
                    Job.id == job_id,
                    Job.status == self.PENDING,
                )
                .values(
                    status=self.CANCELLED,
                    finished_at=now,
                    visibility_deadline=None,
                    last_error=None,
                )
            )
            updated = result.rowcount > 0
            await session.commit()
            return updated
