from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import JiraAttachment, JiraComment, JiraIssue, JiraUser


def parse_user(
    raw_user: dict[str, Any] | None, required: bool = False
) -> JiraUser | None:
    if not raw_user:
        if required:
            raise ValueError("User data is required but not provided")
        return None
    account_id = (
        raw_user.get("accountId") or raw_user.get("name") or raw_user.get("key")
    )
    if not account_id:
        if required:
            raise ValueError(
                "User data missing required identifier (accountId, name, or key)"
            )
        return None
    return JiraUser(
        account_id=account_id,
        display_name=(
            raw_user.get("displayName") or raw_user.get("name") or account_id
        ),
        email_address=raw_user.get("emailAddress"),
    )


def parse_attachment(raw_attachment: dict[str, Any]) -> JiraAttachment:
    required_keys = [
        "id",
        "filename",
        "size",
        "mimeType",
        "content",
        "created",
        "author",
    ]

    missing_keys = [key for key in required_keys if key not in raw_attachment]
    if missing_keys:
        raise ValueError(
            f"Attachment missing required keys: {', '.join(missing_keys)}. Received: {list(raw_attachment.keys())}"
        )

    author = parse_user(raw_attachment.get("author"), required=True)
    if author is None:
        raise ValueError("Missing author in Jira attachment")

    created_raw = raw_attachment.get("created")
    try:
        created_dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
    except Exception as e:
        raise ValueError(
            f"Invalid created timestamp in attachment: {created_raw!r}"
        ) from e

    return JiraAttachment(
        id=raw_attachment.get("id"),
        filename=raw_attachment.get("filename"),
        size=raw_attachment.get("size"),
        mime_type=raw_attachment.get("mimeType"),
        content_url=raw_attachment.get("content"),
        created=created_dt,
        author=author,
    )


def parse_comment(raw_comment: dict[str, Any]) -> JiraComment:
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


def parse_issue(raw_issue: dict[str, Any]) -> JiraIssue:
    # Gather identifiers early for clearer error messages
    issue_id = raw_issue.get("id")
    issue_key = raw_issue.get("key")
    issue_identifier = issue_key or issue_id or "<unknown>"

    # Validate presence of fields
    fields = raw_issue.get("fields")
    if not isinstance(fields, dict):
        raise ValueError(
            f"Jira issue {issue_identifier} missing required 'fields' object"
        )

    # Validate required top-level keys within fields
    required_field_keys = ["summary", "created", "updated", "reporter"]
    missing_simple = [
        k for k in required_field_keys if k not in fields or fields.get(k) is None
    ]
    if missing_simple:
        raise ValueError(
            f"Jira issue {issue_identifier} missing required field(s): {', '.join(missing_simple)}"
        )

    # Validate nested required keys
    def _require_dict_with_key(
        container: dict[str, Any], outer_key: str, inner_key: str
    ) -> None:
        value = container.get(outer_key)
        if (
            not isinstance(value, dict)
            or inner_key not in value
            or value.get(inner_key) is None
        ):
            raise ValueError(
                f"Jira issue {issue_identifier} missing required '{outer_key}.{inner_key}'"
            )

    _require_dict_with_key(fields, "issuetype", "name")
    _require_dict_with_key(fields, "status", "name")
    _require_dict_with_key(fields, "project", "key")

    # Parse reporter (required)
    reporter = parse_user(fields.get("reporter"), required=True)
    if reporter is None:
        raise ValueError(
            f"Missing reporter for Jira issue {issue_identifier}: {fields.get('reporter')!r}"
        )

    # Parent key (optional)
    parent = fields.get("parent")
    parent_key = parent.get("key") if isinstance(parent, dict) else None

    # Timestamps with clear error messages
    created_raw = fields.get("created")
    updated_raw = fields.get("updated")
    try:
        created_dt = (
            datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            if isinstance(created_raw, str)
            else None
        )
    except Exception as e:
        raise ValueError(
            f"Invalid 'created' timestamp for Jira issue {issue_identifier}: {created_raw!r}"
        ) from e
    if created_dt is None:
        raise ValueError(
            f"Jira issue {issue_identifier} missing valid 'created' timestamp"
        )

    try:
        updated_dt = (
            datetime.fromisoformat(updated_raw.replace("Z", "+00:00"))
            if isinstance(updated_raw, str)
            else None
        )
    except Exception as e:
        raise ValueError(
            f"Invalid 'updated' timestamp for Jira issue {issue_identifier}: {updated_raw!r}"
        ) from e
    if updated_dt is None:
        raise ValueError(
            f"Jira issue {issue_identifier} missing valid 'updated' timestamp"
        )

    # Safely extract attachments: support both 'attachment' and 'attachments'
    raw_attachments = fields.get("attachment")
    if raw_attachments is None:
        raw_attachments = fields.get("attachments")
    attachments_list = raw_attachments if isinstance(raw_attachments, list) else []

    # Safely extract comments from fields.comment.comments
    comment_field = fields.get("comment")
    if isinstance(comment_field, dict):
        raw_comments = comment_field.get("comments", [])
    else:
        raw_comments = []
    comments_list = raw_comments if isinstance(raw_comments, list) else []

    # Safely extract subtasks keys
    raw_subtasks = fields.get("subtasks", [])
    subtasks_keys = [
        st.get("key") for st in raw_subtasks if isinstance(st, dict) and st.get("key")
    ]

    # Safely extract linked issues (outward only as before)
    raw_links = fields.get("issuelinks", [])
    linked_outward = [
        link.get("outwardIssue", {}).get("key")
        for link in raw_links
        if isinstance(link, dict)
        and isinstance(link.get("outwardIssue"), dict)
        and link.get("outwardIssue", {}).get("key")
    ]

    # Optional fields
    priority_name = None
    priority = fields.get("priority")
    if isinstance(priority, dict):
        priority_name = priority.get("name")

    # Validate id/key presence for the model
    if not issue_id or not issue_key:
        raise ValueError(
            f"Jira issue missing required top-level identifier(s): id={issue_id!r}, key={issue_key!r}"
        )

    return JiraIssue(
        id=issue_id,
        key=issue_key,
        summary=str(fields.get("summary")),
        description=fields.get("description"),
        issue_type=fields.get("issuetype", {}).get("name"),
        status=fields.get("status", {}).get("name"),
        priority=priority_name,
        project_key=fields.get("project", {}).get("key"),
        created=created_dt,
        updated=updated_dt,
        reporter=reporter,
        assignee=parse_user(fields.get("assignee")),
        labels=(
            fields.get("labels", []) if isinstance(fields.get("labels"), list) else []
        ),
        attachments=[
            parse_attachment(att) for att in attachments_list if isinstance(att, dict)
        ],
        comments=[
            parse_comment(comment)
            for comment in comments_list
            if isinstance(comment, dict)
        ],
        parent_key=parent_key,
        subtasks=subtasks_keys,
        linked_issues=[key for key in linked_outward if key],
    )
