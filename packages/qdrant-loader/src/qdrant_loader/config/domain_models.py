"""Domain-specific Pydantic models for three-file configuration system.

This module defines separate Pydantic models for each configuration domain:
- ConnectivityConfig: Database connections, LLM providers, authentication
- ProjectsConfig: Project definitions and data sources
- FineTuningConfig: Processing parameters and performance tuning
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import BaseConfig
from .chunking import ChunkingConfig
from .embedding import EmbeddingConfig
from .graphiti import GraphitiConfig
from .models import ProjectsConfig as BaseProjectsConfig
from .neo4j import Neo4jConfig
from .qdrant import QdrantConfig
from .state import StateManagementConfig
from ..core.file_conversion import FileConversionConfig


class ConnectivityConfig(BaseConfig):
    """Configuration for database connections, LLM providers, and authentication.

    This model validates the connectivity.yaml configuration file.
    """

    # QDrant vector database configuration
    qdrant: QdrantConfig = Field(
        ..., description="QDrant vector database configuration"
    )

    # Embedding service configuration
    embedding: EmbeddingConfig = Field(
        ..., description="Embedding service configuration"
    )

    # Neo4j configuration (optional, for Graphiti features)
    neo4j: Optional[Neo4jConfig] = Field(
        None, description="Neo4j graph database configuration"
    )

    # Graphiti knowledge graph configuration
    graphiti: GraphitiConfig = Field(
        default_factory=GraphitiConfig,
        description="Graphiti knowledge graph configuration",
    )

    # State management configuration
    state_management: StateManagementConfig = Field(
        default_factory=lambda: StateManagementConfig(database_path=":memory:"),
        description="State management configuration",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert connectivity configuration to dictionary."""
        return {
            "qdrant": self.qdrant.to_dict(),
            "embedding": self.embedding.model_dump(),
            "neo4j": self.neo4j.to_dict() if self.neo4j else None,
            "graphiti": self.graphiti.to_dict(),
            "state_management": self.state_management.to_dict(),
        }


class ProjectsConfig(BaseConfig):
    """Configuration for project definitions and data sources.

    This model validates the projects.yaml configuration file.
    """

    # Multi-project configuration
    projects: BaseProjectsConfig = Field(
        default_factory=BaseProjectsConfig, description="Multi-project configurations"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert projects configuration to dictionary."""
        return {"projects": self.projects.to_dict()}


class FineTuningConfig(BaseConfig):
    """Configuration for processing parameters and performance tuning.

    This model validates the fine-tuning.yaml configuration file.
    """

    # Text chunking configuration
    chunking: ChunkingConfig = Field(
        default_factory=ChunkingConfig, description="Text chunking configuration"
    )

    # File conversion configuration
    file_conversion: FileConversionConfig = Field(
        default_factory=FileConversionConfig,
        description="File conversion configuration",
    )

    # Additional fine-tuning parameters can be added here
    # For example: batch processing, concurrency, rate limiting, etc.

    def to_dict(self) -> Dict[str, Any]:
        """Convert fine-tuning configuration to dictionary."""
        return {
            "chunking": {
                "chunk_size": self.chunking.chunk_size,
                "chunk_overlap": self.chunking.chunk_overlap,
            },
            "file_conversion": {
                "max_file_size": self.file_conversion.max_file_size,
                "conversion_timeout": self.file_conversion.conversion_timeout,
                "markitdown": {
                    "enable_llm_descriptions": self.file_conversion.markitdown.enable_llm_descriptions,
                    "llm_model": self.file_conversion.markitdown.llm_model,
                    "llm_endpoint": self.file_conversion.markitdown.llm_endpoint,
                    "llm_api_key": self.file_conversion.markitdown.llm_api_key,
                },
            },
        }


class DomainConfigValidator:
    """Validator for domain-specific configurations."""

    @staticmethod
    def validate_connectivity(data: Dict[str, Any]) -> ConnectivityConfig:
        """Validate connectivity configuration data.

        Args:
            data: Raw configuration data from connectivity.yaml

        Returns:
            Validated ConnectivityConfig instance

        Raises:
            ValidationError: If validation fails
        """
        return ConnectivityConfig(**data)

    @staticmethod
    def validate_projects(data: Dict[str, Any]) -> ProjectsConfig:
        """Validate projects configuration data.

        Args:
            data: Raw configuration data from projects.yaml

        Returns:
            Validated ProjectsConfig instance

        Raises:
            ValidationError: If validation fails
        """
        return ProjectsConfig(**data)

    @staticmethod
    def validate_fine_tuning(data: Dict[str, Any]) -> FineTuningConfig:
        """Validate fine-tuning configuration data.

        Args:
            data: Raw configuration data from fine-tuning.yaml

        Returns:
            Validated FineTuningConfig instance

        Raises:
            ValidationError: If validation fails
        """
        return FineTuningConfig(**data)
