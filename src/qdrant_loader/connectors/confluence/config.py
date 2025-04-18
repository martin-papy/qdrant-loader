"""Configuration for Confluence connector."""

import os

from pydantic import ConfigDict, Field, field_validator

from qdrant_loader.config.source_config import SourceConfig


class ConfluenceSpaceConfig(SourceConfig):
    """Configuration for a Confluence space."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    space_key: str = Field(..., description="Key of the Confluence space")
    content_types: list[str] = Field(
        default=["page", "blogpost"], description="Types of content to process"
    )
    token: str | None = Field(..., description="Confluence API token")
    email: str | None = Field(..., description="Email associated with the Confluence account")
    include_labels: list[str] = Field(
        default=[], description="List of labels to include (empty list means include all)"
    )
    exclude_labels: list[str] = Field(default=[], description="List of labels to exclude")

    @field_validator("content_types")
    @classmethod
    def validate_content_types(cls, v: list[str]) -> list[str]:
        """Validate content types."""
        valid_types = ["page", "blogpost", "comment"]
        for content_type in v:
            if content_type.lower() not in valid_types:
                raise ValueError(f"Content type must be one of {valid_types}")
        return [t.lower() for t in v]

    @field_validator("token", mode="after")
    @classmethod
    def load_token_from_env(cls, v: str | None) -> str | None:
        """Load token from environment variable if not provided."""
        return v or os.getenv("CONFLUENCE_TOKEN")

    @field_validator("email", mode="after")
    @classmethod
    def load_email_from_env(cls, v: str | None) -> str | None:
        """Load email from environment variable if not provided."""
        return v or os.getenv("CONFLUENCE_EMAIL")
