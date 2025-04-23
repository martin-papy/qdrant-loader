"""Configuration for Jira connector."""

import os

from pydantic import ConfigDict, Field, HttpUrl, field_validator, model_validator

from qdrant_loader.config.source_config import SourceConfig


class JiraProjectConfig(SourceConfig):
    """Configuration for a Jira project."""

    # Authentication
    token: str | None = Field(default=None, description="Jira API token")
    email: str | None = Field(default=None, description="Email associated with the API token")
    base_url: HttpUrl = Field(
        ..., description="Base URL of the Jira instance (e.g., 'https://your-domain.atlassian.net')"
    )

    # Project configuration
    project_key: str = Field(..., description="Project key to process (e.g., 'PROJ')", min_length=1)

    # Rate limiting
    requests_per_minute: int = Field(
        default=60, description="Maximum number of requests per minute", ge=1, le=1000
    )

    # Pagination
    page_size: int = Field(
        default=100, description="Number of items per page for paginated requests", ge=1, le=100
    )

    # Attachment handling
    process_attachments: bool = Field(
        default=True, description="Whether to process issue attachments"
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

    @model_validator(mode="before")
    @classmethod
    def validate_env_vars(cls, values: dict) -> dict:
        """Load values from environment variables if not provided."""
        if values.get("token") is None:
            values["token"] = os.getenv("JIRA_TOKEN")
        if values.get("email") is None:
            values["email"] = os.getenv("JIRA_EMAIL")

        if not values.get("token"):
            raise ValueError(
                "token must be provided either directly or via JIRA_TOKEN environment variable"
            )
        if not values.get("email"):
            raise ValueError(
                "email must be provided either directly or via JIRA_EMAIL environment variable"
            )

        return values

    @field_validator("issue_types", "include_statuses")
    @classmethod
    def validate_list_items(cls, v: list[str]) -> list[str]:
        """Validate that list items are not empty strings."""
        if any(not item.strip() for item in v):
            raise ValueError("List items cannot be empty strings")
        return [item.strip() for item in v]
