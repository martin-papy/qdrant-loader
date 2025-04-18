"""Jira connector implementation."""

import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import structlog
from atlassian import Jira
from pydantic import HttpUrl

from qdrant_loader.connectors.jira.config import JiraConfig
from qdrant_loader.connectors.jira.models import JiraAttachment, JiraIssue, JiraUser
from qdrant_loader.core.document import Document

logger = structlog.get_logger(__name__)


class JiraConnector:
    """Jira connector for fetching and processing issues."""

    def __init__(self, config: JiraConfig):
        """Initialize the Jira connector.

        Args:
            config: The Jira configuration.

        Raises:
            ValueError: If required environment variables are not set.
        """
        self.config = config

        # Validate required environment variables
        token = os.getenv("JIRA_TOKEN")
        if token is None:
            raise ValueError("JIRA_TOKEN environment variable is required")

        email = os.getenv("JIRA_EMAIL")
        if email is None:
            raise ValueError("JIRA_EMAIL environment variable is required")

        self.client = Jira(
            url=str(config.base_url),
            username=email,
            password=token,
        )
        self._last_sync: Optional[datetime] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time = 0.0

    def _make_sync_request(self, jql: str, **kwargs):
        """
        Make a synchronous request to the Jira API, converting parameters as needed:
        - maxResults -> limit
        - startAt -> start
        - Format datetime values in JQL to 'yyyy-MM-dd HH:mm' format
        """
        # Convert pagination parameters
        if "maxResults" in kwargs:
            kwargs["limit"] = int(kwargs.pop("maxResults"))
        if "startAt" in kwargs:
            kwargs["start"] = int(kwargs.pop("startAt"))

        # Format datetime values in JQL query
        for key, value in kwargs.items():
            if isinstance(value, datetime):
                formatted_date = value.strftime("%Y-%m-%d %H:%M")
                jql = jql.replace(f"{{{key}}}", f"'{formatted_date}'")

        return self.client.jql(jql, **kwargs)

    async def _make_request(self, *args, **kwargs):
        """
        Make an asynchronous request to the Jira API by running the synchronous request in a thread.
        Applies rate limiting using asyncio.Lock.
        """
        async with self._rate_limit_lock:
            # Calculate time to wait based on rate limit
            min_interval = 60.0 / self.config.requests_per_minute
            now = time.time()
            time_since_last_request = now - self._last_request_time

            if time_since_last_request < min_interval:
                await asyncio.sleep(min_interval - time_since_last_request)

            self._last_request_time = time.time()
            return await asyncio.to_thread(self._make_sync_request, *args, **kwargs)

    async def get_issues(
        self, updated_after: Optional[datetime] = None
    ) -> AsyncGenerator[JiraIssue, None]:
        """
        Get all issues from Jira.

        Args:
            updated_after: Optional datetime to filter issues updated after this time

        Yields:
            JiraIssue objects
        """
        start_at = 0

        while True:
            jql = f'project = "{self.config.project_key}"'
            if updated_after:
                jql += f" AND updated >= '{updated_after.strftime('%Y-%m-%d %H:%M')}'"

            response = await self._make_request(
                jql=jql, startAt=start_at, maxResults=self.config.page_size
            )

            if not response or not response.get("issues"):
                break

            issues = response["issues"]
            for issue in issues:
                yield self._parse_issue(issue)

            start_at += len(issues)

            if len(issues) < self.config.page_size:
                break

    def _parse_issue(self, raw_issue: dict) -> JiraIssue:
        """Parse raw Jira issue data into JiraIssue model.

        Args:
            raw_issue: Raw issue data from Jira API

        Returns:
            Parsed JiraIssue
        """
        fields = raw_issue["fields"]
        parent = fields.get("parent")
        parent_key = parent.get("key") if parent else None

        # Parse reporter with type assertion since it's required
        reporter = self._parse_user(fields["reporter"], required=True)
        assert reporter is not None  # For type checker

        return JiraIssue(
            id=raw_issue["id"],
            key=raw_issue["key"],
            summary=fields["summary"],
            description=fields.get("description"),
            issue_type=fields["issuetype"]["name"],
            status=fields["status"]["name"],
            priority=fields.get("priority", {}).get("name"),
            project_key=fields["project"]["key"],
            created=datetime.fromisoformat(fields["created"].replace("Z", "+00:00")),
            updated=datetime.fromisoformat(fields["updated"].replace("Z", "+00:00")),
            reporter=reporter,
            assignee=self._parse_user(fields.get("assignee")),
            labels=fields.get("labels", []),
            attachments=[self._parse_attachment(att) for att in fields.get("attachment", [])],
            parent_key=parent_key,
            subtasks=[st["key"] for st in fields.get("subtasks", [])],
            linked_issues=[
                link["outwardIssue"]["key"]
                for link in fields.get("issuelinks", [])
                if "outwardIssue" in link
            ],
        )

    def _parse_user(self, raw_user: Optional[dict], required: bool = False) -> Optional[JiraUser]:
        """Parse raw Jira user data into JiraUser model.

        Args:
            raw_user: Raw user data from Jira API
            required: Whether this user field is required (e.g., reporter, author)

        Returns:
            Parsed JiraUser or None if raw_user is None and not required

        Raises:
            ValueError: If raw_user is None and required is True
        """
        if not raw_user:
            if required:
                raise ValueError("User data is required but not provided")
            return None
        return JiraUser(
            account_id=raw_user["accountId"],
            display_name=raw_user["displayName"],
            email_address=raw_user.get("emailAddress"),
        )

    def _parse_attachment(self, raw_attachment: dict) -> JiraAttachment:
        """Parse raw Jira attachment data into JiraAttachment model.

        Args:
            raw_attachment: Raw attachment data from Jira API

        Returns:
            Parsed JiraAttachment
        """
        # Parse author with type assertion since it's required
        author = self._parse_user(raw_attachment["author"], required=True)
        assert author is not None  # For type checker

        return JiraAttachment(
            id=raw_attachment["id"],
            filename=raw_attachment["filename"],
            size=raw_attachment["size"],
            mime_type=raw_attachment["mimeType"],
            content_url=raw_attachment["content"],
            created=datetime.fromisoformat(raw_attachment["created"].replace("Z", "+00:00")),
            author=author,
        )

    async def get_documents(self) -> List[Document]:
        """Fetch and process documents from Jira.

        Returns:
            List[Document]: List of processed documents
        """
        documents = []

        # Collect all issues
        issues = []
        async for issue in self.get_issues():
            issues.append(issue)

        # Convert issues to documents
        for issue in issues:
            content = f"{issue.summary}\n\n{issue.description or ''}"
            base_url = str(self.config.base_url).rstrip("/")
            document = Document(
                id=issue.id,
                content=content,
                source=self.config.project_key,
                source_type="jira",
                url=f"{base_url}/browse/{issue.key}",
                last_updated=issue.updated,
                metadata={
                    "project": self.config.project_key,
                    "issue_type": issue.issue_type,
                    "status": issue.status,
                    "key": issue.key,
                    "priority": issue.priority,
                    "labels": issue.labels,
                    "reporter": issue.reporter.display_name if issue.reporter else None,
                    "assignee": issue.assignee.display_name if issue.assignee else None,
                    "created": issue.created.isoformat(),
                    "updated": issue.updated.isoformat(),
                    "parent_key": issue.parent_key,
                    "subtasks": issue.subtasks,
                    "linked_issues": issue.linked_issues,
                    "attachments": (
                        [
                            {
                                "id": att.id,
                                "filename": att.filename,
                                "size": att.size,
                                "mime_type": att.mime_type,
                                "created": att.created.isoformat(),
                                "author": att.author.display_name if att.author else None,
                            }
                            for att in issue.attachments
                        ]
                        if issue.attachments
                        else []
                    ),
                },
            )
            documents.append(document)

        return documents
