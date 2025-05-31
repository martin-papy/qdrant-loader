"""Configuration models for file conversion settings."""

from typing import Optional

from pydantic import BaseModel, Field


class MarkItDownConfig(BaseModel):
    """Configuration for MarkItDown-specific settings."""

    enable_llm_descriptions: bool = Field(
        default=False, description="Enable LLM integration for image descriptions"
    )

    llm_model: str = Field(
        default="gpt-4o", description="LLM model for image descriptions (when enabled)"
    )

    llm_endpoint: str = Field(
        default="https://api.openai.com/v1", description="LLM endpoint (when enabled)"
    )

    llm_api_key: Optional[str] = Field(
        default=None,
        description="API key for LLM service (required when enable_llm_descriptions is True)",
    )


class FileConversionConfig(BaseModel):
    """Configuration for file conversion operations."""

    max_file_size: int = Field(
        default=52428800,  # 50MB
        description="Maximum file size for conversion (in bytes)",
        gt=0,
    )

    conversion_timeout: int = Field(
        default=300,  # 5 minutes
        description="Timeout for conversion operations (in seconds)",
        gt=0,
    )

    markitdown: MarkItDownConfig = Field(
        default_factory=MarkItDownConfig, description="MarkItDown specific settings"
    )

    def get_max_file_size_mb(self) -> float:
        """Get maximum file size in megabytes.

        Returns:
            Maximum file size in MB
        """
        return self.max_file_size / (1024 * 1024)

    def is_file_size_allowed(self, file_size: int) -> bool:
        """Check if file size is within allowed limits.

        Args:
            file_size: File size in bytes

        Returns:
            True if file size is allowed, False otherwise
        """
        return file_size <= self.max_file_size


class ConnectorFileConversionConfig(BaseModel):
    """Configuration for file conversion at the connector level."""

    enable_file_conversion: bool = Field(
        default=False, description="Enable file conversion for this connector"
    )

    download_attachments: Optional[bool] = Field(
        default=None,
        description="Download and process attachments (for Confluence/JIRA/PublicDocs)",
    )

    def should_download_attachments(self) -> bool:
        """Check if attachments should be downloaded.

        Returns:
            True if attachments should be downloaded, False otherwise
        """
        # Default to False if not specified
        return self.download_attachments is True
