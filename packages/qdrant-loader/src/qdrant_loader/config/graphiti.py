"""Graphiti configuration settings.

This module provides configuration classes for Graphiti knowledge graph operations,
including LLM client settings, embedder configuration, and operational parameters.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class GraphitiLLMConfig(BaseModel):
    """Configuration for Graphiti LLM client."""

    provider: str = Field(
        default="openai", description="LLM provider (openai, anthropic, etc.)"
    )
    model: str = Field(default="gpt-4o-mini", description="Model name to use")
    api_key: Optional[str] = Field(
        default=None, description="API key for the LLM provider"
    )
    max_tokens: int = Field(
        default=4000, description="Maximum tokens for LLM responses"
    )
    temperature: float = Field(default=0.1, description="Temperature for LLM responses")

    @validator("temperature")
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v


class GraphitiEmbedderConfig(BaseModel):
    """Configuration for Graphiti embedder."""

    provider: str = Field(default="openai", description="Embedder provider")
    model: str = Field(
        default="text-embedding-3-small", description="Embedding model name"
    )
    api_key: Optional[str] = Field(
        default=None, description="API key for the embedder provider"
    )
    dimensions: Optional[int] = Field(
        default=None, description="Embedding dimensions (if supported)"
    )
    batch_size: int = Field(
        default=100, description="Batch size for embedding operations"
    )


class GraphitiOperationalConfig(BaseModel):
    """Operational configuration for Graphiti."""

    max_episode_length: int = Field(
        default=10000, description="Maximum length of episode content"
    )
    search_limit_default: int = Field(
        default=10, description="Default limit for search results"
    )
    search_limit_max: int = Field(
        default=100, description="Maximum limit for search results"
    )
    enable_auto_indexing: bool = Field(
        default=True, description="Enable automatic index creation"
    )
    enable_constraints: bool = Field(
        default=True, description="Enable database constraints"
    )
    timeout_seconds: int = Field(
        default=30, description="Timeout for operations in seconds"
    )


class GraphitiConfig(BaseSettings):
    """Main Graphiti configuration class."""

    enabled: bool = Field(
        default=False, description="Enable Graphiti knowledge graph functionality"
    )

    # LLM Configuration
    llm: GraphitiLLMConfig = Field(default_factory=GraphitiLLMConfig)

    # Embedder Configuration
    embedder: GraphitiEmbedderConfig = Field(default_factory=GraphitiEmbedderConfig)

    # Operational Configuration
    operational: GraphitiOperationalConfig = Field(
        default_factory=GraphitiOperationalConfig
    )

    # Additional settings
    debug_mode: bool = Field(
        default=False, description="Enable debug logging for Graphiti operations"
    )

    class Config:
        env_prefix = "GRAPHITI_"
        case_sensitive = False

    @validator("llm", pre=True)
    def validate_llm_config(cls, v):
        if isinstance(v, dict):
            return GraphitiLLMConfig(**v)
        return v

    @validator("embedder", pre=True)
    def validate_embedder_config(cls, v):
        if isinstance(v, dict):
            return GraphitiEmbedderConfig(**v)
        return v

    @validator("operational", pre=True)
    def validate_operational_config(cls, v):
        if isinstance(v, dict):
            return GraphitiOperationalConfig(**v)
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return {
            "enabled": self.enabled,
            "llm": {
                "provider": self.llm.provider,
                "model": self.llm.model,
                "max_tokens": self.llm.max_tokens,
                "temperature": self.llm.temperature,
            },
            "embedder": {
                "provider": self.embedder.provider,
                "model": self.embedder.model,
                "dimensions": self.embedder.dimensions,
                "batch_size": self.embedder.batch_size,
            },
            "operational": {
                "max_episode_length": self.operational.max_episode_length,
                "search_limit_default": self.operational.search_limit_default,
                "search_limit_max": self.operational.search_limit_max,
                "enable_auto_indexing": self.operational.enable_auto_indexing,
                "enable_constraints": self.operational.enable_constraints,
                "timeout_seconds": self.operational.timeout_seconds,
            },
            "debug_mode": self.debug_mode,
        }
