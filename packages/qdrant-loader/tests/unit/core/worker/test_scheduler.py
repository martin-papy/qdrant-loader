from __future__ import annotations

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

    async def list(self, status: str | None = None, limit: int = 100):
        if status is None:
            all_jobs = []
            for items in self.active_by_status.values():
                all_jobs.extend(items)
            return all_jobs[:limit]
        return self.active_by_status.get(status, [])[:limit]


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
