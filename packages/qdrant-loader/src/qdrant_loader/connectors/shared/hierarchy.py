"""Hierarchy tracking utilities for document metadata enrichment.

POC1-002: Implements hierarchy tracking patterns inspired by Unstructured.io.
Provides unified hierarchy metadata generation across all connector types.

Key concepts:
- parent_id: ID of the parent element (section, document, or container)
- depth: Integer depth in hierarchy (0=root, 1=H1, 2=H2, etc.)
- breadcrumb: List of ancestor titles ["Root", "Parent", "Current"]
- breadcrumb_text: String representation "Root > Parent > Current"
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class HierarchyMetadata:
    """Standardized hierarchy metadata structure.

    Attributes:
        parent_id: ID of parent element (None for root)
        depth: Depth in hierarchy (0 = root level)
        breadcrumb: List of ancestor names
        breadcrumb_text: Human-readable path string
    """
    parent_id: str | None
    depth: int
    breadcrumb: list[str]
    breadcrumb_text: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for metadata storage."""
        return {
            "parent_id": self.parent_id,
            "depth": self.depth,
            "breadcrumb": self.breadcrumb,
            "breadcrumb_text": self.breadcrumb_text,
        }


def build_hierarchy_from_path(
    file_path: str,
    separator: str = "/",
    root_name: str | None = None,
) -> HierarchyMetadata:
    """Build hierarchy metadata from a file path.

    Used by: Git connector, LocalFile connector, PublicDocs connector.

    Args:
        file_path: File path like "docs/api/reference.md"
        separator: Path separator (default "/")
        root_name: Optional root name to prepend (e.g., repository name)

    Returns:
        HierarchyMetadata with path-based hierarchy

    Example:
        >>> build_hierarchy_from_path("docs/api/reference.md", root_name="my-repo")
        HierarchyMetadata(
            parent_id="docs/api",
            depth=3,
            breadcrumb=["my-repo", "docs", "api", "reference.md"],
            breadcrumb_text="my-repo > docs > api > reference.md"
        )
    """
    # Split path and filter empty segments
    parts = [p for p in file_path.split(separator) if p]

    # Prepend root name if provided
    if root_name:
        parts = [root_name] + parts

    # Calculate depth (number of path segments)
    depth = len(parts)

    # Build breadcrumb
    breadcrumb = parts.copy()

    # Generate breadcrumb text
    breadcrumb_text = " > ".join(breadcrumb)

    # Parent ID is the directory path (excluding filename)
    if len(parts) > 1:
        parent_id = separator.join(parts[:-1])
    else:
        parent_id = None

    return HierarchyMetadata(
        parent_id=parent_id,
        depth=depth,
        breadcrumb=breadcrumb,
        breadcrumb_text=breadcrumb_text,
    )


def build_hierarchy_from_ancestors(
    ancestors: list[dict[str, Any]],
    space_name: str | None = None,
    current_title: str | None = None,
) -> HierarchyMetadata:
    """Build hierarchy metadata from Confluence-style ancestors.

    Used by: Confluence connector.

    Args:
        ancestors: List of ancestor pages [{"id": "123", "title": "Parent"}, ...]
        space_name: Optional space name to prepend
        current_title: Current page title to append

    Returns:
        HierarchyMetadata with ancestor-based hierarchy

    Example:
        >>> ancestors = [
        ...     {"id": "1", "title": "Documentation"},
        ...     {"id": "2", "title": "API Reference"}
        ... ]
        >>> build_hierarchy_from_ancestors(ancestors, "DEV", "Auth API")
        HierarchyMetadata(
            parent_id="2",
            depth=4,
            breadcrumb=["DEV", "Documentation", "API Reference", "Auth API"],
            breadcrumb_text="DEV > Documentation > API Reference > Auth API"
        )
    """
    breadcrumb: list[str] = []

    # Add space name as root
    if space_name:
        breadcrumb.append(space_name)

    # Add ancestors in order (from root to immediate parent)
    for ancestor in ancestors:
        title = ancestor.get("title", ancestor.get("name", ""))
        if title:
            breadcrumb.append(title)

    # Add current page title
    if current_title:
        breadcrumb.append(current_title)

    # Depth is total breadcrumb length
    depth = len(breadcrumb)

    # Parent ID is the last ancestor's ID
    parent_id = None
    if ancestors:
        parent_id = str(ancestors[-1].get("id", ""))

    # Generate breadcrumb text
    breadcrumb_text = " > ".join(breadcrumb)

    return HierarchyMetadata(
        parent_id=parent_id,
        depth=depth,
        breadcrumb=breadcrumb,
        breadcrumb_text=breadcrumb_text,
    )


