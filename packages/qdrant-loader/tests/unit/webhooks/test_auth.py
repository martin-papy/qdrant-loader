import asyncio

import pytest
from fastapi import HTTPException

from qdrant_loader.webhooks.auth import (
    _get_webhook_secret_from_env,
    get_webhook_secret,
    verify_webhook_token,
)


@pytest.fixture(autouse=True)
def clear_secret_cache():
    _get_webhook_secret_from_env.cache_clear()
    yield
    _get_webhook_secret_from_env.cache_clear()


def test_get_webhook_secret_global(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "global-secret")
    assert asyncio.run(get_webhook_secret()) == "global-secret"


def test_get_webhook_secret_per_project(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "global-secret")
    monkeypatch.setenv("WEBHOOK_SECRETS", '{"project1": "project-secret"}')
    assert asyncio.run(get_webhook_secret(project_id="project1")) == "project-secret"
    assert asyncio.run(get_webhook_secret(project_id="other")) == "global-secret"


def test_verify_webhook_token_accepts_valid_secret(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "secret")
    asyncio.run(
        verify_webhook_token(
            project_id=None,
            webhook_token="secret",
            authorization=None,
        )
    )


def test_verify_webhook_token_rejects_invalid(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "secret")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            verify_webhook_token(
                project_id=None,
                webhook_token="wrong",
                authorization=None,
            )
        )
    assert exc_info.value.status_code == 401
