"""Configuration for Git connector."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from qdrant_loader.config.source_config import SourceConfig


class GitAuthConfig(BaseModel):
    """Configuration for Git authentication."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    token: str = Field(..., description="Authentication token")


class GitRepoConfig(SourceConfig):
    """Configuration for a Git repository."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    branch: str = Field(default="main", description="Branch to clone")
    include_paths: list[str] = Field(
        default_factory=list, description="Paths to include in the repository"
    )
    exclude_paths: list[str] = Field(
        default_factory=list, description="Paths to exclude from the repository"
    )
    file_types: list[str] = Field(
        default_factory=list, description="File types to process"
    )
    max_file_size: int = Field(
        default=1048576, description="Maximum file size in bytes"
    )  # 1MB
    depth: int = Field(default=1, description="Depth of the repository to clone")
    token: str = Field(..., description="Authentication token for the repository")

    temp_dir: str | None = Field(
        None, description="Temporary directory where the repository is cloned"
    )

    @field_validator("base_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate repository URL."""
        if not v:
            raise ValueError("Repository URL cannot be empty")
        return v

    @field_validator("file_types")
    @classmethod
    def validate_file_types(cls, v: list[str]) -> list[str]:
        """Validate file types."""
        if not v:
            raise ValueError("At least one file type must be specified")
        return v
