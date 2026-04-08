"""Configuration for Jira connector."""

import os
from enum import StrEnum
from typing import Self

from pydantic import ConfigDict, Field, HttpUrl, field_validator, model_validator

from qdrant_loader.config.source_config import SourceConfig


class JiraDeploymentType(StrEnum):
    """Jira deployment types."""

    CLOUD = "cloud"
    DATACENTER = "datacenter"


class JiraProjectConfig(SourceConfig):
    """Configuration for a Jira project."""

    # Authentication
    token: str | None = Field(
        default=None, description="Jira API token or Personal Access Token"
    )
    email: str | None = Field(
        default=None, description="Email associated with the API token (Cloud only)"
    )
    base_url: HttpUrl = Field(
        ...,
        description="Base URL of the Jira instance (e.g., 'https://your-domain.atlassian.net')",
    )

    # Project configuration
    project_key: str = Field(
        ..., description="Project key to process (e.g., 'PROJ')", min_length=1
    )

    # Deployment type
    deployment_type: JiraDeploymentType = Field(
        default=JiraDeploymentType.CLOUD,
        description="Jira deployment type (cloud, datacenter, or server)",
    )

    # Rate limiting
    requests_per_minute: int = Field(
        default=60, description="Maximum number of requests per minute", ge=1, le=1000
    )

    # Pagination
    page_size: int = Field(
        default=100,
        description="Number of items per page for paginated requests",
        ge=1,
        le=100,
    )

    # Attachment handling
    download_attachments: bool = Field(
        default=False, description="Whether to download and process issue attachments"
    )

    # Additional configuration
    issue_types: list[str] = Field(
        default=[],
        description="Optional list of issue types to process (e.g., ['Bug', 'Story']). If empty, all types are processed.",
    )
    include_statuses: list[str] = Field(
        default=[],
        description="Optional list of statuses to include (e.g., ['Open', 'In Progress']). If empty, all statuses are included.",
    )

    model_config = ConfigDict(validate_default=True, arbitrary_types_allowed=True)

    @field_validator("deployment_type", mode="before")
    @classmethod
    def auto_detect_deployment_type(
        cls, v: str | JiraDeploymentType
    ) -> JiraDeploymentType:
        """Auto-detect deployment type if not specified."""
        if isinstance(v, str):
            return JiraDeploymentType(v.lower())
        return v

    @field_validator("token", mode="after")
    @classmethod
    def load_token_from_env(cls, v: str | None) -> str | None:
        """Load token from environment variable if not provided."""
        return v or os.getenv("JIRA_TOKEN")

    @field_validator("email", mode="after")
    @classmethod
    def load_email_from_env(cls, v: str | None) -> str | None:
        """Load email from environment variable if not provided."""
        return v or os.getenv("JIRA_EMAIL")

    @model_validator(mode="after")
    def validate_no_placeholders(self) -> Self:
        """Fail immediately if any required field still contains an un-substituted ${VAR} placeholder."""
        import re

        _placeholder = re.compile(r"\$\{[^}]+\}")

        fields_to_check: dict[str, str | None] = {
            "project_key": self.project_key,
            "base_url": str(self.base_url) if self.base_url else None,
            "token": self.token,
            "email": self.email,
        }

        bad: list[str] = []
        for field_name, value in fields_to_check.items():
            if value and _placeholder.search(value):
                # Extract the variable name for a helpful hint
                var = _placeholder.search(value).group(0)  # type: ignore[union-attr]
                bad.append(f"  - {field_name}: {var} (env var not set)")

        if bad:
            raise ValueError(
                "Jira source config contains un-substituted environment variables.\n"
                "Set the following variables in your .env file or shell before running:\n"
                + "\n".join(bad)
            )

        return self

    @model_validator(mode="after")
    def validate_auth_config(self) -> Self:
        """Validate authentication configuration based on deployment type."""
        if self.deployment_type == JiraDeploymentType.CLOUD:
            # Cloud requires email and token
            if not self.email:
                raise ValueError("Email is required for Jira Cloud deployment")
            if not self.token:
                raise ValueError("API token is required for Jira Cloud deployment")
        else:
            # Data Center/Server requires Personal Access Token
            if not self.token:
                raise ValueError(
                    "Personal Access Token is required for Jira Data Center/Server deployment"
                )

        return self

    @field_validator("issue_types", "include_statuses")
    @classmethod
    def validate_list_items(cls, v: list[str]) -> list[str]:
        """Validate that list items are not empty strings."""
        if any(not item.strip() for item in v):
            raise ValueError("List items cannot be empty strings")
        return [item.strip() for item in v]
