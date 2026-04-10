"""Unit tests for Jira connector."""

import os
from unittest.mock import MagicMock, patch

import pytest
from pydantic import HttpUrl
from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.jira.cloud_connector import JiraCloudConnector
from qdrant_loader.connectors.jira.config import JiraDeploymentType, JiraProjectConfig
from qdrant_loader.connectors.jira.data_center_connector import JiraDataCenterConnector
from qdrant_loader.connectors.jira.models import (
    JiraIssue,
)
from qdrant_loader.core.document import Document
from requests.exceptions import HTTPError


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
def jira_data_center_config():
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
def mock_data_center_issue_data():
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


@pytest.fixture
def mock_cloud_issue_data():
    """Create mock issue data."""
    return {
        "id": "12345",
        "key": "TEST-1",
        "fields": {
            "summary": "Test Issue",
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Test Description"}],
                    }
                ],
            },
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
                        "body": {
                            "type": "doc",
                            "version": 1,
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {"type": "text", "text": "Test comment"}
                                    ],
                                }
                            ],
                        },
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
    """Test suite for BaseJiraConnector."""

    @pytest.fixture(autouse=True)
    def skip_validate_connection(self):
        """Patch _validate_connection to a no-op for all tests in this class.

        Tests here focus on other connector behaviour; connection validation
        is covered separately in TestJiraValidateConnection.
        """
        from unittest.mock import AsyncMock

        with patch(
            "qdrant_loader.connectors.jira.connector.BaseJiraConnector._validate_connection",
            new_callable=AsyncMock,
        ):
            yield

    @pytest.mark.asyncio
    async def test_cloud_initialization(self, jira_cloud_config):
        """Test Cloud connector initialization."""
        connector = JiraCloudConnector(jira_cloud_config)
        assert connector.config == jira_cloud_config
        assert connector._initialized is False
        assert connector.session.auth is not None  # Basic auth should be set

        async with connector:
            assert connector._initialized is True

    @pytest.mark.asyncio
    async def test_datacenter_initialization(self, jira_data_center_config):
        """Test Data Center connector initialization."""
        connector = JiraDataCenterConnector(jira_data_center_config)
        assert connector.config == jira_data_center_config
        assert connector._initialized is False
        assert (
            "Authorization" in connector.session.headers
        )  # Bearer token should be set

        async with connector:
            assert connector._initialized is True

    @pytest.mark.asyncio
    async def test_context_exit_closes_session(self, jira_cloud_config):
        """Connector context exit should close the owned requests session."""
        connector = JiraCloudConnector(jira_cloud_config)

        with patch.object(connector.session, "close") as mock_close:
            async with connector:
                assert connector._initialized is True

            mock_close.assert_called_once()
            assert connector._initialized is False

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
    async def test_get_cloud_issues(self, jira_cloud_config, mock_cloud_issue_data):
        """Test issue retrieval."""
        connector = JiraCloudConnector(jira_cloud_config)

        # Mock the _make_request method
        with patch.object(
            connector,
            "_make_request",
            return_value={
                "issues": [mock_cloud_issue_data],
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
    async def test_get_data_center_issues(
        self, jira_data_center_config, mock_data_center_issue_data
    ):
        """Test issue retrieval."""
        connector = JiraDataCenterConnector(jira_data_center_config)

        # Mock the _make_request method
        with patch.object(
            connector,
            "_make_request",
            return_value={
                "issues": [mock_data_center_issue_data],
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
    async def test_cloud_rate_limiting(self, jira_cloud_config):
        """Test rate limiting functionality."""
        connector = JiraCloudConnector(jira_cloud_config)

        # Mock the actual HTTP request to avoid network calls but keep rate limiting logic
        call_times = []

        def mock_session_request(*args, **kwargs):
            import time

            call_times.append(time.time())
            # Create a mock response
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"issues": []}
            return mock_response

        with patch.object(
            connector.session, "request", side_effect=mock_session_request
        ):
            async with connector:
                # Make multiple requests quickly
                for _ in range(3):
                    await connector._make_request(
                        "GET", "search/jql", params={"jql": 'project = "TEST"'}
                    )

                # Check that rate limiting was applied
                if len(call_times) >= 2:
                    time_diff = call_times[1] - call_times[0]
                    min_interval = 60.0 / connector.config.requests_per_minute
                    assert time_diff >= min_interval * 0.9  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_data_center_rate_limiting(self, jira_data_center_config):
        """Test rate limiting functionality."""
        connector = JiraDataCenterConnector(jira_data_center_config)

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
    async def test_get_cloud_documents(self, jira_cloud_config, mock_cloud_issue_data):
        """Test document conversion."""
        connector = JiraCloudConnector(jira_cloud_config)

        # Mock the _make_request method
        with patch.object(
            connector,
            "_make_request",
            return_value={"issues": [mock_cloud_issue_data]},
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
    async def test_getdata_center_documents(
        self, jira_data_center_config, mock_data_center_issue_data
    ):
        """Test document conversion."""
        connector = JiraDataCenterConnector(jira_data_center_config)

        # Mock the _make_request method
        with patch.object(
            connector,
            "_make_request",
            return_value={
                "issues": [mock_data_center_issue_data],
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
    async def test_cloud_pagination(self, jira_cloud_config, mock_cloud_issue_data):
        """Test pagination handling."""
        connector = JiraCloudConnector(jira_cloud_config)

        # Mock multiple pages
        call_count = 0

        async def mock_make_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First page
                return {
                    "issues": [mock_cloud_issue_data],
                    "nextPageToken": "example token",
                }
            else:
                # Second page (empty)
                return {"issues": []}

        with patch.object(connector, "_make_request", side_effect=mock_make_request):
            async with connector:
                # Collect all issues
                issues = [issue async for issue in connector.get_issues()]

                assert len(issues) == 1
                assert call_count == 2  # Should have made 2 API calls

    @pytest.mark.asyncio
    async def test_pagination(
        self, jira_data_center_config, mock_data_center_issue_data
    ):
        """Test Jira data center pagination handling."""
        connector = JiraDataCenterConnector(jira_data_center_config)

        # Mock multiple pages
        call_count = 0

        async def mock_make_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First page
                return {"issues": [mock_data_center_issue_data], "total": 2}
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
    async def test_cloud_error_handling(self, jira_cloud_config):
        """Test error handling."""
        connector = JiraCloudConnector(jira_cloud_config)

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
    async def test_data_center_error_handling(self, jira_data_center_config):
        """Test error handling."""
        connector = JiraDataCenterConnector(jira_data_center_config)

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
        connector = JiraCloudConnector(cloud_config)
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
        connector = JiraDataCenterConnector(datacenter_config)
        assert connector._auto_detect_deployment_type() == JiraDeploymentType.DATACENTER

    def test_jql_filter_build_with_issue_types(self, jira_cloud_config):
        """Test JQL filter builder with issue_types."""
        config = JiraProjectConfig(
            base_url=HttpUrl("https://test.atlassian.net"),
            project_key="TEST",
            source="test-jira",
            source_type=SourceType.JIRA,
            token="test-token",
            email="test@example.com",
            issue_types=["Bug", "Story"],
        )
        connector = JiraCloudConnector(config)
        jql = connector._build_jql_filter()

        assert 'project = "TEST"' in jql
        assert "type IN " in jql
        assert '"Bug"' in jql
        assert '"Story"' in jql

    def test_jql_filter_build_with_statuses(self, jira_cloud_config):
        """Test JQL filter builder with include_statuses."""
        config = JiraProjectConfig(
            base_url=HttpUrl("https://test.atlassian.net"),
            project_key="TEST",
            source="test-jira",
            source_type=SourceType.JIRA,
            token="test-token",
            email="test@example.com",
            include_statuses=["Open", "In Progress"],
        )
        connector = JiraCloudConnector(config)
        jql = connector._build_jql_filter()

        assert 'project = "TEST"' in jql
        assert "status IN " in jql
        assert '"Open"' in jql
        assert '"In Progress"' in jql

    def test_jql_filter_build_with_all_filters(self, jira_cloud_config):
        """Test JQL filter builder with all filters combined."""
        from datetime import datetime

        config = JiraProjectConfig(
            base_url=HttpUrl("https://test.atlassian.net"),
            project_key="TEST",
            source="test-jira",
            source_type=SourceType.JIRA,
            token="test-token",
            email="test@example.com",
            issue_types=["Bug", "Story"],
            include_statuses=["Open", "In Progress"],
        )
        connector = JiraCloudConnector(config)
        updated_after = datetime(2024, 1, 1, 12, 0)
        jql = connector._build_jql_filter(updated_after=updated_after)

        assert 'project = "TEST"' in jql
        assert "type IN " in jql
        assert '"Bug"' in jql
        assert '"Story"' in jql
        assert "status IN " in jql
        assert '"Open"' in jql
        assert '"In Progress"' in jql
        assert "updated >= " in jql
        assert "2024-01-01" in jql

    def test_jql_filter_build_no_filters(self, jira_cloud_config):
        """Test JQL filter builder without any optional filters."""
        connector = JiraCloudConnector(jira_cloud_config)
        jql = connector._build_jql_filter()

        assert jql == 'project = "TEST"'

    def test_escape_jql_literal_handles_quotes_and_backslashes(self):
        """Test JQL literal escaping for unsafe characters."""
        assert JiraCloudConnector._escape_jql_literal('MY"PROJECT') == 'MY\\"PROJECT'
        assert JiraCloudConnector._escape_jql_literal(r"ABC\DEF") == r"ABC\\DEF"
        assert JiraCloudConnector._escape_jql_literal('A"B\\C') == 'A\\"B\\\\C'

    def test_jql_filter_build_escapes_all_config_literals(self):
        """Test JQL filter builder escapes project, issue type and status values."""
        config = JiraProjectConfig(
            base_url=HttpUrl("https://test.atlassian.net"),
            project_key='MY"PROJECT\\KEY',
            source="test-jira",
            source_type=SourceType.JIRA,
            token="test-token",
            email="test@example.com",
            issue_types=['Bug"Type', r"Feature\Request"],
            include_statuses=['Open"Status', r"In\Progress"],
        )
        connector = JiraCloudConnector(config)
        jql = connector._build_jql_filter()

        assert 'project = "MY\\"PROJECT\\\\KEY"' in jql
        assert '"Bug\\"Type"' in jql
        assert '"Feature\\\\Request"' in jql
        assert '"Open\\"Status"' in jql
        assert '"In\\\\Progress"' in jql

    @pytest.mark.asyncio
    async def test_cloud_issue_filtering(
        self, jira_cloud_config, mock_cloud_issue_data
    ):
        """Test that issue filtering is applied in Cloud connector."""
        config = JiraProjectConfig(
            base_url=HttpUrl("https://test.atlassian.net"),
            project_key="TEST",
            source="test-jira",
            source_type=SourceType.JIRA,
            token="test-token",
            email="test@example.com",
            issue_types=["Bug"],
            include_statuses=["Open"],
        )
        connector = JiraCloudConnector(config)

        # Track the JQL query used
        captured_jql = None

        async def mock_make_request(method, endpoint, **kwargs):
            nonlocal captured_jql
            if "params" in kwargs:
                captured_jql = kwargs["params"].get("jql")
            return {"issues": [mock_cloud_issue_data]}

        with patch.object(connector, "_make_request", side_effect=mock_make_request):
            async with connector:
                issues = []
                async for issue in connector.get_issues():
                    issues.append(issue)
                    break  # Just get the first one

        # Verify filtering was applied in the JQL query
        assert captured_jql is not None
        assert 'project = "TEST"' in captured_jql
        assert "type IN " in captured_jql
        assert '"Bug"' in captured_jql
        assert "status IN " in captured_jql
        assert '"Open"' in captured_jql

    @pytest.mark.asyncio
    async def test_datacenter_issue_filtering(
        self, jira_data_center_config, mock_data_center_issue_data
    ):
        """Test that issue filtering is applied in Data Center connector."""
        config = JiraProjectConfig(
            base_url=HttpUrl("https://jira.company.com"),
            deployment_type=JiraDeploymentType.DATACENTER,
            project_key="TEST",
            source="test-jira",
            source_type=SourceType.JIRA,
            token="test-pat-token",
            issue_types=["Bug", "Task"],
            include_statuses=["Done"],
        )
        connector = JiraDataCenterConnector(config)

        # Track the JQL query used
        captured_jql = None

        async def mock_make_request(method, endpoint, **kwargs):
            nonlocal captured_jql
            if "params" in kwargs:
                captured_jql = kwargs["params"].get("jql")
            return {"issues": [mock_data_center_issue_data], "total": 1}

        with patch.object(connector, "_make_request", side_effect=mock_make_request):
            async with connector:
                issues = []
                async for issue in connector.get_issues():
                    issues.append(issue)
                    break  # Just get the first one

        # Verify filtering was applied in the JQL query
        assert captured_jql is not None
        assert 'project = "TEST"' in captured_jql
        assert "type IN " in captured_jql
        assert '"Bug"' in captured_jql
        assert '"Task"' in captured_jql
        assert "status IN " in captured_jql
        assert '"Done"' in captured_jql


class TestJiraValidateConnection:
    """Tests for _validate_connection() - covers the 4 fatal config failure cases."""

    @pytest.fixture
    def cloud_config(self):
        return JiraProjectConfig(
            base_url=HttpUrl("https://test.atlassian.net"),
            deployment_type=JiraDeploymentType.CLOUD,
            project_key="TEST",
            source="test-jira",
            source_type=SourceType.JIRA,
            token="test-token",
            email="test@example.com",
        )

    def _http_error(self, status_code: int):
        """Build a requests.HTTPError with the given status code."""
        import requests

        resp = requests.Response()
        resp.status_code = status_code
        err = requests.exceptions.HTTPError(response=resp)
        return err

    # ── happy path ────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_validate_connection_success(self, cloud_config):
        """No exception when /myself and /project both succeed."""

        connector = JiraCloudConnector(cloud_config)

        async def ok(*args, **kwargs):
            return {"accountId": "abc", "key": "TEST", "name": "Test Project"}

        with patch.object(connector, "_make_request", side_effect=ok):
            # __aenter__ calls _validate_connection; should not raise
            await connector.__aenter__()
            assert connector._initialized is True

    # ── invalid URL / unreachable host ────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_validate_connection_invalid_url_raises(self, cloud_config):
        """ConnectionError on /myself → ConnectorConfigurationError."""
        import requests
        from qdrant_loader.connectors.base import ConnectorConfigurationError

        connector = JiraCloudConnector(cloud_config)

        with patch.object(
            connector,
            "_make_request",
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            with pytest.raises(ConnectorConfigurationError, match="Cannot connect"):
                await connector.__aenter__()

    # ── invalid token (401) ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_validate_connection_invalid_token_raises(self, cloud_config):
        """HTTP 401 on /myself → ConnectorConfigurationError with auth message."""
        from qdrant_loader.connectors.base import ConnectorConfigurationError

        connector = JiraCloudConnector(cloud_config)

        with patch.object(
            connector,
            "_make_request",
            side_effect=self._http_error(401),
        ):
            with pytest.raises(ConnectorConfigurationError, match="401"):
                await connector.__aenter__()

    # ── no permission (403 on /myself) ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_validate_connection_no_permission_raises(self, cloud_config):
        """HTTP 403 on /myself → ConnectorConfigurationError with permission message."""
        from qdrant_loader.connectors.base import ConnectorConfigurationError

        connector = JiraCloudConnector(cloud_config)

        with patch.object(
            connector,
            "_make_request",
            side_effect=self._http_error(403),
        ):
            with pytest.raises(ConnectorConfigurationError, match="403"):
                await connector.__aenter__()

    # ── wrong project key (404 on /project/{key}) ─────────────────────────────

    @pytest.mark.asyncio
    async def test_validate_connection_wrong_project_key_raises(self, cloud_config):
        """HTTP 404 on /project/{key} → ConnectorConfigurationError with project message."""
        from qdrant_loader.connectors.base import ConnectorConfigurationError

        connector = JiraCloudConnector(cloud_config)

        call_count = 0

        async def side_effect(method, endpoint, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # /myself succeeds
                return {"accountId": "abc"}
            raise self._http_error(404)  # /project/{key} fails

        with patch.object(connector, "_make_request", side_effect=side_effect):
            with pytest.raises(ConnectorConfigurationError, match="not found"):
                await connector.__aenter__()

    # ── no permission on project (403 on /project/{key}) ──────────────────────

    @pytest.mark.asyncio
    async def test_validate_connection_project_no_permission_raises(self, cloud_config):
        """HTTP 403 on /project/{key} → ConnectorConfigurationError."""
        from qdrant_loader.connectors.base import ConnectorConfigurationError

        connector = JiraCloudConnector(cloud_config)

        call_count = 0

        async def side_effect(method, endpoint, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # /myself succeeds
                return {"accountId": "abc"}
            raise self._http_error(403)  # /project/{key} → forbidden

        with patch.object(connector, "_make_request", side_effect=side_effect):
            with pytest.raises(ConnectorConfigurationError, match="403"):
                await connector.__aenter__()
