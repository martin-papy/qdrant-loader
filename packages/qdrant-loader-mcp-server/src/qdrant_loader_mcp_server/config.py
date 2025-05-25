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

    def __init__(self, **data):
        """Initialize configuration with environment variables."""
        # Initialize sub-configs if not provided
        if "server" not in data:
            data["server"] = ServerConfig()
        if "qdrant" not in data:
            data["qdrant"] = QdrantConfig()
        if "openai" not in data:
            data["openai"] = {"api_key": os.getenv("OPENAI_API_KEY")}
        super().__init__(**data)
