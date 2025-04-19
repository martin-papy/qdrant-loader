"""Integration tests for the Jira connector."""

import os
from datetime import datetime, timedelta, timezone

import pytest

from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.jira import JiraConnector
from qdrant_loader.connectors.jira.config import JiraProjectConfig


@pytest.mark.asyncio
async def test_connector_initialization(jira_connector):
    """Test initializing the Jira connector."""
    assert jira_connector is not None
    assert jira_connector.config is not None
    assert jira_connector.client is not None


@pytest.mark.asyncio
async def test_get_issues(jira_connector):
    """Test fetching issues from Jira."""
    issues = []
    async for issue in jira_connector.get_issues():
        issues.append(issue)
    assert len(issues) > 0


@pytest.mark.asyncio
async def test_get_issues_with_filters(jira_connector):
    """Test fetching issues with filters."""
    # Get issues updated in the last 7 days
    start_date = datetime.now(timezone.utc) - timedelta(
        days=365
    )  # Look back 1 year instead of 7 days
    issues = []
    async for issue in jira_connector.get_issues(updated_after=start_date):
        issues.append(issue)
        # Normalize timezones before comparison
        normalized_updated = issue.updated.astimezone(timezone.utc)
        assert (
            normalized_updated >= start_date
        ), f"Issue {issue.key} was updated at {normalized_updated} which is before start date {start_date}"


@pytest.mark.asyncio
async def test_get_issues_with_pagination(jira_connector):
    """Test fetching issues with pagination."""
    # Get first page
    issues_page1 = []
    async for issue in jira_connector.get_issues():
        issues_page1.append(issue)
        if len(issues_page1) >= 10:
            break

    assert len(issues_page1) > 0
    assert len(issues_page1) <= 10


@pytest.mark.asyncio
async def test_get_issues_error_handling(jira_connector):
    """Test error handling when fetching issues."""
    # Test with invalid project key
    invalid_config = JiraProjectConfig(
        source_type=SourceType.JIRA,
        source="test",
        base_url=jira_connector.config.base_url,
        project_key="INVALID",
        requests_per_minute=60,
        page_size=50,
    )
    invalid_connector = JiraConnector(invalid_config)

    with pytest.raises(ValueError):
        async for _ in invalid_connector.get_issues():
            pass  # We expect an error before getting any issues


def test_environment_variable_substitution(test_settings):
    """Test that environment variables are properly substituted in the configuration."""
    jira_settings = test_settings.sources_config.jira["test-project"]

    # Check that environment variables were substituted
    assert str(jira_settings.base_url) == os.getenv("JIRA_URL"), "JIRA_URL not properly substituted"
    assert jira_settings.project_key == os.getenv(
        "JIRA_PROJECT_KEY"
    ), "JIRA_PROJECT_KEY not properly substituted"
    assert jira_settings.token == os.getenv("JIRA_TOKEN"), "JIRA_TOKEN not properly substituted"
    assert jira_settings.email == os.getenv("JIRA_EMAIL"), "JIRA_EMAIL not properly substituted"
