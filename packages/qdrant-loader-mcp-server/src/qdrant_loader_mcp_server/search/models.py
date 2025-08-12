"""Search result models."""

from pydantic import BaseModel


class SearchResult(BaseModel):
    """Search result model with comprehensive metadata."""

    score: float
    text: str
    source_type: str
    source_title: str
    source_url: str | None = None
    file_path: str | None = None
    repo_name: str | None = None

    # Document identification
    document_id: str | None = None
    created_at: str | None = None
    last_modified: str | None = None

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

    # 🔥 NEW: Section-level intelligence
    section_title: str | None = None
    section_type: str | None = None  # e.g., "h1", "h2", "content"
    section_level: int | None = None
    section_anchor: str | None = None
    section_breadcrumb: str | None = None
    section_depth: int | None = None

    # 🔥 NEW: Content analysis
    has_code_blocks: bool = False
    has_tables: bool = False
    has_images: bool = False
    has_links: bool = False
    word_count: int | None = None
    char_count: int | None = None
    estimated_read_time: int | None = None  # minutes
    paragraph_count: int | None = None

    # 🔥 NEW: Semantic analysis (NLP results)
    entities: list[dict | str] = []  # Handle both dict and string formats
    topics: list[dict | str] = []  # Handle both dict and string formats
    key_phrases: list[dict | str] = []
    pos_tags: list[dict] = []

    # 🔥 NEW: Navigation context
    previous_section: str | None = None
    next_section: str | None = None
    sibling_sections: list[str] = []
    subsections: list[str] = []
    document_hierarchy: list[str] = []

    # 🔥 NEW: Chunking context
    chunk_index: int | None = None
    total_chunks: int | None = None
    chunking_strategy: str | None = None

    # 🔥 NEW: File conversion intelligence
    original_file_type: str | None = None
    conversion_method: str | None = None
    is_excel_sheet: bool = False
    is_converted: bool = False

    # 🔥 NEW: Cross-references and enhanced context
    cross_references: list[dict] = []
    topic_analysis: dict | None = None
    content_type_context: str | None = None  # Human-readable content description

    def get_display_title(self) -> str:
        """Get the display title with enhanced hierarchy context."""
        # Use source_title as base, but if empty, derive from other fields
        base_title = self.source_title
        if not base_title or base_title.strip() == "":
            # Try to create title from available data
            if self.file_path:
                import os

                base_title = os.path.basename(self.file_path)
            elif self.repo_name:
                base_title = self.repo_name
            else:
                base_title = "Untitled"

        # 🔥 ENHANCED: Use section breadcrumb for better context
        if self.section_breadcrumb:
            return f"{self.section_title or base_title} ({self.section_breadcrumb})"
        elif self.breadcrumb_text and self.source_type == "confluence":
            return f"{base_title} ({self.breadcrumb_text})"
        elif self.section_title and self.section_title != base_title:
            return f"{base_title} > {self.section_title}"
        return base_title

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
        # Only return hierarchy info for Confluence sources
        if self.source_type != "confluence":
            return None

        # 🔥 ENHANCED: Include section hierarchy
        parts = []

        if self.hierarchy_context:
            parts.append(self.hierarchy_context)

        if self.section_breadcrumb:
            parts.append(f"Section: {self.section_breadcrumb}")

        if self.chunk_index is not None and self.total_chunks is not None:
            parts.append(f"Chunk: {self.chunk_index + 1}/{self.total_chunks}")

        return " | ".join(parts) if parts else None

    def get_content_info(self) -> str | None:
        """Get formatted content analysis information."""
        # 🔥 NEW: Content type summary
        if not any(
            [self.has_code_blocks, self.has_tables, self.has_images, self.has_links]
        ):
            return None

        content_parts = []
        if self.has_code_blocks:
            content_parts.append("Code")
        if self.has_tables:
            content_parts.append("Tables")
        if self.has_images:
            content_parts.append("Images")
        if self.has_links:
            content_parts.append("Links")

        content_info = f"Contains: {', '.join(content_parts)}"

        if self.word_count:
            content_info += f" | {self.word_count} words"
        if self.estimated_read_time:
            content_info += f" | ~{self.estimated_read_time}min read"

        return content_info

    def get_semantic_info(self) -> str | None:
        """Get formatted semantic analysis information."""
        # 🔥 NEW: Semantic analysis summary
        parts = []

        if self.entities:
            entity_count = len(self.entities)
            parts.append(f"{entity_count} entities")

        if self.topics:
            # Handle both string and dict formats for topics
            topic_texts = []
            for topic in self.topics[:3]:
                if isinstance(topic, str):
                    topic_texts.append(topic)
                elif isinstance(topic, dict):
                    topic_texts.append(topic.get("text", str(topic)))
                else:
                    topic_texts.append(str(topic))

            topic_list = ", ".join(topic_texts)
            if len(self.topics) > 3:
                topic_list += f" (+{len(self.topics) - 3} more)"
            parts.append(f"Topics: {topic_list}")

        if self.key_phrases:
            phrase_count = len(self.key_phrases)
            parts.append(f"{phrase_count} key phrases")

        return " | ".join(parts) if parts else None

    def get_navigation_info(self) -> str | None:
        """Get formatted navigation context."""
        # 🔥 NEW: Navigation context
        parts = []

        if self.previous_section:
            parts.append(f"Previous: {self.previous_section}")
        if self.next_section:
            parts.append(f"Next: {self.next_section}")
        if self.sibling_sections:
            sibling_count = len(self.sibling_sections)
            parts.append(f"{sibling_count} siblings")
        if self.subsections:
            subsection_count = len(self.subsections)
            parts.append(f"{subsection_count} subsections")

        return " | ".join(parts) if parts else None

    def is_root_document(self) -> bool:
        """Check if this is a root document (no parent)."""
        return self.parent_id is None and self.parent_document_id is None

    def has_children(self) -> bool:
        """Check if this document has children."""
        return (self.children_count is not None and self.children_count > 0) or bool(
            self.subsections
        )

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
        # 🔥 ENHANCED: Include conversion info
        if self.original_file_type:
            file_type = self.original_file_type
            if self.is_converted and self.conversion_method:
                file_type += f" (converted via {self.conversion_method})"
            return file_type
        elif self.mime_type:
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

    def is_code_content(self) -> bool:
        """Check if this result contains code."""
        return self.has_code_blocks or self.section_type == "code"

    def is_documentation(self) -> bool:
        """Check if this result is documentation content."""
        return (
            self.source_type in ["confluence", "localfile"] and not self.has_code_blocks
        )

    def is_structured_data(self) -> bool:
        """Check if this result contains structured data."""
        return self.has_tables or self.is_excel_sheet

    def get_section_context(self) -> str | None:
        """Get section context for enhanced display."""
        # 🔥 NEW: Rich section context
        if not self.section_title:
            return None

        context = self.section_title
        if self.section_type and self.section_level:
            context = f"[{self.section_type.upper()}] {context}"
        if self.section_anchor:
            context += f" (#{self.section_anchor})"

        return context

    def get_comprehensive_context(self) -> dict[str, str | None]:
        """Get all available context information organized by type."""
        # 🔥 NEW: Comprehensive context for advanced UIs
        return {
            "project": self.get_project_info(),
            "hierarchy": self.get_hierarchy_info(),
            "content": self.get_content_info(),
            "semantic": self.get_semantic_info(),
            "navigation": self.get_navigation_info(),
            "section": self.get_section_context(),
            "attachment": self.get_attachment_info(),
            "file_type": self.get_file_type(),
        }
