from __future__ import annotations

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

    async def claim_next(self, lease_seconds: int = 60) -> Job | None:
        """Atomically claim the next visible pending job."""

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

    async def list(self, status: str | None = None, limit: int = 100) -> list[Job]:
        """List jobs with optional status filter."""


class SQLiteJobQueue:
    """SQLite-backed job queue implementation using SQLAlchemy async sessions."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

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
            return job

    async def claim_next(self, lease_seconds: int = 60) -> Job | None:
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
            next_job_id = (
                select(Job.id)
                .where(claimable_filter)
                .order_by(Job.enqueued_at.asc(), Job.id.asc())
                .limit(1)
                .scalar_subquery()
            )

            stmt = (
                update(Job)
                .where(Job.id == next_job_id, claimable_filter)
                .values(
                    status=self.RUNNING,
                    started_at=now,
                    finished_at=None,
                    visibility_deadline=visibility_deadline,
                    attempts=Job.attempts + 1,
                    last_error=None,
                )
                .returning(Job.id)
            )

            result = await session.execute(stmt)
            claimed_job_id = result.scalar_one_or_none()
            await session.commit()

            if claimed_job_id is None:
                return None

            claimed_job = await session.get(Job, claimed_job_id)
            return claimed_job

    async def mark_done(self, job_id: int, claim_attempt: int) -> bool:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            stmt = (
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
                .returning(Job.id)
            )
            result = await session.execute(stmt)
            updated_job_id = result.scalar_one_or_none()
            await session.commit()
            return updated_job_id is not None

    async def mark_failed(
        self, job_id: int, error_message: str, claim_attempt: int
    ) -> bool:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            stmt = (
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
                .returning(Job.id)
            )
            result = await session.execute(stmt)
            updated_job_id = result.scalar_one_or_none()
            await session.commit()
            return updated_job_id is not None

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
            stmt = (
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
                .returning(Job.id)
            )
            result = await session.execute(stmt)
            updated_job_id = result.scalar_one_or_none()
            await session.commit()
            return updated_job_id is not None

    async def list(self, status: str | None = None, limit: int = 100) -> list[Job]:
        async with self._session_factory() as session:
            stmt = select(Job)
            if status:
                stmt = stmt.where(Job.status == status)
            stmt = stmt.order_by(Job.enqueued_at.asc(), Job.id.asc()).limit(limit)

            result = await session.execute(stmt)
            return list(result.scalars().all())
