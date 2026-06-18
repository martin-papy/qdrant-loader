import asyncio

import pytest
from qdrant_loader.core.worker.job_types import JobType
from qdrant_loader.webhooks.handlers import (
    enqueue_ingest_request,
    normalize_ingest_source_type,
)
from qdrant_loader.webhooks.queue_backend import (
    ChangeEvent,
    QueueBackendManager,
)


class FakeQueueBackend:
    def __init__(self) -> None:
        self.events: list[ChangeEvent] = []

    async def enqueue(self, event: ChangeEvent) -> str:
        self.events.append(event)
        return "1"

    async def close(self) -> None:
        return None


class FakeJob:
    def __init__(self, job_id: int) -> None:
        self.id = job_id


class FakeJobQueue:
    """Fakes the SQLiteJobQueue used by enqueue_ingest_request."""

    def __init__(self) -> None:
        self.jobs: list[tuple[str, dict]] = []

    async def enqueue(self, job_type: str, payload: dict) -> FakeJob:
        self.jobs.append((job_type, payload))
        return FakeJob(len(self.jobs))


@pytest.fixture
def fake_queue():
    backend = FakeQueueBackend()
    backend.job_queue = FakeJobQueue()
    QueueBackendManager.set_backend(backend, backend.job_queue)
    yield backend
    QueueBackendManager.reset()


def test_normalize_ingest_source_type_accepts_all_connectors():
    assert normalize_ingest_source_type("Jira") == "jira"
    assert normalize_ingest_source_type("confluence") == "confluence"
    assert normalize_ingest_source_type("git") == "git"


def test_normalize_ingest_source_type_rejects_unknown():
    with pytest.raises(ValueError, match="Unsupported source type"):
        normalize_ingest_source_type("unknown")


def test_enqueue_ingest_all_projects(fake_queue):
    result = asyncio.run(
        enqueue_ingest_request(
            project_id=None,
            source_type=None,
            source=None,
            force=False,
        )
    )
    assert result["operation"] == JobType.BULK_INGEST
    job_type, payload = fake_queue.job_queue.jobs[0]
    assert job_type == JobType.BULK_INGEST
    assert payload["project_id"] == ""
    assert payload["source_type"] == ""


def test_enqueue_ingest_requires_source_type_when_source_set(fake_queue):
    with pytest.raises(ValueError, match="source_type must be provided"):
        asyncio.run(
            enqueue_ingest_request(
                project_id="p1",
                source_type=None,
                source="my-repo",
            )
        )
