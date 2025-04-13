"""Tests for Jira models."""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from qdrant_loader.connectors.jira.models import JiraUser, JiraAttachment, JiraIssue


def test_jira_user():
    """Test JiraUser model."""
    user = JiraUser(
        account_id="123",
        display_name="Test User",
        email_address="test@example.com",
    )

    assert user.account_id == "123"
    assert user.display_name == "Test User"
    assert user.email_address == "test@example.com"


def test_jira_user_optional_email():
    """Test JiraUser model with optional email."""
    user = JiraUser(
        account_id="123",
        display_name="Test User",
    )

    assert user.account_id == "123"
    assert user.display_name == "Test User"
    assert user.email_address is None


def test_jira_attachment():
    """Test JiraAttachment model."""
    attachment = JiraAttachment(
        id="123",
        filename="test.txt",
        size=1024,
        mime_type="text/plain",
        content_url="https://test.atlassian.net/rest/api/2/attachment/123",
        created=datetime(2024, 1, 1, tzinfo=timezone.utc),
        author=JiraUser(
            account_id="456",
            display_name="Author",
            email_address="author@example.com",
        ),
    )

    assert attachment.id == "123"
    assert attachment.filename == "test.txt"
    assert attachment.size == 1024
    assert attachment.mime_type == "text/plain"
    assert str(attachment.content_url) == "https://test.atlassian.net/rest/api/2/attachment/123"
    assert attachment.created == datetime(2024, 1, 1, tzinfo=timezone.utc)
    assert attachment.author.account_id == "456"
    assert attachment.author.display_name == "Author"
    assert attachment.author.email_address == "author@example.com"


def test_jira_issue():
    """Test JiraIssue model."""
    issue = JiraIssue(
        id="123",
        key="TEST-1",
        summary="Test Issue",
        description="Test Description",
        issue_type="Task",
        status="To Do",
        priority="High",
        project_key="TEST",
        created=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated=datetime(2024, 1, 2, tzinfo=timezone.utc),
        reporter=JiraUser(
            account_id="456",
            display_name="Reporter",
            email_address="reporter@example.com",
        ),
        assignee=None,
        labels=["test", "bug"],
        attachments=[],
        parent_key=None,
        subtasks=[],
        linked_issues=[],
    )

    assert issue.id == "123"
    assert issue.key == "TEST-1"
    assert issue.summary == "Test Issue"
    assert issue.description == "Test Description"
    assert issue.issue_type == "Task"
    assert issue.status == "To Do"
    assert issue.priority == "High"
    assert issue.project_key == "TEST"
    assert issue.created == datetime(2024, 1, 1, tzinfo=timezone.utc)
    assert issue.updated == datetime(2024, 1, 2, tzinfo=timezone.utc)
    assert issue.reporter.account_id == "456"
    assert issue.reporter.display_name == "Reporter"
    assert issue.reporter.email_address == "reporter@example.com"
    assert issue.assignee is None
    assert issue.labels == ["test", "bug"]
    assert issue.attachments == []
    assert issue.parent_key is None
    assert issue.subtasks == []
    assert issue.linked_issues == []


def test_jira_issue_optional_fields():
    """Test JiraIssue model with optional fields."""
    issue = JiraIssue(
        id="123",
        key="TEST-1",
        summary="Test Issue",
        issue_type="Task",
        status="To Do",
        project_key="TEST",
        created=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated=datetime(2024, 1, 2, tzinfo=timezone.utc),
        reporter=JiraUser(
            account_id="456",
            display_name="Reporter",
        ),
    )

    assert issue.description is None
    assert issue.priority is None
    assert issue.assignee is None
    assert issue.labels == []
    assert issue.attachments == []
    assert issue.parent_key is None
    assert issue.subtasks == []
    assert issue.linked_issues == [] 