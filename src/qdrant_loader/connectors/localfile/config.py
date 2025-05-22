"""Configuration for LocalFile connector."""

from pydantic import BaseModel, ConfigDict, Field
from qdrant_loader.config.source_config import SourceConfig


class LocalFileConfig(SourceConfig):
    """Configuration for a local file source."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    base_path: str = Field(..., description="Base directory to scan")
    include_paths: list[str] = Field(
        default_factory=list, description="Paths to include (glob patterns)"
    )
    exclude_paths: list[str] = Field(
        default_factory=list, description="Paths to exclude (glob patterns)"
    )
    file_types: list[str] = Field(default_factory=list, description="File types to process")
    max_file_size: int = Field(default=1048576, description="Maximum file size in bytes")
