"""Jira connector package for qdrant-loader."""

from qdrant_loader.connectors.jira.config import JiraProjectConfig
from qdrant_loader.connectors.jira.connector import JiraConnector

__all__ = ["JiraConnector", "JiraProjectConfig"]
