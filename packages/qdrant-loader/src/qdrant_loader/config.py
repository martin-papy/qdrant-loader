"""Configuration management for the application."""

from pydantic import BaseModel, Field


class SemanticAnalysisConfig(BaseModel):
    """Configuration for semantic analysis."""

    num_topics: int = Field(
        default=3, description="Number of topics to extract using LDA"
    )

    lda_passes: int = Field(default=10, description="Number of passes for LDA training")


class ChunkingConfig(BaseModel):
    """Configuration for document chunking."""

    chunk_size: int = Field(
        default=1000, description="Maximum size of each chunk in characters"
    )

    chunk_overlap: int = Field(
        default=200, description="Number of characters to overlap between chunks"
    )


class GlobalConfig(BaseModel):
    """Global configuration settings."""

    chunking: ChunkingConfig = Field(
        default_factory=ChunkingConfig, description="Chunking configuration"
    )

    semantic_analysis: SemanticAnalysisConfig = Field(
        default_factory=SemanticAnalysisConfig,
        description="Semantic analysis configuration",
    )


class Settings(BaseModel):
    """Application settings."""

    # Qdrant configuration
    QDRANT_URL: str
    QDRANT_API_KEY: str
    QDRANT_COLLECTION_NAME: str

    # OpenAI configuration
    OPENAI_API_KEY: str

    # State management
    STATE_DB_PATH: str

    # Git repository configuration
    REPO_TOKEN: str
    REPO_URL: str

    # Confluence configuration
    CONFLUENCE_URL: str
    CONFLUENCE_SPACE_KEY: str
    CONFLUENCE_TOKEN: str
    CONFLUENCE_EMAIL: str

    # Jira configuration
    JIRA_URL: str
    JIRA_PROJECT_KEY: str
    JIRA_TOKEN: str
    JIRA_EMAIL: str

    # Global configuration
    global_config: GlobalConfig = Field(
        default_factory=GlobalConfig, description="Global configuration settings"
    )
