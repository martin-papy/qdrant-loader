"""Local conftest for code parser tests.

Overrides the session-scoped `setup_test_environment` autouse fixture from the
root conftest so these tests can run without a `config.test.yaml` file.
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """No-op override — these tests use mocks and need no real config file."""
    yield
