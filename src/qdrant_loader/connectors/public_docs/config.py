"""Configuration for Public Documentation connector."""

from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


class SelectorsConfig(BaseModel):
    """Configuration for HTML content extraction selectors."""
    content: str = Field(
        default="article, main, .content",
        description="Main content container selector"
    )
    remove: List[str] = Field(
        default=["nav", "header", "footer", ".sidebar"],
        description="Elements to remove from the content"
    )
    code_blocks: str = Field(
        default="pre code",
        description="Code blocks selector"
    )


class PublicDocsSourceConfig(BaseModel):
    """Configuration for a single public documentation source."""
    base_url: HttpUrl = Field(
        ...,
        description="Base URL of the documentation website"
    )
    version: str = Field(
        ...,
        description="Specific version of the documentation to fetch"
    )
    content_type: str = Field(
        default="html",
        description="Content type of the documentation"
    )
    path_pattern: Optional[str] = Field(
        default=None,
        description="Specific path pattern to match documentation pages"
    )
    exclude_paths: List[str] = Field(
        default=[],
        description="List of paths to exclude from processing"
    )
    selectors: SelectorsConfig = Field(
        default_factory=SelectorsConfig,
        description="CSS selectors for content extraction"
    )

    @field_validator('content_type')
    def validate_content_type(cls, v: str) -> str:
        """Validate content type."""
        valid_types = ['html', 'markdown', 'rst']
        if v.lower() not in valid_types:
            raise ValueError(f"Content type must be one of {valid_types}")
        return v.lower() 