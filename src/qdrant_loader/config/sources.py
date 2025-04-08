"""Sources configuration.

This module defines the configuration for all data sources, including Git repositories,
Confluence spaces, Jira projects, and public documentation.
"""

from typing import Dict, Any, Optional
from pydantic import Field

from .base import BaseConfig, BaseSourceConfig
from .types import (
    SourcesConfigDict,
    GitConfig,
    ConfluenceConfig,
    JiraConfig,
    PublicDocsConfig
)


class GitRepoConfig(BaseSourceConfig):
    """Configuration for a Git repository."""
    url: str = Field(..., description="URL of the Git repository")
    branch: str = Field(default="main", description="Branch to process")
    include_paths: list[str] = Field(default=["/"], description="Paths to include")
    exclude_paths: list[str] = Field(default=[], description="Paths to exclude")
    file_types: list[str] = Field(default=["*"], description="File types to process")
    max_file_size: int = Field(default=1048576, description="Maximum file size in bytes")
    depth: int = Field(default=1, description="Maximum depth to traverse")
    token: Optional[str] = Field(default=None, description="Authentication token")

    def validate(self) -> None:
        """Validate the configuration."""
        if self.depth < 0:
            raise ValueError("Depth must be a positive integer")
        if self.max_file_size < 0:
            raise ValueError("Max file size must be a positive integer")


class ConfluenceSpaceConfig(BaseSourceConfig):
    """Configuration for a Confluence space."""
    url: str = Field(..., description="Base URL of the Confluence instance")
    space_key: str = Field(..., description="Key of the Confluence space")
    content_types: list[str] = Field(
        default=["page", "blogpost"],
        description="Types of content to process"
    )
    token: str = Field(..., description="Authentication token")
    email: str = Field(..., description="Email for authentication")

    def validate(self) -> None:
        """Validate the configuration."""
        valid_content_types = ["page", "blogpost"]
        for content_type in self.content_types:
            if content_type not in valid_content_types:
                raise ValueError(f"Invalid content type: {content_type}")


class JiraProjectConfig(BaseSourceConfig):
    """Configuration for a Jira project."""
    base_url: str = Field(..., description="Base URL of the Jira instance")
    project_key: str = Field(..., description="Key of the Jira project")
    requests_per_minute: int = Field(
        default=60,
        description="Maximum number of requests per minute"
    )
    page_size: int = Field(default=50, description="Number of items per page")
    process_attachments: bool = Field(
        default=True,
        description="Whether to process attachments"
    )
    track_last_sync: bool = Field(
        default=True,
        description="Whether to track last sync time"
    )
    token: str = Field(..., description="Authentication token")
    email: str = Field(..., description="Email for authentication")

    def validate(self) -> None:
        """Validate the configuration."""
        if self.requests_per_minute < 1:
            raise ValueError("Requests per minute must be positive")
        if self.page_size < 1:
            raise ValueError("Page size must be positive")


class PublicDocsConfig(BaseSourceConfig):
    """Configuration for public documentation."""
    base_url: str = Field(..., description="Base URL of the documentation")
    version: str = Field(..., description="Version of the documentation")
    content_type: str = Field(..., description="Type of content")
    path_pattern: str = Field(..., description="Pattern for paths to include")
    exclude_paths: list[str] = Field(
        default=[],
        description="Paths to exclude"
    )

    def validate(self) -> None:
        """Validate the configuration."""
        valid_content_types = ["html", "markdown"]
        if self.content_type not in valid_content_types:
            raise ValueError(f"Invalid content type: {self.content_type}")


class SourcesConfig(BaseConfig):
    """Configuration for all sources."""
    public_docs: Dict[str, PublicDocsConfig] = Field(
        default_factory=dict,
        description="Public documentation sources"
    )
    git_repos: Dict[str, GitRepoConfig] = Field(
        default_factory=dict,
        description="Git repository sources"
    )
    confluence: Dict[str, ConfluenceSpaceConfig] = Field(
        default_factory=dict,
        description="Confluence space sources"
    )
    jira: Dict[str, JiraProjectConfig] = Field(
        default_factory=dict,
        description="Jira project sources"
    )

    def to_dict(self) -> SourcesConfigDict:
        """Convert the configuration to a dictionary."""
        return {
            "public_docs": {
                name: config.dict()
                for name, config in self.public_docs.items()
            },
            "git_repos": {
                name: config.dict()
                for name, config in self.git_repos.items()
            },
            "confluence": {
                name: config.dict()
                for name, config in self.confluence.items()
            },
            "jira": {
                name: config.dict()
                for name, config in self.jira.items()
            }
        }