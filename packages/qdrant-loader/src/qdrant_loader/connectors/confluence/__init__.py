"""Confluence connector package for qdrant-loader."""

from qdrant_loader.connectors.confluence.config import ConfluenceSpaceConfig
from qdrant_loader.connectors.confluence.connector import ConfluenceConnector

__all__ = ["ConfluenceConnector", "ConfluenceSpaceConfig"]
