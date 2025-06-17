"""Configuration for LocalFile connector."""

from pydantic import AnyUrl, ConfigDict, Field, field_validator

from qdrant_loader.config.source_config import SourceConfig


class LocalFileConfig(SourceConfig):
    """Configuration for a local file source."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    include_paths: list[str] = Field(
        default_factory=list, description="Paths to include (glob patterns)"
    )
    exclude_paths: list[str] = Field(
        default_factory=list, description="Paths to exclude (glob patterns)"
    )
    file_types: list[str] = Field(
        default_factory=list, description="File types to process"
    )
    max_file_size: int = Field(
        default=1048576, description="Maximum file size in bytes"
    )

    # Metadata extraction
    enable_enhanced_metadata: bool = Field(
        default=False,
        description="Enable enhanced metadata extraction including file system attributes, directory hierarchy, and content cross-references",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: AnyUrl) -> AnyUrl:
        if v.scheme != "file":
            raise ValueError("base_url for localfile must start with 'file://'")
        return v
