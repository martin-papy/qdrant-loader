"""Configuration settings for the RAG MCP Server."""

import os

from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()


class ServerConfig(BaseModel):
    """Server configuration settings."""

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"


class QdrantConfig(BaseModel):
    """Qdrant configuration settings."""

    url: str = "http://localhost:6333"
    api_key: str | None = None
    collection_name: str = "documents"

    def __init__(self, **data):
        """Initialize with environment variables if not provided."""
        if "url" not in data:
            data["url"] = os.getenv("QDRANT_URL", "http://localhost:6333")
        if "api_key" not in data:
            data["api_key"] = os.getenv("QDRANT_API_KEY")
        if "collection_name" not in data:
            data["collection_name"] = os.getenv("QDRANT_COLLECTION_NAME", "documents")
        super().__init__(**data)


class SearchConfig(BaseModel):
    """Search optimization configuration settings."""

    # Search result caching
    cache_enabled: bool = True
    cache_ttl: int = 300  # 5 minutes default TTL
    cache_max_size: int = 500  # Maximum cached results
    
    # Search parameters optimization
    hnsw_ef: int = 128  # HNSW search parameter
    use_exact_search: bool = False  # Use exact search when needed
    
    def __init__(self, **data):
        """Initialize with environment variables if not provided."""
        if "cache_enabled" not in data:
            data["cache_enabled"] = os.getenv("SEARCH_CACHE_ENABLED", "true").lower() == "true"
        if "cache_ttl" not in data:
            data["cache_ttl"] = int(os.getenv("SEARCH_CACHE_TTL", "300"))
        if "cache_max_size" not in data:
            data["cache_max_size"] = int(os.getenv("SEARCH_CACHE_MAX_SIZE", "500"))
        if "hnsw_ef" not in data:
            data["hnsw_ef"] = int(os.getenv("SEARCH_HNSW_EF", "128"))
        if "use_exact_search" not in data:
            data["use_exact_search"] = os.getenv("SEARCH_USE_EXACT", "false").lower() == "true"
        super().__init__(**data)


class OpenAIConfig(BaseModel):
    """OpenAI configuration settings."""

    api_key: str
    model: str = "text-embedding-3-small"
    chat_model: str = "gpt-3.5-turbo"


class Config(BaseModel):
    """Main configuration class."""

    server: ServerConfig
    qdrant: QdrantConfig
    openai: OpenAIConfig
    search: SearchConfig

    def __init__(self, **data):
        """Initialize configuration with environment variables."""
        # Initialize sub-configs if not provided
        if "server" not in data:
            data["server"] = ServerConfig()
        if "qdrant" not in data:
            data["qdrant"] = QdrantConfig()
        if "openai" not in data:
            data["openai"] = {"api_key": os.getenv("OPENAI_API_KEY")}
        if "search" not in data:
            data["search"] = SearchConfig()
        super().__init__(**data)
