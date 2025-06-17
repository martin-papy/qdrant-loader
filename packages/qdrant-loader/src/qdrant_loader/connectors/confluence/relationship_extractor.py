"""Confluence-specific metadata extractor implementation.

This module provides Confluence-specific metadata extraction capabilities that extend
the base metadata extraction framework.
"""

import re
from typing import Any

from qdrant_loader.connectors.confluence.config import ConfluenceSpaceConfig
from qdrant_loader.connectors.metadata.base import (
    BaseMetadataExtractor,
    MetadataExtractionConfig,
)
from qdrant_loader.connectors.metadata.schemas import (
    AuthorMetadata,
    ConfluenceMetadata,
    CrossReferenceMetadata,
    CrossReferenceType,
    RelationshipMetadata,
    RelationshipType,
    TimestampMetadata,
)
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class ConfluenceRelationshipExtractor(BaseMetadataExtractor):
    """Confluence-specific relationship and cross-reference extractor.

    This class focuses on extracting relationship metadata from Confluence pages
    including author relationships, page hierarchies, cross-references, and
    Confluence-specific structural information for knowledge graph enrichment.
    """

    def __init__(
        self, config: MetadataExtractionConfig, confluence_config: ConfluenceSpaceConfig
    ):
        """Initialize the Confluence metadata extractor.

        Args:
            config: Metadata extraction configuration
            confluence_config: Confluence space configuration
        """
        super().__init__(config)
        self.confluence_config = confluence_config

    def _extract_author_metadata(
        self, content: str, context: dict[str, Any]
    ) -> list[dict[str, Any]] | None:
        """Extract author metadata from Confluence content.

        Args:
            content: Page content
            context: Context containing page metadata

        Returns:
            List of author metadata dictionaries
        """
        try:
            authors = []
            seen_authors = set()

            # Extract page author from context
            page_data = context.get("page_data", {})

            # Primary author (creator)
            creator = page_data.get("history", {}).get("createdBy", {})
            if creator and creator.get("displayName"):
                author_key = (creator.get("displayName"), creator.get("userKey"))
                if author_key not in seen_authors:
                    seen_authors.add(author_key)

                    author_metadata = AuthorMetadata(
                        source="confluence",
                        name=creator.get("displayName") or "Unknown",
                        username=creator.get("userKey"),
                        role="creator",
                        profile_url=creator.get("profilePicture", {}).get("path"),
                        confidence=0.95,
                    )
                    authors.append(author_metadata.model_dump())

            # Last modifier
            last_modifier = page_data.get("version", {}).get("by", {})
            if last_modifier and last_modifier.get("displayName"):
                author_key = (
                    last_modifier.get("displayName"),
                    last_modifier.get("userKey"),
                )
                if author_key not in seen_authors:
                    seen_authors.add(author_key)

                    author_metadata = AuthorMetadata(
                        source="confluence",
                        name=last_modifier.get("displayName") or "Unknown",
                        username=last_modifier.get("userKey"),
                        role="editor",
                        profile_url=last_modifier.get("profilePicture", {}).get("path"),
                        confidence=0.9,
                    )
                    authors.append(author_metadata.model_dump())

            # Extract authors from comments
            comments = (
                page_data.get("children", {}).get("comment", {}).get("results", [])
            )
            for comment in comments:
                comment_author = comment.get("history", {}).get("createdBy", {})
                if comment_author and comment_author.get("displayName"):
                    author_key = (
                        comment_author.get("displayName"),
                        comment_author.get("userKey"),
                    )
                    if author_key not in seen_authors:
                        seen_authors.add(author_key)

                        author_metadata = AuthorMetadata(
                            source="confluence",
                            name=comment_author.get("displayName") or "Unknown",
                            username=comment_author.get("userKey"),
                            role="commenter",
                            profile_url=comment_author.get("profilePicture", {}).get(
                                "path"
                            ),
                            confidence=0.8,
                        )
                        authors.append(author_metadata.model_dump())

            return authors if authors else None

        except Exception as e:
            self.logger.error(f"Error extracting Confluence author metadata: {e}")
            return None

    def _extract_timestamp_metadata(
        self, content: str, context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Extract timestamp metadata from Confluence content.

        Args:
            content: Page content
            context: Context containing page metadata

        Returns:
            Dictionary containing timestamp metadata
        """
        try:
            page_data = context.get("page_data", {})

            created_at = None
            updated_at = None
            version = None

            # Extract creation timestamp
            if "history" in page_data:
                created_at_str = page_data["history"].get("createdDate") or page_data[
                    "history"
                ].get("createdAt")
                if created_at_str:
                    from datetime import datetime

                    try:
                        created_at = datetime.fromisoformat(
                            created_at_str.replace("Z", "+00:00")
                        )
                    except ValueError:
                        # Handle different timestamp formats
                        pass

            # Extract update timestamp and version
            if "version" in page_data:
                version_data = page_data["version"]
                version = str(version_data.get("number", "1"))

                updated_at_str = version_data.get("when") or version_data.get(
                    "friendlyWhen"
                )
                if updated_at_str:
                    try:
                        updated_at = datetime.fromisoformat(
                            updated_at_str.replace("Z", "+00:00")
                        )
                    except ValueError:
                        # Handle different timestamp formats
                        pass

            timestamp_metadata = TimestampMetadata(
                source="confluence",
                created_at=created_at,
                updated_at=updated_at,
                version=version,
                confidence=0.95,
            )

            return timestamp_metadata.model_dump()

        except Exception as e:
            self.logger.error(f"Error extracting Confluence timestamp metadata: {e}")
            return None

    def _extract_relationship_metadata(
        self, content: str, context: dict[str, Any]
    ) -> list[dict[str, Any]] | None:
        """Extract relationship metadata from Confluence page hierarchy.

        Args:
            content: Page content
            context: Context containing page metadata

        Returns:
            List of relationship metadata dictionaries
        """
        try:
            relationships = []
            page_data = context.get("page_data", {})
            page_id = page_data.get("id")

            if not page_id:
                return None

            # Extract parent-child relationships from hierarchy
            hierarchy_info = context.get("hierarchy_info", {})

            # Parent relationship
            parent_id = hierarchy_info.get("parent_id")
            if parent_id:
                parent_relationship = RelationshipMetadata(
                    source="confluence",
                    relationship_type=RelationshipType.PARENT_CHILD,
                    source_entity=parent_id,
                    target_entity=page_id,
                    source_entity_type="page",
                    target_entity_type="page",
                    relationship_strength=1.0,
                    bidirectional=False,
                    properties={"parent_title": hierarchy_info.get("parent_title")},
                    confidence=1.0,
                )
                relationships.append(parent_relationship.model_dump())

            # Child relationships
            children = hierarchy_info.get("children", [])
            for child in children[: self.config.max_relationships]:
                child_relationship = RelationshipMetadata(
                    source="confluence",
                    relationship_type=RelationshipType.PARENT_CHILD,
                    source_entity=page_id,
                    target_entity=child.get("id"),
                    source_entity_type="page",
                    target_entity_type="page",
                    relationship_strength=1.0,
                    bidirectional=False,
                    properties={"child_title": child.get("title")},
                    confidence=1.0,
                )
                relationships.append(child_relationship.model_dump())

            # Space relationship
            space_key = page_data.get("space", {}).get("key")
            if space_key:
                space_relationship = RelationshipMetadata(
                    source="confluence",
                    relationship_type=RelationshipType.HIERARCHY,
                    source_entity=space_key,
                    target_entity=page_id,
                    source_entity_type="space",
                    target_entity_type="page",
                    relationship_strength=1.0,
                    bidirectional=False,
                    properties={"space_name": page_data.get("space", {}).get("name")},
                    confidence=1.0,
                )
                relationships.append(space_relationship.model_dump())

            # Label associations
            labels = page_data.get("metadata", {}).get("labels", {}).get("results", [])
            for label in labels[:5]:  # Limit label relationships
                label_relationship = RelationshipMetadata(
                    source="confluence",
                    relationship_type=RelationshipType.ASSOCIATION,
                    source_entity=page_id,
                    target_entity=label.get("name"),
                    source_entity_type="page",
                    target_entity_type="label",
                    relationship_strength=0.7,
                    bidirectional=False,
                    properties={"label_type": "confluence_label"},
                    confidence=0.9,
                )
                relationships.append(label_relationship.model_dump())

            return relationships if relationships else None

        except Exception as e:
            self.logger.error(f"Error extracting Confluence relationship metadata: {e}")
            return None

    def _extract_cross_reference_metadata(
        self, content: str, context: dict[str, Any]
    ) -> list[dict[str, Any]] | None:
        """Extract cross-reference metadata from Confluence page content.

        Args:
            content: Page content (HTML)
            context: Context containing page metadata

        Returns:
            List of cross-reference metadata dictionaries
        """
        try:
            cross_references = []

            # Extract Confluence-specific page links
            # Pattern for internal page links: [Page Title|confluence:page-id]
            confluence_links = re.findall(r"\[([^\]]*)\|confluence:([^\]]+)\]", content)
            for link_text, page_id in confluence_links:
                cross_ref = CrossReferenceMetadata(
                    source="confluence",
                    reference_type=CrossReferenceType.LINK,
                    target=page_id,
                    target_type="page",
                    anchor_text=link_text.strip(),
                    confidence=0.95,
                )
                cross_references.append(cross_ref.model_dump())

            # Extract @ mentions
            mentions = re.findall(r"@\[([^\]]+)\]", content)
            for mention in mentions:
                cross_ref = CrossReferenceMetadata(
                    source="confluence",
                    reference_type=CrossReferenceType.MENTION,
                    target=mention,
                    target_type="user",
                    anchor_text=f"@{mention}",
                    confidence=0.9,
                )
                cross_references.append(cross_ref.model_dump())

            # Extract attachment references
            attachment_refs = re.findall(r'attachment:([^"\s>]+)', content)
            for attachment in attachment_refs:
                cross_ref = CrossReferenceMetadata(
                    source="confluence",
                    reference_type=CrossReferenceType.ATTACHMENT,
                    target=attachment,
                    target_type="attachment",
                    confidence=0.9,
                )
                cross_references.append(cross_ref.model_dump())

            # Extract macro references
            macro_refs = re.findall(
                r'<ac:structured-macro[^>]*ac:name="([^"]+)"', content
            )
            for macro_name in macro_refs:
                cross_ref = CrossReferenceMetadata(
                    source="confluence",
                    reference_type=CrossReferenceType.EMBED,
                    target=macro_name,
                    target_type="macro",
                    confidence=0.8,
                )
                cross_references.append(cross_ref.model_dump())

            # Extract external links
            external_links = re.findall(
                r'href="(https?://[^"]+)"[^>]*>([^<]*)', content
            )
            for url, link_text in external_links:
                cross_ref = CrossReferenceMetadata(
                    source="confluence",
                    reference_type=CrossReferenceType.LINK,
                    target=url,
                    target_type="url",
                    anchor_text=link_text.strip(),
                    confidence=0.8,
                )
                cross_references.append(cross_ref.model_dump())

            # Limit to max_cross_references
            return (
                cross_references[: self.config.max_cross_references]
                if cross_references
                else None
            )

        except Exception as e:
            self.logger.error(
                f"Error extracting Confluence cross-reference metadata: {e}"
            )
            return None

    def _extract_source_specific_metadata(
        self, content: str, context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Extract Confluence-specific metadata.

        Args:
            content: Page content
            context: Context containing page metadata

        Returns:
            Dictionary containing Confluence-specific metadata
        """
        try:
            page_data = context.get("page_data", {})
            hierarchy_info = context.get("hierarchy_info", {})

            # Extract author information for metadata
            creator = page_data.get("history", {}).get("createdBy", {})
            creator_metadata = None
            if creator and creator.get("displayName"):
                creator_metadata = AuthorMetadata(
                    source="confluence",
                    name=creator.get("displayName") or "Unknown",
                    username=creator.get("userKey"),
                    role="creator",
                    profile_url=creator.get("profilePicture", {}).get("path"),
                    confidence=0.95,
                )

            last_modifier = page_data.get("version", {}).get("by", {})
            last_modifier_metadata = None
            if last_modifier and last_modifier.get("displayName"):
                last_modifier_metadata = AuthorMetadata(
                    source="confluence",
                    name=last_modifier.get("displayName") or "Unknown",
                    username=last_modifier.get("userKey"),
                    role="editor",
                    profile_url=last_modifier.get("profilePicture", {}).get("path"),
                    confidence=0.9,
                )

            confluence_metadata = ConfluenceMetadata(
                source="confluence",
                page_id=page_data.get("id"),
                space_key=page_data.get("space", {}).get("key"),
                space_name=page_data.get("space", {}).get("name"),
                parent_page_id=hierarchy_info.get("parent_id"),
                page_version=page_data.get("version", {}).get("number"),
                content_type=page_data.get("type", "page"),
                labels=[
                    label["name"]
                    for label in page_data.get("metadata", {})
                    .get("labels", {})
                    .get("results", [])
                ],
                restrictions=page_data.get("restrictions", {}),
                attachments=[
                    attachment.get("id")
                    for attachment in page_data.get("children", {})
                    .get("attachment", {})
                    .get("results", [])
                ],
                confidence=0.95,
            )

            return confluence_metadata.model_dump()

        except Exception as e:
            self.logger.error(f"Error extracting Confluence-specific metadata: {e}")
            return None

    def extract_space_metadata(self, space_data: dict) -> dict[str, Any]:
        """Extract space-level metadata.

        Args:
            space_data: Space information from Confluence API

        Returns:
            Dictionary containing space metadata
        """
        try:
            metadata = {
                "space_key": space_data.get("key"),
                "space_name": space_data.get("name"),
                "space_type": space_data.get("type"),
                "description": space_data.get("description", {})
                .get("plain", {})
                .get("value"),
                "homepage_id": space_data.get("homepage", {}).get("id"),
                "permissions": space_data.get("permissions", []),
            }

            return metadata

        except Exception as e:
            self.logger.error(f"Error extracting space metadata: {e}")
            return {}
