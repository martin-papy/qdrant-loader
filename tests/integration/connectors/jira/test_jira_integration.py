"""Integration tests for the Jira connector."""

import os
import pytest
from pathlib import Path
from datetime import datetime, timedelta, timezone
import asyncio
from qdrant_loader.connectors.jira import JiraConnector
from qdrant_loader.connectors.jira.config import JiraConfig
from qdrant_loader.config import Settings, SourcesConfig

@pytest.fixture
def test_settings():
    """Load test settings from environment and config file."""
    # Load environment variables
    env_path = Path(__file__).parent.parent.parent.parent / ".env.test"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value

    # Load configuration
    config_path = Path(__file__).parent.parent.parent.parent / "config.test.yaml"
    if not config_path.exists():
        pytest.fail("Test configuration file not found")
    
    return Settings.from_yaml(config_path)

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
        track_last_sync=True
    )

@pytest.fixture
def connector(jira_config):
    """Create a JiraConnector instance."""
    return JiraConnector(jira_config)

@pytest.mark.asyncio
async def test_connector_initialization(connector):
    """Test initializing the Jira connector."""
    assert connector is not None
    assert connector.config is not None
    assert connector.client is not None

@pytest.mark.asyncio
async def test_get_issues(connector):
    """Test fetching issues from Jira."""
    issues = []
    async for issue in connector.get_issues():
        issues.append(issue)
    assert len(issues) > 0

@pytest.mark.asyncio
async def test_get_issues_with_filters(connector):
    """Test fetching issues with filters."""
    # Get issues updated in the last 7 days
    start_date = datetime.now(timezone.utc) - timedelta(days=7)
    issues = []
    async for issue in connector.get_issues(updated_after=start_date):
        issues.append(issue)
        # Verify all issues were updated after the start date
        assert issue.updated >= start_date

@pytest.mark.asyncio
async def test_get_issues_with_pagination(connector):
    """Test fetching issues with pagination."""
    # Get first page
    issues_page1 = []
    async for issue in connector.get_issues():
        issues_page1.append(issue)
        if len(issues_page1) >= 10:
            break
    
    assert len(issues_page1) > 0
    assert len(issues_page1) <= 10

@pytest.mark.asyncio
async def test_get_issues_error_handling(connector):
    """Test error handling when fetching issues."""
    # Test with invalid project key
    invalid_config = JiraConfig(
        base_url=connector.config.base_url,
        project_key="INVALID",
        requests_per_minute=60,
        page_size=50
    )
    invalid_connector = JiraConnector(invalid_config)

    with pytest.raises(Exception):
        async for _ in invalid_connector.get_issues():
            pass  # We expect an error before getting any issues 