"""Git-specific metadata extractor implementation.

This module provides Git-specific metadata extraction capabilities that extend
the base metadata extraction framework.
"""

import os
import re
from typing import Any

import git

from qdrant_loader.connectors.git.config import GitRepoConfig
from qdrant_loader.connectors.metadata.base import (
    BaseMetadataExtractor,
    MetadataExtractionConfig,
)
from qdrant_loader.connectors.metadata.schemas import (
    AuthorMetadata,
    CrossReferenceMetadata,
    CrossReferenceType,
    GitMetadata,
    RelationshipMetadata,
    RelationshipType,
    TimestampMetadata,
)
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class GitRelationshipExtractor(BaseMetadataExtractor):
    """Git-specific relationship and cross-reference extractor.

    This class focuses on extracting relationship metadata from Git repositories
    including author relationships, file hierarchies, cross-references, and
    Git-specific structural information for knowledge graph enrichment.
    """

    def __init__(self, config: MetadataExtractionConfig, git_config: GitRepoConfig):
        """Initialize the Git metadata extractor.

        Args:
            config: Metadata extraction configuration
            git_config: Git repository configuration
        """
        super().__init__(config)
        self.git_config = git_config
        self._repo = None

    def set_repository(self, repo: git.Repo) -> None:
        """Set the Git repository instance.

        Args:
            repo: Git repository instance
        """
        self._repo = repo

    def _extract_author_metadata(
        self, content: str, context: dict[str, Any]
    ) -> list[dict[str, Any]] | None:
        """Extract author metadata from Git history.

        Args:
            content: File content
            context: Context containing file path and other information

        Returns:
            List of author metadata dictionaries
        """
        if not self._repo:
            return None

        try:
            file_path = context.get("file_path")
            if not file_path:
                return None

            # Get relative path from repository root
            rel_path = os.path.relpath(file_path, self._repo.working_dir)

            # Get commits for this file
            commits = list(self._repo.iter_commits(paths=rel_path, max_count=10))

            authors = []
            seen_authors = set()

            for commit in commits:
                author_key = (commit.author.name, commit.author.email)
                if author_key not in seen_authors:
                    seen_authors.add(author_key)

                    author_metadata = AuthorMetadata(
                        source="git",
                        name=commit.author.name or "Unknown",
                        email=commit.author.email,
                        role="contributor",
                        confidence=0.9,
                    )
                    authors.append(author_metadata.model_dump())

            return authors if authors else None

        except Exception as e:
            self.logger.error(f"Error extracting Git author metadata: {e}")
            return None

    def _extract_timestamp_metadata(
        self, content: str, context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Extract timestamp metadata from Git history.

        Args:
            content: File content
            context: Context containing file path and other information

        Returns:
            Dictionary containing timestamp metadata
        """
        if not self._repo:
            return None

        try:
            file_path = context.get("file_path")
            if not file_path:
                return None

            # Get relative path from repository root
            rel_path = os.path.relpath(file_path, self._repo.working_dir)

            # Get first and last commits for this file
            commits = list(self._repo.iter_commits(paths=rel_path))

            if not commits:
                return None

            # First commit (creation)
            first_commit = commits[-1] if commits else None
            # Last commit (last update)
            last_commit = commits[0] if commits else None

            timestamp_metadata = TimestampMetadata(
                source="git",
                created_at=first_commit.committed_datetime if first_commit else None,
                updated_at=last_commit.committed_datetime if last_commit else None,
                version=last_commit.hexsha[:8] if last_commit else None,
                confidence=0.95,
            )

            return timestamp_metadata.model_dump()

        except Exception as e:
            self.logger.error(f"Error extracting Git timestamp metadata: {e}")
            return None

    def _extract_relationship_metadata(
        self, content: str, context: dict[str, Any]
    ) -> list[dict[str, Any]] | None:
        """Extract relationship metadata from Git repository structure.

        Args:
            content: File content
            context: Context containing file path and other information

        Returns:
            List of relationship metadata dictionaries
        """
        if not self._repo:
            return None

        try:
            file_path = context.get("file_path")
            if not file_path:
                return None

            relationships = []

            # Extract directory hierarchy relationships
            rel_path = os.path.relpath(file_path, self._repo.working_dir)
            dir_path = os.path.dirname(rel_path)

            if dir_path and dir_path != ".":
                # Parent directory relationship
                parent_relationship = RelationshipMetadata(
                    source="git",
                    relationship_type=RelationshipType.PARENT_CHILD,
                    source_entity=dir_path,
                    target_entity=rel_path,
                    source_entity_type="directory",
                    target_entity_type="file",
                    relationship_strength=1.0,
                    bidirectional=False,
                    confidence=1.0,
                )
                relationships.append(parent_relationship.model_dump())

            # Extract sibling file relationships (files in same directory)
            try:
                dir_files = []
                for root, _dirs, files in os.walk(os.path.dirname(file_path)):
                    if root == os.path.dirname(file_path):  # Only immediate directory
                        for file in files:
                            if file != os.path.basename(file_path):
                                sibling_path = os.path.join(root, file)
                                sibling_rel_path = os.path.relpath(
                                    sibling_path, self._repo.working_dir
                                )
                                dir_files.append(sibling_rel_path)
                        break

                # Create sibling relationships for files in same directory
                for sibling_file in dir_files[
                    :5
                ]:  # Limit to avoid too many relationships
                    sibling_relationship = RelationshipMetadata(
                        source="git",
                        relationship_type=RelationshipType.ASSOCIATION,
                        source_entity=rel_path,
                        target_entity=sibling_file,
                        source_entity_type="file",
                        target_entity_type="file",
                        relationship_strength=0.3,
                        bidirectional=True,
                        properties={"relationship_reason": "same_directory"},
                        confidence=0.6,
                    )
                    relationships.append(sibling_relationship.model_dump())

            except Exception as e:
                self.logger.debug(f"Error extracting sibling relationships: {e}")

            return relationships if relationships else None

        except Exception as e:
            self.logger.error(f"Error extracting Git relationship metadata: {e}")
            return None

    def _extract_cross_reference_metadata(
        self, content: str, context: dict[str, Any]
    ) -> list[dict[str, Any]] | None:
        """Extract cross-reference metadata from file content.

        Args:
            content: File content
            context: Context containing file path and other information

        Returns:
            List of cross-reference metadata dictionaries
        """
        try:
            cross_references = []

            # Extract markdown links
            markdown_links = re.findall(r"\[([^\]]*)\]\(([^)]+)\)", content)
            for anchor_text, target in markdown_links:
                cross_ref = CrossReferenceMetadata(
                    source="git",
                    reference_type=CrossReferenceType.LINK,
                    target=target,
                    target_type=(
                        "url" if target.startswith(("http://", "https://")) else "file"
                    ),
                    anchor_text=anchor_text,
                    resolved=False,  # Would need additional logic to resolve
                    confidence=0.8,
                )
                cross_references.append(cross_ref.model_dump())

            # Extract file imports/includes (for code files)
            file_path = context.get("file_path", "")
            if file_path.endswith((".py", ".js", ".ts", ".java", ".cpp", ".c", ".h")):
                # Python imports
                if file_path.endswith(".py"):
                    import_patterns = [
                        r"from\s+([^\s]+)\s+import",
                        r"import\s+([^\s,]+)",
                    ]
                    for pattern in import_patterns:
                        imports = re.findall(pattern, content)
                        for import_target in imports:
                            cross_ref = CrossReferenceMetadata(
                                source="git",
                                reference_type=CrossReferenceType.IMPORT,
                                target=import_target,
                                target_type="module",
                                confidence=0.9,
                            )
                            cross_references.append(cross_ref.model_dump())

                # JavaScript/TypeScript imports
                elif file_path.endswith((".js", ".ts")):
                    import_patterns = [
                        r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]',
                        r'require\([\'"]([^\'"]+)[\'"]\)',
                    ]
                    for pattern in import_patterns:
                        imports = re.findall(pattern, content)
                        for import_target in imports:
                            cross_ref = CrossReferenceMetadata(
                                source="git",
                                reference_type=CrossReferenceType.IMPORT,
                                target=import_target,
                                target_type="module",
                                confidence=0.9,
                            )
                            cross_references.append(cross_ref.model_dump())

            # Extract image references
            image_refs = re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", content)
            for alt_text, image_path in image_refs:
                cross_ref = CrossReferenceMetadata(
                    source="git",
                    reference_type=CrossReferenceType.EMBED,
                    target=image_path,
                    target_type="image",
                    anchor_text=alt_text,
                    confidence=0.9,
                )
                cross_references.append(cross_ref.model_dump())

            return cross_references if cross_references else None

        except Exception as e:
            self.logger.error(f"Error extracting Git cross-reference metadata: {e}")
            return None

    def _extract_source_specific_metadata(
        self, content: str, context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Extract Git-specific metadata.

        Args:
            content: File content
            context: Context containing file path and other information

        Returns:
            Dictionary containing Git-specific metadata
        """
        if not self._repo:
            return None

        try:
            file_path = context.get("file_path")
            if not file_path:
                return None

            # Get relative path from repository root
            rel_path = os.path.relpath(file_path, self._repo.working_dir)

            # Get latest commit for this file
            commits = list(self._repo.iter_commits(paths=rel_path, max_count=1))
            latest_commit = commits[0] if commits else None

            # Extract committer information
            committer_metadata = None
            if latest_commit:
                committer_metadata = AuthorMetadata(
                    source="git",
                    name=latest_commit.committer.name or "Unknown",
                    email=latest_commit.committer.email,
                    role="committer",
                    confidence=0.95,
                )

            git_metadata = GitMetadata(
                source="git",
                commit_hash=latest_commit.hexsha if latest_commit else None,
                branch=(
                    self._repo.active_branch.name if self._repo.active_branch else None
                ),
                repository_url=str(self.git_config.base_url),
                file_path=rel_path,
                commit_message=(
                    str(latest_commit.message).strip()
                    if latest_commit and latest_commit.message
                    else None
                ),
                committer=committer_metadata,
                merge_commit=len(latest_commit.parents) > 1 if latest_commit else False,
                parent_commits=(
                    [p.hexsha for p in latest_commit.parents] if latest_commit else []
                ),
                confidence=0.95,
            )

            return git_metadata.model_dump()

        except Exception as e:
            self.logger.error(f"Error extracting Git-specific metadata: {e}")
            return None

    def extract_repository_metadata(self) -> dict[str, Any]:
        """Extract repository-level metadata.

        Returns:
            Dictionary containing repository metadata
        """
        if not self._repo:
            return {}

        try:
            metadata = {
                "repository_url": str(self.git_config.base_url),
                "branch": (
                    self._repo.active_branch.name if self._repo.active_branch else None
                ),
                "total_commits": len(list(self._repo.iter_commits())),
                "contributors": [],
                "tags": [tag.name for tag in self._repo.tags],
                "branches": [branch.name for branch in self._repo.branches],
            }

            # Get unique contributors
            contributors = {}
            for commit in self._repo.iter_commits(
                max_count=100
            ):  # Limit for performance
                author_key = (commit.author.name, commit.author.email)
                if author_key not in contributors:
                    contributors[author_key] = {
                        "name": commit.author.name,
                        "email": commit.author.email,
                        "first_commit": commit.committed_datetime,
                        "commit_count": 1,
                    }
                else:
                    contributors[author_key]["commit_count"] += 1
                    if (
                        commit.committed_datetime
                        < contributors[author_key]["first_commit"]
                    ):
                        contributors[author_key][
                            "first_commit"
                        ] = commit.committed_datetime

            metadata["contributors"] = list(contributors.values())

            return metadata

        except Exception as e:
            self.logger.error(f"Error extracting repository metadata: {e}")
            return {}
