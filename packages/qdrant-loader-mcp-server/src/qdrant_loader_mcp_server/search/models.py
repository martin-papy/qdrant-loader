"""Search result models."""

from pydantic import BaseModel


class SearchResult(BaseModel):
    """Search result model."""

    score: float
    text: str
    source_type: str
    source_title: str
    source_url: str | None = None
    file_path: str | None = None
    repo_name: str | None = None

    # Project information (for multi-project support)
    project_id: str | None = None
    project_name: str | None = None
    project_description: str | None = None
    collection_name: str | None = None

    # Hierarchy information (primarily for Confluence)
    parent_id: str | None = None
    parent_title: str | None = None
    breadcrumb_text: str | None = None
    depth: int | None = None
    children_count: int | None = None
    hierarchy_context: str | None = None

    # Attachment information (for files attached to documents)
    is_attachment: bool = False
    parent_document_id: str | None = None
    parent_document_title: str | None = None
    attachment_id: str | None = None
    original_filename: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    attachment_author: str | None = None
    attachment_context: str | None = None

    def get_display_title(self) -> str:
        """Get the display title with hierarchy context if available."""
        if self.breadcrumb_text and self.source_type == "confluence":
            return f"{self.source_title} ({self.breadcrumb_text})"
        return self.source_title

    def get_project_info(self) -> str | None:
        """Get formatted project information for display."""
        if not self.project_id:
            return None

        project_info = f"Project: {self.project_name or self.project_id}"
        if self.project_description:
            project_info += f" - {self.project_description}"
        if self.collection_name:
            project_info += f" (Collection: {self.collection_name})"
        return project_info

    def get_hierarchy_info(self) -> str | None:
        """Get formatted hierarchy information for display."""
        if self.source_type != "confluence" or not self.hierarchy_context:
            return None
        return self.hierarchy_context

    def is_root_document(self) -> bool:
        """Check if this is a root document (no parent)."""
        return self.parent_id is None

    def has_children(self) -> bool:
        """Check if this document has children."""
        return self.children_count is not None and self.children_count > 0

    def get_attachment_info(self) -> str | None:
        """Get formatted attachment information for display."""
        if not self.is_attachment or not self.attachment_context:
            return None
        return self.attachment_context

    def is_file_attachment(self) -> bool:
        """Check if this is a file attachment."""
        return self.is_attachment

    def get_file_type(self) -> str | None:
        """Get the file type from MIME type or filename."""
        if self.mime_type:
            return self.mime_type
        elif self.original_filename:
            # Extract extension from filename
            import os

            _, ext = os.path.splitext(self.original_filename)
            return ext.lower().lstrip(".") if ext else None
        return None

    def belongs_to_project(self, project_id: str) -> bool:
        """Check if this result belongs to a specific project."""
        return self.project_id == project_id

    def belongs_to_any_project(self, project_ids: list[str]) -> bool:
        """Check if this result belongs to any of the specified projects."""
        return self.project_id is not None and self.project_id in project_ids
