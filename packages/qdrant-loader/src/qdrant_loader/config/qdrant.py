"""Qdrant configuration settings.

This module defines the Qdrant-specific configuration settings.
"""

from pydantic import Field

from qdrant_loader.config.base import BaseConfig


class QdrantConfig(BaseConfig):
    """Configuration for Qdrant vector database."""

    url: str = Field(..., description="Qdrant server URL")
    api_key: str | None = Field(default=None, description="Qdrant API key")
    collection_name: str = Field(..., description="Qdrant collection name")

    def to_dict(self) -> dict[str, str | None]:
        """Convert the configuration to a dictionary."""
        return {
            "url": self.url,
            "api_key": self.api_key,
            "collection_name": self.collection_name,
        }
