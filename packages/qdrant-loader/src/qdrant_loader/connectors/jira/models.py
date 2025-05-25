"""Data models for Jira connector."""

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class JiraUser(BaseModel):
    """Jira user model."""

    account_id: str = Field(..., description="User's account ID")
    display_name: str = Field(..., description="User's display name")
    email_address: str | None = Field(None, description="User's email address")


class JiraComment(BaseModel):
    """Jira comment model."""

    id: str = Field(..., description="Comment ID")
    body: str = Field(..., description="Comment content")
    created: datetime = Field(..., description="Comment creation timestamp")
    updated: datetime | None = Field(None, description="Comment last update timestamp")
    author: JiraUser = Field(..., description="User who created the comment")


class JiraAttachment(BaseModel):
    """Jira attachment model."""

    id: str = Field(..., description="Attachment ID")
    filename: str = Field(..., description="Attachment filename")
    size: int = Field(..., description="Attachment size in bytes")
    mime_type: str = Field(..., description="Attachment MIME type")
    content_url: HttpUrl = Field(..., description="URL to download attachment content")
    created: datetime = Field(..., description="Attachment creation timestamp")
    author: JiraUser = Field(..., description="User who attached the file")


class JiraIssue(BaseModel):
    """Jira issue model."""

    id: str = Field(..., description="Issue ID")
    key: str = Field(..., description="Issue key")
    summary: str = Field(..., description="Issue summary")
    description: str | None = Field(None, description="Issue description")
    issue_type: str = Field(..., description="Issue type")
    status: str = Field(..., description="Issue status")
    priority: str | None = Field(None, description="Issue priority")
    project_key: str = Field(..., description="Project key")
    created: datetime = Field(..., description="Issue creation timestamp")
    updated: datetime = Field(..., description="Last update timestamp")
    reporter: JiraUser = Field(..., description="Issue reporter")
    assignee: JiraUser | None = Field(None, description="Issue assignee")
    labels: list[str] = Field(default_factory=list, description="Issue labels")
    attachments: list[JiraAttachment] = Field(
        default_factory=list, description="Issue attachments"
    )
    comments: list[JiraComment] = Field(
        default_factory=list, description="Issue comments"
    )
    parent_key: str | None = Field(None, description="Parent issue key for subtasks")
    subtasks: list[str] = Field(
        default_factory=list, description="List of subtask keys"
    )
    linked_issues: list[str] = Field(
        default_factory=list, description="List of linked issue keys"
    )
