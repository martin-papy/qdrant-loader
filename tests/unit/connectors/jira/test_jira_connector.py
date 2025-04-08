"""Tests for the Jira connector."""

import os
import pytest
from unittest.mock import patch, MagicMock, Mock, AsyncMock
from datetime import datetime
from qdrant_loader.connectors.jira import JiraConnector, JiraConfig
from qdrant_loader.connectors.jira.models import JiraIssue, JiraUser, JiraAttachment
from qdrant_loader.core.document import Document

@pytest.fixture
def mock_env_vars():
    """Set up mock environment variables."""
    with patch.dict(os.environ, {
        "JIRA_TOKEN": "test_token",
        "JIRA_EMAIL": "test@example.com"
    }):
        yield

@pytest.fixture
def config(mock_env_vars):
    """Create a JiraConfig instance."""
    return JiraConfig(
        base_url="https://test.atlassian.net",
        project_key="TEST",
        requests_per_minute=60,
        page_size=50,
        process_attachments=True,
        track_last_sync=True
    )

@pytest.fixture
def connector(config):
    """Create a Jira connector."""
    return JiraConnector(config)

@pytest.fixture
def mock_jira_issue():
    """Create a mock Jira issue."""
    return {
        "id": "12345",
        "key": "TEST-123",
        "fields": {
            "summary": "Test Issue",
            "description": "Test Description",
            "issuetype": {"name": "Story"},
            "status": {"name": "In Progress"},
            "priority": {"name": "High"},
            "project": {"key": "TEST"},
            "created": "2024-03-20T10:00:00.000Z",
            "updated": "2024-03-21T15:30:00.000Z",
            "reporter": {
                "accountId": "user123",
                "displayName": "John Doe",
                "emailAddress": "john@example.com"
            },
            "assignee": {
                "accountId": "user456",
                "displayName": "Jane Smith",
                "emailAddress": "jane@example.com"
            },
            "labels": ["bug", "urgent"],
            "attachment": [{
                "id": "att123",
                "filename": "test.txt",
                "size": 1024,
                "mimeType": "text/plain",
                "content": "http://example.com/test.txt",
                "created": "2024-03-20T11:00:00.000Z",
                "author": {
                    "accountId": "user123",
                    "displayName": "John Doe",
                    "emailAddress": "john@example.com"
                }
            }],
            "parent": {"key": "TEST-100"},
            "subtasks": [{"key": "TEST-124"}, {"key": "TEST-125"}],
            "issuelinks": [{"outwardIssue": {"key": "TEST-126"}}]
        }
    }

def test_parse_issue(connector):
    """Test parsing a basic issue."""
    raw_issue = {
        "id": "12345",
        "key": "TEST-1",
        "fields": {
            "summary": "Test Issue",
            "description": "Test Description",
            "issuetype": {"name": "Task"},
            "status": {"name": "To Do"},
            "project": {"key": "TEST"},
            "created": "2024-01-01T00:00:00.000+0000",
            "updated": "2024-01-01T00:00:00.000+0000",
            "reporter": {
                "accountId": "123",
                "displayName": "Test User",
                "emailAddress": "test@example.com"
            }
        }
    }
    
    issue = connector._parse_issue(raw_issue)
    assert isinstance(issue, JiraIssue)
    assert issue.id == "12345"
    assert issue.key == "TEST-1"
    assert issue.summary == "Test Issue"
    assert issue.description == "Test Description"
    assert issue.issue_type == "Task"
    assert issue.status == "To Do"
    assert isinstance(issue.reporter, JiraUser)
    assert issue.reporter.display_name == "Test User"

def test_parse_issue_with_parent(connector):
    """Test parsing an issue with a parent."""
    raw_issue = {
        "id": "12345",
        "key": "TEST-1",
        "fields": {
            "summary": "Test Issue",
            "description": "Test Description",
            "issuetype": {"name": "Sub-task"},
            "status": {"name": "To Do"},
            "project": {"key": "TEST"},
            "created": "2024-01-01T00:00:00.000+0000",
            "updated": "2024-01-01T00:00:00.000+0000",
            "parent": {
                "key": "TEST-0"
            },
            "reporter": {
                "accountId": "123",
                "displayName": "Test User"
            }
        }
    }
    
    issue = connector._parse_issue(raw_issue)
    assert issue.parent_key == "TEST-0"
    assert issue.issue_type == "Sub-task"

