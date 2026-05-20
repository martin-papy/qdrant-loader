from fastapi.testclient import TestClient
import pytest

from qdrant_loader.webhooks.server import app
from qdrant_loader.webhooks.handlers import process_ingest_request


class DummySettings:
    pass


@pytest.mark.asyncio
async def test_process_ingest_request_calls_run_pipeline_ingestion(monkeypatch):
    called = {}

    async def fake_run_pipeline_ingestion(
        settings,
        qdrant_manager,
        project,
        source_type,
        source,
        force,
        metrics_dir=None,
    ):
        called["args"] = {
            "settings": settings,
            "qdrant_manager": qdrant_manager,
            "project": project,
            "source_type": source_type,
            "source": source,
            "force": force,
        }

    class DummyQdrantManager:
        def __init__(self, settings):
            self.settings = settings

    monkeypatch.setattr(
        "qdrant_loader.webhooks.handlers.get_settings",
        lambda: DummySettings(),
    )
    monkeypatch.setattr(
        "qdrant_loader.webhooks.handlers.QdrantManager",
        DummyQdrantManager,
    )
    monkeypatch.setattr(
        "qdrant_loader.webhooks.handlers.run_pipeline_ingestion",
        fake_run_pipeline_ingestion,
    )

    await process_ingest_request(
        project_id="project1",
        source_type="jira",
        source="my-jira-source",
        force=True,
    )

    assert called["args"]["project"] == "project1"
    assert called["args"]["source_type"] == "jira"
    assert called["args"]["source"] == "my-jira-source"
    assert called["args"]["force"] is True


def test_ingest_route_calls_process_ingest_request(monkeypatch):
    called = {}

    async def fake_process_ingest_request(
        project_id,
        source_type,
        source,
        force=False,
    ):
        called["args"] = {
            "project_id": project_id,
            "source_type": source_type,
            "source": source,
            "force": force,
        }

    monkeypatch.setattr(
        "qdrant_loader.webhooks.server.process_ingest_request",
        fake_process_ingest_request,
    )
    monkeypatch.setenv("WEBHOOK_SECRET", "secret")

    client = TestClient(app)
    response = client.post(
        "/ingest?project_id=project1&source_type=jira&source=my-jira-source&force=true&token=secret"
    )

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    assert called["args"]["project_id"] == "project1"
    assert called["args"]["source_type"] == "jira"
    assert called["args"]["source"] == "my-jira-source"
    assert called["args"]["force"] is True


def test_ingest_route_returns_422_for_invalid_request(monkeypatch):
    async def fake_process_ingest_request(
        project_id,
        source_type,
        source,
        force=False,
    ):
        raise ValueError("Project 'test-project' not found or has no configuration")

    monkeypatch.setattr(
        "qdrant_loader.webhooks.server.process_ingest_request",
        fake_process_ingest_request,
    )
    monkeypatch.setenv("WEBHOOK_SECRET", "secret")

    client = TestClient(app)
    response = client.post(
        "/ingest?project_id=test-project&source_type=jira&source=my-source&force=true&token=secret"
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Project 'test-project' not found or has no configuration"
