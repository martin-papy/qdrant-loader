"""Domain-specific Pydantic models for three-file configuration system.

This module defines separate Pydantic models for each configuration domain:
- ConnectivityConfig: Database connections, LLM providers, authentication
- ProjectsConfig: Project definitions and data sources
- FineTuningConfig: Processing parameters and performance tuning
"""

from typing import Any

from pydantic import BaseModel, Field

from ..core.file_conversion import FileConversionConfig
from .base import BaseConfig
from .chunking import ChunkingConfig
from .embedding import EmbeddingConfig
from .graphiti import GraphitiConfig
from .models import ProjectsConfig as BaseProjectsConfig
from .neo4j import Neo4jConfig
from .qdrant import QdrantConfig
from .state import StateManagementConfig


class NetworkConfig(BaseModel):
    """Network and timeout configuration."""

    # Request timing settings
    min_request_interval: float = Field(
        default=0.5, description="Minimum interval between API requests (seconds)"
    )
    base_retry_delay: float = Field(
        default=1.0, description="Base delay for exponential backoff retries (seconds)"
    )
    max_retry_delay: float = Field(
        default=30.0,
        description="Maximum delay for exponential backoff retries (seconds)",
    )
    max_retries: int = Field(default=3, description="Maximum number of retry attempts")

    # HTTP timeout settings
    http_timeout: int = Field(default=60, description="HTTP request timeout (seconds)")
    download_timeout: int = Field(
        default=30, description="File download timeout (seconds)"
    )

    # File size limits
    max_attachment_size: int = Field(
        default=52428800,
        description="Maximum attachment size to download (bytes, default 50MB)",
    )


