"""Configuration for SharePoint connector using Microsoft Graph API.

This module provides configuration for the SharePoint connector that uses
GraphClient from office365-rest-python-client library.

Authentication Methods:
- CLIENT_CREDENTIALS: App-only auth with tenant_id + client_id + client_secret
- USER_CREDENTIALS: Delegated auth with tenant_id + client_id + username + password
  (Note: ROPC flow - does NOT work with MFA-enabled accounts)

Both methods require tenant_id and client_id because GraphClient needs them
for OAuth2 token acquisition.
"""

from enum import Enum
import os
from typing import List, Optional

from pydantic import Field, HttpUrl, field_validator, model_validator

from qdrant_loader.config.source_config import SourceConfig


class SharePointAuthMethod(str, Enum):
    """SharePoint authentication methods.

    CLIENT_CREDENTIALS: Recommended for production. Uses App Registration
        with client_id + client_secret. No MFA issues.

    USER_CREDENTIALS: For dev/test only. Uses ROPC flow which does NOT
        work with MFA-enabled accounts or Conditional Access policies.
    """

    CLIENT_CREDENTIALS = "client_credentials"
    USER_CREDENTIALS = "user_credentials"


class SharePointConfig(SourceConfig):
    """Configuration for SharePoint connector using Microsoft Graph API.

    Supports SharePoint Online via:
    - Client Credentials: App-only auth with client_id + client_secret
    - User Credentials: Delegated auth with username + password (ROPC)

    Both methods require tenant_id and client_id (Azure AD App).

    Example YAML:
        sharepoint:
          my-site:
            base_url: "https://company.sharepoint.com"
            site_url: "https://company.sharepoint.com/sites/mysite"
            relative_url: "/sites/mysite"
            tenant_id: "your-tenant-id"
            client_id: "your-client-id"
            client_secret: "your-client-secret"
            document_libraries:
              - "Documents"
              - "Shared Documents"
    """

    # Site configuration
    site_url: HttpUrl = Field(..., description="SharePoint site URL")
    relative_url: str = Field(
        ..., description="Site relative URL (e.g., /sites/mysite)"
    )
    document_libraries: List[str] = Field(
        default_factory=lambda: ["Documents"],
        description="Document libraries to process",
    )

    # Authentication - Common (required for both methods)
    auth_method: SharePointAuthMethod = Field(
        default=SharePointAuthMethod.CLIENT_CREDENTIALS,
        description="Authentication method",
    )
    tenant_id: Optional[str] = Field(
        default=None,
        description="Azure AD Tenant ID - required for both auth methods",
    )
    client_id: Optional[str] = Field(
        default=None,
        description="Azure AD Application (Client) ID - required for both auth methods",
    )

    # Authentication - Client Credentials specific
    client_secret: Optional[str] = Field(
        default=None,
        description="Azure AD Client Secret - required for CLIENT_CREDENTIALS",
    )

    # Authentication - User Credentials specific (ROPC - dev/test only)
    username: Optional[str] = Field(
        default=None,
        description="SharePoint username - required for USER_CREDENTIALS (ROPC)",
    )
    password: Optional[str] = Field(
        default=None,
        description="SharePoint password - required for USER_CREDENTIALS (ROPC)",
    )

    # Filtering (like Git connector pattern)
    include_paths: List[str] = Field(
        default_factory=list,
        description="Glob patterns for paths to include",
    )
    exclude_paths: List[str] = Field(
        default_factory=list,
        description="Glob patterns for paths to exclude",
    )
    file_types: List[str] = Field(
        default_factory=list,
        description="File extensions to process (e.g., ['pdf', 'docx'])",
    )
    max_file_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        ge=0,
        description="Maximum file size in bytes",
    )

    # Rate limiting
    requests_per_minute: int = Field(
        default=60,
        ge=1,
        le=600,
        description="Maximum API requests per minute",
    )

    @field_validator("file_types", mode="after")
    @classmethod
    def normalize_file_types(cls, v: List[str]) -> List[str]:
        """Normalize file types to lowercase without leading dots."""
        return [ft.lstrip(".").lower().strip() for ft in v] if v else []

    @model_validator(mode="after")
    def load_env_secrets(self):
        """Load secrets from environment variables if not provided.

        Supports the following environment variables:
        - SHAREPOINT_TENANT_ID: Azure AD Tenant ID
        - SHAREPOINT_CLIENT_ID: Azure AD Application (Client) ID
        - SHAREPOINT_CLIENT_SECRET: Client secret for CLIENT_CREDENTIALS auth
        - SHAREPOINT_USERNAME: Username for USER_CREDENTIALS auth (ROPC)
        - SHAREPOINT_PASSWORD: Password for USER_CREDENTIALS auth (ROPC)
        """
        if not self.tenant_id:
            self.tenant_id = os.getenv("SHAREPOINT_TENANT_ID")
        if not self.client_id:
            self.client_id = os.getenv("SHAREPOINT_CLIENT_ID")
        if not self.client_secret:
            self.client_secret = os.getenv("SHAREPOINT_CLIENT_SECRET")
        if not self.username:
            self.username = os.getenv("SHAREPOINT_USERNAME")
        if not self.password:
            self.password = os.getenv("SHAREPOINT_PASSWORD")
        return self

    @model_validator(mode="after")
    def validate_auth(self):
        """Validate authentication configuration.

        Both auth methods require tenant_id and client_id because GraphClient
        needs them for OAuth2 token acquisition:
        - CLIENT_CREDENTIALS: GraphClient(tenant=tenant).with_client_secret(client_id, client_secret)
        - USER_CREDENTIALS: GraphClient(tenant=tenant).with_username_and_password(client_id, username, password)
        """
        # Common requirements for both methods
        if not self.tenant_id:
            raise ValueError("tenant_id is required for authentication")
        if not self.client_id:
            raise ValueError("client_id is required for authentication")

        # Method-specific requirements
        if self.auth_method == SharePointAuthMethod.CLIENT_CREDENTIALS:
            if not self.client_secret:
                raise ValueError("client_secret is required for CLIENT_CREDENTIALS")

        if self.auth_method == SharePointAuthMethod.USER_CREDENTIALS:
            if not self.username:
                raise ValueError("username is required for USER_CREDENTIALS")
            if not self.password:
                raise ValueError("password is required for USER_CREDENTIALS")

        return self
