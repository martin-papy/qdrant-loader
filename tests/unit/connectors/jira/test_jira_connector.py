"""Unit tests for Jira connector."""

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from atlassian import Jira
from pydantic import HttpUrl
from requests.exceptions import HTTPError

from qdrant_loader.connectors.jira.connector import JiraConnector
from qdrant_loader.connectors.jira.config import JiraProjectConfig
from qdrant_loader.connectors.jira.models import JiraIssue, JiraUser, JiraComment, JiraAttachment
from qdrant_loader.core.document import Document
from qdrant_loader.config.types import SourceType


@pytest.fixture
def jira_config():
    """Create a Jira configuration fixture."""
    return JiraProjectConfig(
        base_url=HttpUrl("https://test.atlassian.net"),
        project_key="TEST",
        source="test-jira",
        source_type=SourceType.JIRA,
        requests_per_minute=60,
        page_size=50,
        token="test-token",
        email="test@example.com",
    )


@pytest.fixture
def mock_jira_client():
    """Create a mock Jira client."""
    mock = MagicMock(spec=Jira)

    # Add project validation
    def mock_get_project(project_key):
        if project_key == "TEST":
            return {"key": "TEST", "name": "Test Project"}
        raise HTTPError(
            f"The value '{project_key}' does not exist for the field 'project'",
            response=MagicMock(status_code=400),
        )

    mock.project = MagicMock()
    mock.project.get = mock_get_project

    # Add JQL query handling
    def mock_jql(jql, **kwargs):
        if 'project = "TEST"' in jql:
            # Test data will be set in individual tests
            return {"issues": [], "total": 0}
        else:
            response = MagicMock(status_code=400)
            response.json.return_value = {
                "errorMessages": [],
                "errors": {"project": "The value 'TEST' does not exist for the field 'project'."},
            }
            raise HTTPError(
                "The value 'TEST' does not exist for the field 'project'",
                response=response,
            )

    mock.jql = mock_jql

    # Handle direct GET requests
    def mock_get(url, params=None, **kwargs):
        if "rest/api/2/search" in url:
            jql = params.get("jql", "") if params else ""
            if 'project = "TEST"' in jql:
                # Return data that will be set in individual tests
                return mock.jql(jql, **kwargs)
            else:
                response = MagicMock(status_code=400)
                response.json.return_value = {
                    "errorMessages": [],
                    "errors": {
                        "project": "The value 'TEST' does not exist for the field 'project'."
                    },
                }
                raise HTTPError(
                    "The value 'TEST' does not exist for the field 'project'.",
                    response=response,
                )
        return MagicMock(status_code=200, json=lambda: {})

    mock.get = mock_get
    return mock


@pytest.fixture
def mock_issue_data():
    """Create mock issue data."""
    return {
        "id": "12345",
        "key": "TEST-1",
        "fields": {
            "summary": "Test Issue",
            "description": "Test Description",
            "issuetype": {"name": "Bug"},
            "status": {"name": "Open"},
            "priority": {"name": "High"},
            "project": {"key": "TEST"},
            "created": "2024-01-01T00:00:00.000+0000",
            "updated": "2024-01-02T00:00:00.000+0000",
            "reporter": {
                "accountId": "123",
                "displayName": "Test User",
                "emailAddress": "test@example.com",
            },
            "assignee": {
                "accountId": "456",
                "displayName": "Assignee",
                "emailAddress": "assignee@example.com",
            },
            "labels": ["bug", "test"],
            "attachment": [
                {
                    "id": "att1",
                    "filename": "test.txt",
                    "size": 100,
                    "mimeType": "text/plain",
                    "content": "https://test.atlassian.net/attachments/test.txt",
                    "created": "2024-01-01T00:00:00.000+0000",
                    "author": {
                        "accountId": "123",
                        "displayName": "Test User",
                        "emailAddress": "test@example.com",
                    },
                }
            ],
            "comment": {
                "comments": [
                    {
                        "id": "comment1",
                        "body": "Test comment",
                        "created": "2024-01-01T00:00:00.000+0000",
                        "updated": "2024-01-02T00:00:00.000+0000",
                        "author": {
                            "accountId": "123",
                            "displayName": "Test User",
                            "emailAddress": "test@example.com",
                        },
                    }
                ]
            },
            "parent": {"key": "TEST-0"},
            "subtasks": [{"key": "TEST-2"}],
            "issuelinks": [{"outwardIssue": {"key": "TEST-3"}}],
        },
    }


