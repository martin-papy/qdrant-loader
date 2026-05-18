from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from json import JSONDecodeError
from typing import Any

from qdrant_loader.core.worker.queue import JobQueue

JobHandler = Callable[[str, dict[str, Any]], Awaitable[None]]


class QueueWorkerPool:
    """Run queue jobs with bounded concurrency and per-source serialization."""

    DEFAULT_SOURCE_KEY = "__global__"

    def __init__(
        self,
        queue: JobQueue,
        handler: JobHandler,
        worker_count: int = 4,
        lease_seconds: int = 60,
    ) -> None:
        if worker_count < 1:
            raise ValueError("worker_count must be >= 1")
        if lease_seconds < 1:
            raise ValueError("lease_seconds must be >= 1")

        self._queue = queue
        self._handler = handler
        self._worker_count = worker_count
        self._lease_seconds = lease_seconds
        self._source_locks: dict[str, asyncio.Lock] = {}
        self._source_locks_guard = asyncio.Lock()
        self._queue_io_guard = asyncio.Lock()

    async def run_until_empty(self) -> int:
        """Drain the queue once and return number of attempted jobs."""
        processed_count = 0
        processed_count_guard = asyncio.Lock()

        async def worker() -> None:
            nonlocal processed_count

            while True:
                async with self._queue_io_guard:
                    job = await self._queue.claim_next(lease_seconds=self._lease_seconds)
                if job is None:
                    return

                payload, error_message = self._decode_payload(job.payload_json)
                if error_message is not None:
                    await self._queue.mark_failed(
                        job.id, error_message, claim_attempt=job.attempts
                    )
                    async with processed_count_guard:
                        processed_count += 1
                    continue

                source_key = self._extract_source_key(payload)
                source_lock = await self._get_source_lock(source_key)

                async with source_lock:
                    try:
                        await self._handler(job.type, payload)
                    except Exception as exc:
                        async with self._queue_io_guard:
                            await self._queue.mark_failed(
                                job.id, str(exc), claim_attempt=job.attempts
                            )
                    else:
                        async with self._queue_io_guard:
                            await self._queue.mark_done(
                                job.id, claim_attempt=job.attempts
                            )

                async with processed_count_guard:
                    processed_count += 1

        await asyncio.gather(*(worker() for _ in range(self._worker_count)))
        return processed_count

    async def _get_source_lock(self, source_key: str) -> asyncio.Lock:
        async with self._source_locks_guard:
            lock = self._source_locks.get(source_key)
            if lock is None:
                lock = asyncio.Lock()
                self._source_locks[source_key] = lock
            return lock

    @staticmethod
    def _decode_payload(payload_json: str) -> tuple[dict[str, Any], str | None]:
        try:
            payload = json.loads(payload_json)
        except JSONDecodeError as exc:
            return {}, f"Invalid payload_json: {exc.msg}"

        if not isinstance(payload, dict):
            return {}, "Invalid payload_json: expected JSON object"
        return payload, None

    @classmethod
    def _extract_source_key(cls, payload: dict[str, Any]) -> str:
        # Prefer explicit source lock key if provided by scheduler/producer.
        for field_name in ("source_lock", "source", "source_name", "project_source"):
            value = payload.get(field_name)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return cls.DEFAULT_SOURCE_KEY
