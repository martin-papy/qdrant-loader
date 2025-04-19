"""Test configuration for Jira integration tests."""

import pytest

from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.jira import JiraConnector
from qdrant_loader.connectors.jira.config import JiraProjectConfig
from qdrant_loader.core.state.state_manager import StateManager


@pytest.fixture
def state_manager(test_settings):
    """Create a real StateManager instance for integration tests."""
    return StateManager(test_settings.global_config.state_management)


@pytest.fixture
def jira_config(test_settings):
    """Create a JiraProjectConfig instance from test settings."""
    jira_settings = test_settings.sources_config.jira["test-project"]
    return JiraProjectConfig(
        source_type=SourceType.JIRA,
        source="test-project",
        base_url=jira_settings.base_url,
        project_key=jira_settings.project_key,
        requests_per_minute=jira_settings.requests_per_minute,
        page_size=jira_settings.page_size,
        process_attachments=True,
        track_last_sync=True,
        token=jira_settings.token,
        email=jira_settings.email,
    )


@pytest.fixture
def jira_connector(jira_config):
    """Create a JiraConnector instance."""
    return JiraConnector(jira_config)