def build_hierarchy_from_jira(
    issue_type: str,
    parent_key: str | None = None,
    epic_key: str | None = None,
    project_key: str | None = None,
    issue_key: str | None = None,
) -> HierarchyMetadata:
    """Build hierarchy metadata from JIRA issue relationships.

    Used by: JIRA connector.

    JIRA hierarchy: Project -> Epic -> Story/Task -> Sub-task

    Args:
        issue_type: Type of issue (Epic, Story, Task, Sub-task, Bug)
        parent_key: Parent issue key (for sub-tasks)
        epic_key: Epic key (for stories/tasks linked to epic)
        project_key: Project key
        issue_key: Current issue key

    Returns:
        HierarchyMetadata with JIRA-based hierarchy

    Example:
        >>> build_hierarchy_from_jira(
        ...     issue_type="Sub-task",
        ...     parent_key="PROJ-100",
        ...     epic_key="PROJ-50",
        ...     project_key="PROJ",
        ...     issue_key="PROJ-101"
        ... )
        HierarchyMetadata(
            parent_id="PROJ-100",
            depth=4,
            breadcrumb=["PROJ", "PROJ-50", "PROJ-100", "PROJ-101"],
            breadcrumb_text="PROJ > PROJ-50 > PROJ-100 > PROJ-101"
        )
    """
    breadcrumb: list[str] = []

    # Always start with project
    if project_key:
        breadcrumb.append(project_key)

    # Add epic if present (for non-epic issues)
    if epic_key and issue_type.lower() != "epic":
        breadcrumb.append(epic_key)

    # Add parent for sub-tasks
    if parent_key and issue_type.lower() == "sub-task":
        breadcrumb.append(parent_key)

    # Add current issue
    if issue_key:
        breadcrumb.append(issue_key)

    # Calculate depth based on issue type
    depth = len(breadcrumb)

    # Determine parent ID based on hierarchy
    parent_id = None
    if issue_type.lower() == "sub-task" and parent_key:
        parent_id = parent_key
    elif epic_key and issue_type.lower() != "epic":
        parent_id = epic_key
    elif project_key and issue_type.lower() == "epic":
        parent_id = project_key

    # Generate breadcrumb text
    breadcrumb_text = " > ".join(breadcrumb)

    return HierarchyMetadata(
        parent_id=parent_id,
        depth=depth,
        breadcrumb=breadcrumb,
        breadcrumb_text=breadcrumb_text,
    )


def build_hierarchy_from_markdown_sections(
    section_path: list[str],
    section_level: int,
    document_id: str | None = None,
    document_title: str | None = None,
    section_id: str | None = None,
    parent_section_id: str | None = None,
) -> HierarchyMetadata:
    """Build hierarchy metadata from markdown section structure.

    Used by: Markdown chunking strategy.

    Args:
        section_path: List of parent section titles ["H1 Title", "H2 Title"]
        section_level: Current section header level (1-6)
        document_id: Source document ID
        document_title: Source document title
        section_id: Current section/chunk ID
        parent_section_id: Parent section/chunk ID

    Returns:
        HierarchyMetadata with section-based hierarchy

    Example:
        >>> build_hierarchy_from_markdown_sections(
        ...     section_path=["Installation", "Prerequisites"],
        ...     section_level=3,
        ...     document_title="Getting Started Guide"
        ... )
        HierarchyMetadata(
            parent_id=None,
            depth=3,
            breadcrumb=["Getting Started Guide", "Installation", "Prerequisites"],
            breadcrumb_text="Getting Started Guide > Installation > Prerequisites"
        )
    """
    breadcrumb: list[str] = []

    # Add document title as root if provided
    if document_title:
        breadcrumb.append(document_title)

    # Add section path
    breadcrumb.extend(section_path)

    # Depth is based on section level (H1=1, H2=2, etc.)
    # Add 1 for document level
    depth = section_level + (1 if document_title else 0)

    # Use parent_section_id if provided, otherwise construct from path
    parent_id = parent_section_id

    # Generate breadcrumb text
    breadcrumb_text = " > ".join(breadcrumb)

    return HierarchyMetadata(
        parent_id=parent_id,
        depth=depth,
        breadcrumb=breadcrumb,
        breadcrumb_text=breadcrumb_text,
    )


def merge_hierarchy_metadata(
    base_metadata: dict[str, Any],
    hierarchy: HierarchyMetadata,
) -> dict[str, Any]:
    """Merge hierarchy metadata into existing document metadata.

    Args:
        base_metadata: Existing document metadata dictionary
        hierarchy: HierarchyMetadata to merge

    Returns:
        Updated metadata dictionary with hierarchy fields
    """
    result = base_metadata.copy()
    result.update(hierarchy.to_dict())
    return result
