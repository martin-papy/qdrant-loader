"""Configuration for Confluence connector."""

from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator, ConfigDict
import os


class ConfluenceSpaceConfig(BaseModel):
    """Configuration for a Confluence space."""
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )
    
    url: str = Field(..., description="Base URL of the Confluence instance")
    space_key: str = Field(..., description="Key of the Confluence space")
    content_types: List[str] = Field(
        default=["page", "blogpost"],
        description="Types of content to process"
    )
    token: str = Field(..., description="Confluence API token")
    email: str = Field(..., description="Email associated with the Confluence account")
    include_labels: List[str] = Field(
        default=[],
        description="List of labels to include (empty list means include all)"
    )
    exclude_labels: List[str] = Field(
        default=[],
        description="List of labels to exclude"
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