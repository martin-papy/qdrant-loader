"""Shared configuration types.

This module defines shared TypedDict types for different configuration structures
used across the application. These types provide type safety and documentation
for configuration data structures.
"""

from typing import TypedDict, Optional, List, Dict, Any


class GitConfig(TypedDict):
    """Configuration for Git repositories."""
    url: str
    branch: str
    include_paths: List[str]
    exclude_paths: List[str]
    file_types: List[str]
    max_file_size: int
    depth: int
    token: Optional[str]


class ConfluenceConfig(TypedDict):
    """Configuration for Confluence spaces."""
    url: str
    space_key: str
    content_types: List[str]
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
    token: str
    email: str


class PublicDocsConfig(TypedDict):
    """Configuration for public documentation sources."""
    base_url: str
    version: str
    content_type: str
    path_pattern: str
    exclude_paths: List[str]


class SourcesConfigDict(TypedDict):
    """Configuration for all sources."""
    public_docs: Dict[str, PublicDocsConfig]
    git_repos: Dict[str, GitConfig]
    confluence: Dict[str, ConfluenceConfig]
    jira: Dict[str, JiraConfig]


class GlobalConfigDict(TypedDict):
    """Global configuration settings."""
    chunking: Dict[str, Any]
    embedding: Dict[str, Any]
    logging: Dict[str, Any] 