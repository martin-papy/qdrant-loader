"""Configuration for Confluence connector."""

from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator
import os


class ConfluenceConfig(BaseModel):
    """Configuration for a Confluence space source."""
    url: HttpUrl = Field(
        ...,
        description="Base URL of the Confluence instance"
    )
    space_key: str = Field(
        ...,
        description="Space key to process"
    )
    content_types: List[str] = Field(
        default=["page", "blogpost"],
        description="Content types to process"
    )
    token: Optional[str] = Field(
        default=None,
        description="Confluence API token (loaded from CONFLUENCE_TOKEN env var)"
    )
    email: Optional[str] = Field(
        default=None,
        description="Confluence user email (loaded from CONFLUENCE_EMAIL env var)"
    )
    max_results: Optional[int] = Field(
        default=None,
        description="Maximum number of results to fetch"
    )
    updated_since: Optional[str] = Field(
        default=None,
        description="Only fetch content updated since this date (ISO format)"
    )

    @field_validator('content_types')
    def validate_content_types(cls, v: List[str]) -> List[str]:
        """Validate content types."""
        valid_types = ['page', 'blogpost', 'comment']
        for content_type in v:
            if content_type.lower() not in valid_types:
                raise ValueError(f"Content type must be one of {valid_types}")
        return [t.lower() for t in v]

    @field_validator('token', mode='after')
    def load_token_from_env(cls, v: Optional[str]) -> Optional[str]:
        """Load token from environment variable if not provided."""
        return v or os.getenv('CONFLUENCE_TOKEN')

    @field_validator('email', mode='after')
    def load_email_from_env(cls, v: Optional[str]) -> Optional[str]:
        """Load email from environment variable if not provided."""
        return v or os.getenv('CONFLUENCE_EMAIL') 