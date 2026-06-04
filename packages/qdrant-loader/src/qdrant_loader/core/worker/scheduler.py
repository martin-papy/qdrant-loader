from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable

from qdrant_loader.config.models import ProjectsConfig
from qdrant_loader.config.workers import IncrementalPullScheduleConfig
from qdrant_loader.core.worker.job_types import JobType
from qdrant_loader.core.worker.queue import JobQueue
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class IncrementalPullScheduler:
    """Create periodic INCREMENTAL_PULL jobs using a monotonic clock."""

    SOURCE_TYPES = ("publicdocs", "git", "confluence", "jira", "localfile")

    def __init__(
        self,
        queue: JobQueue,
        projects_config: ProjectsConfig,
        schedule: IncrementalPullScheduleConfig,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        self._queue = queue
        self._projects_config = projects_config
        self._schedule = schedule
        self._monotonic = monotonic or time.monotonic

    async def run(self, stop_event: asyncio.Event) -> None:
        """Run periodic scheduling loop until stop_event is set."""
        if not self._schedule.enabled:
            logger.info("scheduler.incremental_pull.disabled")
            return

        interval = float(self._schedule.interval_seconds)
        next_run_at = self._monotonic() + interval

        logger.info(
            "scheduler.incremental_pull.started",
            interval_seconds=self._schedule.interval_seconds,
        )

        while not stop_event.is_set():
            now = self._monotonic()
            if now >= next_run_at:
                created = await self.run_once()
                logger.info("scheduler.incremental_pull.tick", created=created)

                while next_run_at <= now:
                    next_run_at += interval

            timeout = max(0.0, min(1.0, next_run_at - self._monotonic()))
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=timeout)
            except TimeoutError:
                pass

        logger.info("scheduler.incremental_pull.stopped")

    async def run_once(self) -> int:
        """Attempt to enqueue all due INCREMENTAL_PULL jobs once."""
        if not self._schedule.enabled:
            return 0

        dedup_keys = await self._load_active_dedup_keys()
        created = 0

        for project_id, source_type, source_name in self._iter_project_sources():
            dedup_key = (
                JobType.INCREMENTAL_PULL.value,
                project_id,
                source_type,
                source_name,
            )
            if dedup_key in dedup_keys:
                continue

            payload = dict(self._schedule.payload_defaults)
            payload.update(
                {
                    "project_id": project_id,
                    "source_type": source_type,
                    "source": source_name,
                    "source_lock": f"{project_id}:{source_type}:{source_name}",
                    "force": False,
                }
            )

            await self._queue.enqueue(JobType.INCREMENTAL_PULL, payload)
            dedup_keys.add(dedup_key)
            created += 1

        return created

    def _iter_project_sources(self):
        for project in self._projects_config.projects.values():
            for source_type in self.SOURCE_TYPES:
                source_map = getattr(project.sources, source_type, {}) or {}
                for source_name in source_map.keys():
                    yield project.project_id, source_type, source_name

    async def _load_active_dedup_keys(self) -> set[tuple[str, str, str, str]]:
        """Load all active (non-terminal) job dedup keys to avoid re-enqueueing.

        Paginates through each configured status (dedup_statuses) to ensure all
        active jobs are accounted for, even when a status has >10k entries.
        Scaling: 100k PENDING jobs → ~100 queries of 1k each, O(n) memory constant.

        **Offset pagination caveat:** If new jobs are enqueued during pagination
        (by other workers or the pool), rows can shift and be skipped. This is
        acceptable because:
        1. Unlikely: pagination completes in <100ms for 10k jobs; concurrent
           enqueues during this window are rare.
        2. Dedup only checks jobs active at the START of run_once(). Jobs
           enqueued mid-pagination are not yet in dedup_keys anyway.
        3. Worst case: duplicate enqueue for a source, caught by downstream
           dedup logic or visibility lease enforcement.

        Future: Consider keyset pagination (WHERE (enqueued_at, id) > ...) if
        this risk becomes unacceptable.

        Returns:
            Set of (job_type, project_id, source_type, source_name) tuples.
        """
        keys: set[tuple[str, str, str, str]] = set()

        # JobQueue protocol only supports filtering by one status at a time.
        # Paginate through each configured status to avoid missing jobs when
        # a status has >limit entries. Continue until list returns < limit results.
        for status in self._schedule.dedup_statuses:
            offset = 0
            page_size = 1000
            while True:
                jobs = await self._queue.list(
                    status=status, limit=page_size, offset=offset
                )
                if not jobs:
                    break
                for job in jobs:
                    key = self._job_dedup_key(job)
                    if key is not None:
                        keys.add(key)
                if len(jobs) < page_size:
                    break
                offset += page_size

        return keys

    @staticmethod
    def _job_dedup_key(job) -> tuple[str, str, str, str] | None:
        if getattr(job, "type", None) != JobType.INCREMENTAL_PULL.value:
            return None

        try:
            payload = json.loads(job.payload_json)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

        if not isinstance(payload, dict):
            return None

        project_id = payload.get("project_id")
        source_type = payload.get("source_type")
        source_name = payload.get("source")
        if not all(
            isinstance(v, str) and v.strip()
            for v in (project_id, source_type, source_name)
        ):
            return None

        return (
            "INCREMENTAL_PULL",
            project_id.strip(),
            source_type.strip(),
            source_name.strip(),
        )
