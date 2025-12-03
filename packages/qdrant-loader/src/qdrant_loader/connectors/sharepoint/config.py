"""Configuration for SharePoint connector."""

from pydantic import HttpUrl, Field, field_validator, model_validator
from typing import Optional, List
from enum import Enum
import os
from qdrant_loader.config.source_config import SourceConfig


class SharePointAuthMethod(str, Enum):
    """SharePoint authentication methods."""
    CLIENT_CREDENTIALS = "client_credentials"
    USER_CREDENTIALS = "user_credentials"


class SharePointConfig(SourceConfig):
    """Configuration for a SharePoint repository with Azure AD authentication."""

    relative_url: str = Field(
        ...,
        description="Site relative URL"
    )

    # Authentication
    authentication_method: SharePointAuthMethod = Field(
        default=SharePointAuthMethod.CLIENT_CREDENTIALS
    )

    # Azure AD App Authentication (CLIENT_CREDENTIALS)
    tenant_id: Optional[str] = Field(
        default=None,
        description="Azure AD tenant ID - required for CLIENT_CREDENTIALS"
    )
    client_id: Optional[str] = Field(
        default=None,
        description="Azure AD Application (Client) ID - Required for CLIENT_CREDENTIALS"
    )
    client_secret: Optional[str] = Field(
        default=None,
        description="Azure AD Client Secret - Required for CLIENT_CREDENTIALS"
    )

    # User Authentication (For development/testing only)
    username: Optional[str] = Field(
        default=None,
        description="SharePoint username - Required for USER_CREDENTIALS"
    )
    password: Optional[str] = Field(
        default=None,
        description="SharePoint password - Required for USER_CREDENTIALS"
    )

    document_libraries: List[str] = Field(default_factory=list)
    sharepoint_lists: List[str] = Field(default_factory=list)

    # File Processing
    file_extensions: List[str] = Field(default_factory=list)
    max_file_size: int = 10 * 1024 * 1024  # 10 MB

    # Filtering
    exclude_paths: List[str] = Field(default_factory=list)
    include_content_types: List[str] = Field(default_factory=list)

    # Rate limiting
    requests_per_minute: int = Field(
        default=60,
        description="Maximum API requests per minute",
        ge=1,
        le=600
    )

    @field_validator("file_extensions", mode="after")
    def normalize_extensions(cls, v):
        return [ft.lstrip(".").lower().strip() for ft in v] if v else []


    @model_validator(mode="after")
    def load_env_secret(self):
        if (
            self.authentication_method == SharePointAuthMethod.CLIENT_CREDENTIALS
            and not self.client_secret
        ):
            self.client_secret = os.getenv("SHAREPOINT_CLIENT_SECRET")
        return self

    @model_validator(mode="after")
    def validate_auth(self):
        if self.authentication_method == SharePointAuthMethod.CLIENT_CREDENTIALS:
            if not self.tenant_id:
                raise ValueError("tenant_id is required for CLIENT_CREDENTIALS")
            if not self.client_id:
                raise ValueError("client_id is required for CLIENT_CREDENTIALS")
            if not self.client_secret:
                raise ValueError("client_secret is required for CLIENT_CREDENTIALS")

        if self.authentication_method == SharePointAuthMethod.USER_CREDENTIALS:
            if not self.username:
                raise ValueError("username is required for USER_CREDENTIALS")
            if not self.password:
                raise ValueError("password is required for USER_CREDENTIALS")

        return self
