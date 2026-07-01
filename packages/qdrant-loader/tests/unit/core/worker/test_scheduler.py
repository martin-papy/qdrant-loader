from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

import pytest
from qdrant_loader.config.models import ProjectConfig, ProjectsConfig
from qdrant_loader.config.sources import SourcesConfig
from qdrant_loader.config.workers import IncrementalPullScheduleConfig
from qdrant_loader.core.worker.scheduler import IncrementalPullScheduler


@dataclass
class _FakeJob:
    type: str
    payload_json: str
    status: str


class _FakeQueue:
    def __init__(self):
        self.enqueued: list[tuple[str, dict]] = []
        self.active_by_status: dict[str, list[_FakeJob]] = {}

    async def enqueue(self, job_type: str, payload: dict):
        self.enqueued.append((job_type, payload))
        return _FakeJob(
            type=job_type, payload_json=json.dumps(payload), status="pending"
        )

    async def list(self, status: str | None = None, limit: int = 100, offset: int = 0):
        if status is None:
            all_jobs = []
            for items in self.active_by_status.values():
                all_jobs.extend(items)
            return all_jobs[offset : offset + limit]
        jobs = self.active_by_status.get(status, [])
        return jobs[offset : offset + limit]


def _projects_config() -> ProjectsConfig:
    sources = SourcesConfig()
    sources.git = {"repo-a": object()}
    sources.jira = {"jira-a": object()}
    project = ProjectConfig(
        project_id="demo",
        display_name="Demo",
        sources=sources,
    )
    return ProjectsConfig(projects={"demo": project})


@pytest.mark.asyncio
async def test_scheduler_enqueues_incremental_pull_for_all_sources():
    queue = _FakeQueue()
    schedule = IncrementalPullScheduleConfig(enabled=True, interval=300)
    scheduler = IncrementalPullScheduler(queue, _projects_config(), schedule)

    created = await scheduler.run_once()

    assert created == 2
    assert len(queue.enqueued) == 2
    assert {payload["source"] for _, payload in queue.enqueued} == {"repo-a", "jira-a"}
    assert all(job_type == "INCREMENTAL_PULL" for job_type, _ in queue.enqueued)


@pytest.mark.asyncio
async def test_scheduler_dedups_against_pending_and_running():
    queue = _FakeQueue()
    queue.active_by_status = {
        "pending": [
            _FakeJob(
                type="INCREMENTAL_PULL",
                payload_json=json.dumps(
                    {
                        "project_id": "demo",
                        "source_type": "git",
                        "source": "repo-a",
                    }
                ),
                status="pending",
            )
        ],
        "running": [
            _FakeJob(
                type="INCREMENTAL_PULL",
                payload_json=json.dumps(
                    {
                        "project_id": "demo",
                        "source_type": "jira",
                        "source": "jira-a",
                    }
                ),
                status="running",
            )
        ],
    }

    schedule = IncrementalPullScheduleConfig(
        enabled=True,
        interval="5m",
        dedup_statuses=["pending", "running"],
    )
    scheduler = IncrementalPullScheduler(queue, _projects_config(), schedule)

    created = await scheduler.run_once()

    assert created == 0
    assert queue.enqueued == []


@pytest.mark.asyncio
async def test_scheduler_keeps_canonical_identity_over_payload_defaults():
    queue = _FakeQueue()
    schedule = IncrementalPullScheduleConfig(
        enabled=True,
        interval=300,
        payload_defaults={
            "project_id": "wrong",
            "source_type": "wrong",
            "source": "wrong",
            "source_lock": "wrong:lock",
            "force": True,
            "custom": "ok",
        },
    )
    scheduler = IncrementalPullScheduler(queue, _projects_config(), schedule)

    created = await scheduler.run_once()

    assert created == 2
    first_payload = queue.enqueued[0][1]
    assert first_payload["project_id"] == "demo"
    assert first_payload["source_type"] in {"git", "jira"}
    assert first_payload["source"] in {"repo-a", "jira-a"}
    assert first_payload["source_lock"] in {
        "demo:git:repo-a",
        "demo:jira:jira-a",
    }
    assert first_payload["force"] is False
    assert first_payload["custom"] == "ok"


@pytest.mark.asyncio
async def test_scheduler_run_ticks_immediately_on_startup():
    queue = _FakeQueue()
    schedule = IncrementalPullScheduleConfig(enabled=True, interval=300)
    scheduler = IncrementalPullScheduler(queue, _projects_config(), schedule)
    stop_event = asyncio.Event()

    async def _stop_soon():
        await asyncio.sleep(0.05)
        stop_event.set()

    await asyncio.gather(scheduler.run(stop_event), _stop_soon())

    # Startup tick should enqueue once immediately (without waiting 300s).
    assert len(queue.enqueued) == 2
    assert {payload["source"] for _, payload in queue.enqueued} == {"repo-a", "jira-a"}
