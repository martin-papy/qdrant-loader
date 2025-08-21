from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from .models import JiraAttachment, JiraComment, JiraIssue, JiraUser


def parse_user(raw_user: Dict[str, Any] | None, required: bool = False) -> Optional[JiraUser]:
    if not raw_user:
        if required:
            raise ValueError("User data is required but not provided")
        return None
    account_id = raw_user.get("accountId") or raw_user.get("name") or raw_user.get("key")
    if not account_id:
        if required:
            raise ValueError("User data missing required identifier (accountId, name, or key)")
        return None
    return JiraUser(
        account_id=account_id,
        display_name=(raw_user.get("displayName") or raw_user.get("name") or account_id),
        email_address=raw_user.get("emailAddress"),
    )


def parse_attachment(raw_attachment: Dict[str, Any]) -> JiraAttachment:
    author = parse_user(raw_attachment["author"], required=True)
    if author is None:
        raise ValueError("Missing author in Jira attachment")
    return JiraAttachment(
        id=raw_attachment["id"],
        filename=raw_attachment["filename"],
        size=raw_attachment["size"],
        mime_type=raw_attachment["mimeType"],
        content_url=raw_attachment["content"],
        created=datetime.fromisoformat(raw_attachment["created"].replace("Z", "+00:00")),
        author=author,
    )


def parse_comment(raw_comment: Dict[str, Any]) -> JiraComment:
    author = parse_user(raw_comment["author"], required=True)
    if author is None:
        raise ValueError("Missing author in Jira comment")
    return JiraComment(
        id=raw_comment["id"],
        body=raw_comment["body"],
        created=datetime.fromisoformat(raw_comment["created"].replace("Z", "+00:00")),
        updated=(
            datetime.fromisoformat(raw_comment["updated"].replace("Z", "+00:00"))
            if "updated" in raw_comment
            else None
        ),
        author=author,
    )


def parse_issue(raw_issue: Dict[str, Any]) -> JiraIssue:
    fields = raw_issue["fields"]
    parent = fields.get("parent")
    parent_key = parent.get("key") if parent else None
    reporter = parse_user(fields["reporter"], required=True)
    assert reporter is not None
    return JiraIssue(
        id=raw_issue["id"],
        key=raw_issue["key"],
        summary=fields["summary"],
        description=fields.get("description"),
        issue_type=fields["issuetype"]["name"],
        status=fields["status"]["name"],
        priority=(fields.get("priority", {}).get("name") if fields.get("priority") else None),
        project_key=fields["project"]["key"],
        created=datetime.fromisoformat(fields["created"].replace("Z", "+00:00")),
        updated=datetime.fromisoformat(fields["updated"].replace("Z", "+00:00")),
        reporter=reporter,
        assignee=parse_user(fields.get("assignee")),
        labels=fields.get("labels", []),
        attachments=[parse_attachment(att) for att in fields.get("attachment", [])],
        comments=[parse_comment(comment) for comment in fields.get("comment", {}).get("comments", [])],
        parent_key=parent_key,
        subtasks=[st["key"] for st in fields.get("subtasks", [])],
        linked_issues=[
            link["outwardIssue"]["key"]
            for link in fields.get("issuelinks", [])
            if "outwardIssue" in link
        ],
    )


