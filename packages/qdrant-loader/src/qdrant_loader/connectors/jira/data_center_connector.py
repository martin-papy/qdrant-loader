"""Jira connector implementation."""

from collections.abc import AsyncGenerator
from datetime import datetime
from urllib.parse import urlparse  # noqa: F401 - may be used in URL handling

from requests.auth import HTTPBasicAuth  # noqa: F401 - compatibility

from qdrant_loader.connectors.jira.connector import BaseJiraConnector
from qdrant_loader.connectors.jira.models import (
    JiraIssue,
)
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class JiraDataCenterConnector(BaseJiraConnector):
    """Jira data center connector for fetching and processing issues."""

    SEARCH_ENDPOINT = "search"

    def _get_api_url(self, endpoint: str) -> str:
        """Construct the full API URL for an endpoint.

        Args:
            endpoint: API endpoint path

        Returns:
            str: Full API URL
        """
        return f"{self.base_url}/rest/api/2/{endpoint}"

    async def get_issues(
        self, updated_after: datetime | None = None
    ) -> AsyncGenerator[JiraIssue, None]:
        """
        Get all issues from Jira.

        Args:
            updated_after: Optional datetime to filter issues updated after this time

        Yields:
            JiraIssue objects
        """
        start_at = 0
        page_size = self.config.page_size
        total_issues = 0
        processed_count = 0

        logger.info(
            "🎫 Starting JIRA issue retrieval",
            project_key=self.config.project_key,
            page_size=page_size,
            updated_after=updated_after.isoformat() if updated_after else None,
        )

        while True:
            jql = self._build_jql_filter(updated_after)

            params = {
                "jql": jql,
                "startAt": start_at,
                "maxResults": page_size,
                "expand": "changelog",
                "fields": "*all",
            }

            logger.debug(
                "Fetching JIRA issues page",
                start_at=start_at,
                page_size=page_size,
                jql=jql,
            )

            try:
                response = await self._make_request(
                    "GET", self.SEARCH_ENDPOINT, params=params
                )
            except Exception as e:
                logger.error(
                    "Failed to fetch JIRA issues page",
                    start_at=start_at,
                    page_size=page_size,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise

            if not response or not response.get("issues"):
                logger.debug(
                    "No more JIRA issues found, stopping pagination",
                    start_at=start_at,
                    total_processed=start_at,
                    issues_processed=processed_count,
                )
                break

            issues = response["issues"]

            # Update total count if not set
            if total_issues == 0:
                total_issues = response.get("total", 0)
                logger.info(f"🎫 Found {total_issues} JIRA issues to process")

            # Log progress every 100 issues instead of every 50
            progress_log_interval = 100

            for i, issue in enumerate(issues):
                try:
                    parsed_issue = self._parse_issue(issue,self.config.extra_fields)
                    yield parsed_issue
                    processed_count += 1

                    if (start_at + i + 1) % progress_log_interval == 0:
                        progress_percent = (
                            round((start_at + i + 1) / total_issues * 100, 1)
                            if total_issues > 0
                            else 0
                        )
                        logger.info(
                            f"🎫 Progress: {start_at + i + 1}/{total_issues} issues ({progress_percent}%)"
                        )

                except Exception as e:
                    logger.error(
                        "Failed to parse JIRA issue",
                        issue_id=issue.get("id"),
                        issue_key=issue.get("key"),
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    # Continue processing other issues instead of failing completely
                    continue

            # Check if we've processed all issues
            start_at += len(issues)
            if start_at >= total_issues:
                logger.info(
                    f"✅ Completed JIRA issue retrieval: "
                    f"{start_at} issues attempted, "
                    f"{processed_count} successfully processed"
                )
                break
