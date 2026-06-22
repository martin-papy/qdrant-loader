"""Configuration models for file conversion settings."""

from pydantic import BaseModel, Field

from qdrant_loader.core.conversion.engine import EngineKind
from qdrant_loader.core.conversion.settings import DoclingConversionSettings


class MarkItDownConfig(BaseModel):
    """Configuration for MarkItDown-specific settings."""

    enable_llm_descriptions: bool = Field(
        default=False, description="Enable LLM integration for image descriptions"
    )

    llm_model: str = Field(
        default="gpt-4o",
        description="Deprecated: use global.llm.models.chat; retained for backward compatibility",
    )

    llm_endpoint: str = Field(
        default="https://api.openai.com/v1",
        description="Deprecated: use global.llm.base_url; retained for backward compatibility",
    )

    llm_api_key: str | None = Field(
        default=None,
        description="Deprecated: use global.llm.api_key; retained for backward compatibility",
    )


class FileConversionConfig(BaseModel):
    """Configuration for file conversion operations."""

    max_file_size: int = Field(
        default=52428800,  # 50MB
        description="Maximum file size for conversion (in bytes)",
        gt=0,
        le=104857600,  # 100MB
    )

    conversion_timeout: int = Field(
        default=300,  # 5 minutes
        description="Timeout for conversion operations (in seconds)",
        gt=0,
        le=3600,  # 1 hour
    )

    engine: EngineKind = Field(
        default=EngineKind.MARKITDOWN,
        description=(
            "Which conversion engine to use: 'markitdown' (legacy, markdown-string "
            "path) or 'docling' (structure-aware, full Option B). Config-driven, not a "
            "feature flag."
        ),
    )

    markitdown: MarkItDownConfig = Field(
        default_factory=MarkItDownConfig, description="MarkItDown specific settings"
    )

    docling: DoclingConversionSettings = Field(
        default_factory=DoclingConversionSettings,
        description="Docling engine settings (used when engine='docling')",
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

    download_attachments: bool | None = Field(
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
