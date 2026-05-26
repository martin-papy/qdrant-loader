import asyncio

import pytest

from qdrant_loader.webhooks.handlers import (
    enqueue_webhook_event,
    normalize_source_type,
)
from qdrant_loader.webhooks.queue_backend import (
    FULL_SCAN,
    SINGLE_UPSERT,
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


@pytest.fixture
def fake_queue():
    backend = FakeQueueBackend()
    QueueBackendManager.set_backend(backend)
    yield backend
    QueueBackendManager.reset()


def test_normalize_source_type_accepts_jira():
    assert normalize_source_type("Jira") == "jira"
    assert normalize_source_type("jira") == "jira"


def test_normalize_source_type_rejects_non_jira_sources():
    with pytest.raises(ValueError, match="Unsupported source type"):
        normalize_source_type("confluence")
    with pytest.raises(ValueError, match="Unsupported source type"):
        normalize_source_type("git")


def test_enqueue_single_upsert_for_jira_webhook(fake_queue):
    result = asyncio.run(enqueue_webhook_event(
        project_id="project1",
        source_type="jira",
        source="my-jira",
        payload={
            "webhookEvent": "jira:issue_created",
            "issue": {"key": "ABC-1", "id": "1"},
        },
    ))

    assert result["operation"] == SINGLE_UPSERT
    assert result["entity_id"] == "ABC-1"
    assert len(fake_queue.events) == 1
    assert fake_queue.events[0].operation == SINGLE_UPSERT


def test_enqueue_full_scan_when_force(fake_queue):
    result = asyncio.run(enqueue_webhook_event(
        project_id="project1",
        source_type="jira",
        source="my-jira",
        payload={},
        force=True,
    ))

    assert result["operation"] == FULL_SCAN
    assert fake_queue.events[0].force is True


def test_enqueue_full_scan_when_unparseable(fake_queue):
    result = asyncio.run(enqueue_webhook_event(
        project_id=None,
        source_type="jira",
        source="my-jira",
        payload={"unknown": True},
    ))

    assert result["operation"] == FULL_SCAN
