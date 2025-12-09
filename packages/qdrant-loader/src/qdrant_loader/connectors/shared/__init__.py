"""Shared utilities for connectors (HTTP, attachments, hierarchy, etc.)."""

from .hierarchy import (
    HierarchyMetadata,
    build_hierarchy_from_ancestors,
    build_hierarchy_from_jira,
    build_hierarchy_from_markdown_sections,
    build_hierarchy_from_path,
    merge_hierarchy_metadata,
)

__all__ = [
    "HierarchyMetadata",
    "build_hierarchy_from_path",
    "build_hierarchy_from_ancestors",
    "build_hierarchy_from_jira",
    "build_hierarchy_from_markdown_sections",
    "merge_hierarchy_metadata",
]
