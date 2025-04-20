"""Shared configuration types.

This module defines shared TypedDict types for different configuration structures
used across the application. These types provide type safety and documentation
for configuration data structures.
"""

from enum import Enum
from typing import Any, TypedDict


class SourceType(str, Enum):
    """Enum for supported source types."""

    PUBLICDOCS = "publicdocs"
    GIT = "git"
    CONFLUENCE = "confluence"
    JIRA = "jira"


class GitConfig(TypedDict):
    """Configuration for Git repositories."""

    base_url: str
    branch: str
    include_paths: list[str]
    exclude_paths: list[str]
    file_types: list[str]
    max_file_size: int
    depth: int
    token: str | None


class ConfluenceConfig(TypedDict):
    """Configuration for Confluence spaces."""

    base_url: str
    space_key: str
    content_types: list[str]
    token: str
    email: str


class JiraConfig(TypedDict):
    """Configuration for Jira projects."""

    base_url: str
    project_key: str
    requests_per_minute: int
    page_size: int
    process_attachments: bool
    track_last_sync: bool
    api_token: str
    email: str
    issue_types: list[str]
    include_statuses: list[str]


class PublicDocsConfig(TypedDict):
    """Configuration for public documentation sources."""

    base_url: str
    version: str
    content_type: str
    path_pattern: str
    exclude_paths: list[str]


class SourcesConfigDict(TypedDict):
    """Configuration for all sources."""

    publicdocs: dict[str, PublicDocsConfig]
    git: dict[str, GitConfig]
    confluence: dict[str, ConfluenceConfig]
    jira: dict[str, JiraConfig]


class GlobalConfigDict(TypedDict):
    """Global configuration settings."""

    chunking: dict[str, Any]
    embedding: dict[str, Any]
    sources: dict[str, Any]
    state_management: dict[str, Any]
