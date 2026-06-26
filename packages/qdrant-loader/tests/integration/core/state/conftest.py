"""Shared fixtures for state-layer integration tests (SQLite + Postgres)."""

import os

import pytest
from qdrant_loader.core.state.utils import _normalize_async_url


@pytest.fixture(scope="session")
def postgres_url():
    """A live Postgres async URL, or skip if none is available.

    Precedence: TEST_POSTGRES_URL env (e.g. the docker-compose Postgres or a CI
    service), else a throwaway testcontainers Postgres, else skip the param.
    """
    env_url = os.getenv("TEST_POSTGRES_URL")
    if env_url:
        yield _normalize_async_url(env_url)
        return

    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        pytest.skip("testcontainers not installed; set TEST_POSTGRES_URL to run PG tests")
        return

    try:
        container = PostgresContainer("postgres:16-alpine", driver="asyncpg")
        container.start()
    except Exception as exc:  # Docker not running / image pull failed
        pytest.skip(f"Postgres unavailable (Docker?): {exc}")
        return

    try:
        yield container.get_connection_url()  # postgresql+asyncpg://...
    finally:
        container.stop()
