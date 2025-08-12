"""Configuration models for multi-project support.

This module defines the data structures used for multi-project configuration,
including project contexts, project configurations, and related models.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from .sources import SourcesConfig


@dataclass
class ProjectContext:
    """Project context information passed through the pipeline."""

    project_id: str
    display_name: str
    description: str | None
    collection_name: str
    config_overrides: dict[str, Any]

    def __post_init__(self):
        """Validate project context after initialization."""
        if not self.project_id:
            raise ValueError("project_id cannot be empty")
        if not self.display_name:
            raise ValueError("display_name cannot be empty")
        if not self.collection_name:
            raise ValueError("collection_name cannot be empty")


class ProjectConfig(BaseModel):
    """Configuration for a single project."""

    project_id: str = Field(..., description="Unique project identifier")
    display_name: str = Field(..., description="Human-readable project name")
    description: str | None = Field(None, description="Project description")
    sources: SourcesConfig = Field(
        default_factory=SourcesConfig, description="Project-specific sources"
    )
    overrides: dict[str, Any] = Field(
        default_factory=dict, description="Project-specific configuration overrides"
    )

    def get_effective_collection_name(self, global_collection_name: str) -> str:
        """Get the effective collection name for this project.

        Args:
            global_collection_name: The global collection name from configuration

        Returns:
            The collection name to use for this project (always the global collection name)
        """
        # Always use the global collection name for all projects
        return global_collection_name


class ProjectsConfig(BaseModel):
    """Configuration for multiple projects."""

    projects: dict[str, ProjectConfig] = Field(
        default_factory=dict, description="Project configurations"
    )

    def get_project(self, project_id: str) -> ProjectConfig | None:
        """Get a project configuration by ID.

        Args:
            project_id: The project identifier

        Returns:
            The project configuration if found, None otherwise
        """
        return self.projects.get(project_id)

    def list_project_ids(self) -> list[str]:
        """Get a list of all project IDs.

        Returns:
            List of project identifiers
        """
        return list(self.projects.keys())

    def add_project(self, project_config: ProjectConfig) -> None:
        """Add a project configuration.

        Args:
            project_config: The project configuration to add

        Raises:
            ValueError: If project ID already exists
        """
        if project_config.project_id in self.projects:
            raise ValueError(f"Project '{project_config.project_id}' already exists")

        self.projects[project_config.project_id] = project_config

    def to_dict(self) -> dict[str, Any]:
        """Convert the projects configuration to a dictionary.

        Returns:
            Dict[str, Any]: Projects configuration as a dictionary
        """
        return {
            project_id: project_config.model_dump()
            for project_id, project_config in self.projects.items()
        }


@dataclass
class ParsedConfig:
    """Result of parsing a configuration file."""

    global_config: Any  # Will be GlobalConfig, but avoiding circular import
    projects_config: ProjectsConfig

    def get_all_projects(self) -> list[ProjectConfig]:
        """Get all project configurations.

        Returns:
            List of all project configurations
        """
        return list(self.projects_config.projects.values())


class ProjectStats(BaseModel):
    """Statistics for a project."""

    project_id: str = Field(..., description="Project identifier")
    document_count: int = Field(default=0, description="Number of documents in project")
    source_count: int = Field(default=0, description="Number of sources in project")
    last_updated: datetime | None = Field(None, description="Last update timestamp")
    storage_size: int | None = Field(None, description="Storage size in bytes")

    model_config = ConfigDict()

    @field_serializer("last_updated")
    def serialize_last_updated(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class ProjectInfo(BaseModel):
    """Detailed information about a project."""

    id: str = Field(..., description="Project identifier")
    display_name: str = Field(..., description="Project display name")
    description: str | None = Field(None, description="Project description")
    collection_name: str = Field(..., description="QDrant collection name")
    source_count: int = Field(default=0, description="Number of sources")
    document_count: int = Field(default=0, description="Number of documents")
    last_updated: datetime | None = Field(None, description="Last update timestamp")

    model_config = ConfigDict()

    @field_serializer("last_updated")
    def serialize_last_updated(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class ProjectDetail(ProjectInfo):
    """Detailed project information including sources and statistics."""

    sources: list[dict[str, Any]] = Field(
        default_factory=list, description="Source information"
    )
    statistics: dict[str, Any] = Field(
        default_factory=dict, description="Project statistics"
    )
