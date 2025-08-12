"""Metadata extraction service for hybrid search results."""

from typing import Any

from ...utils.logging import LoggingConfig
from .search_result_models import (
    AttachmentInfo,
    ChunkingContext,
    ContentAnalysis,
    ConversionInfo,
    CrossReferenceInfo,
    HierarchyInfo,
    NavigationContext,
    ProjectInfo,
    SectionInfo,
    SemanticAnalysis,
)


class MetadataExtractor:
    """Extracts and processes metadata from search results."""

    def __init__(self):
        """Initialize the metadata extractor."""
        self.logger = LoggingConfig.get_logger(__name__)

    def extract_project_info(self, metadata: dict) -> ProjectInfo | None:
        """Extract project information from document metadata.

        Args:
            metadata: Document metadata

        Returns:
            ProjectInfo object or None if no project info available
        """
        project_fields = [
            "project_id",
            "project_name",
            "project_description",
            "collection_name",
        ]

        if not any(metadata.get(field) for field in project_fields):
            return None

        return ProjectInfo(
            project_id=metadata.get("project_id"),
            project_name=metadata.get("project_name"),
            project_description=metadata.get("project_description"),
            collection_name=metadata.get("collection_name"),
        )

    def extract_hierarchy_info(self, metadata: dict) -> HierarchyInfo | None:
        """Extract hierarchy information from document metadata.

        Args:
            metadata: Document metadata

        Returns:
            HierarchyInfo object or None if no hierarchy info available
        """
        hierarchy_fields = ["parent_id", "parent_title", "breadcrumb_text", "depth"]

        if not any(metadata.get(field) for field in hierarchy_fields):
            return None

        # Calculate children count
        children = metadata.get("children", [])
        children_count = len(children) if children else None

        # Generate hierarchy context for display
        hierarchy_context = self._generate_hierarchy_context(metadata, children_count)

        return HierarchyInfo(
            parent_id=metadata.get("parent_id"),
            parent_title=metadata.get("parent_title"),
            breadcrumb_text=metadata.get("breadcrumb_text"),
            depth=metadata.get("depth"),
            children_count=children_count,
            hierarchy_context=hierarchy_context,
        )

    def extract_attachment_info(self, metadata: dict) -> AttachmentInfo | None:
        """Extract attachment information from document metadata.

        Args:
            metadata: Document metadata

        Returns:
            AttachmentInfo object or None if not an attachment
        """
        is_attachment = metadata.get("is_attachment", False)
        attachment_fields = [
            "parent_document_id",
            "parent_document_title",
            "attachment_id",
            "original_filename",
            "file_size",
            "mime_type",
            "attachment_author",
        ]

        if not is_attachment and not any(
            metadata.get(field) for field in attachment_fields
        ):
            return None

        attachment_author = metadata.get("attachment_author") or metadata.get("author")
        attachment_context = (
            self._generate_attachment_context(metadata) if is_attachment else None
        )

        return AttachmentInfo(
            is_attachment=is_attachment,
            parent_document_id=metadata.get("parent_document_id"),
            parent_document_title=metadata.get("parent_document_title"),
            attachment_id=metadata.get("attachment_id"),
            original_filename=metadata.get("original_filename"),
            file_size=metadata.get("file_size"),
            mime_type=metadata.get("mime_type"),
            attachment_author=attachment_author,
            attachment_context=attachment_context,
        )

    def extract_section_info(self, metadata: dict) -> SectionInfo | None:
        """Extract section information from document metadata.

        Args:
            metadata: Document metadata

        Returns:
            SectionInfo object or None if no section info available
        """
        section_fields = [
            "section_title",
            "section_type",
            "section_level",
            "section_anchor",
            "section_breadcrumb",
            "section_depth",
        ]

        if not any(metadata.get(field) for field in section_fields):
            return None

        return SectionInfo(
            section_title=metadata.get("section_title"),
            section_type=metadata.get("section_type"),
            section_level=metadata.get("section_level"),
            section_anchor=metadata.get("section_anchor"),
            section_breadcrumb=metadata.get("section_breadcrumb"),
            section_depth=metadata.get("section_depth"),
        )

    def extract_content_analysis(self, metadata: dict) -> ContentAnalysis | None:
        """Extract content analysis from document metadata.

        Args:
            metadata: Document metadata

        Returns:
            ContentAnalysis object or None if no content analysis available
        """
        content_analysis = metadata.get("content_type_analysis", {})

        content_fields = [
            "has_code_blocks",
            "has_tables",
            "has_images",
            "has_links",
            "word_count",
            "char_count",
            "estimated_read_time",
            "paragraph_count",
        ]

        if not content_analysis and not any(
            metadata.get(field) for field in content_fields
        ):
            return None

        return ContentAnalysis(
            has_code_blocks=content_analysis.get("has_code_blocks", False),
            has_tables=content_analysis.get("has_tables", False),
            has_images=content_analysis.get("has_images", False),
            has_links=content_analysis.get("has_links", False),
            word_count=content_analysis.get("word_count"),
            char_count=content_analysis.get("char_count"),
            estimated_read_time=content_analysis.get("estimated_read_time"),
            paragraph_count=content_analysis.get("paragraph_count"),
        )

    def extract_semantic_analysis(self, metadata: dict) -> SemanticAnalysis | None:
        """Extract semantic analysis from document metadata.

        Args:
            metadata: Document metadata

        Returns:
            SemanticAnalysis object or None if no semantic analysis available
        """
        semantic_fields = ["entities", "topics", "key_phrases", "pos_tags"]

        if not any(metadata.get(field) for field in semantic_fields):
            return None

        # Convert spaCy tuples to expected formats for Pydantic validation
        entities = self._process_entities(metadata.get("entities", []))
        topics = self._process_topics(metadata.get("topics", []))
        key_phrases = self._process_key_phrases(metadata.get("key_phrases", []))
        pos_tags = self._process_pos_tags(metadata.get("pos_tags", []))

        return SemanticAnalysis(
            entities=entities,
            topics=topics,
            key_phrases=key_phrases,
            pos_tags=pos_tags,
        )

    def extract_navigation_context(self, metadata: dict) -> NavigationContext | None:
        """Extract navigation context from document metadata.

        Args:
            metadata: Document metadata

        Returns:
            NavigationContext object or None if no navigation context available
        """
        navigation_fields = [
            "previous_section",
            "next_section",
            "sibling_sections",
            "subsections",
            "document_hierarchy",
        ]

        if not any(metadata.get(field) for field in navigation_fields):
            return None

        return NavigationContext(
            previous_section=metadata.get("previous_section"),
            next_section=metadata.get("next_section"),
            sibling_sections=metadata.get("sibling_sections", []),
            subsections=metadata.get("subsections", []),
            document_hierarchy=metadata.get("document_hierarchy", []),
        )

    def extract_chunking_context(self, metadata: dict) -> ChunkingContext | None:
        """Extract chunking context from document metadata.

        Args:
            metadata: Document metadata

        Returns:
            ChunkingContext object or None if no chunking context available
        """
        chunking_fields = ["chunk_index", "total_chunks", "chunking_strategy"]

        if not any(metadata.get(field) for field in chunking_fields):
            return None

        return ChunkingContext(
            chunk_index=metadata.get("chunk_index"),
            total_chunks=metadata.get("total_chunks"),
            chunking_strategy=metadata.get("chunking_strategy"),
        )

    def extract_conversion_info(self, metadata: dict) -> ConversionInfo | None:
        """Extract conversion information from document metadata.

        Args:
            metadata: Document metadata

        Returns:
            ConversionInfo object or None if no conversion info available
        """
        conversion_fields = [
            "original_file_type",
            "conversion_method",
            "is_excel_sheet",
            "is_converted",
        ]

        if not any(metadata.get(field) for field in conversion_fields):
            return None

        return ConversionInfo(
            original_file_type=metadata.get("original_file_type"),
            conversion_method=metadata.get("conversion_method"),
            is_excel_sheet=metadata.get("is_excel_sheet", False),
            is_converted=metadata.get("is_converted", False),
        )

    def extract_cross_reference_info(self, metadata: dict) -> CrossReferenceInfo | None:
        """Extract cross-reference information from document metadata.

        Args:
            metadata: Document metadata

        Returns:
            CrossReferenceInfo object or None if no cross-reference info available
        """
        cross_ref_fields = ["cross_references", "topic_analysis"]

        if not any(metadata.get(field) for field in cross_ref_fields):
            return None

        # Generate content type context
        content_type_context = self._generate_content_type_context(metadata)

        return CrossReferenceInfo(
            cross_references=metadata.get("cross_references", []),
            topic_analysis=metadata.get("topic_analysis"),
            content_type_context=content_type_context,
        )

    def extract_all_metadata(self, metadata: dict) -> dict[str, Any]:
        """Extract all metadata components from document metadata.

        Args:
            metadata: Document metadata

        Returns:
            Dictionary containing all extracted metadata components
        """
        return {
            "project": self.extract_project_info(metadata),
            "hierarchy": self.extract_hierarchy_info(metadata),
            "attachment": self.extract_attachment_info(metadata),
            "section": self.extract_section_info(metadata),
            "content": self.extract_content_analysis(metadata),
            "semantic": self.extract_semantic_analysis(metadata),
            "navigation": self.extract_navigation_context(metadata),
            "chunking": self.extract_chunking_context(metadata),
            "conversion": self.extract_conversion_info(metadata),
            "cross_reference": self.extract_cross_reference_info(metadata),
        }

    def _generate_hierarchy_context(
        self, metadata: dict, children_count: int | None
    ) -> str | None:
        """Generate hierarchy context for display."""
        if not metadata.get("breadcrumb_text") and metadata.get("depth") is None:
            return None

        context_parts = []

        if metadata.get("breadcrumb_text"):
            context_parts.append(f"Path: {metadata.get('breadcrumb_text')}")

        if metadata.get("depth") is not None:
            context_parts.append(f"Depth: {metadata.get('depth')}")

        if children_count is not None and children_count > 0:
            context_parts.append(f"Children: {children_count}")

        return " | ".join(context_parts) if context_parts else None

    def _generate_attachment_context(self, metadata: dict) -> str | None:
        """Generate attachment context for display."""
        context_parts = []

        if metadata.get("original_filename"):
            context_parts.append(f"File: {metadata.get('original_filename')}")

        if metadata.get("file_size"):
            size_str = self._format_file_size(metadata.get("file_size"))
            context_parts.append(f"Size: {size_str}")

        if metadata.get("mime_type"):
            context_parts.append(f"Type: {metadata.get('mime_type')}")

        attachment_author = metadata.get("attachment_author") or metadata.get("author")
        if attachment_author:
            context_parts.append(f"Author: {attachment_author}")

        return " | ".join(context_parts) if context_parts else None

    def _generate_content_type_context(self, metadata: dict) -> str | None:
        """Generate content type context for display."""
        content_analysis = metadata.get("content_type_analysis", {})
        content_types = []

        if content_analysis.get("has_code_blocks"):
            content_types.append("Code")
        if content_analysis.get("has_tables"):
            content_types.append("Tables")
        if content_analysis.get("has_images"):
            content_types.append("Images")
        if content_analysis.get("has_links"):
            content_types.append("Links")

        if not content_types:
            return None

        content_type_context = f"Contains: {', '.join(content_types)}"

        if content_analysis.get("word_count"):
            content_type_context += f" | {content_analysis.get('word_count')} words"
        if content_analysis.get("estimated_read_time"):
            content_type_context += (
                f" | ~{content_analysis.get('estimated_read_time')}min read"
            )

        return content_type_context

    def _format_file_size(self, size: int) -> str:
        """Format file size in human readable format."""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"

    def _process_entities(self, raw_entities: list) -> list[dict | str]:
        """Process entities from spaCy tuples to expected formats."""
        entities = []
        for entity in raw_entities:
            if isinstance(entity, list | tuple) and len(entity) >= 2:
                entities.append({"text": str(entity[0]), "label": str(entity[1])})
            elif isinstance(entity, str):
                entities.append(entity)
            elif isinstance(entity, dict):
                entities.append(entity)
        return entities

    def _process_topics(self, raw_topics: list) -> list[dict | str]:
        """Process topics from spaCy tuples to expected formats."""
        topics = []
        for topic in raw_topics:
            if isinstance(topic, list | tuple) and len(topic) >= 2:
                score = (
                    float(topic[1])
                    if isinstance(topic[1], int | float)
                    else str(topic[1])
                )
                topics.append({"text": str(topic[0]), "score": score})
            elif isinstance(topic, str):
                topics.append(topic)
            elif isinstance(topic, dict):
                topics.append(topic)
        return topics

    def _process_key_phrases(self, raw_key_phrases: list) -> list[dict | str]:
        """Process key phrases from spaCy tuples to expected formats."""
        key_phrases = []
        for phrase in raw_key_phrases:
            if isinstance(phrase, list | tuple) and len(phrase) >= 2:
                score = (
                    float(phrase[1])
                    if isinstance(phrase[1], int | float)
                    else str(phrase[1])
                )
                key_phrases.append({"text": str(phrase[0]), "score": score})
            elif isinstance(phrase, str):
                key_phrases.append(phrase)
            elif isinstance(phrase, dict):
                key_phrases.append(phrase)
        return key_phrases

    def _process_pos_tags(self, raw_pos_tags: list) -> list[dict]:
        """Process POS tags from spaCy tuples to expected formats."""
        pos_tags = []
        for pos_tag in raw_pos_tags:
            if isinstance(pos_tag, list | tuple) and len(pos_tag) >= 2:
                pos_tags.append({"token": str(pos_tag[0]), "tag": str(pos_tag[1])})
            elif isinstance(pos_tag, dict):
                pos_tags.append(pos_tag)
        return pos_tags
