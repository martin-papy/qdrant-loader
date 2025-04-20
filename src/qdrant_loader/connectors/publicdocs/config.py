"""Configuration for Public Documentation connector."""

from pydantic import BaseModel, Field, field_validator

from qdrant_loader.config.source_config import SourceConfig


class SelectorsConfig(BaseModel):
    """Configuration for HTML content extraction selectors."""

    content: str = Field(
        default="article, main, .content", description="Main content container selector"
    )
    remove: list[str] = Field(
        default=["nav", "header", "footer", ".sidebar"],
        description="Elements to remove from the content",
    )
    code_blocks: str = Field(default="pre code", description="Code blocks selector")


class PublicDocsSourceConfig(SourceConfig):
    """Configuration for a single public documentation source."""

    version: str = Field(..., description="Specific version of the documentation to fetch")
    content_type: str = Field(default="html", description="Content type of the documentation")
    path_pattern: str | None = Field(
        default=None, description="Specific path pattern to match documentation pages"
    )
    exclude_paths: list[str] = Field(
        default=[], description="List of paths to exclude from processing"
    )
    selectors: SelectorsConfig = Field(
        default_factory=SelectorsConfig, description="CSS selectors for content extraction"
    )

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        """Validate content type."""
        valid_types = ["html", "markdown", "rst"]
        if v.lower() not in valid_types:
            raise ValueError(f"Content type must be one of {valid_types}")
        return v.lower()
