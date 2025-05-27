"""Configuration for Confluence connector."""

import os
from enum import Enum
from typing import Self

from pydantic import ConfigDict, Field, field_validator, model_validator

from qdrant_loader.config.source_config import SourceConfig


class ConfluenceDeploymentType(str, Enum):
    """Confluence deployment types."""

    CLOUD = "cloud"
    DATACENTER = "datacenter"
    SERVER = "server"  # Legacy, treated same as datacenter


class ConfluenceSpaceConfig(SourceConfig):
    """Configuration for a Confluence space."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    space_key: str = Field(..., description="Key of the Confluence space")
    content_types: list[str] = Field(
        default=["page", "blogpost"], description="Types of content to process"
    )
    deployment_type: ConfluenceDeploymentType = Field(
        default=ConfluenceDeploymentType.CLOUD,
        description="Confluence deployment type (cloud, datacenter, or server)",
    )
    token: str | None = Field(
        ..., description="Confluence API token or Personal Access Token"
    )
    email: str | None = Field(
        default=None,
        description="Email associated with the Confluence account (Cloud only)",
    )

    include_labels: list[str] = Field(
        default=[],
        description="List of labels to include (empty list means include all)",
    )
    exclude_labels: list[str] = Field(
        default=[], description="List of labels to exclude"
    )

    @field_validator("content_types")
    @classmethod
    def validate_content_types(cls, v: list[str]) -> list[str]:
        """Validate content types."""
        valid_types = ["page", "blogpost", "comment"]
        for content_type in v:
            if content_type.lower() not in valid_types:
                raise ValueError(f"Content type must be one of {valid_types}")
        return [t.lower() for t in v]

    @field_validator("deployment_type", mode="before")
    @classmethod
    def auto_detect_deployment_type(
        cls, v: str | ConfluenceDeploymentType
    ) -> ConfluenceDeploymentType:
        """Auto-detect deployment type if not specified."""
        if isinstance(v, str):
            return ConfluenceDeploymentType(v.lower())
        return v

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

    @model_validator(mode="after")
    def validate_auth_config(self) -> Self:
        """Validate authentication configuration based on deployment type."""
        if self.deployment_type == ConfluenceDeploymentType.CLOUD:
            # Cloud requires email and token
            if not self.email:
                raise ValueError("Email is required for Confluence Cloud deployment")
            if not self.token:
                raise ValueError(
                    "API token is required for Confluence Cloud deployment"
                )
        else:
            # Data Center/Server requires Personal Access Token
            if not self.token:
                raise ValueError(
                    "Personal Access Token is required for Confluence Data Center/Server deployment"
                )

        return self