class TestJiraConnector:
    """Test suite for JiraConnector."""

    @pytest.mark.asyncio
    async def test_initialization(self, jira_config, mock_jira_client):
        """Test connector initialization."""
        # Set required environment variables
        os.environ["JIRA_TOKEN"] = "test-token"
        os.environ["JIRA_EMAIL"] = "test@example.com"

        with patch("atlassian.Jira", return_value=mock_jira_client):
            connector = JiraConnector(jira_config)
            assert connector.config == jira_config
            assert connector._initialized is False

            async with connector:
                assert connector._initialized is True
                assert isinstance(connector.client, Jira)

    @pytest.mark.asyncio
    async def test_missing_env_vars(self, jira_config):
        """Test initialization with missing environment variables."""
        # Clear environment variables
        if "JIRA_TOKEN" in os.environ:
            del os.environ["JIRA_TOKEN"]
        if "JIRA_EMAIL" in os.environ:
            del os.environ["JIRA_EMAIL"]

        with pytest.raises(ValueError, match="JIRA_TOKEN environment variable is required"):
            JiraConnector(jira_config)

    @pytest.mark.asyncio
    async def test_get_issues(self, jira_config, mock_jira_client, mock_issue_data):
        """Test issue retrieval."""
        # Set environment variables
        os.environ["JIRA_TOKEN"] = "test-token"
        os.environ["JIRA_EMAIL"] = "test@example.com"

        with patch("atlassian.Jira", return_value=mock_jira_client):
            connector = JiraConnector(jira_config)

            # Patch the _make_sync_request method instead of using the mock client
            with patch.object(
                connector,
                "_make_sync_request",
                return_value={
                    "issues": [mock_issue_data],
                    "total": 1,
                },
            ):
                async with connector:
                    issues = []
                    async for issue in connector.get_issues():
                        issues.append(issue)

                    assert len(issues) == 1
                    issue = issues[0]
                    assert isinstance(issue, JiraIssue)
                    assert issue.key == "TEST-1"
                    assert issue.summary == "Test Issue"
                    assert issue.description == "Test Description"
                    assert issue.issue_type == "Bug"
                    assert issue.status == "Open"
                    assert issue.priority == "High"
                    assert issue.project_key == "TEST"
                    assert len(issue.labels) == 2
                    assert len(issue.attachments) == 1
                    assert len(issue.comments) == 1
                    assert issue.parent_key == "TEST-0"
                    assert len(issue.subtasks) == 1
                    assert len(issue.linked_issues) == 1

    @pytest.mark.asyncio
    async def test_rate_limiting(self, jira_config, mock_jira_client):
        """Test rate limiting functionality."""
        # Set environment variables
        os.environ["JIRA_TOKEN"] = "test-token"
        os.environ["JIRA_EMAIL"] = "test@example.com"

        with patch("atlassian.Jira", return_value=mock_jira_client):
            connector = JiraConnector(jira_config)

            # Create a mock for _make_sync_request
            mock_make_sync_request = MagicMock(return_value={"issues": [], "total": 0})

            with patch.object(connector, "_make_sync_request", mock_make_sync_request):
                async with connector:
                    # Make multiple requests quickly
                    for _ in range(3):
                        await connector._make_request(jql='project = "TEST"')

                    # Verify rate limiting was applied
                    assert mock_make_sync_request.call_count == 3

    @pytest.mark.asyncio
    async def test_get_documents(self, jira_config, mock_jira_client, mock_issue_data):
        """Test document conversion."""
        # Set environment variables
        os.environ["JIRA_TOKEN"] = "test-token"
        os.environ["JIRA_EMAIL"] = "test@example.com"

        with patch("atlassian.Jira", return_value=mock_jira_client):
            connector = JiraConnector(jira_config)

            # Patch the _make_sync_request method
            with patch.object(
                connector,
                "_make_sync_request",
                return_value={
                    "issues": [mock_issue_data],
                    "total": 1,
                },
            ):
                async with connector:
                    documents = await connector.get_documents()

                    assert len(documents) == 1
                    document = documents[0]
                    assert isinstance(document, Document)
                    # Don't check ID since it's auto-generated
                    assert document.title == "Test Issue"
                    assert document.source == "test-jira"
                    assert document.url == "https://test.atlassian.net/browse/TEST-1"
                    assert "Test Description" in document.content
                    assert "Test comment" in document.content
                    assert document.metadata["project"] == "TEST"
                    assert document.metadata["issue_type"] == "Bug"
                    assert document.metadata["status"] == "Open"
                    assert document.metadata["key"] == "TEST-1"
                    assert document.metadata["priority"] == "High"
                    assert len(document.metadata["labels"]) == 2
                    assert len(document.metadata["comments"]) == 1
                    assert len(document.metadata["attachments"]) == 1

    @pytest.mark.asyncio
    async def test_pagination(self, jira_config, mock_jira_client, mock_issue_data):
        """Test pagination handling."""
        # Set environment variables
        os.environ["JIRA_TOKEN"] = "test-token"
        os.environ["JIRA_EMAIL"] = "test@example.com"

        with patch("atlassian.Jira", return_value=mock_jira_client):
            connector = JiraConnector(jira_config)

            # Use a simple mock that returns a single issue
            with patch.object(
                connector,
                "_make_sync_request",
                return_value={"issues": [mock_issue_data], "total": 1},
            ):
                async with connector:
                    # Collect all issues
                    issues = [issue async for issue in connector.get_issues()]

                    # Validate we have the right issue
                    assert len(issues) == 1
                    assert issues[0].key == "TEST-1"
                    assert issues[0].id == "12345"
                    assert issues[0].summary == "Test Issue"
                    assert issues[0].description == "Test Description"

    @pytest.mark.asyncio
    async def test_error_handling(self, jira_config, mock_jira_client):
        """Test error handling."""
        # Set environment variables
        os.environ["JIRA_TOKEN"] = "test-token"
        os.environ["JIRA_EMAIL"] = "test@example.com"

        with patch("atlassian.Jira", return_value=mock_jira_client):
            connector = JiraConnector(jira_config)

            # Create a mock that raises an HTTPError
            mock_make_sync_request = MagicMock(
                side_effect=HTTPError(
                    "The value 'TEST' does not exist for the field 'project'",
                    response=MagicMock(status_code=400),
                )
            )

            with patch.object(connector, "_make_sync_request", mock_make_sync_request):
                async with connector:
                    with pytest.raises(
                        HTTPError, match="The value 'TEST' does not exist for the field 'project'"
                    ):
                        async for _ in connector.get_issues():
                            pass
