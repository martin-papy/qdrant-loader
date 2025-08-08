"""Configuration settings for the RAG MCP Server."""

import os
from typing import Annotated

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()


# --- Helpers -----------------------------------------------------------------

# Accepted boolean truthy/falsey strings (case-insensitive)
TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "f", "no", "n", "off"}


def parse_bool_env(var_name: str, default: bool) -> bool:
    """Parse a boolean from an environment variable robustly.

    Accepted true values: 1, true, t, yes, y, on
    Accepted false values: 0, false, f, no, n, off

    Raises:
        ValueError: If the variable is set but not a valid boolean value.
    """
    raw_value = os.getenv(var_name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(
        f"Invalid boolean for {var_name}: {raw_value!r}. "
        f"Expected one of {sorted(TRUE_VALUES | FALSE_VALUES)}"
    )


def parse_int_env(
    var_name: str,
    default: int,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    """Parse an integer from an environment variable with bounds checking.

    Args:
        var_name: Environment variable name to read.
        default: Value to use when the variable is not set.
        min_value: Optional lower bound (inclusive).
        max_value: Optional upper bound (inclusive).

    Raises:
        ValueError: If the variable is set but not an int, or out of bounds.
    """
    raw_value = os.getenv(var_name)
    if raw_value is None or raw_value.strip() == "":
        return default
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid integer for {var_name}: {raw_value!r}") from exc
    if min_value is not None and value < min_value:
        raise ValueError(f"{var_name} must be >= {min_value}; got {value}")
    if max_value is not None and value > max_value:
        raise ValueError(f"{var_name} must be <= {max_value}; got {value}")
    return value


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
    cache_ttl: Annotated[int, Field(ge=0, le=86_400)] = 300  # 0s..24h
    cache_max_size: Annotated[int, Field(ge=1, le=100_000)] = 500

    # Search parameters optimization
    hnsw_ef: Annotated[int, Field(ge=1, le=32_768)] = 128  # HNSW search parameter
    use_exact_search: bool = False  # Use exact search when needed

    def __init__(self, **data):
        """Initialize with environment variables if not provided.

        Performs robust boolean parsing and strict numeric validation to avoid
        subtle runtime issues from malformed environment inputs.
        """
        if "cache_enabled" not in data:
            data["cache_enabled"] = parse_bool_env("SEARCH_CACHE_ENABLED", True)
        if "cache_ttl" not in data:
            data["cache_ttl"] = parse_int_env(
                "SEARCH_CACHE_TTL", 300, min_value=0, max_value=86_400
            )
        if "cache_max_size" not in data:
            data["cache_max_size"] = parse_int_env(
                "SEARCH_CACHE_MAX_SIZE", 500, min_value=1, max_value=100_000
            )
        if "hnsw_ef" not in data:
            data["hnsw_ef"] = parse_int_env(
                "SEARCH_HNSW_EF", 128, min_value=1, max_value=32_768
            )
        if "use_exact_search" not in data:
            data["use_exact_search"] = parse_bool_env("SEARCH_USE_EXACT", False)
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
