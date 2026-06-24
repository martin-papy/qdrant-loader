"""Global configuration settings.

This module defines the global configuration settings that apply across the application,
including chunking, embedding, and logging configurations.
"""

from typing import Any

from pydantic import Field

from qdrant_loader.config.base import BaseConfig
from qdrant_loader.config.chunking import ChunkingConfig
from qdrant_loader.config.qdrant import QdrantConfig
from qdrant_loader.config.sources import SourcesConfig
from qdrant_loader.config.state import StateManagementConfig
from qdrant_loader.config.workers import WorkersConfig
from qdrant_loader.core.file_conversion import FileConversionConfig


class SemanticAnalysisConfig(BaseConfig):
    """Configuration for semantic analysis."""

    num_topics: int = Field(
        default=3, description="Number of topics to extract using LDA"
    )

    lda_passes: int = Field(default=10, description="Number of passes for LDA training")

    spacy_model: str = Field(
        default="en_core_web_md",
        description="spaCy model to use for text processing. Options: en_core_web_sm (15MB, no vectors), en_core_web_md (50MB, 20k vectors), en_core_web_lg (750MB, 514k vectors)",
    )


class GlobalConfig(BaseConfig):
    """Global configuration settings."""

    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    llm: dict[str, Any] | None = Field(
        default=None, description="Unified LLM configuration (provider-agnostic)"
    )
    semantic_analysis: SemanticAnalysisConfig = Field(
        default_factory=SemanticAnalysisConfig,
        description="Semantic analysis configuration",
    )
    state_management: StateManagementConfig = Field(
        default_factory=StateManagementConfig,
        description="State management configuration",
    )
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    file_conversion: FileConversionConfig = Field(
        default_factory=FileConversionConfig,
        description="File conversion configuration",
    )
    qdrant: QdrantConfig = Field(
        default_factory=QdrantConfig, description="Qdrant configuration"
    )
    workers: WorkersConfig = Field(
        default_factory=WorkersConfig,
        description="Worker scheduling and runtime configuration",
    )

    def __init__(self, **data):
        """Initialize global configuration."""
        # If skip_validation is True and no state_management is provided, use in-memory database
        skip_validation = data.pop("skip_validation", False)
        if skip_validation and "state_management" not in data:
            data["state_management"] = {
                "database_path": "./state.db",
                "table_prefix": "qdrant_loader_",
                "connection_pool": {"size": 5, "timeout": 30},
            }
        super().__init__(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert the configuration to a dictionary."""
        return {
            "chunking": {
                "chunk_size": self.chunking.chunk_size,
                "chunk_overlap": self.chunking.chunk_overlap,
                "enable_semantic_analysis": self.chunking.enable_semantic_analysis,
                "enable_enhanced_semantic_analysis": self.chunking.enable_enhanced_semantic_analysis,
            },
            "llm": self.llm,
            "semantic_analysis": {
                "num_topics": self.semantic_analysis.num_topics,
                "lda_passes": self.semantic_analysis.lda_passes,
                "spacy_model": self.semantic_analysis.spacy_model,
            },
            "sources": self.sources.to_dict(),
            "state_management": self.state_management.to_dict(),
            "file_conversion": {
                "max_file_size": self.file_conversion.max_file_size,
                "conversion_timeout": self.file_conversion.conversion_timeout,
                # EngineKind is a StrEnum; emit the plain string so the merged
                # dict re-parses cleanly through the parser merge path.
                "engine": self.file_conversion.engine.value,
                "markitdown": {
                    "enable_llm_descriptions": self.file_conversion.markitdown.enable_llm_descriptions,
                },
                "docling": self.file_conversion.docling.model_dump(mode="json"),
            },
            "qdrant": self.qdrant.to_dict(),
            "workers": self.workers.to_dict(),
        }
