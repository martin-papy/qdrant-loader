from __future__ import annotations

import asyncio
import json
import time
from json import JSONDecodeError
from typing import Any

from qdrant_loader.core.worker.handlers import JobHandler
from qdrant_loader.core.worker.queue import JobQueue
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class QueueWorkerPool:
    """Run queue jobs with bounded concurrency and per-source serialization."""

    DEFAULT_SOURCE_KEY = "__global__"

    def __init__(
        self,
        queue: JobQueue,
        handler: JobHandler,
        worker_count: int = 4,
        lease_seconds: int = 60,
        max_attempts: int = 1,
        retry_backoff_base_seconds: int = 0,
        job_types: list[str] | None = None,
    ) -> None:
        if worker_count < 1:
            raise ValueError("worker_count must be >= 1")
        if lease_seconds < 1:
            raise ValueError("lease_seconds must be >= 1")
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if retry_backoff_base_seconds < 0:
            raise ValueError("retry_backoff_base_seconds must be >= 0")

        self._queue = queue
        self._handler = handler
        self._worker_count = worker_count
        self._lease_seconds = lease_seconds
        self._max_attempts = max_attempts
        self._retry_backoff_base_seconds = retry_backoff_base_seconds
        self._job_types = job_types
        self._source_locks: dict[str, asyncio.Lock] = {}
        self._source_locks_guard = asyncio.Lock()
        self._queue_io_guard = asyncio.Lock()

    async def run_until_empty(self) -> int:
        """Drain the queue once and return number of attempted jobs."""
        processed_count = 0
        processed_count_guard = asyncio.Lock()
        active_workers: set[int] = set()
        active_workers_guard = asyncio.Lock()

        async def _set_worker_activity(worker_id: int, is_active: bool) -> int:
            async with active_workers_guard:
                if is_active:
                    active_workers.add(worker_id)
                else:
                    active_workers.discard(worker_id)
                return len(active_workers)

        async def worker(worker_id: int) -> None:
            nonlocal processed_count

            while True:
                async with self._queue_io_guard:
                    job = await self._queue.claim_next(
                        lease_seconds=self._lease_seconds,
                        job_types=self._job_types,
                    )
                if job is None:
                    return

                current_active_workers = await _set_worker_activity(worker_id, True)

                payload, error_message = self._decode_payload(job.payload_json)
                if error_message is not None:
                    async with self._queue_io_guard:
                        updated = await self._queue.mark_failed(
                            job.id, error_message, claim_attempt=job.attempts
                        )
                    if not updated:
                        logger.warning(
                            "job.claim_lost_on_terminal_transition",
                            job_id=job.id,
                            worker_id=worker_id,
                            active_workers=current_active_workers,
                            worker_count=self._worker_count,
                        )
                    async with processed_count_guard:
                        processed_count += 1
                    await _set_worker_activity(worker_id, False)
                    continue

                try:
                    source_key = self._extract_source_key(payload)
                except KeyError as exc:
                    async with self._queue_io_guard:
                        updated = await self._queue.mark_failed(
                            job.id, str(exc), claim_attempt=job.attempts
                        )
                    if not updated:
                        logger.warning(
                            "job.claim_lost_on_terminal_transition",
                            job_id=job.id,
                            worker_id=worker_id,
                            active_workers=current_active_workers,
                            worker_count=self._worker_count,
                        )
                    async with processed_count_guard:
                        processed_count += 1
                    await _set_worker_activity(worker_id, False)
                    continue
                source_lock = await self._get_source_lock(source_key)

                logger.info(
                    "job.claimed",
                    job_id=job.id,
                    job_type=job.type,
                    source_key=source_key,
                    attempt=job.attempts,
                    worker_id=worker_id,
                    active_workers=current_active_workers,
                    worker_count=self._worker_count,
                )

                async with source_lock:
                    logger.info(
                        "job.handler_started",
                        job_id=job.id,
                        job_type=job.type,
                        source_key=source_key,
                        attempt=job.attempts,
                        worker_id=worker_id,
                        active_workers=current_active_workers,
                        worker_count=self._worker_count,
                    )
                    t0 = time.monotonic()
                    claim_lost = False
                    renewal_interval = max(1, self._lease_seconds // 3)
                    # Mutable holder so _renew_lease closure can reference handler_task
                    # after it is created (asyncio is single-threaded; the first
                    # renewal sleep guarantees the holder is populated before use).
                    _handler_task_holder: list[asyncio.Task | None] = [None]

                    async def _renew_lease(
                        *,
                        current_job_id: int = job.id,
                        current_claim_attempt: int = job.attempts,
                        current_lease_seconds: int = self._lease_seconds,
                        current_renewal_interval: int = renewal_interval,
                        holder: list[asyncio.Task | None] = _handler_task_holder,
                    ) -> None:
                        nonlocal claim_lost
                        while True:
                            await asyncio.sleep(current_renewal_interval)
                            try:
                                async with self._queue_io_guard:
                                    renewed = await self._queue.extend_visibility(
                                        current_job_id,
                                        current_lease_seconds,
                                        claim_attempt=current_claim_attempt,
                                    )
                                if not renewed:
                                    # Claim was silently lost (job reclaimed or cancelled
                                    # externally). Cancel the handler to abort side-effects.
                                    logger.warning(
                                        "job.claim_lost_on_renewal",
                                        job_id=current_job_id,
                                    )
                                    claim_lost = True
                                    if holder[0] is not None:
                                        holder[0].cancel()
                                    return
                            except Exception as exc:
                                logger.warning(
                                    "job.lease_renew_failed",
                                    job_id=current_job_id,
                                    error=str(exc),
                                    error_type=type(exc).__name__,
                                )

                    # Run handler as a task so the renewal loop can cancel it on claim loss.
                    handler_task = asyncio.create_task(self._handler(job.type, payload))
                    _handler_task_holder[0] = handler_task
                    renewal_task = asyncio.create_task(_renew_lease())

                    handler_exc: Exception | None = None
                    _external_cancelled = False

                    try:
                        await handler_task
                    except asyncio.CancelledError:
                        if not claim_lost:
                            # True external cancellation (not from claim-loss path).
                            # Ensure handler_task is stopped, then re-raise.
                            _external_cancelled = True
                            handler_task.cancel()
                            try:
                                await handler_task
                            except (asyncio.CancelledError, Exception):
                                pass
                        # If claim_lost: expected cancellation triggered by renewal;
                        # fall through to cleanup without re-raising.
                    except Exception as exc:
                        handler_exc = exc
                    finally:
                        renewal_task.cancel()
                        try:
                            await renewal_task
                        except asyncio.CancelledError:
                            pass
                        except Exception as exc:
                            logger.warning(
                                "job.lease_renew_teardown_failed",
                                job_id=job.id,
                                error=str(exc),
                                error_type=type(exc).__name__,
                            )

                    if _external_cancelled:
                        raise asyncio.CancelledError()

                    if claim_lost:
                        # Job was reclaimed by another worker; skip all status mutations
                        # to avoid overwriting the new owner's state.
                        logger.warning(
                            "job.claim_lost_skipping_update",
                            job_id=job.id,
                            job_type=job.type,
                            source_key=source_key,
                            attempt=job.attempts,
                        )
                    elif handler_exc is not None:
                        duration_ms = round((time.monotonic() - t0) * 1000)
                        is_retry = job.attempts < self._max_attempts
                        retry_after_seconds = 0
                        if is_retry and self._retry_backoff_base_seconds > 0:
                            retry_after_seconds = self._retry_backoff_base_seconds * (
                                2 ** (job.attempts - 1)
                            )
                        async with self._queue_io_guard:
                            if is_retry:
                                updated = await self._queue.release_for_retry(
                                    job.id,
                                    str(handler_exc),
                                    claim_attempt=job.attempts,
                                    retry_after_seconds=retry_after_seconds,
                                )
                            else:
                                updated = await self._queue.mark_failed(
                                    job.id,
                                    str(handler_exc),
                                    claim_attempt=job.attempts,
                                )
                        if updated:
                            if is_retry:
                                logger.info(
                                    "job.retry_scheduled",
                                    job_id=job.id,
                                    job_type=job.type,
                                    source_key=source_key,
                                    attempt=job.attempts,
                                    max_attempts=self._max_attempts,
                                    retry_after_seconds=retry_after_seconds,
                                    duration_ms=duration_ms,
                                    error=str(handler_exc),
                                    worker_id=worker_id,
                                    active_workers=current_active_workers,
                                    worker_count=self._worker_count,
                                )
                            else:
                                logger.info(
                                    "job.failed",
                                    job_id=job.id,
                                    job_type=job.type,
                                    source_key=source_key,
                                    attempt=job.attempts,
                                    max_attempts=self._max_attempts,
                                    duration_ms=duration_ms,
                                    error=str(handler_exc),
                                    worker_id=worker_id,
                                    active_workers=current_active_workers,
                                    worker_count=self._worker_count,
                                )
                        else:
                            logger.warning(
                                "job.claim_lost_on_terminal_transition",
                                job_id=job.id,
                                job_type=job.type,
                                source_key=source_key,
                                attempt=job.attempts,
                                worker_id=worker_id,
                                active_workers=current_active_workers,
                                worker_count=self._worker_count,
                            )
                    else:
                        duration_ms = round((time.monotonic() - t0) * 1000)
                        async with self._queue_io_guard:
                            updated = await self._queue.mark_done(
                                job.id, claim_attempt=job.attempts
                            )
                        if updated:
                            logger.info(
                                "job.done",
                                job_id=job.id,
                                job_type=job.type,
                                source_key=source_key,
                                attempt=job.attempts,
                                duration_ms=duration_ms,
                                worker_id=worker_id,
                                active_workers=current_active_workers,
                                worker_count=self._worker_count,
                            )
                        else:
                            logger.warning(
                                "job.claim_lost_on_terminal_transition",
                                job_id=job.id,
                                job_type=job.type,
                                source_key=source_key,
                                attempt=job.attempts,
                                worker_id=worker_id,
                                active_workers=current_active_workers,
                                worker_count=self._worker_count,
                            )

                async with processed_count_guard:
                    processed_count += 1
                await _set_worker_activity(worker_id, False)

        await asyncio.gather(
            *(worker(worker_id) for worker_id in range(1, self._worker_count + 1))
        )
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
        """Return the per-source concurrency key from the job payload.

        Producers *must* set ``source_lock`` to a non-empty string.  This is
        the explicit contract: the pool will never silently fall back to a
        global key, because that would serialize the entire pool and hide a
        missing-field bug until production load.

        Raises:
            KeyError: if ``source_lock`` is absent or blank.
        """
        value = payload.get("source_lock")
        if isinstance(value, str) and value.strip():
            return value.strip()
        raise KeyError(
            "job payload is missing a non-empty 'source_lock' field — "
            "all producers must set it explicitly"
        )
