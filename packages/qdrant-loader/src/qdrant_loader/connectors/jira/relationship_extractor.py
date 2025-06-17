"""JIRA-specific metadata extractor implementation.

This module provides JIRA-specific metadata extraction capabilities that extend
the base metadata extraction framework.
"""

import re
from typing import Any

from qdrant_loader.connectors.jira.config import JiraProjectConfig
from qdrant_loader.connectors.metadata.base import (
    BaseMetadataExtractor,
    MetadataExtractionConfig,
)
from qdrant_loader.connectors.metadata.schemas import (
    AuthorMetadata,
    CrossReferenceMetadata,
    CrossReferenceType,
    JiraMetadata,
    RelationshipMetadata,
    RelationshipType,
    TimestampMetadata,
)
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class JiraRelationshipExtractor(BaseMetadataExtractor):
    """JIRA-specific relationship and cross-reference extractor.

    This class focuses on extracting relationship metadata from JIRA issues
    including author relationships, issue hierarchies, cross-references, and
    JIRA-specific structural information for knowledge graph enrichment.
    """

    def __init__(
        self, config: MetadataExtractionConfig, jira_config: JiraProjectConfig
    ):
        """Initialize the JIRA metadata extractor.

        Args:
            config: Metadata extraction configuration
            jira_config: JIRA project configuration
        """
        super().__init__(config)
        self.jira_config = jira_config

    def _extract_author_metadata(
        self, content: str, context: dict[str, Any]
    ) -> list[dict[str, Any]] | None:
        """Extract author metadata from JIRA issue content.

        Args:
            content: Issue content (description + comments)
            context: Context containing issue metadata

        Returns:
            List of author metadata dictionaries
        """
        try:
            authors = []
            seen_authors = set()

            # Extract issue data from context
            issue_data = context.get("issue_data", {})

            # Primary author (reporter)
            reporter = issue_data.get("reporter")
            if reporter and reporter.get("display_name"):
                author_key = (reporter.get("display_name"), reporter.get("account_id"))
                if author_key not in seen_authors:
                    seen_authors.add(author_key)

                    author_metadata = AuthorMetadata(
                        source="jira",
                        name=reporter.get("display_name") or "Unknown",
                        username=reporter.get("account_id"),
                        role="reporter",
                        profile_url=None,  # JIRA doesn't typically expose profile URLs
                        confidence=0.95,
                    )
                    authors.append(author_metadata.model_dump())

            # Assignee
            assignee = issue_data.get("assignee")
            if assignee and assignee.get("display_name"):
                author_key = (assignee.get("display_name"), assignee.get("account_id"))
                if author_key not in seen_authors:
                    seen_authors.add(author_key)

                    author_metadata = AuthorMetadata(
                        source="jira",
                        name=assignee.get("display_name") or "Unknown",
                        username=assignee.get("account_id"),
                        role="assignee",
                        profile_url=None,
                        confidence=0.9,
                    )
                    authors.append(author_metadata.model_dump())

            # Extract authors from comments
            comments = issue_data.get("comments", [])
            for comment in comments:
                comment_author = comment.get("author", {})
                if comment_author and comment_author.get("display_name"):
                    author_key = (
                        comment_author.get("display_name"),
                        comment_author.get("account_id"),
                    )
                    if author_key not in seen_authors:
                        seen_authors.add(author_key)

                        author_metadata = AuthorMetadata(
                            source="jira",
                            name=comment_author.get("display_name") or "Unknown",
                            username=comment_author.get("account_id"),
                            role="commenter",
                            profile_url=None,
                            confidence=0.8,
                        )
                        authors.append(author_metadata.model_dump())

            # Extract authors from attachments
            attachments = issue_data.get("attachments", [])
            for attachment in attachments:
                attachment_author = attachment.get("author", {})
                if attachment_author and attachment_author.get("display_name"):
                    author_key = (
                        attachment_author.get("display_name"),
                        attachment_author.get("account_id"),
                    )
                    if author_key not in seen_authors:
                        seen_authors.add(author_key)

                        author_metadata = AuthorMetadata(
                            source="jira",
                            name=attachment_author.get("display_name") or "Unknown",
                            username=attachment_author.get("account_id"),
                            role="attacher",
                            profile_url=None,
                            confidence=0.8,
                        )
                        authors.append(author_metadata.model_dump())

            return authors if authors else None

        except Exception as e:
            self.logger.error(f"Error extracting JIRA author metadata: {e}")
            return None

    def _extract_timestamp_metadata(
        self, content: str, context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Extract timestamp metadata from JIRA issue content.

        Args:
            content: Issue content
            context: Context containing issue metadata

        Returns:
            Dictionary containing timestamp metadata
        """
        try:
            issue_data = context.get("issue_data", {})

            created_at = None
            updated_at = None
            version = None

            # Extract creation timestamp
            created_str = issue_data.get("created")
            if created_str:
                from datetime import datetime

                try:
                    if isinstance(created_str, datetime):
                        created_at = created_str
                    else:
                        created_at = datetime.fromisoformat(
                            created_str.replace("Z", "+00:00")
                        )
                except (ValueError, AttributeError):
                    pass

            # Extract update timestamp
            updated_str = issue_data.get("updated")
            if updated_str:
                try:
                    if isinstance(updated_str, datetime):
                        updated_at = updated_str
                    else:
                        updated_at = datetime.fromisoformat(
                            updated_str.replace("Z", "+00:00")
                        )
                except (ValueError, AttributeError):
                    pass

            # JIRA doesn't have versions like Confluence, but we can use key as identifier
            version = issue_data.get("key")

            timestamp_metadata = TimestampMetadata(
                source="jira",
                created_at=created_at,
                updated_at=updated_at,
                version=version,
                confidence=0.95,
            )

            return timestamp_metadata.model_dump()

        except Exception as e:
            self.logger.error(f"Error extracting JIRA timestamp metadata: {e}")
            return None

    def _extract_relationship_metadata(
        self, content: str, context: dict[str, Any]
    ) -> list[dict[str, Any]] | None:
        """Extract relationship metadata from JIRA issue hierarchy and links.

        Args:
            content: Issue content
            context: Context containing issue metadata

        Returns:
            List of relationship metadata dictionaries
        """
        try:
            relationships = []
            issue_data = context.get("issue_data", {})
            issue_key = issue_data.get("key")

            if not issue_key:
                return None

            # Project relationship
            project_key = issue_data.get("project_key")
            if project_key:
                project_relationship = RelationshipMetadata(
                    source="jira",
                    relationship_type=RelationshipType.HIERARCHY,
                    source_entity=project_key,
                    target_entity=issue_key,
                    source_entity_type="project",
                    target_entity_type="issue",
                    relationship_strength=1.0,
                    bidirectional=False,
                    properties={"project": project_key},
                    confidence=1.0,
                )
                relationships.append(project_relationship.model_dump())

            # Parent-child relationships (for subtasks)
            parent_key = issue_data.get("parent_key")
            if parent_key:
                parent_relationship = RelationshipMetadata(
                    source="jira",
                    relationship_type=RelationshipType.PARENT_CHILD,
                    source_entity=parent_key,
                    target_entity=issue_key,
                    source_entity_type="issue",
                    target_entity_type="issue",
                    relationship_strength=1.0,
                    bidirectional=False,
                    properties={"relationship_nature": "subtask"},
                    confidence=1.0,
                )
                relationships.append(parent_relationship.model_dump())

            # Child relationships (subtasks)
            subtasks = issue_data.get("subtasks", [])
            for subtask_key in subtasks[: self.config.max_relationships]:
                child_relationship = RelationshipMetadata(
                    source="jira",
                    relationship_type=RelationshipType.PARENT_CHILD,
                    source_entity=issue_key,
                    target_entity=subtask_key,
                    source_entity_type="issue",
                    target_entity_type="issue",
                    relationship_strength=1.0,
                    bidirectional=False,
                    properties={"relationship_nature": "subtask"},
                    confidence=1.0,
                )
                relationships.append(child_relationship.model_dump())

            # Issue links (blocks, relates to, duplicates, etc.)
            linked_issues = issue_data.get("linked_issues", [])
            for linked_issue in linked_issues[: self.config.max_relationships]:
                # linked_issue might be a dict with link type information
                if isinstance(linked_issue, dict):
                    link_type = linked_issue.get("type", "relates")
                    target_key = linked_issue.get("key")
                else:
                    link_type = "relates"
                    target_key = linked_issue

                if target_key:
                    link_relationship = RelationshipMetadata(
                        source="jira",
                        relationship_type=RelationshipType.ASSOCIATION,
                        source_entity=issue_key,
                        target_entity=target_key,
                        source_entity_type="issue",
                        target_entity_type="issue",
                        relationship_strength=0.8,
                        bidirectional=True,
                        properties={"link_type": link_type},
                        confidence=0.9,
                    )
                    relationships.append(link_relationship.model_dump())

            # Component associations
            components = issue_data.get("components", [])
            for component in components[:5]:  # Limit component relationships
                component_name = (
                    component if isinstance(component, str) else component.get("name")
                )
                if component_name:
                    component_relationship = RelationshipMetadata(
                        source="jira",
                        relationship_type=RelationshipType.ASSOCIATION,
                        source_entity=issue_key,
                        target_entity=component_name,
                        source_entity_type="issue",
                        target_entity_type="component",
                        relationship_strength=0.7,
                        bidirectional=False,
                        properties={"component_type": "jira_component"},
                        confidence=0.9,
                    )
                    relationships.append(component_relationship.model_dump())

            # Epic association
            epic_key = issue_data.get("epic_key")
            if epic_key:
                epic_relationship = RelationshipMetadata(
                    source="jira",
                    relationship_type=RelationshipType.HIERARCHY,
                    source_entity=epic_key,
                    target_entity=issue_key,
                    source_entity_type="epic",
                    target_entity_type="issue",
                    relationship_strength=0.9,
                    bidirectional=False,
                    properties={"epic": epic_key},
                    confidence=0.95,
                )
                relationships.append(epic_relationship.model_dump())

            return relationships if relationships else None

        except Exception as e:
            self.logger.error(f"Error extracting JIRA relationship metadata: {e}")
            return None

    def _extract_cross_reference_metadata(
        self, content: str, context: dict[str, Any]
    ) -> list[dict[str, Any]] | None:
        """Extract cross-reference metadata from JIRA issue content.

        Args:
            content: Issue content (description + comments)
            context: Context containing issue metadata

        Returns:
            List of cross-reference metadata dictionaries
        """
        try:
            cross_references = []

            # Extract JIRA issue key references (e.g., ABC-123, XYZ-456)
            issue_key_pattern = r"\b[A-Z][A-Z0-9]+-\d+\b"
            issue_refs = re.findall(issue_key_pattern, content)
            for issue_key in issue_refs:
                cross_ref = CrossReferenceMetadata(
                    source="jira",
                    reference_type=CrossReferenceType.LINK,
                    target=issue_key,
                    target_type="issue",
                    anchor_text=issue_key,
                    confidence=0.95,
                )
                cross_references.append(cross_ref.model_dump())

            # Extract user mentions (e.g., @username, [~accountid])
            user_mention_patterns = [
                r"@(\w+)",  # @username
                r"\[~([^\]]+)\]",  # [~accountid]
            ]
            for pattern in user_mention_patterns:
                mentions = re.findall(pattern, content)
                for mention in mentions:
                    cross_ref = CrossReferenceMetadata(
                        source="jira",
                        reference_type=CrossReferenceType.MENTION,
                        target=mention,
                        target_type="user",
                        anchor_text=f"@{mention}",
                        confidence=0.9,
                    )
                    cross_references.append(cross_ref.model_dump())

            # Extract external links
            url_pattern = r"https?://[^\s\])]+"
            urls = re.findall(url_pattern, content)
            for url in urls:
                cross_ref = CrossReferenceMetadata(
                    source="jira",
                    reference_type=CrossReferenceType.LINK,
                    target=url,
                    target_type="url",
                    confidence=0.8,
                )
                cross_references.append(cross_ref.model_dump())

            # Extract attachments as cross-references
            issue_data = context.get("issue_data", {})
            attachments = issue_data.get("attachments", [])
            for attachment in attachments:
                attachment_name = attachment.get("filename") or attachment.get("id")
                if attachment_name:
                    cross_ref = CrossReferenceMetadata(
                        source="jira",
                        reference_type=CrossReferenceType.ATTACHMENT,
                        target=attachment_name,
                        target_type="attachment",
                        confidence=0.9,
                    )
                    cross_references.append(cross_ref.model_dump())

            # Limit to max_cross_references
            return (
                cross_references[: self.config.max_cross_references]
                if cross_references
                else None
            )

        except Exception as e:
            self.logger.error(f"Error extracting JIRA cross-reference metadata: {e}")
            return None

    def _extract_source_specific_metadata(
        self, content: str, context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Extract JIRA-specific metadata.

        Args:
            content: Issue content
            context: Context containing issue metadata

        Returns:
            Dictionary containing JIRA-specific metadata
        """
        try:
            issue_data = context.get("issue_data", {})

            jira_metadata = JiraMetadata(
                source="jira",
                issue_key=issue_data.get("key"),
                issue_id=issue_data.get("id"),
                project_key=issue_data.get("project_key"),
                issue_type=issue_data.get("issue_type"),
                status=issue_data.get("status"),
                priority=issue_data.get("priority"),
                labels=issue_data.get("labels", []),
                components=[
                    comp if isinstance(comp, str) else comp.get("name", "")
                    for comp in issue_data.get("components", [])
                ],
                epic_key=issue_data.get("epic_key"),
                parent_key=issue_data.get("parent_key"),
                subtasks=issue_data.get("subtasks", []),
                linked_issues=[
                    {
                        "key": link if isinstance(link, str) else link.get("key", ""),
                        "type": (
                            link.get("type", "relates")
                            if isinstance(link, dict)
                            else "relates"
                        ),
                    }
                    for link in issue_data.get("linked_issues", [])
                ],
                fix_versions=issue_data.get("fix_versions", []),
                affects_versions=issue_data.get("affects_versions", []),
                custom_fields=issue_data.get("custom_fields", {}),
                confidence=0.95,
            )

            return jira_metadata.model_dump()

        except Exception as e:
            self.logger.error(f"Error extracting JIRA-specific metadata: {e}")
            return None

    def extract_project_metadata(self, project_data: dict) -> dict[str, Any]:
        """Extract project-level metadata.

        Args:
            project_data: Project information from JIRA API

        Returns:
            Dictionary containing project metadata
        """
        try:
            metadata = {
                "project_key": project_data.get("key"),
                "project_name": project_data.get("name"),
                "project_type": project_data.get("projectTypeKey"),
                "description": project_data.get("description"),
                "lead": project_data.get("lead", {}).get("displayName"),
                "project_category": project_data.get("projectCategory", {}).get("name"),
                "components": [
                    comp.get("name") for comp in project_data.get("components", [])
                ],
                "versions": [
                    ver.get("name") for ver in project_data.get("versions", [])
                ],
            }

            return metadata

        except Exception as e:
            self.logger.error(f"Error extracting project metadata: {e}")
            return {}
