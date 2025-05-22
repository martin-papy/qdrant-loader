"""Base configuration for all source types."""

from pydantic import AnyUrl, BaseModel, ConfigDict, Field


class SourceConfig(BaseModel):
    """Base configuration for all source types."""

    source_type: str = Field(..., description="Type of the source")
    source: str = Field(..., description="Name of the source")
    base_url: AnyUrl = Field(..., description="Base URL of the source")

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")
