"""Modular search result data structures for hybrid search."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BaseSearchResult:
    """Core search result fields."""
    score: float
    text: str
    source_type: str
    source_title: str
    source_url: str | None = None
    file_path: str | None = None
    repo_name: str | None = None
    vector_score: float = 0.0
    keyword_score: float = 0.0
    # Document identification
    document_id: str | None = None
    created_at: str | None = None
    last_modified: str | None = None


@dataclass  
class ProjectInfo:
    """Project-related information."""
    project_id: str | None = None
    project_name: str | None = None
    project_description: str | None = None
    collection_name: str | None = None


@dataclass
class HierarchyInfo:
    """Hierarchy information (primarily for Confluence)."""
    parent_id: str | None = None
    parent_title: str | None = None
    breadcrumb_text: str | None = None
    depth: int | None = None
    children_count: int | None = None
    hierarchy_context: str | None = None


@dataclass
class AttachmentInfo:
    """Attachment information for files attached to documents."""
    is_attachment: bool = False
    parent_document_id: str | None = None
    parent_document_title: str | None = None
    attachment_id: str | None = None
    original_filename: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    attachment_author: str | None = None
    attachment_context: str | None = None


@dataclass
class SectionInfo:
    """Section-level intelligence."""
    section_title: str | None = None
    section_type: str | None = None  # e.g., "h1", "h2", "content"
    section_level: int | None = None
    section_anchor: str | None = None
    section_breadcrumb: str | None = None
    section_depth: int | None = None


@dataclass
class ContentAnalysis:
    """Content analysis information."""
    has_code_blocks: bool = False
    has_tables: bool = False
    has_images: bool = False
    has_links: bool = False
    word_count: int | None = None
    char_count: int | None = None
    estimated_read_time: int | None = None  # minutes
    paragraph_count: int | None = None


@dataclass
class SemanticAnalysis:
    """Semantic analysis (NLP results)."""
    entities: list[dict | str] = field(default_factory=list)
    topics: list[dict | str] = field(default_factory=list)
    key_phrases: list[dict | str] = field(default_factory=list)
    pos_tags: list[dict] = field(default_factory=list)


@dataclass
class NavigationContext:
    """Navigation context information."""
    previous_section: str | None = None
    next_section: str | None = None
    sibling_sections: list[str] = field(default_factory=list)
    subsections: list[str] = field(default_factory=list)
    document_hierarchy: list[str] = field(default_factory=list)


@dataclass
class ChunkingContext:
    """Chunking context information."""
    chunk_index: int | None = None
    total_chunks: int | None = None
    chunking_strategy: str | None = None


@dataclass
class ConversionInfo:
    """File conversion intelligence."""
    original_file_type: str | None = None
    conversion_method: str | None = None
    is_excel_sheet: bool = False
    is_converted: bool = False


@dataclass
class CrossReferenceInfo:
    """Cross-references and enhanced context."""
    cross_references: list[dict] = field(default_factory=list)
    topic_analysis: dict | None = None
    content_type_context: str | None = None  # Human-readable content description


@dataclass
class HybridSearchResult:
    """Complete hybrid search result combining all components."""
    
    # Core fields
    base: BaseSearchResult
    
    # Optional components
    project: ProjectInfo | None = None
    hierarchy: HierarchyInfo | None = None
    attachment: AttachmentInfo | None = None
    section: SectionInfo | None = None
    content: ContentAnalysis | None = None
    semantic: SemanticAnalysis | None = None
    navigation: NavigationContext | None = None
    chunking: ChunkingContext | None = None
    conversion: ConversionInfo | None = None
    cross_reference: CrossReferenceInfo | None = None

    # Convenience properties for backward compatibility
    @property
    def score(self) -> float:
        """Get result score."""
        return self.base.score
    
    @property
    def text(self) -> str:
        """Get result text."""
        return self.base.text
    
    @property
    def source_type(self) -> str:
        """Get source type."""
        return self.base.source_type
    
    @property
    def source_title(self) -> str:
        """Get source title."""
        return self.base.source_title
    
    @property
    def source_url(self) -> str | None:
        """Get source URL."""
        return self.base.source_url
    
    @property
    def file_path(self) -> str | None:
        """Get file path."""
        return self.base.file_path
    
    @property
    def repo_name(self) -> str | None:
        """Get repository name."""
        return self.base.repo_name
    
    @property
    def vector_score(self) -> float:
        """Get vector search score."""
        return self.base.vector_score
    
    @property
    def keyword_score(self) -> float:
        """Get keyword search score."""
        return self.base.keyword_score
    
    @property
    def document_id(self) -> str | None:
        """Get document ID."""
        return self.base.document_id
    
    @property
    def created_at(self) -> str | None:
        """Get creation timestamp."""
        return self.base.created_at
    
    @property
    def last_modified(self) -> str | None:
        """Get last modified timestamp."""
        return self.base.last_modified

    # Project info properties
    @property
    def project_id(self) -> str | None:
        """Get project ID."""
        return self.project.project_id if self.project else None
    
    @property
    def project_name(self) -> str | None:
        """Get project name."""
        return self.project.project_name if self.project else None
    
    @property
    def project_description(self) -> str | None:
        """Get project description."""
        return self.project.project_description if self.project else None
    
    @property
    def collection_name(self) -> str | None:
        """Get collection name."""
        return self.project.collection_name if self.project else None

    # Hierarchy info properties
    @property
    def parent_id(self) -> str | None:
        """Get parent ID."""
        return self.hierarchy.parent_id if self.hierarchy else None
    
    @property
    def parent_title(self) -> str | None:
        """Get parent title."""
        return self.hierarchy.parent_title if self.hierarchy else None
    
    @property
    def breadcrumb_text(self) -> str | None:
        """Get breadcrumb text."""
        return self.hierarchy.breadcrumb_text if self.hierarchy else None
    
    @property
    def depth(self) -> int | None:
        """Get depth."""
        return self.hierarchy.depth if self.hierarchy else None
    
    @property
    def children_count(self) -> int | None:
        """Get children count."""
        return self.hierarchy.children_count if self.hierarchy else None
    
    @property
    def hierarchy_context(self) -> str | None:
        """Get hierarchy context."""
        return self.hierarchy.hierarchy_context if self.hierarchy else None

    # Attachment info properties
    @property
    def is_attachment(self) -> bool:
        """Check if this is an attachment."""
        return self.attachment.is_attachment if self.attachment else False
    
    @property
    def parent_document_id(self) -> str | None:
        """Get parent document ID."""
        return self.attachment.parent_document_id if self.attachment else None
    
    @property
    def parent_document_title(self) -> str | None:
        """Get parent document title."""
        return self.attachment.parent_document_title if self.attachment else None
    
    @property
    def attachment_id(self) -> str | None:
        """Get attachment ID."""
        return self.attachment.attachment_id if self.attachment else None
    
    @property
    def original_filename(self) -> str | None:
        """Get original filename."""
        return self.attachment.original_filename if self.attachment else None
    
    @property
    def file_size(self) -> int | None:
        """Get file size."""
        return self.attachment.file_size if self.attachment else None
    
    @property
    def mime_type(self) -> str | None:
        """Get MIME type."""
        return self.attachment.mime_type if self.attachment else None
    
    @property
    def attachment_author(self) -> str | None:
        """Get attachment author."""
        return self.attachment.attachment_author if self.attachment else None
    
    @property
    def attachment_context(self) -> str | None:
        """Get attachment context."""
        return self.attachment.attachment_context if self.attachment else None

    # Section info properties
    @property
    def section_title(self) -> str | None:
        """Get section title."""
        return self.section.section_title if self.section else None
    
    @property
    def section_type(self) -> str | None:
        """Get section type."""
        return self.section.section_type if self.section else None
    
    @property
    def section_level(self) -> int | None:
        """Get section level."""
        return self.section.section_level if self.section else None
    
    @property
    def section_anchor(self) -> str | None:
        """Get section anchor."""
        return self.section.section_anchor if self.section else None
    
    @property
    def section_breadcrumb(self) -> str | None:
        """Get section breadcrumb."""
        return self.section.section_breadcrumb if self.section else None
    
    @property
    def section_depth(self) -> int | None:
        """Get section depth."""
        return self.section.section_depth if self.section else None

    # Content analysis properties
    @property
    def has_code_blocks(self) -> bool:
        """Check if content has code blocks."""
        return self.content.has_code_blocks if self.content else False
    
    @property
    def has_tables(self) -> bool:
        """Check if content has tables."""
        return self.content.has_tables if self.content else False
    
    @property
    def has_images(self) -> bool:
        """Check if content has images."""
        return self.content.has_images if self.content else False
    
    @property
    def has_links(self) -> bool:
        """Check if content has links."""
        return self.content.has_links if self.content else False
    
    @property
    def word_count(self) -> int | None:
        """Get word count."""
        return self.content.word_count if self.content else None
    
    @property
    def char_count(self) -> int | None:
        """Get character count."""
        return self.content.char_count if self.content else None
    
    @property
    def estimated_read_time(self) -> int | None:
        """Get estimated read time."""
        return self.content.estimated_read_time if self.content else None
    
    @property
    def paragraph_count(self) -> int | None:
        """Get paragraph count."""
        return self.content.paragraph_count if self.content else None

    # Semantic analysis properties
    @property
    def entities(self) -> list[dict | str]:
        """Get entities."""
        return self.semantic.entities if self.semantic else []
    
    @property
    def topics(self) -> list[dict | str]:
        """Get topics."""
        return self.semantic.topics if self.semantic else []
    
    @property
    def key_phrases(self) -> list[dict | str]:
        """Get key phrases."""
        return self.semantic.key_phrases if self.semantic else []
    
    @property
    def pos_tags(self) -> list[dict]:
        """Get POS tags."""
        return self.semantic.pos_tags if self.semantic else []

    # Navigation context properties
    @property
    def previous_section(self) -> str | None:
        """Get previous section."""
        return self.navigation.previous_section if self.navigation else None
    
    @property
    def next_section(self) -> str | None:
        """Get next section."""
        return self.navigation.next_section if self.navigation else None
    
    @property
    def sibling_sections(self) -> list[str]:
        """Get sibling sections."""
        return self.navigation.sibling_sections if self.navigation else []
    
    @property
    def subsections(self) -> list[str]:
        """Get subsections."""
        return self.navigation.subsections if self.navigation else []
    
    @property
    def document_hierarchy(self) -> list[str]:
        """Get document hierarchy."""
        return self.navigation.document_hierarchy if self.navigation else []

    # Chunking context properties
    @property
    def chunk_index(self) -> int | None:
        """Get chunk index."""
        return self.chunking.chunk_index if self.chunking else None
    
    @property
    def total_chunks(self) -> int | None:
        """Get total chunks."""
        return self.chunking.total_chunks if self.chunking else None
    
    @property
    def chunking_strategy(self) -> str | None:
        """Get chunking strategy."""
        return self.chunking.chunking_strategy if self.chunking else None

    # Conversion info properties
    @property
    def original_file_type(self) -> str | None:
        """Get original file type."""
        return self.conversion.original_file_type if self.conversion else None
    
    @property
    def conversion_method(self) -> str | None:
        """Get conversion method."""
        return self.conversion.conversion_method if self.conversion else None
    
    @property
    def is_excel_sheet(self) -> bool:
        """Check if this is an Excel sheet."""
        return self.conversion.is_excel_sheet if self.conversion else False
    
    @property
    def is_converted(self) -> bool:
        """Check if this content is converted."""
        return self.conversion.is_converted if self.conversion else False

    # Cross-reference properties
    @property
    def cross_references(self) -> list[dict]:
        """Get cross references."""
        return self.cross_reference.cross_references if self.cross_reference else []
    
    @property
    def topic_analysis(self) -> dict | None:
        """Get topic analysis."""
        return self.cross_reference.topic_analysis if self.cross_reference else None
    
    @property
    def content_type_context(self) -> str | None:
        """Get content type context."""
        return self.cross_reference.content_type_context if self.cross_reference else None

    # Helper methods for display (like SearchResult)
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
        if self.source_type != "confluence":
            return None
            
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
        if not any([self.has_code_blocks, self.has_tables, self.has_images, self.has_links]):
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

    def get_section_context(self) -> str | None:
        """Get section context for enhanced display."""
        if not self.section_title:
            return None
            
        context = self.section_title
        if self.section_type and self.section_level:
            context = f"[{self.section_type.upper()}] {context}"
        if self.section_anchor:
            context += f" (#{self.section_anchor})"
            
        return context

    def get_attachment_info(self) -> str | None:
        """Get formatted attachment information for display."""
        if not self.is_attachment or not self.attachment_context:
            return None
        return self.attachment_context

    def get_file_type(self) -> str | None:
        """Get the file type from MIME type or filename."""
        if self.original_file_type:
            file_type = self.original_file_type
            if self.is_converted and self.conversion_method:
                file_type += f" (converted via {self.conversion_method})"
            return file_type
        elif self.mime_type:
            return self.mime_type
        elif self.original_filename:
            import os
            _, ext = os.path.splitext(self.original_filename)
            return ext.lower().lstrip(".") if ext else None
        return None

    def is_root_document(self) -> bool:
        """Check if this is a root document (no parent)."""
        return self.parent_id is None and self.parent_document_id is None

    def has_children(self) -> bool:
        """Check if this document has children."""
        return (self.children_count is not None and self.children_count > 0) or bool(self.subsections)

    def is_file_attachment(self) -> bool:
        """Check if this is a file attachment."""
        return self.is_attachment

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
        return self.source_type in ["confluence", "localfile"] and not self.has_code_blocks

    def is_structured_data(self) -> bool:
        """Check if this result contains structured data."""
        return self.has_tables or self.is_excel_sheet


def create_hybrid_search_result(
    score: float,
    text: str,
    source_type: str,
    source_title: str,
    vector_score: float = 0.0,
    keyword_score: float = 0.0,
    **kwargs
) -> HybridSearchResult:
    """Factory function to create a HybridSearchResult with optional components.
    
    Args:
        score: Overall search score
        text: Result text content
        source_type: Type of source
        source_title: Title of the source
        vector_score: Vector search score
        keyword_score: Keyword search score
        **kwargs: Additional component fields
        
    Returns:
        HybridSearchResult with appropriate components
    """
    # Create base result
    base = BaseSearchResult(
        score=score,
        text=text,
        source_type=source_type,
        source_title=source_title,
        source_url=kwargs.get("source_url"),
        file_path=kwargs.get("file_path"),
        repo_name=kwargs.get("repo_name"),
        vector_score=vector_score,
        keyword_score=keyword_score,
        document_id=kwargs.get("document_id"),
        created_at=kwargs.get("created_at"),
        last_modified=kwargs.get("last_modified"),
    )
    
    # Create optional components based on provided data
    project = None
    if any(key.startswith("project_") for key in kwargs):
        project = ProjectInfo(
            project_id=kwargs.get("project_id"),
            project_name=kwargs.get("project_name"),
            project_description=kwargs.get("project_description"),
            collection_name=kwargs.get("collection_name"),
        )
    
    hierarchy = None
    hierarchy_fields = ["parent_id", "parent_title", "breadcrumb_text", "depth", "children_count", "hierarchy_context"]
    if any(field in kwargs for field in hierarchy_fields):
        hierarchy = HierarchyInfo(
            parent_id=kwargs.get("parent_id"),
            parent_title=kwargs.get("parent_title"),
            breadcrumb_text=kwargs.get("breadcrumb_text"),
            depth=kwargs.get("depth"),
            children_count=kwargs.get("children_count"),
            hierarchy_context=kwargs.get("hierarchy_context"),
        )
    
    attachment = None
    attachment_fields = ["is_attachment", "parent_document_id", "parent_document_title", "attachment_id", 
                        "original_filename", "file_size", "mime_type", "attachment_author", "attachment_context"]
    if any(field in kwargs for field in attachment_fields):
        attachment = AttachmentInfo(
            is_attachment=kwargs.get("is_attachment", False),
            parent_document_id=kwargs.get("parent_document_id"),
            parent_document_title=kwargs.get("parent_document_title"),
            attachment_id=kwargs.get("attachment_id"),
            original_filename=kwargs.get("original_filename"),
            file_size=kwargs.get("file_size"),
            mime_type=kwargs.get("mime_type"),
            attachment_author=kwargs.get("attachment_author"),
            attachment_context=kwargs.get("attachment_context"),
        )
    
    section = None
    section_fields = ["section_title", "section_type", "section_level", "section_anchor", "section_breadcrumb", "section_depth"]
    if any(field in kwargs for field in section_fields):
        section = SectionInfo(
            section_title=kwargs.get("section_title"),
            section_type=kwargs.get("section_type"),
            section_level=kwargs.get("section_level"),
            section_anchor=kwargs.get("section_anchor"),
            section_breadcrumb=kwargs.get("section_breadcrumb"),
            section_depth=kwargs.get("section_depth"),
        )
    
    content = None
    content_fields = ["has_code_blocks", "has_tables", "has_images", "has_links", "word_count", 
                      "char_count", "estimated_read_time", "paragraph_count"]
    if any(field in kwargs for field in content_fields):
        content = ContentAnalysis(
            has_code_blocks=kwargs.get("has_code_blocks", False),
            has_tables=kwargs.get("has_tables", False),
            has_images=kwargs.get("has_images", False),
            has_links=kwargs.get("has_links", False),
            word_count=kwargs.get("word_count"),
            char_count=kwargs.get("char_count"),
            estimated_read_time=kwargs.get("estimated_read_time"),
            paragraph_count=kwargs.get("paragraph_count"),
        )
    
    semantic = None
    semantic_fields = ["entities", "topics", "key_phrases", "pos_tags"]
    if any(field in kwargs for field in semantic_fields):
        semantic = SemanticAnalysis(
            entities=kwargs.get("entities", []),
            topics=kwargs.get("topics", []),
            key_phrases=kwargs.get("key_phrases", []),
            pos_tags=kwargs.get("pos_tags", []),
        )
    
    navigation = None
    navigation_fields = ["previous_section", "next_section", "sibling_sections", "subsections", "document_hierarchy"]
    if any(field in kwargs for field in navigation_fields):
        navigation = NavigationContext(
            previous_section=kwargs.get("previous_section"),
            next_section=kwargs.get("next_section"),
            sibling_sections=kwargs.get("sibling_sections", []),
            subsections=kwargs.get("subsections", []),
            document_hierarchy=kwargs.get("document_hierarchy", []),
        )
    
    chunking = None
    chunking_fields = ["chunk_index", "total_chunks", "chunking_strategy"]
    if any(field in kwargs for field in chunking_fields):
        chunking = ChunkingContext(
            chunk_index=kwargs.get("chunk_index"),
            total_chunks=kwargs.get("total_chunks"),
            chunking_strategy=kwargs.get("chunking_strategy"),
        )
    
    conversion = None
    conversion_fields = ["original_file_type", "conversion_method", "is_excel_sheet", "is_converted"]
    if any(field in kwargs for field in conversion_fields):
        conversion = ConversionInfo(
            original_file_type=kwargs.get("original_file_type"),
            conversion_method=kwargs.get("conversion_method"),
            is_excel_sheet=kwargs.get("is_excel_sheet", False),
            is_converted=kwargs.get("is_converted", False),
        )
    
    cross_reference = None
    cross_ref_fields = ["cross_references", "topic_analysis", "content_type_context"]
    if any(field in kwargs for field in cross_ref_fields):
        cross_reference = CrossReferenceInfo(
            cross_references=kwargs.get("cross_references", []),
            topic_analysis=kwargs.get("topic_analysis"),
            content_type_context=kwargs.get("content_type_context"),
        )
    
    return HybridSearchResult(
        base=base,
        project=project,
        hierarchy=hierarchy,
        attachment=attachment,
        section=section,
        content=content,
        semantic=semantic,
        navigation=navigation,
        chunking=chunking,
        conversion=conversion,
        cross_reference=cross_reference,
    )