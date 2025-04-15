"""Test configuration for Jira integration tests."""

import pytest
from qdrant_loader.connectors.jira.config import JiraConfig
from qdrant_loader.connectors.jira import JiraConnector

@pytest.fixture
def jira_config(test_settings):
    """Create a JiraConfig instance from test settings."""
    jira_settings = test_settings.sources_config.jira["test-project"]
    return JiraConfig(
        base_url=jira_settings.base_url,
        project_key=jira_settings.project_key,
        requests_per_minute=jira_settings.requests_per_minute,
        page_size=jira_settings.page_size,
        process_attachments=True,
        track_last_sync=True,
        api_token=jira_settings.token,
        email=jira_settings.email
    )

@pytest.fixture
def jira_connector(jira_config):
    """Create a JiraConnector instance."""
    return JiraConnector(jira_config)