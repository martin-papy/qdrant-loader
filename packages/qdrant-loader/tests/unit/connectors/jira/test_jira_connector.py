"""Unit tests for Jira connector."""

import os
from unittest.mock import MagicMock, patch

import pytest
from pydantic import HttpUrl
from requests.exceptions import HTTPError

from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.jira.config import JiraDeploymentType, JiraProjectConfig
from qdrant_loader.connectors.jira.connector import JiraConnector
from qdrant_loader.connectors.jira.models import (
    JiraIssue,
)
from qdrant_loader.core.document import Document


@pytest.fixture
def jira_cloud_config():
    """Create a Jira Cloud configuration fixture."""
    return JiraProjectConfig(
        base_url=HttpUrl("https://test.atlassian.net"),
        deployment_type=JiraDeploymentType.CLOUD,
        project_key="TEST",
        source="test-jira",
        source_type=SourceType.JIRA,
        requests_per_minute=60,
        page_size=50,
        token="test-token",
        email="test@example.com",
    )


@pytest.fixture
def jira_datacenter_config():
    """Create a Jira Data Center configuration fixture."""
    return JiraProjectConfig(
        base_url=HttpUrl("https://jira.company.com"),
        deployment_type=JiraDeploymentType.DATACENTER,
        project_key="TEST",
        source="test-jira",
        source_type=SourceType.JIRA,
        requests_per_minute=60,
        page_size=50,
        token="test-pat-token",
        email=None,  # Not required for Data Center
    )


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
    async def test_cloud_initialization(self, jira_cloud_config):
        """Test Cloud connector initialization."""
        connector = JiraConnector(jira_cloud_config)
        assert connector.config == jira_cloud_config
        assert connector._initialized is False
        assert connector.session.auth is not None  # Basic auth should be set

        async with connector:
            assert connector._initialized is True

    @pytest.mark.asyncio
    async def test_datacenter_initialization(self, jira_datacenter_config):
        """Test Data Center connector initialization."""
        connector = JiraConnector(jira_datacenter_config)
        assert connector.config == jira_datacenter_config
        assert connector._initialized is False
        assert (
            "Authorization" in connector.session.headers
        )  # Bearer token should be set

        async with connector:
            assert connector._initialized is True

    def test_missing_cloud_credentials(self):
        """Test initialization with missing Cloud credentials."""
        # Clear environment variables to ensure they don't interfere
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ValueError, match="Email is required for Jira Cloud deployment"
            ):
                JiraProjectConfig(
                    base_url=HttpUrl("https://test.atlassian.net"),
                    deployment_type=JiraDeploymentType.CLOUD,
                    project_key="TEST",
                    source="test-jira",
                    source_type=SourceType.JIRA,
                    token="test-token",
                    email=None,  # Missing email for Cloud
                )

    def test_missing_datacenter_credentials(self):
        """Test initialization with missing Data Center credentials."""
        # Clear environment variables to ensure they don't interfere
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ValueError,
                match="Personal Access Token is required for Jira Data Center/Server deployment",
            ):
                JiraProjectConfig(
                    base_url=HttpUrl("https://jira.company.com"),
                    deployment_type=JiraDeploymentType.DATACENTER,
                    project_key="TEST",
                    source="test-jira",
                    source_type=SourceType.JIRA,
                    token=None,  # Missing token for Data Center
                )

    @pytest.mark.asyncio
    async def test_get_issues(self, jira_cloud_config, mock_issue_data):
        """Test issue retrieval."""
        connector = JiraConnector(jira_cloud_config)

        # Mock the _make_request method
        with patch.object(
            connector,
            "_make_request",
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
                assert isinstance(issues[0], JiraIssue)
                assert issues[0].key == "TEST-1"
                assert issues[0].summary == "Test Issue"

    @pytest.mark.asyncio
    async def test_rate_limiting(self, jira_cloud_config):
        """Test rate limiting functionality."""
        connector = JiraConnector(jira_cloud_config)

        # Mock the actual HTTP request to avoid network calls but keep rate limiting logic
        call_times = []

        def mock_session_request(*args, **kwargs):
            import time

            call_times.append(time.time())
            # Create a mock response
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"issues": [], "total": 0}
            return mock_response

        with patch.object(
            connector.session, "request", side_effect=mock_session_request
        ):
            async with connector:
                # Make multiple requests quickly
                for _ in range(3):
                    await connector._make_request(
                        "GET", "search", params={"jql": 'project = "TEST"'}
                    )

                # Check that rate limiting was applied
                if len(call_times) >= 2:
                    time_diff = call_times[1] - call_times[0]
                    min_interval = 60.0 / connector.config.requests_per_minute
                    assert time_diff >= min_interval * 0.9  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_get_documents(self, jira_cloud_config, mock_issue_data):
        """Test document conversion."""
        connector = JiraConnector(jira_cloud_config)

        # Mock the _make_request method
        with patch.object(
            connector,
            "_make_request",
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
                # The Document class generates its own UUID based on source info
                assert document.title == "Test Issue"
                assert document.source_type == SourceType.JIRA
                assert document.source == "test-jira"
                assert "Test Issue" in document.content
                assert "Test Description" in document.content
                assert "Test comment" in document.content
                # Check metadata
                assert document.metadata["key"] == "TEST-1"
                assert document.metadata["project"] == "TEST"
                assert document.metadata["issue_type"] == "Bug"
                assert document.metadata["status"] == "Open"

    @pytest.mark.asyncio
    async def test_pagination(self, jira_cloud_config, mock_issue_data):
        """Test pagination handling."""
        connector = JiraConnector(jira_cloud_config)

        # Mock multiple pages
        call_count = 0

        async def mock_make_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First page
                return {"issues": [mock_issue_data], "total": 2}
            else:
                # Second page (empty)
                return {"issues": [], "total": 2}

        with patch.object(connector, "_make_request", side_effect=mock_make_request):
            async with connector:
                # Collect all issues
                issues = [issue async for issue in connector.get_issues()]

                assert len(issues) == 1
                assert call_count == 2  # Should have made 2 API calls

    @pytest.mark.asyncio
    async def test_error_handling(self, jira_cloud_config):
        """Test error handling."""
        connector = JiraConnector(jira_cloud_config)

        # Mock an HTTP error
        async def mock_make_request(*args, **kwargs):
            import requests
            from requests.exceptions import HTTPError

            response = requests.Response()
            response.status_code = 400
            response._content = b'{"errorMessages": ["Bad request"]}'
            raise HTTPError("400 Client Error", response=response)

        with patch.object(connector, "_make_request", side_effect=mock_make_request):
            async with connector:
                with pytest.raises(HTTPError, match="400 Client Error"):
                    async for _ in connector.get_issues():
                        pass

    @pytest.mark.asyncio
    async def test_deployment_type_auto_detection(self):
        """Test automatic deployment type detection."""
        # Test Cloud detection
        cloud_config = JiraProjectConfig(
            base_url=HttpUrl("https://test.atlassian.net"),
            project_key="TEST",
            source="test-jira",
            source_type=SourceType.JIRA,
            token="test-token",
            email="test@example.com",
        )
        connector = JiraConnector(cloud_config)
        assert connector._auto_detect_deployment_type() == JiraDeploymentType.CLOUD

        # Test Data Center detection
        datacenter_config = JiraProjectConfig(
            base_url=HttpUrl("https://jira.company.com"),
            deployment_type=JiraDeploymentType.DATACENTER,
            project_key="TEST",
            source="test-jira",
            source_type=SourceType.JIRA,
            token="test-pat-token",
        )
        connector = JiraConnector(datacenter_config)
        assert connector._auto_detect_deployment_type() == JiraDeploymentType.DATACENTER
