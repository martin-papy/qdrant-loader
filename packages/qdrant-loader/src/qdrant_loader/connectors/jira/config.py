"""Configuration for Jira connector."""

import os
from enum import StrEnum
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from qdrant_loader.config.source_config import SourceConfig


class JiraDeploymentType(StrEnum):
    """Jira deployment types."""

    CLOUD = "cloud"
    DATACENTER = "datacenter"


class JiraFieldType(StrEnum):
    SIMPLE = "simple"
    OBJECT = "object"  # extract attribute from single object
    ARRAY = "array"  # plain list
    ARRAY_OBJECT = "array_object"  # extract attribute from list of objects


class JiraExtraField(BaseModel):
    param_name: str = Field(
        ...,
        description="The Jira API parameter name (e.g., 'customfield_11406', 'priority')",
    )
    name: str = Field(
        ...,
        description="Target attribute name on JiraIssue (e.g., 'sah_project')",
    )
    field_type: JiraFieldType = Field(
        default=JiraFieldType.SIMPLE,
        description=(
            "Extraction strategy: "
            "'simple' = direct value, "
            "'object' = extract attribute from object (requires attr_name), "
            "'array' = plain list, "
            "'array_object' = extract attribute from list of objects (requires attr_name)"
        ),
    )
    attr_name: str | None = Field(
        default=None,
        description="Attribute to extract from object(s) (e.g., 'name', 'value')",
    )

    @model_validator(mode="after")
    def validate_attr_requirement(self) -> "JiraExtraField":
        if self.field_type in {JiraFieldType.OBJECT, JiraFieldType.ARRAY_OBJECT}:
            if not self.attr_name:
                raise ValueError(
                    f"'attr_name' is required for field_type='{self.field_type}'"
                )
        return self


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
    extra_fields: list[JiraExtraField] | None = Field(
        default=None,
        description="Optional list of extra Jira fields to retrieve with their extraction type.",
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

    @field_validator("extra_fields")
    @classmethod
    def validate_extra_fields_unique(
        cls, v: list[JiraExtraField] | None
    ) -> list[JiraExtraField] | None:
        """Validate that extra field param_names and names are unique."""
        if v is None:
            return v
        param_names = [f.param_name for f in v if f.param_name is not None]
        if len(param_names) != len(set(param_names)):
            raise ValueError("Extra field 'param_name' values must be unique")
        names = [f.name for f in v if f.name is not None]
        if len(names) != len(set(names)):
            raise ValueError("Extra field 'name' values must be unique")
        return v
