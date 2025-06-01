"""
Project Manager for multi-project support.

This module provides the core project management functionality including:
- Project discovery from configuration
- Project validation and metadata management
- Project context injection and propagation
- Project lifecycle management
"""

import hashlib
from datetime import UTC, datetime
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qdrant_loader.config.models import ProjectConfig, ProjectsConfig
from qdrant_loader.core.state.models import Project, ProjectSource
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class ProjectContext:
    """Context information for a specific project."""

    def __init__(
        self,
        project_id: str,
        display_name: str,
        description: Optional[str] = None,
        collection_name: Optional[str] = None,
        config: Optional[ProjectConfig] = None,
    ):
        self.project_id = project_id
        self.display_name = display_name
        self.description = description
        self.collection_name = collection_name
        self.config = config
        self.created_at = datetime.now(UTC)

    def to_metadata(self) -> Dict[str, str]:
        """Convert project context to metadata dictionary for document injection."""
        metadata = {
            "project_id": self.project_id,
            "project_name": self.display_name,
        }
        if self.description:
            metadata["project_description"] = self.description
        if self.collection_name:
            metadata["collection_name"] = self.collection_name
        return metadata

    def __repr__(self) -> str:
        return f"ProjectContext(id='{self.project_id}', name='{self.display_name}')"