def test_parse_issue_with_subtasks(connector):
    """Test parsing an issue with subtasks."""
    raw_issue = {
        "id": "12345",
        "key": "TEST-1",
        "fields": {
            "summary": "Test Issue",
            "description": "Test Description",
            "issuetype": {"name": "Task"},
            "status": {"name": "To Do"},
            "project": {"key": "TEST"},
            "created": "2024-01-01T00:00:00.000+0000",
            "updated": "2024-01-01T00:00:00.000+0000",
            "subtasks": [
                {
                    "key": "TEST-2"
                }
            ],
            "reporter": {
                "accountId": "123",
                "displayName": "Test User"
            }
        }
    }
    
    issue = connector._parse_issue(raw_issue)
    assert len(issue.subtasks) == 1
    assert issue.subtasks[0] == "TEST-2"

def test_parse_issue_with_linked_issues(connector):
    """Test parsing an issue with linked issues."""
    raw_issue = {
        "id": "12345",
        "key": "TEST-1",
        "fields": {
            "summary": "Test Issue",
            "description": "Test Description",
            "issuetype": {"name": "Task"},
            "status": {"name": "To Do"},
            "project": {"key": "TEST"},
            "created": "2024-01-01T00:00:00.000+0000",
            "updated": "2024-01-01T00:00:00.000+0000",
            "issuelinks": [
                {
                    "type": {"name": "Blocks"},
                    "outwardIssue": {
                        "key": "TEST-2"
                    }
                }
            ],
            "reporter": {
                "accountId": "123",
                "displayName": "Test User"
            }
        }
    }
    
    issue = connector._parse_issue(raw_issue)
    assert len(issue.linked_issues) == 1
    assert issue.linked_issues[0] == "TEST-2"

def test_parse_issue_with_attachments(connector):
    """Test parsing an issue with attachments."""
    raw_issue = {
        "id": "12345",
        "key": "TEST-1",
        "fields": {
            "summary": "Test Issue",
            "description": "Test Description",
            "issuetype": {"name": "Task"},
            "status": {"name": "To Do"},
            "project": {"key": "TEST"},
            "created": "2024-01-01T00:00:00.000+0000",
            "updated": "2024-01-01T00:00:00.000+0000",
            "attachment": [
                {
                    "id": "10000",
                    "filename": "test.txt",
                    "size": 1024,
                    "mimeType": "text/plain",
                    "content": "https://test.atlassian.net/secure/attachment/10000/test.txt",
                    "created": "2024-01-01T00:00:00.000+0000",
                    "author": {
                        "accountId": "123",
                        "displayName": "Test User"
                    }
                }
            ],
            "reporter": {
                "accountId": "123",
                "displayName": "Test User"
            }
        }
    }
    
    issue = connector._parse_issue(raw_issue)
    assert len(issue.attachments) == 1
    attachment = issue.attachments[0]
    assert isinstance(attachment, JiraAttachment)
    assert attachment.id == "10000"
    assert attachment.filename == "test.txt"
    assert attachment.size == 1024
    assert attachment.mime_type == "text/plain"

@pytest.mark.asyncio
async def test_get_documents(config, mock_jira_issue):
    """Test get_documents method."""
    # Mock environment variables
    with patch.dict(os.environ, {
        "JIRA_TOKEN": "test-token",
        "JIRA_EMAIL": "test@example.com"
    }):
        connector = JiraConnector(config)
        
        # Mock the Jira client response
        mock_response = {"issues": [mock_jira_issue]}
        connector.client.jql = Mock(return_value=mock_response)
        
        # Get documents
        documents = await connector.get_documents()
        
        # Verify the results
        assert len(documents) == 1
        doc = documents[0]
        
        # Verify document properties
        assert isinstance(doc, Document)
        assert doc.id == "12345"
        assert doc.content == "Test Issue\n\nTest Description"
        assert doc.source == "TEST"
        assert doc.source_type == "jira"
        assert doc.url == "https://test.atlassian.net/browse/TEST-123"
        
        # Verify metadata
        assert doc.metadata["project"] == "TEST"
        assert doc.metadata["issue_type"] == "Story"
        assert doc.metadata["status"] == "In Progress"
        assert doc.metadata["key"] == "TEST-123"
        assert doc.metadata["priority"] == "High"
        assert doc.metadata["labels"] == ["bug", "urgent"]
        assert doc.metadata["reporter"] == "John Doe"
        assert doc.metadata["assignee"] == "Jane Smith"
        assert doc.metadata["parent_key"] == "TEST-100"
        assert doc.metadata["subtasks"] == ["TEST-124", "TEST-125"]
        assert doc.metadata["linked_issues"] == ["TEST-126"]
        
        # Verify timestamps
        created = datetime.fromisoformat(doc.metadata["created"])
        updated = datetime.fromisoformat(doc.metadata["updated"])
        assert created.year == 2024 and created.month == 3 and created.day == 20
        assert updated.year == 2024 and updated.month == 3 and updated.day == 21
        
        # Verify the Jira client was called correctly
        connector.client.jql.assert_called_once_with(
            jql='project = "TEST"',
            start=0,
            limit=50  # Default page size
        ) 