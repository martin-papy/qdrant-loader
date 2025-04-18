"""Jira connector package for qdrant-loader."""

from qdrant_loader.connectors.jira.config import JiraConfig
from qdrant_loader.connectors.jira.jira_connector import JiraConnector

__all__ = ["JiraConfig", "JiraConnector"]