class ProjectManager:
    """Manages projects for multi-project support."""

    def __init__(self, projects_config: ProjectsConfig, global_collection_name: str):
        """Initialize the project manager with configuration."""
        self.projects_config = projects_config
        self.global_collection_name = global_collection_name
        self.logger = LoggingConfig.get_logger(__name__)
        self._project_contexts: Dict[str, ProjectContext] = {}
        self._initialized = False

    async def initialize(self, session: AsyncSession) -> None:
        """Initialize the project manager and discover projects."""
        if self._initialized:
            return

        self.logger.info("Initializing Project Manager")

        # Discover and validate projects from configuration
        await self._discover_projects(session)

        self._initialized = True
        self.logger.info(
            f"Project Manager initialized with {len(self._project_contexts)} projects"
        )

    async def _discover_projects(self, session: AsyncSession) -> None:
        """Discover projects from configuration and create project contexts."""
        self.logger.debug("Discovering projects from configuration")

        for project_id, project_config in self.projects_config.projects.items():
            self.logger.debug(f"Processing project: {project_id}")

            # Validate project configuration
            await self._validate_project_config(project_id, project_config)

            # Determine collection name using the project's method
            collection_name = project_config.get_effective_collection_name(
                self.global_collection_name
            )

            # Create project context
            context = ProjectContext(
                project_id=project_id,
                display_name=project_config.display_name,
                description=project_config.description,
                collection_name=collection_name,
                config=project_config,
            )

            self._project_contexts[project_id] = context

            # Ensure project exists in database
            await self._ensure_project_in_database(session, context, project_config)

            self.logger.info(
                f"Discovered project: {project_id} ({project_config.display_name})"
            )

    async def _validate_project_config(
        self, project_id: str, config: ProjectConfig
    ) -> None:
        """Validate a project configuration."""
        self.logger.debug(f"Validating project configuration for: {project_id}")

        # Check required fields
        if not config.display_name:
            raise ValueError(f"Project '{project_id}' missing required display_name")

        # Validate sources exist - check if any source type has configurations
        has_sources = any(
            [
                bool(config.sources.git),
                bool(config.sources.confluence),
                bool(config.sources.jira),
                bool(config.sources.localfile),
                bool(config.sources.publicdocs),
            ]
        )

        if not has_sources:
            self.logger.warning(f"Project '{project_id}' has no configured sources")

        # Additional validation can be added here
        self.logger.debug(f"Project configuration valid for: {project_id}")

    async def _ensure_project_in_database(
        self, session: AsyncSession, context: ProjectContext, config: ProjectConfig
    ) -> None:
        """Ensure project exists in database with current configuration."""
        self.logger.debug(f"Ensuring project exists in database: {context.project_id}")

        # Check if project exists
        result = await session.execute(select(Project).filter_by(id=context.project_id))
        project = result.scalar_one_or_none()

        # Calculate configuration hash for change detection
        config_hash = self._calculate_config_hash(config)

        now = datetime.now(UTC)

        if project is not None:
            # Update existing project if configuration changed
            current_config_hash = getattr(project, "config_hash", None)
            if current_config_hash != config_hash:
                self.logger.info(
                    f"Updating project configuration: {context.project_id}"
                )
                # Use setattr for SQLAlchemy model attribute assignment
                setattr(project, "display_name", context.display_name)
                setattr(project, "description", context.description)
                setattr(project, "collection_name", context.collection_name)
                setattr(project, "config_hash", config_hash)
                setattr(project, "updated_at", now)
        else:
            # Create new project
            self.logger.info(f"Creating new project: {context.project_id}")
            project = Project(
                id=context.project_id,
                display_name=context.display_name,
                description=context.description,
                collection_name=context.collection_name,
                config_hash=config_hash,
                created_at=now,
                updated_at=now,
            )
            session.add(project)

        # Update project sources
        await self._update_project_sources(session, context.project_id, config)

        await session.commit()

    async def _update_project_sources(
        self, session: AsyncSession, project_id: str, config: ProjectConfig
    ) -> None:
        """Update project sources in database."""
        self.logger.debug(f"Updating project sources for: {project_id}")

        # Get existing sources
        result = await session.execute(
            select(ProjectSource).filter_by(project_id=project_id)
        )
        existing_sources_list = result.scalars().all()
        existing_sources = {
            (source.source_type, source.source_name): source
            for source in existing_sources_list
        }

        # Track current sources from configuration
        current_sources = set()
        now = datetime.now(UTC)

        # Process each source type from SourcesConfig
        source_types = {
            "git": config.sources.git,
            "confluence": config.sources.confluence,
            "jira": config.sources.jira,
            "localfile": config.sources.localfile,
            "publicdocs": config.sources.publicdocs,
        }

        for source_type, sources in source_types.items():
            if not sources:
                continue

            for source_name, source_config in sources.items():
                current_sources.add((source_type, source_name))

                # Calculate source configuration hash
                source_config_hash = self._calculate_source_config_hash(source_config)

                source_key = (source_type, source_name)
                if source_key in existing_sources:
                    # Update existing source if configuration changed
                    source = existing_sources[source_key]
                    current_source_config_hash = getattr(source, "config_hash", None)
                    if current_source_config_hash != source_config_hash:
                        self.logger.debug(
                            f"Updating source configuration: {source_type}:{source_name}"
                        )
                        setattr(source, "config_hash", source_config_hash)
                        setattr(source, "updated_at", now)
                else:
                    # Create new source
                    self.logger.debug(
                        f"Creating new source: {source_type}:{source_name}"
                    )
                    source = ProjectSource(
                        project_id=project_id,
                        source_type=source_type,
                        source_name=source_name,
                        config_hash=source_config_hash,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(source)

        # Remove sources that are no longer in configuration
        for source_key, source in existing_sources.items():
            if source_key not in current_sources:
                source_type, source_name = source_key
                self.logger.info(
                    f"Removing obsolete source: {source_type}:{source_name}"
                )
                await session.delete(source)

    def _calculate_config_hash(self, config: ProjectConfig) -> str:
        """Calculate hash of project configuration for change detection."""
        # Create a stable representation of the configuration
        config_data = {
            "display_name": config.display_name,
            "description": config.description,
            "sources": {
                "git": {
                    name: self._source_config_to_dict(cfg)
                    for name, cfg in config.sources.git.items()
                },
                "confluence": {
                    name: self._source_config_to_dict(cfg)
                    for name, cfg in config.sources.confluence.items()
                },
                "jira": {
                    name: self._source_config_to_dict(cfg)
                    for name, cfg in config.sources.jira.items()
                },
                "localfile": {
                    name: self._source_config_to_dict(cfg)
                    for name, cfg in config.sources.localfile.items()
                },
                "publicdocs": {
                    name: self._source_config_to_dict(cfg)
                    for name, cfg in config.sources.publicdocs.items()
                },
            },
        }

        # Convert to stable string representation and hash
        config_str = str(sorted(config_data.items()))
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]

    def _calculate_source_config_hash(self, source_config) -> str:
        """Calculate hash of source configuration for change detection."""
        config_dict = self._source_config_to_dict(source_config)
        config_str = str(sorted(config_dict.items()))
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]

    def _source_config_to_dict(self, source_config) -> dict:
        """Convert source configuration to dictionary for hashing."""
        if hasattr(source_config, "model_dump"):
            # Pydantic model
            return source_config.model_dump()
        elif hasattr(source_config, "__dict__"):
            # Regular object
            return {
                k: v for k, v in source_config.__dict__.items() if not k.startswith("_")
            }
        else:
            # Fallback to string representation
            return {"config": str(source_config)}

    def get_project_context(self, project_id: str) -> Optional[ProjectContext]:
        """Get project context by ID."""
        return self._project_contexts.get(project_id)

    def get_all_project_contexts(self) -> Dict[str, ProjectContext]:
        """Get all project contexts."""
        return self._project_contexts.copy()

    def list_project_ids(self) -> List[str]:
        """Get list of all project IDs."""
        return list(self._project_contexts.keys())

    def get_project_collection_name(self, project_id: str) -> Optional[str]:
        """Get the collection name for a specific project."""
        context = self._project_contexts.get(project_id)
        return context.collection_name if context else None

    def inject_project_metadata(
        self, project_id: str, metadata: Dict[str, str]
    ) -> Dict[str, str]:
        """Inject project metadata into document metadata."""
        context = self._project_contexts.get(project_id)
        if not context:
            self.logger.warning(f"Project context not found for ID: {project_id}")
            return metadata

        # Create new metadata dict with project information
        enhanced_metadata = metadata.copy()
        enhanced_metadata.update(context.to_metadata())

        return enhanced_metadata

    def validate_project_exists(self, project_id: str) -> bool:
        """Validate that a project exists."""
        return project_id in self._project_contexts

    async def get_project_stats(
        self, session: AsyncSession, project_id: str
    ) -> Optional[Dict]:
        """Get statistics for a specific project."""
        if not self.validate_project_exists(project_id):
            return None

        context = self._project_contexts[project_id]

        # Get project from database with related data
        result = await session.execute(select(Project).filter_by(id=project_id))
        project = result.scalar_one_or_none()

        if not project:
            return None

        # Calculate statistics
        stats = {
            "project_id": project_id,
            "display_name": context.display_name,
            "description": context.description,
            "collection_name": context.collection_name,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "source_count": len(project.sources),
            "document_count": len(project.document_states),
            "ingestion_count": len(project.ingestion_histories),
        }

        return stats

    def __repr__(self) -> str:
        return f"ProjectManager(projects={len(self._project_contexts)})"
