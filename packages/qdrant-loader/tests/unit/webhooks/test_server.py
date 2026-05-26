from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from qdrant_loader.webhooks.queue_backend import ChangeEvent, QueueBackendManager
from qdrant_loader.webhooks.server import app


class FakeQueueBackend:
    def __init__(self) -> None:
        self.events: list[ChangeEvent] = []

    async def enqueue(self, event: ChangeEvent) -> str:
        self.events.append(event)
        return str(len(self.events))

    async def close(self) -> None:
        return None


@pytest.fixture
def mock_queue_backend(monkeypatch):
    backend = FakeQueueBackend()

    async def fake_initialize():
        QueueBackendManager.set_backend(backend)
        return backend

    async def fake_shutdown():
        QueueBackendManager.reset()

    async def fake_worker(stop_event: asyncio.Event):
        stop_event.set()

    monkeypatch.setattr(QueueBackendManager, "initialize", fake_initialize)
    monkeypatch.setattr(QueueBackendManager, "shutdown", fake_shutdown)
    monkeypatch.setattr(
        "qdrant_loader.webhooks.server.run_webhook_worker",
        fake_worker,
    )
    return backend


def test_webhook_project_route_enqueues_single_event(mock_queue_backend, monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "secret")

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/projects/project1/jira/my-jira-source?token=secret",
            json={
                "webhookEvent": "jira:issue_updated",
                "issue": {"key": "TEST-1", "id": "10001"},
            },
        )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert body["operation"] == "SINGLE_UPSERT"
    assert body["entity_id"] == "TEST-1"
    assert len(mock_queue_backend.events) == 1
    assert mock_queue_backend.events[0].project_id == "project1"


def test_webhook_source_route_enqueues_event(mock_queue_backend, monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "secret")

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/jira/my-jira-source?token=secret",
            json={
                "webhookEvent": "jira:issue_deleted",
                "issue": {"key": "TEST-2", "id": "10002"},
            },
        )

    assert response.status_code == 202
    body = response.json()
    assert body["operation"] == "SINGLE_DELETE"
    assert mock_queue_backend.events[0].project_id is None


def test_webhook_requires_auth(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "secret")

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/jira/my-jira-source?token=wrong-secret",
            json={},
        )

    assert response.status_code == 401
    assert "Invalid or missing webhook token" in response.json()["detail"]


def test_webhook_rejects_non_jira_source(mock_queue_backend, monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "secret")

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/confluence/my-source?token=secret",
            json={},
        )

    assert response.status_code == 400
    assert "Unsupported source type" in response.json()["detail"]


def test_ingest_route_enqueues_full_scan(mock_queue_backend, monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "secret")

    with TestClient(app) as client:
        response = client.post(
            "/ingest?project_id=project1&source_type=jira&source=my-source&force=true&token=secret",
        )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert body["operation"] == "FULL_SCAN"
    assert body["force"] is True
    assert len(mock_queue_backend.events) == 1
    event = mock_queue_backend.events[0]
    assert event.project_id == "project1"
    assert event.source_type == "jira"
    assert event.source == "my-source"
    assert event.force is True


def test_ingest_route_accepts_bearer_auth(mock_queue_backend, monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "secret")

    with TestClient(app) as client:
        response = client.post(
            "/ingest?project_id=project1&source_type=jira&source=my-source",
            headers={"Authorization": "Bearer secret"},
        )

    assert response.status_code == 202
    assert response.json()["queued"] is True


def test_ingest_route_rejects_missing_source_type(mock_queue_backend, monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "secret")

    with TestClient(app) as client:
        response = client.post(
            "/ingest?project_id=test-project&source=my-source&token=secret",
        )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "source_type must be provided when source is specified."
    )
