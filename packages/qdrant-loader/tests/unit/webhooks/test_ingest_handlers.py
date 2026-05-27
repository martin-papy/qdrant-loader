import asyncio

import pytest

from qdrant_loader.webhooks.handlers import (
    enqueue_ingest_request,
    normalize_ingest_source_type,
)
from qdrant_loader.webhooks.queue_backend import FULL_SCAN, ChangeEvent, QueueBackendManager


class FakeQueueBackend:
    def __init__(self) -> None:
        self.events: list[ChangeEvent] = []

    async def enqueue(self, event: ChangeEvent) -> str:
        self.events.append(event)
        return "1"

    async def close(self) -> None:
        return None


@pytest.fixture
def fake_queue():
    backend = FakeQueueBackend()
    QueueBackendManager.set_backend(backend)
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
    assert result["operation"] == FULL_SCAN
    assert fake_queue.events[0].project_id is None
    assert fake_queue.events[0].source_type is None


def test_enqueue_ingest_requires_source_type_when_source_set(fake_queue):
    with pytest.raises(ValueError, match="source_type must be provided"):
        asyncio.run(
            enqueue_ingest_request(
                project_id="p1",
                source_type=None,
                source="my-repo",
            )
        )
