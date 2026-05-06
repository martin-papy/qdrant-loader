import pytest

from qdrant_loader.webhooks.handlers import normalize_source_type, process_webhook_event


class DummySettings:
    pass


@pytest.mark.asyncio
async def test_normalize_source_type_accepts_known_values():
    assert normalize_source_type("Jira") == "jira"
    assert normalize_source_type("confluence") == "confluence"
    assert normalize_source_type("PublicDocs") == "publicdocs"


@pytest.mark.asyncio
async def test_normalize_source_type_rejects_unknown_value():
    with pytest.raises(ValueError):
        normalize_source_type("unknown")


@pytest.mark.asyncio
async def test_process_webhook_event_calls_ingestion(monkeypatch):
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

    await process_webhook_event(
        project_id="project1",
        source_type="jira",
        source="my-jira-source",
        payload={"event": "issue_updated"},
        force=True,
    )

    assert called["args"]["project"] == "project1"
    assert called["args"]["source_type"] == "jira"
    assert called["args"]["source"] == "my-jira-source"
    assert called["args"]["force"] is True
