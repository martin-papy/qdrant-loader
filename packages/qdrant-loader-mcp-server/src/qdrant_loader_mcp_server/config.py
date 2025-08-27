"""Configuration settings for the RAG MCP Server."""

import json
import logging
import os
from typing import Annotated

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()

# Module logger
logger = logging.getLogger(__name__)


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


def parse_float_env(
    var_name: str,
    default: float,
    *,
    min_value: float | None = None,
    max_value: float | None = None,
) -> float:
    """Parse a float from an environment variable with bounds checking.

    Args:
        var_name: Environment variable name to read.
        default: Value to use when the variable is not set.
        min_value: Optional lower bound (inclusive).
        max_value: Optional upper bound (inclusive).

    Raises:
        ValueError: If the variable is set but not a float, or out of bounds.
    """
    raw_value = os.getenv(var_name)
    if raw_value is None or raw_value.strip() == "":
        return default
    try:
        value = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid float for {var_name}: {raw_value!r}") from exc
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

    # Conflict detection performance controls (defaults calibrated for P95 ~8–10s)
    conflict_limit_default: Annotated[int, Field(ge=2, le=50)] = 10
    conflict_max_pairs_total: Annotated[int, Field(ge=1, le=200)] = 24
    conflict_tier_caps: dict = {
        "primary": 12,
        "secondary": 8,
        "tertiary": 4,
        "fallback": 0,
    }
    conflict_use_llm: bool = True
    conflict_max_llm_pairs: Annotated[int, Field(ge=0, le=10)] = 2
    conflict_llm_model: str = "gpt-4o-mini"
    conflict_llm_timeout_s: Annotated[float, Field(gt=0, le=60)] = 12.0
    conflict_overall_timeout_s: Annotated[float, Field(gt=0, le=60)] = 9.0
    conflict_text_window_chars: Annotated[int, Field(ge=200, le=8000)] = 2000
    conflict_embeddings_timeout_s: Annotated[float, Field(gt=0, le=30)] = 2.0
    conflict_embeddings_max_concurrency: Annotated[int, Field(ge=1, le=20)] = 5

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

        # Conflict detection env overrides (optional; safe defaults used if unset)
        def _get_env_dict(name: str, default: dict) -> dict:
            raw = os.getenv(name)
            if not raw:
                return default
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return parsed
                return default
            except (json.JSONDecodeError, ValueError) as exc:
                # Shorten raw value to avoid logging excessively large strings
                raw_preview = raw if len(raw) <= 200 else f"{raw[:200]}..."
                logger.warning(
                    "Failed to parse JSON for env var %s; raw=%r; falling back to default. Error: %s",
                    name,
                    raw_preview,
                    exc,
                    exc_info=True,
                )
                return default

        if "conflict_limit_default" not in data:
            data["conflict_limit_default"] = parse_int_env(
                "SEARCH_CONFLICT_LIMIT_DEFAULT", 10, min_value=2, max_value=50
            )
        if "conflict_max_pairs_total" not in data:
            data["conflict_max_pairs_total"] = parse_int_env(
                "SEARCH_CONFLICT_MAX_PAIRS_TOTAL", 24, min_value=1, max_value=200
            )
        if "conflict_tier_caps" not in data:
            data["conflict_tier_caps"] = _get_env_dict(
                "SEARCH_CONFLICT_TIER_CAPS",
                {"primary": 12, "secondary": 8, "tertiary": 4, "fallback": 0},
            )
        if "conflict_use_llm" not in data:
            data["conflict_use_llm"] = parse_bool_env("SEARCH_CONFLICT_USE_LLM", True)
        if "conflict_max_llm_pairs" not in data:
            data["conflict_max_llm_pairs"] = parse_int_env(
                "SEARCH_CONFLICT_MAX_LLM_PAIRS", 2, min_value=0, max_value=10
            )
        if "conflict_llm_model" not in data:
            data["conflict_llm_model"] = os.getenv(
                "SEARCH_CONFLICT_LLM_MODEL", "gpt-4o-mini"
            )
        if "conflict_llm_timeout_s" not in data:
            data["conflict_llm_timeout_s"] = parse_float_env(
                "SEARCH_CONFLICT_LLM_TIMEOUT_S", 12.0, min_value=1.0, max_value=60.0
            )
        if "conflict_overall_timeout_s" not in data:
            data["conflict_overall_timeout_s"] = parse_float_env(
                "SEARCH_CONFLICT_OVERALL_TIMEOUT_S", 9.0, min_value=1.0, max_value=60.0
            )
        if "conflict_text_window_chars" not in data:
            data["conflict_text_window_chars"] = parse_int_env(
                "SEARCH_CONFLICT_TEXT_WINDOW_CHARS", 2000, min_value=200, max_value=8000
            )
        if "conflict_embeddings_timeout_s" not in data:
            data["conflict_embeddings_timeout_s"] = parse_float_env(
                "SEARCH_CONFLICT_EMBEDDINGS_TIMEOUT_S",
                2.0,
                min_value=1.0,
                max_value=30.0,
            )
        if "conflict_embeddings_max_concurrency" not in data:
            data["conflict_embeddings_max_concurrency"] = parse_int_env(
                "SEARCH_CONFLICT_EMBEDDINGS_MAX_CONCURRENCY",
                5,
                min_value=1,
                max_value=20,
            )
        super().__init__(**data)


class OpenAIConfig(BaseModel):
    """OpenAI configuration settings."""

    api_key: str
    model: str = "text-embedding-3-small"
    chat_model: str = "gpt-3.5-turbo"


class Config(BaseModel):
    """Main configuration class."""

    server: ServerConfig = Field(default_factory=ServerConfig)
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    openai: OpenAIConfig = Field(
        default_factory=lambda: OpenAIConfig(api_key=os.getenv("OPENAI_API_KEY"))
    )
    search: SearchConfig = Field(default_factory=SearchConfig)
