"""Configuration for Git connector."""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import os


class GitAuthConfig(BaseModel):
    """Configuration for Git authentication."""
    token: Optional[str] = Field(
        default=None,
        description="Git access token (loaded from GITHUB_TOKEN env var)"
    )
    username: Optional[str] = Field(
        default=None,
        description="Git username (loaded from GITHUB_USERNAME env var)"
    )

    @field_validator('token', mode='after')
    def load_token_from_env(cls, v: Optional[str]) -> Optional[str]:
        """Load token from environment variable if not provided."""
        return v or os.getenv('GITHUB_TOKEN')

    @field_validator('username', mode='after')
    def load_username_from_env(cls, v: Optional[str]) -> Optional[str]:
        """Load username from environment variable if not provided."""
        return v or os.getenv('GITHUB_USERNAME')


class GitRepoConfig(BaseModel):
    """Configuration for a Git repository source."""
    url: str = Field(
        ...,
        description="URL of the Git repository"
    )
    branch: str = Field(
        default="main",
        description="Branch to clone"
    )
    include_paths: List[str] = Field(
        default=["/"],
        description="Paths to include in processing"
    )
    exclude_paths: List[str] = Field(
        default=[],
        description="Paths to exclude from processing"
    )
    file_types: List[str] = Field(
        default=["*.md", "*.rst", "*.txt"],
        description="File types to process"
    )
    max_file_size: int = Field(
        default=1048576,  # 1MB
        description="Maximum file size to process in bytes",
        ge=0
    )
    depth: int = Field(
        default=1,
        description="Clone depth (0 for full clone)",
        ge=0
    )
    auth: Optional[GitAuthConfig] = Field(
        default=None,
        description="Authentication configuration"
    )

    @field_validator('url')
    def validate_url(cls, v: str) -> str:
        """Validate repository URL."""
        if not v:
            raise ValueError("Repository URL cannot be empty")
        return v

    @field_validator('file_types')
    def validate_file_types(cls, v: List[str]) -> List[str]:
        """Validate file types."""
        if not v:
            raise ValueError("At least one file type must be specified")
        return v 