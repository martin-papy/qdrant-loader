"""
EXPERIMENT with Jira DC / Jira Cloud

pilot_ingest.py — Run qdrant-loader but only ingest first MAX_ISSUES issue.
"""

from datetime import datetime
import sys
import os
from dotenv import load_dotenv

load_dotenv()

try:
    MAX_ISSUES = int(os.getenv("MAX_ISSUES", "200"))
    if MAX_ISSUES < 1:
        raise ValueError("MAX_ISSUES must be at least 1")
except ValueError:
    print("[pilot_ingest] ERROR: MAX_ISSUES must be an integer")
    sys.exit(1)

# Monkey-patch before import pipeline
from qdrant_loader.connectors.jira import data_center_connector as jira_dc_connector  # noqa: E402, I001
from qdrant_loader.connectors.jira import cloud_connector as jira_cloud_connector  # noqa: E402, I001

_original_dc_get_issues = jira_dc_connector.JiraDataCenterConnector.get_issues
_original_cloud_get_issues = jira_cloud_connector.JiraCloudConnector.get_issues


async def _limited_dc_get_issues(self, updated_after: datetime | None = None):
    """Set a limit on the number of ingested Jira Issues (tickets)"""
    print(f"[pilot_ingest] Patched Jira DC Connector: max {MAX_ISSUES} issues\n")
    count = 0
    async for issue in _original_dc_get_issues(self, updated_after):
        if count >= MAX_ISSUES:
            print(
                f"\n[pilot_ingest] Reached MAX_ISSUES={MAX_ISSUES}, stopping early.\n"
            )
            return
        yield issue
        count += 1
        if count % 10 == 0:
            print(f"[pilot_ingest] {count}/{MAX_ISSUES} issues collected...")


jira_dc_connector.JiraDataCenterConnector.get_issues = _limited_dc_get_issues


async def _limited_cloud_get_issues(self, updated_after: datetime | None = None):
    """Set a limit on the number of ingested Jira Issues (tickets)"""
    print(f"[pilot_ingest] Patched Jira Cloud Connector: max {MAX_ISSUES} issues\n")
    count = 0
    async for issue in _original_cloud_get_issues(self, updated_after):
        if count >= MAX_ISSUES:
            print(
                f"\n[pilot_ingest] Reached MAX_ISSUES={MAX_ISSUES}, stopping early.\n"
            )
            return
        yield issue
        count += 1
        if count % 10 == 0:
            print(f"[pilot_ingest] {count}/{MAX_ISSUES} issues collected...")


jira_cloud_connector.JiraCloudConnector.get_issues = _limited_cloud_get_issues


# Normal qdrant-loader CLI run
# Note: sys.argv is mutated here to simulate CLI execution.
# This is intentional because certain features
# are only available when running through the CLI, and are not fully supported via direct function calls.
from qdrant_loader.cli.cli import cli  # noqa: E402, I001

sys.argv = ["qdrant-loader", "serve", "--config", "config.yaml", "--env", ".env", "--host", "0.0.0.0"]

cli()
