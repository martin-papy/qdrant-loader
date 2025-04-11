"""Jira connector package for qdrant-loader."""

from qdrant_loader.connectors.jira.jira_connector import JiraConnector
from qdrant_loader.connectors.jira.config import JiraConfig

__all__ = ["JiraConnector", "JiraConfig"] 