class ServerConfig(BaseModel):
    """Server configuration for various services."""

    # MCP server settings
    mcp_server_port: int = Field(default=8000, description="MCP server port")

    # Metrics server settings
    prometheus_metrics_port: int = Field(
        default=8001, description="Prometheus metrics server port"
    )

    # External API endpoints
    pypi_api_url: str = Field(
        default="https://pypi.org/pypi/qdrant-loader/json",
        description="PyPI API endpoint for version checking",
    )


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
    neo4j: Neo4jConfig | None = Field(
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

    # Network and timeout configuration
    network: NetworkConfig = Field(
        default_factory=NetworkConfig, description="Network and timeout configuration"
    )

    # Server configuration
    server: ServerConfig = Field(
        default_factory=ServerConfig, description="Server configuration"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert connectivity configuration to dictionary.

        Returns the configuration wrapped under 'global' key to match
        the expected structure for the parser.
        """
        return {
            "global": {
                "qdrant": self.qdrant.to_dict(),
                "embedding": self.embedding.model_dump(),
                "neo4j": self.neo4j.to_dict() if self.neo4j else None,
                "graphiti": self.graphiti.to_dict(),
                "state_management": self.state_management.to_dict(),
                "network": self.network.model_dump(),
                "server": self.server.model_dump(),
            }
        }


class PipelineConfig(BaseModel):
    """Pipeline configuration and processing limits."""

    # Processing limits
    max_concurrent_files: int = Field(
        default=10, description="Maximum number of files to process concurrently"
    )
    max_workers: int = Field(default=4, description="Maximum number of worker threads")
    batch_size: int = Field(
        default=100, description="Batch size for processing operations"
    )

    # Timeouts
    processing_timeout: float = Field(
        default=300.0, description="Processing timeout in seconds"
    )
    file_timeout: float = Field(
        default=60.0, description="Individual file processing timeout"
    )

    # Queue settings
    queue_max_size: int = Field(
        default=1000, description="Maximum items in processing queue"
    )

    # Progress reporting
    progress_interval: float = Field(
        default=5.0, description="Progress reporting interval in seconds"
    )


class SearchConfig(BaseModel):
    """Search configuration and limits."""

    # Search limits
    max_results: int = Field(
        default=100, description="Maximum number of search results"
    )
    default_limit: int = Field(default=10, description="Default search result limit")

    # Search parameters
    similarity_threshold: float = Field(
        default=0.7, description="Minimum similarity threshold for results"
    )

    # Query processing
    max_query_length: int = Field(
        default=1000, description="Maximum query length in characters"
    )

    # Timeout settings
    search_timeout: float = Field(
        default=30.0, description="Search operation timeout in seconds"
    )


class CacheConfig(BaseModel):
    """Cache configuration and durations."""

    # Cache durations (in seconds)
    embedding_cache_ttl: int = Field(
        default=3600, description="Embedding cache TTL in seconds"
    )
    metadata_cache_ttl: int = Field(
        default=1800, description="Metadata cache TTL in seconds"
    )
    search_cache_ttl: int = Field(
        default=300, description="Search results cache TTL in seconds"
    )

    # Cache sizes
    max_cache_size: int = Field(
        default=1000, description="Maximum number of items in cache"
    )

    # Cache cleanup
    cleanup_interval: int = Field(
        default=300, description="Cache cleanup interval in seconds"
    )


class WorkerConfig(BaseModel):
    """Worker configuration and limits."""

    # Worker pool settings
    min_workers: int = Field(default=1, description="Minimum number of worker threads")
    max_workers: int = Field(default=10, description="Maximum number of worker threads")

    # Task settings
    max_tasks_per_worker: int = Field(
        default=100, description="Maximum tasks per worker before restart"
    )
    worker_timeout: float = Field(
        default=300.0, description="Worker task timeout in seconds"
    )

    # Queue settings
    task_queue_size: int = Field(
        default=1000, description="Maximum tasks in worker queue"
    )

    # Health monitoring
    health_check_interval: float = Field(
        default=30.0, description="Worker health check interval in seconds"
    )


class ProjectsConfig(BaseConfig):
    """Configuration for project definitions and management.

    This model validates the projects.yaml configuration file.
    """

    projects: BaseProjectsConfig = Field(
        default_factory=BaseProjectsConfig, description="Project definitions"
    )

    # Pipeline configuration
    pipeline: PipelineConfig = Field(
        default_factory=PipelineConfig,
        description="Pipeline configuration and processing limits",
    )

    # Search configuration
    search: SearchConfig = Field(
        default_factory=SearchConfig, description="Search configuration and limits"
    )

    # Cache configuration
    cache: CacheConfig = Field(
        default_factory=CacheConfig, description="Cache configuration and durations"
    )

    # Worker configuration
    workers: WorkerConfig = Field(
        default_factory=WorkerConfig, description="Worker configuration and limits"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert projects configuration to dictionary."""
        return {
            "projects": self.projects.to_dict(),
            "pipeline": self.pipeline.model_dump(),
            "search": self.search.model_dump(),
            "cache": self.cache.model_dump(),
            "workers": self.workers.model_dump(),
        }


class TextProcessingConfig(BaseModel):
    """Text processing limits and parameters."""

    # spaCy processing limits
    max_text_length_for_spacy: int = Field(
        default=100_000,
        description="Maximum text length for spaCy processing (characters)",
    )
    max_entities_to_extract: int = Field(
        default=50, description="Maximum number of entities to extract"
    )
    max_pos_tags_to_extract: int = Field(
        default=200, description="Maximum number of POS tags to extract"
    )


class ChunkingLimitsConfig(BaseModel):
    """Chunking strategy limits and parameters."""

    # General chunking limits
    max_chunks_to_process: int = Field(
        default=1000, description="Maximum number of chunks to process"
    )

    # Markdown strategy limits
    min_section_size: int = Field(
        default=500, description="Minimum characters for a standalone section"
    )
    max_chunks_per_section: int = Field(
        default=100, description="Maximum chunks per section"
    )
    max_chunks_per_document: int = Field(
        default=500, description="Maximum chunks per document"
    )

    # Code strategy limits
    max_elements_to_process: int = Field(
        default=800, description="Maximum number of code elements to process"
    )
    chunk_size_threshold: int = Field(
        default=40_000, description="Files larger than this use simple chunking"
    )
    max_element_size: int = Field(
        default=20_000, description="Skip individual elements larger than this"
    )

    # HTML strategy limits
    max_html_size_for_parsing: int = Field(
        default=500_000, description="Maximum HTML size for complex parsing (bytes)"
    )
    max_sections_to_process: int = Field(
        default=200, description="Maximum number of sections to process"
    )
    max_chunk_size_for_nlp: int = Field(
        default=20_000, description="Maximum chunk size for NLP processing"
    )
    simple_parsing_threshold: int = Field(
        default=100_000, description="Use simple parsing for files larger than this"
    )

    # JSON strategy limits
    max_objects_to_process: int = Field(
        default=200, description="Maximum number of JSON objects to process"
    )
    max_array_items_to_process: int = Field(
        default=50, description="Maximum array items to process"
    )
    max_object_keys_to_process: int = Field(
        default=100, description="Maximum object keys to process"
    )
    simple_chunking_threshold: int = Field(
        default=500_000, description="Use simple chunking for files larger than this"
    )


class EntityExtractionConfig(BaseModel):
    """Entity extraction parameters."""

    batch_size: int = Field(default=10, description="Batch size for entity extraction")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    max_text_length: int = Field(
        default=10000, description="Maximum text length for entity extraction"
    )
    confidence_threshold: float = Field(
        default=0.5, description="Confidence threshold for entity extraction"
    )
    max_entities: int = Field(
        default=50, description="Maximum number of entities to extract"
    )
    retry_delay: float = Field(
        default=1.0, description="Retry delay for failed extractions"
    )
    queue_max_size: int = Field(
        default=1000, description="Maximum items in processing queue"
    )
    progress_callback_interval: float = Field(
        default=1.0, description="Seconds between progress updates"
    )
    task_timeout: float = Field(default=300.0, description="Task timeout in seconds")


class PerformanceConfig(BaseModel):
    """Performance monitoring and resource limits."""

    # Resource monitoring thresholds
    cpu_threshold: float = Field(
        default=80.0, description="CPU usage threshold for alerts (%)"
    )
    memory_threshold: float = Field(
        default=80.0, description="Memory usage threshold for alerts (%)"
    )
    monitoring_interval: float = Field(
        default=5.0, description="Resource monitoring interval (seconds)"
    )

    # Processing timeouts
    base_timeout: float = Field(
        default=10.0, description="Base timeout for processing operations"
    )

    # Vector and embedding settings
    vector_size: int = Field(default=1536, description="Vector embedding dimension")


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

    # Text processing configuration
    text_processing: TextProcessingConfig = Field(
        default_factory=TextProcessingConfig,
        description="Text processing limits and parameters",
    )

    # Chunking limits configuration
    chunking_limits: ChunkingLimitsConfig = Field(
        default_factory=ChunkingLimitsConfig,
        description="Chunking strategy limits and parameters",
    )

    # Entity extraction configuration
    entity_extraction: EntityExtractionConfig = Field(
        default_factory=EntityExtractionConfig,
        description="Entity extraction parameters",
    )

    # Performance configuration
    performance: PerformanceConfig = Field(
        default_factory=PerformanceConfig,
        description="Performance monitoring and resource limits",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert fine-tuning configuration to dictionary."""
        return {
            "chunking": self.chunking.to_dict(),
            "file_conversion": self.file_conversion.to_dict(),
            "text_processing": self.text_processing.model_dump(),
            "chunking_limits": self.chunking_limits.model_dump(),
            "entity_extraction": self.entity_extraction.model_dump(),
            "performance": self.performance.model_dump(),
        }


class MetadataExtractionConfig(BaseConfig):
    """Configuration for metadata extraction settings and strategies.

    This model validates the metadata-extraction.yaml configuration file.
    """

    # Store the raw configuration as-is for now
    # This allows the system to load the file without requiring
    # detailed Pydantic models for every metadata extraction option
    metadata_extraction: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata extraction configuration settings"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata extraction configuration to dictionary.

        Returns:
            Dictionary representation of the configuration
        """
        return self.metadata_extraction


class ValidationConfig(BaseConfig):
    """Configuration for validation rules and repair strategies.

    This model validates the validation.yaml configuration file.
    """

    # Store the raw configuration as-is for now
    # This allows the system to load the file without requiring
    # detailed Pydantic models for every validation option
    validation: dict[str, Any] = Field(
        default_factory=dict,
        description="Validation and repair configuration settings"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert validation configuration to dictionary.

        Returns:
            Dictionary representation of the configuration
        """
        return self.validation


class DomainConfigValidator:
    """Validator for domain-specific configurations."""

    @staticmethod
    def validate_connectivity(data: dict[str, Any]) -> ConnectivityConfig:
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
    def validate_projects(data: dict[str, Any]) -> ProjectsConfig:
        """Validate projects configuration data.

        Args:
            data: Raw configuration data from projects.yaml

        Returns:
            Validated ProjectsConfig instance

        Raises:
            ValidationError: If validation fails
        """
        # Extract the projects section
        projects_data = data.get("projects", {})

        # Inject source_type and source fields for each project's sources
        enhanced_projects_data = {}
        for project_id, project_config in projects_data.items():
            enhanced_project_config = project_config.copy()

            # Process sources if they exist
            if "sources" in enhanced_project_config:
                sources_data = enhanced_project_config["sources"]
                enhanced_sources_data = DomainConfigValidator._inject_source_metadata(
                    sources_data
                )
                enhanced_project_config["sources"] = enhanced_sources_data

            enhanced_projects_data[project_id] = enhanced_project_config

        # Create BaseProjectsConfig with enhanced data
        base_projects_config = BaseProjectsConfig(projects=enhanced_projects_data)

        # Create the ProjectsConfig with the validated projects data
        # Other fields will use their default_factory values
        return ProjectsConfig(projects=base_projects_config)

    @staticmethod
    def _inject_source_metadata(sources_data: dict[str, Any]) -> dict[str, Any]:
        """Inject source_type and source fields into source configurations.

        Args:
            sources_data: Raw sources configuration data

        Returns:
            Dict[str, Any]: Enhanced sources data with injected metadata
        """
        enhanced_data = {}

        for source_type, source_configs in sources_data.items():
            if not isinstance(source_configs, dict):
                enhanced_data[source_type] = source_configs
                continue

            enhanced_source_configs = {}
            for source_name, source_config in source_configs.items():
                if isinstance(source_config, dict):
                    # Create a copy to avoid modifying the original
                    enhanced_config = source_config.copy()

                    # Always inject source_type and source fields
                    enhanced_config["source_type"] = source_type
                    enhanced_config["source"] = source_name

                    enhanced_source_configs[source_name] = enhanced_config
                else:
                    enhanced_source_configs[source_name] = source_config

            enhanced_data[source_type] = enhanced_source_configs

        return enhanced_data

    @staticmethod
    def validate_fine_tuning(data: dict[str, Any]) -> FineTuningConfig:
        """Validate fine-tuning configuration data.

        Args:
            data: Raw fine-tuning configuration data

        Returns:
            Validated FineTuningConfig instance

        Raises:
            ValidationError: If validation fails
        """
        return FineTuningConfig(**data)

    @staticmethod
    def validate_metadata_extraction(data: dict[str, Any]) -> MetadataExtractionConfig:
        """Validate metadata extraction configuration data.

        Args:
            data: Raw metadata extraction configuration data

        Returns:
            Validated MetadataExtractionConfig instance

        Raises:
            ValidationError: If validation fails
        """
        return MetadataExtractionConfig(**data)

    @staticmethod
    def validate_validation(data: dict[str, Any]) -> ValidationConfig:
        """Validate validation configuration data.

        Args:
            data: Raw validation configuration data

        Returns:
            Validated ValidationConfig instance

        Raises:
            ValidationError: If validation fails
        """
        return ValidationConfig(**data)
